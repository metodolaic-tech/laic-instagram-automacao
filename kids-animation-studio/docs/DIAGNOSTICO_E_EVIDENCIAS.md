# Diagnóstico do ambiente e evidências do protótipo

## Fase 1: ambiente onde o protótipo foi construído e testado

| Item | Resultado |
|---|---|
| Sistema | Linux x86_64 (servidor na nuvem, **sem placa de vídeo**) |
| CPU / RAM | 4 núcleos / 16 GB |
| Python | 3.13 |
| Blender | módulo `bpy` 5.3.0 (instalado via `pip`, o Blender real como biblioteca). Motor Cycles em CPU. EEVEE **não** funciona sem GPU/OpenGL. |
| FFmpeg | 6.1.1 (com `libass` para legendas e `xfade` para transições) |
| Voz | `piper-tts` 1.8.0 + vozes pt_BR cadu, jeff e faber (licenças conferidas nos MODEL_CARDs) |
| Serviços pagos | nenhum usado (sem chaves ElevenLabs/Anthropic; travas desligadas) |

Limitação do ambiente: o site de downloads do Blender e o Hugging Face estavam bloqueados por
padrão. O Blender foi obtido pelo PyPI (`bpy`) e o acesso ao Hugging Face (somente para baixar as
vozes) foi liberado em um ambiente de nuvem específico do projeto.

## Teste de aceitação (critérios de sucesso da Fase 2)

Comando executado:

```bash
python kas.py novo "Crie uma animação infantil de 25 segundos sobre um leãozinho que aprende a compartilhar" \
       --duracao 25 --qualidade rascunho --auto
```

| Critério | Resultado | Evidência |
|---|---|---|
| MP4 reproduzível de 20–30 s | ✅ **27,96 s**, H.264 + AAC, 16:9 (640×360) e 9:16 (720×1280) | `exemplos/tito_aprende_a_compartilhar/video_16x9.mp4`, `video_9x16.mp4` |
| História infantil curta | ✅ "Tito Aprende a Compartilhar": gancho → conflito → lição | `roteiro.md` |
| Pelo menos um personagem 3D original | ✅ Tito (leão) e Lila (coelha), modelos 3D procedurais originais | `tito_leao.png`, `lila_coelho.png` |
| Movimento perceptível | ✅ andar, pular, acenar, segurar, entregar a cesta, comemorar, piscar, boca sincronizada; câmera com aproximação e panorâmica | `folha_de_contato.jpg` |
| Narração em português do Brasil | ✅ narrador + 2 vozes de personagem (Piper local) | `RELATORIO.md` |
| Música de fundo | ✅ trilha original "aventura → celebração", com redução automática durante as falas | `RELATORIO.md` |
| Pelo menos duas cenas | ✅ 3 cenas com transições | `roteiro.md` |
| Áudio sincronizado | ✅ cenas dimensionadas pela duração real das falas; legendas e boca usam os mesmos instantes; loudness integrado **−15,5 LUFS** | `legendas.srt` |
| Arquivos organizados | ✅ pasta de projeto padronizada (roteiro, personagens, áudio, cenas, final) | `docs/ARQUITETURA.md` |
| Relatório de ferramentas, custo e licenças | ✅ custo total R$ 0 | `RELATORIO.md` |

Tempos medidos (4 núcleos, sem GPU): roteiro < 1 s · folhas de modelo ~11 s · vozes ~3 s ·
**render 3D 12 min (345 quadros, ~2,1 s/quadro)** · edição + exportação ~35 s · capa ~25 s.

## Testes automatizados

`python -m unittest discover -s tests -v` → **15 testes, todos passando**, incluindo síntese de voz
real com Piper, render real no Blender, transições no FFmpeg, ducking da música, legendas,
aprovação e retomada de projeto, e trava de serviços pagos.

## O que não foi testado aqui

* ElevenLabs (voz Bianca) e roteirista Claude: implementados com travas e volta automática para as
  opções gratuitas, mas não executados (são pagos e não havia chaves).
* Instalação real no Windows: scripts e guia escritos; o código usa só recursos multiplataforma
  (detecção do `blender.exe`, caminhos com `pathlib`), mas não foi executado em uma máquina Windows.
* Render com GPU (OptiX/CUDA): ativado automaticamente quando há placa, mas o servidor de teste não tinha GPU.
