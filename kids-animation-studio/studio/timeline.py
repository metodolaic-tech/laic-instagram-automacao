"""Planejamento da linha do tempo.

Transforma o roteiro (story.json) + a duracao REAL de cada audio de voz em:
  * duracao de cada cena;
  * instante exato de cada fala (para audio, legenda e sincronia labial);
  * instante de cada acao dos personagens (andar, pular, acenar...);
  * posicoes no palco 3D, objetos e camera;
  * marcacoes de efeitos sonoros.

E isso que garante que boca, gestos, legendas e som fiquem sincronizados.
"""
from . import art_director as ad

LEAD = 0.6       # silencio antes da primeira fala da cena
GAP = 0.35       # pausa entre falas
TAIL = 1.0       # respiro no fim da cena
TRANSICAO = 0.4  # duracao da transicao (crossfade) entre cenas
MIN_SCENE = 3.5

HOME = {"P": (-0.75, 0.0, 20), "A": (0.75, 0.0, -20), "SO": (0.0, 0.0, 0)}


def plan_scene(scene, line_info, last=False):
    """line_info: lista [{id, dur, envelope, falante}] na ordem narracao, falas."""
    t = LEAD
    lines = []
    for li in line_info:
        lines.append({**li, "t0": round(t, 3), "t1": round(t + li["dur"], 3)})
        t += li["dur"] + GAP
    end_speech = t - GAP if lines else LEAD
    dur = max(MIN_SCENE, end_speech + TAIL + (0.8 if last else 0.0))
    return {"duracao": round(dur, 3), "falas": lines}


def _interval(em, plan, dur):
    falas = plan["falas"]
    narr = [l for l in falas if l["tipo"] == "narracao"]
    dial = [l for l in falas if l["tipo"] == "fala"]
    if em == "inicio":
        return 0.1, 1.3
    if em == "fim":
        last = falas[-1]["t1"] if falas else 0.5
        return min(last, dur - 1.2), dur - 0.2
    if em == "narracao" and narr:
        return narr[0]["t0"], narr[0]["t1"]
    if em.startswith("fala"):
        try:
            k = int(em[4:])
            return dial[k]["t0"], dial[k]["t1"]
        except (ValueError, IndexError):
            pass
    return 0.3, min(dur - 0.2, 2.0)


def build_scene_spec(scene, plan, chars, render, out_dir, seed=1):
    """Gera o JSON que o scene_builder (Blender) le."""
    dur = plan["duracao"]
    role = {}
    ids = scene["personagens"]
    if len(ids) == 1:
        role[ids[0]] = "SO"
    else:
        role[ids[0]], role[ids[1]] = "P", "A"
    seguir = scene["movimento"] == "seguir"
    specs = []
    for cid in ids:
        sheet = chars[cid]
        hx, hy, face = HOME[role[cid]]
        acts = [a for a in scene["acoes"] if a["personagem"] == cid]
        walk = next((a for a in acts if a["tipo"] == "andar"), None)
        start = (hx, hy)
        out_acts = []
        if walk:
            t0, t1 = _interval(walk["em"], plan, dur)
            t1 = min(t1, t0 + 2.6)
            t1 = max(t1, t0 + 1.2)
            if seguir:
                start = (hx - 3.2, hy)
            else:
                side = -1 if hx <= 0 else 1
                start = (side * 3.6, 1.6)
            out_acts.append({"tipo": "andar", "t0": round(t0, 2), "t1": round(t1, 2), "para": [hx, hy]})
        for a in acts:
            if a["tipo"] == "andar":
                continue
            t0, t1 = _interval(a["em"], plan, dur)
            if a["tipo"] in ("acenar", "oferecer", "comemorar", "segurar"):
                t1 = max(t1, t0 + 1.5)
                t1 = min(t1, dur - 0.1)
            item = {"tipo": a["tipo"], "t0": round(t0, 2), "t1": round(t1, 2)}
            if a["tipo"] == "expressao":
                item["expressao"] = a.get("expressao", "feliz")
            if a["tipo"] in ("acenar", "oferecer"):
                item["lado"] = 1 if role[cid] == "P" else -1
            if a["tipo"] == "virar":
                item["angulo"] = 60
            out_acts.append(item)
        falas = [{"t0": l["t0"], "envelope": l["envelope"], "env_fps": 12}
                 for l in plan["falas"] if l.get("falante") == cid]
        specs.append({"ficha": sheet, "inicio": list(start), "direcao": face, "acoes": out_acts, "falas": falas})

    objetos = []
    ob = scene.get("objeto")
    if ob:
        P_id = ids[0]
        A_id = ids[1] if len(ids) > 1 else ids[0]
        pos = {"P_frente": (-0.2, -0.65), "A_frente": (0.2, -0.65), "longe": (1.6, 2.5)}.get(ob.get("posicao"), (0, -0.6))
        o = {"id": "obj", "tipo": ob["tipo"], "pos": list(pos), "movimentos": []}
        holder = next((a for a in scene["acoes"] if a["tipo"] == "segurar"), None)
        if holder:  # quem "segura" pega o objeto nas maos
            t0, _ = _interval(holder["em"], plan, dur)
            o["movimentos"].append({"t0": round(t0, 2), "t1": round(t0 + 0.5, 2), "para": holder["personagem"]})
        if ob.get("entrega"):
            giver, taker = (P_id, A_id) if ob["entrega"] == "P->A" else (A_id, P_id)
            give = next((a for a in scene["acoes"] if a["personagem"] == giver and a["tipo"] == "oferecer"), None)
            t0, _ = _interval(give["em"], plan, dur) if give else _interval("narracao", plan, dur)
            o["movimentos"].append({"t0": round(t0 + 0.3, 2), "t1": round(t0 + 1.3, 2), "para": taker})
        o["movimentos"].sort(key=lambda m: m["t0"])
        objetos.append(o)

    cam = {"plano": scene["plano"] if len(ids) > 1 or scene["plano"] != "dois" else "medio",
           "movimento": scene["movimento"]}
    if scene.get("foco"):
        cam["foco"] = scene["foco"]
    return {
        "saida": str(out_dir),
        "duracao": dur,
        "semente": seed,
        "render": render,
        "cenario": ad.load_set(scene["cenario"]),
        "personagens": specs,
        "objetos": objetos,
        "camera": cam,
    }


def sfx_cues(scene, spec, plan):
    """Lista (efeito, instante) dentro da cena."""
    cues = []
    wanted = set(scene.get("efeitos", []))
    for cs in spec["personagens"]:
        for a in cs["acoes"]:
            if a["tipo"] == "andar" and "passos" in wanted:
                cues.append(("passos", a["t0"]))
            if a["tipo"] == "pular":
                cues.append(("boing", a["t0"] + 0.25))
            if a["tipo"] == "comemorar":
                cues.append(("boing", a["t0"] + 0.25))
                if "risadas" in wanted:
                    cues.append(("risadas", a["t0"] + 0.3))
    for o in spec.get("objetos", []):
        for mv in o.get("movimentos", []):
            cues.append(("brilho", mv["t1"] - 0.1))
            cues.append(("pop", mv["t0"]))
    if "brilho" in wanted and not any(c[0] == "brilho" for c in cues):
        cues.append(("brilho", max(0.2, plan["duracao"] - 1.6)))
    if "pop" in wanted and not any(c[0] == "pop" for c in cues):
        cues.append(("pop", 0.3))
    if scene["cenario"] in ("floresta", "campo"):
        cues.append(("passaros", 0.2))
    return cues


def music_segments(scenes, starts, durations):
    """Ate 2 blocos musicais: clima inicial e clima do climax/final."""
    emos = [s["emocao_musical"] for s in scenes]
    total = starts[-1] + durations[-1]
    k = next((i for i, e in enumerate(emos) if e == "celebracao"), None)
    if k is None or k == 0:
        return [{"emocao": emos[0], "inicio": 0.0, "fim": total}]
    return [{"emocao": emos[0], "inicio": 0.0, "fim": starts[k] + 0.6},
            {"emocao": "celebracao", "inicio": starts[k] - 0.6, "fim": total}]
