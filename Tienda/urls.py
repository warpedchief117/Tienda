from . import views
from django.urls import path

app_name = 'tienda'

urlpatterns = [
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('registro-empleado/', views.registro_empleado, name='registro_empleado'),
    path('registro-cliente/', views.registro_cliente, name='registro_cliente'),
    #URLS para dashboards y usuarios clientes
    path('', views.landing, name='landing'),
    path('dashboard-socio/', views.dashboard_socio, name='dashboard_socio'),
    path('dashboard-dueno/', views.dashboard_dueno, name='dashboard_dueno'),

]
