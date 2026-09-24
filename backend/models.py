"""
models.py — Pydantic schemas para FastAPI
Validación de request/response con documentación automática en Swagger.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


# ─── Auth ────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario")
    email: EmailStr = Field(..., description="Correo electrónico")
    password: str = Field(..., min_length=6, description="Contraseña (mín. 6 caracteres)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "conductor01",
                "email": "conductor@ejemplo.com",
                "password": "segura123"
            }
        }
    }


class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario")
    password: str = Field(..., description="Contraseña")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "conductor01",
                "password": "segura123"
            }
        }
    }


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT de acceso")
    token_type: str = Field(default="bearer")
    username: str
    expires_in: int = Field(description="Segundos hasta expiración")


class UserPublic(BaseModel):
    id: int
    username: str
    email: str


# ─── Análisis de frame ───────────────────────────────────────────

class LandmarkPoint(BaseModel):
    x: float = Field(..., description="Coordenada X normalizada (0-1)")
    y: float = Field(..., description="Coordenada Y normalizada (0-1)")


class FrameRequest(BaseModel):
    frame: str = Field(
        ...,
        description="Frame de video en base64 (data URL JPEG)"
    )
    ear_threshold: Optional[float] = Field(
        default=0.25,
        ge=0.1, le=0.5,
        description="Umbral EAR personalizado"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "frame": "data:image/jpeg;base64,/9j/4AAQ...",
                "ear_threshold": 0.25
            }
        }
    }


class AnalysisResponse(BaseModel):
    face_detected: bool = Field(..., description="¿Se detectó un rostro?")
    ear: float = Field(..., description="Eye Aspect Ratio promedio")
    blink_left: float = Field(..., description="Blendshape eyeBlinkLeft (0-1)")
    blink_right: float = Field(..., description="Blendshape eyeBlinkRight (0-1)")
    jaw_open: float = Field(..., description="Blendshape jawOpen (0-1)")
    alert_level: str = Field(..., description="Nivel: ALERTA | ADVERTENCIA | PELIGRO")
    message: str = Field(..., description="Mensaje descriptivo")
    eye_landmarks: List[LandmarkPoint] = Field(
        default=[],
        description="Puntos clave de ojos para dibujar en canvas"
    )
    mouth_landmarks: List[LandmarkPoint] = Field(
        default=[],
        description="Puntos clave de boca para dibujar en canvas"
    )


# ─── General ─────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
