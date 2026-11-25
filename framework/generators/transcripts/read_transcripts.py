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
  - `--notion-db <id>` : base Notion lue par l'API officielle (integration interne,
    jeton NOTION_TOKEN ou ~/.config/pm-framework/notion.env). Filtre la colonne
    « Catégorie » (--category, Omi par defaut) : transcriptions du pendentif Omi
    rangees dans « Notes de réunion » du Notion perso.

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


def _load_token(env_file):
    """Jeton d'integration Notion : variable NOTION_TOKEN, sinon fichier env (cle=valeur)."""
    import os
    tok = os.environ.get("NOTION_TOKEN")
    if tok:
        return tok
    p = Path(os.path.expanduser(env_file))
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("NOTION_TOKEN="):
                return line.split("=", 1)[1].strip()
    sys.exit(f"Aucun jeton Notion : definir NOTION_TOKEN ou {env_file}")


def from_notion_db(db_id, category, token, since=None, until=None):
    """Lit une base Notion par l'API officielle (integration interne), LECTURE SEULE.

    Garde les lignes dont la colonne multi-select « Catégorie » contient `category`
    (ex. Omi), filtre la colonne Date cote Notion, et lit le corps de chaque page
    (resume + transcription) en texte brut.
    """
    import time, urllib.request, urllib.error
    H = {"Authorization": "Bearer " + token, "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

    def api(method, path, data=None):
        for att in range(6):
            time.sleep(0.35)
            req = urllib.request.Request("https://api.notion.com/v1" + path,
                                         json.dumps(data).encode() if data is not None else None, H, method=method)
            try:
                return json.load(urllib.request.urlopen(req, timeout=60))
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503):
                    time.sleep(2 * (att + 1)); continue
                raise
        raise RuntimeError("API Notion indisponible")

    filters = []
    if category:
        filters.append({"property": "Catégorie", "multi_select": {"contains": category}})
    if since:
        filters.append({"property": "Date", "date": {"on_or_after": since}})
    if until:
        filters.append({"property": "Date", "date": {"on_or_before": until + "T23:59:59"}})
    body = {"page_size": 100}
    if filters:
        body["filter"] = {"and": filters} if len(filters) > 1 else filters[0]

    out, cursor = [], None
    while True:
        if cursor:
            body["start_cursor"] = cursor
        res = api("POST", f"/databases/{db_id}/query", body)
        for pg in res["results"]:
            props = pg["properties"]
            title = "".join(t["plain_text"] for v in props.values() if v["type"] == "title" for t in v["title"])
            d = (props.get("Date") or {}).get("date") or {}
            lines, bc = [], None
            while True:
                q = f"/blocks/{pg['id']}/children?page_size=100" + (f"&start_cursor={bc}" if bc else "")
                ch = api("GET", q)
                for b in ch["results"]:
                    v = b.get(b["type"], {})
                    if isinstance(v, dict) and "rich_text" in v:
                        lines.append("".join(r.get("plain_text", "") for r in v["rich_text"]))
                if not ch.get("has_more"):
                    break
                bc = ch["next_cursor"]
            out.append({"date": _day(d.get("start", "")), "title": title or "(sans titre)",
                        "url": pg["url"], "text": "\n".join(lines).strip()})
        if not res.get("has_more"):
            break
        cursor = res["next_cursor"]
    return out


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--dump", help="export JSON/JSONL des meeting notes (connecteur Notion)")
    src.add_argument("--files", help="dossier de .md/.txt")
    src.add_argument("--notion-db", help="id d'une base Notion lue par l'API (integration interne)")
    ap.add_argument("--category", default="Omi", help="valeur de la colonne Catégorie a garder (--notion-db)")
    ap.add_argument("--token-env", default="~/.config/pm-framework/notion.env",
                    help="fichier contenant NOTION_TOKEN=... (--notion-db)")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--date", help="un seul jour (ISO)")
    ap.add_argument("--json", action="store_true", help="sortie JSON (pour un generateur aval)")
    ap.add_argument("--excerpt", type=int, default=160, help="longueur de l'extrait lisible")
    a = ap.parse_args()

    since = a.date or a.since
    until = a.date or a.until
    if a.notion_db:
        recs = from_notion_db(a.notion_db, a.category, _load_token(a.token_env), since, until)
    else:
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
