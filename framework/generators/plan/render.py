#!/usr/bin/env python3
"""Rend la page « Avancement et sprints » (plan de sprints) depuis un JSON de donnees.

Reutilisable comme le generateur `archi` : le DESIGN vit dans le gabarit
`plan_design.tmpl.html` (CSS + Chart.js + interactions), on l'edite ; ce module ne
fait qu'injecter un seul bloc JSON (`meta` + `report` + `sprints[]`) dans le gabarit.
Le JSON suit le contrat de `CONTRACT.md`. Aucune dependance, aucune ecriture ailleurs
que le fichier de sortie.

  python3 render.py donnees.json [sortie.html]   # rend la page
  python3 render.py --example [sortie.html]       # rend l'exemple (plan.example.json)

Pour produire le JSON depuis un Jira, voir `from_jira.py` (pipeline config-driven),
qui appelle ce renderer a la fin.
"""
import sys, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
TMPL = os.path.join(HERE, "plan_design.tmpl.html")


def render(datajson, out_path):
    """Injecte `datajson` (dict) dans le gabarit et ecrit `out_path`."""
    tmpl = open(TMPL, encoding="utf-8").read()
    blob = json.dumps(datajson, ensure_ascii=False).replace("</", "<\\/")  # sûreté </script>
    html = tmpl.replace("__DATAJSON__", blob)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return len(html)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    if argv[0] == "--example":
        src = os.path.join(HERE, "plan.example.json")
        out = argv[1] if len(argv) > 1 else "plan.example.html"
    else:
        src = argv[0]
        out = argv[1] if len(argv) > 1 else "plan.html"
    if not os.path.exists(src):
        sys.exit(f"JSON introuvable : {src}")
    data = json.load(open(src, encoding="utf-8"))
    n = render(data, out)
    print(f"écrit {out} | {n} octets | {len(data.get('sprints', []))} sprints")


if __name__ == "__main__":
    main(sys.argv[1:])
