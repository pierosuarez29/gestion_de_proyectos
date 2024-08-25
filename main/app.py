#debug mode

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_mysqldb import MySQL
from uuid import uuid4
from datetime import datetime



app = Flask(__name__)

# Configuración de la clave secreta
app.config['SECRET_KEY'] = 'mi_clave_secreta_123'  # Cambia esto a una clave secreta única y segura

#conexion MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '2911'#'1608'#1405
app.config['MYSQL_DB'] = 'gestion_de_proyectos'

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
    filtros = request.args.getlist('filter')  # Filtros seleccionados
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
        
        # Agregar condiciones de búsqueda
        if search:
            query += " AND (p.Nombre_Producto LIKE %s OR p.Tipo LIKE %s OR m.Nombre_Marca LIKE %s)"
            params += [f'%{search}%'] * 3
        
        # Agregar condiciones de filtro
        if filtros:
            marcas_filtros = [f for f in filtros if f in marcas]
            tipos_filtros = [f for f in filtros if f in tipos]

            if marcas_filtros:
                query += " AND m.Nombre_Marca IN (" + ", ".join(["%s"] * len(marcas_filtros)) + ")"
                params.extend(marcas_filtros)
                
            if tipos_filtros:
                query += " AND p.Tipo IN (" + ", ".join(["%s"] * len(tipos_filtros)) + ")"
                params.extend(tipos_filtros)

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
            return render_template('productos/ver_productos.html', productos=productos, marcas=marcas, tipos=tipos, selected_filters=filtros)
    except Exception as e:
        flash('Error al cargar los productos: {}'.format(e))
        return redirect(url_for('dashboard_menu'))

@app.route('/agregar_al_carrito', methods=['POST'])
@login_required
def agregar_al_carrito():
    id_producto = request.form.get('id_producto')
    cantidad = int(request.form.get('cantidad'))

    try:
        cursor = conexion.connection.cursor()

        # Verificar si ya existe un carrito para el usuario actual
        cursor.execute("SELECT ID_Carrito FROM Carrito WHERE ID_Empleado = %s AND DATE(Fecha_Creacion) = DATE(NOW())", (current_user.id,))
        carrito = cursor.fetchone()

        if carrito:
            id_carrito = carrito[0]
        else:
            id_carrito = str(uuid4())
            cursor.execute("INSERT INTO Carrito (ID_Carrito, ID_Empleado, Fecha_Creacion) VALUES (%s, %s, %s)",
                           (id_carrito, current_user.id, datetime.now()))
        
        # Verificar si el producto ya está en el carrito
        cursor.execute("SELECT ID_Detalle_Carrito FROM Detalle_Carrito WHERE ID_Carrito = %s AND ID_Producto = %s", (id_carrito, id_producto))
        detalle = cursor.fetchone()

        if detalle:
            # Actualizar cantidad
            cursor.execute("UPDATE Detalle_Carrito SET Cantidad = Cantidad + %s WHERE ID_Detalle_Carrito = %s",
                        (cantidad, detalle[0]))
        else:
            # Insertar nuevo detalle
            id_detalle_carrito = str(uuid4())
            cursor.execute("INSERT INTO Detalle_Carrito (ID_Detalle_Carrito, ID_Carrito, ID_Producto, Cantidad) VALUES (%s, %s, %s, %s)",
                        (id_detalle_carrito, id_carrito, id_producto, cantidad))
        
        conexion.connection.commit()
        cursor.close()
        flash('Producto agregado al carrito exitosamente.')
        return redirect(url_for('ver_productos'))
    except Exception as e:
        flash('Error al agregar el producto al carrito: {}'.format(e))
        return redirect(url_for('ver_productos'))


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
            return redirect(url_for('ver_productos') + '?no_hay=true')
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
        print("ID_CLIENTE: ",id_cliente)
        if not id_cliente:
            flash('No se ha seleccionado un cliente para el carrito.')
            return redirect(url_for('ver_carrito'))

        # Obtener el carrito del usuario actual
        cursor.execute("""
            SELECT ID_Carrito
            FROM Carrito
            WHERE ID_Empleado = %s AND DATE(Fecha_Creacion) = DATE(NOW())
        """, (current_user.id,))
        carrito = cursor.fetchone()

        #if not carrito:
        #    flash('No hay carrito para procesar.')
        #    return redirect(url_for('ver_productos'))

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

        #if not detalles_carrito:
        #    flash('El carrito está vacío. No se puede procesar la compra.')
        #    return redirect(url_for('ver_carrito'))

        for producto_id, cantidad in detalles_carrito:
            cursor.execute("""
                INSERT INTO Detalle_Venta (ID_Detalle_Venta, ID_Producto, ID_Venta, Cantidad_Venta)
                VALUES (%s, %s, %s, %s)
            """, (str(uuid4()), producto_id, id_venta, cantidad))
            
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

        # Limpiar ID_Cliente de la sesión
        session.pop('id_cliente', None)

        # Redirigir a la página de confirmación
        return redirect(url_for('ver_productos'))

    except Exception as e:
        # Imprimir el error en la consola para depuración
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
        
        # Obtener las ventas del cliente
        cursor.execute("""
            SELECT v.ID_Venta, v.Fecha, v.Estado, SUM(dv.Cantidad_Venta * p.Precio_Venta) AS Total
            FROM Venta v
            JOIN Detalle_Venta dv ON v.ID_Venta = dv.ID_Venta
            JOIN Producto p ON dv.ID_Producto = p.ID_Producto
            WHERE v.ID_Cliente = %s
            GROUP BY v.ID_Venta, v.Fecha, v.Estado
        """, (id_cliente,))
        ventas = cursor.fetchall()
        #print (ventas)
        cursor.close()
        
        return render_template('clientes/ver_ventas_cliente.html', ventas=ventas, cliente_nombre=cliente_nombre)
    except Exception as e:
        print('Error al cargar las ventas del cliente: {}'.format(e))
        return redirect(url_for('ver_clientes'))

@app.route('/ver_detalles_venta/<venta_id>')
@login_required
def ver_detalles_venta(venta_id):
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
        
        # Obtener detalles de los productos en la venta
        cursor.execute('''
            SELECT p.Nombre_Producto, dv.Cantidad_Venta, p.Precio_Venta, (dv.Cantidad_Venta * p.Precio_Venta) AS Total
            FROM Detalle_Venta dv
            JOIN Producto p ON dv.ID_Producto = p.ID_Producto
            WHERE dv.ID_Venta = %s
        ''', (venta_id,))
        detalles = cursor.fetchall()
        
        cursor.close()

        return render_template('clientes/ver_detalles_venta.html', venta=venta, detalles=detalles)
    except Exception as e:
        flash('Error al cargar los detalles de la venta: {}'.format(e))
        return redirect(url_for('ver_ventas_cliente', id_cliente=current_user.id))



    

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
        cursor = conexion.connection.cursor()
        cursor.execute("""
            SELECT DNI_Empleado, Nombres_Empleado, Apellidos_Empleado, Telefono_Empleado, Email, Direccion, ID_Empleado
            FROM Empleado
            WHERE Estado = 'Activo'
        """)
        empleados = cursor.fetchall()
        cursor.close()
        return render_template('empleados/ver_empleados.html', empleados=empleados)
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