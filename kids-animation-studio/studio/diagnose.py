"""Fase 1 - Diagnostico do ambiente.

Verifica sistema operacional, hardware, ferramentas e licencas, e diz o que
falta instalar. Nada e instalado automaticamente.
"""
import os
import platform
import shutil
import subprocess
import sys

from .config import VOICES_DIR, load_config


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""


def find_blender(cfg=None):
    """Procura o Blender instalado (executavel). Retorna caminho ou None."""
    cfg = cfg or load_config()
    cands = [cfg.get("blender_executavel"), os.environ.get("BLENDER_PATH"), shutil.which("blender")]
    if platform.system() == "Windows":
        base = r"C:\Program Files\Blender Foundation"
        if os.path.isdir(base):
            for d in sorted(os.listdir(base), reverse=True):
                cands.append(os.path.join(base, d, "blender.exe"))
    elif platform.system() == "Darwin":
        cands.append("/Applications/Blender.app/Contents/MacOS/Blender")
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def bpy_version():
    out = _run([sys.executable, "-c", "import bpy;print(bpy.app.version_string)"])
    lines = [l for l in out.strip().splitlines() if l and l[0].isdigit()]
    return lines[-1] if lines else None


def gpu_info():
    if shutil.which("nvidia-smi"):
        out = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
        if out.strip():
            return out.strip()
    return None


def memory_gb():
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                return round(int(f.readline().split()[1]) / 1024 / 1024, 1)
        if platform.system() == "Windows":
            import ctypes

            class M(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("t", ctypes.c_ulonglong),
                            ("a", ctypes.c_ulonglong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
            m = M()
            m.l = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.t / 1024 ** 3, 1)
    except Exception:
        pass
    return None


def diagnose():
    cfg = load_config()
    ff = shutil.which("ffmpeg")
    ffv = " ".join(_run(["ffmpeg", "-version"]).split()[:3]) if ff else None
    blender = find_blender(cfg)
    blender_v = _run([blender, "--version"]).splitlines()[0] if blender else None
    bpy_v = None if blender else bpy_version()
    try:
        import piper  # noqa: F401
        piper_ok = True
    except Exception:
        piper_ok = False
    voices = sorted(p.name[:-5] for p in VOICES_DIR.glob("*.onnx")) if VOICES_DIR.exists() else []
    try:
        import numpy  # noqa: F401
        import PIL  # noqa: F401
        libs = True
    except Exception:
        libs = False
    items = [
        {"item": "Sistema", "ok": True, "valor": f"{platform.system()} {platform.release()} ({platform.machine()})"},
        {"item": "Python", "ok": sys.version_info >= (3, 10), "valor": sys.version.split()[0]},
        {"item": "CPU (núcleos)", "ok": True, "valor": os.cpu_count()},
        {"item": "Memória RAM (GB)", "ok": (memory_gb() or 8) >= 8, "valor": memory_gb()},
        {"item": "GPU NVIDIA", "ok": True, "valor": gpu_info() or "não encontrada (render em CPU, mais lento)"},
        {"item": "FFmpeg", "ok": bool(ff), "valor": ffv or "FALTANDO - instale (gratuito, LGPL/GPL)"},
        {"item": "Blender", "ok": bool(blender or bpy_v),
         "valor": blender_v or (f"módulo bpy {bpy_v}" if bpy_v else "FALTANDO - instale Blender 4.2+ (gratuito, GPL)")},
        {"item": "Piper TTS", "ok": piper_ok, "valor": "instalado" if piper_ok else "FALTANDO - pip install piper-tts"},
        {"item": "Vozes pt-BR", "ok": bool(voices), "valor": ", ".join(voices) or "FALTANDO - python kas.py baixar-vozes"},
        {"item": "numpy/Pillow", "ok": libs, "valor": "ok" if libs else "FALTANDO - pip install -r requirements.txt"},
        {"item": "ElevenLabs (opcional, pago)", "ok": True,
         "valor": "chave definida" if os.environ.get("ELEVENLABS_API_KEY") else "sem chave (usando voz local gratuita)"},
        {"item": "Claude API (opcional, pago)", "ok": True,
         "valor": "chave definida" if os.environ.get("ANTHROPIC_API_KEY") else "sem chave (roteirista local gratuito)"},
        {"item": "Serviços pagos autorizados", "ok": True,
         "valor": "SIM" if cfg.get("permitir_servicos_pagos") else "NÃO (nenhum crédito será consumido)"},
    ]
    ready = all(i["ok"] for i in items)
    return {"pronto": ready, "itens": items, "blender": blender, "bpy": bpy_v}


def print_report(d=None):
    d = d or diagnose()
    print("\n=== Diagnóstico do Kids Animation Studio AI ===\n")
    for i in d["itens"]:
        print(f" [{'OK' if i['ok'] else '!!'}] {i['item']:<30} {i['valor']}")
    print("\nPronto para produzir!" if d["pronto"] else "\nAlgo está faltando: veja os itens marcados com !!")
    return d
