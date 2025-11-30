from django.contrib import admin

# Register your models here.
from .models import *

# Registrar modelos
admin.site.register(Usuario)
admin.site.register(MetodoPagoUsuario)
admin.site.register(Rol)
admin.site.register(EstadoClave)
admin.site.register(EstadoCarrito)
admin.site.register(Categoria)
admin.site.register(Producto)
admin.site.register(ClaveJuego)
admin.site.register(Carrito)
admin.site.register(CarritoDetalle)
admin.site.register(Factura)
admin.site.register(DetalleFactura)
admin.site.register(Transaccion)
admin.site.register(EntregaClave)
admin.site.register(Etiqueta)