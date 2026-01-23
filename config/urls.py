from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from app.views import CustomAdminLoginView

def home(request):
    return HttpResponse('RentManager está online ✓')

urlpatterns = [
    path('', home, name='home'),
    path('admin/login/', CustomAdminLoginView.as_view(), name='admin_login'),
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),
]
