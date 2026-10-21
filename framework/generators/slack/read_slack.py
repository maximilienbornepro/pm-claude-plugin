#!/usr/bin/env python3
"""Lecteur de conversations Slack - LECTURE SEULE, source pluggable.

Normalise un export de messages Slack (produit par Claude via Claude in Chrome, voir le SKILL) vers
une forme commune
  {date, author, channel, thread, text, url}
et le filtre sur une fenetre de dates. La sortie alimente les generateurs aval (revue des sujets,
weekly report). N'ecrit RIEN, ni dans Slack ni ailleurs.

Le script ne parle jamais a Slack : c'est Claude qui lit (recherche + threads, jamais de saisie dans un
composer) et depose un export JSON/JSONL ; ce lecteur le normalise, comme `read_transcripts.py` pour les
transcriptions. Separer la lecture (interactive, cote Claude) du traitement (deterministe, teste) garde
la regle de securite verifiable.

    python3 read_slack.py --dump slack.json --since 2026-10-12 --until 2026-10-18
    python3 read_slack.py --dump slack.jsonl --date 2026-10-15 --json out.json

Forme d'entree toleree (une ligne = un message) : objets avec au moins un champ texte. Cles reconnues :
  date   : date, ts, timestamp, Created time, created_at, time
  author : author, user, from, sender, name
  channel: channel, conversation, in, chan
  thread : thread, thread_ts, in_thread (bool ou id)
  text   : text, message, content, body
  url    : url, permalink, link
Accepte une liste, du JSONL, ou {"messages": [...]} / {"results": [...]}.
"""
import argparse
import json
import re
import sys
from pathlib import Path

DATE_KEYS = ("date", "ts", "timestamp", "Created time", "created_at", "created", "time")
AUTHOR_KEYS = ("author", "user", "from", "sender", "name")
CHANNEL_KEYS = ("channel", "conversation", "in", "chan")
THREAD_KEYS = ("thread", "thread_ts", "in_thread", "parent")
TEXT_KEYS = ("text", "message", "content", "body")
URL_KEYS = ("url", "permalink", "link")


def _first(d, keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


def _day(s):
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(s))
    return m.group(0) if m else ""


def _norm(d):
    return {
        "date": _day(_first(d, DATE_KEYS)),
        "author": str(_first(d, AUTHOR_KEYS, "(inconnu)")).strip(),
        "channel": str(_first(d, CHANNEL_KEYS, "(sans canal)")).strip(),
        "thread": bool(_first(d, THREAD_KEYS, False)),
        "text": str(_first(d, TEXT_KEYS)).strip(),
        "url": _first(d, URL_KEYS),
    }


def load_dump(path):
    raw = Path(path).read_text(encoding="utf-8").strip()
    try:
        data = json.loads(raw)                       # JSON (liste ou objet)
    except json.JSONDecodeError:
        data = [json.loads(l) for l in raw.splitlines() if l.strip()]  # JSONL
    if isinstance(data, dict):
        data = data.get("messages") or data.get("results") or data.get("rows") or [data]
    return [_norm(r) for r in data if isinstance(r, dict)]


def in_window(rows, since, until):
    out = []
    for r in rows:
        d = r["date"]
        if not d:
            continue
        if since and d < since:
            continue
        if until and d > until:
            continue
        out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True, help="export Slack JSON/JSONL (produit par Claude)")
    ap.add_argument("--since", help="AAAA-MM-JJ (inclus)")
    ap.add_argument("--until", help="AAAA-MM-JJ (inclus)")
    ap.add_argument("--date", help="un seul jour AAAA-MM-JJ (equivaut a --since=--until)")
    ap.add_argument("--json", help="ecrit la sortie normalisee dans ce fichier")
    args = ap.parse_args(argv)
    since = args.date or args.since
    until = args.date or args.until
    rows = in_window(load_dump(args.dump), since, until)
    rows.sort(key=lambda r: (r["date"], r["channel"]))
    if args.json:
        Path(args.json).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"ecrit {args.json} | {len(rows)} messages")
        return 0
    chans = {}
    for r in rows:
        chans.setdefault(r["channel"], 0)
        chans[r["channel"]] += 1
    print(f"{len(rows)} messages sur la fenetre | canaux : "
          + ", ".join(f"{c} ({n})" for c, n in sorted(chans.items(), key=lambda x: -x[1])))
    for r in rows:
        th = " [thread]" if r["thread"] else ""
        print(f"  {r['date']} #{r['channel']} {r['author']}{th}: {r['text'][:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
