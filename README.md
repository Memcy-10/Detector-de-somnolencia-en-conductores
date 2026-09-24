# 🚗 Sistema de Detección de Somnolencia para Conductores

> **Taller Final — Python · SENA · Tercer Trimestre**  
> Modelo pre-entrenado: **MediaPipe Face Mesh** (468 landmarks faciales)

**Autores:** Maicol Montoya y Samuel Palacio

**Frontend:**
https://frontend-eosin-three-ek416xrump.vercel.app/

**Backend:**
https://detector-de-somnolencia-en-conductores.onrender.com

---

## 📌 Descripción

Este proyecto implementa un sistema de **detección de somnolencia en tiempo real** para conductores, utilizando el modelo pre-entrenado de **MediaPipe Face Mesh** a través de la cámara web.

El sistema analiza el video fotograma a fotograma y calcula métricas biométricas del rostro para detectar señales de fatiga antes de que el conductor se quede dormido al volante.

---

## 🧠 ¿Cómo funciona?

### Modelo utilizado
**MediaPipe Face Mesh** detecta **468 puntos de referencia (landmarks)** en el rostro en tiempo real. Estos puntos permiten medir con precisión la apertura de ojos y boca.

### Métricas de detección

| Métrica | Fórmula | Umbral | Detecta |
|---------|---------|--------|---------|
| **EAR** (Eye Aspect Ratio) | `(‖p2-p6‖ + ‖p3-p5‖) / (2·‖p1-p4‖)` | < 0.22 | Ojos cerrados |
| **MAR** (Mouth Aspect Ratio) | `(‖A‖ + ‖B‖ + ‖C‖) / (3·‖D‖)` | > 0.65 | Bostezos |

### Niveles de alerta

| Nivel | Color | Condición |
|-------|-------|-----------|
| 🟢 **ALERTA** | Verde | Conductor despierto |
| 🟡 **ADVERTENCIA** | Amarillo | Inicio de fatiga (ojos semi-cerrados o bostezo) |
| 🔴 **¡PELIGRO!** | Rojo | Somnolencia severa — alerta sonora activada |

---

## 🛠️ Instalación

### 1. Clona el repositorio o descarga los archivos

### 2. Crea un entorno virtual (recomendado)
```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Linux/macOS
```

### 3. Instala las dependencias
```bash
pip install -r requirements.txt
```

---

## ▶️ Ejecución

```bash
python detector_somnolencia.py
```

---

## ⌨️ Controles

| Tecla | Acción |
|-------|--------|
| `Q` o `ESC` | Salir del programa |
| `R` | Reiniciar contadores de parpadeos y bostezos |
| `C` | **Calibrar** umbral EAR personalizado (mantén ojos abiertos 3 seg.) |

---

## 📊 Interfaz visual (HUD)

- **Panel superior izquierdo**: Barras de EAR y MAR en tiempo real
- **Badge superior derecho**: Nivel de alerta actual
- **Gráfica inferior derecha**: Historial del EAR de los últimos segundos
- **Puntos faciales**: Contorno de ojos (verde/rojo) y boca (cian/amarillo)
- **Mensaje central**: Alerta visual grande en caso de ¡PELIGRO!

---

## 📦 Dependencias

```
mediapipe    >= 0.10.0   → Modelo Face Mesh pre-entrenado
opencv-python >= 4.8.0   → Captura y procesamiento de video
numpy         >= 1.24.0  → Cálculos vectoriales
pygame        >= 2.5.0   → Alertas sonoras sintéticas
```

---

## 🔬 Landmarks de MediaPipe utilizados

```python
RIGHT_EYE = [362, 385, 387, 263, 373, 380]  # Ojo derecho (cámara)
LEFT_EYE  = [33,  160, 158, 133, 153, 144]  # Ojo izquierdo (cámara)
MOUTH     = [61,  39,  0,   269, 291, 405, 17, 181]  # Boca
```

---

## 📐 Estructura del proyecto

```
Taller Final Python/
├── detector_somnolencia.py   # Script principal
├── requirements.txt           # Dependencias
└── README.md                  # Esta documentación
```

---

## ⚠️ Consideraciones importantes

- **Iluminación**: El sistema funciona mejor con buena iluminación frontal.
- **Calibración**: Usa `C` para personalizar el umbral EAR a tu apertura ocular natural.
- **Ángulo**: Posiciona la cámara a la altura del rostro para mayor precisión.
- **Uso**: Este sistema es un prototipo educativo, **no reemplaza** las medidas de seguridad vial.

---

*Desarrollado con ❤️ para el Taller Final de Python · SENA*
