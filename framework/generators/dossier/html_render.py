#!/usr/bin/env python3
"""dossier/html - dossier projet en page HTML (pile de slides 16:9) depuis UNE source, dossier.json.

Même source que l'export PowerPoint (dossier.py), même charte que la maquette validée
(docs/maquette/index.html) : la CSS de la maquette est reprise telle quelle, chaque `kind` de slide
produit le même balisage que la maquette. Un sommaire est inséré juste après la couverture.

Usage :
  html_render.py <mission> -o <dossier>            écrit <dossier>/index.html (+ <dossier>/logos/)
  html_render.py <mission> -o <dossier> --input f  source autre que profiles/<mission>/dossier/dossier.json

Écrit UNIQUEMENT dans le dossier demandé, en local. Lecture seule vis-à-vis de la mission.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ── Colour tokens: mirror of framework/lib/slides.py (C, LEVEL, PILL, STATUS, RACI, HEAT). ──────────
# Kept local so the HTML export does not need python-pptx; keep both in sync.
C = {
    "noir": "0B0B0B", "ivoire": "F7F4EF", "blanc": "FFFFFF", "encre": "1A1A1A", "gris": "8A8580",
    "filet": "D9D3CA", "voile": "ECE6DD", "sable": "E9DFD1", "taupe": "B7A99A", "sauge": "A9B5A0",
    "ardoise": "5E6670", "bordeaux": "7A1F23", "or": "B8975A", "texte": "4A4643", "cap": "5A5550",
    "voile2": "F1ECE5", "e1": "F0EBE3",
}
CSS_VARS = {"noir", "ivoire", "blanc", "encre", "gris", "filet", "voile", "sable", "taupe", "sauge",
            "ardoise", "bordeaux", "or"}
STATUS = {"v": "7E9A6E", "j": "D9B44A", "o": "C9803A", "r": C["bordeaux"]}
RACI = {"R": "noir", "A": "bordeaux", "C": "sable", "I": "voile"}
DARK_FILLS = {"noir", "bordeaux", "ardoise"}

# ── Charter: CSS of docs/maquette/index.html, verbatim ─────────────────────────────────────────────
CHARTER_CSS = r"""
  /* ── Design tokens: single source for HTML and PPTX export ─────────────── */
  :root {
    --noir: #0B0B0B; --ivoire: #F7F4EF; --blanc: #FFFFFF; --encre: #1A1A1A;
    --gris: #8A8580; --filet: #D9D3CA; --voile: #ECE6DD;
    --sable: #E9DFD1; --taupe: #B7A99A; --sauge: #A9B5A0; --ardoise: #5E6670;
    --bordeaux: #7A1F23; --or: #B8975A;
    --sans: "Helvetica Neue", "Avenir Next", "Segoe UI", Arial, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-padding-top: 24px; }
  .slide:target { outline: 2px solid #B8975A; outline-offset: 6px; }
  body { background: #2a2a2a; font-family: var(--sans); padding: 32px 0 64px; }
  .note { max-width: 1100px; margin: 0 auto 28px; color: #cfcac3; font: 300 14px/1.6 var(--sans); }
  .note b { color: #fff; font-weight: 500; }

  /* One slide = one 16:9 frame, sized in cqw so it scales exactly */
  .slide { position: relative; width: min(1100px, 94vw); aspect-ratio: 16 / 9; margin: 0 auto 28px;
    container-type: inline-size; overflow: hidden; background: var(--ivoire); color: var(--encre);
    box-shadow: 0 10px 40px rgba(0,0,0,.35); }
  .foot { position: absolute; left: 4cqw; right: 4cqw; bottom: 2.4cqw; display: flex; justify-content: space-between;
    font: 300 0.98cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--gris); }
  .foot .src { color: var(--encre); text-decoration: none; letter-spacing: .02em; text-transform: none; font-weight: 300; border-bottom: 1px solid var(--or); }
  .logo-c { position: absolute; top: 3.2cqw; right: 4cqw; height: 1.15cqw; opacity: .9; }
  .logo-n { position: absolute; top: 3.4cqw; left: 8cqw; height: 4.2cqw; }

  /* Black section slides, white type */
  .noire { background: var(--noir); color: var(--blanc); display: flex; flex-direction: column; justify-content: center; padding: 0 8cqw; }
  .noire .kicker { font: 300 1.15cqw var(--sans); letter-spacing: .02em; text-transform: none; color: #9a948c; margin-bottom: 2.6cqw; }
  .noire h1 { font: 200 5.0cqw/1.1 var(--sans); letter-spacing: .01em; text-transform: none; }
  .noire .rule { width: 6cqw; height: 1px; background: var(--or); margin: 3cqw 0 2.2cqw; }
  .noire .sub { font: 200 1.5cqw var(--sans); letter-spacing: .02em; color: #d8d2ca; }
  .noire .foot { color: #6d6862; }
  .noire .num { position: absolute; right: 8cqw; top: 50%; transform: translateY(-50%); font: 100 16cqw var(--sans); color: #1f1f1f; }
  .cover { align-items: center; text-align: center; padding: 0; }
  .cover .big { height: 10cqw; margin-bottom: 4cqw; }
  .cover h1 { font-size: 4.2cqw; letter-spacing: .04em; }
  .cover .rule { margin: 2.6cqw auto 2cqw; }

  /* Content slides */
  .content { padding: 4.4cqw 6cqw 6cqw; }
  .eyebrow { font: 300 1.09cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--gris); }
  .title { font: 200 2.4cqw/1.15 var(--sans); margin: .8cqw 0 0; }
  .cap { font: 200 .98cqw/1.55 var(--sans); color: #5a5550; max-width: 82cqw; margin-top: .9cqw; }
  .lead { font: 200 1.3cqw/1.5 var(--sans); color: #4a4643; }
  .grid { display: grid; gap: 2.4cqw; margin-top: 2.4cqw; }
  b, strong { font-weight: 400; }

  /* Tables */
  table.t { width: 100%; border-collapse: collapse; margin-top: 2.2cqw; }
  .t th { font: 400 0.86cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--gris); text-align: left; padding: 0 .9cqw .9cqw; border-bottom: 1px solid var(--encre); white-space: nowrap; }
  .t td { font: 300 1cqw/1.35 var(--sans); padding: .85cqw .9cqw; border-bottom: 1px solid var(--filet); vertical-align: top; }
  .t td.k { color: var(--gris); letter-spacing: .15em; white-space: nowrap; }
  .t td.n, .t th.n { text-align: right; font-variant-numeric: tabular-nums; }
  .t tr.tot td { border-top: 1px solid var(--encre); border-bottom: none; font-weight: 400; }
  .t.small td { font-size: .92cqw; padding: .7cqw .8cqw; }
  .dot { display: inline-block; width: .8cqw; height: .8cqw; margin-right: .6cqw; vertical-align: middle; }
  .pill { display: inline-block; font: 400 0.83cqw var(--sans); letter-spacing: .02em; text-transform: none; padding: .4cqw .8cqw; white-space: nowrap; }

  /* Levels / statuses: flat colour blocks */
  .l1 { background: #EEE8DF; } .l2 { background: var(--sable); } .l3 { background: var(--taupe); } .l4 { background: var(--bordeaux); color: #fff; }
  .s-ok { background: var(--sauge); } .s-cours { background: var(--sable); } .s-risque { background: var(--taupe); }
  .s-bloque { background: var(--bordeaux); color: #fff; } .s-afaire { background: var(--voile); } .s-fait { background: var(--noir); color: #fff; }

  /* Risk matrix */
  .matrix { display: grid; grid-template-columns: 3cqw repeat(4, 1fr); grid-template-rows: repeat(4, 1fr) 2.6cqw; gap: .35cqw; height: 26cqw; }
  .matrix .cell { display: flex; align-items: center; justify-content: center; gap: .5cqw; }
  .matrix .ax { font: 300 0.92cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--gris); display: flex; align-items: center; justify-content: center; }
  .matrix .ay { writing-mode: vertical-rl; transform: rotate(180deg); }
  .chip { display: inline-flex; align-items: center; justify-content: center; min-width: 2.6cqw; height: 2.6cqw; border-radius: 50%; background: var(--blanc); color: var(--encre); font: 400 .8cqw var(--sans); }
  .toplist { list-style: none; }
  .toplist li { display: grid; grid-template-columns: 4cqw 1fr auto; align-items: baseline; gap: 1.2cqw; padding: 1.15cqw 0; border-bottom: 1px solid var(--filet); }
  .toplist .id { font: 300 .9cqw var(--sans); letter-spacing: .2em; color: var(--gris); }
  .toplist .lb { font: 300 1.25cqw/1.35 var(--sans); }
  .toplist .lb small { display: block; font: 200 .9cqw/1.4 var(--sans); color: var(--gris); margin-top: .3cqw; }

  /* KPIs, bars, tiles */
  .kpi { font: 100 12cqw/.85 var(--sans); letter-spacing: -.03em; }
  .kpi sup { font: 200 3cqw var(--sans); vertical-align: top; margin-left: .4cqw; }
  .bars .row { display: grid; grid-template-columns: 9cqw 1fr 5cqw; align-items: center; gap: 1.4cqw; margin: 1.2cqw 0; }
  .bars .lbl { font: 300 1.09cqw var(--sans); letter-spacing: .02em; text-transform: none; }
  .bars .track { height: 2cqw; background: var(--voile); position: relative; }
  .bars .fill { position: absolute; inset: 0 auto 0 0; }
  .bars .mark { position: absolute; top: -.5cqw; bottom: -.5cqw; width: 1px; background: var(--bordeaux); }
  .bars .val { font: 200 1.5cqw var(--sans); text-align: right; }
  .tiles { display: grid; gap: 0; }
  .tile { padding: 2cqw 2cqw; display: flex; flex-direction: column; justify-content: space-between; min-height: 11cqw; }
  .tile .k { font: 400 0.86cqw var(--sans); letter-spacing: .02em; text-transform: none; }
  .tile .v { font: 100 4.6cqw/1 var(--sans); }
  .tile .s { font: 200 .9cqw var(--sans); }
  .legend { display: flex; gap: 2.4cqw; font: 300 0.98cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--gris); margin-top: 1cqw; }
  .legend i { display: inline-block; width: 1.6cqw; height: 2px; vertical-align: middle; margin-right: .6cqw; }

  svg text { font-family: var(--sans); font-weight: 300; }

  /* Columns (weekly, CR) */
  .cols { display: grid; gap: 2.6cqw; margin-top: 2.6cqw; }
  .col h3 { font: 400 0.92cqw var(--sans); letter-spacing: .02em; text-transform: none; padding-bottom: .9cqw; border-bottom: 1px solid var(--encre); margin-bottom: 1cqw; }
  .col ul { list-style: none; }
  .col li { font: 300 1.02cqw/1.45 var(--sans); padding: .55cqw 0; border-bottom: 1px solid var(--filet); }
  .col li small { color: var(--gris); font-weight: 200; }

  /* RACI */
  .raci td.r { text-align: center; font: 400 1cqw var(--sans); padding: .75cqw 0; }
  .raci .R { background: var(--noir); color: #fff; } .raci .A { background: var(--bordeaux); color: #fff; }
  .raci .C { background: var(--sable); } .raci .I { background: var(--voile); color: var(--gris); }

  /* Weather cards (technical follow-up) */
  .meteo { display: grid; grid-template-columns: repeat(5, 1fr); gap: .5cqw; margin-top: 2.4cqw; }
  .dom { padding: 1.6cqw 1.4cqw; min-height: 9.5cqw; display: flex; flex-direction: column; justify-content: space-between; }
  .dom .k { font: 400 0.86cqw var(--sans); letter-spacing: .02em; text-transform: none; }
  .dom .v { font: 200 1.05cqw/1.35 var(--sans); }
  .stack { display: flex; height: .6cqw; margin-top: .9cqw; }
  /* Weekly (mirror of the Notion block): nested bullets by theme */
  .wk { display: grid; grid-template-columns: 1.25fr 1fr 1.15fr; gap: 2.6cqw; margin-top: 1.8cqw; }
  .wk h3 { font: 400 0.92cqw var(--sans); letter-spacing: .02em; text-transform: none; padding-bottom: .8cqw; border-bottom: 1px solid var(--encre); margin-bottom: .7cqw; }
  .wk ul { list-style: none; }
  .wk > div > ul > li { font: 300 1.12cqw/1.45 var(--sans); padding: .6cqw 0; }
  .wk ul ul li { font: 200 1.06cqw/1.45 var(--sans); padding: .12cqw 0 .12cqw 1.3cqw; position: relative; }
  .wk ul ul li::before { content: "–"; position: absolute; left: 0; color: var(--gris); }
  /* Partner report (mirror of the partner-report mail) */
  .mail { margin-top: 1.4cqw; font: 300 1.08cqw/1.5 var(--sans); }
  .mail .obj { font: 400 1.05cqw var(--sans); padding-bottom: .8cqw; border-bottom: 1px solid var(--encre); margin-bottom: .8cqw; }
  .mail .obj span { display: block; font: 300 0.83cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--gris); margin-bottom: .3cqw; }
  .mail > p { margin: .35cqw 0; }
  .mail .subj { display: grid; grid-template-columns: 1fr 1fr; gap: 1.3cqw 2.6cqw; margin: 1.2cqw 0; }
  .mail h4 { font: 400 1.12cqw var(--sans); margin-bottom: .2cqw; }
  .mail .subj p { margin: 0; }
  /* Inter-team responsibilities and staffing */
  .inter td.own { background: var(--sable); }
  .staff th, .staff td { text-align: center; }
  .staff th:first-child, .staff td:first-child { text-align: left; }
  .staff th.cur { background: var(--noir); color: #fff; padding: .75cqw .9cqw; vertical-align: middle; }
  .staff td:nth-child(3) { box-shadow: inset 2px 0 0 var(--noir), inset -2px 0 0 var(--noir); }
  .staff tr.tbd td:first-child { color: var(--bordeaux); }
  .staff th:nth-child(n+3) { width: 14%; }
  .staff td.k { text-align: left; }
  .staff th:nth-child(2), .staff td:nth-child(2) { text-align: left; }
  .staff tr.ph td { font: 300 0.9cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--gris); border-bottom: 1px solid var(--filet); padding-top: .5cqw; }
  .staff tr.ph td.cur { background: var(--noir); color: #fff; }
  .staff td { padding: .42cqw .8cqw; }
  .staff .e0 { color: var(--gris); } .staff .e1 { background: #F0EBE3; } .staff .e2 { background: var(--sable); }
  .staff .e3 { background: var(--taupe); } .staff .e4 { background: var(--ardoise); color: #fff; }
  .staff tr.tot2 td { border-bottom: none; color: var(--gris); }
  /* Workstreams (mirror of the project dashboard "Build workstreams" slide) */
  .chant { margin-top: 1.4cqw; }
  .chant td { font-size: .95cqw; padding: .62cqw .6cqw; vertical-align: middle; }
  .chant th { padding-bottom: .6cqw; }
  .chant td.k2 { color: #4a4643; white-space: nowrap; }
  .chant td.cm { font-weight: 200; color: #3a3633; }
  .chant td:nth-child(5) { white-space: nowrap; width: 11cqw; }
  .pbar { display: inline-block; vertical-align: middle; width: 6.4cqw; height: .85cqw; background: var(--voile); position: relative; margin-right: .6cqw; }
  .pbar span { position: absolute; inset: 0 auto 0 0; background: var(--encre); }
  .pc { font-variant-numeric: tabular-nums; }
  .st { display: inline-block; width: .95cqw; height: .95cqw; border-radius: 50%; vertical-align: middle; }
  .prio { color: var(--or); font-size: .9em; }
  .legend.chl { margin-top: 1.2cqw; gap: 1.8cqw; font-size: .75cqw; }
  .legend.chl .st { margin-right: .5cqw; width: .8cqw; height: .8cqw; }
  /* Architecture macro view: golden SVG vocabulary, dossier skin */
  .archi-svg { --bg:#F7F4EF;--surface:#FFFFFF;--s2:#F1ECE5;--ink:#1A1A1A;--muted:#8A8580;--line:#D9D3CA;--sai:#1A1A1A;--sai-bg:#ECE6DD;--grn:#6E8B63;--grn-bg:#EEF1EA;--ext:#8A8580;--ext-bg:#F1ECE5;--air:#5E6670;--air-bg:#ECEEF0;--ksatc:#7E9A6E;--ksat-bg:#EEF1EA;--kc:#7A1F23;--kc-bg:#F3E7E7;--iceye:#5E6670;--iceye-bg:#ECEEF0;--s3:#B8975A;--rds:#8C7B69;--amb:#B8975A;--soc:#7A1F23; }
  .archi-svg text { font-family: var(--sans, "Helvetica Neue", Arial, sans-serif); }
  .archi-svg .t { fill: var(--ink); font-weight: 400; font-size: 15px; } .archi-svg .tm { fill: var(--ink); font-weight: 400; font-size: 13.5px; }
  .archi-svg .s { fill: var(--muted); font-size: 12px; font-weight: 300; } .archi-svg .lbl { fill: var(--muted); font-size: 11px; font-weight: 300; letter-spacing: .06em; }
  .archi-svg rect.bg, .archi-svg .box { fill: var(--surface); stroke: var(--line); stroke-width: 1; }
  .archi-svg .zone { fill: var(--s2); stroke: var(--line); stroke-dasharray: 5 5; }
  .archi-svg .arr { stroke: var(--muted); stroke-width: 1.6; fill: none; } .archi-svg .flow { stroke: var(--sai); stroke-width: 2; fill: none; stroke-dasharray: 7 7; }
  .archi-svg .api { stroke: var(--sai); stroke-width: 3; fill: none; } .archi-svg .auth { stroke: var(--kc); stroke-width: 2.2; fill: none; stroke-dasharray: 3 4; }
  .archi-svg .zoom { display: none; }
  .archi-link { display: inline-block; margin-top: .6cqw; font: 300 0.92cqw var(--sans); letter-spacing: .02em; text-transform: none; color: var(--encre); text-decoration: none; border-bottom: 1px solid var(--or); }
"""

# Additions for generated-only blocks (agenda, fitted charts, generic cells). Charter values only.
EXTRA_CSS = r"""
  /* Generated page: no hand-written note above the deck */
  /* Slides whose chart must fill the remaining height without overflowing the frame */
  .fit { display: flex; flex-direction: column; }
  .fit > * { flex: none; }
  .fit > .grow { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; }
  .fit > .grow > svg { flex: 1 1 auto; min-height: 0; width: 100%; height: 100%; display: block; }
  .fit > .archi-link { align-self: flex-start; }
  .t td.cm { font-weight: 200; color: #3a3633; }
  .t td.c, .t th.c { text-align: center; }
  .legend .dot { margin-right: .6cqw; }
  .legend .st { margin-right: .5cqw; }
  .legend .bdg { display: inline-block; width: .9cqw; height: .9cqw; border-radius: 50%; background: var(--noir); vertical-align: middle; margin-right: .6cqw; }
  /* Agenda (sommaire) */
  .agenda { display: grid; gap: 2.4cqw 2.6cqw; margin-top: 3.2cqw; align-items: start; }
  .agenda h3 { font: 400 0.92cqw var(--sans); letter-spacing: .02em; text-transform: none; padding-bottom: .8cqw; border-bottom: 1px solid var(--encre); margin-bottom: .5cqw; }
  .agenda h3 a { color: var(--encre); text-decoration: none; }
  .agenda h3 .n { color: var(--or); margin-right: .9cqw; letter-spacing: .02em; }
  .agenda ul { list-style: none; }
  .agenda li { font: 300 1.02cqw/1.4 var(--sans); padding: .45cqw 0; border-bottom: 1px solid var(--filet); }
  .agenda li a { color: var(--encre); text-decoration: none; }
  .agenda li a:hover, .agenda h3 a:hover { border-bottom: 1px solid var(--or); }
"""

FILE_EXT = re.compile(r"\.[A-Za-z0-9]{1,6}$")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── small helpers ─────────────────────────────────────────────────────────────────────────────────
def esc(t) -> str:
    # Local escape: this module is named html.py, so the stdlib `html` cannot be imported when run as a script.
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#x27;"))


def rich(t) -> str:
    """Escaped text with **bold** -> <b>, newlines -> <br>."""
    parts = re.split(r"\*\*", esc(t))
    out = "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))
    return out.replace("\n", "<br>")


def hexc(name) -> str:
    """Colour token or raw hex -> '#RRGGBB' (for SVG attributes)."""
    if not name:
        return "none"
    return "#" + C.get(name, str(name).lstrip("#"))


def cssc(name) -> str:
    """Colour token -> CSS value (var(--x) when the charter declares it)."""
    return f"var(--{name})" if name in CSS_VARS else hexc(name)


def fg_of(fill) -> str:
    return "#fff" if fill in DARK_FILLS else "var(--encre)"


def pct(v) -> str:
    return f"{float(v):.4g}%"


def num(v) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


# ── agenda ────────────────────────────────────────────────────────────────────────────────────────
def _section_title(sl) -> str:
    return " ".join(sl.get("title", "").split("\n")).strip()


def slide_ids(deck) -> list:
    """Stable id per slide (same scheme as pptx_render.slide_ids): its `id`, else cover / section-<k>."""
    out, k = [], 0
    for sl in deck["slides"]:
        if sl.get("id"):
            out.append(sl["id"])
        elif sl["kind"] == "cover":
            out.append("cover")
        else:
            k += 1
            out.append(f"section-{k}")
    return out


def _agenda_full(deck):
    """[(section_title, num, section_anchor, [(slide_id, title)])] ; empty groups are dropped."""
    out, cur = [], ["Synthèse", "", None, []]
    for sid, sl in zip(slide_ids(deck), deck["slides"]):
        if sl["kind"] == "cover":
            continue
        if sl["kind"] == "section":
            if cur[3]:
                out.append(tuple(cur))
            cur = [_section_title(sl), sl.get("num", ""), sid, []]
        else:
            cur[3].append((sid, sl.get("title", "")))
    if cur[3]:
        out.append(tuple(cur))
    return out


def agenda(deck) -> list:
    """Sections of the deck in order, each with its content slides.

    Returns [(section_title, num, [(slide_id, title)])]. Content slides placed before the first
    section slide go under a pseudo-section "Synthèse" (num ""). Same output as
    pptx_render.agenda (mirrored here so the HTML export does not need python-pptx).
    """
    return [(t, n, items) for t, n, _, items in _agenda_full(deck)]


# ── legend ────────────────────────────────────────────────────────────────────────────────────────
def legend_html(items, cls="legend", style="", titles=None):
    out = []
    for kind, label in items:
        k, _, v = (kind or "").partition(":")
        if k == "st":
            mark = f'<span class="st" style="background:#{STATUS[v]}"></span>'
        elif k == "pill":
            mark = f'<span class="dot s-{esc(v)}"></span>'
        elif k == "raci":
            mark = f'<span class="dot" style="background:{cssc(RACI[v])}"></span>'
        elif k == "line":
            mark = f'<i style="background:{hexc(v)}"></i>'
        elif k == "dash":
            mark = f'<i style="background:repeating-linear-gradient(90deg,{hexc(v)} 0 2px,transparent 2px 6px)"></i>'
        elif k == "star":
            mark = '<span class="prio">★</span>'
        elif k == "badge":
            mark = '<span class="bdg"></span>'
        else:
            mark = ""
        out.append(f"<span>{mark}{esc(label)}</span>")
    st = f' style="{style}"' if style else ""
    return f'<div class="{cls}"{st}>{"".join(out)}</div>'


# ── tables ────────────────────────────────────────────────────────────────────────────────────────
def _heat_class(h) -> str:
    if h == 0:
        return "e0"
    if h <= .5:
        return "e1"
    if h <= 1:
        return "e2"
    return "e3" if h < 2 else "e4"


def cell_html(v, col, st_titles, tag="td", total=False):
    """One table cell from the JSON cell model (see dossier.py cell_of)."""
    if not isinstance(v, dict):
        v = {"t": "" if v is None else str(v)}
    t = v.get("t", "")
    classes, style = [], []
    align = v.get("align", col.get("align", "l"))
    if "pill" in v:
        inner = f'<span class="pill s-{esc(v["pill"])}">{esc(t)}</span>'
    elif "dot" in v:
        inner = f'<span class="dot {esc(v["dot"])}"></span>{rich(t)}'
    elif "raci" in v:
        r = v["raci"]
        classes += ["r", r]
        inner, align = esc(r), "raci"
    elif "heat" in v:
        classes.append(_heat_class(v["heat"]))
        inner = esc(t)
    elif "st" in v:
        title = st_titles.get(v["st"], "")
        tt = f' title="{esc(title)}"' if title else ""
        inner = f'<span class="st" style="background:#{STATUS[v["st"]]}"{tt}></span>'
    elif "bar" in v:
        inner = (f'<div class="pbar"><span style="width:{pct(v["bar"])}"></span></div>'
                 f'<span class="pc">{esc(v["bar"])} %</span>')
        align = "l"
    elif "stack" in v:
        spans = "".join(f'<span class="s-{esc(k)}" style="width:{pct(f * 100)}"></span>'
                        for k, f in v["stack"] if f > 0)
        inner, align = f'<div class="stack">{spans}</div>', "l"
    else:
        inner = rich(t)
        if v.get("star"):
            inner += ' <span class="prio" title="Priorité de la semaine">★</span>'
        if v.get("muted"):
            classes.append("k")
        elif v.get("light"):
            classes.append("cm")
        if v.get("c"):
            style.append(f"color:{cssc(v['c'])}")
    if align == "r":
        classes.append("n")
    elif align == "c":
        classes.append("c")
    cl = f' class="{" ".join(classes)}"' if classes else ""
    sty = f' style="{";".join(style)}"' if style else ""
    return f"<{tag}{cl}{sty}>{inner}</{tag}>"


def table_html(tab, small=False, style="", legend=None):
    cols = tab["cols"]
    rows = tab["rows"]
    flat = [c for r in rows for c in r if isinstance(c, dict)]
    cls = ["t"]
    if small:
        cls.append("small")
    if any("raci" in c for c in flat):
        cls.append("raci")
    if any("heat" in c for c in flat):
        cls.append("staff")
    if any("bar" in c or "st" in c for c in flat):
        cls.append("chant")
    st_titles = {k.partition(":")[2]: lab for k, lab in (legend or []) if k.startswith("st:")}
    cur = tab.get("current_col")
    out = [f'<table class="{" ".join(cls)}"' + (f' style="{style}"' if style else "") + ">"]
    out.append("<colgroup>" + "".join(f'<col style="width:{pct(c.get("w", 1 / len(cols)) * 100)}">' for c in cols)
               + "</colgroup>")
    if not tab.get("nohead"):
        ths = []
        for j, c in enumerate(cols):
            ccls = []
            if c.get("align") == "r":
                ccls.append("n")
            elif c.get("align") == "c":
                ccls.append("c")
            if cur is not None and j == cur:
                ccls.append("cur")
            dot = f'<span class="dot s-{esc(c["key"])}"></span>' if c.get("key") else ""
            cl = f' class="{" ".join(ccls)}"' if ccls else ""
            ths.append(f"<th{cl}>{dot}{esc(c.get('h', ''))}</th>")
        out.append("<thead><tr>" + "".join(ths) + "</tr></thead>")
    out.append("<tbody>")
    for r in rows:
        out.append("<tr>" + "".join(cell_html(v, cols[j], st_titles) for j, v in enumerate(r)) + "</tr>")
    for key, trc in (("total", "tot"), ("total2", "tot2")):
        if tab.get(key):
            out.append(f'<tr class="{trc}">' + "".join(cell_html(v, cols[j], st_titles) for j, v in enumerate(tab[key]))
                       + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


# ── charts (SVG) ──────────────────────────────────────────────────────────────────────────────────
def chart_svg(c, big=True, label="Burn-down en jours"):
    """Burn-down: axes in days, elapsed band, ideal / real / trend, today line + dot + label, markers."""
    if big:
        W, H, L, R, T, B, band = 1000, 330, 60, 970, 38, 290, 30
        fs, fs_today, fs_date, lw, rad, banner_y, tick_dy, date_dy = 11, 13, 10, 2.2, 5, 52, 20, 35
    else:
        W, H, L, R, T, B, band = 1000, 420, 60, 960, 20, 360, 20
        fs, fs_today, fs_date, lw, rad, banner_y, tick_dy, date_dy = 15, 17, 13, 3, 7, 45, 28, 50
    (x0, x1), (y0, y1) = c["x"], c["y"]

    def px(d):
        return L + (R - L) * (d - x0) / (x1 - x0)

    def py(v):
        return B - (B - T) * (v - y0) / (y1 - y0)

    def pts(seq):
        return " ".join(f"{num(px(a))},{num(py(b))}" for a, b in seq)

    ex = px(c["elapsed"])
    o = [f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" aria-label="{esc(label)}">']
    o.append(f'<rect x="{L}" y="{band}" width="{num(ex - L)}" height="{B - band}" fill="#ECE6DD" opacity=".55"/>')
    ls = 3
    if c.get("elapsed_label"):
        o.append(f'<text x="{num((L + ex) / 2)}" y="{banner_y}" text-anchor="middle" font-size="{fs if big else 14}" '
                 f'letter-spacing=".3" fill="#8A8580">{esc(c["elapsed_label"])}</text>')
    if c.get("remain_label"):
        o.append(f'<text x="{num((ex + R) / 2)}" y="{banner_y}" text-anchor="middle" font-size="{fs if big else 14}" '
                 f'letter-spacing=".3" fill="#8A8580">{esc(c["remain_label"])}</text>')
    o.append(f'<g stroke="#D9D3CA" stroke-width="1"><line x1="{L}" y1="{B}" x2="{R}" y2="{B}"/>'
             f'<line x1="{L}" y1="{T}" x2="{L}" y2="{B}"/></g>')
    o.append(f'<g font-size="{fs}" fill="#8A8580" letter-spacing=".3">')
    for v in c.get("yticks", []):
        o.append(f'<text x="{L - 10}" y="{num(py(v) + fs * .35)}" text-anchor="end">{esc(v)}</text>')
    for d, lab in c.get("xticks", []):
        o.append(f'<text x="{num(px(d))}" y="{B + tick_dy}" text-anchor="middle">{esc(lab)}</text>')
    for d, lab in c.get("xdates", []):
        o.append(f'<text x="{num(px(d))}" y="{B + date_dy}" text-anchor="middle" font-size="{fs_date}">{esc(lab)}</text>')
    o.append("</g>")
    if c.get("ideal"):
        o.append(f'<polyline points="{pts(c["ideal"])}" fill="none" stroke="#B7A99A" stroke-width="{1 if big else 1.2}" '
                 f'stroke-dasharray="{"4 6" if big else "5 7"}"/>')
    if c.get("real"):
        o.append(f'<polyline points="{pts(c["real"])}" fill="none" stroke="#0B0B0B" stroke-width="{lw}"/>')
    if c.get("trend"):
        o.append(f'<polyline points="{pts(c["trend"])}" fill="none" stroke="#0B0B0B" stroke-width="{1.2 if big else 1.5}" '
                 f'stroke-dasharray="{"2 5" if big else "2 6"}"/>')
    for i, v in enumerate(c.get("vlines", [])):
        X = px(v["x"])
        col = hexc(v.get("c", "encre"))
        tcol = hexc("ardoise") if v.get("c") == "sauge" else col
        o.append(f'<line x1="{num(X)}" y1="{band}" x2="{num(X)}" y2="{B}" stroke="{col}" stroke-width="1.2"/>')
        o.append(f'<text x="{num(X - 4)}" y="{76 + 20 * i}" text-anchor="end" font-size="{fs}" letter-spacing=".3" '
                 f'fill="{tcol}">{esc(v["label"])}</text>')
    t = c.get("today")
    if t:
        o.append(f'<line x1="{num(ex)}" y1="{band}" x2="{num(ex)}" y2="{B}" stroke="#7A1F23" stroke-width="1"/>')
        ty = py(t["y"])
        o.append(f'<circle cx="{num(ex)}" cy="{num(ty)}" r="{rad}" fill="#7A1F23"/>')
        o.append(f'<text x="{num(ex + 8 + (4 if not big else 0))}" y="{num(ty - 6 - (2 if not big else 0))}" '
                 f'font-size="{fs_today}" fill="#7A1F23">{esc(t["label"])}</text>')
    if c.get("end_label") and c.get("trend"):
        o.append(f'<text x="{R - 5}" y="{num(py(c["trend"][-1][1]) - 8)}" text-anchor="end" font-size="{fs}" '
                 f'fill="#5E6670">{esc(c["end_label"])}</text>')
    o.append("</svg>")
    return "".join(o)


def gantt_svg(g):
    gx, gw = 220, 752
    days = g["days"]
    lanes = g["lanes"]

    def px(d):
        return gx + gw * d / days

    top = 44
    bottom = top + 50 * len(lanes) + 6
    H = bottom + 30
    o = [f'<svg viewBox="0 0 1000 {H}" preserveAspectRatio="xMidYMid meet" aria-label="Gantt">']
    o.append('<g font-size="11" letter-spacing=".3" fill="#8A8580">')
    o += [f'<text x="{num(px(d))}" y="18">{esc(lab)}</text>' for d, lab in g.get("months", [])]
    o.append('</g><g stroke="#D9D3CA">')
    o += [f'<line x1="{num(px(d) - 10)}" y1="8" x2="{num(px(d) - 10)}" y2="{bottom}"/>' for d, _ in g.get("months", []) if d]
    o.append('</g><g font-size="10" fill="#8A8580">')
    o += [f'<text x="{num(px(d))}" y="36">{esc(lab)}</text>' for d, lab in g.get("weeks", [])]
    o.append('</g><g font-size="13" fill="#1A1A1A" letter-spacing=".3">')
    o += [f'<text x="0" y="{72 + 50 * i}">{esc(ln["n"])}</text>' for i, ln in enumerate(lanes)]
    o.append('</g><g stroke="#ECE6DD">')
    o += [f'<line x1="0" y1="{92 + 50 * i}" x2="980" y2="{92 + 50 * i}"/>' for i in range(len(lanes) - 1)]
    o.append("</g>")
    for i, ln in enumerate(lanes):
        y = 60 + 50 * i
        a, b, done = px(ln["a"]), px(ln["b"]), px(ln.get("done", ln["a"]))
        o.append(f'<rect x="{num(a)}" y="{y}" width="{num(b - a)}" height="18" fill="#E9DFD1"/>')
        if ln.get("done", ln["a"]) > ln["a"]:
            o.append(f'<rect x="{num(a)}" y="{y}" width="{num(done - a)}" height="18" fill="{hexc(ln.get("c", "noir"))}"/>')
    t = g.get("today")
    if t:
        X = px(t["d"])
        o.append(f'<line x1="{num(X)}" y1="{top}" x2="{num(X)}" y2="{bottom}" stroke="#7A1F23"/>')
        o.append(f'<text x="{num(X + 4)}" y="{bottom + 12}" font-size="11" fill="#7A1F23" letter-spacing=".3">'
                 f'{esc(t["label"])}</text>')
    for m in g.get("milestones", []):
        X = px(m["d"])
        col = hexc(m.get("c", "encre"))
        lab = m["label"]
        o.append(f'<rect x="{num(X - 5)}" y="{bottom + 5}" width="10" height="10" transform="rotate(45 {num(X)} {bottom + 10})" '
                 f'fill="{col}"/>')
        if X + 9 + len(lab) * 8.6 < 1000:
            o.append(f'<text x="{num(X + 9)}" y="{bottom + 28}" font-size="11" letter-spacing=".3" fill="{col}">{esc(lab)}</text>')
        else:
            o.append(f'<text x="{num(X - 12)}" y="{bottom + 28}" text-anchor="end" font-size="11" letter-spacing=".3" '
                     f'fill="{col}">{esc(lab)}</text>')
    o.append("</svg>")
    return "".join(o)


def milestones_svg(sl):
    o = ['<svg viewBox="0 0 1000 220" style="width:100%;margin-top:5cqw" aria-label="Frise des jalons">',
         '<line x1="20" y1="100" x2="980" y2="100" stroke="#1A1A1A" stroke-width="1"/>',
         f'<rect x="20" y="94" width="{num(960 * sl.get("elapsed", 0))}" height="12" fill="#1A1A1A"/>',
         '<g font-weight="300">']
    for it in sl["items"]:
        X = 20 + 960 * it["p"]
        col = hexc(it.get("c", "encre"))
        end = it["p"] > .9
        anchor = "end" if end else "middle"
        if it.get("shape") == "dot":
            mark = f'<circle cx="{num(X)}" cy="100" r="7" fill="{col}"/>'
        else:
            s = 18 if end else 14
            mark = (f'<rect x="{num(X - s / 2)}" y="{100 - s / 2}" width="{s}" height="{s}" '
                    f'transform="rotate(45 {num(X)} 100)" fill="{col}"/>')
        tx = 980 if end else X  # last milestone: labels end at the line end, clear of their neighbour
        o.append(f'<g>{mark}<text x="{num(tx)}" y="70" text-anchor="{anchor}" font-size="13" letter-spacing=".3" '
                 f'fill="#8A8580">{esc(it["top"])}</text><text x="{num(tx)}" y="150" text-anchor="{anchor}" '
                 f'font-size="18" fill="#1A1A1A">{esc(it["date"])}</text></g>')
    o.append("</g></svg>")
    return "".join(o)


def diagram_svg(g, uid, label="Schéma"):
    """Boxes / links / labels on a w x h canvas (same units as the JSON)."""
    W, H = g["w"], g["h"]
    o = [f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" aria-label="{esc(label)}"><defs>']
    for mid, colr in (("k", "#1A1A1A"), ("g", "#8A8580")):
        o.append(f'<marker id="{uid}-{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                 f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{colr}"/></marker>')
    o.append("</defs>")
    for ln in g.get("links", []):
        dash = ln.get("dash", False)
        colr = hexc(ln.get("c") or ("gris" if dash else "encre"))
        mk = f"{uid}-g" if dash else f"{uid}-k"
        p = " ".join(f"{num(a)},{num(b)}" for a, b in ln["p"])
        attrs = f'fill="none" stroke="{colr}" stroke-width="1"'
        if dash:
            attrs += ' stroke-dasharray="4 4"'
        if ln.get("start"):
            attrs += f' marker-start="url(#{mk})"'
        if ln.get("end"):
            attrs += f' marker-end="url(#{mk})"'
        o.append(f'<polyline points="{p}" {attrs}/>')
    o.append('<g font-size="11.5" fill="#5E6670">')
    o += [f'<text x="{num(x)}" y="{num(y)}">{esc(t)}</text>' for x, y, t in g.get("labels", [])]
    o.append("</g>")
    for b in g.get("boxes", []):
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        fill = b.get("fill")
        fg = hexc(b.get("color") or "encre")
        if b.get("outline"):
            o.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="{hexc(fill) if fill else "none"}" '
                     f'stroke="{fg}" stroke-width="1.2"/>')
        else:
            o.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="{hexc(fill) if fill else "none"}"/>')
        narrow = w < 200
        fs, ss, sls = (14, 10.5, ".5") if narrow else (15, 11, "1")
        cx, cy = x + w / 2, y + h / 2
        if b.get("s"):
            o.append(f'<text x="{num(cx)}" y="{num(cy - 3)}" text-anchor="middle" font-size="{fs}" fill="{fg}">{esc(b["n"])}</text>')
            o.append(f'<text x="{num(cx)}" y="{num(cy + 14)}" text-anchor="middle" font-size="{ss}" letter-spacing=".3" '
                     f'fill="{fg}" opacity=".75">{esc(b["s"])}</text>')
        else:
            o.append(f'<text x="{num(cx)}" y="{num(cy + 5)}" text-anchor="middle" font-size="{fs}" fill="{fg}">{esc(b["n"])}</text>')
        if b.get("badge") is not None:
            bc = "#B8975A" if fill == "noir" else "#0B0B0B"
            o.append(f'<circle cx="{num(x + w - 10)}" cy="{num(y + 10)}" r="8" fill="{bc}"/>'
                     f'<text x="{num(x + w - 10)}" y="{num(y + 13.5)}" text-anchor="middle" font-size="10" fill="#fff">'
                     f'{esc(b["badge"])}</text>')
    o.append("</svg>")
    return "".join(o)


# ── slide kinds (body only; header and chrome are shared) ─────────────────────────────────────────
def tiles_html(items, cols_style, tile_style="", vsize=None):
    out = []
    for t in items:
        fill = t.get("c", "sable")
        col = ";color:#fff" if fill in DARK_FILLS else ""
        vs = f' style="font-size:{vsize}"' if vsize else ""
        if vsize:  # compact tiles (sprint): sub-label inline, as in the mockup
            sub = f' <small style="font-size:.35em">{esc(t["s"])}</small>' if t.get("s") else ""
            out.append(f'<div class="tile" style="background:{cssc(fill)}{col}{tile_style}"><span class="k">{esc(t["k"])}</span>'
                       f'<span class="v"{vs}>{esc(t["v"])}{sub}</span></div>')
        else:
            sub = f'<span class="s">{esc(t["s"])}</span>' if t.get("s") else ""
            out.append(f'<div class="tile" style="background:{cssc(fill)}{col}{tile_style}"><span class="k">{esc(t["k"])}</span>'
                       f'<span class="v">{esc(t["v"])}</span>{sub}</div>')
    return f'<div class="tiles" style="{cols_style}">' + "".join(out) + "</div>"


def k_table(sl, ctx):
    o = [table_html(sl["table"], small=sl.get("small"), legend=sl.get("legend"))]
    if sl.get("note"):
        o.append(f'<p class="lead" style="font-size:.9cqw;margin-top:1.4cqw;color:var(--gris)">{rich(sl["note"])}</p>')
    if sl.get("legend"):
        chl = any(k.startswith("st:") or k == "star" for k, _ in sl["legend"])
        o.append(legend_html(sl["legend"], "legend chl" if chl else "legend"))
    return "".join(o)


def k_tiles_table(sl, ctx):
    n = len(sl["tiles"])
    return (tiles_html(sl["tiles"], f"grid-template-columns: repeat({n}, 1fr); margin-top: 2.6cqw;")
            + table_html(sl["table"], small=True, style="margin-top:2.2cqw"))


def k_progress(sl, ctx):
    rows = []
    for b in sl["bars"]:
        v = b.get("v") or f"{b['p']} %"
        if " / " in v:
            a, _, z = v.partition(" / ")
            val = f'{esc(a)}<small style="font-size:.55em;color:var(--gris)"> /{esc(z)}</small>'
        else:
            val = esc(v)
        mark = "" if b.get("time") else f'<span class="mark" style="left:{pct(sl["expected"])}"></span>'
        rows.append(f'<div class="row"><span class="lbl">{esc(b["l"])}</span><span class="track">'
                    f'<span class="fill" style="width:{pct(b["p"])};background:{cssc(b.get("c", "encre"))}"></span>{mark}</span>'
                    f'<span class="val">{val}</span></div>')
        if b.get("time"):
            rows.append(f'<div class="row" style="margin-bottom:2cqw"><span></span><span style="font:200 .85cqw var(--sans);'
                        f'color:var(--gris)">Trait bordeaux : avancement attendu à date ({esc(sl["expected"])} %)</span><span></span></div>')
    return ('<div class="grid" style="grid-template-columns: 1fr 1.5fr; align-items: center; margin-top: 3cqw;"><div>'
            f'<div class="kpi">{esc(sl["kpi"])}<sup>{esc(sl.get("unit", ""))}</sup></div>'
            f'<p class="lead" style="margin-top:1.8cqw">{rich(sl.get("lead", ""))}</p></div>'
            f'<div class="bars">{"".join(rows)}</div></div>')


def k_burndown(sl, ctx):
    o = [f'<div class="grow" style="margin-top:1.4cqw">{chart_svg(sl["chart"], True, sl.get("title", ""))}</div>']
    if sl.get("legend"):
        o.append(legend_html(sl["legend"]))
    return "".join(o)


def k_sprint(sl, ctx):
    return ('<div class="grid" style="grid-template-columns: 1fr 1.9fr; margin-top: 2.2cqw; align-items: start;">'
            + tiles_html(sl["tiles"], "grid-template-columns: 1fr;", ";min-height:7.4cqw", vsize="3.4cqw")
            + chart_svg(sl["chart"], False, sl.get("title", "")).replace("<svg ", '<svg style="width:100%" ', 1)
            + "</div>")


def k_gantt(sl, ctx):
    return f'<div class="grow" style="margin-top:1.6cqw">{gantt_svg(sl["gantt"])}</div>'


def k_milestones(sl, ctx):
    return milestones_svg(sl)


def k_meteo(sl, ctx):
    n = len(sl["domains"])
    cards = []
    for d in sl["domains"]:
        dark = d["st"] in ("bloque", "fait")
        on, off = ("#fff", "rgba(255,255,255,.35)") if dark else ("#1A1A1A", "rgba(0,0,0,.15)")
        c = float(d.get("closed", 0)) * 100
        cards.append(f'<div class="dom s-{esc(d["st"])}"><span class="k">{esc(d["k"])}</span><span class="v">{rich(d["v"])}</span>'
                     f'<div class="stack"><span style="width:{pct(c)};background:{on}"></span>'
                     f'<span style="width:{pct(100 - c)};background:{off}"></span></div></div>')
    o = f'<div class="meteo" style="grid-template-columns: repeat({n}, 1fr);">' + "".join(cards) + "</div>"
    if sl.get("legend"):
        o += legend_html(sl["legend"], style="margin-top:2cqw")
    return o


def k_matrix(sl, ctx):
    cells = ['<div class="ax ay" style="grid-row:1/5">Probabilité</div>']
    for r in range(4):
        for c in range(4):
            chips = "".join(f'<span class="chip">{esc(i)}</span>' for i in sl.get("chips", {}).get(f"{r},{c}", []))
            cells.append(f'<div class="cell {esc(sl["grid"][r][c])}">{chips}</div>')
    cells.append('<div></div><div class="ax" style="grid-column:2/6">Impact</div>')
    items = []
    for it in sl.get("top", []):
        items.append(f'<li><span class="id">{esc(it["id"])}</span><span class="lb">{rich(it["t"])}<small>{rich(it.get("lev", ""))}</small>'
                     f'</span><span class="pill {esc(it["lvl"])}">{esc(it["lt"])}</span></li>')
    return ('<div class="grid" style="grid-template-columns: 1fr 1.15fr; align-items: start;">'
            f'<div class="matrix">{"".join(cells)}</div><ol class="toplist">{"".join(items)}</ol></div>')


def k_diagram(sl, ctx):
    o = [f'<div class="grow" style="margin-top:1.2cqw">{diagram_svg(sl["diagram"], ctx["uid"], sl.get("title", ""))}</div>']
    if sl.get("legend"):
        o.append(legend_html(sl["legend"]))
    return "".join(o)


def k_gate(sl, ctx):
    return ('<div class="grid" style="grid-template-columns: 1fr 2.4fr; align-items: start;">'
            f'<div><div class="kpi" style="font-size:9cqw">{esc(sl["kpi"])}<span style="font-size:.4em;color:var(--gris)">'
            f'{esc(sl.get("of", ""))}</span></div><p class="lead" style="margin-top:1.4cqw">{rich(sl.get("lead", ""))}</p></div>'
            + table_html(sl["table"], small=True, style="margin-top:0") + "</div>")


def k_weekly(sl, ctx):
    cols = []
    for c in sl["cols"]:
        lis = []
        for it in c["items"]:
            t = f" {rich(it['t'])}" if it.get("t") else ""
            sub = "<ul>" + "".join(f"<li>{rich(s)}</li>" for s in it["sub"]) + "</ul>" if it.get("sub") else ""
            lis.append(f"<li><b>{rich(it['b'])}</b>{t}{sub}</li>")
        cols.append(f"<div><h3>{esc(c['h'])}</h3><ul>{''.join(lis)}</ul></div>")
    return f'<div class="wk">{"".join(cols)}</div>'


def k_mail(sl, ctx):
    subj = "".join(f'<div><h4>{rich(s["h"])}</h4><p>{rich(s.get("s", ""))}</p><p>{rich(s.get("n", ""))}</p></div>'
                   for s in sl.get("subjects", []))
    return ('<div class="mail">'
            f'<div class="obj"><span>Objet</span>{esc(sl.get("obj", ""))}</div>'
            + "".join(f"<p>{rich(p)}</p>" for p in sl.get("intro", []))
            + f'<div class="subj">{subj}</div>'
            + "".join(f"<p>{rich(p)}</p>" for p in sl.get("closing", []))
            + "</div>")


def k_archi(sl, ctx):
    sys.path.insert(0, str(ROOT / "framework" / "generators" / "archi"))
    import dossier_skin as K  # noqa: E402
    model = json.loads((ctx["mission_dir"] / sl["model"]).read_text(encoding="utf-8"))
    svg = K.overview_svg(model)
    svg = svg.replace("<svg ", '<svg class="archi-svg" preserveAspectRatio="xMidYMid meet" ', 1)
    o = [f'<div class="grow" style="margin-top:1.2cqw">{svg}</div>']
    if sl.get("link"):
        o.append(f'<a class="archi-link" href="{esc(sl["link"])}" target="_blank" rel="noopener">'
                 f'{esc(sl.get("link_label", "Vue interactive et sous-vues ↗"))}</a>')
    return "".join(o)


KINDS = {"table": k_table, "tiles_table": k_tiles_table, "progress": k_progress, "burndown": k_burndown,
         "sprint": k_sprint, "gantt": k_gantt, "milestones": k_milestones, "meteo": k_meteo, "matrix": k_matrix,
         "diagram": k_diagram, "gate": k_gate, "weekly": k_weekly, "mail": k_mail, "archi": k_archi}
FIT = {"burndown", "gantt", "diagram", "archi"}


# ── chrome and slide frames ───────────────────────────────────────────────────────────────────────
def src_href(src: str) -> str:
    first = src.split(" · ")[0].strip()
    return first if (" " not in first and FILE_EXT.search(first)) else "#"


def chrome(sl, deck, page, dark, logos):
    """Logo (white on black slides, wordmark on content slides), footer, source link, page number."""
    o = []
    if sl.get("kind") != "cover":
        lg = logos.get("dark" if dark else "light")
        if lg:
            o.append(f'<img class="{"logo-n" if dark else "logo-c"}" src="{esc(lg)}" alt="Logo client">')
    project = sl.get("project") or deck.get("project", "")
    src = ""
    if sl.get("src"):
        src = (f'<a class="src" href="{esc(src_href(sl["src"]))}" title="Ouvrir la source">'
               f'Source · {esc(sl["src"])} ↗</a>')
    o.append(f'<div class="foot"><span>{esc(project)} · {esc(sl.get("section", ""))}</span>{src}<span>{page:02d}</span></div>')
    return "".join(o)


def cover_html(sl, deck, page, logos, sid):
    big = f'<img class="big" src="{esc(logos["dark"])}" alt="Logo client">' if logos.get("dark") else ""
    return (f'<section id="{esc(sid)}" class="slide noire cover">{big}<h1>{rich(sl.get("title", ""))}</h1>'
            f'<div class="rule"></div><div class="sub">{esc(sl.get("sub", ""))}</div>'
            + chrome(sl, deck, page, True, logos) + "</section>")


def section_html(sl, deck, page, logos, sid):
    title = "<br>".join(esc(t) for t in sl.get("title", "").split("\n"))
    return (f'<section id="{esc(sid)}" class="slide noire">' + chrome(sl, deck, page, True, logos)
            + f'<div class="kicker">{esc(sl.get("kicker", deck.get("kicker", "")))}</div><h1>{title}</h1>'
            f'<div class="rule"></div><div class="sub">{esc(sl.get("sub", ""))}</div>'
            f'<div class="num">{esc(sl.get("num", ""))}</div></section>')


def content_html(sl, deck, page, logos, sid, body, fit=False):
    head = (f'<div class="eyebrow">{esc(sl.get("eyebrow", ""))}</div><h2 class="title">{esc(sl.get("title", ""))}</h2>'
            + (f'<p class="cap">{rich(sl["cap"])}</p>' if sl.get("cap") else ""))
    cls = "slide content fit" if fit else "slide content"
    return (f'<section id="{esc(sid)}" class="{cls}">' + chrome(sl, deck, page, False, logos)
            + head + body + "</section>")


def agenda_html(deck, page, logos):
    groups = _agenda_full(deck)
    ncol = max(1, min(4, len(groups)))
    blocks = []
    for title, n, anchor, items in groups:
        nn = f'<span class="n">{esc(n)}</span>' if n else ""
        h = f'<a href="#{esc(anchor)}">{nn}{esc(title)}</a>' if anchor else f"{nn}{esc(title)}"
        lis = "".join(f'<li><a href="#{esc(i)}">{esc(t)}</a></li>' for i, t in items)
        blocks.append(f"<div><h3>{h}</h3><ul>{lis}</ul></div>")
    sl = {"kind": "agenda", "section": "Sommaire", "eyebrow": "Dossier projet · Sommaire", "title": "Sommaire"}
    body = f'<nav class="agenda" style="grid-template-columns: repeat({ncol}, 1fr);">{"".join(blocks)}</nav>'
    return content_html(sl, deck, page, logos, "sommaire", body)


# ── page ──────────────────────────────────────────────────────────────────────────────────────────
def _copy_logos(deck, mission_dir: Path, out_dir: Path) -> dict:
    """Copy deck['logos'] files into out_dir/logos/ ; return {key: relative href}."""
    out = {}
    for key, rel in (deck.get("logos") or {}).items():
        src = Path(mission_dir) / rel
        if not src.exists():
            continue
        dst = out_dir / "logos" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        out[key] = f"logos/{src.name}"
    return out


def build(deck: dict, mission_dir: Path, logos: dict) -> str:
    slides, page = [], 0
    ids = slide_ids(deck)
    has_cover = any(sl["kind"] == "cover" for sl in deck["slides"])
    if not has_cover:  # no cover: the agenda opens the deck
        page += 1
        slides.append(agenda_html(deck, page, logos))
    for n, (sid, sl) in enumerate(zip(ids, deck["slides"]), 1):
        k = sl["kind"]
        page += 1
        if k == "cover":
            slides.append(cover_html(sl, deck, page, logos, sid))
            page += 1
            slides.append(agenda_html(deck, page, logos))
        elif k == "section":
            slides.append(section_html(sl, deck, page, logos, sid))
        else:
            fn = KINDS.get(k)
            if fn is None:
                raise ValueError(f"slide {n} ({sid}) : kind inconnu « {k} »")
            ctx = {"mission_dir": Path(mission_dir), "uid": f"d{n}"}
            slides.append(content_html(sl, deck, page, logos, sid, fn(sl, ctx), fit=k in FIT))
    title = f"{deck.get('project', '')} · Dossier projet"
    return ("<!doctype html>\n<html lang=\"fr\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(title)}</title>\n<style>{CHARTER_CSS}{EXTRA_CSS}</style>\n</head>\n<body>\n"
            + "\n\n".join(slides) + "\n</body>\n</html>\n")


def render_html(deck: dict, mission_dir: Path, out_dir: Path) -> Path:
    """Render the dossier to out_dir/index.html (logos copied to out_dir/logos/). Returns the page path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logos = _copy_logos(deck, Path(mission_dir), out_dir)
    page = out_dir / "index.html"
    page.write_text(build(deck, Path(mission_dir), logos), encoding="utf-8")
    return page


def main(argv):
    if not argv or argv[0].startswith("-") or "-o" not in argv:
        print(__doc__)
        return 2
    prof = _load("pmf_profile", ROOT / "framework" / "lib" / "profile.py")
    mission = argv[0]
    mdir = Path(prof.mission_dir(mission))
    src = Path(argv[argv.index("--input") + 1]) if "--input" in argv else (mdir / "dossier" / "dossier.json" if (mdir / "dossier" / "dossier.json").exists() else mdir / "dossier.json")
    deck = json.loads(src.read_text(encoding="utf-8"))
    out = render_html(deck, mdir, Path(argv[argv.index("-o") + 1]))
    print(f"ok : {out} ({len(deck['slides']) + 1} slides, sommaire compris)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
