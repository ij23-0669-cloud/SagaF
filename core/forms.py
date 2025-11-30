from django import forms
from .models import Producto, Usuario, Rol, Etiqueta
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

# Choices para Plataformas
PLATAFORMA_CHOICES = [
    ('', '-- Selecciona una plataforma --'),
    ('Steam', 'Steam'),
    ('PS4', 'PS4'),
    ('PS5', 'PS5'),
    ('XBOX One', 'XBOX One'),
    ('Xbox Series X/S', 'Xbox Series X/S'),
    ('Nintendo Switch', 'Nintendo Switch'),
    ('Nintendo Switch 2', 'Nintendo Switch 2'),
]

# Choices para Géneros
GENERO_CHOICES = [
    ('', '-- Selecciona un género --'),
    ('Acción', 'Acción'),
    ('Aventura', 'Aventura'),
    ('Acción-Aventura', 'Acción-Aventura'),
    ('Juegos de Rol (RPG)', 'Juegos de Rol (RPG)'),
    ('Estrategia', 'Estrategia'),
    ('Simulación', 'Simulación'),
    ('Deportes', 'Deportes'),
    ('Carreras', 'Carreras'),
    ('Plataformas', 'Plataformas'),
    ('Lucha (Fighting)', 'Lucha (Fighting)'),
    ('Disparos en Primera Persona (FPS)', 'Disparos en Primera Persona (FPS)'),
    ('Disparos en Tercera Persona (TPS)', 'Disparos en Tercera Persona (TPS)'),
    ('Puzle', 'Puzle'),
    ('Ritmo/Música', 'Ritmo/Música'),
]

class ProductoForm(forms.ModelForm):
    plataforma = forms.ChoiceField(
        choices=PLATAFORMA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
        })
    )

    etiquetas = forms.ModelMultipleChoiceField(
        queryset=Etiqueta.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox rounded border-gray-300'
        }),
        required=False
    )

    class Meta:
        model = Producto
        fields = ['nombre', 'id_categoria', 'plataforma', 'precio', 'stock', 'desarrollador', 'descripcion', 'imagen_url', 'etiquetas']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
            }),
            'desarrollador': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red',
                'rows': 3
            }),
            'imagen_url': forms.URLInput(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
            }),
            'id_categoria': forms.Select(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
            }),
        }

class UsuarioForm(forms.ModelForm):
    contraseña = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
        })
    )

    confirmar_contraseña = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white focus:border-saga-red focus:ring-saga-red'
        })
    )

    fecha_nacimiento = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full rounded-lg border border-gray-300 p-3'
        })
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellido', 'usuario', 'correo', 'contraseña', 'confirmar_contraseña', 'pais', 'fecha_nacimiento']

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'block w-full rounded-lg border border-gray-300 p-3'}),
            'apellido': forms.TextInput(attrs={'class': 'block w-full rounded-lg border border-gray-300 p-3'}),
            'usuario': forms.TextInput(attrs={'class': 'block w-full rounded-lg border border-gray-300 p-3'}),
            'correo': forms.EmailInput(attrs={'class': 'block w-full rounded-lg border border-gray-300 p-3'}),
            
            # Campo de países con menú desplegable
            'pais': CountrySelectWidget(attrs={
                'class': 'block w-full rounded-lg border border-gray-300 p-3 bg-white'
            }),
        }

    # Validación de nombre de usuario único
    def clean_usuario(self):
        username = self.cleaned_data.get('usuario')
        if Usuario.objects.filter(usuario=username).exists():
            raise ValidationError("El nombre de usuario ya existe.")
        return username

    # Validación de contraseñas iguales
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("contraseña")
        confirm = cleaned_data.get("confirmar_contraseña")

        if password and confirm and password != confirm:
            raise ValidationError("Las contraseñas no coinciden.")

        return cleaned_data
    
class LoginForm(forms.Form):
    usuario_o_correo = forms.CharField(
        label='Usuario o Correo',
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 pl-10 border border-gray-300 rounded-lg focus:ring-1 focus:ring-saga-red focus:border-saga-red placeholder-gray-500',
            'placeholder': 'usuario@correo.com o usuario',
            'required': True
        })
    )
    contraseña = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full p-3 pl-10 border border-gray-300 rounded-lg focus:ring-1 focus:ring-saga-red focus:border-saga-red placeholder-gray-500',
            'placeholder': '••••••••',
            'required': True
        })
    )