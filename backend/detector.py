"""
detector.py — Motor de detección de somnolencia
Usa la nueva MediaPipe Tasks API (FaceLandmarker) con:
  - Blendshapes: eyeBlinkLeft, eyeBlinkRight, jawOpen
  - EAR (Eye Aspect Ratio) calculado desde landmarks
El modelo face_landmarker.task se descarga automáticamente si no existe.
"""

import os
import math
import base64
import urllib.request
import numpy as np
import cv2
import mediapipe as mp

# ─── Rutas y configuración ────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH     = os.path.join(BASE_DIR, "face_landmarker.task")
MODEL_URL      = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# ─── API de MediaPipe Tasks ───────────────────────────────────────
BaseOptions         = mp.tasks.BaseOptions
FaceLandmarker      = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOpts  = mp.tasks.vision.FaceLandmarkerOptions
RunningMode         = mp.tasks.vision.RunningMode

# ─── Índices de landmarks (MediaPipe Face Mesh 478) ───────────────
LEFT_EYE   = [362, 380, 374, 263, 386, 385]
RIGHT_EYE  = [33,  159, 158, 133, 153, 145]
MOUTH_IDX  = [61,  39,   0, 269, 291, 405,  17, 181]

# ─── Umbrales ─────────────────────────────────────────────────────
BLINK_THR     = 0.40   # blendshape eyeBlink > umbral → ojo cerrado
JAW_THR       = 0.28   # blendshape jawOpen  > umbral → bostezo
EAR_DEFAULT   = 0.25   # EAR por defecto


def _download_model():
    """Descarga el modelo pre-entrenado si no existe en disco."""
    if os.path.exists(MODEL_PATH):
        return
    print(f"[Detector] Descargando modelo MediaPipe Face Landmarker (~30 MB)...")
    print(f"[Detector] URL: {MODEL_URL}")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"[Detector] Modelo guardado en: {MODEL_PATH}")
    except Exception as e:
        raise RuntimeError(
            f"No se pudo descargar el modelo MediaPipe: {e}\n"
            f"Descárgalo manualmente de:\n{MODEL_URL}\n"
            f"y colócalo en: {MODEL_PATH}"
        )


def _euclidean(p1, p2) -> float:
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


def _calculate_ear(landmarks, indices) -> float:
    """Eye Aspect Ratio: (A + B) / (2 * C)"""
    pts = [landmarks[i] for i in indices]
    A = _euclidean(pts[1], pts[5])
    B = _euclidean(pts[2], pts[4])
    C = _euclidean(pts[0], pts[3])
    return (A + B) / (2.0 * C) if C > 0 else 0.0


def _get_blendshape(blendshapes, name: str) -> float:
    """Extrae el score de un blendshape por nombre."""
    for b in blendshapes:
        if b.category_name == name:
            return b.score
    return 0.0


def _landmark_to_dict(lm) -> dict:
    return {"x": round(lm.x, 4), "y": round(lm.y, 4)}


# ─── Clase Detector ───────────────────────────────────────────────

class DrowsinessDetector:
    """
    Detector de somnolencia usando MediaPipe FaceLandmarker (Tasks API).
    Singleton — se inicializa una sola vez al arrancar FastAPI.
    """

    _instance: "DrowsinessDetector | None" = None

    def __init__(self):
        _download_model()
        options = FaceLandmarkerOpts(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            output_face_blendshapes=True,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = FaceLandmarker.create_from_options(options)
        print("[Detector] FaceLandmarker listo.")

    @classmethod
    def get_instance(cls) -> "DrowsinessDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def analyze(self, frame_b64: str, ear_threshold: float = EAR_DEFAULT) -> dict:
        """
        Analiza un frame en base64 y retorna las métricas de somnolencia.

        Args:
            frame_b64: Imagen JPEG en base64 (con o sin prefijo data URL)
            ear_threshold: Umbral EAR personalizado

        Returns:
            dict con ear, blendshapes, alert_level, landmarks
        """
        # ── Decodificar imagen ─────────────────────────────────────
        if "," in frame_b64:
            frame_b64 = frame_b64.split(",")[1]
        img_bytes = base64.b64decode(frame_b64)
        nparr     = np.frombuffer(img_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_bgr is None:
            return self._empty_result("Frame inválido o corrupto")

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # ── Inferencia ────────────────────────────────────────────
        result = self.landmarker.detect(mp_image)

        if not result.face_landmarks:
            return self._empty_result("Rostro no detectado")

        landmarks   = result.face_landmarks[0]
        blendshapes = result.face_blendshapes[0] if result.face_blendshapes else []

        # ── Métricas ──────────────────────────────────────────────
        ear_l = _calculate_ear(landmarks, LEFT_EYE)
        ear_r = _calculate_ear(landmarks, RIGHT_EYE)
        ear   = (ear_l + ear_r) / 2.0

        blink_left  = _get_blendshape(blendshapes, "eyeBlinkLeft")
        blink_right = _get_blendshape(blendshapes, "eyeBlinkRight")
        jaw_open    = _get_blendshape(blendshapes, "jawOpen")

        # ── Nivel de alerta ───────────────────────────────────────
        eyes_closed = (blink_left > BLINK_THR and blink_right > BLINK_THR) \
                       or ear < ear_threshold
        yawning     = jaw_open > JAW_THR

        if eyes_closed and yawning:
            level   = "PELIGRO"
            message = "¡Somnolencia severa! Detenga el vehiculo"
        elif eyes_closed:
            level   = "ADVERTENCIA"
            message = "Ojos cerrados detectados — precaución"
        elif yawning:
            level   = "ADVERTENCIA"
            message = "Bostezo detectado — señal de fatiga"
        else:
            level   = "ALERTA"
            message = "Conductor alerta"

        # ── Landmarks clave para el canvas ────────────────────────
        eye_pts   = [_landmark_to_dict(landmarks[i])
                     for i in LEFT_EYE + RIGHT_EYE]
        mouth_pts = [_landmark_to_dict(landmarks[i])
                     for i in MOUTH_IDX]

        return {
            "face_detected":  True,
            "ear":            round(ear, 4),
            "blink_left":     round(blink_left, 4),
            "blink_right":    round(blink_right, 4),
            "jaw_open":       round(jaw_open, 4),
            "alert_level":    level,
            "message":        message,
            "eye_landmarks":  eye_pts,
            "mouth_landmarks": mouth_pts,
        }

    @staticmethod
    def _empty_result(message: str) -> dict:
        return {
            "face_detected":  False,
            "ear":            0.0,
            "blink_left":     0.0,
            "blink_right":    0.0,
            "jaw_open":       0.0,
            "alert_level":    "ALERTA",
            "message":        message,
            "eye_landmarks":  [],
            "mouth_landmarks": [],
        }
