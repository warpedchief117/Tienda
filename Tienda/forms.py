from django import forms
from django.contrib.auth.models import Group
from django import forms
from django.contrib.auth import get_user_model





class ContactoForm(forms.Form):
    nombre = forms.CharField(label='Nombre', max_length=100)
    email = forms.EmailField(label='Correo electrónico')
    mensaje = forms.CharField(label='Mensaje', widget=forms.Textarea(attrs={'rows': 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            attrs = {'class': 'form-control'}
            if field_name == 'mensaje':
                attrs['placeholder'] = 'Escribe tu mensaje aquí'
            elif field_name == 'email':
                attrs['placeholder'] = 'Tu correo'
            elif field_name == 'nombre':
                attrs['placeholder'] = 'Tu nombre'

            field.widget.attrs.update(attrs)