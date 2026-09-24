"""
main.py — FastAPI Application
Sistema de detección de somnolencia — API REST con Swagger UI en /docs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import create_tables, get_db
from models import (
    RegisterRequest, LoginRequest, TokenResponse,
    FrameRequest, AnalysisResponse, UserPublic, ErrorResponse
)
from auth import (
    create_access_token, authenticate_user, create_user,
    get_user_by_username, get_user_by_email, get_current_user,
    TOKEN_EXPIRE_H
)
from detector import DrowsinessDetector

# ─── Inicialización ───────────────────────────────────────────────
create_tables()

app = FastAPI(
    title="API — Detector de Somnolencia",
    description=(
        "## Sistema de detección de somnolencia para conductores\n\n"
        "Usa el modelo pre-entrenado **MediaPipe FaceLandmarker** para analizar "
        "frames de video en tiempo real y detectar señales de fatiga.\n\n"
        "### Flujo de uso:\n"
        "1. `POST /api/auth/register` — Crear cuenta\n"
        "2. `POST /api/auth/login` — Obtener token JWT\n"
        "3. `POST /api/analyze` — Enviar frame (con Bearer token)\n\n"
        "### Métricas:\n"
        "- **EAR** (Eye Aspect Ratio): apertura ocular\n"
        "- **eyeBlink** (Blendshape): score de ojos cerrados\n"
        "- **jawOpen** (Blendshape): score de bostezo"
    ),
    version="1.0.0",
    contact={"name": "SENA — Taller Final Python"},
    license_info={"name": "MIT"},
)

# ─── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000",
                   "https://*.vercel.app", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Rutas de autenticación ───────────────────────────────────────

@app.post(
    "/api/auth/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    tags=["Autenticación"],
)
async def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Crea una nueva cuenta de usuario con contraseña hasheada (bcrypt)."""
    if get_user_by_username(db, data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya existe"
        )
    if get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    user = create_user(db, data.username, data.email, data.password)
    return UserPublic(id=user.id, username=user.username, email=user.email)


@app.post(
    "/api/auth/login",
    response_model=TokenResponse,
    summary="Iniciar sesión y obtener JWT",
    tags=["Autenticación"],
)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica al usuario y devuelve un token JWT Bearer.
    Usa el token en el header `Authorization: Bearer <token>` para rutas protegidas.
    """
    user = authenticate_user(db, data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    expires = timedelta(hours=TOKEN_EXPIRE_H)
    token   = create_access_token({"sub": user.username}, expires_delta=expires)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        expires_in=int(expires.total_seconds()),
    )


@app.get(
    "/api/auth/me",
    response_model=UserPublic,
    summary="Perfil del usuario autenticado",
    tags=["Autenticación"],
)
async def me(current_user=Depends(get_current_user)):
    """Devuelve los datos del usuario autenticado con el JWT."""
    return UserPublic(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email
    )


# ─── Ruta de análisis ─────────────────────────────────────────────

@app.post(
    "/api/analyze",
    response_model=AnalysisResponse,
    summary="Analizar frame de video",
    tags=["Detección de Somnolencia"],
    responses={
        200: {"description": "Análisis exitoso"},
        401: {"model": ErrorResponse, "description": "Token inválido"},
        422: {"model": ErrorResponse, "description": "Frame inválido"},
    }
)
async def analyze_frame(
    request: FrameRequest,
    current_user=Depends(get_current_user)
):
    """
    Analiza un frame de video y retorna métricas de somnolencia.

    - **frame**: Imagen JPEG en base64 (con o sin prefijo `data:image/jpeg;base64,`)
    - **ear_threshold**: Umbral EAR personalizado (default 0.25)

    Retorna:
    - `ear`: Eye Aspect Ratio (< threshold → ojos cerrados)
    - `blink_left/right`: Score blendshape 0-1 (> 0.4 → ojo cerrado)
    - `jaw_open`: Score bostezo 0-1 (> 0.28 → bostezo)
    - `alert_level`: `ALERTA` | `ADVERTENCIA` | `PELIGRO`
    - `eye_landmarks` / `mouth_landmarks`: coordenadas normalizadas para canvas
    """
    detector = DrowsinessDetector.get_instance()
    result   = detector.analyze(request.frame, request.ear_threshold)
    return AnalysisResponse(**result)


# ─── Health check ─────────────────────────────────────────────────

@app.get("/api/health", summary="Estado del servidor", tags=["Sistema"])
async def health():
    """Verifica que el servidor está operativo."""
    return {
        "status": "ok",
        "service": "Detector de Somnolencia API",
        "version": "1.0.0"
    }


# ─── Punto de entrada ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
