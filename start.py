"""
start.py — Arranca ambos servidores (FastAPI + Django) en paralelo
Uso: python start.py
"""

import subprocess
import sys
import os
import time
import signal
import threading

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FASTAPI_CMD = [
    sys.executable, "-m", "uvicorn",
    "main:app",
    "--host", "0.0.0.0",
    "--port", "8001",
    "--reload",
]

DJANGO_CMD = [
    sys.executable, "manage.py",
    "runserver", "8000",
    "--noreload",
]

procs = []


def run(cmd, cwd, label):
    print(f"\n[{label}] Iniciando en {cwd}")
    print(f"[{label}] Comando: {' '.join(cmd)}\n")
    p = subprocess.Popen(
        cmd, cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    procs.append(p)
    for line in p.stdout:
        print(f"[{label}] {line}", end="")


def shutdown(sig, frame):
    print("\n\n[!] Deteniendo servidores...")
    for p in procs:
        p.terminate()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("=" * 60)
    print("  DriveSafe AI -- Sistema de Deteccion de Somnolencia")
    print("=" * 60)
    print("  FastAPI (Backend)  -> http://localhost:8001")
    print("  FastAPI (Swagger)  -> http://localhost:8001/docs")
    print("  Django  (Frontend) -> http://localhost:8000")
    print("=" * 60)
    print("  Ctrl+C para detener ambos servidores")
    print("=" * 60)

    # Arrancar en hilos paralelos
    t1 = threading.Thread(
        target=run,
        args=(FASTAPI_CMD, os.path.join(BASE_DIR, "backend"), "FastAPI"),
        daemon=True
    )
    t2 = threading.Thread(
        target=run,
        args=(DJANGO_CMD, os.path.join(BASE_DIR, "frontend"), "Django"),
        daemon=True
    )

    t1.start()
    time.sleep(2)   # dar tiempo a FastAPI de arrancar primero (descarga el modelo)
    t2.start()

    t1.join()
    t2.join()
