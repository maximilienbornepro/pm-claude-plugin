#!/usr/bin/env python3
"""console - sert EN DIRECT, sur localhost, deux consoles de gestion (DM-022).

Contrairement à l'artefact (figé), cette console lit l'état à chaque requête :

  /        la console du PLUGIN  : commandes (pm list), templates, décisions, modifications par jour (git) ;
  /projet  la console du PROJET  : activité par jour (usage.log du projet) + état des portes (gate).

Deux interfaces distinctes : le plugin (générique, portable) d'un côté ; le projet qui l'appelle de l'autre.
Stdlib uniquement (http.server), identité Adservio. Lecture seule : il n'écrit rien.

    pm run console [--mission sinbad] [--port 8765]
"""
import argparse
import collections
import html
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "gate"))
import templates as TPL          # noqa: E402

CSS = """
:root{color-scheme:light;--blanc:#fff;--neige:#f5f5f7;--bordure:#e8e8e8;--noir:#1d1d1f;--corps:#6e6e73;
--tertiaire:#86868b;--royal:#0033ff;--sky:#38b6ff;--corail:#ff5757;--voile:rgba(0,51,255,.06);
--ombre:0 1px 2px rgba(29,29,31,.04),0 10px 30px rgba(29,29,31,.06);
--sans:-apple-system,BlinkMacSystemFont,system-ui,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
*{box-sizing:border-box}body{background:var(--blanc);color:var(--corps);font-family:var(--sans);
line-height:1.6;font-weight:400;-webkit-font-smoothing:antialiased;margin:0}
.wrap{max-width:900px;margin:0 auto;padding:28px 16px 72px}
.nav{display:flex;gap:6px;margin-bottom:22px}
.nav a{font-size:12.5px;font-weight:600;color:var(--corps);text-decoration:none;padding:7px 13px;border-radius:9px;background:var(--neige)}
.nav a.on{background:var(--royal);color:#fff}
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--tertiaire);margin:0 0 10px}
h1{font-size:27px;font-weight:700;letter-spacing:-.03em;color:var(--noir);margin:0}
.ver{font-size:12px;font-weight:600;color:var(--royal);background:var(--voile);border-radius:999px;padding:3px 11px;margin-left:8px;vertical-align:3px}
.live{font-size:11px;color:#1d9e75;font-weight:600;margin-left:8px}
.lede{color:var(--corps);font-size:14.5px;font-weight:300;margin:9px 0 0;max-width:66ch}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0 0}
@media(max-width:620px){.tiles{grid-template-columns:1fr 1fr}}
.tile{background:var(--neige);border-radius:12px;padding:13px 15px}
.tile .n{font-size:24px;font-weight:700;color:var(--noir);letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.tile .l{font-size:12px;color:var(--corps);margin-top:2px}
section{margin-top:40px}h2{font-size:19px;font-weight:700;letter-spacing:-.02em;color:var(--noir);margin:0 0 4px}
.sub{color:var(--corps);font-size:14px;font-weight:300;max-width:70ch;margin:5px 0 0}
.day{border:1px solid var(--bordure);border-radius:13px;box-shadow:var(--ombre);padding:13px 15px;margin:10px 0 0}
.day .h{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:7px}
.day .d{font-weight:700;color:var(--noir);font-size:15px}.day .cnt{margin-left:auto;font-size:11px;color:var(--tertiaire)}
.item{font-size:13px;color:var(--noir);padding:3px 0 3px 14px;position:relative}
.item::before{content:"";position:absolute;left:3px;top:11px;width:4px;height:4px;border-radius:50%;background:var(--royal)}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{font-size:12px;color:var(--noir);background:var(--neige);border:1px solid var(--bordure);border-radius:999px;padding:3px 9px}
.chip b{color:var(--royal);font-weight:600;margin-left:3px}
.fam{border:1px solid var(--bordure);border-radius:12px;box-shadow:var(--ombre);padding:12px 15px;margin:10px 0 0}
.fam .t{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--tertiaire);margin:0 0 8px}
.cmds{display:flex;flex-wrap:wrap;gap:6px}
.cmd{font-size:12.5px;color:var(--noir);background:var(--neige);border-radius:8px;padding:4px 10px}
.cmd.w{box-shadow:inset 3px 0 0 var(--corail)}
.grow{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--noir);padding:5px 0;border-bottom:1px solid var(--bordure)}
.gpct{font-variant-numeric:tabular-nums;font-weight:600;min-width:42px}
.foot{margin-top:38px;padding-top:16px;border-top:1px solid var(--bordure);font-size:12px;color:var(--tertiaire)}
"""

FAMILIES = [
    ("Amorcage", ["init", "setup", "preflight", "drive-scaffold", "notion-scaffold"]),
    ("Pilotage en donnee", ["method", "gate", "trace-audit", "cockpit", "templates"]),
    ("Livrables", ["projection", "deck-gate", "risks", "raci", "archi", "poc", "partner-report", "activity"]),
    ("Jira & audits", ["jira-images", "jira-changes-audit", "jira-sprints-audit", "notion-topics-audit", "docs-coherence-audit", "transcripts"]),
    ("Office & transverse", ["office", "tones", "agent", "reset"]),
]


def _pm():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_pm", ROOT / "framework" / "pm.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def plugin_days():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--since=2026-10-01",
                              "--pretty=format:%ad|%s", "--date=format:%Y-%m-%d"],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return []
    days = collections.OrderedDict()
    for line in out.splitlines():
        if "|" not in line:
            continue
        d, s = line.split("|", 1)
        if s.startswith("Publication"):          # on garde les étapes, pas les bumps de version
            continue
        days.setdefault(d, []).append(s)
    return list(days.items())


def project_days(project_root):
    log = Path(project_root) / ".claude" / "usage.log"
    if not log.exists():
        return []
    byday = collections.defaultdict(collections.Counter)
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        day = str(d.get("ts") or d.get("time") or "")[:10]
        name = d.get("name") or d.get("tool") or "?"
        if day:
            byday[day][name] += 1
    return sorted(byday.items(), reverse=True)


def gates_overview(mission):
    try:
        import gate as G
        gs = G.load_gates(mission)
        import method as M
        sd = M.seuil(mission, "gate_defaut", 90)
        out = []
        for g in gs:
            r = G.evaluate(g, default_seuil=sd)
            flag = "acte manquant" if (r["seuil_atteint"] and not r["acte_ok"]) else (
                "bloquant" if r["bloquants_ouverts"] else ("franchie" if r["franchie"] else ""))
            out.append((str(g.get("id")), g.get("name", ""), r["pct"], flag))
        return out
    except Exception:
        return []


def page_plugin():
    pm = _pm()
    gen = pm.GEN
    ndm = 0
    try:
        ndm = (ROOT / "DECISIONS.md").read_text(encoding="utf-8").count("\n## DM-")
    except Exception:
        pass
    ver = "?"
    try:
        ver = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    except Exception:
        pass
    tiles = [(str(len(gen)), "commandes pm run"), (str(sum(len(v) for v in TPL.catalog().values())), "templates"),
             (str(ndm), "decisions (DM)"), (ver, "version")]
    days = "".join(
        f'<div class="day"><div class="h"><span class="d">{html.escape(d)}</span>'
        f'<span class="cnt">{len(items)} changements</span></div>' +
        "".join(f'<div class="item">{html.escape(s)}</div>' for s in items) + "</div>"
        for d, items in plugin_days())
    fams = "".join(
        f'<div class="fam"><p class="t">{html.escape(fam)}</p><div class="cmds">' +
        "".join(f'<span class="cmd {"w" if (c in gen and not gen[c][2]) else ""}">{html.escape(c)}</span>'
                for c in cmds) + "</div></div>"
        for fam, cmds in FAMILIES)
    body = (f'<p class="eyebrow">console / le plugin</p>'
            f'<h1>pm-framework, console<span class="ver">v{html.escape(ver)}</span><span class="live">en direct</span></h1>'
            f'<p class="lede">Le moteur, generique et portable. Lu en direct a chaque ouverture. '
            f'Le travail sur un projet est dans la console du projet.</p>'
            f'<div class="tiles">' + "".join(
                f'<div class="tile"><div class="n">{html.escape(n)}</div><div class="l">{html.escape(l)}</div></div>'
                for n, l in tiles) + '</div>'
            f'<section><h2>Modifications du plugin</h2><p class="sub">Les etapes de construction, par jour (git). '
            f'En direct.</p>{days}</section>'
            f'<section><h2>Catalogue</h2><p class="sub">Les commandes pm run, par famille.</p>{fams}</section>'
            f'<div class="foot">Lu en direct depuis le git du plugin et pm.py. Console du projet : <a href="/projet">/projet</a>.</div>')
    return _shell("plugin", body)


def page_projet(mission, project_root):
    pdays = project_days(project_root)
    gov = gates_overview(mission)
    nact = sum(sum(c.values()) for _, c in pdays)
    tiles = [(mission, "mission"), (str(len(pdays)), "jours d'activite"),
             (str(nact), "actions tracees"), (str(len(gov)), "portes (gates)")]
    days = "".join(
        f'<div class="day"><div class="h"><span class="d">{html.escape(d)}</span>'
        f'<span class="cnt">{sum(c.values())} actions</span></div><div class="chips">' +
        "".join(f'<span class="chip">{html.escape(n)}<b>x{k}</b></span>' for n, k in c.most_common()) +
        "</div></div>"
        for d, c in pdays)
    if not pdays:
        days = '<p class="sub">Aucune activite dans .claude/usage.log (le hook journal_usage ne l\'a pas encore alimente ici).</p>'
    grows = "".join(
        f'<div class="grow"><span class="gpct">{(str(pct)+"%") if pct is not None else "-"}</span>'
        f'<span>{html.escape(gid)} {html.escape(nm)}</span>'
        f'<span style="margin-left:auto;color:var(--tertiaire);font-size:12px">{html.escape(fl)}</span></div>'
        for gid, nm, pct, fl in gov) or '<p class="sub">Pas de portes declarees (gate.yml) pour cette mission.</p>'
    body = (f'<p class="eyebrow">console / le projet</p>'
            f'<h1>{html.escape(mission)}, console projet<span class="live">en direct</span></h1>'
            f'<p class="lede">Le travail sur le projet qui appelle le plugin. Active par jour (hook d\'usage) '
            f'et etat des portes, lus en direct.</p>'
            f'<div class="tiles">' + "".join(
                f'<div class="tile"><div class="n">{html.escape(n)}</div><div class="l">{html.escape(l)}</div></div>'
                for n, l in tiles) + '</div>'
            f'<section><h2>Activite par jour</h2><p class="sub">Skills et agents lances sur le projet '
            f'(.claude/usage.log).</p>{days}</section>'
            f'<section><h2>Portes (gates)</h2><p class="sub">Etat calcule des portes de la mission.</p>{grows}</section>'
            f'<div class="foot">Lu en direct depuis usage.log et gate.yml. Console du plugin : <a href="/">/</a>.</div>')
    return _shell("projet", body)


def _shell(active, body):
    nav = (f'<div class="nav"><a href="/" class="{"on" if active=="plugin" else ""}">Plugin</a>'
           f'<a href="/projet" class="{"on" if active=="projet" else ""}">Projet</a></div>')
    title = "pm-framework, console" if active == "plugin" else "Projet, console"
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>{CSS}</style></head><body><div class="wrap">{nav}{body}</div></body></html>')


def make_handler(mission, project_root):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            path = self.path.split("?")[0]
            try:
                html_doc = page_projet(mission, project_root) if path.rstrip("/") == "/projet" else page_plugin()
                data = html_doc.encode("utf-8")
            except Exception as e:  # fail-soft : jamais de 500 opaque
                data = f"<pre>erreur console : {html.escape(str(e))}</pre>".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mission", default="sinbad")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--project-root", default=str(Path.cwd()),
                    help="racine du projet (pour .claude/usage.log) ; defaut : repertoire courant")
    args = ap.parse_args()
    srv = HTTPServer(("127.0.0.1", args.port), make_handler(args.mission, args.project_root))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Console pm-framework EN DIRECT : {url}  (plugin)   et   {url}projet  (projet {args.mission})")
    print("  Ctrl-C pour arreter. Lecture seule : rien n'est ecrit.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\narrete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
