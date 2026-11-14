# Limitações conhecidas (com transparência) e próximos passos

## O que o protótipo NÃO faz ainda

| Limitação | Impacto | Alternativa viável hoje |
|---|---|---|
| Personagens feitos de formas primitivas com **rig hierárquico** (sem armature/skinning, sem deformação da malha) | Movimentos claros e fofos, mas sem a maciez de grandes estúdios (cotovelos, dedos, tecido) | Fase 3: modelar personagens no Blender (ou escultura), criar armature e usar o mesmo sistema de ações; o código de animação já separa "o que fazer" de "como o corpo é" |
| **Sincronia labial por volume** (boca abre conforme a intensidade da voz) | Convence em vídeos curtos; não forma fonemas (A, O, M...) | Usar Rhubarb Lip Sync (MIT) para gerar visemas e trocar a forma da boca |
| Render em CPU é lento para alta qualidade | 25 s em "rascunho" ≈ 10–12 min em 4 núcleos; "padrão"/"alta" levam bem mais | GPU NVIDIA (OptiX liga sozinho); EEVEE em máquinas com GPU; render noturno |
| Qualidade "rascunho" a 12 quadros/s | Movimento "em dois", estilo comum em animação, mas menos fluido | Qualidades "padrão" e "alta" renderizam a 24 quadros/s |
| Roteirista local usa modelos narrativos | Histórias curtas e seguras, mas com variedade limitada (10 modelos) | Ativar o roteirista Claude (pago) ou escrever novos modelos em `writer.py` |
| Vozes Piper pt-BR são masculinas/neutras; o tom infantil vem de *pitch shift* | Diferenciação razoável entre personagens; não substitui dublagem | ElevenLabs (voz Bianca) ou gravações próprias na pasta `audio/importar` |
| ElevenLabs e Claude não puderam ser testados neste ambiente (sem chaves; serviços pagos) | Código implementado com travas e com volta automática para o Piper | Testar com sua chave, com "Permitir serviços pagos" ligado |
| Não há interação física complexa (abraços, mãos segurando com precisão) | Objetos "flutuam" até a mão do personagem | Constraints "Child Of" do Blender na Fase 3 |

## Roteiro de evolução

1. **Fase 3 — Qualidade:** armature com skinning, rostos com shape keys (sorriso, fonemas),
   pelos com Geometry Nodes, céu com nuvens volumétricas, mais cenários e espécies, Rhubarb Lip Sync.
2. **Fase 4 — Automação:** fila de produção (vários vídeos à noite), séries com o mesmo elenco,
   reaproveitamento de cenas e geração de cortes para Shorts.
3. **Fase 5 — Interface:** edição visual de personagens (cores, acessórios) e linha do tempo no painel.
4. **Fase 6 — Ensino:** trilha de exercícios progressivos e projetos-modelo para alunos.
