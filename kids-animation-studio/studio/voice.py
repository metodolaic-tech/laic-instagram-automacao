"""Modulo D - Voz e narracao.

Provedores (em ordem de preferencia por custo):
  1. "importado": voce grava (celular, Audacity) e coloca os arquivos em
     projetos/<projeto>/audio/importar/  com o nome  cena01_narracao.wav,
     cena01_fala1.wav ...  O estudio usa esses arquivos no lugar da sintese.
  2. "piper": sintese neural LOCAL e GRATUITA (piper-tts, GPL-3.0). Vozes pt-BR
     cadu e jeff (dados e modelo-base CC0) e faber (dados CC0, modelo-base
     Hi-Fi TTS CC BY 4.0 -> atribuicao recomendada). Roda em CPU.
  3. "elevenlabs": voz Bianca (preferencia do usuario), se existir na sua conta.
     CONSOME CREDITOS: so roda com ELEVENLABS_API_KEY definida e
     `permitir_servicos_pagos = true`. Nao contorna limites da plataforma.

Cada personagem tem voz propria e consistente (modelo + tom), definida na ficha.
O tom infantil e obtido deslocando a altura (pitch) sem mudar a velocidade.
"""
import json
import os
import subprocess
import urllib.request
import wave
from pathlib import Path

import numpy as np

from .config import VOICES_DIR

SR = 44100

PIPER_VOICES = {
    "pt_BR-cadu-medium": {"licenca": "Dados CC0; modelo-base rdh CC0", "comercial": True, "atribuicao": False},
    "pt_BR-jeff-medium": {"licenca": "Dados CC0; modelo-base rdh CC0", "comercial": True, "atribuicao": False},
    "pt_BR-faber-medium": {"licenca": "Dados CC0; modelo-base Hi-Fi TTS (CC BY 4.0)", "comercial": True,
                           "atribuicao": True},
}
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR"


def download_voices(names=None, log=print):
    """Baixa as vozes Piper pt-BR (gratis) do Hugging Face."""
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    for name in names or PIPER_VOICES:
        speaker = name.split("-")[1]
        for ext in (".onnx", ".onnx.json"):
            dest = VOICES_DIR / f"{name}{ext}"
            if dest.exists() and dest.stat().st_size > 1000:
                continue
            url = f"{HF_BASE}/{speaker}/medium/{name}{ext}"
            log(f"Baixando {url}")
            urllib.request.urlretrieve(url, dest)
        card = VOICES_DIR / f"{name}.MODEL_CARD"
        if not card.exists():
            try:
                urllib.request.urlretrieve(f"{HF_BASE}/{speaker}/medium/MODEL_CARD", card)
            except Exception:
                pass


def available_piper_voices():
    return sorted(p.name[:-5] for p in VOICES_DIR.glob("*.onnx"))


_PIPER_CACHE = {}


def _piper(model):
    from piper import PiperVoice  # import tardio: so quando necessario
    if model not in _PIPER_CACHE:
        path = VOICES_DIR / f"{model}.onnx"
        if not path.exists():
            raise FileNotFoundError(
                f"Voz {model} nao encontrada em {VOICES_DIR}. Rode: python kas.py baixar-vozes")
        _PIPER_CACHE[model] = PiperVoice.load(str(path))
    return _PIPER_CACHE[model]


def synth_piper(text, out_wav, model, speed=1.0):
    from piper import SynthesisConfig
    voice = _piper(model)
    cfg = SynthesisConfig(length_scale=1.0 / max(0.5, speed), noise_scale=0.5, noise_w_scale=0.4)
    tmp = str(out_wav) + ".raw.wav"
    with wave.open(tmp, "wb") as w:
        voice.synthesize_wav(text, w, syn_config=cfg)
    return tmp


def synth_elevenlabs(text, out_mp3, cfg):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise PermissionError("ELEVENLABS_API_KEY nao definida.")
    if not cfg.get("permitir_servicos_pagos"):
        raise PermissionError("ElevenLabs consome creditos: ative 'permitir_servicos_pagos' para autorizar.")
    voice_id = cfg.get("elevenlabs_voice_id") or find_elevenlabs_voice(cfg.get("elevenlabs_voz_preferida", "Bianca"), key)
    body = json.dumps({"text": text, "model_id": cfg.get("elevenlabs_modelo", "eleven_multilingual_v2"),
                       "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        Path(out_mp3).write_bytes(r.read())
    return str(out_mp3)


def find_elevenlabs_voice(name, key):
    req = urllib.request.Request("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
    with urllib.request.urlopen(req, timeout=60) as r:
        voices = json.loads(r.read())["voices"]
    for v in voices:
        if v["name"].lower().startswith(name.lower()):
            return v["voice_id"]
    raise LookupError(f"A voz '{name}' nao esta disponivel na sua conta ElevenLabs.")


def to_final_wav(src, dst, pitch=1.0, gain_db=0.0):
    """Converte para WAV 44.1 kHz mono, com ajuste de tom (pitch) sem mudar a duracao."""
    filters = []
    if abs(pitch - 1.0) > 0.01:
        filters += [f"asetrate={int(22050 * pitch)}", "aresample=22050", f"atempo={1 / pitch:.4f}"]
    filters += ["highpass=f=70", "acompressor=threshold=-18dB:ratio=3:attack=5:release=80",
                f"volume={gain_db}dB", "silenceremove=start_periods=1:start_threshold=-50dB",
                "areverse", "silenceremove=start_periods=1:start_threshold=-50dB", "areverse"]
    pre = ["-af", ",".join(filters)]
    # asetrate precisa da taxa original; forcamos 22050 na entrada
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "22050", "-ac", "1", "-f", "wav", str(dst) + ".22k.wav"]
    subprocess.run(cmd, check=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(dst) + ".22k.wav", *pre, "-ar", str(SR), "-ac", "1", str(dst)]
    subprocess.run(cmd, check=True)
    os.remove(str(dst) + ".22k.wav")


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
        return data, w.getframerate()


def duration(path):
    d, sr = read_wav(path)
    return len(d) / sr


def envelope(path, fps=12):
    """Volume da fala por quadro (0..1) para a sincronia labial."""
    d, sr = read_wav(path)
    hop = int(sr / fps)
    vals = []
    for i in range(0, len(d), hop):
        seg = d[i:i + hop]
        vals.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    if not vals:
        return []
    peak = max(vals) or 1.0
    out = []
    for v in vals:
        x = v / peak
        x = 0.0 if x < 0.12 else min(1.0, (x - 0.12) / 0.6)
        out.append(round(x, 3))
    return out


def voice_for(speaker_sheet, cfg):
    """Configuracao de voz do narrador ou personagem."""
    if speaker_sheet is None:
        return {"provedor": cfg.get("voz_provedor", "piper"), "modelo": cfg.get("voz_narrador_piper", "pt_BR-cadu-medium"),
                "tom": 1.0, "velocidade": 0.95}
    v = dict(speaker_sheet.get("voz", {}))
    v.setdefault("provedor", "piper")
    if cfg.get("voz_provedor") == "elevenlabs":
        v["provedor"] = "elevenlabs"
    return v


def synthesize_line(text, out_wav, vcfg, cfg, imported=None, log=print):
    """Gera (ou importa) um audio de fala. Retorna dict com metadados de origem."""
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    if imported and Path(imported).exists():
        to_final_wav(imported, out_wav)
        return {"origem": "importado", "arquivo_original": str(imported), "licenca": "gravacao propria do usuario"}
    prov = vcfg.get("provedor", "piper")
    if prov == "elevenlabs":
        try:
            mp3 = synth_elevenlabs(text, str(out_wav) + ".mp3", cfg)
            to_final_wav(mp3, out_wav)
            os.remove(mp3)
            return {"origem": "elevenlabs", "voz": cfg.get("elevenlabs_voz_preferida"),
                    "licenca": "conforme plano ElevenLabs da sua conta (verifique uso comercial)"}
        except Exception as e:  # cai para a alternativa gratuita
            log(f"ElevenLabs indisponivel ({e}). Usando Piper local (gratis).")
            prov = "piper"
    model = vcfg.get("modelo", "pt_BR-cadu-medium")
    if model not in available_piper_voices() and available_piper_voices():
        model = available_piper_voices()[0]
    raw = synth_piper(text, out_wav, model, speed=vcfg.get("velocidade", 1.0))
    to_final_wav(raw, out_wav, pitch=float(vcfg.get("tom", 1.0)))
    os.remove(raw)
    info = PIPER_VOICES.get(model, {})
    return {"origem": "piper (local)", "voz": model, "tom": vcfg.get("tom", 1.0), "licenca": info.get("licenca", "ver MODEL_CARD")}
