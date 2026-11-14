# Aula: como este vídeo foi produzido

Projeto: **Crie uma animação infantil de 25 segundos sobre um leãozinho que aprende a compartilhar**

## 1. Roteiro (Módulo A - Roteirista)

**O que está acontecendo:** Transformamos o tema em uma história curta com começo (gancho de curiosidade), meio (um pequeno problema) e fim (a lição). Cada cena já sai com narração, falas, ações, câmera e clima musical.

**Ferramenta:** Roteirista local do estúdio (modelos narrativos em Python). Opcional: Claude via API.

**Por que esta ferramenta:** Funciona offline e de graça, e garante histórias adequadas para crianças e no tamanho certo para redes sociais.

**Custo:** R$ 0 no modo local. O modo Claude cobra por uso (só roda se você autorizar).

**Arquivos gerados:** `roteiro/historia.json`, `roteiro/roteiro.md`

**Para o aluno reproduzir:** Abra roteiro.md, leia em voz alta e veja se uma criança entenderia. Edite o texto no painel antes de aprovar.

## 2. Personagens (Módulo B - Diretor de Arte)

**O que está acontecendo:** Cada personagem tem uma ficha fixa (cores, proporções, acessório, voz). A ficha é reutilizada em todos os episódios, garantindo que o personagem seja sempre o mesmo.

**Ferramenta:** Fichas JSON + renderização 3D no Blender (folha de modelo).

**Por que esta ferramenta:** Consistência visual é o que faz o público reconhecer e gostar dos personagens.

**Custo:** R$ 0 (Blender é software livre, licença GPL).

**Arquivos gerados:** `personagens/<id>.md`, `personagens/<id>.png`, `library/characters/<id>.json`

**Para o aluno reproduzir:** Abra a ficha em library/characters, mude uma cor e gere de novo para ver o efeito.

## 3. Vozes (Módulo D - Voz e Narração)

**O que está acontecendo:** Geramos um áudio para cada fala. O narrador e cada personagem têm uma voz própria; o tom infantil é criado subindo a altura (pitch) sem acelerar a fala.

**Ferramenta:** Piper TTS (local) com vozes pt-BR. Opcional: ElevenLabs (voz Bianca) ou suas gravações.

**Por que esta ferramenta:** Piper roda no próprio computador, sem internet e sem custo, com qualidade boa em português.

**Custo:** R$ 0 com Piper ou gravações próprias. ElevenLabs consome créditos do seu plano.

**Arquivos gerados:** `audio/vozes/*.wav`, `audio/importar/ (coloque aqui suas gravações)`

**Para o aluno reproduzir:** Grave sua própria voz no celular, salve como cena01_narracao.wav na pasta importar e rode de novo a etapa de voz.

## 4. Música e efeitos (Módulo E)

**O que está acontecendo:** Compomos uma trilha original no clima de cada parte da história e criamos efeitos (pulo, brilho, passos, passarinhos). Tudo é registrado com origem e licença.

**Ferramenta:** Compositor procedural em Python (numpy) ou faixas da sua biblioteca com licença registrada.

**Por que esta ferramenta:** Música de terceiros sem licença derruba vídeos e monetização. Trilha própria elimina esse risco.

**Custo:** R$ 0.

**Arquivos gerados:** `audio/musica_*.wav`, `library/music/licencas.json`

**Para o aluno reproduzir:** Baixe uma faixa da YouTube Audio Library, registre em licencas.json com a emoção e permite_comercial=true, e o estúdio passa a usá-la.

## 5. Animação 3D (Módulo C - Animador)

**O que está acontecendo:** O Blender monta o cenário, constrói os personagens em 3D, anima articulações (andar, pular, acenar, piscar, falar com a boca sincronizada ao áudio), move a câmera e renderiza quadro a quadro.

**Ferramenta:** Blender 5 (motor Cycles) controlado por script Python.

**Por que esta ferramenta:** É animação 3D de verdade, gratuita e reproduzível, sem depender de serviços online.

**Custo:** R$ 0. Custo de tempo: o render usa o processador e pode levar minutos.

**Arquivos gerados:** `cenas/cenaNN/quadros/*.png`, `cenas/cenaNN/cena.json`, `cenas/cenaNN.mp4`

**Para o aluno reproduzir:** Abra cena.json, troque o 'movimento' da câmera para 'panoramica' e renderize só essa cena.

## 6. Edição (Módulo F - Editor)

**O que está acontecendo:** Juntamos as cenas com transições, colocamos vozes, efeitos e música (que abaixa sozinha quando alguém fala), adicionamos legendas e exportamos nas versões 16:9 e 9:16.

**Ferramenta:** FFmpeg (software livre) + Python.

**Por que esta ferramenta:** FFmpeg é o padrão da indústria para vídeo, gratuito e automatizável.

**Custo:** R$ 0.

**Arquivos gerados:** `final/video_16x9.mp4`, `final/video_9x16.mp4`, `final/previa.mp4`, `final/legendas.srt`

**Para o aluno reproduzir:** Assista à prévia, anote correções e use 'refazer etapa' no painel.

## 7. Publicação (Módulo G)

**O que está acontecendo:** Preparamos títulos, descrição, hashtags, capas e um checklist de políticas. O estúdio NÃO publica: você revisa e publica manualmente.

**Ferramenta:** Python + Pillow (capas).

**Por que esta ferramenta:** Publicar exige decisão humana: conteúdo infantil tem regras específicas em cada plataforma.

**Custo:** R$ 0.

**Arquivos gerados:** `final/PUBLICACAO.md`, `final/metadados.json`, `final/capa.jpg`, `final/capa_vertical.jpg`

**Para o aluno reproduzir:** Leia o checklist com os alunos e discuta por que cada item existe.

## 8. Relatório

**O que está acontecendo:** Registramos ferramentas, versões, licenças, custos, tempos e arquivos gerados.

**Ferramenta:** Python.

**Por que esta ferramenta:** Transparência: você sabe exatamente o que foi usado e pode provar a origem de tudo.

**Custo:** R$ 0.

**Arquivos gerados:** `RELATORIO.md`, `relatorio.json`

**Para o aluno reproduzir:** Compare os tempos de render entre a qualidade 'rascunho' e 'padrao'.

