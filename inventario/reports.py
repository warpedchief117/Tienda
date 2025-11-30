from django.db.models import Sum, F
from .models import Producto, Inventario, MovimientoInventario
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm 
from datetime import datetime
from django.http import HttpResponse
from django.contrib.postgres.aggregates import ArrayAgg
from .models import Categoria, Atributo, Producto, ValorAtributo, Ubicacion, Empleado, Inventario, Temporada, MovimientoInventario


# -----------------------------
# Helper para filtros
# -----------------------------
def filtrar_productos(categoria_id=None, subcategoria_id=None,
                      temporada_id=None, dueño_id=None):
    """
    Devuelve un queryset de productos filtrado según los parámetros recibidos.
    - categoria_id: ID de la categoría padre
    - subcategoria_id: ID de la subcategoría
    - temporada_id: ID de la temporada (M2M)
    - dueño_id: ID del dueño (Empleado)
    """

    qs = (
        Producto.objects
        .select_related("categoria", "dueño")   # relaciones directas
        .prefetch_related("temporada")          # relación M2M
    )

    # Filtrar por categoría padre
    if categoria_id:
        qs = qs.filter(categoria__padre_id=categoria_id)

    # Filtrar por subcategoría
    if subcategoria_id:
        qs = qs.filter(categoria_id=subcategoria_id)

    # Filtrar por temporada (M2M)
    if temporada_id:
        qs = qs.filter(temporada__id=temporada_id)

    # Filtrar por dueño
    if dueño_id:
        qs = qs.filter(dueño_id=dueño_id)

    return qs.distinct()


def parse_filtros(request):
    """
    Extrae filtros desde request.GET y devuelve un diccionario
    con las claves esperadas por nombres_filtros y get_datos_reporte.
    Convierte a int los valores que representan IDs si son válidos.
    """

    def to_int(value):
        try:
            return int(value) if int(value) > 0 else None
        except (ValueError, TypeError):
            return None

    # Tipo de reporte: solo aceptamos los definidos
    tipo = (request.GET.get("tipo") or "general").strip()
    if tipo not in {"general", "movimientos", "resumen_movimientos"}:
        tipo = "general"

    return {
        "ubicacion": to_int(request.GET.get("ubicacion")),       # FK → Ubicacion.id
        "categoria": to_int(request.GET.get("categoria")),       # FK → Categoria.id (padre)
        "subcategoria": to_int(request.GET.get("subcategoria")), # FK → Categoria.id (hija)
        "temporada": to_int(request.GET.get("temporada")),       # FK → Temporada.id (M2M)
        "dueño": to_int(request.GET.get("dueño")),               # FK → Empleado.id
        "movimiento": (request.GET.get("movimiento") or "").strip(),  # campo tipo/motivo en MovimientoInventario
        "tipo": tipo,
    }



# -----------------------------
# Servicios de reportes
# -----------------------------


def inventario_general(categoria_id=None, subcategoria_id=None,
                       temporada_id=None, dueño_id=None, ubicacion_id=None):
    # Filtrar productos según los parámetros
    productos = filtrar_productos(categoria_id, subcategoria_id, temporada_id, dueño_id)

    inventario = (
        Inventario.objects
        .filter(producto__in=productos)
        .select_related("producto__categoria__padre", "producto__dueño", "ubicacion")
        .prefetch_related("producto__temporada")
    )

    # ✅ aplicar filtro de ubicación si está presente
    if ubicacion_id:
        inventario = inventario.filter(ubicacion_id=ubicacion_id)

    qs = (
        inventario
        .values(
            "producto_id",   # FK real en Inventario
            "ubicacion_id",  # FK real en Inventario
            producto_nombre=F("producto__nombre"),
            dueño_nombre=F("producto__dueño__user__username"),
            categoria_nombre=F("producto__categoria__padre__nombre"),
            subcategoria_nombre=F("producto__categoria__nombre"),
            ubicacion_nombre=F("ubicacion__nombre"),
        )
        .annotate(total=Sum("cantidad_actual"))   # campo real en Inventario
        .order_by("producto__nombre")
    )

    # Resolver temporadas sin N+1
    producto_map = {
        p.id: ", ".join([t.nombre for t in p.temporada.all()]) or "N/A"
        for p in productos
    }
    for item in qs:
        item["temporada_nombres"] = producto_map.get(item["producto_id"], "N/A")

    return qs







def movimientos_por_tipo(tipo=None, categoria_id=None, subcategoria_id=None,
                         temporada_id=None, dueño_id=None):
    # Filtrar productos según los parámetros
    productos = filtrar_productos(categoria_id, subcategoria_id, temporada_id, dueño_id)

    queryset = (
        MovimientoInventario.objects
        .filter(producto__in=productos)
        .select_related(
            "producto__categoria__padre",
            "producto__dueño__user",
            "origen",
            "destino"
        )
        .prefetch_related("producto__temporada")
    )

    # Filtro por tipo de movimiento (entrada, salida, ajuste, transferencia)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
        
    qs = (
        queryset
        .values(
            "producto_id",
            "tipo",       # campo directo
            "motivo",     # campo directo
            "cantidad",   # campo directo
            "fecha",      # campo directo
            producto_nombre=F("producto__nombre"),
            dueño_nombre=F("producto__dueño__user__username"),
            categoria_nombre=F("producto__categoria__padre__nombre"),
            subcategoria_nombre=F("producto__categoria__nombre"),
            origen_nombre=F("origen__nombre"),
            destino_nombre=F("destino__nombre"),
        )

        .order_by("-fecha")
    )


    # Resolver temporadas sin N+1
    producto_map = {
        p.id: ", ".join([t.nombre for t in p.temporada.all()]) or "N/A"
        for p in productos
    }
    for item in qs:
        item["temporada_nombres"] = producto_map.get(item["producto_id"], "N/A")

    return qs


def resumen_movimientos(categoria_id=None, subcategoria_id=None,
                        temporada_id=None, dueño_id=None):
    productos = filtrar_productos(categoria_id, subcategoria_id, temporada_id, dueño_id)

    movimientos = (
        MovimientoInventario.objects
        .filter(producto__in=productos)
        .select_related(
            'producto__categoria__padre',
            'producto__dueño'
        )
        .prefetch_related('producto__temporada')
    )

    qs = (
        movimientos
        .values(
            'tipo',                                # campo real en MovimientoInventario
            'producto__id',                        # id del producto
            'producto__nombre',                    # nombre del producto
            'producto__categoria__padre__nombre',  # categoría padre
            'producto__categoria__nombre',         # subcategoría
            "producto__dueño__user__username",             # nombre del dueño (ajusta al campo real en Empleado)
        )
        .annotate(total=Sum('cantidad'))           # cantidad real del modelo
        .order_by('tipo')
    )

    # Resolver temporadas sin N+1
    producto_map = {
        p.id: ", ".join([t.nombre for t in p.temporada.all()]) or "N/A"
        for p in productos
    }
    for item in qs:
        item["temporada_nombres"] = producto_map.get(item["producto__id"], "N/A")
    return qs


def total_global(categoria_id=None, subcategoria_id=None,
                 temporada_id=None, dueño_id=None):
    productos = filtrar_productos(categoria_id, subcategoria_id, temporada_id, dueño_id)
    inventario = Inventario.objects.filter(producto__in=productos)
    return inventario.aggregate(total=Sum('cantidad_actual'))['total'] or 0




# -----------------------------
# Dispatcher central
# -----------------------------
def get_datos_reporte(tipo,
                      categoria_id=None,
                      subcategoria_id=None,
                      temporada_id=None,
                      ubicacion_id=None,
                      dueño_id=None,
                      movimiento_tipo=None):
    """
    Dispatcher central de reportes.
    Según el tipo, llama a la función correspondiente en reports.py
    """

    if tipo == 'general':
        # Inventario general con filtros de categoría, subcategoría, temporada, dueño y ubicación
        return inventario_general(
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
            temporada_id=temporada_id,
            dueño_id=dueño_id,
            ubicacion_id=ubicacion_id
        )

    elif tipo == 'movimientos':
        # Movimientos filtrados por tipo, categoría, subcategoría, temporada y dueño
        return movimientos_por_tipo(
            tipo=movimiento_tipo,
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
            temporada_id=temporada_id,
            dueño_id=dueño_id
        )

    elif tipo == 'resumen_movimientos':
        # Resumen de movimientos agrupados por tipo
        return resumen_movimientos(
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id,
            temporada_id=temporada_id,
            dueño_id=dueño_id
        )

    # Si no coincide con ninguno, devuelve lista vacía
    return []




def nombres_filtros(filtros):
    """
    Convierte los IDs de filtros en nombres legibles usando los modelos reales.
    Si no encuentra el registro, devuelve 'Desconocido'.
    """

    resultado = {
        "ubicacion": None,
        "categoria": None,
        "subcategoria": None,
        "temporada": None,
        "dueño": None,
    }

    if filtros.get("ubicacion"):
        resultado["ubicacion"] = Ubicacion.objects.filter(
            id=filtros["ubicacion"]
        ).values_list("nombre", flat=True).first() or "Desconocido"

    if filtros.get("categoria"):
        resultado["categoria"] = Categoria.objects.filter(
            id=filtros["categoria"]
        ).values_list("nombre", flat=True).first() or "Desconocido"

    if filtros.get("subcategoria"):
        resultado["subcategoria"] = Categoria.objects.filter(
            id=filtros["subcategoria"]
        ).values_list("nombre", flat=True).first() or "Desconocido"

    if filtros.get("temporada"):
        resultado["temporada"] = Temporada.objects.filter(
            id=filtros["temporada"]
        ).values_list("nombre", flat=True).first() or "Desconocido"

    if filtros.get("dueño"):
        resultado["dueño"] = Empleado.objects.filter(
            id=filtros["dueño"]
        ).values_list("user__first_name", flat=True).first() or "Desconocido"

    return resultado







def generar_pdf(tipo_reporte, filtros, usuario):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo_reporte}.pdf"'

    pagesize = landscape(A4) if tipo_reporte == "movimientos" else A4
    p = canvas.Canvas(response, pagesize=pagesize)
    width, height = pagesize
    pagina = 1

    # --- Encabezado con logo y metadatos ---
    logo_path = "static/img/logotienda.png"
    try:
        p.drawImage(logo_path, 50, height - 80, width=60, height=60,
                    preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    p.setFont("Helvetica-Bold", 16)
    p.drawRightString(width - 50, height - 50, "Comercializadora Modelo")

    p.setFont("Helvetica", 10)
    p.drawRightString(width - 50, height - 70, f"Reporte generado por: {usuario}")
    p.drawRightString(width - 50, height - 85, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    filtros_nombres = nombres_filtros(filtros)

    # --- Mensajes informativos según filtros ---
    p.setFont("Helvetica-Oblique", 10)
    y_info = height - 120
    mensajes = []
    if filtros_nombres.get("temporada"):
        mensajes.append(f"de la temporada {filtros_nombres['temporada']}")
    if filtros_nombres.get("ubicacion"):
        mensajes.append(f"en la ubicación {filtros_nombres['ubicacion']}")
    if filtros_nombres.get("categoria"):
        mensajes.append(f"de la categoría {filtros_nombres['categoria']}")
    if filtros_nombres.get("subcategoria"):
        mensajes.append(f"de la subcategoría {filtros_nombres['subcategoria']}")
    if filtros_nombres.get("dueño"):
        mensajes.append(f"del dueño {filtros_nombres['dueño']}")

    if mensajes:
        texto = "Estos productos son " + ", ".join(mensajes)
        p.drawString(50, y_info, texto)

    # --- Helpers internos ---
    y = height - 190
    def nueva_pagina():
        nonlocal y, pagina
        p.setFont("Helvetica", 9)
        p.drawRightString(width - 30, 20, f"Página {pagina}")
        p.showPage()
        pagina += 1
        y = height - 100

    def dibujar_fila(celdas, negrita=False):
        nonlocal y
        if y < 80:
            nueva_pagina()
        p.setFont("Helvetica-Bold" if negrita else "Helvetica", 9)
        x = 50
        ancho_disponible = width - 100
        ancho_columna = ancho_disponible / len(celdas)
        for texto in celdas:
            p.rect(x, y, ancho_columna, 15, stroke=1, fill=0)
            p.drawString(x + 2, y + 3, str(texto))
            x += ancho_columna
        y -= 15

    # --- Datos del reporte ---
    datos = get_datos_reporte(
        tipo_reporte,
        categoria_id=filtros.get("categoria"),
        subcategoria_id=filtros.get("subcategoria"),
        temporada_id=filtros.get("temporada"),
        ubicacion_id=filtros.get("ubicacion"),
        dueño_id=filtros.get("dueño"),
        movimiento_tipo=filtros.get("movimiento")
    )

    # --- Renderizado según tipo ---
    if tipo_reporte in ["general", "movimientos"]:
        columnas = ["Producto"]
        if tipo_reporte == "movimientos" and not filtros.get("movimiento"):
            columnas.append("Tipo")
        if not filtros.get("dueño"):
            columnas.append("Dueño")
        if not filtros.get("categoria"):
            columnas.append("Categoría")
        if not filtros.get("subcategoria"):
            columnas.append("Subcategoría")
        if not filtros.get("temporada"):
            columnas.append("Temporada")
        if not filtros.get("ubicacion") and tipo_reporte == "general":
            columnas.append("Ubicación")

        columnas.append("Cantidad")
        if tipo_reporte == "movimientos":
            columnas += ["Origen", "Destino", "Fecha"]

        dibujar_fila(columnas, negrita=True)

        for item in datos:
            fila = [item.get("producto_nombre", "N/A")]
            if tipo_reporte == "movimientos" and not filtros.get("movimiento"):
                fila.append(item.get("tipo", "N/A"))
            if not filtros.get("dueño"):
                fila.append(item.get("dueño_nombre", "N/A"))
            if not filtros.get("categoria"):
                fila.append(item.get("categoria_nombre", "N/A"))
            if not filtros.get("subcategoria"):
                fila.append(item.get("subcategoria_nombre", "N/A"))
            if not filtros.get("temporada"):
                fila.append(item.get("temporada_nombres", "N/A"))
            if not filtros.get("ubicacion") and tipo_reporte == "general":
                fila.append(item.get("ubicacion_nombre", "N/A"))

            # Cantidad
            if tipo_reporte == "general":
                fila.append(item.get("total", 0))
            else:  # movimientos
                fila.append(item.get("cantidad", 0))

            if tipo_reporte == "movimientos":
                fecha = item.get("fecha")
                fila += [
                    item.get("origen_nombre", "-"),
                    item.get("destino_nombre", "-"),
                    fecha.strftime("%d/%m/%Y %H:%M") if isinstance(fecha, datetime) else "-"
                ]
            dibujar_fila(fila)

    p.save()
    return response



def exportar_criticos_pdf(usuario, ubicacion_id=None):
    criticos = Inventario.objects.filter(cantidad_actual__lte=100)
    if ubicacion_id:
        criticos = criticos.filter(ubicacion_id=ubicacion_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="productos_bajo_stock.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    pagina = 1
    y = height - 100

    # --- Encabezado con logo ---
    logo_path = "static/img/logotienda.png"
    try:
        p.drawImage(logo_path, 50, height - 80, width=60, height=60,
                    preserveAspectRatio=True, mask='auto')
    except:
        pass

    p.setFont("Helvetica-Bold", 16)
    p.drawRightString(width - 50, height - 50, "Comercializadora Modelo")

    p.setFont("Helvetica", 10)
    p.drawRightString(width - 50, height - 70, f"Reporte generado por: {usuario}")
    p.drawRightString(width - 50, height - 85, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if ubicacion_id:
        ubicacion = Ubicacion.objects.filter(id=ubicacion_id).first()
        if ubicacion:
            p.drawRightString(width - 50, height - 100, f"Ubicación: {ubicacion.nombre}")

    # --- Tabla de críticos ---
    y = height - 160
    def nueva_pagina():
        nonlocal y, pagina
        p.setFont("Helvetica", 9)
        p.drawRightString(width - 30, 20, f"Página {pagina}")
        p.showPage()
        pagina += 1
        y = height - 100

    def dibujar_fila(celdas, anchos, negrita=False):
        nonlocal y
        if y < 80:
            nueva_pagina()
        p.setFont("Helvetica-Bold" if negrita else "Helvetica", 9)
        x = 50
        for texto, ancho in zip(celdas, anchos):
            p.rect(x, y, ancho, 15, stroke=1, fill=0)
            p.drawString(x + 2, y + 3, str(texto))
            x += ancho
        y -= 15

    # Encabezados
    dibujar_fila(["Producto", "Stock actual", "Ubicación"], [200, 100, 200], negrita=True)

    # Filas
    for inv in criticos:
        dibujar_fila([inv.producto.nombre, inv.cantidad_actual, inv.ubicacion.nombre],
                     [200, 100, 200])

    p.showPage()
    p.save()
    return response


