from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from tienda import views as tienda_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Página principal (landing)
    path('', TemplateView.as_view(template_name='tienda/landing.html'), name='landing'),

    # Admin
    path('admin/', admin.site.urls),

    # Rutas de la app tienda
    path('tienda/', include('tienda.urls')),

    # Vistas públicas desde tienda/views.py
    path('contacto/', tienda_views.contacto, name='contacto'),
    path('about-us/', tienda_views.aboutus, name='about-us'),

    # Otras apps (actívalas cuando estén listas)
    path('inventario/', include('inventario.urls')),
    # path('ventas/', include('ventas.urls')),
    path('configuracion/', tienda_views.configuracion_perfil, name='profile_settings'),
    
]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Personalización del panel de administración
admin.site.site_header = "Administración de tienda"
admin.site.site_title = "Tienda"
