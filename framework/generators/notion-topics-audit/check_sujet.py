#!/usr/bin/env python3
"""notion-sujets - validateur de FORMAT d'un sujet (LECTURE SEULE).

Verifie qu'un corps de sujet respecte la structure imposee (config de mission
profiles/<mission>/notion_sujets.yml > structure) AVANT toute ecriture via le
connecteur. N'ecrit rien : il signale les defauts a corriger.

Controles :
  - presence des sections (ex. **Contexte**, **Action attendue**), dans l'ordre ;
  - pas de liste a plat de 3+ puces sans intitule de theme (regrouper) ;
  - pas de prose de plus de N caracteres (la decouper) ;
  - pas de vraie mention @ (nom en texte simple, sinon notification).

    python3 check_sujet.py --body sujet.md [--mission sinbad]
    cat sujet.md | python3 check_sujet.py --body -
"""
import argparse, re, sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof   # noqa: E402


def _bold_headers(txt):
    # lignes qui sont un intitule en gras seul (**Theme** ou **Theme** : ...)
    return [m.group(1).strip() for m in re.finditer(r"^\s*\*\*(.+?)\*\*\s*:?\s*$", txt, re.M)]


def check(txt, st):
    v = []
    heads = _bold_headers(txt)
    heads_l = [h.casefold().rstrip(" :") for h in heads]
    # 1) sections presentes et dans l'ordre
    want = [s.casefold() for s in st.get("sections", [])]
    pos = [heads_l.index(w) for w in want if w in heads_l]
    for w, sec in zip(want, st.get("sections", [])):
        if w not in heads_l:
            v.append(f"section manquante : **{sec}**")
    if pos == sorted(pos) and len(pos) == len(want) and want:
        pass
    elif all(w in heads_l for w in want) and pos != sorted(pos):
        v.append("sections dans le desordre (attendu : " + " puis ".join(st["sections"]) + ")")
    # 2) liste a plat de 3+ puces sans theme : compter les puces de meme niveau consecutives
    run = 0
    flat_max = st.get("flat_list_max", 2)
    for line in txt.splitlines():
        if re.match(r"^\s*[-*]\s+\S", line) and not re.match(r"^\s*[-*]\s+\*\*", line):
            run += 1
            if run == flat_max + 1:
                v.append(f"liste a plat de {flat_max+1}+ puces sans intitule de theme (ranger par theme)")
        elif line.strip():
            run = 0
    # 3) prose trop longue (ligne non-puce, hors titres)
    mx = st.get("max_prose_chars", 180)
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith(("-", "*", "#")) or s.startswith("**"):
            continue
        if len(s) > mx:
            v.append(f"paragraphe de {len(s)} caracteres (> {mx}) : a decouper")
    # 4) vraie mention @
    if re.search(r"(?<!\w)@[A-Z][\w-]+", txt) or "data-mention" in txt or "notion.so/" in txt and "@" in txt:
        v.append("mention @ detectee : mettre le nom en texte simple (sinon notification)")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True, help="corps du sujet (markdown) ; '-' = stdin")
    ap.add_argument("--mission", default="sinbad")
    a = ap.parse_args()
    cfg = prof._load_yaml(prof.mission_dir(a.mission) / "notion-topics.yml")
    st = cfg.get("structure", {})
    txt = sys.stdin.read() if a.body == "-" else Path(a.body).read_text(encoding="utf-8")
    viol = check(txt, st)
    if viol:
        print("DEFAUTS de format (a corriger avant ecriture) :")
        for x in viol:
            print(f"  - {x}")
        sys.exit(1)
    print("Format OK (Contexte/Action, un niveau, pas de prose au kilometre, pas de mention).")


if __name__ == "__main__":
    main()
