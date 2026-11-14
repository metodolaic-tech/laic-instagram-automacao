"""Modulo A - Roteirista.

Cria historias infantis originais, curtas, educativas e com estrutura
gancho -> desenvolvimento -> conclusao (com licao final).

Dois motores:
  * "local"  (padrao, gratis, offline): modelos narrativos por valor/categoria
              preenchidos com os personagens da biblioteca;
  * "claude" (opcional, pago por uso): pede a historia ao Claude via API
              oficial da Anthropic, com saida em JSON validada. So roda com
              ANTHROPIC_API_KEY e `permitir_servicos_pagos = true`.

A saida e sempre o mesmo formato (story.json), que alimenta os demais modulos.
Cada cena traz: cenario, plano/movimento de camera, emocao musical,
narracao, falas, acoes dos personagens, objetos e efeitos sonoros.
"""
import json
import os
import re

from . import art_director as ad

CATEGORIAS = {
    "valores": "Valores familiares",
    "animais": "Animais",
    "aventura": "Aventuras",
    "educacao": "Educação",
    "biblica": "Histórias bíblicas (recontadas com animais)",
}

FAIXAS = {"2-4": "2 a 4 anos", "4-6": "4 a 6 anos", "6-8": "6 a 8 anos"}

# Palavras do tema -> modelo de historia
TEMAS = [
    ("compartilhar", ["compartilh", "dividir", "partilh", "egois"]),
    ("coragem", ["corag", "medo", "valent", "escuro"]),
    ("honestidade", ["verdade", "mentir", "mentira", "honest", "sincer"]),
    ("paciencia", ["pacien", "esperar", "espera", "calma"]),
    ("gratidao", ["obrigad", "gratid", "agradec", "grato", "grata"]),
    ("biblica_ovelha", ["ovelha perdida", "parabola da ovelha", "ovelhinha perdida"]),
    ("biblica_samaritano", ["samaritano", "proximo"]),
    ("educacao_contar", ["contar", "numero", "numeros", "matematic"]),
    ("aventura_estrela", ["aventura", "estrela", "tesouro", "explorar"]),
    ("amizade", ["amizade", "amigo", "amiga", "ajud", "ajudar", "gentil"]),
]

# ---------------------------------------------------------------------------
# Modelos de historia.
# {P}=protagonista {Pe}=especie do protagonista {A}=amigo(a) {Ae}=especie
# Cada "batida" vira uma cena. "essencial": entra mesmo nos videos curtos.
# acoes: quem (P/A), tipo, em (inicio | narracao | falaN | fim)
# ---------------------------------------------------------------------------
MODELOS = {
    "compartilhar": {
        "categoria": "valores", "valor": "compartilhar", "objeto": "frutas",
        "titulo": "{P} Aprende a Compartilhar",
        "moral": "Quando a gente divide, a alegria fica muito maior!",
        "batidas": [
            {"essencial": True, "cenario": "savana", "plano": "geral", "movimento": "aproximar", "emocao": "aventura",
             "so_P": True,
             "narracao": "Na savana dourada, o {Pe} {P} encontrou a cesta de frutas mais bonita de todas!",
             "falas": [("P", "Uau! São todas minhas!", "feliz")],
             "acoes": [("P", "andar", "narracao"), ("P", "pular", "fala0"), ("P", "expressao:feliz", "inicio")],
             "efeitos": ["passos", "boing"], "objeto_pos": "P_frente"},
            {"essencial": True, "cenario": "savana", "plano": "dois", "movimento": "panoramica", "emocao": "ternura",
             "narracao": "Então chegou {A}, com a barriga roncando de fome.",
             "falas": [("A", "{P}, você me dá uma frutinha?", "triste"), ("P", "Não! A cesta é só minha!", "bravo")],
             "acoes": [("A", "andar", "narracao"), ("A", "expressao:triste", "fala0"), ("P", "segurar", "fala1"),
                       ("P", "expressao:bravo", "fala1")],
             "efeitos": ["passos"], "objeto_pos": "P_frente"},
            {"essencial": False, "cenario": "savana", "plano": "close", "movimento": "aproximar", "emocao": "suspense",
             "foco": "P",
             "narracao": "Mas comer sozinho não teve graça nenhuma. {P} ficou pensando...",
             "falas": [("P", "Hum... será que dividir é bom?", "pensativo")],
             "acoes": [("P", "expressao:pensativo", "narracao"), ("P", "acenar_cabeca", "fala0")],
             "efeitos": []},
            {"essencial": True, "cenario": "savana", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "{P} ofereceu a cesta, e os dois fizeram um piquenique.",
             "falas": [("P", "Toma, {A}! Vamos dividir!", "feliz"), ("A", "Obrigada, {P}! Você é demais!", "feliz")],
             "acoes": [("P", "expressao:feliz", "inicio"), ("P", "oferecer", "fala0"), ("A", "expressao:feliz", "fala1"),
                       ("A", "comemorar", "fala1"), ("P", "comemorar", "fim")],
             "efeitos": ["brilho", "boing"], "entrega": True},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "E aprenderam que quando a gente divide, a alegria fica muito maior!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "amizade": {
        "categoria": "valores", "valor": "amizade", "objeto": "bola",
        "titulo": "{P} e o Poder da Amizade",
        "moral": "Amigo de verdade ajuda o outro sempre que pode!",
        "batidas": [
            {"essencial": True, "cenario": "campo", "plano": "geral", "movimento": "lateral", "emocao": "alegria",
             "so_P": True,
             "narracao": "No campo florido, {P} brincava de bola quando ouviu um choro.",
             "falas": [("P", "Quem está chorando?", "surpreso")],
             "acoes": [("P", "pular", "narracao"), ("P", "expressao:surpreso", "fala0")], "efeitos": ["boing"],
             "objeto_pos": "P_frente"},
            {"essencial": True, "cenario": "campo", "plano": "dois", "movimento": "panoramica", "emocao": "ternura",
             "narracao": "Era {A}, que não tinha ninguém para brincar.",
             "falas": [("A", "Ninguém quer brincar comigo...", "triste"), ("P", "Eu quero! Vem comigo!", "feliz")],
             "acoes": [("A", "andar", "narracao"), ("A", "expressao:triste", "fala0"), ("P", "acenar", "fala1"),
                       ("P", "expressao:feliz", "fala1")], "efeitos": ["passos"]},
            {"essencial": True, "cenario": "campo", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "Os dois brincaram a tarde inteira e viraram melhores amigos.",
             "falas": [("A", "Obrigada por ser meu amigo!", "feliz")],
             "acoes": [("A", "expressao:feliz", "inicio"), ("P", "comemorar", "narracao"), ("A", "comemorar", "fala0")],
             "efeitos": ["brilho", "risadas"], "entrega": True},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Amigo de verdade ajuda o outro sempre que pode!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "coragem": {
        "categoria": "valores", "valor": "coragem", "objeto": "estrela",
        "titulo": "{P} e a Floresta Escura",
        "moral": "Ter coragem não é não ter medo: é seguir em frente mesmo com medo!",
        "batidas": [
            {"essencial": True, "cenario": "floresta", "plano": "geral", "movimento": "aproximar", "emocao": "suspense",
             "so_P": True,
             "narracao": "Na floresta, uma estrelinha caiu bem perto de {P}. Mas {P} tinha medo de ir lá!",
             "falas": [("P", "E se tiver um monstro?", "surpreso")],
             "acoes": [("P", "expressao:surpreso", "inicio"), ("P", "segurar", "fala0")], "efeitos": ["brilho"],
             "objeto_pos": "longe"},
            {"essencial": True, "cenario": "floresta", "plano": "dois", "movimento": "panoramica", "emocao": "ternura",
             "narracao": "{A} chegou e segurou a mão do amigo.",
             "falas": [("A", "Vamos juntos? Um passinho de cada vez!", "feliz"), ("P", "Tá bom... eu vou tentar!", "pensativo")],
             "acoes": [("A", "andar", "narracao"), ("A", "acenar", "fala0"), ("P", "acenar_cabeca", "fala1")],
             "efeitos": ["passos"]},
            {"essencial": True, "cenario": "floresta", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "Passo a passo, eles chegaram. Era só uma estrelinha brilhante!",
             "falas": [("P", "Eu consegui! Eu fui corajoso!", "feliz")],
             "acoes": [("P", "andar", "narracao"), ("A", "andar", "narracao"), ("P", "comemorar", "fala0"),
                       ("P", "expressao:feliz", "fala0")], "efeitos": ["passos", "brilho"]},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Ter coragem não é não ter medo: é seguir em frente mesmo com medo!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "honestidade": {
        "categoria": "valores", "valor": "honestidade", "objeto": "bola",
        "titulo": "{P} Fala a Verdade",
        "moral": "Falar a verdade deixa o coração leve e a amizade forte!",
        "batidas": [
            {"essencial": True, "cenario": "campo", "plano": "geral", "movimento": "lateral", "emocao": "alegria",
             "so_P": True,
             "narracao": "{P} chutou a bola de {A} tão forte que ela foi parar no rio!",
             "falas": [("P", "Ih... e agora?", "surpreso")],
             "acoes": [("P", "pular", "narracao"), ("P", "expressao:surpreso", "fala0")], "efeitos": ["boing", "whoosh"]},
            {"essencial": True, "cenario": "campo", "plano": "dois", "movimento": "panoramica", "emocao": "suspense",
             "narracao": "{A} chegou procurando a bola. {P} pensou em esconder o que fez.",
             "falas": [("A", "Você viu minha bola?", "triste"), ("P", "Fui eu... desculpa, {A}.", "triste")],
             "acoes": [("A", "andar", "narracao"), ("P", "expressao:pensativo", "narracao"), ("P", "expressao:triste", "fala1")],
             "efeitos": ["passos"]},
            {"essencial": True, "cenario": "campo", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "{A} deu um abraço apertado. E juntos pegaram a bola de volta.",
             "falas": [("A", "Obrigada por falar a verdade!", "feliz")],
             "acoes": [("A", "expressao:feliz", "inicio"), ("P", "expressao:feliz", "narracao"), ("A", "comemorar", "fala0")],
             "efeitos": ["brilho"], "objeto_pos": "P_frente"},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Falar a verdade deixa o coração leve e a amizade forte!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "paciencia": {
        "categoria": "valores", "valor": "paciência", "objeto": "frutas",
        "titulo": "{P} Aprende a Esperar",
        "moral": "Tudo que é bom tem a sua hora. Quem espera, colhe!",
        "batidas": [
            {"essencial": True, "cenario": "campo", "plano": "geral", "movimento": "aproximar", "emocao": "alegria",
             "so_P": True,
             "narracao": "{P} plantou uma sementinha e queria frutas para hoje mesmo!",
             "falas": [("P", "Cresce logo, sementinha!", "bravo")],
             "acoes": [("P", "pular", "fala0"), ("P", "expressao:bravo", "fala0")], "efeitos": ["boing"]},
            {"essencial": True, "cenario": "campo", "plano": "dois", "movimento": "panoramica", "emocao": "ternura",
             "narracao": "{A} explicou que as plantas precisam de tempo, água e sol.",
             "falas": [("A", "Vamos cuidar dela juntos, um pouquinho por dia.", "feliz"), ("P", "Tá bom, eu espero!", "pensativo")],
             "acoes": [("A", "andar", "narracao"), ("A", "acenar", "fala0"), ("P", "acenar_cabeca", "fala1")],
             "efeitos": ["passos"]},
            {"essencial": True, "cenario": "campo", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "Os dias passaram e, finalmente, vieram frutas docinhas para todos!",
             "falas": [("P", "Valeu a pena esperar!", "feliz")],
             "acoes": [("P", "comemorar", "fala0"), ("A", "comemorar", "fala0"), ("P", "expressao:feliz", "inicio")],
             "efeitos": ["brilho"], "objeto_pos": "P_frente"},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Tudo que é bom tem a sua hora. Quem espera, colhe!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "gratidao": {
        "categoria": "valores", "valor": "gratidão", "objeto": "presente",
        "titulo": "O Obrigado de {P}",
        "moral": "Dizer obrigado deixa todo mundo mais feliz!",
        "batidas": [
            {"essencial": True, "cenario": "floresta", "plano": "geral", "movimento": "aproximar", "emocao": "alegria",
             "narracao": "Era aniversário de {P}, e {A} trouxe um presente surpresa!",
             "falas": [("A", "Feliz aniversário, {P}!", "feliz")],
             "acoes": [("A", "andar", "narracao"), ("A", "acenar", "fala0"), ("P", "expressao:surpreso", "fala0")],
             "efeitos": ["passos", "brilho"], "objeto_pos": "A_frente"},
            {"essencial": True, "cenario": "floresta", "plano": "dois", "movimento": "panoramica", "emocao": "ternura",
             "narracao": "{P} ficou tão animado que quase esqueceu de agradecer.",
             "falas": [("P", "Obrigado, {A}! Você é muito especial!", "feliz")],
             "acoes": [("P", "comemorar", "narracao"), ("P", "expressao:feliz", "fala0")], "efeitos": ["boing"],
             "entrega_inversa": True},
            {"essencial": True, "cenario": "floresta", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "{A} sorriu de orelha a orelha. Um obrigado vale muito!",
             "falas": [("A", "De nada, meu amigo!", "feliz")],
             "acoes": [("A", "comemorar", "narracao"), ("P", "acenar", "fala0")], "efeitos": ["brilho"]},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Dizer obrigado deixa todo mundo mais feliz!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "biblica_ovelha": {
        "categoria": "biblica", "valor": "amor e cuidado", "objeto": None, "especies": ("urso", "ovelha"),
        "titulo": "A Ovelhinha Perdida",
        "moral": "Assim como na parábola de Jesus, cada um de nós é amado e procurado!",
        "batidas": [
            {"essencial": True, "cenario": "campo", "plano": "geral", "movimento": "aproximar", "emocao": "ternura",
             "narracao": "{P} cuidava de cem ovelhinhas. Um dia, contou e faltava uma: {A}!",
             "falas": [("P", "Onde está a {A}?", "surpreso")],
             "acoes": [("P", "expressao:surpreso", "fala0"), ("P", "virar", "narracao")], "efeitos": []},
            {"essencial": True, "cenario": "floresta", "plano": "geral", "movimento": "seguir", "emocao": "suspense",
             "narracao": "{P} procurou por toda a floresta, sem desistir.",
             "falas": [("P", "{A}! Cadê você?", "triste")],
             "acoes": [("P", "andar", "narracao"), ("P", "expressao:triste", "fala0")], "efeitos": ["passos"], "so_P": True},
            {"essencial": True, "cenario": "floresta", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "Até que encontrou {A}, e houve uma grande festa!",
             "falas": [("A", "Você veio me buscar!", "feliz"), ("P", "Claro! Você é muito importante!", "feliz")],
             "acoes": [("A", "comemorar", "fala0"), ("P", "comemorar", "fala1"), ("A", "expressao:feliz", "inicio")],
             "efeitos": ["brilho", "risadas"]},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Assim como na parábola de Jesus, cada um de nós é amado e procurado!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "biblica_samaritano": {
        "categoria": "biblica", "valor": "amar o próximo", "objeto": "cesta", "especies": None,
        "titulo": "{P}, o Bom Vizinho",
        "moral": "Como ensinou Jesus: ame o seu próximo e ajude quem precisa!",
        "batidas": [
            {"essencial": True, "cenario": "floresta", "plano": "geral", "movimento": "lateral", "emocao": "suspense",
             "narracao": "{A} tropeçou na trilha e machucou o pé. Muitos passaram e não pararam.",
             "falas": [("A", "Ai, ai... alguém me ajuda?", "triste")],
             "acoes": [("A", "expressao:triste", "inicio")], "efeitos": ["boing"]},
            {"essencial": True, "cenario": "floresta", "plano": "dois", "movimento": "panoramica", "emocao": "ternura",
             "narracao": "Mas {P} parou, cuidou do machucado e dividiu seu lanche.",
             "falas": [("P", "Calma, {A}. Eu vou te ajudar!", "feliz")],
             "acoes": [("P", "andar", "narracao"), ("P", "oferecer", "fala0")], "efeitos": ["passos"], "entrega": True},
            {"essencial": True, "cenario": "floresta", "plano": "dois", "movimento": "aproximar", "emocao": "celebracao",
             "narracao": "{A} ficou bem. E {P} mostrou o que é amar o próximo.",
             "falas": [("A", "Obrigada, você tem um coração enorme!", "feliz")],
             "acoes": [("A", "comemorar", "fala0"), ("P", "expressao:feliz", "inicio"), ("A", "expressao:feliz", "inicio")],
             "efeitos": ["brilho"]},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Como ensinou Jesus: ame o seu próximo e ajude quem precisa!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "educacao_contar": {
        "categoria": "educacao", "valor": "aprender a contar", "objeto": "frutas",
        "titulo": "Contando Frutas com {P}",
        "moral": "Contar é divertido: um, dois, três, e a gente aprende de vez!",
        "batidas": [
            {"essencial": True, "cenario": "campo", "plano": "geral", "movimento": "aproximar", "emocao": "alegria",
             "so_P": True,
             "narracao": "{P} achou uma cesta de frutas. Quantas será que tem?",
             "falas": [("P", "Me ajuda a contar?", "feliz")],
             "acoes": [("P", "andar", "narracao"), ("P", "acenar", "fala0")], "efeitos": ["passos"], "objeto_pos": "P_frente"},
            {"essencial": True, "cenario": "campo", "plano": "close", "movimento": "aproximar", "emocao": "alegria",
             "foco": "P",
             "narracao": "Vamos lá! Uma, duas, três, quatro, cinco, seis!",
             "falas": [("P", "Seis frutinhas!", "surpreso")],
             "acoes": [("P", "acenar_cabeca", "narracao"), ("P", "pular", "fala0")], "efeitos": ["pop", "boing"]},
            {"essencial": True, "cenario": "campo", "plano": "dois", "movimento": "panoramica", "emocao": "celebracao",
             "narracao": "{A} chegou, e cada um ficou com três. Seis dividido por dois!",
             "falas": [("A", "Três para mim e três para você!", "feliz")],
             "acoes": [("A", "andar", "narracao"), ("A", "comemorar", "fala0"), ("P", "comemorar", "fala0")],
             "efeitos": ["brilho"], "entrega": True},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Contar é divertido: um, dois, três, e a gente aprende de vez!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
    "aventura_estrela": {
        "categoria": "aventura", "valor": "trabalho em equipe", "objeto": "estrela",
        "titulo": "{P} e a Estrela Perdida",
        "moral": "Juntos, a gente vai mais longe!",
        "batidas": [
            {"essencial": True, "cenario": "floresta", "plano": "geral", "movimento": "aproximar", "emocao": "aventura",
             "so_P": True,
             "narracao": "Uma estrela caiu do céu, e {P} decidiu devolvê-la para casa!",
             "falas": [("P", "Que aventura incrível!", "surpreso")],
             "acoes": [("P", "pular", "fala0"), ("P", "expressao:surpreso", "inicio")], "efeitos": ["brilho", "boing"],
             "objeto_pos": "longe"},
            {"essencial": True, "cenario": "savana", "plano": "geral", "movimento": "seguir", "emocao": "aventura",
             "narracao": "{P} e {A} atravessaram a savana com a estrela.",
             "falas": [("A", "Juntos a gente chega lá!", "feliz")],
             "acoes": [("P", "andar", "narracao"), ("A", "andar", "narracao"), ("A", "acenar", "fala0")],
             "efeitos": ["passos"]},
            {"essencial": True, "cenario": "entardecer", "plano": "dois", "movimento": "grua", "emocao": "celebracao",
             "narracao": "No alto da colina, a estrela voltou a brilhar no céu!",
             "falas": [("P", "Conseguimos, {A}!", "feliz")],
             "acoes": [("P", "comemorar", "fala0"), ("A", "comemorar", "fala0"), ("P", "expressao:feliz", "inicio")],
             "efeitos": ["brilho"]},
            {"essencial": False, "cenario": "entardecer", "plano": "geral", "movimento": "grua", "emocao": "ternura",
             "narracao": "Juntos, a gente vai mais longe!",
             "falas": [], "acoes": [("P", "acenar", "narracao"), ("A", "acenar", "narracao")], "efeitos": ["brilho"]},
        ],
    },
}


def detect_template(tema, categoria=None):
    t = ad.slug(tema).replace("_", " ")
    for key, words in TEMAS:
        if any(w in t for w in words):
            return key
    if categoria == "biblica":
        return "biblica_ovelha"
    if categoria == "educacao":
        return "educacao_contar"
    if categoria == "aventura":
        return "aventura_estrela"
    return "amizade"


def _gender_from_theme(tema, species):
    t = ad.slug(tema)
    fem = ad.ESPECIES[species]["feminino"]
    return "f" if ad.slug(fem) in t or re.search(r"\b(uma|a) (" + species + r"a)\b", t.replace("_", " ")) else "m"


def _name_from_theme(tema):
    m = re.search(r"chamad[oa]s? ([A-ZÀ-Ú][a-zà-ú]+)", tema)
    return m.group(1) if m else None


def choose_characters(tema, modelo):
    """Escolhe protagonista e amigo, reutilizando a biblioteca quando possivel."""
    ad.ensure_default_library()
    species = ad.detect_species(tema)
    pref = modelo.get("especies")
    if pref and not species:
        species = pref[0]
    species = species or "leao"
    nome = _name_from_theme(tema)
    genero = _gender_from_theme(tema, species)
    prot = None
    if not nome:
        prot = ad.find_character(species)
    if prot is None or (nome and prot["nome"] != nome):
        prot = ad.create_character(species, genero, nome, "protagonista")
        ad.save_character(prot)
    # amigo: outra especie (ou a pedida pelo modelo)
    friend_species = pref[1] if pref else None
    if not friend_species:
        rest = [w for w in ad.slug(tema).split("_")]
        for sp, d in ad.ESPECIES.items():
            if sp != species and any(w in rest for w in d["palavras"]):
                friend_species = sp
                break
    friend_species = friend_species or ("coelho" if species != "coelho" else "urso")
    friend = ad.find_character(friend_species, exclude=(prot["id"],))
    if friend is None:
        friend = ad.create_character(friend_species, "f" if prot["genero"] == "m" else "m", None, "amigo(a)")
        ad.save_character(friend)
    return prot, friend


def _fill(text, P, A):
    return (text.replace("{P}", P["nome"]).replace("{A}", A["nome"])
            .replace("{Pe}", P["especie_nome"]).replace("{Ae}", A["especie_nome"]))


def _fix_gender(text, ch):
    if ch["genero"] == "f":
        text = text.replace("corajoso", "corajosa").replace("animado", "animada").replace("Obrigado", "Obrigada")
    else:
        text = text.replace("Obrigada", "Obrigado")
    return text


def write_story_local(tema, duracao=30, faixa="4-6", categoria=None, cenario=None):
    key = detect_template(tema, categoria)
    m = MODELOS[key]
    P, A = choose_characters(tema, m)
    n_scenes = max(3, min(len(m["batidas"]), round(duracao / 9)))
    beats = [b for b in m["batidas"] if b["essencial"]]
    extras = [b for b in m["batidas"] if not b["essencial"]]
    while len(beats) < n_scenes and extras:
        e = extras.pop(0)
        idx = m["batidas"].index(e)
        # insere na ordem original
        order = [m["batidas"].index(b) for b in beats]
        pos = sum(1 for o in order if o < idx)
        beats.insert(pos, e)
    ids = {"P": P["id"], "A": A["id"]}
    scenes = []
    for i, b in enumerate(beats):
        falas = []
        for who, txt, emo in b["falas"]:
            ch = P if who == "P" else A
            falas.append({"personagem": ids[who], "texto": _fix_gender(_fill(txt, P, A), ch), "emocao": emo})
        acoes = []
        for who, tipo, em in b["acoes"]:
            if tipo.startswith("expressao:"):
                acoes.append({"personagem": ids[who], "tipo": "expressao", "expressao": tipo.split(":")[1], "em": em})
            else:
                acoes.append({"personagem": ids[who], "tipo": tipo, "em": em})
        sc = {
            "numero": i + 1,
            "cenario": cenario if (cenario and b["cenario"] != "entardecer") else b["cenario"],
            "plano": b["plano"],
            "movimento": b["movimento"],
            "emocao_musical": b["emocao"],
            "narracao": _fix_gender(_fill(b["narracao"], P, A), P),
            "falas": falas,
            "acoes": acoes,
            "efeitos": b.get("efeitos", []),
            "personagens": [ids["P"]] if b.get("so_P") else [ids["P"], ids["A"]],
        }
        if b.get("foco"):
            sc["foco"] = ids[b["foco"]]
        if m.get("objeto") and (b.get("objeto_pos") or b.get("entrega") or b.get("entrega_inversa")):
            sc["objeto"] = {"tipo": m["objeto"], "posicao": b.get("objeto_pos", "P_frente"),
                            "entrega": "P->A" if b.get("entrega") else ("A->P" if b.get("entrega_inversa") else None)}
        scenes.append(sc)
    titulo = _fill(m["titulo"], P, A)
    story = {
        "titulo": titulo,
        "tema": tema,
        "modelo": key,
        "categoria": m["categoria"],
        "categoria_nome": CATEGORIAS[m["categoria"]],
        "valor": m["valor"],
        "faixa_etaria": faixa,
        "duracao_alvo": duracao,
        "moral": m["moral"],
        "gancho": scenes[0]["narracao"],
        "personagens": [P["id"], A["id"]],
        "cenas": scenes,
        "motor": "local (modelos narrativos do estúdio, gratuito)",
    }
    return story


# ---------------------------------------------------------------------------
# Motor opcional: Claude (API paga). So e chamado com autorizacao explicita.
# ---------------------------------------------------------------------------
STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "moral": {"type": "string"},
        "cenas": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "cenario": {"type": "string", "enum": ["savana", "floresta", "campo", "entardecer"]},
                "plano": {"type": "string", "enum": ["geral", "medio", "close", "dois"]},
                "movimento": {"type": "string", "enum": ["parado", "aproximar", "afastar", "panoramica", "lateral", "grua"]},
                "emocao_musical": {"type": "string", "enum": ["aventura", "alegria", "ternura", "suspense", "celebracao"]},
                "narracao": {"type": "string"},
                "falas": {"type": "array", "items": {"type": "object", "properties": {
                    "quem": {"type": "string", "enum": ["P", "A"]},
                    "texto": {"type": "string"},
                    "emocao": {"type": "string", "enum": ["neutro", "feliz", "triste", "surpreso", "pensativo", "bravo"]}},
                    "required": ["quem", "texto", "emocao"], "additionalProperties": False}},
                "acoes": {"type": "array", "items": {"type": "object", "properties": {
                    "quem": {"type": "string", "enum": ["P", "A"]},
                    "tipo": {"type": "string", "enum": ["andar", "pular", "comemorar", "acenar", "oferecer", "segurar", "acenar_cabeca"]},
                    "em": {"type": "string"}},
                    "required": ["quem", "tipo", "em"], "additionalProperties": False}},
            },
            "required": ["cenario", "plano", "movimento", "emocao_musical", "narracao", "falas", "acoes"],
            "additionalProperties": False}},
    },
    "required": ["titulo", "moral", "cenas"],
    "additionalProperties": False,
}


def write_story_claude(tema, duracao, faixa, categoria, cfg):
    """Gera a historia com o Claude. Requer `pip install anthropic` e chave."""
    import anthropic  # dependencia opcional

    base = write_story_local(tema, duracao, faixa, categoria)  # define personagens
    P, A = ad.load_character(base["personagens"][0]), ad.load_character(base["personagens"][1])
    n = max(3, min(7, round(duracao / 9)))
    prompt = (
        f"Escreva uma historia infantil ORIGINAL em portugues do Brasil para criancas de {FAIXAS.get(faixa, faixa)}, "
        f"tema: '{tema}'. Protagonista P = {P['nome']} ({P['especie_nome']}, {P['personalidade']}). "
        f"Amigo(a) A = {A['nome']} ({A['especie_nome']}, {A['personalidade']}). "
        f"Exatamente {n} cenas, video total de cerca de {duracao} segundos: narracao de no maximo 18 palavras por cena e "
        "no maximo 2 falas curtas (ate 8 palavras) por cena. Comece com um gancho de curiosidade, desenvolva um "
        "pequeno conflito e termine com uma licao clara e positiva. Nada assustador, violento ou com marcas/"
        "personagens de terceiros. Em 'acoes', 'em' deve ser 'inicio', 'narracao', 'fala0', 'fala1' ou 'fim'."
    )
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=cfg.get("claude_modelo", "claude-opus-5-5"),
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": STORY_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("O Claude recusou o pedido; usando o roteirista local.")
    text = "".join(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    ids = {"P": P["id"], "A": A["id"]}
    scenes = []
    for i, c in enumerate(data["cenas"]):
        scenes.append({
            "numero": i + 1, "cenario": c["cenario"], "plano": c["plano"], "movimento": c["movimento"],
            "emocao_musical": c["emocao_musical"], "narracao": c["narracao"],
            "falas": [{"personagem": ids[f["quem"]], "texto": f["texto"], "emocao": f["emocao"]} for f in c["falas"][:2]],
            "acoes": [{"personagem": ids[a["quem"]], "tipo": a["tipo"], "em": a["em"]} for a in c["acoes"]],
            "efeitos": ["brilho"] if i == len(data["cenas"]) - 1 else [],
            "personagens": [P["id"], A["id"]],
        })
    base.update({"titulo": data["titulo"], "moral": data["moral"], "cenas": scenes, "gancho": scenes[0]["narracao"],
                 "motor": f"Claude ({cfg.get('claude_modelo')}) via API da Anthropic - uso pago"})
    return base


def write_story(tema, duracao=30, faixa="4-6", categoria=None, cfg=None, cenario=None):
    cfg = cfg or {}
    if cfg.get("roteirista") == "claude":
        if not cfg.get("permitir_servicos_pagos"):
            raise PermissionError("Roteirista Claude e pago: ative 'permitir_servicos_pagos' nas configuracoes.")
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            raise PermissionError("Defina ANTHROPIC_API_KEY para usar o roteirista Claude.")
        return write_story_claude(tema, duracao, faixa, categoria, cfg)
    return write_story_local(tema, duracao, faixa, categoria, cenario)


def script_markdown(story, chars):
    names = {c["id"]: c["nome"] for c in chars}
    L = [f"# {story['titulo']}", "", f"**Tema:** {story['tema']}  ", f"**Categoria:** {story['categoria_nome']}  ",
         f"**Valor ensinado:** {story['valor']}  ", f"**Faixa etária:** {FAIXAS.get(story['faixa_etaria'], story['faixa_etaria'])}  ",
         f"**Gancho inicial:** {story['gancho']}  ", f"**Moral:** {story['moral']}  ", f"**Roteirista:** {story['motor']}", ""]
    for sc in story["cenas"]:
        L += [f"## Cena {sc['numero']} — {sc['cenario']} ({sc['plano']}, câmera: {sc['movimento']}, música: {sc['emocao_musical']})",
              "", f"**NARRADOR:** {sc['narracao']}", ""]
        for f in sc["falas"]:
            L.append(f"**{names.get(f['personagem'], f['personagem']).upper()}** _({f['emocao']})_: {f['texto']}  ")
        if sc["acoes"]:
            L += ["", "_Ações:_ " + "; ".join(f"{names.get(a['personagem'])} {a['tipo']}"
                                               + (f" ({a['expressao']})" if a.get('expressao') else "") + f" [{a['em']}]"
                                               for a in sc["acoes"])]
        if sc.get("efeitos"):
            L.append(f"_Efeitos sonoros:_ {', '.join(sc['efeitos'])}")
        L.append("")
    return "\n".join(L)
