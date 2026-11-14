"""Modulo E - Musica e efeitos sonoros.

Duas fontes, sempre com origem e licenca registradas:

1. Biblioteca do usuario (library/music e library/sfx): faixas baixadas de
   fontes com licenca verificavel (ex.: YouTube Audio Library, Pixabay Music,
   Free Music Archive com CC BY / CC0, Incompetech CC BY). Cada arquivo precisa
   de uma entrada em `licencas.json` com autor, licenca, URL e se permite uso
   comercial. Faixas sem `permite_comercial: true` NUNCA sao usadas.

2. Compositor procedural do estudio (padrao): cria uma trilha ORIGINAL a partir
   de escalas, acordes e timbres sintetizados em Python (numpy). Como e gerada
   pelo proprio estudio, nao ha direitos de terceiros: pode ser usada
   comercialmente. O mesmo vale para os efeitos sonoros sintetizados.

Emocoes suportadas: aventura, alegria, ternura, suspense (leve), celebracao.
"""
import json
import math
import random
import wave
from pathlib import Path

import numpy as np

from .config import LIBRARY

SR = 44100
EMOCOES = ["aventura", "alegria", "ternura", "suspense", "celebracao"]

# tonica (MIDI), modo, BPM, progressao (graus), timbre principal
STYLE = {
    "aventura": dict(root=62, mode="major", bpm=118, prog=[0, 4, 5, 3], lead="pluck", drums=True, swing=0.0),
    "alegria": dict(root=60, mode="major", bpm=124, prog=[0, 5, 3, 4], lead="marimba", drums=True, swing=0.08),
    "ternura": dict(root=65, mode="major", bpm=84, prog=[0, 3, 5, 4], lead="bell", drums=False, swing=0.0),
    "suspense": dict(root=57, mode="minor", bpm=92, prog=[0, 5, 3, 4], lead="pizz", drums=False, swing=0.0),
    "celebracao": dict(root=62, mode="major", bpm=132, prog=[0, 4, 5, 4], lead="marimba", drums=True, swing=0.05),
}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}


def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a=0.005, d=0.1, s=0.5, r=0.1):
    t = np.arange(n) / SR
    e = np.ones(n) * s
    ai, di = int(a * SR), int(d * SR)
    e[:ai] = np.linspace(0, 1, max(1, ai))[:len(e[:ai])]
    e[ai:ai + di] = np.linspace(1, s, max(1, di))[:len(e[ai:ai + di])]
    ri = int(r * SR)
    if ri and n > ri:
        e[-ri:] *= np.linspace(1, 0, ri)
    return e


def tone(freq, dur, kind="pluck", vel=0.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == "marimba":
        w = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t * 25)
        e = np.exp(-t * 6.0)
    elif kind == "bell":
        w = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 3) \
            + 0.2 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t * 6)
        e = np.exp(-t * 2.2)
    elif kind == "pizz":
        w = np.sign(np.sin(2 * np.pi * freq * t)) * 0.3 + np.sin(2 * np.pi * freq * t)
        e = np.exp(-t * 9.0)
    elif kind == "pad":
        w = sum(np.sin(2 * np.pi * freq * (1 + dt) * t) for dt in (-0.004, 0, 0.005)) / 3
        e = env_adsr(n, a=0.25, d=0.3, s=0.8, r=0.4)
    elif kind == "bass":
        w = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
        e = env_adsr(n, a=0.01, d=0.15, s=0.6, r=0.08)
    else:  # pluck (corda dedilhada simples)
        w = sum((0.6 ** k) * np.sin(2 * np.pi * freq * (k + 1) * t) for k in range(5))
        e = np.exp(-t * 5.0)
    out = w * e * vel
    fade = min(n, int(0.004 * SR))
    if fade:
        out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def noise_hit(dur, decay, hp=True, vel=0.3, rnd=None):
    rnd = rnd or np.random.default_rng(1)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rnd.standard_normal(n).astype(np.float32)
    if hp:
        x = np.diff(x, prepend=0)
    return x * np.exp(-t * decay) * vel


def kick(vel=0.8):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    f = 110 * np.exp(-t * 20) + 45
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * vel).astype(np.float32)


def add(buf, sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= buf.shape[0] or i < 0:
        return
    j = min(buf.shape[0], i + len(sig))
    s = sig[: j - i] * gain
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:j, 0] += s * l
    buf[i:j, 1] += s * r


def compose(emocao, seconds, seed=7):
    """Compoe uma faixa original para a emocao pedida, com o tamanho exato."""
    st = STYLE.get(emocao, STYLE["alegria"])
    rnd = random.Random(f"{emocao}{seed}")
    nrng = np.random.default_rng(seed)
    beat = 60.0 / st["bpm"]
    bar = beat * 4
    total = seconds + 1.0
    buf = np.zeros((int(total * SR), 2), dtype=np.float32)
    scale = SCALES[st["mode"]]

    def deg(d, octave=0):
        return st["root"] + scale[d % 7] + 12 * (d // 7 + octave)

    # melodia: motivo de 2 compassos que se repete com variacao
    motif = []
    for b in range(8):
        motif.append(rnd.choice([0, 2, 4, 2, 4, 5, 7, 4]) if b % 2 == 0 else rnd.choice([None, 1, 2, 3, 4, 6]))
    bars = int(total / bar) + 1
    for bi in range(bars):
        t0 = bi * bar
        chord = st["prog"][bi % len(st["prog"])]
        triad = [deg(chord), deg(chord + 2), deg(chord + 4)]
        # pad
        for m in triad:
            add(buf, tone(midi_hz(m - 12), bar + 0.1, "pad", 0.09), t0, pan=rnd.uniform(-0.3, 0.3))
        # baixo
        for k in range(2 if st["bpm"] < 100 else 4):
            step = bar / (2 if st["bpm"] < 100 else 4)
            add(buf, tone(midi_hz(deg(chord, -2)), step * 0.9, "bass", 0.32), t0 + k * step)
        # melodia em colcheias
        for k in range(8):
            d = motif[k]
            if d is None or (bi % 4 == 3 and k > 5):
                continue
            var = 1 if (bi % 4 == 2 and k % 3 == 0) else 0
            m = deg(chord + d + var, 1)
            sw = st["swing"] * beat if k % 2 else 0.0
            add(buf, tone(midi_hz(m), beat * 0.9, st["lead"], 0.22), t0 + k * beat / 2 + sw, pan=0.15)
        # percussao leve
        if st["drums"]:
            for k in range(4):
                if k % 2 == 0:
                    add(buf, kick(0.45), t0 + k * beat)
                add(buf, noise_hit(0.08, 60, vel=0.06, rnd=nrng), t0 + k * beat + beat / 2, pan=0.3)
                add(buf, noise_hit(0.05, 90, vel=0.035, rnd=nrng), t0 + k * beat + beat / 4, pan=-0.3)
            if emocao == "celebracao":
                add(buf, noise_hit(0.6, 5, vel=0.05, rnd=nrng), t0, pan=0.0)
    out = buf[: int(seconds * SR)]
    # fade in/out
    fi, fo = int(0.8 * SR), int(min(2.0, seconds / 4) * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    out[-fo:] *= np.linspace(1, 0, fo)[:, None]
    peak = np.max(np.abs(out)) or 1.0
    return out / peak * 0.8


# ---------------------------------------------------------------------------
# Efeitos sonoros sintetizados (originais)
# ---------------------------------------------------------------------------

def sfx(name, seed=3):
    rng = np.random.default_rng(seed)
    if name == "boing":
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        f = 180 + 260 * np.exp(-t * 6) * (1 + 0.3 * np.sin(2 * np.pi * 14 * t))
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * 0.5).astype(np.float32)
    if name == "pop":
        n = int(0.12 * SR)
        t = np.arange(n) / SR
        f = 900 * np.exp(-t * 30) + 300
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * 0.6).astype(np.float32)
    if name == "brilho":  # chime / magia
        out = np.zeros(int(1.4 * SR), dtype=np.float32)
        for k, m in enumerate([84, 88, 91, 96, 100]):
            s = tone(midi_hz(m), 1.0, "bell", 0.18)
            i = int(k * 0.07 * SR)
            out[i:i + len(s)] += s[: len(out) - i]
        return out
    if name == "whoosh":
        n = int(0.6 * SR)
        x = rng.standard_normal(n).astype(np.float32)
        k = np.ones(40) / 40
        x = np.convolve(x, k, mode="same")
        t = np.linspace(0, 1, n)
        return (x * np.sin(np.pi * t) ** 2 * 1.5).astype(np.float32)
    if name == "passos":
        out = np.zeros(int(1.6 * SR), dtype=np.float32)
        for k in range(5):
            s = noise_hit(0.07, 70, hp=False, vel=0.25, rnd=rng)
            s = np.convolve(s, np.ones(25) / 25, mode="same")
            i = int(k * 0.32 * SR)
            out[i:i + len(s)] += s
        return out
    if name == "risadas":
        out = np.zeros(int(1.0 * SR), dtype=np.float32)
        for k in range(5):
            s = tone(520 + 40 * (k % 2), 0.12, "pluck", 0.12)
            i = int(k * 0.15 * SR)
            out[i:i + len(s)] += s
        return out
    if name == "passaros":
        out = np.zeros(int(2.0 * SR), dtype=np.float32)
        for k in range(4):
            n = int(0.12 * SR)
            t = np.arange(n) / SR
            f = 2500 + 900 * np.sin(2 * np.pi * 18 * t)
            s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) * 0.08
            i = int((0.2 + k * 0.4 + rng.uniform(0, 0.1)) * SR)
            out[i:i + n] += s.astype(np.float32)
        return out
    return np.zeros(int(0.1 * SR), dtype=np.float32)


SFX_INFO = {k: "sintetizado pelo estudio (original, livre para uso comercial)" for k in
            ["boing", "pop", "brilho", "whoosh", "passos", "risadas", "passaros"]}


# ---------------------------------------------------------------------------
# Biblioteca com licencas
# ---------------------------------------------------------------------------

def library_index(kind="music"):
    p = LIBRARY / kind / "licencas.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("faixas", [])
    except json.JSONDecodeError:
        return []


def pick_library_track(emocao):
    """Escolhe uma faixa da biblioteca do usuario com licenca comercial valida."""
    for item in library_index("music"):
        f = LIBRARY / "music" / item.get("arquivo", "")
        if item.get("emocao") == emocao and item.get("permite_comercial") is True and f.exists():
            return f, item
    return None, None


def write_wav(path, data, sr=SR):
    data = np.asarray(data, dtype=np.float32)
    if data.ndim == 1:
        data = data[:, None]
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
