from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import  ContactoForm
from .models import Cliente, Usuario, Empleado
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group

# landing para redirigir según rol

def landing(request):
    user = request.user

    if user.is_authenticated:
        empleado = getattr(user, 'empleado', None)
        cliente = getattr(user, 'cliente', None)

        if empleado:
            rol = empleado.rol
            if rol == 'dueño' or user.is_superuser:
                return redirect('tienda:dashboard_dueno')
            elif rol in ['cajero', 'almacenista', 'ayudante']:
                return redirect('tienda:dashboard_socio')
        elif cliente:
            return render(request, 'tienda/landing.html', {'cliente': cliente})

    return render(request, 'tienda/landing.html')

    
def dashboard_socio(request):
    return render(request, 'tienda/dashboard_socio.html')

def dashboard_dueno(request):
    return render(request, 'tienda/dashboard_dueno.html')


def login_user(request):
    if request.method == 'POST': 
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            tiene_cliente = hasattr(user, 'cliente')
            tiene_empleado = hasattr(user, 'empleado')
            es_superuser = user.is_superuser

            if tiene_cliente and tiene_empleado:
                return redirect('seleccionar_rol')  # Vista donde elige cómo entrar

            if es_superuser:
                return redirect('tienda:dashboard_dueno')

            if tiene_empleado:
                rol = user.empleado.rol
                if rol == 'dueño':
                    return redirect('tienda:dashboard_dueno')
                elif rol in ['cajero', 'almacenista', 'ayudante']:
                    return redirect('tienda:dashboard_socio')

            if tiene_cliente:
                return render(request, 'tienda/landing.html', {'cliente': user.cliente})

            messages.error(request, "⚠️ Tu cuenta no tiene un perfil asignado.")
        else:
            messages.error(request, "❌ Usuario o contraseña incorrectos")

        return redirect('tienda:login')

    return render(request, 'tienda/login.html')


# Vista de logout
def logout_user(request):
    logout(request)
    return redirect('tienda:login')

# Registro de empleados usando formulario Django
def registro_empleado(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        edad = request.POST.get('edad')
        direccion = request.POST.get('direccion')
        numero_contacto = request.POST.get('numero_contacto')
        rol = request.POST.get('rol')
        contacto_emergencia = request.POST.get('contacto_emergencia')
        descripcion_contacto_emergencia = request.POST.get('descripcion_contacto_emergencia')

        # Validaciones básicas
        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect('tienda:registro_empleado')

        if len(password1) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return redirect('tienda:registro_empleado')

        if Usuario.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya está registrado.")
            return redirect('tienda:registro_empleado')

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, "Este correo ya está registrado.")
            return redirect('tienda:registro_empleado')

        # Crear usuario
        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        usuario.is_staff = True
        usuario.is_superuser = (rol == 'dueño')
        usuario.save()

        # Asignar grupo
        try:
            grupo_empleado = Group.objects.get(name='Empleado')
            usuario.groups.add(grupo_empleado)
        except Group.DoesNotExist:
            pass

        # Crear empleado
        empleado = Empleado.objects.create(
            user=usuario,
            edad=edad,
            direccion=direccion,
            numero_contacto=numero_contacto,
            rol=rol,
            contacto_emergencia=contacto_emergencia,
            descripcion_contacto_emergencia=descripcion_contacto_emergencia
        )

        messages.success(request, "Empleado registrado exitosamente.")
        return redirect('tienda:login')

    return render(request, 'tienda/registro_empleado.html')

# Registro de clientes usando formulario manual
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
            return render(request, 'tienda/registro_cliente.html', {'errores': errores})

        # Crear usuario sin permisos administrativos
        user = Usuario.objects.create_user(
            username=username,
            password=password1,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_staff = False
        user.is_superuser = False
        user.save()

        # Asignar al grupo "Cliente"
        grupo_cliente, _ = Group.objects.get_or_create(name='Cliente')
        user.groups.add(grupo_cliente)

        # Crear instancia de Cliente
        cliente = Cliente(user=user, direccion=direccion, numero_contacto=numero_contacto)
        cliente.save()
        
        messages.success(request, "Cliente registrado exitosamente ✅.")
        return redirect('tienda:login')
    
    return render(request, 'tienda/registro_cliente.html')



# Vista de contacto
def contacto(request):
    puede_enviar = False
    form = ContactoForm()

    if hasattr(request.user, 'cliente'):
        puede_enviar = True
    elif hasattr(request.user, 'empleado') or request.user.is_superuser:
        messages.error(request, "Los empleados no pueden enviar mensajes.")
    else:
        messages.warning(request, "Tu cuenta no tiene un rol asignado.")

    return render(request, 'tienda/contacto.html', {
        'form': form,
        'puede_enviar': puede_enviar
    })
    
# Vista de "Sobre nosotros"
def aboutus(request):
    return render(request, 'tienda/about-us.html')


def configuracion_perfil(request):
    return render(request, 'tienda/profile_config.html')