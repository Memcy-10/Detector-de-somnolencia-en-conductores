"""Vistas de Django para servir la interfaz del detector."""
from django.conf import settings
from django.shortcuts import render, redirect

FASTAPI = settings.FASTAPI_URL


def login_view(request):
    """Sirve la página de login; la autenticación ocurre en el navegador."""
    return render(request, "login.html")


def dashboard_view(request):
    """Dashboard principal; el acceso se comprueba en JavaScript."""
    context = {
        "fastapi_url": FASTAPI,
    }
    return render(request, "dashboard.html", context)


def logout_view(request):
    """Ruta de respaldo; el cierre real borra localStorage en el navegador."""
    return redirect("login")
