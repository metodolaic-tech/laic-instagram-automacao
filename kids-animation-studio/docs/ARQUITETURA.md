# Arquitetura

```
             tema ──► [A Roteirista] ──► historia.json ──(aprovação)──►
                                                            │
       library/characters ◄──► [B Diretor de Arte] ──► fichas + folha de modelo 3D ──(aprovação)──►
                                                            │
                         [D Voz] ── falas.wav ──► [linha do tempo] ◄── durações reais das falas
                                                            │  instantes de falas, ações, efeitos, câmera
                 ┌──────────────────────────────────────────┼───────────────────────┐
                 ▼                                          ▼                       ▼
        [E Música] plano musical               [C Animador / Blender]       envelopes de volume
                 │                               quadros PNG por cena  ◄── (sincronia labial)
                 ▼                                          │
        [F Editor / FFmpeg] ◄───────────────────────────────┘
          crossfades · mixagem com ducking · legendas · 16:9 + 9:16 · prévia
                 │
                 ▼
        [G Publicação] títulos, descrição, capas, checklist  ──► você revisa e publica
                 │
                 ▼
          RELATORIO.md (ferramentas, licenças, custos)   AULA.md (Modo Ensino)
```

## Decisões principais

* **Um único formato de roteiro (`historia.json`)** liga todos os módulos. Trocar o roteirista
  (local ↔ Claude) não muda nada nas etapas seguintes.
* **A voz manda no tempo.** As cenas são dimensionadas pela duração real dos áudios; a animação,
  as legendas e os efeitos usam os mesmos instantes (`roteiro/linha_do_tempo.json`). É isso que
  mantém tudo sincronizado.
* **Blender em processo separado por cena.** Se uma cena falhar, as outras ficam salvas; o render
  retoma do último quadro. Funciona com o programa Blender (`blender -b -P`) ou com o módulo `bpy`.
* **Personagens procedurais com rig hierárquico.** Cada parte do corpo é um objeto 3D preso a um
  pivô (articulação). Isso permite animar por código de forma confiável e reproduzível, sem
  depender de modelos de terceiros.
* **Estado em disco (`projeto.json`).** Etapas: `pendente → executando → aguardando_aprovacao →
  concluida` (ou `erro`). O painel e a linha de comando leem o mesmo arquivo.
* **Painel sem dependências.** `http.server` da biblioteca padrão, escutando só em `127.0.0.1`.
* **Travas de custo e publicação.** Serviços pagos exigem chave + autorização; publicação é sempre manual.

## Pastas de um projeto

```
projetos/<data>_<tema>/
  projeto.json                 estado, parâmetros, tempos
  log.txt                      registro legível
  AULA.md                      explicação passo a passo (Modo Ensino)
  RELATORIO.md / relatorio.json
  roteiro/historia.json, roteiro.md, linha_do_tempo.json
  personagens/<id>.md, <id>.png
  audio/vozes/*.wav, importar/, mixagem.wav, trilha_*.wav, fontes_*.json, efeitos.json, plano_musical.json
  cenas/cenaNN/cena.json, quadros/*.png, estado.json ; cenas/cenaNN.mp4
  final/video_16x9.mp4, video_9x16.mp4, previa.mp4, legendas.srt, capa*.jpg, PUBLICACAO.md, metadados.json
```

## Como estender

| Quero... | Onde |
|---|---|
| Nova espécie | `ESPECIES` em `studio/art_director.py` (orelhas, cauda, extras, paletas) |
| Novo cenário | um JSON em `library/sets/` (cores, céu, sol, elementos) |
| Novo tipo de elemento de cenário | `add_element` em `studio/blender/scene_builder.py` |
| Nova ação de personagem | método em `Character` + mapeamento em `run()` (scene_builder) + `timeline.py` |
| Novo modelo de história | `MODELOS` e `TEMAS` em `studio/writer.py` |
| Nova emoção musical | `STYLE` em `studio/music.py` |
