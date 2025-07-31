from django import forms
from .models import Empleado, Usuario

class RegistroEmpleadoForm(forms.ModelForm):
    username = forms.CharField(label="Nombre de Usuario", max_length=150)
    first_name = forms.CharField(label="Nombre(s)", max_length=150)
    last_name = forms.CharField(label="Apellido(s)", max_length=150)
    email = forms.EmailField(label="Correo Electrónico", max_length=254)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput)

    class Meta:
        model = Empleado
        fields = [
            'edad', 'direccion', 'numero_contacto',
            'rol', 'contacto_emergencia', 'descripcion_contacto_emergencia'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            attrs = {'class': 'form-control'}

            if field_name == 'rol':
                field.widget = forms.Select(attrs={'class': 'form-control'})
            if field_name == 'edad':
                attrs['min'] = '16'
                attrs['placeholder'] = '(mínima 16)'

            field.widget.attrs.update(attrs)

        # Excluir el rol "dueño"
        self.fields['rol'].choices = [
            choice for choice in self.fields['rol'].choices if choice[0] != 'dueño'
        ]

    def clean(self):
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get('password1')
        pwd2 = cleaned_data.get('password2')

        if pwd1 and pwd2 and pwd1 != pwd2:
            self.add_error('password2', "Las contraseñas no coinciden")

        return cleaned_data

    def clean_edad(self):
        edad = self.cleaned_data.get('edad')
        if edad is not None and edad < 16:
            raise forms.ValidationError("Menores de 16 años no pueden chambear")
        return edad

    def clean_username(self):
        username = self.cleaned_data['username']
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("El nombre de usuario ya está registrado.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo ya está registrado.")
        return email

    def save(self, commit=True):
        usuario = Usuario.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password1'],
            email=self.cleaned_data['email']
        )
        usuario.first_name = self.cleaned_data['first_name']
        usuario.last_name = self.cleaned_data['last_name']
        usuario.save()

        empleado = super().save(commit=False)
        empleado.user = usuario
        if commit:
            empleado.save()
        return empleado


class ContactoForm(forms.Form):
    nombre = forms.CharField(label='Nombre', max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Tu nombre'
    }))
    email = forms.EmailField(label='Correo electrónico', widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Tu correo'
    }))
    mensaje = forms.CharField(label='Mensaje', widget=forms.Textarea(attrs={
        'class': 'form-control',
        'placeholder': 'Escribe tu mensaje aquí',
        'rows': 4
    }))
