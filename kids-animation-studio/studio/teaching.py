"""Modo Ensino: explica cada etapa em linguagem simples, para uso em aula.

Para cada etapa: o que acontece, ferramenta usada, por que foi escolhida,
custo, arquivos gerados e como o aluno pode reproduzir.
"""

ETAPAS = {
    "roteiro": {
        "titulo": "1. Roteiro (Módulo A - Roteirista)",
        "o_que": "Transformamos o tema em uma história curta com começo (gancho de curiosidade), meio (um pequeno "
                 "problema) e fim (a lição). Cada cena já sai com narração, falas, ações, câmera e clima musical.",
        "ferramenta": "Roteirista local do estúdio (modelos narrativos em Python). Opcional: Claude via API.",
        "por_que": "Funciona offline e de graça, e garante histórias adequadas para crianças e no tamanho certo para "
                   "redes sociais.",
        "custo": "R$ 0 no modo local. O modo Claude cobra por uso (só roda se você autorizar).",
        "arquivos": ["roteiro/historia.json", "roteiro/roteiro.md"],
        "reproduzir": "Abra roteiro.md, leia em voz alta e veja se uma criança entenderia. Edite o texto no painel "
                      "antes de aprovar.",
    },
    "personagens": {
        "titulo": "2. Personagens (Módulo B - Diretor de Arte)",
        "o_que": "Cada personagem tem uma ficha fixa (cores, proporções, acessório, voz). A ficha é reutilizada em "
                 "todos os episódios, garantindo que o personagem seja sempre o mesmo.",
        "ferramenta": "Fichas JSON + renderização 3D no Blender (folha de modelo).",
        "por_que": "Consistência visual é o que faz o público reconhecer e gostar dos personagens.",
        "custo": "R$ 0 (Blender é software livre, licença GPL).",
        "arquivos": ["personagens/<id>.md", "personagens/<id>.png", "library/characters/<id>.json"],
        "reproduzir": "Abra a ficha em library/characters, mude uma cor e gere de novo para ver o efeito.",
    },
    "voz": {
        "titulo": "3. Vozes (Módulo D - Voz e Narração)",
        "o_que": "Geramos um áudio para cada fala. O narrador e cada personagem têm uma voz própria; o tom infantil é "
                 "criado subindo a altura (pitch) sem acelerar a fala.",
        "ferramenta": "Piper TTS (local) com vozes pt-BR. Opcional: ElevenLabs (voz Bianca) ou suas gravações.",
        "por_que": "Piper roda no próprio computador, sem internet e sem custo, com qualidade boa em português.",
        "custo": "R$ 0 com Piper ou gravações próprias. ElevenLabs consome créditos do seu plano.",
        "arquivos": ["audio/vozes/*.wav", "audio/importar/ (coloque aqui suas gravações)"],
        "reproduzir": "Grave sua própria voz no celular, salve como cena01_narracao.wav na pasta importar e rode de "
                      "novo a etapa de voz.",
    },
    "musica": {
        "titulo": "4. Música e efeitos (Módulo E)",
        "o_que": "Compomos uma trilha original no clima de cada parte da história e criamos efeitos (pulo, brilho, "
                 "passos, passarinhos). Tudo é registrado com origem e licença.",
        "ferramenta": "Compositor procedural em Python (numpy) ou faixas da sua biblioteca com licença registrada.",
        "por_que": "Música de terceiros sem licença derruba vídeos e monetização. Trilha própria elimina esse risco.",
        "custo": "R$ 0.",
        "arquivos": ["audio/musica_*.wav", "library/music/licencas.json"],
        "reproduzir": "Baixe uma faixa da YouTube Audio Library, registre em licencas.json com a emoção e "
                      "permite_comercial=true, e o estúdio passa a usá-la.",
    },
    "animacao": {
        "titulo": "5. Animação 3D (Módulo C - Animador)",
        "o_que": "O Blender monta o cenário, constrói os personagens em 3D, anima articulações (andar, pular, acenar, "
                 "piscar, falar com a boca sincronizada ao áudio), move a câmera e renderiza quadro a quadro.",
        "ferramenta": "Blender 5 (motor Cycles) controlado por script Python.",
        "por_que": "É animação 3D de verdade, gratuita e reproduzível, sem depender de serviços online.",
        "custo": "R$ 0. Custo de tempo: o render usa o processador e pode levar minutos.",
        "arquivos": ["cenas/cenaNN/quadros/*.png", "cenas/cenaNN/cena.json", "cenas/cenaNN.mp4"],
        "reproduzir": "Abra cena.json, troque o 'movimento' da câmera para 'panoramica' e renderize só essa cena.",
    },
    "edicao": {
        "titulo": "6. Edição (Módulo F - Editor)",
        "o_que": "Juntamos as cenas com transições, colocamos vozes, efeitos e música (que abaixa sozinha quando "
                 "alguém fala), adicionamos legendas e exportamos nas versões 16:9 e 9:16.",
        "ferramenta": "FFmpeg (software livre) + Python.",
        "por_que": "FFmpeg é o padrão da indústria para vídeo, gratuito e automatizável.",
        "custo": "R$ 0.",
        "arquivos": ["final/video_16x9.mp4", "final/video_9x16.mp4", "final/previa.mp4", "final/legendas.srt"],
        "reproduzir": "Assista à prévia, anote correções e use 'refazer etapa' no painel.",
    },
    "publicacao": {
        "titulo": "7. Publicação (Módulo G)",
        "o_que": "Preparamos títulos, descrição, hashtags, capas e um checklist de políticas. O estúdio NÃO publica: "
                 "você revisa e publica manualmente.",
        "ferramenta": "Python + Pillow (capas).",
        "por_que": "Publicar exige decisão humana: conteúdo infantil tem regras específicas em cada plataforma.",
        "custo": "R$ 0.",
        "arquivos": ["final/PUBLICACAO.md", "final/metadados.json", "final/capa.jpg", "final/capa_vertical.jpg"],
        "reproduzir": "Leia o checklist com os alunos e discuta por que cada item existe.",
    },
    "relatorio": {
        "titulo": "8. Relatório",
        "o_que": "Registramos ferramentas, versões, licenças, custos, tempos e arquivos gerados.",
        "ferramenta": "Python.",
        "por_que": "Transparência: você sabe exatamente o que foi usado e pode provar a origem de tudo.",
        "custo": "R$ 0.",
        "arquivos": ["RELATORIO.md", "relatorio.json"],
        "reproduzir": "Compare os tempos de render entre a qualidade 'rascunho' e 'padrao'.",
    },
}


def explain(etapa):
    e = ETAPAS.get(etapa)
    if not e:
        return ""
    return "\n".join([
        f"## {e['titulo']}", "",
        f"**O que está acontecendo:** {e['o_que']}", "",
        f"**Ferramenta:** {e['ferramenta']}", "",
        f"**Por que esta ferramenta:** {e['por_que']}", "",
        f"**Custo:** {e['custo']}", "",
        "**Arquivos gerados:** " + ", ".join(f"`{a}`" for a in e["arquivos"]), "",
        f"**Para o aluno reproduzir:** {e['reproduzir']}", "",
    ])
