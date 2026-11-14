"""Modulo F - Editor audiovisual (FFmpeg + numpy).

Etapas:
  1. Converte os quadros PNG de cada cena em um clipe de video;
  2. Une as cenas com transicoes suaves (crossfade);
  3. Monta as trilhas de audio: vozes, efeitos e musica, com "ducking"
     (a musica abaixa sozinha quando alguem fala);
  4. Gera legendas (.ass estilizada para queimar no video e .srt para upload);
  5. Exporta MP4 16:9 e 9:16 e uma previa leve para revisao.
"""
import json
import subprocess
from pathlib import Path

import numpy as np

from . import music
from .voice import read_wav

SR = music.SR
FONT_CANDIDATES = [
    "library/fonts/Baloo2-Bold.ttf", "library/fonts/Fredoka-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("FFmpeg falhou:\n" + " ".join(map(str, cmd)) + "\n" + r.stderr[-2000:])
    return r


def font_path(root):
    for f in FONT_CANDIDATES:
        p = Path(f) if Path(f).is_absolute() else root / f
        if p.exists():
            return p
    for p in (root / "library" / "fonts").glob("*.ttf"):
        return p
    return None


def probe_duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(r.stdout.strip())


def frames_to_clip(frames_dir, out_mp4, render_fps, fps_out=24):
    frames = sorted(Path(frames_dir).glob("quadro_*.png"))
    if not frames:
        raise FileNotFoundError(f"Nenhum quadro em {frames_dir}")
    first = int(frames[0].stem.split("_")[1])
    run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(render_fps), "-start_number", str(first),
         "-i", str(Path(frames_dir) / "quadro_%04d.png"), "-r", str(fps_out), "-c:v", "libx264", "-preset", "medium",
         "-crf", "17", "-pix_fmt", "yuv420p", str(out_mp4)])
    return len(frames) / render_fps


def join_clips(clips, durations, out_mp4, transition):
    """Une clipes com crossfade. Retorna o instante de inicio de cada cena."""
    starts = []
    acc = 0.0
    for i, d in enumerate(durations):
        starts.append(round(acc, 3))
        acc += d - transition
    if len(clips) == 1:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clips[0]), "-c", "copy", str(out_mp4)])
        return starts
    inputs = []
    for c in clips:
        inputs += ["-i", str(c)]
    chain = []
    prev = "[0:v]"
    for i in range(1, len(clips)):
        out = f"[v{i}]"
        offset = starts[i]
        chain.append(f"{prev}[{i}:v]xfade=transition=fade:duration={transition}:offset={offset:.3f}{out}")
        prev = out
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chain), "-map", prev,
         "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(out_mp4)])
    return starts


def load_audio_any(path):
    """Le qualquer audio (mp3/wav) convertendo com ffmpeg para estereo 44.1k."""
    tmp = Path(str(path) + ".tmp.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ar", str(SR), "-ac", "2", str(tmp)])
    import wave
    with wave.open(str(tmp), "rb") as w:
        d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    tmp.unlink()
    return d.reshape(-1, 2)


def place(buf, sig, t, gain=1.0):
    i = int(t * SR)
    if i < 0 or i >= len(buf):
        return
    if sig.ndim == 1:
        sig = np.stack([sig, sig], axis=1)
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def mix_audio(total, voice_events, sfx_events, music_segments, cfg, out_wav, music_sources):
    """voice_events: [(wav, t)]; sfx_events: [(nome, t)]; music_segments: [{emocao, inicio, fim}]."""
    n = int((total + 0.5) * SR)
    voice = np.zeros((n, 2), np.float32)
    for wav, t in voice_events:
        d, sr = read_wav(wav)
        place(voice, d, t, 1.0)
    fx = np.zeros((n, 2), np.float32)
    for name, t in sfx_events:
        g = 0.25 if name == "passaros" else (0.35 if name == "passos" else 0.5)
        place(fx, music.sfx(name), t, g)
    mus = np.zeros((n, 2), np.float32)
    for k, seg in enumerate(music_segments):
        length = seg["fim"] - seg["inicio"]
        track, info = music.pick_library_track(seg["emocao"])
        if track is not None:
            data = load_audio_any(track)
            reps = int(np.ceil(length * SR / len(data)))
            data = np.tile(data, (reps, 1))[: int(length * SR)]
            fo = int(min(2.0, length / 3) * SR)
            data[-fo:] *= np.linspace(1, 0, fo)[:, None]
            music_sources.append({"emocao": seg["emocao"], "arquivo": str(track), **info})
        else:
            data = music.compose(seg["emocao"], length, seed=7 + k)
            music_sources.append({"emocao": seg["emocao"], "origem": "composta pelo estudio (procedural, original)",
                                  "licenca": "propria - livre para uso comercial"})
        if k > 0:  # crossfade de entrada
            fi = int(1.2 * SR)
            data[:fi] *= np.linspace(0, 1, fi)[:, None]
        place(mus, data, seg["inicio"])
    # ducking: envelope da voz suavizado
    vmono = np.abs(voice[:, 0])
    win = int(0.05 * SR)
    kernel = np.ones(win) / win
    env = np.convolve(vmono, kernel, mode="same")
    active = (env > 0.01).astype(np.float32)
    # ataque 80 ms / soltura 400 ms
    sm = np.convolve(active, np.ones(int(0.4 * SR)) / int(0.4 * SR), mode="same")
    sm = np.clip(sm * 3, 0, 1)
    base_db = cfg.get("volume_musica_db", -20)
    duck_db = cfg.get("reducao_musica_durante_fala_db", -12)
    gain = 10 ** ((base_db + duck_db * sm) / 20)
    mix = voice * 1.0 + fx * 0.8 + mus * gain[:, None]
    peak = np.max(np.abs(mix)) or 1.0
    if peak > 0.98:
        mix = mix / peak * 0.98
    music.write_wav(out_wav, mix)
    stems = Path(out_wav).parent
    music.write_wav(stems / "trilha_vozes.wav", voice)
    music.write_wav(stems / "trilha_musica.wav", mus * gain[:, None])
    music.write_wav(stems / "trilha_efeitos.wav", fx * 0.8)
    return {"pico": float(peak)}


# ---------------------------------------------------------------------------
# Legendas
# ---------------------------------------------------------------------------

def _ts_srt(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def _ts_ass(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def wrap(text, width=38):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def write_subtitles(cues, srt_path, ass_path, w, h, font_name="DejaVu Sans"):
    """cues: [{t0, t1, texto, falante_nome, cor}] em tempo global."""
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{_ts_srt(c['t0'])} --> {_ts_srt(c['t1'])}\n" + "\n".join(wrap(c["texto"], 42)) + "\n\n")
    vertical = h > w
    size = int(h * (0.034 if vertical else 0.062))
    margin_v = int(h * (0.20 if vertical else 0.06))
    width_chars = 22 if vertical else 40
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narrador,{font_name},{size},&H00FFFFFF,&H00FFFFFF,&H00402A1A,&H64000000,-1,0,0,0,100,100,0,0,1,{max(2, size // 9)},{max(1, size // 18)},2,30,30,{margin_v},1
Style: Fala,{font_name},{size},&H0066E6FF,&H00FFFFFF,&H00402A1A,&H64000000,-1,0,0,0,100,100,0,0,1,{max(2, size // 9)},{max(1, size // 18)},2,30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(head)
        for c in cues:
            style = "Narrador" if c.get("narrador") else "Fala"
            txt = "\\N".join(wrap(c["texto"], width_chars))
            f.write(f"Dialogue: 0,{_ts_ass(c['t0'])},{_ts_ass(c['t1'])},{style},,0,0,0,,{{\\fad(120,120)}}{txt}\n")


def _escape_filter_path(p):
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def export_final(video, audio_wav, ass_path, out_mp4, fonts_dir=None, extra_vf=None, size=None):
    vf = []
    if extra_vf:
        vf.append(extra_vf)
    sub = f"subtitles='{_escape_filter_path(ass_path)}'"
    if fonts_dir:
        sub += f":fontsdir='{_escape_filter_path(fonts_dir)}'"
    vf.append(sub)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio_wav),
         "-vf", ",".join(vf), "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", "-shortest", str(out_mp4)])


def make_alt_aspect(video, out_mp4, src_vertical, title=None, font=None):
    """Cria a versao na outra proporcao com fundo desfocado (sem cortar personagens)."""
    if not src_vertical:  # 16:9 -> 9:16
        W, H = 720, 1280
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2,eq=brightness=-0.06[bg];"
              f"[0:v]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2")
        if title and font:
            t = title.replace(":", "\\:").replace("'", "\u2019")
            fs = min(52, int((W - 50) / (0.62 * max(1, len(title)))))
            fc += (f",drawtext=fontfile='{_escape_filter_path(font)}':text='{t}':fontcolor=white:fontsize={fs}:"
                   f"borderw=5:bordercolor=0x402A1A:x=(w-text_w)/2:y=170")
    else:  # 9:16 -> 16:9
        W, H = 1280, 720
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2,eq=brightness=-0.06[bg];"
              f"[0:v]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-filter_complex", fc + "[v]", "-map", "[v]",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", str(out_mp4)])
    return W, H


def make_preview(final_mp4, out_mp4):
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final_mp4), "-vf", "scale=-2:360", "-c:v", "libx264",
         "-crf", "28", "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k", str(out_mp4)])


def contact_sheet(video, out_png, n=6):
    """Folha de contato: quadros espalhados do video (evidencia visual rapida)."""
    d = probe_duration(video)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf",
         f"fps={n}/{d:.2f},scale=480:-2,tile=3x{(n + 2) // 3}", "-frames:v", "1", str(out_png)])
