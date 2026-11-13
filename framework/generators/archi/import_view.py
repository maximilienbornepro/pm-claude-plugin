#!/usr/bin/env python3
"""import_view - fige un draw.io dans UNE vue du modele (remplace son rendu genere).

    python3 import_view.py <model.json> --view <id_de_vue> <fichier.drawio> [--page <n|nom>] [-o sortie.json]
    python3 import_view.py <model.json> --view <id_de_vue> --clear [-o sortie.json]

- Le XML est stocke tel quel dans `views[].drawio` (+ `drawio_name`, `drawio_page`) ; la page HTML le rend
  au chargement avec le meme moteur que le bouton « Importer un draw.io » (golden_import.js) :
  diagramme de sequence (umlLifeline) -> sequence au style du schema de reference, sinon boites et zones.
- La vue d'ensemble reste generee depuis le modele ; on importe typiquement dans une sous-vue.
- Sans `-o`, ecrit `<model>.import.json` a cote : le modele d'origine n'est jamais ecrase par defaut.
"""
import json
import sys
from pathlib import Path


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if not a or "--view" not in a:
        print(__doc__)
        return 2
    model_path = Path(a[0])
    vid = a[a.index("--view") + 1]
    out = Path(a[a.index("-o") + 1]) if "-o" in a else model_path.with_suffix(".import.json")
    m = json.loads(model_path.read_text(encoding="utf-8"))
    view = next((v for v in m.get("views") or [] if v.get("id") == vid), None)
    if view is None:
        print(f"Vue inconnue : {vid}. Vues : {', '.join(v.get('id', '?') for v in m.get('views') or [])}")
        return 1
    if "--clear" in a:
        for k in ("drawio", "drawio_name", "drawio_page"):
            view.pop(k, None)
    else:
        rest = [x for i, x in enumerate(a[1:], 1)
                if not x.startswith("-") and a[i - 1] not in ("--view", "-o", "--page")]
        if not rest:
            print("Fichier .drawio manquant.")
            return 2
        src = Path(rest[0])
        xml = src.read_text(encoding="utf-8")
        if "<mxfile" not in xml and "<mxGraphModel" not in xml:
            print(f"{src} n'est pas un fichier draw.io.")
            return 1
        view["drawio"] = xml
        view["drawio_name"] = src.name
        if "--page" in a:
            p = a[a.index("--page") + 1]
            if p.isdigit():
                view["drawio_page"] = int(p)
            else:
                import re
                names = re.findall(r'<diagram[^>]*name="([^"]*)"', xml)
                if p not in names:
                    print(f"Page inconnue : {p}. Pages : {', '.join(names)}")
                    return 1
                view["drawio_page"] = names.index(p)
    out.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ecrit : {out} (vue {vid}{' videe' if '--clear' in a else ' <- ' + view.get('drawio_name', '')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
