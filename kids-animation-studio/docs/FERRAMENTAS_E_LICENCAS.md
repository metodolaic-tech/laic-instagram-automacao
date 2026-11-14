# Ferramentas, custos e licenças: análise "gratuito primeiro"

Para cada ferramenta respondemos às perguntas do projeto: existe versão gratuita? Permite uso
comercial? Exige cartão? Tem limites? Roda localmente? Que hardware precisa? Tem API/automação?
Pode ser ensinada legalmente em curso? Qual a alternativa se deixar de ser gratuita?

> Licenças e políticas mudam. Esta análise reflete o que foi verificado em novembro de 2026
> (as vozes Piper foram conferidas nos MODEL_CARDs oficiais no momento do download). Confira as
> fontes antes de decisões comerciais importantes.

## Ferramentas usadas no fluxo padrão (custo total: R$ 0)

| Ferramenta | Grátis? | Uso comercial do resultado | Cartão? | Limites | Local? | Hardware | Automação | Ensinável em curso | Alternativa |
|---|---|---|---|---|---|---|---|---|---|
| **Blender 4.2+ / 5.x** (GPL-2.0+) | Sim, 100% | Sim: o que você cria é seu; a GPL vale para o programa, não para os vídeos | Não | Nenhum | Sim | CPU 4+ núcleos; GPU NVIDIA/AMD/Apple acelera | API Python completa (`bpy`) | Sim | — (é o padrão aberto do 3D) |
| **FFmpeg** (LGPL/GPL) | Sim | Sim | Não | Nenhum | Sim | Qualquer | Linha de comando | Sim | GStreamer |
| **Piper TTS** (`piper-tts`, GPL-3.0) | Sim | Sim: o áudio gerado não é "obra derivada" do programa | Não | Nenhum | Sim | CPU comum (~0,2 s por frase) | API Python | Sim | Coqui XTTS (licença CPML, **não comercial**), espeak-ng (robótico) |
| **Voz pt_BR-cadu-medium** | Sim | Sim: dataset CC0 e modelo-base CC0 | Não | — | Sim | — | — | Sim | jeff (CC0) |
| **Voz pt_BR-jeff-medium** | Sim | Sim: dataset CC0 e modelo-base CC0 | Não | — | Sim | — | — | Sim | cadu (CC0) |
| **Voz pt_BR-faber-medium** | Sim | Sim, com **atribuição** (modelo-base Hi-Fi TTS, CC BY 4.0). O estúdio adiciona o crédito na descrição | Não | — | Sim | — | — | Sim | cadu/jeff |
| **Python, numpy, Pillow** | Sim | Sim (PSF/BSD/HPND) | Não | — | Sim | Qualquer | — | Sim | — |
| **Compositor de trilha e efeitos do estúdio** | Sim | Sim: gerado pelo próprio estúdio, sem terceiros | Não | — | Sim | Qualquer | Sim | Sim | Bibliotecas abaixo |

## Opcionais (desligados por padrão)

| Serviço | Custo | Observações |
|---|---|---|
| **ElevenLabs** (voz Bianca) | Plano gratuito limitado e **sem uso comercial**; uso comercial exige plano pago. Consome créditos por caractere. | Só roda com `ELEVENLABS_API_KEY` **e** "Permitir serviços pagos". O estúdio procura a voz "Bianca" em `/v1/voices` da sua conta; se não existir, avisa e usa o Piper. Não contorna limites. |
| **Claude (API Anthropic)** para roteiros | Pago por token (o roteiro de 1 vídeo custa centavos de dólar). Exige conta com faturamento. | Só roda com `ANTHROPIC_API_KEY` **e** "Permitir serviços pagos". Saída validada por esquema JSON; se falhar, o roteirista local continua disponível. |

## Bibliotecas de música e efeitos com licença verificável

Use-as cadastrando cada arquivo em `library/music/licencas.json` (autor, URL, licença,
`permite_comercial`). Arquivos sem `permite_comercial: true` **nunca** são usados.

| Fonte | Licença típica | Observação |
|---|---|---|
| YouTube Audio Library | Licença própria do YouTube; algumas faixas exigem atribuição | Livre para usar nos seus vídeos, inclusive monetizados; confira as regras para uso fora do YouTube |
| Pixabay Music / Sound Effects | Licença de Conteúdo Pixabay | Uso comercial permitido; não revenda as faixas isoladas |
| Free Music Archive | Varia por faixa (CC BY, CC BY-NC...) | **Evite NC** (não comercial) |
| Incompetech (Kevin MacLeod) | CC BY 4.0 | Exige crédito na descrição |
| Freesound | CC0, CC BY ou CC BY-NC (varia por som) | Filtre por CC0/CC BY |
| OpenGameArt | CC0, CC BY, GPL (varia) | Filtre por CC0/CC BY |

## Custos: software × infraestrutura × APIs

| Tipo | No fluxo padrão | Observação |
|---|---|---|
| Software | **R$ 0** | Tudo livre ou gratuito |
| Infraestrutura | Seu computador (energia) | Em nuvem paga-se o tempo de máquina; GPU na nuvem pode custar caro por hora |
| APIs | **R$ 0** | ElevenLabs/Claude só com autorização explícita |

## Ferramentas avaliadas e não adotadas (por enquanto)

| Ferramenta | Motivo |
|---|---|
| Geradores de vídeo por IA em nuvem | Créditos pagos, limites diários, termos que mudam, pouco controle de consistência do personagem; não são animação 3D controlável |
| Coqui XTTS-v2 | Licença CPML: **não permite uso comercial** |
| gTTS / tradutores online | Uso não autorizado de serviço; sem licença comercial |
| EEVEE (motor em tempo real do Blender) | Excelente com GPU, mas não funciona em servidores sem placa de vídeo/OpenGL. O estúdio usa Cycles em CPU por padrão e liga a GPU automaticamente quando existe |
| Rigs prontos de terceiros (Mixamo etc.) | Termos próprios e conta obrigatória; preferimos personagens 100% originais e gerados por código |
