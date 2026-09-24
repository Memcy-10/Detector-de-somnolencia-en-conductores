"""config/urls.py — URL raíz de Django"""

from django.urls import path, include

urlpatterns = [
    path("", include("drowsiness.urls")),
]
