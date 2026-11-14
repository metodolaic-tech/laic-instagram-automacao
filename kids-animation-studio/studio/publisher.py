"""Modulo G - Publicacao e monetizacao (preparo, NUNCA publica sozinho).

Gera: titulos, descricao, hashtags, tags, miniatura (capa) com texto,
legenda .srt, checklist de politicas (conteudo infantil, direitos autorais,
conteudo sintetico/IA, originalidade) para YouTube, Facebook, Instagram e TikTok.

Importante:
  * Este modulo nao envia nada para nenhuma plataforma. A publicacao e feita
    por voce, manualmente, depois de assistir e aprovar o video.
  * Nao ha promessa de ganhos nem de aprovacao em programas de monetizacao:
    cada plataforma decide com base nas proprias regras, que mudam com o tempo.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

VALOR_HASHTAG = {
    "compartilhar": "#compartilhar", "amizade": "#amizade", "coragem": "#coragem", "honestidade": "#honestidade",
    "paciência": "#paciencia", "gratidão": "#gratidao",
}


def titles(story, chars):
    p = chars[0]["nome"]
    t = story["titulo"]
    return [
        f"{t} | Desenho Animado Infantil 3D",
        f"{t} 🦁✨ Historinha com Lição para Crianças",
        f"{p} e uma lição sobre {story['valor']} | Animação Infantil",
    ]


def description(story, chars, credits):
    names = ", ".join(f"{c['nome']} ({c['especie_nome']})" for c in chars)
    tags = ["#desenhoinfantil", "#historinhainfantil", "#animacao3d", "#criancas", "#licaodevida"]
    tags.insert(0, VALOR_HASHTAG.get(story["valor"], "#valores"))
    lines = [
        f"{story['titulo']} — uma historinha animada sobre {story['valor']}!",
        "",
        story["gancho"],
        "",
        f"✨ Lição: {story['moral']}",
        "",
        f"Personagens: {names}.",
        "",
        "Pergunta para conversar com a criança depois do vídeo:",
        f"👉 Você já viveu uma situação parecida? O que você faria no lugar de {chars[0]['nome']}?",
        "",
        "Animação original criada com Blender (3D), vozes sintetizadas e trilha original.",
    ]
    if credits:
        lines += ["", "Créditos e licenças:"] + [f"- {c}" for c in credits]
    lines += ["", " ".join(tags)]
    return "\n".join(lines), tags


def policy_checklist():
    return [
        "[ ] Assisti ao vídeo inteiro e aprovo o conteúdo (linguagem, imagens e mensagem adequadas à idade).",
        "[ ] YouTube: marcar como 'Conteúdo feito para crianças' (exigência legal/COPPA). Isso desativa comentários e "
        "anúncios personalizados e muda a forma de monetização.",
        "[ ] YouTube: avaliar o rótulo de 'conteúdo alterado ou sintético' quando a IA gerar algo que pareça real "
        "(vozes realistas imitando pessoas reais, por exemplo). Animações claramente fictícias normalmente não exigem, "
        "mas confira a regra atual na Central de Ajuda.",
        "[ ] Originalidade: personagens, roteiro e trilha são originais; nenhum personagem, marca ou música de terceiros.",
        "[ ] Músicas/efeitos de biblioteca externa: licença com uso comercial registrada em licencas.json e crédito na descrição.",
        "[ ] Voz: Piper (vozes pt-BR CC0/CC BY) ou ElevenLabs conforme o plano da sua conta, que precisa permitir uso comercial.",
        "[ ] Monetização: canais com conteúdo repetitivo ou produzido em massa podem ser recusados nos programas de "
        "parceria. Varie histórias, roteiros e personagens; agregue valor educativo real.",
        "[ ] Instagram/Facebook/TikTok: conteúdo infantil não pode ser direcionado com dados de menores; siga as regras "
        "de cada plataforma e use o selo de conteúdo gerado por IA quando a plataforma pedir.",
        "[ ] Nunca prometa ganhos aos alunos: aprovação e receita dependem de cada plataforma.",
    ]


def make_thumbnail(base_png, title, out_png, font_path=None):
    img = Image.open(base_png).convert("RGB").resize((1280, 720), Image.LANCZOS)
    # leve vinheta para destacar o texto
    shade = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(shade)
    d.rectangle([0, 520, 1280, 720], fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(60))
    img = Image.composite(Image.new("RGB", img.size, (30, 20, 10)), img, shade)
    draw = ImageDraw.Draw(img)
    size = 84
    font = None
    while size > 40:
        try:
            font = ImageFont.truetype(str(font_path), size) if font_path else ImageFont.load_default()
        except OSError:
            font = ImageFont.load_default()
            break
        if draw.textlength(title, font=font) < 1180:
            break
        size -= 4
    tw = draw.textlength(title, font=font)
    x, y = (1280 - tw) / 2, 590
    draw.text((x, y), title, font=font, fill=(255, 230, 80), stroke_width=8, stroke_fill=(70, 35, 10))
    img.save(out_png, quality=92)
    # versao vertical (capa de Reels/Shorts/TikTok)
    v = Image.open(base_png).convert("RGB")
    W, H = 720, 1280
    bg = v.resize((int(v.width * H / v.height), H)).filter(ImageFilter.GaussianBlur(25))
    left = (bg.width - W) // 2
    bg = bg.crop((left, 0, left + W, H))
    fg = v.resize((W, int(v.height * W / v.width)))
    bg.paste(fg, (0, (H - fg.height) // 2))
    dv = ImageDraw.Draw(bg)
    fsize = 60
    words, lines, cur = title.split(), [], ""
    for w in words:
        if len(cur) + len(w) > 16 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    try:
        f2 = ImageFont.truetype(str(font_path), fsize) if font_path else ImageFont.load_default()
    except OSError:
        f2 = ImageFont.load_default()
    for i, ln in enumerate(lines):
        tw = dv.textlength(ln, font=f2)
        dv.text(((W - tw) / 2, 150 + i * (fsize + 12)), ln, font=f2, fill=(255, 230, 80), stroke_width=7,
                stroke_fill=(70, 35, 10))
    out_v = Path(out_png).with_name(Path(out_png).stem + "_vertical.jpg")
    bg.save(out_v, quality=92)
    return out_png, out_v


def build_package(story, chars, credits, out_dir):
    desc, tags = description(story, chars, credits)
    meta = {
        "titulos_sugeridos": titles(story, chars),
        "descricao": desc,
        "hashtags": tags,
        "tags": [story["valor"], "desenho infantil", "animação 3d", "historinha", "lição de moral"]
                + [c["especie_nome"] for c in chars],
        "idioma": "pt-BR",
        "publico": "Feito para crianças (marcar na plataforma)",
        "faixa_etaria": story["faixa_etaria"],
        "categoria_youtube": "Filmes e desenhos / Educação",
        "checklist_politicas": policy_checklist(),
        "status_publicacao": "NAO PUBLICADO - aguardando revisao e publicacao manual pelo usuario",
    }
    Path(out_dir, "metadados.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# Pacote de publicação — {story['titulo']}", "", "## Títulos sugeridos"]
    md += [f"{i}. {t}" for i, t in enumerate(meta["titulos_sugeridos"], 1)]
    md += ["", "## Descrição", "```", desc, "```", "", "## Arquivos", "- `video_16x9.mp4` — YouTube / Facebook",
           "- `video_9x16.mp4` — Reels / Shorts / TikTok", "- `capa.jpg` e `capa_vertical.jpg` — miniaturas",
           "- `legendas.srt` — enviar como legenda (acessibilidade)", "", "## Checklist antes de publicar"]
    md += meta["checklist_politicas"]
    md += ["", "> O estúdio **não publica** nada automaticamente. Revise, aprove e publique manualmente."]
    Path(out_dir, "PUBLICACAO.md").write_text("\n".join(md), encoding="utf-8")
    return meta
