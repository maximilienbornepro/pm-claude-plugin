#!/usr/bin/env python3
"""Harness du plan de sprints : valide un JSON de donnees contre CONTRACT.md.

Lecture seule, sans dependance. Rend 0 si le JSON est rendable, 1 sinon, et liste
les problemes. Sert de garde avant publication et de test de regression.

  python3 validate.py donnees.json
  python3 validate.py            # valide plan.example.json
"""
import sys, os, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
POLES = ("back", "front", "sre")


def _date(v):
    try:
        datetime.date.fromisoformat(str(v)[:10]); return True
    except Exception:
        return False


def check(d):
    errs, warns = [], []

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    # ---- meta
    meta = d.get("meta") or {}
    need(isinstance(meta.get("brand"), dict), "meta.brand manquant")
    for k in ("today", "freeze", "mep"):
        need(_date(meta.get(k)), f"meta.{k} absent ou non-date")
    if meta.get("links") is not None:
        for i, l in enumerate(meta["links"]):
            need(l.get("label") and l.get("url"), f"meta.links[{i}] : label/url requis")

    # ---- report
    r = d.get("report") or {}
    kpi = r.get("kpi") or {}
    for k in ("v1_pct", "v1_real", "v1_charge", "v1_reste"):
        need(isinstance(kpi.get(k), (int, float)), f"report.kpi.{k} manquant")
    for pl in POLES:
        g = (r.get("poles") or {}).get(pl)
        need(isinstance(g, dict), f"report.poles.{pl} manquant")
        if isinstance(g, dict):
            for k in ("charge", "reste", "pct"):
                need(isinstance(g.get(k), (int, float)), f"report.poles.{pl}.{k} manquant")
    b = r.get("burn_v1") or {}
    need(isinstance(b.get("scope"), (int, float)), "report.burn_v1.scope manquant")
    need(_date(b.get("start")), "report.burn_v1.start absent")
    tk = b.get("tk")
    need(isinstance(tk, list) and tk, "report.burn_v1.tk vide (tickets du burn-down, série calculée côté page)")
    for p in (tk or []):
        need(isinstance(p.get("e"), (int, float)), "report.burn_v1.tk : chaque ticket a `e` (estimation)")
        need("cd" in p and "td" in p and "st" in p, "report.burn_v1.tk : chaque ticket a cd, td, st")

    # ---- sprints
    sprints = d.get("sprints") or []
    need(isinstance(sprints, list) and sprints, "sprints vide")
    nums = []
    for s in sprints:
        n = s.get("n"); nums.append(n)
        tag = f"sprint {n}"
        for k in ("dates", "start", "end", "objectif"):
            need(s.get(k) not in (None, ""), f"{tag} : {k} manquant")
        need(_date(s.get("start")) and _date(s.get("end")), f"{tag} : start/end non-date")
        for k in ("tot", "bugs", "ntk", "estTotal"):
            need(isinstance(s.get(k), (int, float)), f"{tag} : {k} manquant")
        pls = s.get("poles") or {}
        for pl in POLES:
            g = pls.get(pl)
            need(isinstance(g, dict), f"{tag} : poles.{pl} manquant")
            if isinstance(g, dict):
                for k in ("label", "tot", "load", "cap"):
                    need(g.get(k) is not None, f"{tag}.{pl} : {k} manquant")
        need(isinstance(s.get("tickets"), list), f"{tag} : tickets doit être une liste")
        if isinstance(s.get("tickets"), list):
            need(len(s["tickets"]) == s.get("ntk"),
                 f"{tag} : ntk={s.get('ntk')} mais {len(s['tickets'])} tickets")
            for t in s["tickets"]:
                for k in ("k", "s", "p", "e", "r", "st", "ph"):
                    need(k in t, f"{tag} ticket {t.get('k','?')} : champ {k} manquant")
        bn = s.get("burn") or {}
        need("scope" in bn and "len" in bn and isinstance(bn.get("tk"), list),
             f"{tag} : burn {{scope, len, start, tk}} requis (tk = tickets, série calculée côté page)")
    if nums and nums != sorted(nums):
        warns.append(f"sprints non ordonnés : {nums}")
    if nums and nums[0] != 1:
        warns.append("le premier sprint devrait être le n°1 (en cours)")

    return errs, warns


def main(argv):
    src = argv[0] if argv else os.path.join(HERE, "plan.example.json")
    if not os.path.exists(src):
        sys.exit(f"JSON introuvable : {src}")
    data = json.load(open(src, encoding="utf-8"))
    errs, warns = check(data)
    for w in warns:
        print(f"  ⚠ {w}")
    if errs:
        for e in errs:
            print(f"  ✗ {e}")
        print(f"ÉCHEC : {len(errs)} erreur(s)" + (f", {len(warns)} avertissement(s)" if warns else ""))
        return 1
    print(f"OK : {os.path.basename(src)} valide"
          + (f" ({len(warns)} avertissement(s))" if warns else "")
          + f" · {len(data.get('sprints', []))} sprints")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
