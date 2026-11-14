"""Orquestrador da producao (Fase 4 - Automacao).

Conecta os modulos na ordem:
  roteiro -> personagens -> voz -> musica -> animacao -> edicao -> publicacao -> relatorio

* Cada etapa grava seus arquivos na pasta do projeto e marca o estado em
  projeto.json. Se algo falhar (ou o computador desligar), basta rodar de novo:
  etapas concluidas sao puladas e o render continua do ultimo quadro salvo.
* Portoes de aprovacao: depois do roteiro e dos personagens a producao para e
  espera sua aprovacao (no painel ou com `python kas.py aprovar`).
"""
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

from . import art_director as ad
from . import editor, music, publisher, teaching, timeline, voice, writer
from .config import PROJECTS, ROOT, load_config, resolution
from .diagnose import find_blender

ETAPAS = ["roteiro", "personagens", "voz", "musica", "animacao", "edicao", "publicacao", "relatorio"]
APROVACAO = {"roteiro", "personagens"}
BUILDER = ROOT / "studio" / "blender" / "scene_builder.py"

STUDIO_SET = {"id": "estudio", "nome": "Estúdio", "chao": ["#DCE6F2", "#C9D6E8"], "colinas": "#C9D6E8",
              "ceu_topo": "#9EC5F0", "ceu_horizonte": "#EAF2FB", "luz_ceu": 1.2, "sol_cor": "#FFF6E8",
              "sol_forca": 3.0, "sol_elevacao": 50, "sol_azimute": -30, "nuvens": 0, "elementos": []}


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


class Project:
    def __init__(self, pid):
        self.id = pid
        self.dir = PROJECTS / pid
        self.file = self.dir / "projeto.json"
        self._lock = threading.Lock()
        self.data = json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else None

    # ------------------------------------------------------------------
    @classmethod
    def create(cls, tema, duracao=30, proporcao="16:9", faixa="4-6", categoria=None, qualidade=None,
               cenario=None, voz=None, modo_ensino=None):
        cfg = load_config()
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        pid = f"{stamp}_{ad.slug(tema)[:40]}"
        p = cls(pid)
        p.dir.mkdir(parents=True, exist_ok=True)
        for sub in ["roteiro", "personagens", "audio/vozes", "audio/importar", "cenas", "final"]:
            (p.dir / sub).mkdir(parents=True, exist_ok=True)
        p.data = {
            "id": pid, "tema": tema, "criado_em": now(),
            "parametros": {"duracao": int(duracao), "proporcao": proporcao, "faixa": faixa, "categoria": categoria,
                           "qualidade": qualidade or cfg["qualidade"], "cenario": cenario,
                           "voz": voz or cfg["voz_provedor"],
                           "modo_ensino": cfg["modo_ensino"] if modo_ensino is None else bool(modo_ensino)},
            "etapas": {e: {"status": "pendente"} for e in ETAPAS},
            "progresso": {"etapa": None, "pct": 0, "mensagem": "Projeto criado"},
            "tempos": {},
        }
        p.save()
        (p.dir / "audio" / "importar" / "LEIA-ME.txt").write_text(
            "Coloque aqui gravacoes proprias para substituir a voz sintetica.\n"
            "Nomes: cena01_narracao.wav, cena01_fala1.wav, cena01_fala2.wav, cena02_narracao.wav ...\n"
            "Depois, refaca a etapa 'voz'.\n", encoding="utf-8")
        return p

    @classmethod
    def list_all(cls):
        out = []
        if PROJECTS.exists():
            for d in sorted(PROJECTS.iterdir(), reverse=True):
                if (d / "projeto.json").exists():
                    out.append(cls(d.name).data)
        return out

    def save(self):
        with self._lock:
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.file)

    def reload(self):
        self.data = json.loads(self.file.read_text(encoding="utf-8"))

    def log(self, msg, etapa=None, pct=None):
        line = f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(self.dir / "log.txt", "a", encoding="utf-8") as f:
            f.write(line + "\n")
        prog = self.data["progresso"]
        prog["mensagem"] = msg
        if etapa:
            prog["etapa"] = etapa
        if pct is not None:
            prog["pct"] = int(pct)
        self.save()

    def status(self, etapa):
        return self.data["etapas"][etapa]["status"]

    def set_status(self, etapa, status, **extra):
        self.data["etapas"][etapa].update({"status": status, "atualizado_em": now(), **extra})
        self.save()

    def approve(self, etapa):
        if self.status(etapa) == "aguardando_aprovacao":
            self.set_status(etapa, "concluida", aprovado_em=now())
            self.log(f"Etapa '{etapa}' aprovada pelo usuário.")
            return True
        return False

    def reset_from(self, etapa):
        """Refaz a etapa indicada e todas as seguintes."""
        idx = ETAPAS.index(etapa)
        for e in ETAPAS[idx:]:
            self.data["etapas"][e] = {"status": "pendente"}
        if etapa in ("roteiro", "personagens", "voz", "animacao"):
            # quadros antigos nao valem mais se o roteiro/vozes mudarem
            if etapa != "animacao":
                shutil.rmtree(self.dir / "cenas", ignore_errors=True)
                (self.dir / "cenas").mkdir()
        self.save()

    def path(self, *parts):
        return self.dir.joinpath(*parts)

    def read_json(self, *parts):
        return json.loads(self.path(*parts).read_text(encoding="utf-8"))

    def write_json(self, obj, *parts):
        self.path(*parts).parent.mkdir(parents=True, exist_ok=True)
        self.path(*parts).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def teach(self, etapa):
        if not self.data["parametros"].get("modo_ensino"):
            return
        txt = teaching.explain(etapa)
        aula = self.path("AULA.md")
        if not aula.exists():
            aula.write_text(f"# Aula: como este vídeo foi produzido\n\nProjeto: **{self.data['tema']}**\n\n",
                            encoding="utf-8")
        with open(aula, "a", encoding="utf-8") as f:
            f.write(txt + "\n")
        self.log(f"[MODO ENSINO] {teaching.ETAPAS[etapa]['titulo']}: {teaching.ETAPAS[etapa]['o_que']}")


# ---------------------------------------------------------------------------
# Execucao das etapas
# ---------------------------------------------------------------------------

def chars_of(p):
    story = p.read_json("roteiro", "historia.json")
    return {cid: ad.load_character(cid) for cid in story["personagens"]}


def run_blender(spec_path, log, total_frames=None):
    blender = find_blender()
    if blender:
        cmd = [blender, "-b", "--factory-startup", "-noaudio", "-P", str(BUILDER), "--", str(spec_path)]
    else:
        cmd = [sys.executable, str(BUILDER), str(spec_path)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    tail = []
    done = 0
    for line in proc.stdout:
        tail = (tail + [line.rstrip()])[-40:]
        if "Saved:" in line:
            done += 1
            if log and (done % 6 == 0 or done == total_frames):
                log(done)
    proc.wait()
    if proc.returncode != 0 or not any("KAS_OK" in l for l in tail):
        raise RuntimeError("Blender falhou:\n" + "\n".join(tail[-25:]))


def step_roteiro(p, cfg):
    prm = p.data["parametros"]
    story = writer.write_story(p.data["tema"], prm["duracao"], prm["faixa"], prm.get("categoria"), cfg,
                               cenario=prm.get("cenario"))
    p.write_json(story, "roteiro", "historia.json")
    chars = [ad.load_character(c) for c in story["personagens"]]
    p.path("roteiro", "roteiro.md").write_text(writer.script_markdown(story, chars), encoding="utf-8")
    p.data["titulo"] = story["titulo"]
    p.log(f"Roteiro pronto: '{story['titulo']}' com {len(story['cenas'])} cenas ({story['motor']}).")


def step_personagens(p, cfg):
    story = p.read_json("roteiro", "historia.json")
    out = []
    for cid in story["personagens"]:
        sheet = ad.load_character(cid)
        p.path("personagens", f"{cid}.md").write_text(ad.character_sheet_markdown(sheet), encoding="utf-8")
        png = p.path("personagens", f"{cid}.png")
        if not png.exists():
            p.log(f"Renderizando folha de modelo 3D de {sheet['nome']}...")
            spec = {"saida": str(p.path("personagens")), "duracao": 1.0, "semente": 5,
                    "render": {"largura": 540, "altura": 540, "fps": 12, "amostras": 16},
                    "cenario": STUDIO_SET,
                    "personagens": [{"ficha": sheet, "inicio": [0, 0], "direcao": 15,
                                     "acoes": [{"tipo": "expressao", "t0": 0, "expressao": "feliz"},
                                               {"tipo": "acenar", "t0": 0.0, "t1": 3.0, "lado": 1}]}],
                    "camera": {"plano": "medio", "movimento": "parado"},
                    "quadro_unico": 8, "nome_quadro": f"{cid}.png"}
            sp = p.path("personagens", f"{cid}_spec.json")
            sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            run_blender(sp, None)
            sp.unlink()
        out.append(cid)
    p.log(f"Fichas e folhas de modelo prontas: {', '.join(out)}.")


def step_voz(p, cfg):
    story = p.read_json("roteiro", "historia.json")
    chars = chars_of(p)
    prm = p.data["parametros"]
    cfg = dict(cfg, voz_provedor=prm.get("voz", cfg["voz_provedor"]))
    plans, fontes = [], []
    n = len(story["cenas"])
    for i, sc in enumerate(story["cenas"]):
        k = sc["numero"]
        lines = []
        items = [("narracao", None, sc["narracao"], "neutro")] + \
                [("fala", f["personagem"], f["texto"], f["emocao"]) for f in sc["falas"]]
        fala_idx = 0
        for tipo, who, text, emo in items:
            if not text.strip():
                continue
            if tipo == "fala":
                fala_idx += 1
                name = f"cena{k:02d}_fala{fala_idx}"
            else:
                name = f"cena{k:02d}_narracao"
            wav = p.path("audio", "vozes", name + ".wav")
            imp = None
            for ext in (".wav", ".mp3", ".m4a", ".ogg"):
                cand = p.path("audio", "importar", name + ext)
                if cand.exists():
                    imp = cand
            if not wav.exists() or imp:
                vcfg = voice.voice_for(chars.get(who) if who else None, cfg)
                info = voice.synthesize_line(text, wav, vcfg, cfg, imported=imp, log=p.log)
                fontes.append({"arquivo": wav.name, "texto": text, **info})
            d = voice.duration(wav)
            lines.append({"id": name, "tipo": tipo, "falante": who, "texto": text, "emocao": emo,
                          "audio": str(wav.relative_to(p.dir)), "dur": round(d, 3),
                          "envelope": voice.envelope(wav, 12) if who else []})
        plan = timeline.plan_scene(sc, lines, last=(i == n - 1))
        plans.append(plan)
        p.log(f"Vozes da cena {k}: {len(lines)} falas, cena com {plan['duracao']:.1f}s.", pct=100 * (i + 1) / n)
    old = p.path("audio", "fontes_voz.json")
    if old.exists() and not fontes:
        fontes = json.loads(old.read_text(encoding="utf-8"))
    p.write_json(fontes, "audio", "fontes_voz.json")
    p.write_json({"cenas": plans}, "roteiro", "linha_do_tempo.json")
    total = sum(pl["duracao"] for pl in plans) - timeline.TRANSICAO * (len(plans) - 1)
    p.log(f"Duração estimada do vídeo: {total:.1f}s (alvo: {prm['duracao']}s).")


def _clip_durations(p):
    plans = p.read_json("roteiro", "linha_do_tempo.json")["cenas"]
    fps = render_fps(p)
    return [(round(pl["duracao"] * fps) + 1) / fps for pl in plans]


def render_fps(p):
    return 12 if p.data["parametros"]["qualidade"] in ("rascunho", "teste") else 24


def step_musica(p, cfg):
    story = p.read_json("roteiro", "historia.json")
    durs = _clip_durations(p)
    starts = []
    acc = 0.0
    for d in durs:
        starts.append(round(acc, 3))
        acc += d - timeline.TRANSICAO
    segs = timeline.music_segments(story["cenas"], starts, durs)
    p.write_json({"segmentos": segs, "inicios": starts, "duracoes": durs}, "audio", "plano_musical.json")
    p.log("Trilha planejada: " + " → ".join(s["emocao"] for s in segs) + ". Efeitos: sintetizados pelo estúdio.")


def step_animacao(p, cfg):
    story = p.read_json("roteiro", "historia.json")
    plans = p.read_json("roteiro", "linha_do_tempo.json")["cenas"]
    chars = chars_of(p)
    prm = p.data["parametros"]
    w, h, samples = resolution(prm["qualidade"], prm["proporcao"])
    fps = render_fps(p)
    render = {"largura": w, "altura": h, "fps": fps, "amostras": max(4, samples // 2) if fps == 12 else samples}
    n = len(story["cenas"])
    total_frames = sum(round(pl["duracao"] * fps) + 1 for pl in plans)
    done_before = 0
    t_start = time.time()
    for i, (sc, plan) in enumerate(zip(story["cenas"], plans)):
        k = sc["numero"]
        sdir = p.path("cenas", f"cena{k:02d}")
        qdir = sdir / "quadros"
        qdir.mkdir(parents=True, exist_ok=True)
        spec = timeline.build_scene_spec(sc, plan, chars, render, qdir, seed=100 + k)
        h_spec = hashlib.md5(json.dumps(spec, sort_keys=True).encode()).hexdigest()
        nframes = round(plan["duracao"] * fps) + 1
        meta = sdir / "estado.json"
        prev = json.loads(meta.read_text()) if meta.exists() else {}
        if prev.get("hash") != h_spec:
            for f in qdir.glob("quadro_*.png"):
                f.unlink()
        existing = sorted(qdir.glob("quadro_*.png"))
        clip = p.path("cenas", f"cena{k:02d}.mp4")
        if len(existing) >= nframes and clip.exists() and prev.get("hash") == h_spec:
            p.log(f"Cena {k} já renderizada (retomando).")
            done_before += nframes
            continue
        meta.write_text(json.dumps({"hash": h_spec, "quadros": nframes}))
        if len(existing) >= nframes and prev.get("hash") == h_spec:
            editor.frames_to_clip(qdir, clip, fps)  # quadros completos: so falta o clipe
            done_before += nframes
            continue
        if existing:
            # retoma do ultimo quadro salvo (ele e refeito, pois pode ter sido cortado por uma queda)
            existing[-1].unlink()
            spec["quadro_inicial"] = len(existing)
            p.log(f"Cena {k}: retomando do quadro {len(existing)}.")
        sp = sdir / "cena.json"
        sp.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        base_done = done_before

        def prog(fr, k=k, base=base_done):
            el = time.time() - t_start
            pct = 100 * (base + fr) / total_frames
            eta = el / max(1e-3, base + fr - 0) * (total_frames - base - fr) if fr else 0
            p.log(f"Cena {k}/{n}: quadro {fr}/{nframes} (faltam ~{eta / 60:.0f} min)", pct=pct)

        p.log(f"Renderizando cena {k}/{n} ({nframes} quadros, {w}x{h}, cenário {sc['cenario']}, "
              f"câmera {sc['plano']}/{sc['movimento']})...")
        run_blender(sp, prog, nframes)
        editor.frames_to_clip(qdir, clip, fps)
        done_before += nframes
    p.data["tempos"]["render_segundos"] = round(time.time() - t_start, 1)
    p.log(f"Animação concluída em {(time.time() - t_start) / 60:.1f} min.")


def step_edicao(p, cfg):
    story = p.read_json("roteiro", "historia.json")
    plans = p.read_json("roteiro", "linha_do_tempo.json")["cenas"]
    mplan = p.read_json("audio", "plano_musical.json")
    chars = chars_of(p)
    prm = p.data["parametros"]
    fps = render_fps(p)
    clips = [p.path("cenas", f"cena{sc['numero']:02d}.mp4") for sc in story["cenas"]]
    durs = [editor.probe_duration(c) for c in clips]
    final = p.path("final")
    joined = final / "montagem_sem_audio.mp4"
    starts = editor.join_clips(clips, durs, joined, timeline.TRANSICAO)
    p.log("Cenas unidas com transições.", pct=20)

    voice_events, sfx_events, cues = [], [], []
    w, h, _ = resolution(prm["qualidade"], prm["proporcao"])
    render = {"largura": w, "altura": h, "fps": fps, "amostras": 8}
    for i, (sc, plan) in enumerate(zip(story["cenas"], plans)):
        st = starts[i]
        for ln in plan["falas"]:
            voice_events.append((p.path(ln["audio"]), st + ln["t0"]))
            nome = chars[ln["falante"]]["nome"] if ln.get("falante") else None
            cues.append({"t0": st + ln["t0"], "t1": st + ln["t1"] + 0.25, "narrador": nome is None,
                         "texto": (f"{nome}: " if nome else "") + ln["texto"]})
        spec = timeline.build_scene_spec(sc, plan, chars, render, "-", seed=100 + sc["numero"])
        for name, t in timeline.sfx_cues(sc, spec, plan):
            sfx_events.append((name, st + t))
        if i > 0:
            sfx_events.append(("whoosh", st - 0.3))
    total = starts[-1] + durs[-1]
    fontes_musica = []
    mix = p.path("audio", "mixagem.wav")
    editor.mix_audio(total, voice_events, sfx_events, mplan["segmentos"], cfg, mix, fontes_musica)
    p.write_json(fontes_musica, "audio", "fontes_musica.json")
    p.write_json([{"efeito": n, "instante": round(t, 2), "origem": music.SFX_INFO.get(n)} for n, t in sfx_events],
                 "audio", "efeitos.json")
    p.log("Áudio mixado: vozes + efeitos + música com redução automática durante as falas.", pct=50)

    font = editor.font_path(ROOT)
    fonts_dir = font.parent if font else None
    font_name = "DejaVu Sans" if (font and "DejaVu" in font.name) else (font.stem.split("-")[0] if font else "Arial")
    vertical = prm["proporcao"] == "9:16"
    editor.write_subtitles(cues, final / "legendas.srt", final / "legendas_nativa.ass", w, h, font_name)
    native = final / ("video_9x16.mp4" if vertical else "video_16x9.mp4")
    editor.export_final(joined, mix, final / "legendas_nativa.ass", native, fonts_dir)
    p.log(f"Versão {prm['proporcao']} exportada.", pct=75)
    alt = final / ("video_16x9.mp4" if vertical else "video_9x16.mp4")
    alt_raw = final / "montagem_outra_proporcao.mp4"
    W, H = editor.make_alt_aspect(joined, alt_raw, vertical, title=None if vertical else story["titulo"], font=font)
    editor.write_subtitles(cues, final / "legendas_tmp.srt", final / "legendas_outra.ass", W, H, font_name)
    (final / "legendas_tmp.srt").unlink()
    editor.export_final(alt_raw, mix, final / "legendas_outra.ass", alt, fonts_dir)
    editor.make_preview(native, final / "previa.mp4")
    editor.contact_sheet(native, final / "folha_de_contato.jpg")
    for tmp in (joined, alt_raw):
        tmp.unlink()
    p.data["video_duracao"] = round(editor.probe_duration(native), 2)
    p.log(f"Vídeos prontos: {native.name} e {alt.name} ({p.data['video_duracao']}s).", pct=100)


def step_publicacao(p, cfg):
    story = p.read_json("roteiro", "historia.json")
    plans = p.read_json("roteiro", "linha_do_tempo.json")["cenas"]
    chars = chars_of(p)
    clist = [chars[c] for c in story["personagens"]]
    final = p.path("final")
    # quadro para a capa: cena de celebracao (ou a ultima), em alta resolucao
    idx = next((i for i, s in enumerate(story["cenas"]) if s["emocao_musical"] == "celebracao"), len(story["cenas"]) - 1)
    sc, plan = story["cenas"][idx], plans[idx]
    render = {"largura": 1280, "altura": 720, "fps": render_fps(p), "amostras": 24}
    spec = timeline.build_scene_spec(sc, plan, chars, render, final, seed=100 + sc["numero"])
    spec["camera"]["plano"] = "dois" if len(sc["personagens"]) > 1 else "medio"
    spec["quadro_unico"] = max(2, int(plan["duracao"] * render["fps"] * 0.6))
    spec["nome_quadro"] = "capa_base.png"
    sp = final / "capa_spec.json"
    sp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    p.log("Renderizando quadro em alta para a capa...")
    run_blender(sp, None)
    sp.unlink()
    font = editor.font_path(ROOT)
    publisher.make_thumbnail(final / "capa_base.png", story["titulo"], final / "capa.jpg", font)
    credits = []
    for f in json.loads(p.path("audio", "fontes_voz.json").read_text(encoding="utf-8")):
        if "faber" in str(f.get("voz", "")):
            credits.append("Voz sintética Piper 'faber' (pt-BR) — modelo-base Hi-Fi TTS, CC BY 4.0.")
            break
    for m in p.read_json("audio", "fontes_musica.json"):
        if m.get("atribuicao"):
            credits.append(m["atribuicao"])
    publisher.build_package(story, clist, credits, final)
    p.log("Pacote de publicação pronto (nada foi publicado: revise e publique manualmente).")


def tool_versions():
    v = {"python": sys.version.split()[0], "sistema": f"{platform.system()} {platform.release()}"}
    try:
        v["ffmpeg"] = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split()[2]
    except Exception:
        v["ffmpeg"] = "?"
    b = find_blender()
    if b:
        v["blender"] = subprocess.run([b, "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    else:
        try:
            import importlib.metadata as md
            v["blender"] = "bpy " + md.version("bpy")
        except Exception:
            v["blender"] = "?"
    try:
        import importlib.metadata as md
        v["piper-tts"] = md.version("piper-tts")
        v["numpy"] = md.version("numpy")
        v["pillow"] = md.version("pillow")
    except Exception:
        pass
    return v


def step_relatorio(p, cfg):
    story = p.read_json("roteiro", "historia.json")
    v = tool_versions()
    voz = json.loads(p.path("audio", "fontes_voz.json").read_text(encoding="utf-8"))
    mus = p.read_json("audio", "fontes_musica.json")
    pagos = any(x.get("origem") == "elevenlabs" for x in voz) or "Claude" in story.get("motor", "")
    files = sorted(str(f.relative_to(p.dir)) for f in p.dir.rglob("*") if f.is_file() and "quadros" not in f.parts)
    nq = sum(1 for _ in p.dir.rglob("quadro_*.png"))
    tools = [
        ("Blender " + v.get("blender", ""), "Animação 3D, render (Cycles)", "GPL-2.0-or-later", "Sim (o software é livre; o que você cria é seu)", "R$ 0"),
        ("FFmpeg " + v.get("ffmpeg", ""), "Edição, transições, legendas, exportação", "LGPL/GPL", "Sim", "R$ 0"),
        ("Piper TTS " + v.get("piper-tts", ""), "Síntese de voz local", "GPL-3.0 (o áudio gerado não herda a licença)", "Sim", "R$ 0"),
        ("Vozes Piper pt-BR", "Narrador e personagens", "cadu/jeff: CC0 · faber: CC0 + base CC BY 4.0", "Sim (faber: dar crédito)", "R$ 0"),
        ("Python + numpy + Pillow", "Orquestração, música, mixagem, capas", "PSF / BSD / HPND", "Sim", "R$ 0"),
        ("Compositor e efeitos do estúdio", "Trilha e efeitos originais", "Própria", "Sim", "R$ 0"),
    ]
    if any(x.get("origem") == "elevenlabs" for x in voz):
        tools.append(("ElevenLabs", "Voz premium", "Termos do plano contratado", "Depende do plano", "Créditos do plano"))
    if "Claude" in story.get("motor", ""):
        tools.append(("Claude (API Anthropic)", "Roteiro", "Termos comerciais da API", "Sim", "Pago por uso"))
    md = [f"# Relatório de produção — {story['titulo']}", "", f"Gerado em {now()}.", "",
          "## Resultado", f"- Duração do vídeo: **{p.data.get('video_duracao', '?')} s**",
          f"- Cenas: {len(story['cenas'])} · Personagens 3D: {', '.join(story['personagens'])}",
          f"- Quadros 3D renderizados: {nq} · Tempo de render: {p.data['tempos'].get('render_segundos', '?')} s",
          f"- Qualidade: {p.data['parametros']['qualidade']} · Proporção nativa: {p.data['parametros']['proporcao']}",
          f"- Roteirista: {story['motor']}", "",
          "## Custos", f"- Software: **R$ 0** (tudo livre/gratuito)",
          f"- APIs pagas: **{'SIM — ver abaixo' if pagos else 'nenhuma usada (R$ 0)'}**",
          "- Infraestrutura: seu próprio computador (energia elétrica). Em nuvem, cobre-se o tempo de máquina.", "",
          "## Ferramentas e licenças", "| Ferramenta | Uso | Licença | Uso comercial do resultado | Custo |", "|---|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in tools]
    md += ["", "## Origem de cada áudio", "### Vozes"]
    md += [f"- `{x['arquivo']}` — {x.get('origem')} {x.get('voz', '')} · {x.get('licenca', '')}" for x in voz]
    md += ["", "### Música"] + [f"- {m.get('emocao')}: {m.get('origem', m.get('arquivo'))} · {m.get('licenca')}" for m in mus]
    md += ["", "### Efeitos sonoros", "- Todos sintetizados pelo estúdio (originais, sem direitos de terceiros).", "",
           "## Tempos por etapa"] + [f"- {k}: {v} s" for k, v in p.data["tempos"].items()]
    md += ["", "## Limitações conhecidas",
           "- Personagens montados com formas primitivas (rig hierárquico, sem deformação de malha/skinning).",
           "- Sincronia labial por volume da fala (abre/fecha a boca), não por fonemas.",
           "- Render em CPU: qualidade 'rascunho' a 12 quadros/s (animação \"em dois\") para ser rápido.",
           "", "## Arquivos gerados"] + [f"- `{f}`" for f in files]
    p.path("RELATORIO.md").write_text("\n".join(md), encoding="utf-8")
    p.write_json({"versoes": v, "custo_apis": "pago" if pagos else "R$ 0", "arquivos": files,
                  "tempos": p.data["tempos"]}, "relatorio.json")
    p.log("Relatório de ferramentas, licenças e custos gerado.")


STEPS = {"roteiro": step_roteiro, "personagens": step_personagens, "voz": step_voz, "musica": step_musica,
         "animacao": step_animacao, "edicao": step_edicao, "publicacao": step_publicacao, "relatorio": step_relatorio}


def run_pipeline(p, auto_approve=False, until=None):
    """Executa as etapas pendentes. Para nos portoes de aprovacao."""
    cfg = load_config()
    need_approval = cfg.get("exigir_aprovacao", True) and not auto_approve
    for etapa in ETAPAS:
        st = p.status(etapa)
        if st == "concluida":
            continue
        if st == "aguardando_aprovacao":
            if auto_approve:
                p.approve(etapa)
                continue
            p.log(f"Aguardando sua aprovação da etapa '{etapa}'.", etapa=etapa)
            return "aguardando_aprovacao"
        p.set_status(etapa, "executando", iniciado_em=now())
        p.data["progresso"].update({"etapa": etapa, "pct": 0})
        p.teach(etapa)
        t0 = time.time()
        try:
            STEPS[etapa](p, cfg)
        except Exception as e:
            p.set_status(etapa, "erro", erro=str(e)[-3000:])
            p.log(f"ERRO na etapa '{etapa}': {e}")
            with open(p.path("log.txt"), "a", encoding="utf-8") as f:
                f.write(traceback.format_exc())
            return "erro"
        p.data["tempos"][etapa] = round(time.time() - t0, 1)
        if etapa in APROVACAO and need_approval:
            p.set_status(etapa, "aguardando_aprovacao")
            p.log(f"Etapa '{etapa}' pronta. Revise e aprove para continuar.", etapa=etapa, pct=100)
            return "aguardando_aprovacao"
        p.set_status(etapa, "concluida")
        if until and etapa == until:
            return "parado"
    p.data["progresso"].update({"etapa": "concluido", "pct": 100, "mensagem": "Vídeo pronto para revisão!"})
    p.save()
    return "concluido"
