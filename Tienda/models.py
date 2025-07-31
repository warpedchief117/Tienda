from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    TIPO_USUARIO = [
        ('cliente', 'Cliente'),
        ('empleado', 'Empleado'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPO_USUARIO)
    email = models.EmailField(unique=True)  # sobrescribe el campo original
    def __str__(self):
        return f"{self.username} ({self.tipo})"
    
    

class Empleado(models.Model):
    ROL_CHOICES = [
        ('cajero', 'Cajero'),
        ('ayudante', 'Ayudante General'),
        ('almacenista', 'Almacenista'),
        ('dueño', 'Dueño'),  # dueño se esconde del dropdown 
    ]
    user = models.OneToOneField(Usuario, on_delete=models.CASCADE)    
    edad = models.IntegerField(null=True, blank=True)
    direccion = models.CharField(blank=True)
    numero_contacto = models.CharField(max_length=20)
    rol = models.CharField(max_length=50, choices=ROL_CHOICES)
    contacto_emergencia = models.CharField(max_length=100)
    descripcion_contacto_emergencia = models.TextField(max_length=100)
    

    def __str__(self):
        return f"{self.user} ({self.rol})"
    

class Cliente(models.Model):
    user = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    direccion = models.CharField(max_length=255)
    numero_contacto = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.username} (Cliente)"
