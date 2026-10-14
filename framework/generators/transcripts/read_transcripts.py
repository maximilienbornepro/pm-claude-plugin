#!/usr/bin/env python3
"""Lecteur de transcriptions - LECTURE SEULE, sources pluggables.

Normalise des transcriptions / comptes rendus de reunion vers une forme commune
  {date, title, url, text}
et les filtre sur une fenetre de dates. La sortie alimente les generateurs aval
(sujets, CR partenaires, revue des risques, synthese d'appel). N'ecrit rien.

Deux sources, au choix :
  - `--dump <f.json|f.jsonl>` : export produit par Claude via le connecteur Notion
    (notion-query-meeting-notes + fetch). JSON (liste) ou JSONL. C'est la source par
    defaut du framework (Notion meeting notes).
  - `--files <dossier>` : fichiers .md/.txt locaux (source pluggable). La date vient
    d'un frontmatter `date:` ou du nom de fichier (AAAA-MM-JJ) ; le titre du `# titre`
    ou du nom de fichier.

Filtre : --since / --until (ISO AAAA-MM-JJ) ou --date (un seul jour). Sortie lisible,
ou --json pour la passer telle quelle a un generateur aval.

    python3 read_transcripts.py --dump notes.json --since 2026-10-01 --until 2026-10-12
    python3 read_transcripts.py --files ./transcriptions --date 2026-10-02 --json
"""
import argparse, json, re, sys
from pathlib import Path

DATE_KEYS = ("date", "Created time", "created_time", "createdTime", "created", "timestamp", "Last edited time")
TEXT_KEYS = ("text", "content", "body", "transcript", "resume")
URL_KEYS = ("url", "Url", "link")
TITLE_KEYS = ("title", "Title", "name", "Name")


def _first(d, keys, default=""):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return default


def _day(s):
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(s))
    return m.group(0) if m else ""


def _norm_record(d):
    return {
        "date": _day(_first(d, DATE_KEYS)),
        "title": str(_first(d, TITLE_KEYS, "(sans titre)")).strip(),
        "url": _first(d, URL_KEYS),
        "text": str(_first(d, TEXT_KEYS)).strip(),
    }


def from_dump(path):
    raw = Path(path).read_text(encoding="utf-8").strip()
    if raw[:1] in ("[", "{"):
        data = json.loads(raw)
    else:  # JSONL
        data = [json.loads(l) for l in raw.splitlines() if l.strip()]
    # tolere {"results": [...]} / {"pages": [...]} (forme du connecteur) ou un seul enregistrement
    if isinstance(data, dict):
        data = data.get("results") or data.get("pages") or [data]
    return [_norm_record(r) for r in data]


def from_files(folder):
    out = []
    for p in sorted(Path(folder).glob("**/*")):
        if p.suffix.lower() not in (".md", ".txt"):
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        mdate = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", txt, re.M)
        date = mdate.group(1) if mdate else _day(p.name)
        mtitle = re.search(r"^#\s+(.+)$", txt, re.M)
        title = mtitle.group(1).strip() if mtitle else p.stem
        out.append({"date": date, "title": title, "url": str(p), "text": txt.strip()})
    return out


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dump", help="export JSON/JSONL des meeting notes (connecteur Notion)")
    src.add_argument("--files", help="dossier de .md/.txt")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--date", help="un seul jour (ISO)")
    ap.add_argument("--json", action="store_true", help="sortie JSON (pour un generateur aval)")
    ap.add_argument("--excerpt", type=int, default=160, help="longueur de l'extrait lisible")
    a = ap.parse_args()

    since = a.date or a.since
    until = a.date or a.until
    recs = from_dump(a.dump) if a.dump else from_files(a.files)
    recs = [r for r in recs if r["date"]]
    recs = [r for r in recs if (not since or r["date"] >= since) and (not until or r["date"] <= until)]
    recs.sort(key=lambda r: (r["date"], r["title"]))

    if a.json:
        sys.stdout.write(json.dumps(recs, ensure_ascii=False, indent=2) + "\n")
        return
    fen = f"{since or '...'} -> {until or '...'}"
    print(f"Transcriptions ({len(recs)}) sur {fen} :")
    for r in recs:
        ex = re.sub(r"\s+", " ", r["text"])[:a.excerpt]
        print(f"- [{r['date']}] {r['title']}")
        if r["url"]:
            print(f"    {r['url']}")
        if ex:
            print(f"    « {ex}{'…' if len(r['text']) > a.excerpt else ''} »")
    print("\nLecture seule : alimente sujets / CR / risques, n'ecrit rien.")


if __name__ == "__main__":
    main()
