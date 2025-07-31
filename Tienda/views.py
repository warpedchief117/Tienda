from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import RegistroEmpleadoForm, ContactoForm
from . models import Cliente, Usuario
from django.contrib.auth.decorators import login_required

# funcion home solo para empleados.
@login_required
def home(request):
    if request.user.is_superuser or hasattr(request.user, 'empleado'):
        return render(request, 'home.html')
    else:
        return redirect('landing')


def login_user(request):
    if request.method == 'POST': 
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('Tienda:home')  # Vista de empleados/admin
            elif hasattr(user, 'empleado'):
                return redirect('Tienda:home')
            elif hasattr(user, 'cliente'):
                return redirect('landing')
            else:
                return redirect('landing')
        else:
            messages.error(request, "❌ Usuario o contraseña incorrectos")
            return redirect('Tienda:login')


    return render(request, 'login.html')

#FUNCION DE LOGOUT
def logout_user(request):
    logout(request)
    return redirect('Tienda:login')

#Logica de formulario USANDO .FORMS de registro de empleado.
def registro_empleado(request):
    if request.method == 'POST':
        form = RegistroEmpleadoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "✅ Usuario creado exitosamente. ¡Ahora inicia sesión!")
                return redirect('Tienda:login')
            except Exception as e:
                messages.error(request, f"❌ Ocurrió un error al registrar: {str(e)}")
        else:
            messages.error(request, "⚠️ Verifica los campos marcados en rojo.")
    else:
        form = RegistroEmpleadoForm()
    
    return render(request, 'registro_empleado.html', {'form': form})

#LOGICA DE FORMULARIO MANUAL HTML DE REGISTRO DE CLIENTES.

def registro_cliente(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        direccion = request.POST.get('direccion')
        numero_contacto = request.POST.get('numero_contacto')

        errores = []
        if password1 != password2:
            errores.append("Las contraseñas no coinciden.")
        if Usuario.objects.filter(username=username).exists():
            errores.append("El nombre de usuario ya está registrado.")
        if Usuario.objects.filter(email=email).exists():
            errores.append("Este correo ya está registrado.")

        if errores:
            return render(request, 'registro_cliente.html', {'errores': errores})

        user = Usuario.objects.create_user(
            username=username,
            password=password1,
            email=email,
            first_name=first_name,
            last_name=last_name,
            tipo='cliente',)

        cliente = Cliente(user=user, direccion=direccion, numero_contacto=numero_contacto)
        cliente.save()
        
        messages.success(request, "Cliente registrado exitosamente ✅.")
        return redirect('Tienda:login')
    return render(request, 'registro_cliente.html')

def contacto(request):
    form = ContactoForm()
    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            # Aquí puedes guardar, enviar email, etc.
            messages.success(request, 'Mensaje enviado con éxito. ¡Gracias por contactarnos!')
            # Redirigir o mostrar mensaje de éxito
    return render(request, 'contacto.html', {'form': form})

def aboutus(request):
    return render(request,'about-us.html')
