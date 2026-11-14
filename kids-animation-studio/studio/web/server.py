"""Painel web local (sem dependencias extras: usa apenas a biblioteca padrao do Python).

Abra com:  python kas.py painel   ->  http://localhost:8765
O servidor escuta apenas em 127.0.0.1 (seu computador). Nada fica exposto na internet.
"""
import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .. import art_director as ad
from .. import teaching
from ..config import PROJECTS, load_config, save_config
from ..diagnose import diagnose
from ..pipeline import ETAPAS, Project, run_pipeline

STATIC = Path(__file__).parent / "index.html"
WORKERS = {}


def start_worker(pid, auto=False):
    t = WORKERS.get(pid)
    if t and t.is_alive():
        return False

    def work():
        p = Project(pid)
        try:
            run_pipeline(p, auto_approve=auto)
        except Exception as e:  # garante que o erro aparece no painel
            p.log(f"ERRO inesperado: {e}")

    t = threading.Thread(target=work, daemon=True)
    WORKERS[pid] = t
    t.start()
    return True


def valid_pid(pid):
    import re
    return bool(re.fullmatch(r"[A-Za-z0-9_\-]{3,120}", pid or "")) and (PROJECTS / pid / "projeto.json").exists()


def project_view(pid):
    p = Project(pid)
    d = dict(p.data)
    d["rodando"] = bool(WORKERS.get(pid) and WORKERS[pid].is_alive())
    files = {}
    for rel in ["roteiro/roteiro.md", "roteiro/historia.json", "final/video_16x9.mp4", "final/video_9x16.mp4",
                "final/previa.mp4", "final/capa.jpg", "final/capa_vertical.jpg", "final/legendas.srt",
                "final/PUBLICACAO.md", "final/metadados.json", "RELATORIO.md", "AULA.md", "log.txt",
                "final/folha_de_contato.jpg"]:
        if p.path(rel).exists():
            files[rel] = True
    d["arquivos"] = files
    if p.path("roteiro", "historia.json").exists():
        d["historia"] = p.read_json("roteiro", "historia.json")
        d["personagens"] = [ad.load_character(c) for c in d["historia"]["personagens"]]
    if p.path("log.txt").exists():
        d["log"] = p.path("log.txt").read_text(encoding="utf-8").splitlines()[-30:]
    return d


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _file(self, path):
        path = Path(path)
        if not path.exists() or not path.is_file():
            return self._json({"erro": "arquivo não encontrado"}, 404)
        size = path.stat().st_size
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix in (".md", ".srt", ".txt", ".json"):
            ctype += "; charset=utf-8"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else 0
            end = int(b) if b else size - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 16, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def do_GET(self):
        u = urlparse(self.path)
        parts = [unquote(x) for x in u.path.strip("/").split("/") if x]
        if not parts:
            return self._file(STATIC)
        if parts[0] == "api":
            if parts[1:] == ["projetos"]:
                return self._json(Project.list_all())
            if parts[1] == "projetos" and len(parts) == 3:
                if not valid_pid(parts[2]):
                    return self._json({"erro": "projeto não encontrado"}, 404)
                return self._json(project_view(parts[2]))
            if parts[1:] == ["personagens"]:
                ad.ensure_default_library()
                return self._json(ad.list_characters())
            if parts[1:] == ["cenarios"]:
                return self._json([{"id": s["id"], "nome": s["nome"], "descricao": s["descricao"]} for s in ad.list_sets()])
            if parts[1:] == ["diagnostico"]:
                return self._json(diagnose())
            if parts[1:] == ["config"]:
                return self._json(load_config())
            if parts[1:] == ["ensino"]:
                return self._json(teaching.ETAPAS)
        if parts[0] == "arquivos" and len(parts) >= 3:
            if not valid_pid(parts[1]):
                return self._json({"erro": "projeto não encontrado"}, 404)
            base = (PROJECTS / parts[1]).resolve()
            target = (base / "/".join(parts[2:])).resolve()
            if base not in target.parents:
                return self._json({"erro": "caminho inválido"}, 403)
            return self._file(target)
        if parts[0] == "biblioteca" and len(parts) == 2:
            # imagem de personagem: usa a folha de modelo mais recente encontrada
            for d in sorted(PROJECTS.glob("*/personagens"), reverse=True):
                f = d / f"{parts[1]}.png"
                if f.exists():
                    return self._file(f)
            return self._json({"erro": "sem imagem"}, 404)
        return self._json({"erro": "não encontrado"}, 404)

    def do_POST(self):
        parts = [unquote(x) for x in urlparse(self.path).path.strip("/").split("/") if x]
        try:
            body = self._body()
        except json.JSONDecodeError:
            return self._json({"erro": "JSON inválido"}, 400)
        if parts == ["api", "projetos"]:
            tema = (body.get("tema") or "").strip()
            if len(tema) < 5:
                return self._json({"erro": "Escreva um tema para a história."}, 400)
            p = Project.create(tema, int(body.get("duracao", 25)), body.get("proporcao", "16:9"), body.get("faixa", "4-6"),
                               body.get("categoria") or None, body.get("qualidade") or None, body.get("cenario") or None,
                               body.get("voz") or None, body.get("modo_ensino", True))
            start_worker(p.id)
            return self._json({"id": p.id})
        if len(parts) == 4 and parts[:2] == ["api", "projetos"]:
            pid, action = parts[2], parts[3]
            if not valid_pid(pid):
                return self._json({"erro": "projeto não encontrado"}, 404)
            p = Project(pid)
            if action == "continuar":
                return self._json({"iniciado": start_worker(pid)})
            if action == "aprovar":
                ok = p.approve(body.get("etapa"))
                if ok:
                    start_worker(pid)
                return self._json({"aprovado": ok})
            if action == "refazer":
                if WORKERS.get(pid) and WORKERS[pid].is_alive():
                    return self._json({"erro": "Aguarde a etapa atual terminar."}, 409)
                etapa = body.get("etapa")
                if etapa not in ETAPAS:
                    return self._json({"erro": "etapa inválida"}, 400)
                p.reset_from(etapa)
                start_worker(pid)
                return self._json({"ok": True})
            if action == "roteiro":
                # edicao manual do roteiro antes de aprovar
                if p.status("roteiro") != "aguardando_aprovacao":
                    return self._json({"erro": "O roteiro só pode ser editado antes da aprovação."}, 409)
                story = p.read_json("roteiro", "historia.json")
                for sc, new in zip(story["cenas"], body.get("cenas", [])):
                    sc["narracao"] = new.get("narracao", sc["narracao"]).strip()
                    for f, nf in zip(sc["falas"], new.get("falas", [])):
                        f["texto"] = nf.strip() or f["texto"]
                if body.get("titulo"):
                    story["titulo"] = body["titulo"].strip()
                    p.data["titulo"] = story["titulo"]
                p.write_json(story, "roteiro", "historia.json")
                from ..writer import script_markdown
                chars = [ad.load_character(c) for c in story["personagens"]]
                p.path("roteiro", "roteiro.md").write_text(script_markdown(story, chars), encoding="utf-8")
                p.log("Roteiro editado manualmente pelo usuário.")
                return self._json({"ok": True})
        if parts == ["api", "config"]:
            cfg = load_config()
            for k in ("qualidade", "modo_ensino", "exigir_aprovacao", "voz_provedor", "permitir_servicos_pagos",
                      "roteirista", "volume_musica_db", "elevenlabs_voz_preferida", "blender_executavel"):
                if k in body:
                    cfg[k] = body[k]
            save_config(cfg)
            return self._json(cfg)
        return self._json({"erro": "não encontrado"}, 404)


def serve(port=8765, open_browser=True):
    PROJECTS.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print(f"Painel do Kids Animation Studio AI em {url}  (Ctrl+C para sair)")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("Painel encerrado.")
