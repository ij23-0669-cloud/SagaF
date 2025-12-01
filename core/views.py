from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta
from .forms import ProductoForm, UsuarioForm, LoginForm
from .models import *
from django.views.decorators.http import require_http_methods
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
import logging
import random
from datetime import datetime
import json
from django.views.decorators.http import require_POST
from .models import Usuario, Producto, Carrito, CarritoDetalle, EstadoCarrito, Etiqueta
import stripe
from django.conf import settings
from .models import MetodoPagoUsuario
from django.views.decorators.http import require_GET
from django.contrib.auth.hashers import check_password, make_password


logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Página principal
def index(request):
    return render(request, 'core/index.html')

# Crear cuenta — con asignación automática de rol
def crear_cuenta(request):
    ADMIN_EMAIL = "adminsaga2529@gmail.com"
    ADMIN_PASSWORD = "admin1234"
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            correo = form.cleaned_data.get('correo', '')
            contraseña_raw = form.cleaned_data.get('contraseña', '')
            
            # Hasear contraseña
            user.contraseña = make_password(contraseña_raw)
            
            # Estado por defecto: activo
            user.estado = 'activo'
            
            # Asignar rol automáticamente
            if correo == ADMIN_EMAIL and contraseña_raw == ADMIN_PASSWORD:
                # Es administrador
                rol_admin = Rol.objects.filter(nombre__iexact='admin').first()
                if not rol_admin:
                    rol_admin = Rol.objects.filter(nombre__iexact='administrador').first()
                if rol_admin:
                    user.rol = rol_admin
                else:
                    messages.error(request, "Rol administrador no existe en BD. Contacta con soporte.")
                    return render(request, 'core/crearCuenta.html', {'form': form})
                messages.success(request, "Cuenta administrador creada correctamente.")
            else:
                # Es usuario normal
                rol_usuario = Rol.objects.filter(nombre__iexact='usuario').first()
                if not rol_usuario:
                    rol_usuario = Rol.objects.filter(nombre__iexact='client').first()
                if rol_usuario:
                    user.rol = rol_usuario
                else:
                    messages.error(request, "Rol usuario no existe en BD. Contacta con soporte.")
                    return render(request, 'core/crearCuenta.html', {'form': form})
                messages.success(request, "Cuenta creada correctamente. Ya puedes iniciar sesión.")
            
            try:
                user.save()
                return redirect('login')
            except Exception as e:
                messages.error(request, f"Error al guardar el usuario: {str(e)}")
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = UsuarioForm()

    return render(request, 'core/crearCuenta.html', {'form': form})

# Login — con verificación de inactividad
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            usuario_o_correo = form.cleaned_data.get('usuario_o_correo', '')
            contraseña_input = form.cleaned_data.get('contraseña', '')
            
            try:
                # Buscar por usuario o correo
                user = Usuario.objects.filter(usuario=usuario_o_correo).first() or Usuario.objects.filter(correo=usuario_o_correo).first()
                
                if not user:
                    messages.error(request, "Usuario o correo no existe.")
                    return render(request, 'core/login.html', {'form': form})
                
                # Verificar inactividad (3 meses = 90 días)
                ahora = timezone.now().date()
                fecha_mod = user.fecha_modificacion
                dias_inactivo = (ahora - fecha_mod).days
                
                if dias_inactivo > 90:
                    user.estado = 'inactivo'
                    user.save()
                    messages.error(request, "Tu cuenta ha sido desactivada por inactividad. Contacta con soporte.")
                    return render(request, 'core/login.html', {'form': form})
                
                # Verificar estado
                if user.estado != 'activo':
                    messages.error(request, "Tu cuenta no está activa.")
                    return render(request, 'core/login.html', {'form': form})
                
                # Verificar contraseña (comparar hasheada)
                if check_password(contraseña_input, user.contraseña):
                    # Login exitoso — actualizar fecha_modificacion
                    user.fecha_modificacion = ahora
                    user.save()
                    
                    # Guardar en sesión
                    request.session['user_id'] = user.id_usuario
                    request.session['user_username'] = user.usuario
                    request.session['user_rol'] = user.rol.nombre if user.rol else 'usuario'
                    request.session['usuario_nombre'] = user.nombre
                    
                    messages.success(request, f"¡Bienvenido {user.usuario}!")
                    
                    # Normalizar rol para redirección
                    role_name = 'usuario'
                    if hasattr(user, 'rol') and user.rol:
                        role_name = user.rol.nombre if hasattr(user.rol, 'nombre') else str(user.rol)
                    role_name = (role_name or 'usuario').strip().lower()
                    
                    # Redirigir según rol
                    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
                    if role_name in admin_aliases:
                        return redirect('panel_admin')
                    return redirect('index')
                else:
                    messages.error(request, "Contraseña incorrecta.")
            except Exception as e:
                messages.error(request, f"Error al iniciar sesión: {str(e)}")
        else:
            messages.error(request, "Por favor completa todos los campos.")
    else:
        form = LoginForm()
    
    return render(request, 'core/login.html', {'form': form})



# Logout
def logout_view(request):
    request.session.flush()
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect('index')

# Perfil del usuario (usuario normal)
def perfil_usuario(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    
    # Obtener choices del campo 'pais'
    try:
        country_field = Usuario._meta.get_field('pais')
        country_choices = getattr(country_field, 'choices', None) or []
    except Exception:
        country_choices = []

    # Leer el tab desde la URL ?tab=...
    active_tab = request.GET.get('tab', 'personal')

    # Tabs válidos (los que usa switchTab())
    valid_tabs = {'personal', 'payment', 'security', 'history'}

    if active_tab not in valid_tabs:
        active_tab = 'personal'

    context = {
        'user': usuario,
        'country_choices': country_choices,
        'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        'active_tab': active_tab,
    }
    return render(request, 'core/perfilDeUsuario.html', context)



# Perfil del cliente (cliente propio)
def perfil_cliente(request, cliente_id):
    """Muestra el perfil detallado de un cliente - solo para admins."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()
    
    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases:
        messages.error(request, "No tienes acceso a esta página.")
        return redirect('index')
    
    # Obtener el cliente
    cliente = get_object_or_404(Usuario, id_usuario=cliente_id)
    
    # Verificar que no sea admin
    cliente_role = (cliente.rol.nombre if hasattr(cliente, 'rol') and cliente.rol else 'usuario').strip().lower()
    if cliente_role in admin_aliases:
        messages.error(request, "No puedes ver el perfil de un administrador.")
        return redirect('listado_clientes')
    
    # Obtener información del cliente
    facturas = Factura.objects.filter(usuario=cliente, estado='Completado').order_by('-fecha')
    num_compras = facturas.count()
    total_gasto = facturas.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')
    
    # Número de transacciones (cada factura puede tener múltiples productos)
    num_transacciones = Transaccion.objects.filter(factura__usuario=cliente, estado='Exitosa').count()
    
    # Cliente frecuente (3 o más compras)
    es_frecuente = num_compras >= 3
    
    # Fecha de registro
    fecha_registro = cliente.fecha_registro.strftime('%d/%m/%Y') if cliente.fecha_registro else 'N/A'
    
    # Método de pago principal
    metodo_principal = MetodoPagoUsuario.objects.filter(usuario=cliente, es_principal=True).first()
    
    # Historial de compras detallado
    historial = []
    for factura in facturas:
        detalles = DetalleFactura.objects.filter(factura=factura).select_related('producto')
        productos_comprados = [
            {
                'nombre': detalle.producto.nombre,
                'plataforma': detalle.producto.plataforma or 'N/A',
                'cantidad': detalle.cantidad,
                'precio': detalle.precio_venta_unitario,
                'subtotal': detalle.subtotal
            }
            for detalle in detalles
        ]
        
        historial.append({
            'id': factura.id_factura,
            'fecha': factura.fecha.strftime('%d/%m/%Y'),
            'total': factura.total,
            'productos': productos_comprados
        })
    
    context = {
        'cliente': cliente,
        'num_compras': num_compras,
        'num_transacciones': num_transacciones,
        'total_gasto': total_gasto,
        'metodo_principal': metodo_principal,
        'historial': historial,
        'es_frecuente': es_frecuente,
        'fecha_registro': fecha_registro
    }
    
    return render(request, 'core/perfilCliente.html', context)

# Añadir juegos
def anadir_juegos(request):
    """
    Vista para añadir/gestionar juegos. Usa la sesión personalizada (user_id / user_rol)
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    usuario_session = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()

    role_name = 'usuario'
    if hasattr(usuario_session, 'rol') and usuario_session.rol:
        role_name = usuario_session.rol.nombre if hasattr(usuario_session.rol, 'nombre') else str(usuario_session.rol)
    role_name = (role_name or 'usuario').strip().lower()

    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases and role_name not in admin_aliases:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('index')

    # MANEJO DE ACTUALIZACIÓN DE STOCK
    if request.method == 'POST' and request.POST.get('action') == 'update_stock':
        producto_id = request.POST.get('producto_id')
        stock_change = int(request.POST.get('stock_change', 0))
        
        producto = get_object_or_404(Producto, id_producto=producto_id)
        nuevo_stock = producto.stock + stock_change
        
        if nuevo_stock < 0:
            messages.error(request, f"No se puede reducir el stock de '{producto.nombre}' por debajo de 0.")
        else:
            producto.stock = nuevo_stock
            producto.save()
            
            # Generar claves si aumentó el stock
            if stock_change > 0:
                estado_disponible, _ = EstadoClave.objects.get_or_create(nombre='Disponible')
                for _ in range(stock_change):
                    ClaveJuego.objects.create(producto=producto, estado_clave=estado_disponible)
                messages.success(request, f"Stock de '{producto.nombre}' actualizado a {nuevo_stock}. Se generaron {stock_change} claves nuevas.")
            else:
                messages.success(request, f"Stock de '{producto.nombre}' actualizado a {nuevo_stock}.")
        
        return redirect('anadir_juegos')

    # MANEJO DE ACTUALIZACIÓN DE ETIQUETAS
    if request.method == 'POST' and request.POST.get('action') == 'update_etiquetas':
        producto_id = request.POST.get('producto_id')
        producto = get_object_or_404(Producto, id_producto=producto_id)
        
        etiqueta_ids = request.POST.getlist('etiqueta_id')
        producto.etiquetas.clear()
        
        for etiqueta_id in etiqueta_ids:
            try:
                etiqueta = Etiqueta.objects.get(id_etiqueta=etiqueta_id)
                producto.etiquetas.add(etiqueta)
            except Etiqueta.DoesNotExist:
                pass
        
        messages.success(request, f"Etiquetas de '{producto.nombre}' actualizadas correctamente.")
        return redirect('anadir_juegos')

    # LÓGICA ORIGINAL DE AÑADIR PRODUCTO
    if request.method == 'POST' and not request.POST.get('action'):
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save(commit=False)
            codigo_enviado = request.POST.get('codigo_producto') or ''
            if codigo_enviado:
                producto.codigo_producto = codigo_enviado
            if not getattr(producto, 'codigo_producto', None):
                d = datetime.now()
                datePart = str(d.year)[2:] + str(d.month).zfill(2) + str(d.day).zfill(2)
                producto.codigo_producto = 'GAME' + datePart + str(random.randint(1000, 9999))
            producto.save()
            
            # Generar claves según el stock inicial
            if producto.stock > 0:
                estado_disponible, _ = EstadoClave.objects.get_or_create(nombre='Disponible')
                for _ in range(producto.stock):
                    ClaveJuego.objects.create(producto=producto, estado_clave=estado_disponible)
            
            messages.success(request, f'¡Producto "{producto.nombre}" añadido con éxito!')
            return redirect('anadir_juegos')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{field}: {err}')
    else:
        form = ProductoForm()

    productos = Producto.objects.all().order_by('-id_producto')
    etiquetas = Etiqueta.objects.all()

    return render(request, 'core/añadirJuegos.html', {
        'form': form,
        'productos': productos,
        'etiquetas': etiquetas
    })

def eliminar_producto(request, id_producto):
    """
    Eliminar producto — accesible solo por admin (misma comprobación de sesión/rol).
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    usuario_session = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()
    role_name = 'usuario'
    if hasattr(usuario_session, 'rol') and usuario_session.rol:
        role_name = usuario_session.rol.nombre if hasattr(usuario_session.rol, 'nombre') else str(usuario_session.rol)
    role_name = (role_name or 'usuario').strip().lower()

    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases and role_name not in admin_aliases:
        messages.error(request, "No tienes permisos para eliminar productos.")
        return redirect('index')

    producto = get_object_or_404(Producto, id_producto=id_producto)
    nombre = producto.nombre
    producto.delete()
    messages.success(request, f'Producto "{nombre}" eliminado correctamente.')
    return redirect('anadir_juegos')

# Página de pago
def pago(request):
    return render(request, 'core/pago.html')

# Factura individual
def factura(request):
    return render(request, 'core/factura.html')

# Reporte de facturas (lista)
def reporte_factura(request):
    """Reporte detallado de facturas - solo para admins."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()
    
    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases:
        messages.error(request, "No tienes acceso a esta página.")
        return redirect('index')
    
    # Obtener todas las facturas con sus detalles
    facturas = Factura.objects.select_related('usuario').prefetch_related(
        'detallefactura_set__producto',
        'transaccion_set'
    ).order_by('-fecha')
    
    # Preparar datos para el template
    facturas_data = []
    for factura in facturas:
        # Obtener el primer producto (producto clave) de la factura
        primer_detalle = factura.detallefactura_set.first()
        producto_clave = primer_detalle.producto.nombre if primer_detalle else 'N/A'
        
        # Obtener la transacción asociada
        transaccion = factura.transaccion_set.first()
        transaccion_id = f"TXN-{transaccion.id_transaccion}" if transaccion else 'N/A'
        
        # Calcular subtotal (antes de impuestos - asumiendo 0% de impuesto)
        subtotal = factura.total
        impuesto = Decimal('0.00')  # Si tienes impuestos, calcúlalos aquí
        
        facturas_data.append({
            'id': f"SAGA-{factura.id_factura}",
            'fecha': factura.fecha.strftime('%Y-%m-%d'),
            'cliente': f"{factura.usuario.nombre} {factura.usuario.apellido}",
            'producto': producto_clave,
            'subtotal': float(subtotal),
            'impuesto': float(impuesto),
            'total': float(factura.total),
            'estado': factura.estado,
            'transaccion_id': transaccion_id
        })
    
    context = {
        'facturas_json': json.dumps(facturas_data)
    }
    
    return render(request, 'core/reporteDeFactura.html', context)

# Reporte de ventas
def reporte_ventas(request):
    """Reporte de juegos vendidos - solo para admins."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()
    
    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases:
        messages.error(request, "No tienes acceso a esta página.")
        return redirect('index')
    
    # Obtener todos los detalles de facturas completadas
    detalles = DetalleFactura.objects.filter(
        factura__estado='Completado'
    ).select_related('producto', 'producto__id_categoria').values(
        'producto__id_producto',
        'producto__nombre',
        'producto__id_categoria__nombre',
        'producto__plataforma',
        'precio_venta_unitario'
    ).annotate(
        cantidad_vendida=models.Sum('cantidad'),
        ventas_totales=models.Sum('subtotal')
    ).order_by('-ventas_totales')
    
    # Calcular total global
    total_global = sum(item['ventas_totales'] for item in detalles) if detalles else Decimal('0.00')
    
    # Preparar datos para el template
    ventas_data = []
    for detalle in detalles:
        porcentaje = (float(detalle['ventas_totales']) / float(total_global) * 100) if total_global > 0 else 0
        
        ventas_data.append({
            'id': f"GAME-{detalle['producto__id_producto']}",
            'gameName': detalle['producto__nombre'],
            'genre': detalle['producto__id_categoria__nombre'] or 'N/A',
            'platform': detalle['producto__plataforma'] or 'N/A',
            'unitPrice': float(detalle['precio_venta_unitario']),
            'quantity': detalle['cantidad_vendida'],
            'totalSales': float(detalle['ventas_totales']),
            'percentage': round(porcentaje, 2)
        })
    
    # Obtener periodo (primera y última factura)
    primera_factura = Factura.objects.filter(estado='Completado').order_by('fecha').first()
    ultima_factura = Factura.objects.filter(estado='Completado').order_by('-fecha').first()
    
    fecha_inicio = primera_factura.fecha.strftime('%d/%m/%Y') if primera_factura else 'N/A'
    fecha_fin = ultima_factura.fecha.strftime('%d/%m/%Y') if ultima_factura else 'N/A'
    
    context = {
        'ventas_json': json.dumps(ventas_data),
        'total_global': float(total_global),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }
    
    return render(request, 'core/reporteDeVentas.html', context)

# Listado de clientes
def listado_clientes(request):
    """Listado de clientes con estadísticas - solo para admins."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()
    
    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases:
        messages.error(request, "No tienes acceso a esta página.")
        return redirect('index')
    
    # Obtener SOLO usuarios que NO son administradores
    clientes = Usuario.objects.exclude(
        rol__nombre__in=['admin', 'administrador', 'administrator', 'superadmin', 'superuser']
    ).select_related('rol')
    
    # Calcular estadísticas por cliente
    clientes_data = []
    total_clientes = 0
    clientes_frecuentes = 0
    total_transacciones = 0
    total_gasto_global = Decimal('0.00')
    metodos_pago = {}
    mayor_gasto_cliente = None
    mayor_gasto_monto = Decimal('0.00')
    
    for cliente in clientes:
        # Obtener facturas completadas del cliente
        facturas = Factura.objects.filter(usuario=cliente, estado='Completado')
        num_compras = facturas.count()
        total_gasto = facturas.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')
        
        # Método de pago preferido (marca de la tarjeta principal)
        metodo_preferido = 'N/A'
        metodo_mas_usado = MetodoPagoUsuario.objects.filter(
            usuario=cliente,
            es_principal=True
        ).first()
        
        if metodo_mas_usado:
            metodo_preferido = metodo_mas_usado.marca or 'Tarjeta'
            metodos_pago[metodo_mas_usado.marca] = metodos_pago.get(metodo_mas_usado.marca, 0) + 1
        
        # Cliente frecuente (3 o más compras)
        es_frecuente = num_compras >= 3
        
        clientes_data.append({
            'id': cliente.id_usuario,
            'nombre': f"{cliente.nombre} {cliente.apellido}",
            'correo': cliente.correo,
            'pais': cliente.get_pais_display() if cliente.pais else 'N/A',
            'metodo_preferido': metodo_preferido,
            'total_compras': total_gasto,
            'num_compras': num_compras,
            'es_frecuente': es_frecuente
        })
        
        total_clientes += 1
        if es_frecuente:
            clientes_frecuentes += 1
        total_transacciones += num_compras
        total_gasto_global += total_gasto
        
        if total_gasto > mayor_gasto_monto:
            mayor_gasto_monto = total_gasto
            mayor_gasto_cliente = f"{cliente.nombre} {cliente.apellido}"
    
    # Estadísticas globales
    promedio_transacciones = (total_transacciones / total_clientes) if total_clientes > 0 else 0
    promedio_gasto = (total_gasto_global / total_clientes) if total_clientes > 0 else Decimal('0.00')
    
    # Método más usado
    metodo_mas_comun = 'N/A'
    metodo_porcentaje = 0
    if metodos_pago:
        metodo_mas_comun = max(metodos_pago, key=metodos_pago.get)
        metodo_porcentaje = int((metodos_pago[metodo_mas_comun] / sum(metodos_pago.values())) * 100)
    
    # Ordenar clientes por total de compras (descendente)
    clientes_data.sort(key=lambda x: x['total_compras'], reverse=True)
    
    # Periodo (primera y última factura)
    primera_factura = Factura.objects.filter(estado='Completado').order_by('fecha').first()
    ultima_factura = Factura.objects.filter(estado='Completado').order_by('-fecha').first()
    
    fecha_inicio = primera_factura.fecha.strftime('%d/%m/%Y') if primera_factura else 'N/A'
    fecha_fin = ultima_factura.fecha.strftime('%d/%m/%Y') if ultima_factura else 'N/A'
    
    context = {
        'clientes': clientes_data,
        'total_clientes': total_clientes,
        'clientes_frecuentes': clientes_frecuentes,
        'promedio_transacciones': round(promedio_transacciones, 1),
        'promedio_gasto': promedio_gasto,
        'metodo_mas_comun': f"{metodo_mas_comun} ({metodo_porcentaje}%)",
        'mayor_gasto_cliente': mayor_gasto_cliente or 'N/A',
        'mayor_gasto_monto': mayor_gasto_monto,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }
    
    return render(request, 'core/listadoClientes.html', context)

@require_http_methods(["POST"])
def actualizar_perfil(request):
    """Actualiza el perfil del usuario autenticado"""
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'No autenticado'}, status=401)
    
    try:
        user_id = request.session.get('user_id')
        user = Usuario.objects.get(id_usuario=user_id)
        
        # Obtener datos del POST
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        usuario = request.POST.get('usuario', '').strip()
        fecha_nacimiento_raw = request.POST.get('fecha_nacimiento', '').strip()
        pais = request.POST.get('pais', '').strip()
        
        # Validaciones
        if not nombre or not apellido or not usuario:
            return JsonResponse({
                'success': False,
                'message': 'Por favor, rellena al menos el Nombre, Apellido y Nombre de Usuario.'
            }, status=400)
        
        # Verificar si el nuevo usuario ya existe (si es diferente al actual)
        if usuario != user.usuario and Usuario.objects.filter(usuario=usuario).exists():
            return JsonResponse({
                'success': False,
                'message': 'El nombre de usuario ya existe.'
            }, status=400)
        
        # Parsear fecha si viene como string (YYYY-MM-DD)
        fecha_nacimiento_parsed = None
        if fecha_nacimiento_raw:
            fecha_nacimiento_parsed = parse_date(fecha_nacimiento_raw)
            if fecha_nacimiento_parsed is None:
                return JsonResponse({
                    'success': False,
                    'message': 'Formato de fecha inválido. Usa YYYY-MM-DD.'
                }, status=400)
        
        # Actualizar datos
        user.nombre = nombre
        user.apellido = apellido
        user.usuario = usuario
        if fecha_nacimiento_parsed:
            user.fecha_nacimiento = fecha_nacimiento_parsed
        # si no se envía fecha, mantenemos la existente
        user.pais = pais
        user.fecha_modificacion = timezone.now().date()
        user.save()
        
        # Actualizar sesión
        request.session['user_username'] = usuario
        request.session['usuario_nombre'] = user.nombre  # o usuario.usuario si prefieres el username
        request.session.modified = True
        
        # Preparar valor seguro para la respuesta JSON
        fecha_nac_val = ''
        if getattr(user, 'fecha_nacimiento', None):
            try:
                fecha_nac_val = user.fecha_nacimiento.isoformat()
            except Exception:
                fecha_nac_val = str(user.fecha_nacimiento)

        # Serializar país de forma segura (django-countries Country -> código + label)
        pais_label = ''
        pais_value = ''
        try:
            if hasattr(user, 'get_pais_display'):
                pais_label = user.get_pais_display()
            else:
                pais_label = str(user.pais) if user.pais is not None else ''
        except Exception:
            pais_label = str(user.pais) if user.pais is not None else ''

        try:
            if user.pais is None:
                pais_value = ''
            else:
                # user.pais puede ser un objeto Country; intentar obtener código o usar str()
                pais_value = getattr(user.pais, 'code', None) or str(user.pais)
        except Exception:
            pais_value = str(user.pais) if user.pais is not None else ''

        return JsonResponse({
            'success': True,
            'message': '¡Perfil actualizado con éxito!',
            'user': {
                'username': user.usuario,
                'nombre': user.nombre,
                'apellido': user.apellido,
                'email': user.correo,
                'fecha_nacimiento': fecha_nac_val,
                'pais': pais_label,
                'pais_value': pais_value
            }
        })
    
    except Usuario.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)

@login_required(login_url='login')
def actualizar_etiqueta(request, id_producto):
    """Actualiza las etiquetas de un producto (solo para admins)."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()
    
    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases:
        messages.error(request, "No tienes permisos para actualizar etiquetas.")
        return redirect('index')

    producto = get_object_or_404(Producto, id_producto=id_producto)
    
    # Obtener etiquetas seleccionadas del POST
    etiqueta_ids = request.POST.getlist('etiqueta_id')
    
    # Limpiar etiquetas previas
    producto.etiquetas.clear()
    
    # Añadir nuevas etiquetas
    for etiqueta_id in etiqueta_ids:
        try:
            etiqueta = Etiqueta.objects.get(id_etiqueta=etiqueta_id)
            producto.etiquetas.add(etiqueta)
        except Etiqueta.DoesNotExist:
            pass
    
    messages.success(request, f"Etiquetas de '{producto.nombre}' actualizadas correctamente.")
    return redirect('anadir_juegos')

@require_http_methods(['GET'])
def api_productos(request):
    """Retorna todos los productos con sus etiquetas en formato JSON"""
    productos = Producto.objects.all().values(
        'id_producto', 'nombre', 'precio', 'plataforma', 
        'imagen_url', 'descripcion', 'stock'
    )
    
    productos_list = []
    for p in productos:
        etiquetas = Producto.objects.get(id_producto=p['id_producto']).etiquetas.all().values('id_etiqueta', 'nombre')
        p['etiquetas'] = list(etiquetas)
        productos_list.append(p)
    
    return JsonResponse({'productos': productos_list})

@require_POST
def api_add_to_cart(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        producto_id = int(payload.get('producto_id'))
        cantidad = int(payload.get('cantidad', 1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

    producto = get_object_or_404(Producto, id_producto=producto_id)
    estado_abierto, _ = EstadoCarrito.objects.get_or_create(nombre='Abierto')
    carrito, _ = Carrito.objects.get_or_create(usuario=usuario, estado_carrito=estado_abierto)

    detalle, created = CarritoDetalle.objects.get_or_create(
        carrito=carrito,
        producto=producto,
        defaults={'cantidad': 0, 'subtotal': Decimal('0.00')}
    )
    detalle.cantidad = detalle.cantidad + max(1, cantidad)
    detalle.save()

    items_qs = carrito.carritodetalle_set.select_related('producto').all()
    items = [{
        'id_detalle': d.id_detalle,
        'producto_id': d.producto.id_producto,
        'producto_nombre': d.producto.nombre,
        'cantidad': d.cantidad,
        'subtotal': float(d.subtotal),
        'imagen_url': d.producto.imagen_url,
        'precio_unitario': float(d.producto.precio)
    } for d in items_qs]
    total = sum(i['subtotal'] for i in items)
    return JsonResponse({'ok': True, 'carrito_id': carrito.id_carrito, 'total': total, 'items': items})

@require_http_methods(['GET'])
def api_get_cart(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    estado_abierto, _ = EstadoCarrito.objects.get_or_create(nombre='Abierto')
    try:
        carrito = Carrito.objects.get(usuario=usuario, estado_carrito=estado_abierto)
    except Carrito.DoesNotExist:
        return JsonResponse({'ok': True, 'items': [], 'total': 0.0})
    
    items_qs = carrito.carritodetalle_set.select_related('producto').all()
    items = [{
        'id_detalle': d.id_detalle,
        'producto_id': d.producto.id_producto,
        'producto_nombre': d.producto.nombre,
        'cantidad': d.cantidad,
        'subtotal': float(d.subtotal),
        'imagen_url': d.producto.imagen_url,
        'precio_unitario': float(d.producto.precio)
    } for d in items_qs]
    total = sum(i['subtotal'] for i in items)
    return JsonResponse({'ok': True, 'items': items, 'total': total})

@require_POST
def api_remove_from_cart(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        detalle_id = int(payload.get('id_detalle'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

    estado_abierto, _ = EstadoCarrito.objects.get_or_create(nombre='Abierto')
    carrito = get_object_or_404(Carrito, usuario=usuario, estado_carrito=estado_abierto)
    detalle = get_object_or_404(CarritoDetalle, id_detalle=detalle_id, carrito=carrito)
    detalle.delete()

    items_qs = carrito.carritodetalle_set.select_related('producto').all()
    items = [{
        'id_detalle': d.id_detalle,
        'producto_id': d.producto.id_producto,
        'producto_nombre': d.producto.nombre,
        'cantidad': d.cantidad,
        'subtotal': float(d.subtotal),
        'imagen_url': d.producto.imagen_url,
        'precio_unitario': float(d.producto.precio)
    } for d in items_qs]
    total = sum(i['subtotal'] for i in items)
    return JsonResponse({'ok': True, 'items': items, 'total': total})

@require_POST
def api_update_cart(request):
    from decimal import Decimal
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        id_detalle = int(payload.get('id_detalle'))
        cantidad = int(payload.get('cantidad', 1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

    if cantidad < 1:
        return JsonResponse({'ok': False, 'error': 'invalid_cantidad'}, status=400)

    estado_abierto, _ = EstadoCarrito.objects.get_or_create(nombre='Abierto')
    carrito = get_object_or_404(Carrito, usuario=usuario, estado_carrito=estado_abierto)
    detalle = get_object_or_404(CarritoDetalle, id_detalle=id_detalle, carrito=carrito)

    detalle.cantidad = cantidad
    detalle.save()

    items_qs = carrito.carritodetalle_set.select_related('producto').all()
    items = [{
        'id_detalle': d.id_detalle,
        'producto_id': d.producto.id_producto,
        'producto_nombre': d.producto.nombre,
        'cantidad': d.cantidad,
        'subtotal': float(d.subtotal),
        'imagen_url': d.producto.imagen_url,
        'precio_unitario': float(d.producto.precio)
    } for d in items_qs]
    total = sum(i['subtotal'] for i in items)
    return JsonResponse({'ok': True, 'items': items, 'total': total})

@require_POST
def api_create_payment_method(request):
    """
    POST JSON { stripe_payment_method_id: "pm_...", marca: "Visa", ultimos_4: "4242", vencimiento: "12/25" }
    Guarda el método de pago en la BD asociado al usuario actual.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        stripe_pm_id = payload.get('stripe_payment_method_id')
        marca = payload.get('marca', 'Desconocida')
        ultimos_4 = payload.get('ultimos_4', '****')
        vencimiento = payload.get('vencimiento', '01/01')
    except Exception as e:
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

    if not stripe_pm_id:
        return JsonResponse({'ok': False, 'error': 'missing_stripe_id'}, status=400)

    # Verificar que el método de pago existe en Stripe
    try:
        pm = stripe.PaymentMethod.retrieve(stripe_pm_id)
    except stripe.error.InvalidRequestError:
        return JsonResponse({'ok': False, 'error': 'invalid_payment_method'}, status=400)

    # Crear o obtener Customer en Stripe
    try:
        if usuario.stripe_customer_id:
            customer = stripe.Customer.retrieve(usuario.stripe_customer_id)
        else:
            customer = stripe.Customer.create(
                email=usuario.correo,
                name=f"{usuario.nombre} {usuario.apellido}",
                metadata={'usuario_id': usuario.id_usuario}
            )
            usuario.stripe_customer_id = customer.id
            usuario.save()
    except stripe.error.StripeError as e:
        return JsonResponse({'ok': False, 'error': f'Error creando customer: {str(e)}'}, status=400)

    # Adjuntar PaymentMethod al Customer
    try:
        stripe.PaymentMethod.attach(stripe_pm_id, customer=customer.id)
    except stripe.error.StripeError as e:
        return JsonResponse({'ok': False, 'error': f'Error adjuntando método: {str(e)}'}, status=400)

    # Si el usuario ya tiene métodos de pago, asegurarse de que este no sea principal
    es_principal = MetodoPagoUsuario.objects.filter(usuario=usuario).count() == 0

    # Guardar en BD
    metodo, created = MetodoPagoUsuario.objects.get_or_create(
        usuario=usuario,
        stripe_payment_method_id=stripe_pm_id,
        defaults={
            'marca': marca,
            'ultimos_4': ultimos_4,
            'vencimiento': vencimiento,
            'es_principal': es_principal
        }
    )

    if not created:
        return JsonResponse({'ok': False, 'error': 'payment_method_already_saved'}, status=400)

    return JsonResponse({
        'ok': True,
        'message': f'Tarjeta {marca} **** {ultimos_4} guardada con éxito',
        'metodo_id': metodo.id_metodo,
        'es_principal': es_principal
    })

@require_POST
def api_delete_payment_method(request):
    """Elimina un método de pago."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        metodo_id = int(payload.get('id_metodo'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

    metodo = get_object_or_404(MetodoPagoUsuario, id_metodo=metodo_id, usuario=usuario)
    era_principal = metodo.es_principal
    metodo.delete()

    # Si era el principal, asignar otro como principal
    if era_principal:
        proximo = MetodoPagoUsuario.objects.filter(usuario=usuario).first()
        if proximo:
            proximo.es_principal = True
            proximo.save()

    return JsonResponse({'ok': True, 'message': 'Método de pago eliminado'})

@require_POST
def api_set_primary_payment_method(request):
    """Establece un método de pago como principal."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        metodo_id = int(payload.get('id_metodo'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

    metodo = get_object_or_404(MetodoPagoUsuario, id_metodo=metodo_id, usuario=usuario)

    # Quitar principal de todos
    MetodoPagoUsuario.objects.filter(usuario=usuario).update(es_principal=False)
    # Establecer como principal
    metodo.es_principal = True
    metodo.save()

    return JsonResponse({'ok': True, 'message': f'{metodo.marca} **** {metodo.ultimos_4} es ahora tu tarjeta principal'})

@require_http_methods(['GET'])
def api_get_payment_methods(request):
    """Obtiene los métodos de pago del usuario."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    metodos = MetodoPagoUsuario.objects.filter(usuario=usuario)

    items = [{
        'id_metodo': m.id_metodo,
        'marca': m.marca,
        'ultimos_4': m.ultimos_4,
        'vencimiento': m.vencimiento,
        'es_principal': m.es_principal,
        'stripe_pm_id': m.stripe_payment_method_id
    } for m in metodos]

    return JsonResponse({'ok': True, 'items': items})

@require_POST
def api_process_payment(request):
    """Procesa el pago usando la tarjeta principal del usuario (asegura Customer y adjunta PaymentMethod)."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)
    usuario = get_object_or_404(Usuario, id_usuario=user_id)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        monto_centavos = int(payload.get('monto_centavos'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)
    if monto_centavos <= 0:
        return JsonResponse({'ok': False, 'error': 'invalid_amount'}, status=400)

    # Obtener tarjeta principal
    try:
        metodo_pago = MetodoPagoUsuario.objects.get(usuario=usuario, es_principal=True)
    except MetodoPagoUsuario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'no_payment_method'}, status=400)

    # Obtener carrito abierto
    estado_abierto, _ = EstadoCarrito.objects.get_or_create(nombre='Abierto')
    try:
        carrito = Carrito.objects.get(usuario=usuario, estado_carrito=estado_abierto)
    except Carrito.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'empty_cart'}, status=400)
    if carrito.carritodetalle_set.count() == 0:
        return JsonResponse({'ok': False, 'error': 'empty_cart'}, status=400)

    # Asegurar Customer en Stripe
    try:
        if not usuario.stripe_customer_id:
            customer = stripe.Customer.create(email=usuario.correo, name=f"{usuario.nombre} {usuario.apellido}", metadata={'usuario_id': usuario.id_usuario})
            usuario.stripe_customer_id = customer.id
            usuario.save()
        else:
            customer = stripe.Customer.retrieve(usuario.stripe_customer_id)
    except stripe.error.StripeError as e:
        return JsonResponse({'ok': False, 'error': 'stripe_customer_error', 'message': str(e)}, status=400)

    # Recuperar PaymentMethod y adjuntarlo si hace falta
    try:
        pm = stripe.PaymentMethod.retrieve(metodo_pago.stripe_payment_method_id)
    except stripe.error.StripeError as e:
        return JsonResponse({'ok': False, 'error': 'invalid_payment_method', 'message': str(e)}, status=400)

    # Si el PM está adjunto a otro customer, no podemos usarlo
    if getattr(pm, 'customer', None) and pm.customer != customer.id:
        return JsonResponse({
            'ok': False,
            'error': 'payment_method_attached_other_customer',
            'message': 'La tarjeta está vinculada a otro cliente en Stripe. Reagrega la tarjeta desde tu perfil.'
        }, status=400)

    # Si no está adjunto, intentar adjuntar
    if not getattr(pm, 'customer', None):
        try:
            stripe.PaymentMethod.attach(pm.id, customer=customer.id)
        except stripe.error.InvalidRequestError as e:
            return JsonResponse({'ok': False, 'error': 'pm_attach_failed', 'message': str(e)}, status=400)
        except stripe.error.StripeError as e:
            return JsonResponse({'ok': False, 'error': 'stripe_error', 'message': str(e)}, status=400)

    # Crear y confirmar PaymentIntent con customer y payment_method
    try:
        intent = stripe.PaymentIntent.create(
            amount=monto_centavos,
            currency='usd',
            customer=customer.id,
            payment_method=metodo_pago.stripe_payment_method_id,
            off_session=True,
            confirm=True,
            metadata={
                'usuario_id': usuario.id_usuario,
                'carrito_id': carrito.id_carrito
            }
        )
    except stripe.error.CardError as e:
        return JsonResponse({'ok': False, 'error': 'card_error', 'message': e.user_message}, status=400)
    except stripe.error.StripeError as e:
        return JsonResponse({'ok': False, 'error': 'stripe_error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': 'server_error', 'message': str(e)}, status=500)

    if intent.status != 'succeeded':
        return JsonResponse({'ok': False, 'error': f'payment_failed', 'message': f'Intent status: {intent.status}'}, status=400)

    # Pago exitoso: crear factura, detalles y asignar claves
    factura = Factura.objects.create(
        usuario=usuario,
        metodo_pago=metodo_pago,
        total=Decimal(monto_centavos / 100),
        impuesto_total=Decimal('0.00'),
        descuento_total=Decimal('0.00'),
        estado='Completado'
    )

    # Obtener estado "Entregada"
    estado_entregada, _ = EstadoClave.objects.get_or_create(nombre='Entregada')

    # Procesar cada detalle del carrito
    for detalle in carrito.carritodetalle_set.all():
        # Crear DetalleFactura
        DetalleFactura.objects.create(
            factura=factura,
            producto=detalle.producto,
            cantidad=detalle.cantidad,
            precio_venta_unitario=detalle.producto.precio,
            subtotal=detalle.subtotal
        )

        # REDUCIR STOCK DEL PRODUCTO
        producto = detalle.producto
        if producto.stock >= detalle.cantidad:
            producto.stock -= detalle.cantidad
            producto.save()
        else:
            print(f"⚠️ ADVERTENCIA: Stock insuficiente para {producto.nombre}. Stock actual: {producto.stock}, Cantidad solicitada: {detalle.cantidad}")

        # ASIGNAR CLAVES DISPONIBLES: obtener N claves sin factura asignada
        claves_disponibles = ClaveJuego.objects.filter(
            producto=detalle.producto,
            factura__isnull=True,  # sin asignar
            estado_clave__nombre='Disponible'  # estado disponible
        )[:detalle.cantidad]

        if claves_disponibles.count() < detalle.cantidad:
            print(f"⚠️ ADVERTENCIA: Solo hay {claves_disponibles.count()} claves para {detalle.producto.nombre}, se necesitan {detalle.cantidad}")

        for clave in claves_disponibles:
            clave.factura = factura
            clave.estado_clave = estado_entregada
            clave.save()

    # Crear transacción
    Transaccion.objects.create(
        factura=factura,
        monto=Decimal(monto_centavos / 100),
        metodo='Stripe - ' + metodo_pago.marca,
        estado='Exitosa'
    )

    # Marcar carrito como completado
    estado_completado, _ = EstadoCarrito.objects.get_or_create(nombre='Completado')
    carrito.estado_carrito = estado_completado
    carrito.save()

    return JsonResponse({
        'ok': True,
        'message': '¡Pago realizado exitosamente!',
        'factura_id': factura.id_factura,
        'intent_id': intent.id
    })

# Confirmación de compra
def confirmacion_compra(request, factura_id):
    """
    Muestra la factura detallada después de un pago exitoso.
    Solo permite acceso al usuario propietario de la factura.
    """
    factura = get_object_or_404(Factura, id_factura=factura_id)
    # Seguridad: solo el usuario propietario puede ver la factura
    if request.session.get('user_id') != factura.usuario.id_usuario:
        return redirect('index')

    detalles = DetalleFactura.objects.filter(factura=factura).select_related('producto')
    subtotal = sum([d.subtotal for d in detalles]) if detalles.exists() else Decimal('0.00')
    impuesto = factura.impuesto_total or Decimal('0.00')
    descuento = factura.descuento_total or Decimal('0.00')
    total = factura.total or (subtotal + impuesto - descuento)

    context = {
        'factura': factura,
        'detalles': detalles,
        'subtotal': subtotal,
        'impuesto': impuesto,
        'descuento': descuento,
        'total': total,
        'cliente_nombre': f"{factura.usuario.nombre} {factura.usuario.apellido}",
        'cliente_correo': factura.usuario.correo,
        'metodo_pago_display': f"{factura.metodo_pago.marca} **** {factura.metodo_pago.ultimos_4}" if factura.metodo_pago else 'N/A',
    }
    return render(request, 'core/factura.html', context)



def panel_admin(request):
    """Panel de administración - solo para admins."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    
    usuario = get_object_or_404(Usuario, id_usuario=user_id)
    session_role = (request.session.get('user_rol') or '').strip().lower()
    
    admin_aliases = {'admin', 'administrador', 'administrator', 'superadmin', 'superuser'}
    if session_role not in admin_aliases:
        messages.error(request, "No tienes acceso a esta página.")
        return redirect('index')
    
    return render(request, 'core/panelAdmin.html')

@require_http_methods(["GET"])
def purchase_history_api(request):
    """Devuelve el historial de compras con claves agrupadas por producto."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'ok': False, 'error': 'No autenticado'}, status=401)

    try:
        usuario = Usuario.objects.get(id_usuario=user_id)
        
        # Obtener facturas completadas
        facturas = Factura.objects.filter(
            usuario=usuario,
            estado='Completado'
        ).order_by('-fecha')

        items = []
        
        for factura in facturas:
            # Obtener cada detalle (producto individual) de la factura
            detalles = DetalleFactura.objects.filter(factura=factura).select_related('producto')
            
            for detalle in detalles:
                # Obtener TODAS las claves de este producto en esta factura
                todas_claves = ClaveJuego.objects.filter(
                    factura=factura,
                    producto=detalle.producto,
                    estado_clave__nombre='Entregada'
                ).order_by('id_clave').values_list('clave', flat=True)
                
                # Contar cuántas claves de este producto ya se asignaron a otros detalles anteriores
                detalles_anteriores = DetalleFactura.objects.filter(
                    factura=factura,
                    producto=detalle.producto,
                    id_detalle__lt=detalle.id_detalle
                ).aggregate(total_cantidad=models.Sum('cantidad'))
                
                claves_usadas = detalles_anteriores['total_cantidad'] or 0
                
                # Obtener solo las claves de este detalle específico
                keys = list(todas_claves[claves_usadas:claves_usadas + detalle.cantidad])
                
                items.append({
                    'id': f'SAGA-{factura.id_factura}',
                    'date': factura.fecha.strftime('%Y-%m-%d %H:%M:%S'),
                    'item': detalle.producto.nombre,
                    'platform': detalle.producto.plataforma or 'N/A',
                    'amount': float(detalle.subtotal),
                    'keys': keys
                })

        return JsonResponse({'ok': True, 'items': items})
        
    except Usuario.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)



@require_POST
def api_change_password(request):
    if not request.session.get('user_id'):
        return JsonResponse({'ok': False, 'error': 'not_authenticated'}, status=401)

    usuario = get_object_or_404(Usuario, id_usuario=request.session['user_id'])

    try:
        payload = json.loads(request.body or '{}')
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)

    current_password = (payload.get('current_password') or '').strip()
    new_password = (payload.get('new_password') or '').strip()
    confirm_password = (payload.get('confirm_password') or '').strip()

    if not current_password or not new_password or not confirm_password:
        return JsonResponse({'ok': False, 'error': 'missing_fields'}, status=400)

    if new_password != confirm_password:
        return JsonResponse({'ok': False, 'error': 'password_mismatch'}, status=400)

    if len(new_password) < 8:
        return JsonResponse({'ok': False, 'error': 'password_too_short'}, status=400)

    password_attr = None
    for candidate in ('password', 'contrasena', 'contraseña'):
        if hasattr(usuario, candidate):
            password_attr = candidate
            break

    if not password_attr:
        return JsonResponse({'ok': False, 'error': 'password_field_missing'}, status=500)

    stored_password = getattr(usuario, password_attr, '')

    password_matches = False
    if stored_password:
        if check_password(current_password, stored_password):
            password_matches = True
        elif stored_password == current_password:
            password_matches = True

    if not password_matches:
        return JsonResponse({'ok': False, 'error': 'invalid_current_password'}, status=400)

    setattr(usuario, password_attr, make_password(new_password))
    usuario.save(update_fields=[password_attr])

    return JsonResponse({'ok': True, 'message': 'Contraseña actualizada correctamente.'})
