"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from Tienda import views


urlpatterns = [
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('admin/', admin.site.urls),
    path('tienda/', include('Tienda.urls')),# Include the URLs from the Tienda app
    path('contacto/', views.contacto, name='contacto'), 
    path('about-us/', views.aboutus, name='about-us'), 
    #path('inventario/', include('Inventario.urls')), # Uncomment if you have an Inventario app
    #path('inventario/', include('Inventario.urls')),# Include the URLs from the Inventario app
    #path('ventas/', include('Ventas.urls')),  PARA APP VENTAS.
]

admin.site.site_header = "Administración de tienda"
admin.site.site_title = "Tienda"