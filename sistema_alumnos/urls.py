import os
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('gestion.urls')),
]

# Habilitar ruta de administración solo si ENABLE_ADMIN es activado explícitamente en variables de entorno
if os.environ.get('ENABLE_ADMIN', 'False').lower() in ['true', '1']:
    urlpatterns.append(path('admin/', admin.site.urls))
