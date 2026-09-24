"""
=====================================================================
  SISTEMA DE DETECCIÓN DE SOMNOLENCIA PARA CONDUCTORES
  Usando MediaPipe Face Mesh (modelo pre-entrenado)
=====================================================================
  Métricas utilizadas:
    - EAR (Eye Aspect Ratio): Detecta ojos cerrados
    - MAR (Mouth Aspect Ratio): Detecta bostezos
    - Tiempo de respuesta del conductor
=====================================================================
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import math
import pygame
import os
import sys

# ─────────────────────────────────────────────
#  CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────
EAR_THRESHOLD      = 0.22   # Por debajo → ojos cerrados
MAR_THRESHOLD      = 0.65   # Por encima → bostezo detectado
EAR_CONSEC_FRAMES  = 20     # Frames consecutivos antes de alerta
MAR_CONSEC_FRAMES  = 15     # Frames consecutivos de bostezo
FATIGUE_BLINK_THR  = 40     # Parpadeos por minuto que indican fatiga

# ─── Índices de landmarks de MediaPipe Face Mesh ───────────────────
#  Ojo derecho (desde perspectiva de la cámara = izquierda del usuario)
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
#  Ojo izquierdo
LEFT_EYE  = [33,  160, 158, 133, 153, 144]
#  Boca
MOUTH     = [61,  39,  0,   269, 291, 405, 17, 181]

# ─── Colores (BGR) ────────────────────────────────────────────────
COLOR_GREEN  = (0,  220,  80)
COLOR_YELLOW = (0,  200, 255)
COLOR_RED    = (0,   50, 255)
COLOR_CYAN   = (220, 220,   0)
COLOR_WHITE  = (255, 255, 255)
COLOR_BG     = (20,   20,  35)


# ─────────────────────────────────────────────
#  FUNCIONES DE CÁLCULO
# ─────────────────────────────────────────────

def calcular_distancia(p1, p2):
    """Distancia euclidiana entre dos puntos (x, y)."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def calcular_ear(landmarks, indices, w, h):
    """
    Eye Aspect Ratio (EAR).
    Fórmula: (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    """
    puntos = []
    for idx in indices:
        lm = landmarks[idx]
        puntos.append((lm.x * w, lm.y * h))

    # Distancias verticales
    A = calcular_distancia(puntos[1], puntos[5])
    B = calcular_distancia(puntos[2], puntos[4])
    # Distancia horizontal
    C = calcular_distancia(puntos[0], puntos[3])

    if C == 0:
        return 0.0
    return (A + B) / (2.0 * C)


def calcular_mar(landmarks, indices, w, h):
    """
    Mouth Aspect Ratio (MAR) — detecta bostezos.
    Compara apertura vertical con anchura horizontal de la boca.
    """
    puntos = []
    for idx in indices:
        lm = landmarks[idx]
        puntos.append((lm.x * w, lm.y * h))

    # Distancias verticales (arriba-abajo)
    A = calcular_distancia(puntos[1], puntos[7])
    B = calcular_distancia(puntos[2], puntos[6])
    C = calcular_distancia(puntos[3], puntos[5])
    # Distancia horizontal
    D = calcular_distancia(puntos[0], puntos[4])

    if D == 0:
        return 0.0
    return (A + B + C) / (3.0 * D)


# ─────────────────────────────────────────────
#  SISTEMA DE ALERTAS SONORAS
# ─────────────────────────────────────────────

class SistemaAlertas:
    """Gestiona las alertas visuales y sonoras."""

    def __init__(self):
        self.audio_disponible = False
        self._iniciar_audio()
        self.ultima_alerta = 0
        self.cooldown_alerta = 3.0  # segundos entre alertas

    def _iniciar_audio(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.audio_disponible = True
        except Exception:
            print("[!] Audio no disponible — alertas solo visuales")

    def _generar_beep(self, frecuencia=880, duracion_ms=500):
        """Genera un beep sintético sin necesitar archivo .wav externo."""
        if not self.audio_disponible:
            return
        sample_rate = 22050
        n_samples = int(sample_rate * duracion_ms / 1000)
        t = np.linspace(0, duracion_ms / 1000, n_samples, endpoint=False)
        onda = (np.sin(2 * np.pi * frecuencia * t) * 32767).astype(np.int16)
        sonido = pygame.sndarray.make_sound(onda)
        sonido.play()

    def emitir_alerta(self, nivel="advertencia"):
        """
        nivel: 'advertencia' (amarillo) | 'peligro' (rojo)
        """
        ahora = time.time()
        if ahora - self.ultima_alerta < self.cooldown_alerta:
            return
        self.ultima_alerta = ahora

        if nivel == "peligro":
            self._generar_beep(frecuencia=1200, duracion_ms=800)
        else:
            self._generar_beep(frecuencia=880,  duracion_ms=400)


# ─────────────────────────────────────────────
#  VISUALIZACIÓN HUD
# ─────────────────────────────────────────────

def dibujar_barra(frame, valor, maximo, x, y, ancho, alto, color, etiqueta):
    """Dibuja una barra de progreso con etiqueta."""
    porcentaje = min(valor / maximo, 1.0)
    cv2.rectangle(frame, (x, y), (x + ancho, y + alto),
                  (60, 60, 80), -1)
    cv2.rectangle(frame, (x, y), (x + int(ancho * porcentaje), y + alto),
                  color, -1)
    cv2.rectangle(frame, (x, y), (x + ancho, y + alto),
                  (120, 120, 140), 1)
    cv2.putText(frame, f"{etiqueta}: {valor:.2f}", (x, y - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_WHITE, 1, cv2.LINE_AA)


def dibujar_puntos_ojos(frame, landmarks, indices, w, h, color):
    """Dibuja el contorno del ojo con líneas conectadas."""
    puntos = []
    for idx in indices:
        lm = landmarks[idx]
        px, py = int(lm.x * w), int(lm.y * h)
        puntos.append((px, py))
        cv2.circle(frame, (px, py), 2, color, -1)

    # Conectar puntos formando el contorno
    for i in range(len(puntos)):
        cv2.line(frame, puntos[i], puntos[(i + 1) % len(puntos)],
                 color, 1, cv2.LINE_AA)


def dibujar_hud(frame, estado):
    """
    Dibuja el HUD (Heads-Up Display) con toda la información
    de somnolencia sobre el frame de video.
    """
    h, w = frame.shape[:2]

    # ── Panel superior izquierdo ─────────────────────────────────
    panel_h = 160
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (270, panel_h), (15, 15, 30), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    # Título
    cv2.putText(frame, "DETECTOR DE SOMNOLENCIA", (10, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLOR_CYAN, 1, cv2.LINE_AA)
    cv2.line(frame, (10, 28), (260, 28), COLOR_CYAN, 1)

    # Barras de métricas
    ear_color = COLOR_RED if estado["ear"] < EAR_THRESHOLD else COLOR_GREEN
    mar_color = COLOR_YELLOW if estado["mar"] > MAR_THRESHOLD else COLOR_GREEN

    dibujar_barra(frame, estado["ear"], 0.45, 10, 45, 250, 14,
                  ear_color, "EAR (Ojos)")
    dibujar_barra(frame, estado["mar"], 1.2,  10, 85, 250, 14,
                  mar_color, "MAR (Boca)")

    # Contadores
    cv2.putText(frame,
                f"Parpadeos: {estado['parpadeos']}  "
                f"Bostezos: {estado['bostezos']}",
                (10, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)
    cv2.putText(frame,
                f"Tiempo activo: {estado['tiempo']:.0f}s",
                (10, 140),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLOR_WHITE, 1, cv2.LINE_AA)

    # ── Indicador de estado (esquina superior derecha) ───────────
    estado_txt  = estado["nivel"]
    estado_color = {
        "ALERTA":       COLOR_GREEN,
        "ADVERTENCIA":  COLOR_YELLOW,
        "¡PELIGRO!":    COLOR_RED,
    }.get(estado_txt, COLOR_WHITE)

    # Fondo del badge
    (tw, th), _ = cv2.getTextSize(estado_txt,
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
    bx = w - tw - 30
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (bx - 10, 8), (w - 5, 38), estado_color, -1)
    cv2.addWeighted(overlay2, 0.45, frame, 0.55, 0, frame)
    cv2.putText(frame, estado_txt, (bx - 6, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, estado_color, 2, cv2.LINE_AA)

    # ── Alerta visual grande si hay peligro ──────────────────────
    if estado_txt == "¡PELIGRO!":
        pulso = int(time.time() * 4) % 2 == 0  # parpadeo 2 Hz
        if pulso:
            overlay3 = frame.copy()
            cv2.rectangle(overlay3, (0, 0), (w, h), COLOR_RED, -1)
            cv2.addWeighted(overlay3, 0.12, frame, 0.88, 0, frame)

        # Mensaje central
        msg = "¡PELIGRO! DESCANSE AHORA"
        (mw, mh), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        mx = (w - mw) // 2
        my = h // 2
        cv2.putText(frame, msg, (mx + 2, my + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, msg, (mx, my),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLOR_RED, 2, cv2.LINE_AA)

    elif estado_txt == "ADVERTENCIA":
        msg = "Señales de fatiga detectadas"
        (mw, _), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 1)
        mx = (w - mw) // 2
        my = h - 40
        cv2.putText(frame, msg, (mx + 1, my + 1),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, msg, (mx, my),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_YELLOW, 1, cv2.LINE_AA)

    # ── Instrucciones (abajo izquierda) ──────────────────────────
    cv2.putText(frame, "Q: Salir  |  R: Reiniciar contadores  |  C: Calibrar",
                (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 150, 170), 1, cv2.LINE_AA)


# ─────────────────────────────────────────────
#  CLASE PRINCIPAL DEL DETECTOR
# ─────────────────────────────────────────────

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "face_landmarker.task")
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

def _asegurar_modelo_landmarker():
    if not os.path.exists(MODEL_PATH):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        print("[Detector] Descargando modelo Face Landmarker...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

class DetectorSomnolencia:
    """
    Sistema completo de detección de somnolencia.
    Soporta MediaPipe Tasks API (v1.0+) y legacy mp.solutions.
    """

    def __init__(self):
        # ── MediaPipe Compatibility ───────────────────────────
        self.use_tasks_api = not hasattr(mp, 'solutions')
        if not self.use_tasks_api:
            try:
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6
                )
            except AttributeError:
                self.use_tasks_api = True

        if self.use_tasks_api:
            import urllib.request
            _asegurar_modelo_landmarker()
            base_opts = mp.tasks.BaseOptions(model_asset_path=MODEL_PATH)
            opts = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=base_opts,
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_faces=1
            )
            self.landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(opts)

        # ── Contadores ────────────────────────────────────────
        self.frames_ojo_cerrado = 0
        self.frames_boca_abierta = 0
        self.total_parpadeos    = 0
        self.total_bostezos     = 0
        self.nivel_alerta       = "ALERTA"
        self.tiempo_inicio      = time.time()

        # ── Umbral EAR dinámico (calibración) ─────────────────
        self.ear_threshold_actual = EAR_THRESHOLD
        self.en_calibracion      = False
        self.buffer_calibracion  = []

        # ── Alertas ───────────────────────────────────────────
        self.alertas = SistemaAlertas()

        # ── Historial EAR para gráfica ─────────────────────────
        self.ear_historial = []
        self.mar_historial = []

    def reiniciar_contadores(self):
        self.total_parpadeos    = 0
        self.total_bostezos     = 0
        self.frames_ojo_cerrado = 0
        self.frames_boca_abierta = 0
        self.tiempo_inicio      = time.time()
        self.nivel_alerta       = "ALERTA"
        print("[✓] Contadores reiniciados")

    def iniciar_calibracion(self):
        """Calibra el umbral EAR al estado 'ojos abiertos' del usuario."""
        print("[CAL] Calibrando... mantén los ojos abiertos por 3 segundos")
        self.en_calibracion = True
        self.buffer_calibracion = []

    def _actualizar_calibracion(self, ear_actual):
        if len(self.buffer_calibracion) < 90:   # ~3s a 30fps
            self.buffer_calibracion.append(ear_actual)
        else:
            promedio = np.mean(self.buffer_calibracion)
            self.ear_threshold_actual = promedio * 0.75  # 75% del valor abierto
            self.en_calibracion = False
            print(f"[CAL] Calibración completa. Nuevo umbral EAR: "
                  f"{self.ear_threshold_actual:.3f}")

    def _determinar_nivel(self, ear, mar):
        """
        Lógica de niveles:
          ALERTA      → Conductor despierto
          ADVERTENCIA → Inicio de fatiga (ojos semi-cerrados o bostezo)
          ¡PELIGRO!   → Somnolencia severa
        """
        if (self.frames_ojo_cerrado >= EAR_CONSEC_FRAMES * 1.5
                or self.total_bostezos >= 3):
            return "¡PELIGRO!"
        elif (self.frames_ojo_cerrado >= EAR_CONSEC_FRAMES // 2
              or self.frames_boca_abierta >= MAR_CONSEC_FRAMES):
            return "ADVERTENCIA"
        else:
            return "ALERTA"

    def dibujar_grafica_ear(self, frame):
        """Mini-gráfica de EAR en tiempo real (esquina inferior derecha)."""
        h, w = frame.shape[:2]
        gw, gh = 200, 70
        gx, gy = w - gw - 10, h - gh - 30

        # Fondo
        overlay = frame.copy()
        cv2.rectangle(overlay, (gx - 5, gy - 20),
                      (gx + gw + 5, gy + gh + 5), (15, 15, 30), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        cv2.putText(frame, "EAR histórico", (gx, gy - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, COLOR_CYAN, 1)

        # Línea de umbral
        umbral_y = gy + gh - int((self.ear_threshold_actual / 0.45) * gh)
        cv2.line(frame, (gx, umbral_y), (gx + gw, umbral_y),
                 COLOR_RED, 1, cv2.LINE_AA)

        # Gráfica
        historial = self.ear_historial[-gw:]
        for i in range(1, len(historial)):
            y1 = gy + gh - int((historial[i - 1] / 0.45) * gh)
            y2 = gy + gh - int((historial[i]     / 0.45) * gh)
            y1 = max(gy, min(gy + gh, y1))
            y2 = max(gy, min(gy + gh, y2))
            color = (COLOR_RED if historial[i] < self.ear_threshold_actual
                     else COLOR_GREEN)
            cv2.line(frame, (gx + i - 1, y1), (gx + i, y2),
                     color, 1, cv2.LINE_AA)

    def procesar_frame(self, frame):
        """
        Procesa un frame de video y retorna el frame anotado
        junto con el estado actual del sistema.
        """
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        ear = 0.0
        mar = 0.0
        rostro_detectado = False
        landmarks = None

        if self.use_tasks_api:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            resultados = self.landmarker.detect(mp_image)
            if resultados and resultados.face_landmarks:
                landmarks = resultados.face_landmarks[0]
        else:
            rgb.flags.writeable = False
            resultados = self.face_mesh.process(rgb)
            rgb.flags.writeable = True
            if resultados.multi_face_landmarks:
                landmarks = resultados.multi_face_landmarks[0].landmark

        if landmarks is not None:
            rostro_detectado = True

            # ── Calcular EAR y MAR ────────────────────────────
            ear_der = calcular_ear(landmarks, RIGHT_EYE, w, h)
            ear_izq = calcular_ear(landmarks, LEFT_EYE,  w, h)
            ear     = (ear_der + ear_izq) / 2.0
            mar     = calcular_mar(landmarks, MOUTH, w, h)

            # ── Calibración dinámica ──────────────────────────
            if self.en_calibracion:
                self._actualizar_calibracion(ear)

            # ── Detección de parpadeo ─────────────────────────
            if ear < self.ear_threshold_actual:
                self.frames_ojo_cerrado += 1
            else:
                if self.frames_ojo_cerrado >= 2:   # parpadeo completado
                    self.total_parpadeos += 1
                self.frames_ojo_cerrado = 0

            # ── Detección de bostezo ──────────────────────────
            if mar > MAR_THRESHOLD:
                self.frames_boca_abierta += 1
            else:
                if self.frames_boca_abierta >= MAR_CONSEC_FRAMES:
                    self.total_bostezos += 1
                self.frames_boca_abierta = 0

            # ── Dibujar puntos faciales (ojos y boca) ─────────
            ojo_color = (COLOR_RED if ear < self.ear_threshold_actual
                         else COLOR_GREEN)
            boca_color = (COLOR_YELLOW if mar > MAR_THRESHOLD
                          else COLOR_CYAN)

            dibujar_puntos_ojos(frame, landmarks, RIGHT_EYE, w, h, ojo_color)
            dibujar_puntos_ojos(frame, landmarks, LEFT_EYE,  w, h, ojo_color)
            dibujar_puntos_ojos(frame, landmarks, MOUTH,     w, h, boca_color)

        # ── Historial para gráfica ─────────────────────────────
        self.ear_historial.append(ear)
        if len(self.ear_historial) > 300:
            self.ear_historial.pop(0)

        # ── Nivel de alerta ────────────────────────────────────
        self.nivel_alerta = self._determinar_nivel(ear, mar)

        # ── Emitir alerta sonora si corresponde ───────────────
        if self.nivel_alerta == "¡PELIGRO!":
            self.alertas.emitir_alerta("peligro")
        elif self.nivel_alerta == "ADVERTENCIA":
            self.alertas.emitir_alerta("advertencia")

        # ── Estado del sistema ────────────────────────────────
        estado = {
            "ear":        ear,
            "mar":        mar,
            "parpadeos":  self.total_parpadeos,
            "bostezos":   self.total_bostezos,
            "nivel":      self.nivel_alerta,
            "tiempo":     time.time() - self.tiempo_inicio,
            "rostro":     rostro_detectado,
        }

        # ── HUD y gráfica ──────────────────────────────────────
        dibujar_hud(frame, estado)
        if rostro_detectado:
            self.dibujar_grafica_ear(frame)

        # ── Mensaje si no hay rostro ───────────────────────────
        if not rostro_detectado:
            msg = "⚠  Rostro no detectado"
            (mw, _), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX,
                                          0.7, 2)
            cv2.putText(frame, msg, ((w - mw) // 2, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_YELLOW,
                        2, cv2.LINE_AA)

        # ── Indicador de calibración ───────────────────────────
        if self.en_calibracion:
            progreso = len(self.buffer_calibracion) / 90.0
            cv2.putText(frame,
                        f"Calibrando... {int(progreso*100)}%",
                        (10, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        COLOR_CYAN, 2, cv2.LINE_AA)

        return frame, estado


# ─────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  SISTEMA DE DETECCIÓN DE SOMNOLENCIA — MediaPipe")
    print("=" * 60)
    print("  Controles:")
    print("    Q → Salir")
    print("    R → Reiniciar contadores")
    print("    C → Calibrar umbral EAR personal")
    print("=" * 60)

    # ── Cámara ────────────────────────────────────────────────
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] No se pudo abrir la cámara.")
        sys.exit(1)

    # Configurar resolución
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  854)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    detector = DetectorSomnolencia()

    # ── FPS counter ───────────────────────────────────────────
    fps_tiempo = time.time()
    fps_contador = 0
    fps_actual   = 0

    cv2.namedWindow("Detector de Somnolencia", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Detector de Somnolencia", 854, 480)

    print("[✓] Sistema iniciado. Procesando video...")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] No se pudo leer el frame.")
            break

        frame = cv2.flip(frame, 1)  # Espejo horizontal

        # ── Procesar frame ────────────────────────────────────
        frame, estado = detector.procesar_frame(frame)

        # ── FPS ───────────────────────────────────────────────
        fps_contador += 1
        if time.time() - fps_tiempo >= 1.0:
            fps_actual   = fps_contador
            fps_contador = 0
            fps_tiempo   = time.time()

        h, w = frame.shape[:2]
        cv2.putText(frame, f"FPS: {fps_actual}", (w - 90, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (150, 150, 170), 1, cv2.LINE_AA)

        cv2.imshow("Detector de Somnolencia", frame)

        # ── Teclas ────────────────────────────────────────────
        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q") or tecla == 27:    # Q o ESC
            break
        elif tecla == ord("r"):
            detector.reiniciar_contadores()
        elif tecla == ord("c"):
            detector.iniciar_calibracion()

    # ── Limpieza ──────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    try:
        pygame.mixer.quit()
    except Exception:
        pass
    print("[✓] Sistema detenido correctamente.")


if __name__ == "__main__":
    main()
