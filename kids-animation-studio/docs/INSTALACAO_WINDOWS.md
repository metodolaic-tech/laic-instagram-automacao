# Instalação no Windows (passo a passo para iniciantes)

Tempo estimado: 20 a 40 minutos (a maior parte é download). Custo: **R$ 0**.

## Computador recomendado

| | Mínimo | Recomendado |
|---|---|---|
| Sistema | Windows 10 64 bits | Windows 11 |
| Processador | 4 núcleos | 8 núcleos ou mais |
| Memória | 8 GB | 16 GB |
| Placa de vídeo | não obrigatória (render no processador) | NVIDIA RTX (o Blender usa OptiX e fica muitas vezes mais rápido) |
| Disco livre | 10 GB | 30 GB (os quadros do render ocupam espaço) |

Referência medida neste protótipo (processador de 4 núcleos, sem placa de vídeo): qualidade
**rascunho** (640×360, 12 quadros/s) leva ~2 s por quadro, ou seja, **cerca de 10 a 12 minutos para
um vídeo de 25 s**. A qualidade "padrão" (720p, 24 quadros/s) leva várias vezes mais no processador;
com placa NVIDIA o tempo cai bastante.

## Opção A — instalador automático

1. Baixe a pasta `kids-animation-studio` (botão **Code → Download ZIP** no GitHub) e extraia em
   `C:\KidsStudio` (evite pastas com acentos ou dentro do OneDrive).
2. Dê dois cliques em **`instalar_windows.bat`**. Ele usa o `winget` (já vem no Windows 10/11) para
   instalar Python 3.13, FFmpeg e Blender, cria o ambiente do estúdio e baixa as vozes.
3. Feche a janela, abra de novo e dê dois cliques em **`iniciar_painel.bat`**.
   O navegador abre em `http://localhost:8765`.

## Opção B — manual

1. **Python 3.12 ou 3.13**: <https://www.python.org/downloads/>. Na instalação, marque
   **"Add python.exe to PATH"**.
2. **Blender 4.2 ou mais novo** (gratuito, GPL): <https://www.blender.org/download/>. Instale no
   local padrão (`C:\Program Files\Blender Foundation\...`). O estúdio encontra sozinho.
   Se instalou em outro lugar, defina a variável de ambiente `BLENDER_PATH` com o caminho do
   `blender.exe`.
3. **FFmpeg** (gratuito): abra o PowerShell e rode `winget install Gyan.FFmpeg`.
4. Abra o PowerShell **na pasta do estúdio** e rode:

   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python kas.py baixar-vozes
   python kas.py diagnostico
   python kas.py painel
   ```

## Primeiro vídeo

1. No painel, escreva o tema (ex.: *Um leãozinho que aprende a compartilhar*), duração 25 s,
   formato 16:9, qualidade **Rascunho**, e clique **Criar roteiro**.
2. Leia o roteiro, edite se quiser e clique **Aprovar roteiro**.
3. Veja as folhas de modelo dos personagens e clique **Aprovar personagens e produzir**.
4. Acompanhe a barra de progresso. Quando terminar, o vídeo aparece no painel com os botões de
   download (MP4 16:9, MP4 9:16, capas, legendas, pacote de publicação, relatório e aula).

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `FFmpeg FALTANDO` no diagnóstico | Feche e abra o terminal (o PATH só atualiza em janelas novas). |
| `Blender FALTANDO` | Defina `BLENDER_PATH=C:\caminho\blender.exe` ou preencha `blender_executavel` no `config.json`. |
| Vozes faltando | `python kas.py baixar-vozes` (precisa de internet uma vez; os arquivos ficam em `modelos/vozes`). |
| O render parou (queda de energia) | Abra o projeto no painel e clique **Continuar / retomar**: ele recomeça do último quadro salvo. |
| Quero usar minha voz | Grave `cena01_narracao.wav` etc. em `projetos/<projeto>/audio/importar/` e use **Refazer a partir de: Vozes**. |

## Opcional: serviços pagos (desligados por padrão)

* **ElevenLabs (voz Bianca):** crie a variável `ELEVENLABS_API_KEY` no Windows
  (Configurações → Sistema → Sobre → Configurações avançadas → Variáveis de ambiente), ative
  "Permitir serviços pagos" no painel e escolha a voz ElevenLabs no formulário. Se a voz Bianca não
  estiver na sua conta, o estúdio avisa e usa o Piper gratuito.
* **Claude (roteiros mais variados):** `pip install anthropic`, variável `ANTHROPIC_API_KEY`, e no
  `config.json` coloque `"roteirista": "claude"` e `"permitir_servicos_pagos": true`.
