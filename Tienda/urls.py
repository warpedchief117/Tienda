from . import views
from django.urls import path

app_name = 'Tienda'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('registro-empleado/', views.registro_empleado, name='registro_empleado'),
    path('registro-cliente/', views.registro_cliente, name='registro_cliente'),

]
