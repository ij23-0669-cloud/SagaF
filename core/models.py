from django.db import models
from django_countries.fields import CountryField    
from decimal import Decimal
import secrets
import string
from django.db.models.signals import post_save
from django.dispatch import receiver


# Create your models here.
from django.db import models

# Roles
class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=30)

    def __str__(self):
        return self.nombre

# Estados de clave
class EstadoClave(models.Model):
    id_estado_clave = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=30)

    def __str__(self):
        return self.nombre

# Estados de carrito
class EstadoCarrito(models.Model):
    id_estado_carrito = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=30)

    def __str__(self):
        return self.nombre

class Etiqueta(models.Model):
    id_etiqueta = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

# Categorías
class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre

# Usuarios
class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    usuario = models.CharField(max_length=30, unique=True)
    correo = models.CharField(max_length=100)
    contraseña = models.CharField(max_length=255)
    pais = CountryField(blank_label='Seleccione un país')    
    fecha_nacimiento = models.DateField()
    fecha_registro = models.DateField(auto_now_add=True)
    fecha_modificacion = models.DateField(auto_now=True)
    estado = models.CharField(max_length=15)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT)
    metodo_pago_preferido = models.ForeignKey(
        'MetodoPagoUsuario',  # ← Cambiar a MetodoPagoUsuario
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_prefieren'
)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.usuario


# Métodos de pago con Stripe (ESTE ES EL ÚNICO A MANTENER)
class MetodoPagoUsuario(models.Model):
    id_metodo = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='metodos_pago_stripe')  # ← Cambiar related_name
    stripe_payment_method_id = models.CharField(max_length=255, unique=True)  # ID de Stripe
    marca = models.CharField(max_length=50)  # Visa, Mastercard, etc.
    ultimos_4 = models.CharField(max_length=4)
    vencimiento = models.CharField(max_length=5)  # MM/YY
    es_principal = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-es_principal', '-creado_en']

    def __str__(self):
        return f'{self.marca} **** {self.ultimos_4} - {self.usuario.usuario}'

# Productos
class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    plataforma = models.CharField(max_length=30)
    desarrollador = models.CharField(max_length=50)
    imagen_url = models.CharField(max_length=255)
    fecha_agregado = models.DateField(auto_now_add=True)
    id_categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    etiquetas = models.ManyToManyField(Etiqueta, blank=True)
    
    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Si es nuevo, generar claves según el stock
        if is_new and self.stock > 0:
            self._generar_claves_iniciales()

    def _generar_claves_iniciales(self):
        """Genera N claves únicas al crear el producto (N = stock)"""
        from .models import EstadoClave
        
        estado_disponible, _ = EstadoClave.objects.get_or_create(nombre='Disponible')
        claves_existentes = ClaveJuego.objects.filter(producto=self).count()
        claves_a_generar = self.stock - claves_existentes

        for _ in range(claves_a_generar):
            ClaveJuego.objects.create(producto=self, estado_clave=estado_disponible)
            # ClaveJuego.save() generará la clave automáticamente


# helper para generar claves según plataforma
def _generate_key_for_platform(platform: str) -> str:
    """
    Genera una clave formateada según la plataforma.
    Plataformas soportadas:
      - Steam:  XXXXX-XXXXX-XXXXX  (3 grupos de 5 -> 15 chars)
      - PlayStation: XXXX-XXXX-XXXX (3 grupos de 4 -> 12 chars)
      - Xbox:  XXXXX-XXXXX-XXXXX-XXXXX-XXXXX (5 grupos de 5 -> 25 chars)
      - Nintendo eShop: XXXX-XXXX-XXXX-XXXX (4 grupos de 4 -> 16 chars)
    """
    allowed = string.ascii_uppercase + string.digits
    pf = (platform or '').lower()
    if 'steam' in pf:
        groups = [5,5,5]
    elif 'play' in pf or 'playstation' in pf:
        groups = [4,4,4]
    elif 'xbox' in pf:
        groups = [5,5,5,5,5]
    elif 'nintendo' in pf or 'eshop' in pf:
        groups = [4,4,4,4]
    else:
        # fallback: 4-4-4
        groups = [4,4,4]

    parts = []
    for n in groups:
        part = ''.join(secrets.choice(allowed) for _ in range(n))
        parts.append(part)
    return '-'.join(parts)


class ClaveJuego(models.Model):
    id_clave = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='claves')
    factura = models.ForeignKey('Factura', on_delete=models.SET_NULL, null=True, blank=True, related_name='claves_entregadas')
    clave = models.CharField(max_length=255, unique=True, blank=True)
    estado_clave = models.ForeignKey(EstadoClave, on_delete=models.PROTECT)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.clave

    def save(self, *args, **kwargs):
        # Generar clave única si no existe
        if not self.clave:
            attempt = 0
            max_attempts = 10
            while attempt < max_attempts:
                gen = _generate_key_for_platform(getattr(self.producto, 'plataforma', '') or '')
                if not ClaveJuego.objects.filter(clave=gen).exists():
                    self.clave = gen
                    break
                attempt += 1
            if not self.clave:
                self.clave = f"{_generate_key_for_platform(getattr(self.producto, 'plataforma', '') or '')}-{secrets.token_hex(3).upper()}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-fecha_creacion']
        unique_together = ('producto', 'clave')

# Crear una clave automáticamente cuando se añade un Producto (si no existen claves para él)
@receiver(post_save, sender=Producto)
def create_initial_key_for_new_product(sender, instance, created, **kwargs):
    if not created:
        return
    # sólo crear si no existen claves para este producto
    if ClaveJuego.objects.filter(producto=instance).exists():
        return
    # intentar obtener un EstadoClave por defecto o crearlo
    estado, _ = EstadoClave.objects.get_or_create(nombre='Disponible')
    # crear una clave (ClaveJuego.save generará la clave)
    ClaveJuego.objects.create(producto=instance, estado_clave=estado)

# Carrito
class Carrito(models.Model):
    id_carrito = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha_creacion = models.DateField(auto_now_add=True)
    estado_carrito = models.ForeignKey(EstadoCarrito, on_delete=models.PROTECT)

    def __str__(self):
        return f'Carrito {self.id_carrito} - {self.usuario}'

# Detalle del carrito
class CarritoDetalle(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='carritodetalle_set')  # importante el related_name
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ('carrito', 'producto')

    def save(self, *args, **kwargs):
        self.subtotal = (self.producto.precio or Decimal('0.00')) * Decimal(self.cantidad)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre}'

# Facturas
class Factura(models.Model):
    id_factura = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    metodo_pago = models.ForeignKey(MetodoPagoUsuario, on_delete=models.SET_NULL, null=True)  # ← Cambiar a MetodoPagoUsuario
    fecha = models.DateField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    impuesto_total = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=15)

# Detalle de factura
class DetalleFactura(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_venta_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

# Transacciones
class Transaccion(models.Model):
    id_transaccion = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=30)
    estado = models.CharField(max_length=15)

# Entregas de claves
class EntregaClave(models.Model):
    id_entrega = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE)
    clave = models.ForeignKey(ClaveJuego, on_delete=models.PROTECT)
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Clave entregada para factura {self.factura.id_factura}'

