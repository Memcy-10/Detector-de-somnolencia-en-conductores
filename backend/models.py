"""
models.py — Pydantic schemas para FastAPI
Validación de request/response con documentación automática en Swagger.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


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
