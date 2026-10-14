#!/usr/bin/env python3
"""Collecte les prompts PERTINENTS d'une journee depuis les transcripts Claude Code.

"Pertinent" = la requete a produit une MODIFICATION du projet (regles ci-dessous).
Les questions, lectures, recherches, audits, dry-run et previews sont ignores.

Entree  : les .jsonl de session sous ~/.claude/projects/<slug>/ (option --project-dir).
Sortie  : une ligne JSON par prompt pertinent (candidat d'activite a verser au store) :
          {date, heure, prompt, modifs:[...], session, projet}
          sur stdout ; a relire et curer avant d'alimenter activites.jsonl.

  python3 collect.py --project-dir ~/.claude/projects/-Users-...-Sinbad --date 2026-10-12
  python3 collect.py --project-dir ... --since 2026-10-06 --until 2026-10-12 --projet SINBAD

Aucune dependance externe. Lecture seule : n'ecrit rien, n'appelle aucun service.

--- Regles de pertinence (ce qui compte comme "modification du projet") ----------
Un prompt est garde s'il est suivi, AVANT le prompt utilisateur suivant, d'au moins
un appel d'outil modifiant :
  - edition de fichier : Write, Edit, MultiEdit, NotebookEdit ;
  - publication : Artifact (publish/delete), ou un Bash parmi PUBLISH_CMDS ;
  - Jira en ecriture : editJiraIssue, createJiraIssue, transitionJiraIssue,
    createIssueLink, (addOrEdit|add)...Comment, executeWrite/executeDestructive ;
  - Notion en ecriture : notion-update-*, notion-create-*, notion-move-*,
    notion-duplicate-*, notion-upload-*, notion-restore-* ;
  - Confluence : createConfluence*, updateConfluencePage ;
  - Office/Drive : create_file, update_file, trash_file, copy_file, share_file ;
  - externe : teams_send*, teams_reply* ;
  - Bash modifiant : git commit|git push, *.sh de publication, embed_figma.py
    (hors --check/--dry-run), jira_sprints.py ... --apply, onedrive_xlsx ... write.
Tout le reste (questions, Read/Grep/Glob, *_search, executeRead, audits, --dry-run,
--check, build_*.py vers le scratchpad) n'est PAS modifiant.
"""
import argparse, datetime, json, os, re, sys
from pathlib import Path

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
JIRA_WRITE = re.compile(r"(editJiraIssue|createJiraIssue|transitionJiraIssue|createIssueLink|"
                        r"Comment$|executeWrite|executeDestructive|updateConfluence|createConfluence)")
NOTION_WRITE = re.compile(r"notion-(update|create|move|duplicate|upload|restore)")
DRIVE_WRITE = re.compile(r"(create_file|update_file|trash_file|copy_file|share_file)$")
EXT_WRITE = re.compile(r"(teams_send|teams_reply|teams_create_chat)")
PUBLISH_CMDS = re.compile(r"(sync_plan\.sh|sync_pages\.sh|publish\.sh|git +commit|git +push)")
BASH_WRITE = re.compile(r"(jira_sprints\.py[^\n]*--apply|onedrive_xlsx[^\n]*\b(write|set|save)\b)")
BASH_SKIP = re.compile(r"(--dry-run|--check)")
EMBED = re.compile(r"embed_figma\.py")


def _tool_is_modifier(name, inp):
    name = name or ""
    if name in WRITE_TOOLS:
        return name
    if name == "Artifact":
        act = (inp or {}).get("action", "publish")
        return "Artifact:publish" if act in ("publish", "delete", None) else None
    if JIRA_WRITE.search(name):
        return name
    if NOTION_WRITE.search(name):
        return name
    if DRIVE_WRITE.search(name) or EXT_WRITE.search(name):
        return name
    if name == "Bash":
        cmd = (inp or {}).get("command", "")
        if PUBLISH_CMDS.search(cmd) or BASH_WRITE.search(cmd):
            return "Bash"
        if EMBED.search(cmd) and not BASH_SKIP.search(cmd):
            return "Bash"
    return None


def _target(name, inp):
    """Petite empreinte de ce qui a ete modifie (pour le store)."""
    inp = inp or {}
    if name in WRITE_TOOLS:
        return inp.get("file_path") or inp.get("notebook_path") or name
    if name == "Bash":
        c = (inp.get("command") or "").strip().replace("\n", " ")
        return c[:120]
    if name == "Artifact":
        return "artifact:" + str(inp.get("action", "publish"))
    for k in ("issueIdOrKey", "pageId", "url", "cloudId"):
        if inp.get(k):
            return f"{name}:{inp[k]}"
    return name


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
                parts.append(b["text"])
        return "\n".join(parts)
    return ""


def _is_real_user(obj):
    if obj.get("type") != "user":
        return False
    c = (obj.get("message") or {}).get("content")
    if isinstance(c, str):
        return bool(c.strip())
    if isinstance(c, list):
        return any(isinstance(b, dict) and b.get("type") == "text" for b in c) and \
               not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)
    return False


def _day(ts):
    return (ts or "")[:10]


def collect(files, since, until):
    out = []
    for f in files:
        session = Path(f).stem
        cur = None  # {prompt, date, heure, modifs:set}
        try:
            lines = Path(f).read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except Exception:
                continue
            if _is_real_user(o):
                if cur and cur["modifs"]:
                    out.append(cur)
                txt = _text_of((o.get("message") or {}).get("content")).strip()
                ts = o.get("timestamp") or ""
                # ignore les messages injectes par le harness (reminders, hooks)
                if txt.startswith("<") or "system-reminder" in txt[:40].lower():
                    cur = None
                    continue
                cur = {"prompt": txt, "date": _day(ts), "heure": ts[11:16], "modifs": set(), "session": session}
            elif o.get("type") == "assistant" and cur is not None:
                for b in (o.get("message") or {}).get("content", []) or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        m = _tool_is_modifier(b.get("name"), b.get("input"))
                        if m:
                            cur["modifs"].add(_target(b.get("name"), b.get("input")))
        if cur and cur["modifs"]:
            out.append(cur)
    # fenetre de dates + mise en forme
    res = []
    for e in out:
        if since and e["date"] < since:
            continue
        if until and e["date"] > until:
            continue
        res.append({"date": e["date"], "heure": e["heure"], "prompt": e["prompt"],
                    "modifs": sorted(e["modifs"]), "session": e["session"]})
    res.sort(key=lambda e: (e["date"], e["heure"]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True, help="dossier ~/.claude/projects/<slug>")
    ap.add_argument("--date", help="un seul jour (ISO)")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--projet", default="")
    a = ap.parse_args()
    since = a.date or a.since
    until = a.date or a.until
    d = Path(os.path.expanduser(a.project_dir))
    files = sorted(str(p) for p in d.glob("*.jsonl"))
    for e in collect(files, since, until):
        if a.projet:
            e["projet"] = a.projet
        sys.stdout.write(json.dumps(e, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
