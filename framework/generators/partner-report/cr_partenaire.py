#!/usr/bin/env python3
"""Generateur cr-partenaire - RENDU TEXTE, JAMAIS D'ENVOI.

Rend le mail de suivi apres un call partenaire, au format valide : objet, intro
courte, un point par sujet (titre en gras + situation + une seule prochaine etape,
jalon en gras), conclusion, signature. Langue par partenaire (config de mission) :
KSAT en anglais, Airbus en francais, systematiquement.

Le fond vient d'un JSON (produit par Claude depuis la transcription + les sujets) ;
ce generateur ne fait que la MISE EN FORME. Il n'envoie rien, ne cree aucun brouillon.

    python3 cr_partenaire.py --input call.json [--mission sinbad]
    cat call.json | python3 cr_partenaire.py --input -

JSON attendu :
  {"partner":"ksat"|"airbus", "meeting":"Weekly technical meeting", "date":"2026-10-13",
   "intro": "...optionnel...", "closing": "...optionnel...",
   "points":[
     {"title":"Authentication", "situation":"...", "next_step":"Pierre sends the diagram",
      "deadline":"this week"},
     {"title":"Technical questions", "situation":"...", "closed": true}
   ]}
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof   # noqa: E402

L = {
    "en": {"subject": "SAI x {p} - {m}, follow-up {d}", "hello": "Hello everyone,",
           "next": "Next step: {t}", "closed": "Next step: none, this topic is closed.",
           "regards": "Best regards,"},
    "fr": {"subject": "SAI x {p} - {m}, suivi du {d}", "hello": "Bonjour à tous,",
           "next": "Prochaine étape : {t}", "closed": "Prochaine étape : aucune, ce point est clos.",
           "regards": "Bien cordialement,"},
}


def ddmm(iso):
    try:
        y, m, d = iso[:10].split("-"); return f"{d}/{m}"
    except Exception:
        return iso


def render(data, cfg):
    part = (data.get("partner") or "").lower()
    pconf = (cfg.get("partners") or {}).get(part)
    if not pconf:
        sys.exit(f"partenaire inconnu : {part!r} (attendus : {list((cfg.get('partners') or {}))})")
    lang = pconf.get("lang", "fr")
    label = pconf.get("label", part.upper())
    t = L[lang]
    intro = data.get("intro") or (cfg.get("intro") or {}).get(lang, "")
    closing = data.get("closing") or (cfg.get("closing") or {}).get(lang, "")
    sign = cfg.get("signature", "")

    out = []
    out.append("Subject: " if lang == "en" else "Objet : ")
    out[-1] += t["subject"].format(p=label, m=data.get("meeting", ""), d=ddmm(data.get("date", "")))
    out.append("")
    out.append(t["hello"])
    out.append("")
    if intro:
        out.append(intro); out.append("")
    for pt in data.get("points", []):
        out.append(f"**{pt.get('title','').strip()}**")
        if pt.get("situation"):
            out.append(pt["situation"].strip())
        if pt.get("closed"):
            out.append(t["closed"])
        else:
            line = t["next"].format(t=pt.get("next_step", "").strip().rstrip("."))
            dl = (pt.get("deadline") or "").strip()
            line += f" **{dl}**." if dl else "."
            out.append(line)
        out.append("")
    if closing:
        out.append(closing); out.append("")
    out.append(t["regards"])
    out.append(sign)
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON du call ; '-' = stdin")
    ap.add_argument("--mission", default="sinbad")
    a = ap.parse_args()
    cfg = prof._load_yaml(prof.mission_dir(a.mission) / "partner-report.yml")
    raw = sys.stdin.read() if a.input == "-" else Path(a.input).read_text(encoding="utf-8")
    data = json.loads(raw)
    sys.stdout.write(render(data, cfg))
    sys.stderr.write("\n[cr-partenaire] rendu texte uniquement - RIEN n'est envoye. "
                     "Copie/colle dans ton client mail.\n")


if __name__ == "__main__":
    main()
