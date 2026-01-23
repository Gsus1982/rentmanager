from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
import logging

logger = logging.getLogger('django.contrib.auth')

def home(request):
    return HttpResponse('RentManager está online ✓')

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),
]

# Hook para loguear intentos de login en admin
original_login = admin.site.login
def logged_login(request):
    if request.method == 'POST':
        logger.info(f"DEBUG: POST /admin/login/, username={request.POST.get('username', 'NO_USERNAME')}")
    return original_login(request)

admin.site.login = logged_login
