
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('generate_meshes/', views.generate_meshes, name='generate_meshes'),
]

