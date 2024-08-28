#debug mode

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file,jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_mysqldb import MySQL
from uuid import uuid4
from datetime import datetime
import pdfkit
import platform
from io import BytesIO



app = Flask(__name__)

# Configuración de la clave secreta
app.config['SECRET_KEY'] = 'mi_clave_secreta_123'  # Cambia esto a una clave secreta única y segura


# Configuración dinámica para pdfkit según el entorno
if platform.system() == "Windows":
    # Ruta de wkhtmltopdf en Windows
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
    #conexion MySQL
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = '2911'#'1608'#1405
    app.config['MYSQL_DB'] = 'gestion_de_proyectos'
    
else:
    # Para Linux y MacOS, wkhtmltopdf está generalmente en /usr/bin/wkhtmltopdf
    PDFKIT_CONFIG = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
    #conexion MySQL
    app.config['MYSQL_HOST'] = 'pierzam.mysql.pythonanywhere-services.com'
    app.config['MYSQL_USER'] = 'pierzam'
    app.config['MYSQL_PASSWORD'] = '70983031p'
    app.config['MYSQL_DB'] = 'pierzam$gestion_proyectos'

conexion = MySQL(app)
# Configuración Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

class User(UserMixin):
    def __init__(self, id_sesion, nombre_sesion, apellido_sesion):
        self.id = id_sesion  # `UserMixin` espera `id` como atributo
        self.nombre = nombre_sesion
        self.apellido = apellido_sesion

@login_manager.user_loader
def load_user(user_id):
    # Cargar el usuario basado en su ID
    cursor = conexion.connection.cursor()
    cursor.execute("SELECT * FROM Empleado WHERE ID_Empleado = %s", (user_id,))
    user_empleado = cursor.fetchone()
    cursor.close()
    
    if user_empleado:
        return User(id_sesion=user_empleado[0], nombre_sesion=user_empleado[1], apellido_sesion=user_empleado[2])
    return None


@app.route('/')
def index():
    return redirect(url_for('iniciar_sesion'))

@app.route('/iniciar_sesion', methods=['GET', 'POST']) # visualizar eventos
def iniciar_sesion():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        try:
            cursor = conexion.connection.cursor()
            cursor.execute("SELECT * FROM Empleado WHERE DNI_Empleado = %s", (usuario,))
            #id, nombre,apellido,telefono,dni,contraseña,email,direccion,estado,rol
            #0.  1       2          3       4   5           6   7           8   9
            user_empleado = cursor.fetchone()
            cursor.close()
            
            if user_empleado and user_empleado[5] == password:
                user = User(id_sesion=user_empleado[0], nombre_sesion=user_empleado[1], apellido_sesion=user_empleado[2])
                login_user(user)
                return redirect(url_for('dashboard_menu'))
            
            flash('Credenciales inválidas. Por favor, intenta nuevamente.')
            return redirect(url_for('index'))
        except Exception as e:
            flash('Ocurrió un error al procesar tu solicitud: {}'.format(e))
            return redirect(url_for('index'))
    return render_template('iniciar_sesion.html')

@app.route('/menu')
@login_required
def dashboard_menu():
    nombre = current_user.nombre
    apellido = current_user.apellido
    return render_template('dashboard_menu.html', nombre = nombre, apellido = apellido)
    

@app.route('/ver_productos', methods=['GET'])
@login_required
def ver_productos():
    search = request.args.get('search', '')
    filtros_marca = request.args.getlist('filter_marca')  # Filtros seleccionados por marca
    filtros_tipo = request.args.getlist('filter_tipo')  # Filtros seleccionados por tipo
    sort = request.args.get('sort', '')  # Parámetro de ordenación

    try:
        cursor = conexion.connection.cursor()

        # Obtener las marcas y tipos para el filtrado
        cursor.execute("SELECT DISTINCT Nombre_Marca FROM Marca")
        marcas = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT Tipo FROM Producto")
        tipos = [row[0] for row in cursor.fetchall()]

        # Construcción de la consulta SQL
        query = """
            SELECT p.ID_Producto, p.Precio_Venta, p.Nombre_Producto, p.Descripcion, p.Estado, p.Stock, p.Tipo, m.Nombre_Marca
            FROM Producto p
            LEFT JOIN Marca m ON p.ID_Marca = m.ID_Marca
            WHERE p.Estado = 'Disponible'
        """

        params = []
        
        # Agregar condiciones de filtro por marca
        if filtros_marca:
            query += " AND m.Nombre_Marca IN (" + ", ".join(["%s"] * len(filtros_marca)) + ")"
            params.extend(filtros_marca)

        # Agregar condiciones de filtro por tipo
        if filtros_tipo:
            query += " AND p.Tipo IN (" + ", ".join(["%s"] * len(filtros_tipo)) + ")"
            params.extend(filtros_tipo)

        # Agregar condiciones de búsqueda
        if search:
            query += " AND (p.Nombre_Producto LIKE %s OR p.Tipo LIKE %s OR m.Nombre_Marca LIKE %s)"
            params += [f'%{search}%'] * 3

        # Agregar cláusula de ordenación
        if sort == 'nombre_asc':
            query += " ORDER BY p.Nombre_Producto ASC"
        elif sort == 'nombre_desc':
            query += " ORDER BY p.Nombre_Producto DESC"
        elif sort == 'precio_asc':
            query += " ORDER BY p.Precio_Venta ASC"
        elif sort == 'precio_desc':
            query += " ORDER BY p.Precio_Venta DESC"

        # Ejecutar la consulta
        cursor.execute(query, params)
        productos = cursor.fetchall()
        cursor.close()

        # Detectar si la solicitud es AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Renderizar solo la parte de productos como un fragmento de HTML
            return render_template('productos/_productos.html', productos=productos)
        else:
            # Renderizar la página completa
            return render_template('productos/ver_productos.html', productos=productos, marcas=marcas, tipos=tipos, selected_filters=filtros_marca + filtros_tipo)
    except Exception as e:
        flash('Error al cargar los productos: {}'.format(e))
        return redirect(url_for('dashboard_menu'))

@app.route('/ver_detalle_producto/<string:id_producto>')
def ver_detalle_producto(id_producto):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT * FROM Producto WHERE ID_Producto = %s", (id_producto,))
        producto = cursor.fetchone()
        cursor.close()
        print(producto)
        if producto:
            return render_template('productos/producto_detalle.html', producto=producto)
        else:
            flash('Producto no encontrado.')
            return redirect(url_for('ver_productos'))
    except Exception as e:
        flash('Error al cargar los detalles del producto: {}'.format(e))
        return redirect(url_for('ver_productos'))

@app.route('/producto/<id_producto>', methods=['GET', 'POST'])
def editar_producto(id_producto):
    if request.method == 'POST':
        # Recibe datos del formulario
        nombre = request.form['nombre']
        precio = request.form['precio']
        descripcion = request.form['descripcion']
        stock = request.form['stock']
        estado = request.form['estado']
        tipo = request.form['tipo']

        # Realiza la actualización del producto en la base de datos
        try:
            cursor = conexion.connection.cursor()
            query = """
                UPDATE Producto 
                SET Nombre_Producto= %s, Precio_Venta = %s, Descripcion = %s, Stock = %s, Estado = %s, Tipo = %s 
                WHERE ID_Producto = %s
            """
            cursor.execute(query, (nombre, precio, descripcion, stock, estado, tipo, id_producto))
            conexion.connection.commit()
            flash('Producto actualizado con éxito!', 'success')
        except Exception as e:
            flash(f'Error al actualizar el producto: {e}', 'danger')
        finally:
            cursor.close()

        return redirect(url_for('editar_producto', id_producto=id_producto))

    else:
        # Obtener los detalles del producto de la base de datos
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT * FROM Producto WHERE ID_Producto = %s", (id_producto,))
        producto = cursor.fetchone()
        cursor.close()
        
        return render_template('productos/producto_detalle.html', producto=producto)

@app.route('/agregar_al_carrito', methods=['POST'])
@login_required
def agregar_al_carrito():
    id_producto = request.form.get('id_producto')
    cantidad = int(request.form.get('cantidad'))

    if cantidad <= 0:
        flash('La cantidad debe ser mayor a 0.')
        return redirect(url_for('ver_productos'))

    try:
        cursor = conexion.connection.cursor()

        # Verificar si ya existe un carrito para el usuario actual
        cursor.execute("""
            SELECT ID_Carrito 
            FROM Carrito 
            WHERE ID_Empleado = %s AND DATE(Fecha_Creacion) = DATE(NOW())
        """, (current_user.id,))
        carrito = cursor.fetchone()

        if carrito:
            id_carrito = carrito[0]
        else:
            id_carrito = str(uuid4())
            cursor.execute("""
                INSERT INTO Carrito (ID_Carrito, ID_Empleado, Fecha_Creacion) 
                VALUES (%s, %s, %s)
            """, (id_carrito, current_user.id, datetime.now()))
        
        # Verificar si el producto ya está en el carrito
        cursor.execute("""
            SELECT ID_Detalle_Carrito 
            FROM Detalle_Carrito 
            WHERE ID_Carrito = %s AND ID_Producto = %s
        """, (id_carrito, id_producto))
        detalle = cursor.fetchone()

        if detalle:
            # Actualizar cantidad
            cursor.execute("""
                UPDATE Detalle_Carrito 
                SET Cantidad = Cantidad + %s 
                WHERE ID_Detalle_Carrito = %s
            """, (cantidad, detalle[0]))
        else:
            # Insertar nuevo detalle
            id_detalle_carrito = str(uuid4())
            cursor.execute("""
                INSERT INTO Detalle_Carrito (ID_Detalle_Carrito, ID_Carrito, ID_Producto, Cantidad) 
                VALUES (%s, %s, %s, %s)
            """, (id_detalle_carrito, id_carrito, id_producto, cantidad))
        
        conexion.connection.commit()
        cursor.close()
        flash('Producto agregado al carrito exitosamente.')
        return redirect(url_for('ver_productos'))
    except Exception as e:
        flash('Error al agregar el producto al carrito: {}'.format(e))
        return redirect(url_for('ver_productos'))



    
@app.route('/obtener_cantidad_carrito', methods=['GET'])
@login_required
def obtener_cantidad_carrito():
    try:
        cursor = conexion.connection.cursor()
        
        # Consulta para obtener el ID del carrito del empleado actual
        cursor.execute("""
            SELECT ID_Carrito 
            FROM Carrito 
            WHERE ID_Empleado = %s AND DATE(Fecha_Creacion) = DATE(NOW())
        """, (current_user.id,))
        carrito_id = cursor.fetchone()
        
        if carrito_id is None:
            # Si no hay carrito para hoy, devolver cantidad 0
            cursor.close()
            return jsonify({'cantidad': 0})
        
        carrito_id = carrito_id[0]
        
        # Consulta para sumar la cantidad total de productos en el carrito
        cursor.execute("""
            SELECT SUM(Cantidad) 
            FROM Detalle_Carrito 
            WHERE ID_Carrito = %s
        """, (carrito_id,))
        cantidad_total = cursor.fetchone()[0]
        
        # Si no hay productos en el carrito, la suma será None, así que establecemos 0 en ese caso
        if cantidad_total is None:
            cantidad_total = 0
        
        cursor.close()
        return jsonify({'cantidad': cantidad_total})
    except Exception as e:
        print(f'Error al obtener la cantidad del carrito: {e}')
        return jsonify({'cantidad': 0}), 500



@app.route('/ver_carrito', methods=['GET', 'POST'])
@login_required
def ver_carrito():
    productos = []
    total = 0.0
    
    if request.method == 'POST':
        dni_cliente = request.form.get('dni_cliente')

        cursor = conexion.connection.cursor()
        cursor.execute("SELECT * FROM Cliente WHERE DNI_Cliente = %s", (dni_cliente,))
        cliente = cursor.fetchone()

        if cliente:
            # Guardar el ID_Cliente en la sesión
            session['id_cliente'] = cliente[0]  # Asumiendo que el ID_Cliente es el primer campo en el resultado
            return render_template('productos/carrito.html', productos=productos, total=total, cliente=cliente)

        # Cliente no encontrado, mostrar formulario para agregar nuevo cliente
        return render_template('productos/carrito.html', productos=productos, total=total, dni_cliente=dni_cliente)

    try:
        cursor = conexion.connection.cursor()

        # Obtener el carrito del usuario actual
        cursor.execute("""
            SELECT ID_Carrito
            FROM Carrito
            WHERE ID_Empleado = %s AND DATE(Fecha_Creacion) = DATE(NOW())
        """, (current_user.id,))
        carrito = cursor.fetchone()

        if not carrito:
            flash('No tienes productos en el carrito.')
            return redirect(url_for('ver_productos'))
        id_carrito = carrito[0]

        # Obtener los detalles del carrito
        cursor.execute("""
            SELECT p.ID_Producto, p.Nombre_Producto, p.Precio_Venta, dc.Cantidad
            FROM Detalle_Carrito dc
            JOIN Producto p ON dc.ID_Producto = p.ID_Producto
            WHERE dc.ID_Carrito = %s
        """, (id_carrito,))
        productos = cursor.fetchall()

        # Calcular el total acumulado
        total = sum(producto[2] * producto[3] for producto in productos)

        cursor.close()
        return render_template('productos/carrito.html', productos=productos, total=total)

    except Exception as e:
        flash(f'Error al obtener el carrito: {e}')
        return redirect(url_for('ver_productos'))



@app.route('/registrar_cliente', methods=['POST'])
def registrar_cliente():
    try:
        dni_cliente = request.form.get('dni_cliente')
        nombre_cliente = request.form.get('nombre_cliente')
        apellido_cliente = request.form.get('apellido_cliente')
        telefono_cliente = request.form.get('telefono_cliente')
        email_cliente = request.form.get('email_cliente')
        direccion_cliente = request.form.get('direccion_cliente')

        # Insertar nuevo cliente en la base de datos
        cursor = conexion.connection.cursor()
        id_cliente = str(uuid4())
        cursor.execute("""
            INSERT INTO Cliente (ID_Cliente, Nombre_Cliente, Apellido_Cliente, DNI_Cliente, Telefono_Cliente, Email, Direccion)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (id_cliente, nombre_cliente, apellido_cliente, dni_cliente, telefono_cliente, email_cliente, direccion_cliente))
        conexion.connection.commit()
        cursor.close()

        flash('Cliente registrado exitosamente.')
        return redirect(url_for('ver_carrito'))

    except Exception as e:
        flash(f'Error al registrar el cliente: {e}')
        return redirect(url_for('ver_carrito'))

@app.route('/buscar_cliente_ajax', methods=['POST'])
@login_required
def buscar_cliente_ajax():
    dni_cliente = request.form.get('dni_cliente')
    
    cursor = conexion.connection.cursor()
    cursor.execute("SELECT * FROM Cliente WHERE DNI_Cliente = %s", (dni_cliente,))
    cliente = cursor.fetchone()
    cursor.close()

    if cliente:
        # Guardar el ID del cliente en la sesión
        session['id_cliente'] = cliente[0]
        # Renderizar solo el fragmento de HTML para los datos del cliente
        return render_template('productos/cliente_info.html', cliente=cliente)
    else:
        # Renderizar solo el fragmento de HTML para el formulario de registro
        return render_template('productos/cliente_info.html', dni_cliente=dni_cliente)


@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    try:
        cursor = conexion.connection.cursor()

        # Obtener el ID_Cliente de la sesión
        id_cliente = session.get('id_cliente')
        
        if not id_cliente:
            print('No se ha seleccionado un cliente para el carrito.')
            return redirect(url_for('ver_carrito'))

        # Obtener el carrito del usuario actual
        cursor.execute("""
            SELECT ID_Carrito
            FROM Carrito
            WHERE ID_Empleado = %s AND DATE(Fecha_Creacion) = DATE(NOW())
        """, (current_user.id,))
        carrito = cursor.fetchone()

        if not carrito:
            print('No hay carrito disponible para procesar.')
            return redirect(url_for('ver_carrito'))

        id_carrito = carrito[0]

        # Crear una nueva venta
        id_venta = str(uuid4())
        fecha = datetime.now().date()
        cursor.execute("""
            INSERT INTO Venta (ID_Venta, ID_Cliente, ID_Empleado, Fecha, Estado)
            VALUES (%s, %s, %s, %s, 'Pendiente')
        """, (id_venta, id_cliente, current_user.id, fecha))

        # Obtener los detalles del carrito
        cursor.execute("""
            SELECT ID_Producto, Cantidad
            FROM Detalle_Carrito
            WHERE ID_Carrito = %s
        """, (id_carrito,))
        detalles_carrito = cursor.fetchall()
        
        total_venta = 0
        for producto_id, cantidad in detalles_carrito:
            cursor.execute("""
                INSERT INTO Detalle_Venta (ID_Detalle_Venta, ID_Producto, ID_Venta, Cantidad_Venta)
                VALUES (%s, %s, %s, %s)
            """, (str(uuid4()), producto_id, id_venta, cantidad))
            
            # Obtener el precio del producto
            cursor.execute("""
                SELECT Precio_Venta
                FROM Producto
                WHERE ID_Producto = %s
            """, (producto_id,))
            precio = cursor.fetchone()
            if precio is None:
                raise ValueError(f"El precio del producto con ID {producto_id} no se encuentra en la base de datos.")
            precio = precio[0]
            total_venta += precio * cantidad
            
            # Actualizar el stock del producto restando la cantidad vendida
            cursor.execute("""
                UPDATE Producto
                SET Stock = Stock - %s
                WHERE ID_Producto = %s
            """, (cantidad, producto_id))

        # Vaciar el carrito
        cursor.execute("DELETE FROM Detalle_Carrito WHERE ID_Carrito = %s", (id_carrito,))
        cursor.execute("DELETE FROM Carrito WHERE ID_Carrito = %s", (id_carrito,))
        
        # Confirmar transacciones
        conexion.connection.commit()
        cursor.close()
        print(f"id_cliente: {id_cliente}, id_venta: {id_venta}")
        
        # Limpiar ID_Cliente de la sesión
        session.pop('id_cliente', None)
        print("Redirigiendo a ver_detalles_venta")
        
        # Redirigir a la página de detalles de la venta
        return redirect(url_for('ver_detalles_venta', id_cliente=id_cliente, venta_id=id_venta) + '?compra_realizada=true' )

    except Exception as e:
        print(f'Ocurrió un error al procesar la compra: {e}')
        conexion.connection.rollback()
        return redirect(url_for('ver_carrito'))



@app.route('/ver_clientes')
@login_required
def ver_clientes():
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("SELECT * FROM Cliente WHERE Estado = 'Activo'")
        clientes = cursor.fetchall()
        cursor.close()
        return render_template('clientes/ver_clientes.html', clientes=clientes)
    except Exception as e:
        flash('Error al cargar los clientes: {}'.format(e))
        return redirect(url_for('dashboard_menu'))
    
    
@app.route('/ver_ventas_cliente/<id_cliente>')
@login_required
def ver_ventas_cliente(id_cliente):
    try:
        cursor = conexion.connection.cursor()
        
        # Obtener el nombre completo del cliente
        cursor.execute("SELECT Nombre_Cliente, Apellido_Cliente FROM Cliente WHERE ID_Cliente = %s", (id_cliente,))
        cliente = cursor.fetchone()
        cliente_nombre = f"{cliente[0]} {cliente[1]}" if cliente else "Desconocido"
        
        # Obtener las ventas del cliente, ordenadas por fecha (más recientes primero)
        cursor.execute("""
            SELECT v.ID_Venta, v.Fecha, v.Estado, SUM(dv.Cantidad_Venta * p.Precio_Venta) AS Total
            FROM Venta v
            JOIN Detalle_Venta dv ON v.ID_Venta = dv.ID_Venta
            JOIN Producto p ON dv.ID_Producto = p.ID_Producto
            WHERE v.ID_Cliente = %s
            GROUP BY v.ID_Venta, v.Fecha, v.Estado
            ORDER BY v.Fecha ASC
        """, (id_cliente,))
        ventas = cursor.fetchall()
        #print(ventas)
        cursor.close()
        
        return render_template('clientes/ver_ventas_cliente.html', ventas=ventas, cliente_nombre=cliente_nombre, id_cliente=id_cliente)
    except Exception as e:
        print(f'Error al cargar las ventas del cliente: {e}')
        return redirect(url_for('ver_clientes'))


@app.route('/ver_detalles_venta/<id_cliente>/<venta_id>')
@login_required
def ver_detalles_venta(id_cliente,venta_id):
    try:
        cursor = conexion.connection.cursor()
        
        # Obtener información básica de la venta y del cliente
        cursor.execute('''
            SELECT v.ID_Venta, v.Fecha, v.Estado, SUM(dv.Cantidad_Venta * p.Precio_Venta) AS Total, CONCAT(c.Nombre_Cliente, ' ', c.Apellido_Cliente) AS Nombre_Cliente, v.ID_Cliente
            FROM Venta v
            JOIN Detalle_Venta dv ON v.ID_Venta = dv.ID_Venta
            JOIN Producto p ON dv.ID_Producto = p.ID_Producto
            JOIN Cliente c ON v.ID_Cliente = c.ID_Cliente
            WHERE v.ID_Venta = %s
            GROUP BY v.ID_Venta, v.Fecha, v.Estado, Nombre_Cliente, v.ID_Cliente
        ''', (venta_id,))
        venta = cursor.fetchone()
        print(venta)
        # Obtener detalles de los productos en la venta
        cursor.execute('''
            SELECT p.Nombre_Producto, dv.Cantidad_Venta, p.Precio_Venta, (dv.Cantidad_Venta * p.Precio_Venta) AS Total
            FROM Detalle_Venta dv
            JOIN Producto p ON dv.ID_Producto = p.ID_Producto
            WHERE dv.ID_Venta = %s
        ''', (venta_id,))
        detalles = cursor.fetchall()
        print(detalles)
        cursor.close()

        return render_template('clientes/ver_detalles_venta.html', venta=venta, detalles=detalles)
    except Exception as e:
        flash('Error al cargar los detalles de la venta: {}'.format(e))
        return redirect(url_for('ver_ventas_cliente', id_cliente=id_cliente))

@app.route('/generar_boleta/<venta_id>', methods=['GET'])
@login_required
def generar_boleta_pdf(venta_id):
    try:
        cursor = conexion.connection.cursor()
        
        # Obtener información básica de la venta y del cliente
        cursor.execute('''
            SELECT v.ID_Venta, v.Fecha, v.Estado, SUM(dv.Cantidad_Venta * p.Precio_Venta) AS Total,
                   CONCAT(c.Nombre_Cliente, ' ', c.Apellido_Cliente) AS Nombre_Cliente, c.DNI_Cliente, v.ID_Cliente
            FROM Venta v
            JOIN Detalle_Venta dv ON v.ID_Venta = dv.ID_Venta
            JOIN Producto p ON dv.ID_Producto = p.ID_Producto
            JOIN Cliente c ON v.ID_Cliente = c.ID_Cliente
            WHERE v.ID_Venta = %s
            GROUP BY v.ID_Venta, v.Fecha, v.Estado, Nombre_Cliente, c.DNI_Cliente, v.ID_Cliente
        ''', (venta_id,))
        venta = cursor.fetchone()
        
        # Obtener detalles de los productos en la venta
        cursor.execute('''
            SELECT p.Nombre_Producto, dv.Cantidad_Venta, p.Precio_Venta, (dv.Cantidad_Venta * p.Precio_Venta) AS Total
            FROM Detalle_Venta dv
            JOIN Producto p ON dv.ID_Producto = p.ID_Producto
            WHERE dv.ID_Venta = %s
        ''', (venta_id,))
        detalles = cursor.fetchall()
        
        cursor.close()

        # Procesar el número de boleta (formato de letras-letras-letras)
        boleta_numero = str(venta[0])[:8].upper()   # Toma los primeros cuatro caracteres

        # Renderizar la plantilla HTML
        rendered_html = render_template('boleta/boleta.html', 
                                        venta_id=venta[0], 
                                        fecha_emision=venta[1],
                                        cliente_nombre=venta[4],
                                        cliente_dni=venta[5],
                                        tipo_moneda="Soles",  # Asumimos "Soles", modificar según sea necesario
                                        observacion="Sin observaciones",  # Asumimos "Sin observaciones"
                                        items=[{'cantidad': d[1], 'unidad_medida': 'Unidad', 'codigo': '12345', 'descripcion': d[0], 'valor_unitario': d[2], 'descuento': 0, 'importe_venta': d[3]} for d in detalles],
                                        importe_total=venta[3],
                                        boleta_serie=boleta_numero)  # Añadir el número de boleta al contexto

        # Generar el PDF desde el HTML renderizado
        pdf = pdfkit.from_string(rendered_html, False, configuration=PDFKIT_CONFIG)

        # Preparar el archivo PDF para enviar como respuesta
        response = BytesIO(pdf)
        response.seek(0)

        return send_file(response, as_attachment=True, download_name=f'boleta_{venta_id}.pdf', mimetype='application/pdf')

    except Exception as e:
        flash(f"Error al generar la boleta: {str(e)}", "error")
        return redirect(url_for('ver_detalles_venta', venta_id=venta_id))



    

@app.route('/ver_proveedores')
@login_required
def ver_proveedores():
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("""
            SELECT RUC, Nombre_Proveedor, Apellido_Proveedor, Telefono_Proveedor, Email, Direccion, ID_Proveedor
            FROM Proveedor
            WHERE Estado = 'Activo'
        """)
        proveedores_data = cursor.fetchall()
        cursor.close()
        
        # Convertir la tupla de tuplas en una lista de diccionarios
        proveedores = [
            {
                'RUC': proveedor[0],
                'Nombre_Proveedor': proveedor[1],
                'Apellido_Proveedor': proveedor[2],
                'Telefono_Proveedor': proveedor[3],
                'Email': proveedor[4],
                'Direccion': proveedor[5],
                'ID_Proveedor' : proveedor[6],
            }
            for proveedor in proveedores_data
        ]
        
        return render_template('proveedores/ver_proveedores.html', proveedores=proveedores)
    except Exception as e:
        flash('Error al cargar los proveedores: {}'.format(e))
        return redirect(url_for('dashboard_menu'))

@app.route('/agregar_proveedor', methods=['GET', 'POST'])
@login_required
def agregar_proveedor():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        telefono = request.form.get('telefono')
        ruc = request.form.get('ruc')
        email = request.form.get('email')
        direccion = request.form.get('direccion')
        
        try:
            cursor = conexion.connection.cursor()
            cursor.execute("""
                INSERT INTO Proveedor (ID_Proveedor, Nombre_Proveedor, Apellido_Proveedor, Telefono_Proveedor, RUC, Email, Direccion, Estado)
                VALUES (UUID(), %s, %s, %s, %s, %s, %s, 'Activo')
            """, (nombre, apellido, telefono, ruc, email, direccion))
            conexion.connection.commit()
            cursor.close()
            
            flash('Proveedor agregado exitosamente.')
            return redirect(url_for('ver_proveedores'))
        except Exception as e:
            flash('Error al agregar el proveedor: {}'.format(e))
            return redirect(url_for('ver_proveedores'))
    
    return render_template('proveedores/ver_proveedores.html')

@app.route('/cambiar_estado_proveedor/<id_proveedor>')
@login_required
def cambiar_estado_proveedor(id_proveedor):
    try:
        cursor = conexion.connection.cursor()
        print(id_proveedor)
        # Cambiar el estado del proveedor de Activo a Inactivo o viceversa
        cursor.execute("""
            UPDATE Proveedor
            SET Estado = CASE
                WHEN Estado = 'Activo' THEN 'Inactivo'
                ELSE 'Activo'
            END
            WHERE ID_Proveedor = %s
        """, (id_proveedor,))
        conexion.connection.commit()
        cursor.close()
        flash('Estado del proveedor actualizado correctamente.')
    except Exception as e:
        flash('Error al actualizar el estado del proveedor: {}'.format(e))
    
    return redirect(url_for('ver_proveedores'))



@app.route('/ver_empleados')
@login_required
def ver_empleados():
    try:
        id_empleado_actual = current_user.id
        cursor = conexion.connection.cursor()
        cursor.execute("""
            SELECT DNI_Empleado, Nombres_Empleado, Apellidos_Empleado, Telefono_Empleado, Email, Direccion, ID_Empleado
            FROM Empleado
            WHERE Estado = 'Activo'
        """)
        empleados = cursor.fetchall()
        cursor.close()
        return render_template('empleados/ver_empleados.html', empleados=empleados,id_empleado_actual=id_empleado_actual )
    except Exception as e:
        flash('Error al cargar los empleados: {}'.format(e))
        return redirect(url_for('index'))

@app.route('/agregar_empleado', methods=['POST'])
@login_required
def agregar_empleado():
    try:
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        telefono = request.form['telefono']
        dni = request.form['dni']
        email = request.form['email']
        direccion = request.form['direccion']
        contraseña = request.form['contraseña']
        
        cursor = conexion.connection.cursor()
        cursor.execute("""
            INSERT INTO Empleado (ID_Empleado, Nombres_Empleado, Apellidos_Empleado, Telefono_Empleado, DNI_Empleado, Email, Direccion, Contraseña, Estado, Rol)
            VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s, 'Activo', 'Normal')
        """, (nombre, apellido, telefono, dni, email, direccion, contraseña))
        conexion.connection.commit()
        cursor.close()
        flash('Empleado agregado correctamente.')
    except Exception as e:
        flash('Error al agregar el empleado: {}'.format(e))
    
    return redirect(url_for('ver_empleados'))

@app.route('/cambiar_estado_empleado/<id_empleado>')
@login_required
def cambiar_estado_empleado(id_empleado):
    try:
        cursor = conexion.connection.cursor()
        cursor.execute("""
            UPDATE Empleado
            SET Estado = CASE
                WHEN Estado = 'Activo' THEN 'Inactivo'
                ELSE 'Activo'
            END
            WHERE ID_Empleado = %s
        """, (id_empleado,))
        conexion.connection.commit()
        cursor.close()
        flash('Estado del empleado actualizado correctamente.')
    except Exception as e:
        flash('Error al actualizar el estado del empleado: {}'.format(e))
    
    return redirect(url_for('ver_empleados'))



if __name__=='__main__':
    app.run(debug=True,port=5000)