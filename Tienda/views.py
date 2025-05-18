from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

# Create your views here.
def home(request):
    return render(request, 'home.html')


def login (request):
        if request.method == 'POST':
            worker_id = request.POST.get('worker_id')
            password = request.POST.get('password')
            user = authenticate(request, username=worker_id, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # Redirige al usuario a la página de inicio
            else:
                messages.error(request, "Número de trabajador o contraseña incorrectos.")
        return render(request, 'login.html')

def logout (request):
    return render(request, 'logout.html')

def register (request):
    
    return render(request, 'register.html')

def NewProduct (request):
    return render(request, 'NewProduct.html')