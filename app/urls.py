from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Inmuebles
    path('inmuebles/', views.inmuebles_list, name='inmuebles_list'),
    path('inmuebles/crear/', views.InmuebleCreateView.as_view(), name='inmueble_create'),
    path('inmuebles/<int:pk>/', views.inmueble_detail, name='inmueble_detail'),
    path('inmuebles/<int:pk>/editar/', views.InmuebleUpdateView.as_view(), name='inmueble_update'),
    path('inmuebles/<int:pk>/eliminar/', views.InmuebleDeleteView.as_view(), name='inmueble_delete'),
    
    # Gastos
    path('inmuebles/<int:inmueble_pk>/gasto/', views.GastoCreateView.as_view(), name='gasto_create'),
    path('gastos/<int:pk>/editar/', views.GastoUpdateView.as_view(), name='gasto_update'),
    path('gastos/<int:pk>/eliminar/', views.GastoDeleteView.as_view(), name='gasto_delete'),
    
    # Reportes
    path('reportes/', views.reportes, name='reportes'),
    
    # API
    path('api/dashboard-data/', views.api_dashboard_data, name='api_dashboard_data'),
]
