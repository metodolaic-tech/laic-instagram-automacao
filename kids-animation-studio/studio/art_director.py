"""Modulo B - Diretor de Arte.

Responsavel pela consistencia visual:
  * fichas de personagens (aparencia, roupas, proporcoes, expressoes,
    caracteristicas permanentes) salvas na biblioteca e reutilizadas
    entre episodios;
  * paletas e estilo do estudio;
  * prompts visuais padronizados (para quem quiser gerar artes 2D de apoio
    em outras ferramentas, mantendo a mesma descricao);
  * folha de modelo (model sheet) renderizada em 3D para aprovacao.

Todos os personagens sao ORIGINAIS: montados a partir de formas simples
e paletas proprias, sem copiar personagens de estudios conhecidos.
"""
import json
import os
import random
import re
import unicodedata

from pathlib import Path

from .config import LIBRARY

# KAS_PERSONAGENS permite usar outra pasta (ex.: nos testes automatizados)
CHAR_DIR = Path(os.environ.get("KAS_PERSONAGENS", LIBRARY / "characters"))
SET_DIR = LIBRARY / "sets"

ESTILO_ESTUDIO = (
    "animacao infantil 3D estilizada e original, personagens com cabeca grande e olhos "
    "expressivos com brilho, formas arredondadas, cores vibrantes, iluminacao suave de fim "
    "de manha, sombras macias, profundidade de campo cinematografica, cenario detalhado"
)

# Especies suportadas pelo gerador 3D procedural.
# Cada especie define formas (orelhas, cauda, extras) e paletas possiveis.
ESPECIES = {
    "leao": {"nome": "leãozinho", "feminino": "leoazinha", "orelhas": "redondas", "cauda": "tufo", "extras": ["juba"],
             "paletas": [{"pelo": "#E8A33C", "barriga": "#F7D9A0", "juba": "#B5541C"},
                         {"pelo": "#F0B44C", "barriga": "#FBE3B5", "juba": "#C2662A"}],
             "palavras": ["leao", "leaozinho", "leoazinha", "leoa"]},
    "coelho": {"nome": "coelhinho", "feminino": "coelhinha", "orelhas": "longas", "cauda": "fofa", "extras": [],
               "paletas": [{"pelo": "#F4F1EC", "barriga": "#FFFFFF", "juba": "#E8DCCB", "bochecha": "#FFB3C1"},
                           {"pelo": "#C8A27A", "barriga": "#F3E3CC", "juba": "#A47D58"}],
               "palavras": ["coelho", "coelhinho", "coelha", "coelhinha"]},
    "urso": {"nome": "ursinho", "feminino": "ursinha", "orelhas": "redondas", "cauda": "curta", "extras": [],
             "paletas": [{"pelo": "#8B5A2B", "barriga": "#D9B38C", "juba": "#5E3B1A"},
                         {"pelo": "#B07A4A", "barriga": "#EED2B0", "juba": "#7A4E2D"}],
             "palavras": ["urso", "ursinho", "ursa", "ursinha"]},
    "elefante": {"nome": "elefantinho", "feminino": "elefantinha", "orelhas": "grandes", "cauda": "fina", "extras": ["tromba"],
                 "paletas": [{"pelo": "#9FB3C8", "barriga": "#C9D6E3", "juba": "#7F93A8", "bochecha": "#F7A8B8"}],
                 "palavras": ["elefante", "elefantinho", "elefantinha"]},
    "raposa": {"nome": "raposinha", "feminino": "raposinha", "orelhas": "pontudas", "cauda": "longa", "extras": [],
               "paletas": [{"pelo": "#EE7B30", "barriga": "#FFF1E0", "juba": "#C85A1A"}],
               "palavras": ["raposa", "raposinha", "raposo"]},
    "gato": {"nome": "gatinho", "feminino": "gatinha", "orelhas": "pontudas", "cauda": "longa", "extras": [],
             "paletas": [{"pelo": "#9E9E9E", "barriga": "#F5F5F5", "juba": "#757575"},
                         {"pelo": "#F2A65A", "barriga": "#FFF3E0", "juba": "#D9822B"}],
             "palavras": ["gato", "gatinho", "gata", "gatinha"]},
    "cachorro": {"nome": "cachorrinho", "feminino": "cachorrinha", "orelhas": "caidas", "cauda": "fofa", "extras": [],
                 "paletas": [{"pelo": "#D9A066", "barriga": "#FFF1DC", "juba": "#8C5A2B"},
                             {"pelo": "#FFFFFF", "barriga": "#F5F0E6", "juba": "#3A3A3A"}],
                 "palavras": ["cachorro", "cachorrinho", "cachorra", "cachorrinha", "cao", "filhote"]},
    "macaco": {"nome": "macaquinho", "feminino": "macaquinha", "orelhas": "redondas", "cauda": "longa", "extras": [],
               "paletas": [{"pelo": "#7B4A2A", "barriga": "#E9C9A3", "juba": "#5A341C"}],
               "palavras": ["macaco", "macaquinho", "macaca", "macaquinha"]},
    "ovelha": {"nome": "ovelhinha", "feminino": "ovelhinha", "orelhas": "caidas", "cauda": "fofa", "extras": ["la"],
               "paletas": [{"pelo": "#E9E4DA", "barriga": "#FFFFFF", "juba": "#FFFFFF", "nariz": "#3A2E2A"}],
               "palavras": ["ovelha", "ovelhinha", "cordeiro", "cordeirinho", "carneiro"]},
}

NOMES = {
    "m": ["Tito", "Beto", "Juca", "Nino", "Dudu", "Pipo", "Lelo", "Teo", "Bento", "Caco"],
    "f": ["Lila", "Mia", "Nina", "Bia", "Lulu", "Tata", "Duda", "Kiki", "Mel", "Lia"],
}
CORES_ROUPA = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#14B8A6"]
CORES_OLHOS = ["#5B3A1A", "#2F6B3A", "#1E4E8C", "#6B4423"]
ACESSORIOS = ["lenco", "laco", "chapeu", "mochila"]


def slug(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def detect_species(text):
    """Encontra a especie citada no tema (ex.: 'leaozinho' -> 'leao')."""
    norm = " " + slug(text).replace("_", " ") + " "
    for sp, d in ESPECIES.items():
        for w in d["palavras"]:
            if f" {w} " in norm or f" {w}s " in norm:
                return sp
    return None


def list_characters():
    out = []
    for f in sorted(CHAR_DIR.glob("*.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def load_character(cid):
    f = CHAR_DIR / f"{cid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def save_character(sheet):
    CHAR_DIR.mkdir(parents=True, exist_ok=True)
    (CHAR_DIR / f"{sheet['id']}.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=2), encoding="utf-8")


def load_set(sid):
    return json.loads((SET_DIR / f"{sid}.json").read_text(encoding="utf-8"))


def list_sets():
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(SET_DIR.glob("*.json"))]


def find_character(species, exclude=()):
    """Reutiliza um personagem existente da especie (consistencia entre episodios)."""
    for c in list_characters():
        if c["especie"] == species and c["id"] not in exclude:
            return c
    return None


def create_character(species, genero="m", nome=None, papel="protagonista", seed=None, personalidade=None):
    rnd = random.Random(seed if seed is not None else f"{species}{genero}{nome}")
    d = ESPECIES[species]
    nome = nome or rnd.choice(NOMES[genero])
    paleta = dict(rnd.choice(d["paletas"]))
    paleta.setdefault("juba", paleta["pelo"])
    paleta.setdefault("nariz", "#3A2A25")
    paleta.setdefault("bochecha", "#FF9AA2")
    paleta["olhos"] = rnd.choice(CORES_OLHOS)
    paleta["roupa"] = rnd.choice(CORES_ROUPA)
    acessorio = rnd.choice(ACESSORIOS if genero == "f" else ["lenco", "chapeu", "mochila"])
    especie_nome = d["feminino"] if genero == "f" else d["nome"]
    pers = personalidade or rnd.choice([
        "curioso, brincalhão e cheio de energia", "gentil, calmo e observador",
        "corajoso, um pouco teimoso, mas de bom coração", "alegre, falante e muito amigo",
    ])
    if genero == "f":
        pers = pers.replace("curioso", "curiosa").replace("brincalhão", "brincalhona").replace("observador", "observadora") \
            .replace("corajoso", "corajosa").replace("teimoso", "teimosa").replace("calmo", "calma").replace("amigo", "amiga")
    acc_txt = {"lenco": "lenço no pescoço", "laco": "laço na cabeça", "chapeu": "chapeuzinho", "mochila": "mochilinha nas costas"}[acessorio]
    sheet = {
        "id": f"{slug(nome)}_{species}",
        "nome": nome,
        "especie": species,
        "especie_nome": especie_nome,
        "genero": genero,
        "papel": papel,
        "personalidade": pers,
        "cores": paleta,
        "proporcoes": {"altura": round(rnd.uniform(0.95, 1.08), 2), "cabeca": round(rnd.uniform(1.0, 1.1), 2),
                       "olhos": round(rnd.uniform(1.0, 1.15), 2)},
        "orelhas": d["orelhas"],
        "cauda": d["cauda"],
        "extras": d["extras"],
        "acessorio": acessorio,
        "caracteristicas_permanentes": [
            f"{especie_nome} de pelagem {paleta['pelo']} e barriga {paleta['barriga']}",
            f"olhos grandes cor {paleta['olhos']} com pontos de brilho",
            f"usa sempre {acc_txt} na cor {paleta['roupa']}",
            "cabeça grande (proporção infantil), corpo arredondado, bochechas rosadas",
        ],
        "expressoes": ["neutro", "feliz", "triste", "surpreso", "pensativo", "bravo"],
        "voz": {"provedor": "piper", "modelo": "pt_BR-jeff-medium" if genero == "m" else "pt_BR-faber-medium",
                "tom": 1.22 if genero == "m" else 1.18, "velocidade": 1.0},
        "origem": "personagem original gerado pelo Kids Animation Studio AI",
    }
    sheet["prompt_visual"] = visual_prompt(sheet)
    return sheet


def visual_prompt(sheet):
    c = sheet["cores"]
    return (
        f"{sheet['nome']}, {sheet['especie_nome']} original, {ESTILO_ESTUDIO}; pelagem {c['pelo']}, "
        f"barriga {c['barriga']}, olhos {c['olhos']} grandes e brilhantes, "
        + "; ".join(sheet["caracteristicas_permanentes"])
        + "; personalidade: " + sheet["personalidade"]
        + ". Nao copiar personagens existentes."
    )


def character_sheet_markdown(sheet):
    lines = [f"# Ficha do personagem: {sheet['nome']}", "",
             f"- **Especie:** {sheet['especie_nome']}", f"- **Papel:** {sheet['papel']}",
             f"- **Personalidade:** {sheet['personalidade']}",
             f"- **Proporcoes:** altura {sheet['proporcoes']['altura']}, cabeca {sheet['proporcoes']['cabeca']}, olhos {sheet['proporcoes']['olhos']}",
             f"- **Acessorio fixo:** {sheet['acessorio']}", "", "## Paleta"]
    for k, v in sheet["cores"].items():
        lines.append(f"- {k}: `{v}`")
    lines += ["", "## Caracteristicas permanentes (nunca mudam entre episodios)"]
    lines += [f"- {x}" for x in sheet["caracteristicas_permanentes"]]
    lines += ["", "## Expressoes disponiveis", ", ".join(sheet["expressoes"]), "",
              "## Voz", f"{sheet['voz']}", "", "## Prompt visual padronizado", sheet["prompt_visual"], ""]
    return "\n".join(lines)


def ensure_default_library():
    """Cria personagens iniciais na biblioteca (se ainda nao existirem)."""
    defaults = [("leao", "m", "Tito", "protagonista", "curioso, brincalhão e cheio de energia"),
                ("coelho", "f", "Lila", "amiga", "gentil, calma e observadora"),
                ("urso", "m", "Bento", "amigo", "alegre, falante e muito amigo"),
                ("elefante", "f", "Nina", "amiga", "corajosa, um pouco teimosa, mas de bom coração")]
    for sp, g, n, papel, pers in defaults:
        sid = f"{slug(n)}_{sp}"
        if not (CHAR_DIR / f"{sid}.json").exists():
            save_character(create_character(sp, g, n, papel, seed=sid, personalidade=pers))
