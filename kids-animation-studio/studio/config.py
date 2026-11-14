"""Configuracoes globais do Kids Animation Studio AI.

Tudo e salvo localmente em `config.json` na raiz do estudio. Nenhuma chave de API
e gravada aqui: chaves ficam em variaveis de ambiente (ELEVENLABS_API_KEY,
ANTHROPIC_API_KEY) para nao vazarem em arquivos compartilhados.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "library"
PROJECTS = Path(os.environ.get("KAS_PROJETOS", ROOT / "projetos"))
MODELS = ROOT / "modelos"
VOICES_DIR = MODELS / "vozes"
CONFIG_FILE = ROOT / "config.json"

QUALITY_PRESETS = {
    # nome: (largura base 16:9, altura base, amostras Cycles)
    "teste": (320, 180, 4),  # so para validar o fluxo rapidamente
    "rascunho": (640, 360, 12),
    "padrao": (1280, 720, 24),
    "alta": (1920, 1080, 48),
}

DEFAULTS = {
    "idioma": "pt-BR",
    "qualidade": "rascunho",
    "fps": 24,
    "proporcao": "16:9",
    "modo_ensino": True,
    "exigir_aprovacao": True,
    # provedores de voz: "piper" (local, gratis), "elevenlabs" (pago por creditos),
    # "importado" (arquivos gravados manualmente)
    "voz_provedor": "piper",
    "voz_narrador_piper": "pt_BR-cadu-medium",
    "elevenlabs_voz_preferida": "Bianca",
    "elevenlabs_modelo": "eleven_multilingual_v2",
    # Seguranca financeira: nada que consome creditos roda sem isso = True
    "permitir_servicos_pagos": False,
    # Roteirista: "local" (modelos de historia, gratis) ou "claude" (API paga)
    "roteirista": "local",
    "claude_modelo": "claude-opus-5-5",
    "volume_musica_db": -20,
    "reducao_musica_durante_fala_db": -12,
    "blender_executavel": "",
}


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return cfg


def save_config(cfg):
    clean = {k: v for k, v in cfg.items() if k in DEFAULTS}
    CONFIG_FILE.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def resolution(quality, aspect):
    w, h, samples = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["rascunho"])
    if aspect == "9:16":
        w, h = h, w
    return w, h, samples
