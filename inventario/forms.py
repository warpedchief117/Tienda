from django import forms

from tienda.models import Empleado
from .models import Categoria, TransferenciaInventario, Producto, Categoria, Ubicacion


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'padre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'padre': forms.Select(attrs={
                'class': 'form-control',
                'id': 'campo-padre'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['padre'].required = False
        self.fields['padre'].queryset = Categoria.objects.filter(padre__isnull=True)

    def clean(self):
        cleaned_data = super().clean()
        es_subcategoria = self.data.get('es_subcategoria') == 'on'
        padre = cleaned_data.get('padre')

        if es_subcategoria and not padre:
            self.add_error('padre', 'Debes seleccionar una categoría padre si estás creando una subcategoría.')
        elif es_subcategoria and padre and not Categoria.objects.filter(id=padre.id, padre__isnull=True).exists():
            self.add_error('padre', 'La categoría seleccionada no es válida como categoría padre.')

##Formularios de inventario

class TransferenciaInventarioForm(forms.ModelForm):
    class Meta:
        model = TransferenciaInventario
        fields = ['producto', 'cantidad', 'origen', 'destino']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'origen': forms.Select(attrs={'class': 'form-control'}),
            'destino': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get('origen')
        destino = cleaned_data.get('destino')
        cantidad = cleaned_data.get('cantidad')
        producto = cleaned_data.get('producto')

        if origen == destino:
            self.add_error('destino', "La ubicación de origen y destino no pueden ser iguales.")

        if cantidad is not None and cantidad <= 0:
            self.add_error('cantidad', "La cantidad debe ser mayor que cero.")

        # Validación opcional de stock
        if producto and origen and cantidad:
            from .models import Inventario
            inv_origen = Inventario.objects.filter(producto=producto, ubicacion=origen).first()
            if not inv_origen or inv_origen.cantidad_actual < cantidad:
                self.add_error('cantidad', "Inventario insuficiente en la ubicación de origen.")

        return cleaned_data

        
        
#Formulario para agregar producto a inventario dentro de una ubicación.
class AgregarInventarioForm(forms.Form):
    cantidad = forms.IntegerField(
        min_value=1,
        label="Cantidad a agregar",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. 10'
        })
    )



#Formulario para registrar productos ALFIN.

class ProductoForm(forms.ModelForm):
    categoria_padre = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(padre__isnull=True),
        label="Categoría padre",
        required=True,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_categoria_padre'})
    )

    subcategoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        label="Subcategoría",
        required=True,  # ahora sí debe ser obligatorio
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_subcategoria'})
    )

    cantidad_inicial = forms.IntegerField(
        label="Cantidad inicial",
        min_value=1,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Número de piezas al registrar el producto"
    )
    
    ubicacion = forms.ModelChoiceField(
        queryset=Ubicacion.objects.all(),
        required=True,
        label="Ubicación de registro",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio_mayoreo', 'precio_menudeo',
            'precio_docena', 'foto_url', 'temporada', 'dueño',
            'codigo_barras', 'tipo_codigo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'precio_mayoreo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'precio_menudeo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'precio_docena': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'foto_url': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'capture': 'environment'
            }),
            'temporada': forms.Select(attrs={'class': 'form-control'}),  # si es FK
            'dueño': forms.Select(attrs={'class': 'form-control'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_codigo': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['dueño'].queryset = Empleado.objects.filter(rol='dueño')

        if 'categoria_padre' in self.data:
            try:
                padre_id = int(self.data.get('categoria_padre'))
                self.fields['subcategoria'].queryset = Categoria.objects.filter(padre_id=padre_id)
            except (ValueError, TypeError):
                self.fields['subcategoria'].queryset = Categoria.objects.none()
        elif self.instance.pk and self.instance.categoria:
            padre = self.instance.categoria.padre
            self.fields['subcategoria'].queryset = Categoria.objects.filter(padre=padre) if padre else Categoria.objects.none()
        else:
            self.fields['subcategoria'].queryset = Categoria.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        subcategoria = cleaned_data.get('subcategoria')

        if not subcategoria:
            raise forms.ValidationError('Debes seleccionar una subcategoría válida.')

        # Temporada es opcional → no validamos nada aquí
        return cleaned_data

