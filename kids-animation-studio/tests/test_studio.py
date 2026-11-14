"""Testes basicos do Kids Animation Studio AI.

Rodar:  python -m unittest discover -s tests -v
Os testes de voz e de Blender sao pulados automaticamente se as ferramentas
nao estiverem instaladas.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="kas_test_")
os.environ["KAS_PROJETOS"] = TMP
os.environ["KAS_PERSONAGENS"] = os.path.join(TMP, "personagens")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from studio import art_director as ad  # noqa: E402
from studio import editor, music, timeline, writer  # noqa: E402
from studio.config import VOICES_DIR  # noqa: E402
from studio.pipeline import Project, run_pipeline  # noqa: E402


def has_bpy():
    if shutil.which("blender"):
        return True
    r = subprocess.run([sys.executable, "-c", "import bpy"], capture_output=True)
    return r.returncode == 0


def has_piper():
    try:
        import piper  # noqa: F401
        return any(VOICES_DIR.glob("*.onnx"))
    except Exception:
        return False


class TestWriter(unittest.TestCase):
    def test_species_detection(self):
        self.assertEqual(ad.detect_species("Um leãozinho que aprende a compartilhar"), "leao")
        self.assertEqual(ad.detect_species("A coelhinha corajosa"), "coelho")
        self.assertIsNone(ad.detect_species("Uma historia sem bichos"))

    def test_template_detection(self):
        self.assertEqual(writer.detect_template("leãozinho que aprende a compartilhar"), "compartilhar")
        self.assertEqual(writer.detect_template("um ursinho com medo do escuro"), "coragem")
        self.assertEqual(writer.detect_template("a ovelha perdida"), "biblica_ovelha")
        self.assertEqual(writer.detect_template("qualquer coisa"), "amizade")

    def test_story_structure(self):
        for tema, dur, n_min in [("Um leãozinho que aprende a compartilhar", 25, 3),
                                 ("Um elefantinho com medo do escuro", 60, 4),
                                 ("Aprender a contar com um macaquinho", 30, 3)]:
            s = writer.write_story_local(tema, dur)
            self.assertGreaterEqual(len(s["cenas"]), n_min)
            self.assertTrue(s["moral"])
            for sc in s["cenas"]:
                self.assertNotIn("{", sc["narracao"])
                for f in sc["falas"]:
                    self.assertNotIn("{", f["texto"])
                    self.assertIn(f["personagem"], s["personagens"])
                self.assertIn(sc["cenario"], [x["id"] for x in ad.list_sets()])

    def test_character_consistency(self):
        a = writer.write_story_local("Um leãozinho que aprende a compartilhar", 25)
        b = writer.write_story_local("Um leãozinho corajoso", 25)
        self.assertEqual(a["personagens"][0], b["personagens"][0], "o mesmo personagem deve ser reutilizado")

    def test_paid_writer_blocked_by_default(self):
        with self.assertRaises(PermissionError):
            writer.write_story("tema qualquer", 25, cfg={"roteirista": "claude", "permitir_servicos_pagos": False})


class TestTimeline(unittest.TestCase):
    def setUp(self):
        self.story = writer.write_story_local("Um leãozinho que aprende a compartilhar", 25)
        self.chars = {c: ad.load_character(c) for c in self.story["personagens"]}

    def lines(self, sc):
        out = [{"id": "n", "tipo": "narracao", "falante": None, "texto": sc["narracao"], "dur": 3.0, "envelope": []}]
        for f in sc["falas"]:
            out.append({"id": "f", "tipo": "fala", "falante": f["personagem"], "texto": f["texto"], "dur": 1.5,
                        "envelope": [0.5] * 18})
        return out

    def test_plan_and_spec(self):
        sc = self.story["cenas"][1]
        plan = timeline.plan_scene(sc, self.lines(sc))
        self.assertGreater(plan["duracao"], 3.0 + 1.5)
        t = [l["t0"] for l in plan["falas"]]
        self.assertEqual(t, sorted(t), "falas em ordem e sem sobreposicao")
        spec = timeline.build_scene_spec(sc, plan, self.chars, {"largura": 64, "altura": 36, "fps": 12, "amostras": 1}, "/tmp/x")
        self.assertEqual(len(spec["personagens"]), 2)
        walkers = [a for c in spec["personagens"] for a in c["acoes"] if a["tipo"] == "andar"]
        self.assertTrue(walkers)
        for w in walkers:
            self.assertLess(w["t0"], w["t1"])
        talking = [c for c in spec["personagens"] if c["falas"]]
        self.assertTrue(talking, "sincronia labial precisa de envelopes")

    def test_music_segments(self):
        segs = timeline.music_segments(self.story["cenas"], [0, 8, 16], [8.4, 8.4, 10])
        self.assertEqual(segs[-1]["emocao"], "celebracao")
        self.assertAlmostEqual(segs[-1]["fim"], 26.0)


class TestAudio(unittest.TestCase):
    def test_compose_length(self):
        for e in music.EMOCOES:
            x = music.compose(e, 5.0)
            self.assertEqual(x.shape, (int(5.0 * music.SR), 2))
            self.assertLessEqual(np.max(np.abs(x)), 0.81)
            self.assertGreater(np.max(np.abs(x)), 0.1)

    def test_sfx(self):
        for n in music.SFX_INFO:
            self.assertGreater(np.max(np.abs(music.sfx(n))), 0.01, n)

    def test_mix_ducking(self):
        d = Path(TMP) / "mix"
        d.mkdir(exist_ok=True)
        v = np.zeros(int(4 * music.SR), np.float32)
        v[int(1 * music.SR):int(2 * music.SR)] = 0.5 * np.sin(np.linspace(0, 2000, int(music.SR)))
        music.write_wav(d / "voz.wav", v)
        fontes = []
        editor.mix_audio(4.0, [(d / "voz.wav", 0.0)], [], [{"emocao": "alegria", "inicio": 0, "fim": 4.0}],
                         {"volume_musica_db": -20, "reducao_musica_durante_fala_db": -12}, d / "mix.wav", fontes)
        from studio.voice import read_wav
        m, _ = read_wav(d / "trilha_musica.wav")
        sr = music.SR
        quiet = np.sqrt(np.mean(m[int(1.3 * sr):int(1.7 * sr)] ** 2))
        loud = np.sqrt(np.mean(m[int(3.0 * sr):int(3.3 * sr)] ** 2))
        self.assertLess(quiet, loud * 0.5, "musica deve abaixar durante a fala")
        self.assertEqual(fontes[0]["licenca"], "propria - livre para uso comercial")

    def test_subtitles(self):
        d = Path(TMP)
        cues = [{"t0": 0.5, "t1": 2.0, "texto": "Era uma vez um leãozinho chamado Tito.", "narrador": True}]
        editor.write_subtitles(cues, d / "a.srt", d / "a.ass", 640, 360)
        self.assertIn("00:00:00,500 --> 00:00:02,000", (d / "a.srt").read_text(encoding="utf-8"))
        self.assertIn("Dialogue:", (d / "a.ass").read_text(encoding="utf-8"))


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg nao instalado")
class TestVideo(unittest.TestCase):
    def test_join_with_transitions(self):
        d = Path(TMP) / "clips"
        d.mkdir(exist_ok=True)
        clips = []
        for i, c in enumerate(["red", "blue"]):
            out = d / f"c{i}.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color={c}:s=160x90:d=2:r=24",
                            "-pix_fmt", "yuv420p", str(out)], check=True)
            clips.append(out)
        starts = editor.join_clips(clips, [2.0, 2.0], d / "j.mp4", 0.4)
        self.assertEqual(starts, [0.0, 1.6])
        self.assertAlmostEqual(editor.probe_duration(d / "j.mp4"), 3.6, delta=0.1)


class TestProject(unittest.TestCase):
    def test_resume_and_approval(self):
        p = Project.create("Um ursinho que aprende a esperar", duracao=25)
        res = run_pipeline(p, auto_approve=False)
        self.assertEqual(res, "aguardando_aprovacao")
        self.assertEqual(p.status("roteiro"), "aguardando_aprovacao")
        self.assertTrue(p.path("roteiro", "roteiro.md").exists())
        self.assertTrue(p.approve("roteiro"))
        p2 = Project(p.id)  # reabre do disco (retomada)
        self.assertEqual(p2.status("roteiro"), "concluida")
        p2.reset_from("roteiro")
        self.assertEqual(Project(p.id).status("roteiro"), "pendente")


@unittest.skipUnless(has_piper(), "Piper ou vozes nao instalados")
class TestVoice(unittest.TestCase):
    def test_synthesis(self):
        from studio import voice
        out = Path(TMP) / "v.wav"
        info = voice.synthesize_line("Olá, crianças! Vamos aprender juntos?", out,
                                     {"provedor": "piper", "modelo": voice.available_piper_voices()[0], "tom": 1.2}, {})
        self.assertIn("piper", info["origem"])
        self.assertGreater(voice.duration(out), 1.0)
        env = voice.envelope(out)
        self.assertGreater(max(env), 0.5)


@unittest.skipUnless(has_bpy(), "Blender/bpy nao instalado")
class TestBlender(unittest.TestCase):
    def test_tiny_render(self):
        sheet = ad.create_character("raposa", "f", "Teste", seed=1)
        out = Path(TMP) / "render"
        spec = {"saida": str(out), "duracao": 0.2, "semente": 1,
                "render": {"largura": 96, "altura": 54, "fps": 12, "amostras": 1},
                "cenario": ad.load_set("campo"),
                "personagens": [{"ficha": sheet, "inicio": [0, 0], "acoes": [{"tipo": "pular", "t0": 0.0}],
                                 "falas": [{"t0": 0.0, "envelope": [0.2, 0.8, 0.4], "env_fps": 12}]}],
                "camera": {"plano": "medio", "movimento": "aproximar"}}
        sp = Path(TMP) / "tiny.json"
        sp.write_text(json.dumps(spec))
        r = subprocess.run([sys.executable, str(ROOT / "studio" / "blender" / "scene_builder.py"), str(sp)],
                           capture_output=True, text=True, timeout=300)
        self.assertIn("KAS_OK", r.stdout + r.stderr)
        self.assertEqual(len(list(out.glob("quadro_*.png"))), 3)  # 0,2 s a 12 qps = quadros 1..3


if __name__ == "__main__":
    unittest.main()
