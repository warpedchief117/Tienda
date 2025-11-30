import decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from .models import Categoria, Atributo, Producto, ValorAtributo, Ubicacion, Empleado, Inventario, Temporada, MovimientoInventario
from django.http import HttpResponse, JsonResponse
from datetime import datetime
from barcode import EAN13, Code128
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from .forms import CategoriaForm, TransferenciaInventarioForm, AgregarInventarioForm
from .services import aplicar_movimiento_inventario, registrar_movimiento, generar_codigo, generar_base64, detectar_tipo_codigo
from .forms import ProductoForm
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from inventario import reports
from django.core.files.uploadedfile import InMemoryUploadedFile





@login_required
def nuevo_producto(request):
    if not request.user.is_superuser and not hasattr(request.user, 'empleado'):
        raise PermissionDenied("Solo empleados o administradores pueden registrar productos.")

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        codigo = request.POST.get('codigo_barras')

        try:
            cantidad = int(request.POST.get('cantidad_inicial', '0'))
        except (ValueError, TypeError):
            cantidad = 0

        ubicacion_id = request.POST.get('ubicacion')
        ubicacion = Ubicacion.objects.filter(id=ubicacion_id).first()

        # 🟢 Si el producto ya existe → redirigir a agregar inventario
        producto_existente = Producto.objects.filter(codigo_barras=codigo).first()
        if producto_existente and ubicacion:
            request.session['cantidad_inicial'] = cantidad
            return redirect('inventario:agregar_inventario',
                            producto_id=producto_existente.id,
                            ubicacion_id=ubicacion.id)

        # 🆕 Producto nuevo
        if form.is_valid():
            # 🚨 Validar antes de guardar: si no hay código, mandar a seleccionar etiqueta
            if not codigo or codigo.strip() in ["", "0", "None"]:
                messages.info(request, "Este producto no tiene código de barras. Selecciona una etiqueta.")

                # Guardamos datos limpios del formulario pero solo valores simples
                pendiente = {}
                for key, value in form.cleaned_data.items():
                    if isinstance(value, decimal.Decimal):
                        pendiente[key] = str(value)
                    elif hasattr(value, "pk"):  # Model instance
                        pendiente[key] = value.pk
                    elif isinstance(value, (list, tuple)):
                        ids = []
                        for v in value:
                            ids.append(v.pk if hasattr(v, "pk") else str(v))
                        pendiente[key] = ids
                    else:
                        pendiente[key] = str(value) if value is not None else None

                # ⚠️ Asegurar campos obligatorios con valores por defecto
                pendiente["precio_mayoreo"] = pendiente.get("precio_mayoreo") or "0"
                pendiente["precio_menudeo"] = pendiente.get("precio_menudeo") or "0"
                pendiente["precio_docena"] = pendiente.get("precio_docena") or "0"

                # Guardar también los atributos escritos
                atributos_pendientes = {}
                for key, value in request.POST.items():
                    if key.startswith("atributo_") and value.strip():
                        atributos_pendientes[key] = value.strip()
                pendiente["atributos"] = atributos_pendientes

                # Guardar en sesión los datos clave
                request.session['pendiente_producto'] = pendiente
                request.session['pendiente_inventario'] = {
                    'cantidad': cantidad,
                    'ubicacion_id': ubicacion.id if ubicacion else None,
                }
                request.session['pendiente_has_file'] = bool(request.FILES)

                # ⚠️ Guardar el dueño seleccionado en el formulario
                dueño = form.cleaned_data.get("dueño")
                pendiente['dueño'] = dueño.id if dueño else None

                return redirect('inventario:seleccionar_etiqueta_temp')

            # 🚀 Flujo normal: producto con código
            producto = form.save(commit=False)

            # Registrado por → siempre el usuario que llena el formulario
            producto.registrado_por = getattr(request.user, "empleado", None)

            # Dueño → empleado con rol dueño seleccionado en el formulario
            dueño = form.cleaned_data.get("dueño")
            if dueño:
                producto.dueño = dueño

            # 🔍 Subcategoría seleccionada en el formulario
            subcategoria = form.cleaned_data.get('categoria')
            if not subcategoria or subcategoria.padre is None:
                messages.error(request, "Debes seleccionar una subcategoría válida.")
                return render(request, 'inventario/nuevo_producto.html', {
                    'form': form,
                    'atributos': Atributo.objects.select_related('categoria').all(),
                    'subcategorias': Categoria.objects.filter(padre__isnull=False),
                })

            producto.categoria = subcategoria

            # ✅ Asignar precios y ubicación
            producto.precio_mayoreo = form.cleaned_data.get("precio_mayoreo") or 0
            producto.precio_menudeo = form.cleaned_data.get("precio_menudeo") or 0
            producto.precio_docena = form.cleaned_data.get("precio_docena") or 0

            producto.save()

            # 🔍 Validar atributos requeridos
            atributos_faltantes = []
            atributos_requeridos = Atributo.objects.filter(categoria=subcategoria)
            for atributo in atributos_requeridos:
                key = f"atributo_{atributo.id}"
                valor = request.POST.get(key, '').strip()
                if not valor:
                    atributos_faltantes.append(atributo.nombre)

            if atributos_faltantes:
                producto.delete()
                messages.error(request, f"Faltan valores para: {', '.join(atributos_faltantes)}")
                return render(request, 'inventario/nuevo_producto.html', {
                    'form': form,
                    'atributos': Atributo.objects.select_related('categoria').all(),
                    'subcategorias': Categoria.objects.filter(padre__isnull=False),
                })

            form.save_m2m()

            # ✅ Guardar valores de atributos
            for key, value in request.POST.items():
                if key.startswith('atributo_') and value.strip():
                    try:
                        atributo_id = int(key.split('_')[1])
                        atributo = Atributo.objects.get(id=atributo_id)
                        ValorAtributo.objects.update_or_create(
                            producto=producto,
                            atributo=atributo,
                            defaults={'valor': value.strip()}
                        )
                    except (ValueError, Atributo.DoesNotExist):
                        continue

            # 🧠 Detectar tipo de código
            producto.tipo_codigo = detectar_tipo_codigo(producto.codigo_barras)
            producto.save()

            # 📦 Registrar inventario inicial
            if cantidad and ubicacion:
                aplicar_movimiento_inventario(
                    producto=producto,
                    cantidad=cantidad,
                    destino=ubicacion,
                    empleado=getattr(request.user, "empleado", None),
                    motivo="nuevo"
                )

            messages.success(request, "Producto registrado correctamente.")
            return redirect('inventario:lista_productos')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = ProductoForm()

    atributos = Atributo.objects.select_related('categoria').all()
    subcategorias = Categoria.objects.filter(padre__isnull=False)

    return render(request, 'inventario/nuevo_producto.html', {
        'form': form,
        'atributos': atributos,
        'subcategorias': subcategorias,
    })

    
    
    
    
#view para verificar si existe inventario de ese producto en esa ubicacion, formulario reactivo
@login_required
def verificar_inventario_existente(request):
    producto_id = request.GET.get('producto')
    ubicacion_id = request.GET.get('ubicacion')

    if producto_id and ubicacion_id:
        existe = Inventario.objects.filter(
            producto_id=producto_id,
            ubicacion_id=ubicacion_id
        ).exists()
        return JsonResponse({'existe': existe})

    return JsonResponse({'existe': False})


    
    
#funcion para buscar productos por codigos y rellenar el formulario de productoForm
@login_required
def buscar_producto_por_codigo(request):
    codigo = request.GET.get('codigo')
    producto = Producto.objects.filter(codigo_barras=codigo).select_related('categoria').first()

    if not producto:
        return JsonResponse({'existe': False})

    # Subcategoría y padre
    subcategoria = producto.categoria
    categoria_padre = subcategoria.padre if subcategoria else None

    # Atributos definidos para la subcategoría
    atributos_definidos = Atributo.objects.filter(categoria=subcategoria) if subcategoria else []
    atributos_list = []
    for atributo in atributos_definidos:
        valor_obj = ValorAtributo.objects.filter(producto=producto, atributo=atributo).first()
        atributos_list.append({
            'id': atributo.id,
            'nombre': atributo.nombre,
            'valor': valor_obj.valor if valor_obj else ''
        })

    return JsonResponse({
        'existe': True,
        'producto_id': producto.id,
        'nombre': producto.nombre,
        'descripcion': producto.descripcion,
        'precio_menudeo': producto.precio_menudeo,
        'precio_mayoreo': producto.precio_mayoreo,
        'precio_docena': producto.precio_docena,
        'tipo_codigo': producto.tipo_codigo,
        'dueño_id': producto.dueño.id if producto.dueño else None,
        'categoria_padre_id': categoria_padre.id if categoria_padre else None,
        'categoria_padre_nombre': categoria_padre.nombre if categoria_padre else None,
        'subcategoria_id': subcategoria.id if subcategoria else None,
        'subcategoria_nombre': subcategoria.nombre if subcategoria else None,
        'atributos': atributos_list,
    })


    
        
@login_required
def categoria_view(request):
    user = request.user
    es_dueno = user.is_superuser or user.groups.filter(name='Dueño').exists()
    es_empleado = hasattr(user, 'empleado')

    if not (es_dueno or es_empleado):
        raise PermissionDenied("No tienes permiso para ver esta página.")

    categorias = Categoria.objects.order_by('padre__nombre', 'nombre')
    form = CategoriaForm() if es_dueno else None  # Solo los dueños ven el formulario

    if request.method == 'POST':
        if not es_dueno:
            raise PermissionDenied("No tienes permiso para modificar categorías.")

        categoria_id = request.POST.get('categoria_id')

        if categoria_id:
            categoria = get_object_or_404(Categoria, id=categoria_id)

            # Si solo se está actualizando la descripción desde el card
            if 'descripcion' in request.POST and 'nombre' not in request.POST:
                categoria.descripcion = request.POST.get('descripcion', '')
                categoria.save()
                messages.success(request, "Descripción actualizada correctamente.")
                return redirect('inventario:categorias')
            else:
                form = CategoriaForm(request.POST, instance=categoria)
        else:
            form = CategoriaForm(request.POST)

        if form and form.is_valid():
            form.save()
            messages.success(request, "Categoría guardada correctamente.")
            return redirect('inventario:categorias')

    return render(request, 'inventario/categorias.html', {
        'categorias': categorias,
        'form': form,
        'solo_lectura': not es_dueno,
        'mostrar_formulario': es_dueno
    })


# Vista para mover productos de un inventario-origen a un inventario-destino
@login_required
def transferir_inventario(request):
    if request.method == 'POST':
        form = TransferenciaInventarioForm(request.POST)
        if form.is_valid():
            transferencia = form.save(commit=False)
            transferencia.realizado_por = getattr(request.user, "empleado", None)

            try:
                transferencia.full_clean()
                transferencia.save()

                # Aplicar movimiento
                aplicar_movimiento_inventario(
                    producto=transferencia.producto,
                    cantidad=transferencia.cantidad,
                    origen=transferencia.origen,
                    destino=transferencia.destino,
                    empleado=transferencia.realizado_por,
                    tipo="transferencia",
                    transferencia=transferencia
                )

                # ⚖️ Verificar stock restante en origen
                try:
                    stock_restante = transferencia.origen.inventarios.get(
                        producto=transferencia.producto
                    ).cantidad_actual
                except transferencia.origen.inventarios.model.DoesNotExist:
                    stock_restante = 0

                # Cantidad actual en destino
                try:
                    destino_inv = transferencia.destino.inventarios.get(
                        producto=transferencia.producto
                    )
                    cantidad_destino = destino_inv.cantidad_actual
                except transferencia.destino.inventarios.model.DoesNotExist:
                    cantidad_destino = transferencia.cantidad

                return JsonResponse({
                    "success": True,
                    "producto_id": transferencia.producto.id,
                    "producto_nombre": transferencia.producto.nombre,
                    "cantidad": cantidad_destino,
                    "origen_id": transferencia.origen.id,
                    "destino_id": transferencia.destino.id,
                    "remove_card": stock_restante == 0,
                    "add_card": True
                })

            except ValidationError as e:
                return JsonResponse({"success": False, "errors": e.messages})

    return JsonResponse({"success": False, "errors": ["Método inválido"]})








#FUNCION PARA AJUSTES DE INVENTARIO SALIDAS POR PERDIDA DAÑOS O ROBO
def ajuste_inventario(request):
    # Lógica para ajustes de inventario
    return render(request, 'inventario/ajuste_inventario.html')



@login_required
def agregar_inventario(request, producto_id, ubicacion_id):
    producto = get_object_or_404(Producto, id=producto_id)
    ubicacion = get_object_or_404(Ubicacion, id=ubicacion_id)

    if request.method == "POST":
        form = AgregarInventarioForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            try:
                aplicar_movimiento_inventario(
                    producto=producto,
                    cantidad=cantidad,
                    destino=ubicacion,
                    empleado=getattr(request.user, "empleado", None),
                    motivo="reabastecimiento"
                )
                # Mensaje global
                messages.success(
                    request,
                    f"{cantidad} piezas agregadas a {producto.nombre} en {ubicacion.nombre}."
                )
            except ValidationError as e:
                messages.error(request, str(e))

            # Al guardar: regresar al Kanban (lista_productos) y marcar el producto actualizado
            return redirect(
                f"{reverse('inventario:lista_productos')}?updated={producto.id}&cantidad={cantidad}"
            )
    else:
        cantidad_inicial = request.session.pop('cantidad_inicial', None)
        form = AgregarInventarioForm(initial={'cantidad': cantidad_inicial} if cantidad_inicial else None)

    inventario = Inventario.objects.filter(producto=producto, ubicacion=ubicacion).first()
    return render(request, "inventario/agregar_inventario.html", {
        "form": form,
        "producto": producto,
        "ubicacion": ubicacion,
        "inventario": inventario,
    })


    


@login_required
def dashboard_inventario(request):
    productos_total = Producto.objects.count()
    stock_total = Inventario.objects.aggregate(total=Sum('cantidad_actual'))['total'] or 0
    ubicaciones = Ubicacion.objects.all()

    # 1) Leer el parámetro exacto que manda el select
    ubicacion_id = request.GET.get("ubicacion_id")
    ubicacion_seleccionada = None

    # 2) Base queryset (solo críticos). Ajusta el umbral si quieres
    bajos_qs = Inventario.objects.filter(cantidad_actual__lt=100)

    # 3) Si hay filtro, aplicar
    if ubicacion_id:
        # Opcional: castear a int para evitar sorpresas de comparación
        try:
            ubicacion_id_int = int(ubicacion_id)
        except (TypeError, ValueError):
            ubicacion_id_int = None

        if ubicacion_id_int:
            ubicacion_seleccionada = get_object_or_404(Ubicacion, id=ubicacion_id_int)
            bajos_qs = bajos_qs.filter(ubicacion=ubicacion_seleccionada)

    # 4) Menor rotación (esto no depende de ubicación, salvo que quieras filtrarlo también)
    menos_rotacion = Producto.objects.annotate(
        movimientos_count=Count('movimientos')
    ).order_by('movimientos_count')[:10]

    context = {
        "productos_total": productos_total,
        "stock_total": stock_total,
        "ubicaciones": ubicaciones,
        "ubicacion_seleccionada": ubicacion_seleccionada,
        "bajos": bajos_qs,
        "menos_rotacion": menos_rotacion,
    }
    return render(request, "inventario/dashboard_inventario.html", context)



@login_required
def exportar_criticos(request):
    usuario = request.user.get_full_name() or request.user.username
    ubicacion_id = request.GET.get("ubicacion_id")

    if ubicacion_id:
        try:
            ubicacion_id_int = int(ubicacion_id)
        except (TypeError, ValueError):
            ubicacion_id_int = None
    else:
        ubicacion_id_int = None

    return reports.exportar_criticos_pdf(usuario, ubicacion_id_int)




#view para ver todos los productos en producto/
@login_required
def lista_productos(request):
    # Base queryset con relaciones optimizadas
    productos = Producto.objects.select_related(
        'registrado_por__user',
        'dueño__user',
        'categoria',
        'categoria__padre'
    ).prefetch_related('inventarios__ubicacion', 'temporada').all()

    # Filtros GET
    dueño_id = request.GET.get('dueño')
    registrado_por_id = request.GET.get('usuario')
    categoria_padre_id = request.GET.get('categoria_padre')
    subcategoria_id = request.GET.get('subcategoria')
    precio_tipo = request.GET.get('precio_tipo')
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')

    if dueño_id:
        productos = productos.filter(dueño__id=dueño_id)
    if registrado_por_id:
        productos = productos.filter(registrado_por__id=registrado_por_id)
    if subcategoria_id:
        productos = productos.filter(categoria__id=subcategoria_id)
    if categoria_padre_id:
        productos = productos.filter(categoria__padre__id=categoria_padre_id)
    if precio_tipo in ['menudeo', 'mayoreo', 'docena']:
        if precio_min:
            productos = productos.filter(**{f'precio_{precio_tipo}__gte': precio_min})
        if precio_max:
            productos = productos.filter(**{f'precio_{precio_tipo}__lte': precio_max})

    # Datos para filtros
    empleados = Empleado.objects.select_related('user').all()
    dueños = empleados.filter(rol='dueño')
    registradores = empleados.exclude(rol='dueño')
    categorias_padre = Categoria.objects.filter(padre__isnull=True)
    subcategorias = Categoria.objects.filter(padre__isnull=False)

    # Ubicaciones necesarias para el drag & drop
    piso = Ubicacion.objects.get(nombre="Piso")
    bodega_interna = Ubicacion.objects.get(nombre="Bodega Interna")
    moderna = Ubicacion.objects.get(nombre="Moderna")

    return render(request, 'inventario/productos.html', {
        'productos': productos,
        'empleados': empleados,
        'dueños': dueños,
        'registradores': registradores,
        'categorias_padre': categorias_padre,
        'subcategorias': subcategorias,
        'ubicacion_piso': piso,
        'ubicacion_bodega_interna': bodega_interna,
        'ubicacion_moderna': moderna,
    })

    



@login_required
def reportes(request):
    filtros = reports.parse_filtros(request)
    tipo_reporte = filtros.get('tipo', '')

    inventario, movimientos, resumen = [], [], []

    if tipo_reporte == 'general':
        inventario = reports.get_datos_reporte(
            tipo_reporte,
            categoria_id=filtros.get('categoria'),
            subcategoria_id=filtros.get('subcategoria'),
            temporada_id=filtros.get('temporada'),
            ubicacion_id=filtros.get('ubicacion'),
            dueño_id=filtros.get('dueño')
        )

    elif tipo_reporte == 'movimientos':
        movimientos = reports.get_datos_reporte(
            tipo_reporte,
            categoria_id=filtros.get('categoria'),
            subcategoria_id=filtros.get('subcategoria'),
            temporada_id=filtros.get('temporada'),
            movimiento_tipo=filtros.get('movimiento')
        )
        resumen = reports.resumen_movimientos(
            filtros.get('categoria'),
            filtros.get('subcategoria'),
            filtros.get('temporada'),
            filtros.get('dueño')
        )

    filtros_nombres = reports.nombres_filtros(filtros)
    contexto = {
        'tipo_reporte': tipo_reporte,
        'filtro_movimiento': filtros.get('movimiento'),
        'filtro_ubicacion': filtros.get('ubicacion'),
        'filtro_categoria': filtros.get('categoria'),
        'filtro_subcategoria': filtros.get('subcategoria'),
        'filtro_temporada': filtros.get('temporada'),
        'filtro_dueño': filtros.get('dueño'),   # ✅ con acento
        'ubicacion_nombre': filtros_nombres.get("ubicacion"),
        'categoria_nombre': filtros_nombres.get("categoria"),
        'subcategoria_nombre': filtros_nombres.get("subcategoria"),
        'temporada_nombre': filtros_nombres.get("temporada"),
        'dueño_nombre': filtros_nombres.get("dueño"),   # ✅ con acento
        'ubicaciones': reports.Ubicacion.objects.all(),
        'categorias_padre': reports.Categoria.objects.filter(padre__isnull=True).order_by('nombre'),
        'subcategorias_para_padre': reports.Categoria.objects.filter(
            padre_id=filtros.get('categoria')
        ).order_by('nombre') if filtros.get('categoria') else [],
        'temporadas': reports.Temporada.objects.all(),
        'dueños': reports.Empleado.objects.filter(rol='dueño'),  # revisa si tu modelo guarda con acento
        'inventario': inventario,
        'movimientos': movimientos,
        'resumen': resumen,
        'total_global': reports.total_global(
            filtros.get('categoria'),
            filtros.get('subcategoria'),
            filtros.get('temporada'),
            filtros.get('dueño')
        ),
    }
    return render(request, 'inventario/reportes.html', contexto)






@login_required
def api_categorias(request):
    """
    Devuelve:
    - categorias_padre: lista de categorías raíz con sus subcategorías
      [{id, nombre, subcategorias:[{id,nombre}]}]
    """
    # Categorías padre
    padres = Categoria.objects.filter(padre__isnull=True).order_by('nombre')

    # Subcategorías
    subqs = Categoria.objects.filter(padre__isnull=False).order_by('nombre')
    subs_por_padre = {}
    for s in subqs:
        subs_por_padre.setdefault(s.padre_id, []).append({
            'id': s.id,
            'nombre': s.nombre
        })

    categorias_data = []
    for p in padres:
        categorias_data.append({
            'id': p.id,
            'nombre': p.nombre,
            'subcategorias': subs_por_padre.get(p.id, [])
        })

    return JsonResponse({'categorias_padre': categorias_data})



@login_required
def reporte_pdf(request):
    filtros = reports.parse_filtros(request)
    tipo_reporte = filtros.get('tipo', '')
    usuario = request.user.get_full_name() or request.user.username

    # Asegúrate de que 'filtros' contenga todos los campos relevantes:
    # categoria, subcategoria, temporada, ubicacion, dueno, movimiento
    return reports.generar_pdf(
        tipo_reporte,
        filtros,   # aquí ya van todos los filtros
        usuario
    )


@login_required
def seleccionar_etiqueta_temp(request):
    etiquetas = [
        {"nombre": "Pequeña", "tamaño": "50x20 mm", "tipo": "chica", "descripcion": "Ideal para empaques pequeños"},
        {"nombre": "Mediana", "tamaño": "100x30 mm", "tipo": "mediana", "descripcion": "Para cajas medianas o productos estándar"},
        {"nombre": "Grande", "tamaño": "135x32 mm", "tipo": "grande", "descripcion": "Para empaques grandes o logísticos"},
    ]

    if request.method == "POST":
        tamaño = request.POST.get("tipo_codigo")
        pendiente = request.session.get("pendiente_producto")
        inventario_pendiente = request.session.get("pendiente_inventario")
        has_file = request.session.get("pendiente_has_file", False)

        if not pendiente:
            messages.error(request, "No hay datos de producto pendientes.")
            return redirect("inventario:nuevo_producto")

        # 🆕 Crear producto directamente con los datos de sesión
        producto = Producto(
            nombre=pendiente.get("nombre"),
            descripcion=pendiente.get("descripcion"),
            precio_menudeo=pendiente.get("precio_menudeo") or 0,
            precio_mayoreo=pendiente.get("precio_mayoreo") or 0,
            precio_docena=pendiente.get("precio_docena") or 0,
            registrado_por=getattr(request.user, "empleado", None),
        )

        # Dueño → empleado con rol dueño seleccionado en el formulario
        dueño_id = pendiente.get("dueño")
        if dueño_id:
            try:
                producto.dueño_id = int(dueño_id)
            except (ValueError, TypeError):
                producto.dueño_id = None

        # 🔍 Asociar subcategoría explícitamente usando el ID guardado
        subcategoria_id = pendiente.get("categoria") or pendiente.get("categoria_id") or pendiente.get("subcategoria")
        if subcategoria_id:
            try:
                producto.categoria = Categoria.objects.filter(id=int(subcategoria_id)).first()
            except (ValueError, TypeError):
                producto.categoria = None

        # ⚠️ Si había archivo, lo tomamos de request.FILES
        if has_file and request.FILES:
            producto.foto_url = request.FILES.get("imagen")

        producto.save()

        # 🔑 Generar código de barras
        codigo, clase_barcode, tipo_str = generar_codigo(producto.id or 0, tamaño)
        producto.codigo_barras = codigo
        producto.tipo_codigo = tipo_str
        producto.save()

        # ✅ Guardar valores de atributos
        for key, value in pendiente.get("atributos", {}).items():
            if key.startswith("atributo_") and value.strip():
                try:
                    atributo_id = int(key.split("_")[1])
                    atributo = Atributo.objects.get(id=atributo_id)
                    ValorAtributo.objects.update_or_create(
                        producto=producto,
                        atributo=atributo,
                        defaults={"valor": value.strip()}
                    )
                except (ValueError, Atributo.DoesNotExist):
                    continue

        # 📦 Inventario inicial
        if inventario_pendiente:
            cantidad = inventario_pendiente.get("cantidad")
            ubicacion_id = inventario_pendiente.get("ubicacion_id")
            if cantidad and ubicacion_id:
                ubicacion = Ubicacion.objects.filter(id=ubicacion_id).first()
                if ubicacion:
                    aplicar_movimiento_inventario(
                        producto=producto,
                        cantidad=int(cantidad),
                        destino=ubicacion,
                        empleado=getattr(request.user, "empleado", None),
                        motivo="nuevo"
                    )

        messages.success(request, "Producto registrado y etiqueta asignada correctamente.")
        return redirect("inventario:lista_productos")

    return render(request, "inventario/seleccionar_etiqueta.html", {"etiquetas": etiquetas})

    
    
def codigo_base64(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if producto.codigo_barras and producto.tipo_codigo:
        # Selecciona la clase correcta
        clase = EAN13 if producto.tipo_codigo == 'ean13' else Code128
        imagen_base64 = generar_base64(producto.codigo_barras, clase)
        return JsonResponse({'imagen': imagen_base64})
    else:
        return JsonResponse({'imagen': None})