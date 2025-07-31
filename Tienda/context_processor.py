# Tienda/context_processors.py

def tipo_usuario(request):
    tipo = 'visitante'
    if request.user.is_authenticated:
        if request.user.tipo == 'empleado' or request.user.is_superuser:
            tipo = 'empleado'
        elif request.user.tipo == 'cliente':
            tipo = 'cliente'
    return {'tipo_usuario': tipo}
