from django.urls import path
from . import views

app_name = 'gestion'

urlpatterns = [
    path('', views.buscador_view, name='buscador'),
    path('api/alumno/<str:dni>/', views.alumno_detalle_json, name='alumno_detalle_json'),
    path('alumno/<str:dni>/imprimir/', views.imprimir_estado_academico, name='imprimir_estado_academico'),
]
