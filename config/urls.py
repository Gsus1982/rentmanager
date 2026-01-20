from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse('RentManager está online ✓')

urlpatterns = [
    path('', home, name='home'),  # ← AÑADE ESTA LÍNEA PRIMERO
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),  # o lo que sea
]
