# 🎬 Kids Animation Studio AI

Produtora automatizada de **vídeos infantis em animação 3D**: você digita um tema e o estúdio
escreve a história, cria personagens 3D originais, gera as vozes em português, compõe a trilha,
anima no **Blender**, edita no **FFmpeg** e prepara o pacote de publicação. Tudo isso com
**ferramentas gratuitas e de código aberto**.

> "Crie uma animação infantil de 25 segundos sobre um leãozinho que aprende a compartilhar."
> → `video_16x9.mp4`, `video_9x16.mp4`, capas, legendas, descrição, checklist e relatório de licenças.

## O que já funciona (protótipo verificado)

| Etapa | Módulo | Ferramenta | Custo |
|---|---|---|---|
| História com gancho, conflito e lição | A · Roteirista | Modelos narrativos locais (opcional: Claude) | R$ 0 |
| Fichas de personagem e folha de modelo 3D | B · Diretor de Arte | Python + Blender | R$ 0 |
| Cenários, personagens, movimento, câmera, luz e render 3D | C · Animador | Blender 5 (Cycles), script Python | R$ 0 |
| Narração e vozes dos personagens em pt-BR | D · Voz | Piper TTS local (opcional: ElevenLabs/Bianca, gravações próprias) | R$ 0 |
| Trilha original por emoção e efeitos sonoros | E · Música | Compositor procedural em Python | R$ 0 |
| Montagem, transições, mixagem com ducking, legendas, 16:9 e 9:16 | F · Editor | FFmpeg | R$ 0 |
| Títulos, descrição, hashtags, capas, checklist de políticas | G · Publicação | Python + Pillow | R$ 0 |

**Animação 3D de verdade:** os personagens são modelos 3D com articulações (quadril, cabeça,
braços, pernas, cauda, olhos, sobrancelhas, boca) animadas por keyframes: andar, pular, acenar,
comemorar, entregar objetos, piscar, respirar, expressões faciais e **boca sincronizada com o volume
da fala**. A câmera faz travelling, panorâmica, grua e aproximação, com profundidade de campo.

## Início rápido

```bash
pip install -r requirements.txt          # numpy, pillow, piper-tts
python kas.py baixar-vozes               # vozes pt-BR gratuitas (Piper)
python kas.py diagnostico                # confere Blender, FFmpeg, vozes
python kas.py painel                     # abre http://localhost:8765
```

Ou direto pela linha de comando:

```bash
python kas.py novo "Um leãozinho que aprende a compartilhar" --duracao 25          # para no roteiro p/ aprovação
python kas.py aprovar <projeto> roteiro
python kas.py produzir <projeto>                                                    # para nos personagens
python kas.py aprovar <projeto> personagens
python kas.py produzir <projeto>                                                    # render, edição, publicação
# ou tudo de uma vez:  python kas.py novo "..." --duracao 25 --auto
```

Windows: siga [docs/INSTALACAO_WINDOWS.md](docs/INSTALACAO_WINDOWS.md) (ou use `instalar_windows.bat`
e `iniciar_painel.bat`).

## Estrutura

```
kas.py                       linha de comando
studio/
  writer.py                  Módulo A – Roteirista
  art_director.py            Módulo B – Diretor de Arte (fichas, espécies, paletas, prompts)
  blender/scene_builder.py   Módulo C – Animador 3D (roda dentro do Blender)
  voice.py                   Módulo D – Voz (Piper, ElevenLabs, importação)
  music.py                   Módulo E – Música e efeitos
  editor.py                  Módulo F – Editor (FFmpeg)
  publisher.py               Módulo G – Publicação (nunca publica sozinho)
  timeline.py                sincronia: falas ↔ ações ↔ legendas ↔ som
  pipeline.py                orquestrador com retomada e aprovações
  teaching.py                Modo Ensino
  diagnose.py                Fase 1 – diagnóstico do ambiente
  web/                       painel local (somente biblioteca padrão do Python)
library/                     personagens, cenários, músicas e efeitos reutilizáveis
projetos/<id>/               tudo de cada vídeo (roteiro, áudio, cenas, final, relatório, aula)
docs/                        instalação, ensino, licenças, arquitetura, limitações
tests/                       testes automatizados
```

## Segurança financeira e de publicação

* **Nada pago roda sem autorização:** ElevenLabs e Claude só funcionam com chave em variável de
  ambiente **e** com `permitir_servicos_pagos = true` no painel. Desligado por padrão.
* **Nada é publicado automaticamente.** O estúdio gera o pacote; você revisa e publica.
* Não há promessa de ganhos nem de aprovação em programas de monetização.

## Documentação

* [Instalação no Windows](docs/INSTALACAO_WINDOWS.md)
* [Modo Ensino e roteiro de aula](docs/MODO_ENSINO.md)
* [Ferramentas, custos e licenças (análise "gratuito primeiro")](docs/FERRAMENTAS_E_LICENCAS.md)
* [Arquitetura](docs/ARQUITETURA.md)
* [Limitações e próximos passos](docs/LIMITACOES_E_ROADMAP.md)
* [Diagnóstico e evidências do protótipo](docs/DIAGNOSTICO_E_EVIDENCIAS.md) · vídeo de exemplo em [exemplos/tito_aprende_a_compartilhar](exemplos/tito_aprende_a_compartilhar)

## Testes

```bash
python -m unittest discover -s tests -v
```
