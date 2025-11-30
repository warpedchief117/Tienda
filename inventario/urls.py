from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('categorias/', views.categoria_view, name='categorias'),
    path('nuevo_producto/', views.nuevo_producto, name='nuevo_producto'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/pdf/', views.reporte_pdf, name='reporte_pdf'),
    path('producto/<int:producto_id>/codigo_base64/', views.codigo_base64, name='codigo_base64'),
    path('seleccionar_etiqueta_temp/', views.seleccionar_etiqueta_temp, name='seleccionar_etiqueta_temp'),
    path('buscar_producto/', views.buscar_producto_por_codigo, name='buscar_producto'),    
    path('verificar_inventario/', views.verificar_inventario_existente, name='verificar_inventario'),
    path('agregar_inventario/<int:producto_id>/<int:ubicacion_id>/',views.agregar_inventario, name='agregar_inventario'),
    path('dashboard-inventario/', views.dashboard_inventario, name='dashboard_inventario'),
    path('transferir_inventario/', views.transferir_inventario, name='transferir_inventario'), 
    path('ajuste-inventario' , views.ajuste_inventario, name='ajustes'),  
    # urls.py
    path('exportar-criticos/', views.exportar_criticos, name='exportar_criticos'),
    path('api/categorias/', views.api_categorias, name='api_categorias'),
]

