"""API REST del detector de somnolencia."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from detector import DrowsinessDetector
from models import AnalysisResponse, ErrorResponse, FrameRequest


app = FastAPI(
    title="API - Detector de Somnolencia",
    description=(
        "Sistema de deteccion de somnolencia para conductores. "
        "Las cuentas se guardan unicamente en el almacenamiento local "
        "del navegador."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post(
    "/api/analyze",
    response_model=AnalysisResponse,
    summary="Analizar frame de video",
    tags=["Deteccion de Somnolencia"],
    responses={
        200: {"description": "Analisis exitoso"},
        422: {"model": ErrorResponse, "description": "Frame invalido"},
    },
)
async def analyze_frame(request: FrameRequest):
    """Analiza un frame y devuelve las metricas de somnolencia."""
    detector = DrowsinessDetector.get_instance()
    result = detector.analyze(request.frame, request.ear_threshold)
    return AnalysisResponse(**result)


@app.get("/api/health", summary="Estado del servidor", tags=["Sistema"])
async def health():
    """Verifica que el servidor esta operativo."""
    return {
        "status": "ok",
        "service": "Detector de Somnolencia API",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
