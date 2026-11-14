# Modo Ensino: como usar o estúdio em aula

O Modo Ensino vem **ligado por padrão**. A cada etapa o estúdio:

* mostra no painel um quadro "📚 Modo Ensino" com **o que está acontecendo, a ferramenta, por que
  ela foi escolhida, o custo, os arquivos gerados e como o aluno pode reproduzir**;
* escreve tudo em `projetos/<projeto>/AULA.md`, que vira a apostila daquela produção;
* registra em `log.txt` cada passo em português simples.

## Roteiro de demonstração (aula de ~50 minutos)

| Tempo | Atividade | O que mostrar |
|---|---|---|
| 0–5 min | Abertura | Um vídeo pronto (`final/video_9x16.mp4`) e a pergunta: "quanto custou?" → Relatório: R$ 0 |
| 5–10 min | Diagnóstico | `python kas.py diagnostico`: o que é cada ferramenta, por que é gratuita, o que é licença |
| 10–15 min | Roteiro | Criar projeto no painel com um tema sugerido pela turma; ler o roteiro em voz alta; editar uma fala; aprovar |
| 15–20 min | Personagens | Folha de modelo 3D; conversar sobre **consistência** e **originalidade** (por que não copiar personagens famosos) |
| 20–30 min | Vozes e música | Ouvir `audio/vozes/*.wav`; explicar pitch; mostrar `licencas.json` e por que música sem licença derruba vídeos |
| 30–40 min | Render 3D | Barra de progresso; abrir `cenas/cena01/cena.json`; mostrar um quadro PNG; explicar keyframes (andar, pular, piscar) |
| 40–47 min | Edição e publicação | Ducking (música abaixa na fala), legendas, 16:9 × 9:16, `PUBLICACAO.md` e o checklist |
| 47–50 min | Fechamento | Monetização: regras de conteúdo infantil, conteúdo repetitivo, **nenhuma promessa de ganhos** |

Dica: para a aula não depender do tempo de render, rode a produção antes (qualidade "rascunho")
e, ao vivo, crie um projeto novo só até a etapa de personagens. Para um render rápido ao vivo, use
`--qualidade teste` (320×180, cerca de 3 minutos).

## Exercícios para os alunos

1. **Troque a cor de um personagem:** edite `library/characters/tito_leao.json` (campo `cores.pelo`),
   rode um novo projeto e compare as folhas de modelo.
2. **Grave sua própria narração:** salve `cena01_narracao.wav` em `audio/importar/` e refaça a etapa
   de vozes. Observe como a cena muda de duração e tudo continua sincronizado.
3. **Mude a câmera:** em `writer.py`, troque `"movimento": "aproximar"` por `"panoramica"` em uma cena.
4. **Crie um cenário:** copie `library/sets/campo.json`, mude cores e elementos (`arvore`, `flor`,
   `pedra`, `cogumelo`, `pinheiro`, `acacia`, `capim`, `casinha`, `arbusto`).
5. **Cadastre uma música licenciada:** baixe uma faixa da YouTube Audio Library, preencha
   `library/music/licencas.json` e refaça a etapa de música.
6. **Discussão:** quais itens do checklist de publicação existem por causa de lei? Quais por causa
   das regras das plataformas?

## Mensagens importantes para os alunos

* Tudo no fluxo padrão é gratuito e pode ser ensinado e usado comercialmente.
* Serviços pagos (ElevenLabs, Claude) são opcionais e ficam travados até você autorizar.
* O estúdio **não publica** nada: a responsabilidade da publicação é de quem publica.
* Monetização depende das plataformas. Ninguém pode garantir aprovação ou renda.
