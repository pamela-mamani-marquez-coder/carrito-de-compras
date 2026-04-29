from flask import Flask, render_template, request, redirect, url_for, flash, session, g
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'carrito_secreto_2026'
DATABASE = 'tienda.db'

# Conexión a BD
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Inicializar BD con productos
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio REAL NOT NULL,
            imagen TEXT,
            stock INTEGER DEFAULT 0
        )''')
        
        # Verificar si ya hay productos
        count = db.execute('SELECT COUNT(*) FROM productos').fetchone()[0]
        if count == 0:
            # Insertar productos de ejemplo
            productos_ejemplo = [
                ('Laptop HP', 'Laptop HP 15" Intel i5, 8GB RAM, 256GB SSD', 650.00, 'laptop.jpg', 10),
                ('Mouse Inalámbrico', 'Mouse Logitech inalámbrico ergonómico', 25.00, 'mouse.jpg', 50),
                ('Teclado Mecánico', 'Teclado mecánico RGB retroiluminado', 75.00, 'teclado.jpg', 30),
                ('Monitor 24"', 'Monitor LED Full HD 144Hz', 200.00, 'monitor.jpg', 15),
                ('Audífonos Gaming', 'Audífonos con micrófono y sonido surround', 60.00, 'audifonos.jpg', 25),
                ('Webcam HD', 'Cámara web 1080p con micrófono', 45.00, 'webcam.jpg', 20),
            ]
            db.executemany('INSERT INTO productos (nombre, descripcion, precio, imagen, stock) VALUES (?,?,?,?,?)', productos_ejemplo)
            db.commit()
        db.commit()

# Ruta principal - Catálogo
@app.route('/')
def index():
    db = get_db()
    productos = db.execute('SELECT * FROM productos').fetchall()
    return render_template('index.html', productos=productos)

# Agregar al carrito
@app.route('/agregar/<int:id>', methods=['POST'])
def agregar_al_carrito(id):
    if 'carrito' not in session:
        session['carrito'] = {}
    
    cantidad = int(request.form.get('cantidad', 1))
    
    if str(id) in session['carrito']:
        session['carrito'][str(id)] += cantidad
    else:
        session['carrito'][str(id)] = cantidad
    
    session.modified = True
    flash('Producto agregado al carrito', 'success')
    return redirect(url_for('index'))

# Ver carrito
@app.route('/carrito')
def ver_carrito():
    if 'carrito' not in session or not session['carrito']:
        flash('Tu carrito está vacío', 'info')
        return render_template('carrito.html', productos=[], total=0)
    
    db = get_db()
    productos_en_carrito = []
    total = 0
    
    for prod_id, cantidad in session['carrito'].items():
        producto = db.execute('SELECT * FROM productos WHERE id = ?', (prod_id,)).fetchone()
        if producto:
            subtotal = producto['precio'] * cantidad
            total += subtotal
            productos_en_carrito.append({
                'producto': producto,
                'cantidad': cantidad,
                'subtotal': subtotal
            })
    
    return render_template('carrito.html', productos=productos_en_carrito, total=total)

# Actualizar cantidad
@app.route('/actualizar/<int:id>', methods=['POST'])
def actualizar_carrito(id):
    cantidad = int(request.form.get('cantidad', 1))
    
    if 'carrito' in session and str(id) in session['carrito']:
        if cantidad > 0:
            session['carrito'][str(id)] = cantidad
        else:
            del session['carrito'][str(id)]
        session.modified = True
    
    flash('Carrito actualizado', 'info')
    return redirect(url_for('ver_carrito'))

# Eliminar del carrito
@app.route('/eliminar/<int:id>')
def eliminar_del_carrito(id):
    if 'carrito' in session and str(id) in session['carrito']:
        del session['carrito'][str(id)]
        session.modified = True
        flash('Producto eliminado del carrito', 'danger')
    
    return redirect(url_for('ver_carrito'))
#checkout
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'carrito' not in session or not session['carrito']:
        flash('Tu carrito está vacío', 'warning')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Procesar datos del formulario
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        direccion = request.form.get('direccion')
        telefono = request.form.get('telefono', '')
        
        # Preparar datos del pedido para mostrar en confirmación
        db = get_db()
        productos_pedido = []
        total = 0
        
        for prod_id, cantidad in session['carrito'].items():
            producto = db.execute('SELECT * FROM productos WHERE id = ?', (prod_id,)).fetchone()
            if producto:
                subtotal = producto['precio'] * cantidad
                total += subtotal
                productos_pedido.append({
                    'nombre': producto['nombre'],
                    'cantidad': cantidad,
                    'precio': producto['precio'],
                    'subtotal': subtotal
                })
        
        pedido_data = {
            'nombre': nombre,
            'email': email,
            'direccion': direccion,
            'telefono': telefono,
            'productos': productos_pedido,
            'total': total,
            'fecha': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'orden_id': f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        # Limpiar carrito
        session.pop('carrito', None)
        
        # Mostrar página de confirmación (no PDF)
        flash('¡Compra exitosa! Tu orden ha sido procesada.', 'success')
        return render_template('confirmacion.html', pedido=pedido_data)
    
    # GET: mostrar formulario de checkout
    db = get_db()
    total = sum(
        db.execute('SELECT precio FROM productos WHERE id = ?', (pid,)).fetchone()[0] * cant 
        for pid, cant in session['carrito'].items()
    )
    return render_template('checkout.html', total=total)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)