#!/usr/bin/env python3
"""Kids Animation Studio AI - linha de comando.

Exemplos:
  python kas.py diagnostico
  python kas.py baixar-vozes
  python kas.py novo "Um leãozinho que aprende a compartilhar" --duracao 25 --auto
  python kas.py produzir <id_do_projeto>
  python kas.py aprovar <id_do_projeto> roteiro
  python kas.py refazer <id_do_projeto> voz
  python kas.py status <id_do_projeto>
  python kas.py listar
  python kas.py personagens
  python kas.py painel            (abre a interface web em http://localhost:8765)
"""
import argparse
import json
import sys

from studio import art_director as ad
from studio.diagnose import print_report
from studio.pipeline import ETAPAS, Project, run_pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kas", description="Kids Animation Studio AI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("diagnostico", help="verifica o computador e as ferramentas")
    sub.add_parser("baixar-vozes", help="baixa as vozes gratuitas pt-BR do Piper")
    n = sub.add_parser("novo", help="cria um projeto a partir de um tema")
    n.add_argument("tema")
    n.add_argument("--duracao", type=int, default=25)
    n.add_argument("--proporcao", choices=["16:9", "9:16"], default="16:9")
    n.add_argument("--faixa", choices=["2-4", "4-6", "6-8"], default="4-6")
    n.add_argument("--categoria", choices=["valores", "animais", "aventura", "educacao", "biblica"])
    n.add_argument("--qualidade", choices=["teste", "rascunho", "padrao", "alta"])
    n.add_argument("--cenario", choices=["savana", "floresta", "campo"])
    n.add_argument("--voz", choices=["piper", "elevenlabs"])
    n.add_argument("--sem-ensino", action="store_true")
    n.add_argument("--auto", action="store_true", help="aprova roteiro e personagens automaticamente")
    n.add_argument("--ate", choices=ETAPAS, help="para depois desta etapa")
    for name in ("produzir", "status"):
        s = sub.add_parser(name)
        s.add_argument("projeto")
        if name == "produzir":
            s.add_argument("--auto", action="store_true")
            s.add_argument("--ate", choices=ETAPAS)
    a = sub.add_parser("aprovar")
    a.add_argument("projeto")
    a.add_argument("etapa", choices=["roteiro", "personagens"])
    r = sub.add_parser("refazer", help="refaz uma etapa e as seguintes")
    r.add_argument("projeto")
    r.add_argument("etapa", choices=ETAPAS)
    sub.add_parser("listar")
    sub.add_parser("personagens")
    w = sub.add_parser("painel")
    w.add_argument("--porta", type=int, default=8765)
    args = ap.parse_args(argv)

    if args.cmd == "diagnostico":
        d = print_report()
        return 0 if d["pronto"] else 1
    if args.cmd == "baixar-vozes":
        from studio.voice import download_voices
        download_voices()
        print("Vozes prontas.")
        return 0
    if args.cmd == "novo":
        p = Project.create(args.tema, args.duracao, args.proporcao, args.faixa, args.categoria, args.qualidade,
                           args.cenario, args.voz, modo_ensino=not args.sem_ensino)
        print(f"Projeto criado: {p.id}")
        res = run_pipeline(p, auto_approve=args.auto, until=args.ate)
        print(f"Resultado: {res}  (pasta: {p.dir})")
        return 0 if res != "erro" else 2
    if args.cmd == "produzir":
        p = Project(args.projeto)
        res = run_pipeline(p, auto_approve=args.auto, until=args.ate)
        print(f"Resultado: {res}")
        return 0 if res != "erro" else 2
    if args.cmd == "aprovar":
        p = Project(args.projeto)
        print("Aprovado." if p.approve(args.etapa) else "Essa etapa não estava aguardando aprovação.")
        return 0
    if args.cmd == "refazer":
        p = Project(args.projeto)
        p.reset_from(args.etapa)
        print(f"Etapas a partir de '{args.etapa}' serão refeitas. Rode: python kas.py produzir {p.id}")
        return 0
    if args.cmd == "status":
        p = Project(args.projeto)
        for e in ETAPAS:
            print(f"  {e:<12} {p.status(e)}")
        print(json.dumps(p.data["progresso"], ensure_ascii=False))
        return 0
    if args.cmd == "listar":
        for d in Project.list_all():
            print(f"{d['id']}  |  {d.get('titulo', d['tema'])}  |  {d['progresso'].get('mensagem')}")
        return 0
    if args.cmd == "personagens":
        ad.ensure_default_library()
        for c in ad.list_characters():
            print(f"{c['id']:<20} {c['nome']:<8} {c['especie_nome']:<14} {c['personalidade']}")
        return 0
    if args.cmd == "painel":
        from studio.web.server import serve
        serve(args.porta)
        return 0


if __name__ == "__main__":
    sys.exit(main())
