"""
views.py — Vistas de Django
Maneja login, registro, dashboard y logout usando sesiones.
El JWT obtenido de FastAPI se guarda en la sesión Django.
"""

import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods

FASTAPI = settings.FASTAPI_URL


def _api_post(endpoint: str, data: dict) -> tuple:
    """Hace POST a FastAPI y retorna (json, status_code)."""
    try:
        r = requests.post(f"{FASTAPI}{endpoint}", json=data, timeout=10)
        return r.json(), r.status_code
    except requests.exceptions.ConnectionError:
        return {"detail": "No se pudo conectar al backend (FastAPI)"}, 503


def login_required_session(view_func):
    """Decorador simple: redirige a login si no hay JWT en sesión."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get("jwt_token"):
            return redirect("login")
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── Vistas ───────────────────────────────────────────────────────

@require_http_methods(["GET", "POST"])
def login_view(request):
    """Página de inicio de sesión."""
    if request.session.get("jwt_token"):
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        data, status_code = _api_post("/api/auth/login", {
            "username": username,
            "password": password
        })

        if status_code == 200:
            request.session["jwt_token"] = data["access_token"]
            request.session["username"]  = data["username"]
            return redirect("dashboard")
        else:
            error = data.get("detail", "Credenciales incorrectas")
            messages.error(request, error)

    return render(request, "login.html")


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Página de registro de usuario."""
    if request.session.get("jwt_token"):
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email    = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm  = request.POST.get("confirm_password", "")

        if password != confirm:
            messages.error(request, "Las contraseñas no coinciden")
        elif len(password) < 6:
            messages.error(request, "La contraseña debe tener al menos 6 caracteres")
        else:
            data, status_code = _api_post("/api/auth/register", {
                "username": username,
                "email":    email,
                "password": password
            })
            if status_code == 201:
                messages.success(request, "Cuenta creada exitosamente. Inicia sesión.")
                return redirect("login")
            else:
                error = data.get("detail", "Error al registrar")
                messages.error(request, error)

    return render(request, "register.html")


@login_required_session
def dashboard_view(request):
    """Dashboard principal — cámara en vivo + detección de somnolencia."""
    context = {
        "username":  request.session.get("username", "Usuario"),
        "jwt_token": request.session.get("jwt_token", ""),
        "fastapi_url": FASTAPI,
    }
    return render(request, "dashboard.html", context)


def logout_view(request):
    """Cierra sesión y limpia la sesión Django."""
    request.session.flush()
    return redirect("login")
