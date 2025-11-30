from django.core.exceptions import ValidationError
from .models import Inventario, MovimientoInventario, TransferenciaInventario
import random
import io
import base64
from barcode import EAN13, Code128
from barcode.writer import ImageWriter
from django.db import transaction



#Funcion que solo actualiza el stock de inventario
def actualizar_stock(inventario, *, sumar=0, restar=0, ajustar=None):
    # Validar exclusividad de parámetros
    if ajustar is not None and (sumar or restar):
        raise ValidationError("No se puede usar 'ajustar' junto con 'sumar' o 'restar'.")

    if ajustar is not None:
        if ajustar < 0:
            raise ValidationError("No puedes ajustar el inventario a un valor negativo.")
        inventario.cantidad_actual = ajustar
    else:
        nuevo = inventario.cantidad_actual + sumar - restar
        if nuevo < 0:
            raise ValidationError("La operación dejaría el inventario en negativo.")
        inventario.cantidad_actual = nuevo

    inventario.save()
    return inventario




#RFuncion que registra el movimiento de inventario-
def registrar_movimiento(producto, cantidad, origen=None, destino=None, empleado=None, motivo=None, tipo=None, transferencia=None):
    return MovimientoInventario.objects.create(
        producto=producto,
        motivo=motivo,
        tipo=tipo,
        cantidad=cantidad,
        origen=origen,
        destino=destino,
        realizado_por=empleado,
        transferencia=transferencia   # 👈 vínculo al maestro
    )


def aplicar_movimiento_inventario(*, producto, cantidad, origen=None, destino=None, empleado=None, motivo=None, tipo=None, transferencia=None):
    try:
        cantidad = int(cantidad)
    except (ValueError, TypeError):
        raise ValidationError("La cantidad debe ser un número entero válido.")
    if cantidad <= 0:
        raise ValidationError("La cantidad debe ser mayor que cero.")

    # Deducir tipo automáticamente según motivo (si existe)
    if motivo:
        tipo = MovimientoInventario.MAPEO_TIPO_POR_MOTIVO.get(motivo)
        if not tipo:
            raise ValidationError(f"El motivo '{motivo}' no es válido.")

    with transaction.atomic():
        if tipo == "entrada":
            inv_dest, _ = Inventario.objects.get_or_create(producto=producto, ubicacion=destino)
            inv_dest = Inventario.objects.select_for_update().get(pk=inv_dest.pk)
            actualizar_stock(inv_dest, sumar=cantidad)
            registrar_movimiento(producto, cantidad, destino=destino, empleado=empleado, motivo=motivo, tipo=tipo, transferencia=transferencia)
            return inv_dest

        elif tipo == "salida":
            inv_orig = Inventario.objects.select_for_update().filter(producto=producto, ubicacion=origen).first()
            if not inv_orig or inv_orig.cantidad_actual < cantidad:
                raise ValidationError("Inventario insuficiente para realizar la salida.")
            actualizar_stock(inv_orig, restar=cantidad)
            registrar_movimiento(producto, cantidad, origen=origen, empleado=empleado, motivo=motivo, tipo=tipo, transferencia=transferencia)
            return inv_orig

        elif tipo == "ajuste":
            inv_dest, _ = Inventario.objects.get_or_create(producto=producto, ubicacion=destino)
            inv_dest = Inventario.objects.select_for_update().get(pk=inv_dest.pk)
            actualizar_stock(inv_dest, ajustar=cantidad)
            registrar_movimiento(producto, cantidad, destino=destino, empleado=empleado, motivo=motivo, tipo=tipo, transferencia=transferencia)
            return inv_dest

        elif tipo == "transferencia":
            # Bloquear inventario origen
            inv_orig = Inventario.objects.select_for_update().filter(producto=producto, ubicacion=origen).first()
            if not inv_orig or inv_orig.cantidad_actual < cantidad:
                raise ValidationError("Inventario insuficiente en la ubicación de origen.")
            actualizar_stock(inv_orig, restar=cantidad)

            # Bloquear/crear inventario destino
            inv_dest, _ = Inventario.objects.get_or_create(producto=producto, ubicacion=destino)
            inv_dest = Inventario.objects.select_for_update().get(pk=inv_dest.pk)
            actualizar_stock(inv_dest, sumar=cantidad)

            # Registrar salida en origen
            registrar_movimiento(
                producto, cantidad,
                origen=origen,
                empleado=empleado,
                tipo="salida",
                transferencia=transferencia
            )

            # Registrar entrada en destino
            registrar_movimiento(
                producto, cantidad,
                destino=destino,
                empleado=empleado,
                tipo="entrada",
                transferencia=transferencia
            )

            return inv_orig, inv_dest



    
    
#Funciones para la generacion y manejo de codigo de barras
def generar_codigo(producto_id, tamaño):
    """
    Genera un código de barras y su clase según el tamaño de etiqueta.
    """
    if tamaño == 'chica':
        codigo = f"{producto_id:06d}{random.randint(100,999)}"
        clase = Code128
        tipo_str = 'code128'
    elif tamaño == 'mediana':
        codigo = f"{producto_id:06d}{random.randint(1000,9999)}"
        clase = Code128
        tipo_str = 'code128'
    elif tamaño == 'grande':
        # Genera un número de 12 dígitos para EAN13
        codigo = f"{producto_id:06d}{random.randint(100000,999999)}"  # 6 + 6 = 12 dígitos
        clase = EAN13
        tipo_str = 'ean13'
    return codigo, clase, tipo_str


def generar_base64(codigo, clase_barcode):
    """
    Genera una imagen PNG del código de barras y la devuelve en base64.
    """
    buffer = io.BytesIO()
    barcode = clase_barcode(codigo, writer=ImageWriter())
    barcode.write(buffer)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')



def detectar_tipo_codigo(codigo):
    """
    Detecta el tipo de código de barras según el formato ingresado.
    """
    if len(codigo) == 13 and codigo.isdigit():
        return 'ean13'
    elif codigo.isalnum() and len(codigo) <= 20:
        return 'code128'
    else:
        return 'code128'  # fallback seguro
