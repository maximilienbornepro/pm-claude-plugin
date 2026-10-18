#!/usr/bin/env python3
"""Pipeline Jira -> JSON du plan -> page, piloté par la config (comme `projection`).

Construit le JSON du plan de sprints (contrat `CONTRACT.md`) depuis un Jira, puis
le rend via `render.py`. AUCUNE valeur de mission en dur : tout vient de la config.

  - `profiles/<mission>/projection.yml`  : capacité, pôles, versions, workflow, dates
    (réutilisé tel quel ; mêmes chiffres que le générateur `projection`).
  - `profiles/<mission>/plan.yml`         : cadence des sprints, marque/liens, éditorial.

Répartition : Jira fait foi (champ sprint de chaque ticket). Seuls les tickets du
backlog sont placés par le calcul, sous la cible de capacité du pôle. Burn-down réel :
un ticket descend la courbe le jour où il passe en Testing ou fermé (dates Jira).

  PMF_JIRA_ENV=<.../.env> python3 from_jira.py <mission> [sortie.html]
  PMF_JIRA_ENV=<.../.env> python3 from_jira.py <mission> --json plan.json   # JSON seul

Lecture seule : uniquement des requêtes Jira de lecture. N'écrit que le fichier de sortie.
"""
import sys, os, json, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "lib"))
sys.path.insert(0, str(HERE.parent / "projection"))
sys.path.insert(0, str(HERE))
import profile as prof          # noqa: E402
import jira as jira_mod         # noqa: E402
import project as P             # noqa: E402  (load_config + helpers vérifiés)
import render as R              # noqa: E402

MOIS = ["jan", "fév", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]


def r1(x):
    return round(x * 10) / 10


def _date(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def dcourt(d):
    return f"{d.day:02d} {MOIS[d.month - 1]}"


# ------------------------------------------------------------------ config plan
def load_plan_cfg(mission):
    path = prof.mission_dir(mission) / "plan.yml"
    cfg = prof._load_yaml(path) if path.exists() else {}
    cad = cfg.get("cadence") or {}
    caps = cad.get("caps") or {}
    brand = cfg.get("brand") or {}
    edi = cfg.get("editorial") or {}
    mdir = prof.mission_dir(mission)

    def _load_edi(name):
        v = edi.get(name)
        if not v:
            return {}
        p = (mdir / v) if not os.path.isabs(v) else Path(v)
        return json.load(open(p, encoding="utf-8")) if p.exists() else {}

    logo = ""
    if brand.get("logo_file"):
        lp = mdir / brand["logo_file"]
        if lp.exists():
            logo = open(lp, encoding="utf-8").read().strip()
    return {
        "sprint_field": cfg.get("sprint_field") or "customfield_10020",
        "second_start": _date(cad.get("second_sprint_start")) or (datetime.date.today()),
        "length": int(cad.get("length_days") or 14),
        "caps": {"back": int(caps.get("back") or 17), "front": int(caps.get("front") or 15),
                 "sre": int(caps.get("sre") or 10)},
        "v11_from": int(cad.get("v11_from_sprint") or 5),
        "bug_pct": float(cad.get("bug_reserve_pct") or 0.20),
        "burn_wip": set(cfg.get("burn_wip") or ["Testing"]),
        "brand": {"title": brand.get("title") or f"Avancement et sprints {mission}",
                  "sub": brand.get("sub") or "", "logo": logo,
                  "app_url": brand.get("app_url") or "", "app_label": brand.get("app_label") or ""},
        "jira": cfg.get("jira_browse") or "",
        "links": cfg.get("links") or [],
        "nav": cfg.get("nav") or [],
        "release_link": cfg.get("release_link"),
        "obj": (_load_edi("objectifs") or {}).get("objectifs") or _load_edi("objectifs"),
        "nar": (_load_edi("narratif") or {}).get("sprints") or _load_edi("narratif"),
        "pobj": (_load_edi("poles") or {}).get("poles") or _load_edi("poles"),
    }


# ------------------------------------------------------------------ Jira -> rows
def fetch_rows(mission, cfg, pcfg):
    J = jira_mod.Jira(mission)
    types = ", ".join(cfg["issue_types"])
    jql = f"project={J.project} AND issuetype in ({types}) ORDER BY key"
    fields = ["summary", "issuetype", "status", "timeoriginalestimate", "parent",
              "fixVersions", "resolutiondate", "updated", pcfg["sprint_field"]]
    issues = J.search(jql, fields)

    # map sprint Jira -> numéro de plan (actif = 1, futurs par date de début)
    board = J.sprints("active,future")
    def _sd(s):
        return s.get("startDate") or "9999"
    active = [s for s in board if (s.get("state") == "active")]
    future = sorted([s for s in board if s.get("state") != "active"], key=_sd)
    plan_no = {}
    n = 1
    for s in active:
        plan_no[s["id"]] = n; n += 1
    n = max(n, 2)
    for s in future:
        plan_no[s["id"]] = n; n += 1

    W = cfg["status_weights"]
    burn_set = set(cfg["done_statuses"]) | set(pcfg["burn_wip"])
    rows = []
    for i in issues:
        f = i["fields"]
        st = (f.get("status") or {}).get("name", "")
        if st in cfg["excluded_statuses"]:
            continue
        epic = ((f.get("parent") or {}).get("fields", {}) or {}).get("summary") or "(sans epic)"
        fix = [v.get("name") for v in (f.get("fixVersions") or [])]
        is_next = (cfg["next_version"] in fix) or (epic in cfg["v2_epics"]) or (i["key"] in cfg["forced_v11"])
        est = round((f.get("timeoriginalestimate") or 0) / cfg["day_seconds"], 2)
        done = st in cfg["done_statuses"]
        # numéro de sprint du ticket
        sp = None
        raw = f.get(pcfg["sprint_field"]) or []
        if isinstance(raw, list):
            for s in raw:
                sid = s.get("id") if isinstance(s, dict) else None
                if sid in plan_no:
                    sp = plan_no[sid]
        res = None
        if st in burn_set:
            res = (f.get("resolutiondate") or f.get("updated") or "")[:10] or None
        rows.append({
            "k": i["key"], "s": f.get("summary") or "", "e": epic, "p": P._pole(cfg, epic),
            "est": est, "r": round(est * (1 - W.get(st, 0.0)), 2), "st": st,
            "ph": "V1.1" if is_next else "V1",
            "sp": sp, "res": res, "d": 1 if done else 0, "ne": 0 if est else 1,
        })
    return J, rows


# ------------------------------------------------------------------ allocation
def allocate(rows, cfg, pcfg):
    WIP = {s for s, w in cfg["status_weights"].items() if 0 < w < 1}
    PRIO = lambda t: -t["r"]
    caps = pcfg["caps"]
    live = [t for t in rows if not t["d"] and (not t["ne"] or t["sp"])]
    doneV1 = [t for t in rows if t["d"] and t["ph"] == "V1"]

    def inS1(t):
        return t["sp"] == 1 or (not t["sp"] and t["st"] in WIP and not t["ne"])

    alloc = {"S1": [t for t in live if inS1(t)] + doneV1}
    restV1 = [t for t in live if not inS1(t) and t["ph"] == "V1"]
    restV11 = [t for t in live if not inS1(t) and t["ph"] == "V1.1"]
    charge = {}

    def place(t, start):
        k = start
        while True:
            sp = f"S{k}"; cap = caps[t["p"]]; load = charge.get((sp, t["p"]), 0.0)
            if load + t["r"] <= cap or load == 0:
                alloc.setdefault(sp, []).append(t); charge[(sp, t["p"])] = load + t["r"]; return
            k += 1

    for t in [t for t in restV1 + restV11 if t["sp"]]:
        alloc.setdefault(f"S{t['sp']}", []).append(t)
    restV1 = [t for t in restV1 if not t["sp"]]
    restV11 = [t for t in restV11 if not t["sp"]]
    for t in sorted(restV1, key=PRIO):
        place(t, 2)
    for t in sorted(restV11, key=PRIO):
        place(t, pcfg["v11_from"])
    nsp = max(int(s[1:]) for s in alloc)
    for k in range(2, nsp + 1):
        alloc.setdefault(f"S{k}", [])
    return alloc, nsp


# ------------------------------------------------------------------ dates sprint
def sp_window(n, pcfg):
    a = pcfg["second_start"] + datetime.timedelta(days=pcfg["length"] * (n - 2))
    return a, a + datetime.timedelta(days=pcfg["length"])


def sp_meta(n, start, end, phases, freeze, mep):
    dt = f"{dcourt(start)} → {dcourt(end)}"
    if start <= freeze < end:
        dt += " · gel"
    if start <= mep < end:
        dt += " · MEP"
    if n == 1:
        hint = "en cours"
    elif end <= freeze:
        hint = "découpage proposé"
    elif phases == {"V1"}:
        hint = "reste V1"
    elif "V1" in phases:
        hint = "reste V1 + V1.1"
    else:
        hint = "V1.1 · après le gel"
    return dt, hint


# ------------------------------------------------------------------ burn-down
def burndown(rows, start, end, today):
    length = (end - start).days
    bset = []
    for t in rows:
        e = t.get("est") or 0
        if e <= 0:
            continue
        r = _date(t["res"]) if t.get("res") else None
        if r is not None and r < start:
            continue
        bset.append((e, r))
    scope = r1(sum(e for e, _ in bset))
    if start > today:
        return {"scope": scope, "len": length, "serie": []}
    last = min(today, end)
    elapsed = max(0, (last - start).days)
    serie = []
    for d in range(0, elapsed + 1):
        day = start + datetime.timedelta(days=d)
        serie.append({"x": d, "y": r1(sum(e for e, r in bset if r is None or r > day))})
    return {"scope": scope, "len": length, "serie": serie}


# ------------------------------------------------------------------ assemblage
DEV = {"back", "front"}


def build_datajson(mission, cfg, pcfg, rows, alloc, nsp):
    today = datetime.date.today()
    freeze, mep = cfg["code_freeze"], cfg["mep"]
    dpw = cfg["days_per_week"]
    W = cfg["status_weights"]
    POLES = ("back", "front", "sre")

    def agg(rs):
        charge = sum(t["est"] for t in rs)
        real = sum(t["est"] * W.get(t["st"], 0.0) for t in rs)
        return r1(charge), r1(real), r1(charge - real)

    def pole_report(rs, phase):
        sub = [t for t in rs if t["ph"] == phase]
        charge, real, reste = agg(sub)
        return charge, real, reste

    poles = {}
    for pl in POLES:
        rs = [t for t in rows if t["p"] == pl and t["ph"] == "V1"]
        charge, real, reste = agg(rs)
        cap_etp = P._cap_etp(cfg, pl)
        off = P._off_total(cfg, pl)
        weeks = round((reste + off) / cap_etp / dpw) if reste else 0
        poles[pl] = {"charge": charge, "real": real, "reste": reste,
                     "pct": round(real / charge * 100) if charge else 0,
                     "weeks": weeks, "cap_etp": round(cap_etp, 2)}
    v11 = {}
    for pl in POLES:
        rs = [t for t in rows if t["p"] == pl and t["ph"] == "V1.1"]
        charge, real, reste = agg(rs)
        v11[pl] = {"charge": charge, "real": real, "reste": reste,
                   "pct": round(real / charge * 100) if charge else 0}
    v1_all = [t for t in rows if t["ph"] == "V1"]
    c1, r1v, rest1 = agg(v1_all)
    nx = [t for t in rows if t["ph"] == "V1.1"]
    cN, rN, restN = agg(nx)
    # fin V1 et dépassement
    def end_pole(pl):
        reste = poles[pl]["reste"]; off = P._off_total(cfg, pl); cap = P._cap_etp(cfg, pl)
        import math
        wd = math.ceil((reste + off) / cap) if reste > 0 else 0
        return P._add_biz_days(today, wd)
    v1_end = max(end_pole(pl) for pl in POLES)
    avail_weeks = round(P._biz_days(today, freeze) / dpw)

    # burn-down du plan (V1)
    def burn_v1():
        v1 = [t for t in rows if t["ph"] == "V1" and (t.get("est") or 0) > 0]
        scope = r1(sum(t["est"] for t in v1))
        res = [_date(t["res"]) for t in v1 if t.get("res")]
        res = [d for d in res if d]
        start = min(res) if res else today - datetime.timedelta(days=7)
        start -= datetime.timedelta(days=start.weekday())
        serie, d = [], start
        while d < today:
            serie.append({"t": d.isoformat(), "d": (d - start).days,
                          "y": r1(sum(t["est"] for t in v1 if not (t.get("res") and _date(t["res"]) and _date(t["res"]) <= d)))})
            d += datetime.timedelta(days=7)
        serie.append({"t": today.isoformat(), "d": (today - start).days,
                      "y": r1(sum(t["est"] for t in v1 if not (t.get("res") and _date(t["res"]) and _date(t["res"]) <= today)))})
        return {"scope": scope, "start": start.isoformat(),
                "freeze": freeze.isoformat(), "freeze_d": (freeze - start).days,
                "mep": mep.isoformat(), "mep_d": (mep - start).days,
                "today": today.isoformat(), "today_d": (today - start).days, "serie": serie}

    # sprints[]
    def pole_block(rs, pl, n):
        sub = [t for t in rs if t["p"] == pl]
        tot = r1(sum(t["r"] for t in sub))
        est = r1(sum((t.get("est") or 0) for t in sub))
        bugs = r1(est * pcfg["bug_pct"]) if pl in DEV else 0.0
        done = r1(sum((t.get("est") or 0) for t in sub if t["d"]))
        be = {}
        for t in sorted(sub, key=lambda x: -x["r"]):
            be.setdefault(t["e"], []).append(t)
        epics = [{"e": ep, "r": r1(sum(x["r"] for x in be[ep])), "n": len(be[ep]),
                  "done": sum(1 for x in be[ep] if x["d"])} for ep in be]
        return {"label": pl.capitalize() if pl != "sre" else "SRE",
                "tot": tot, "est": est, "bugs": bugs, "done": done,
                "load": r1(tot + bugs), "cap": pcfg["caps"][pl], "n": len(sub), "epics": epics,
                "objectif": (pcfg["pobj"].get(str(n), {}) or {}).get(pl, "")}

    sprints = []
    for n in range(1, nsp + 1):
        rs = alloc[f"S{n}"]
        if n == 1:
            # S1 = sprint en cours : la fenêtre se termine au début du sprint 2.
            a, b = pcfg["second_start"] - datetime.timedelta(days=pcfg["length"]), pcfg["second_start"]
        else:
            a, b = sp_window(n, pcfg)
        phases = {t["ph"] for t in rs} or {"V1"}
        dt, hint = sp_meta(n, a, b, phases, freeze, mep)
        tot = r1(sum(t["r"] for t in rs))
        bugs = r1(sum((t.get("est") or 0) for t in rs if t["p"] in DEV) * pcfg["bug_pct"])
        estTotal = r1(sum((t.get("est") or 0) for t in rs))
        sprints.append({
            "n": n, "dates": dt, "hint": hint, "start": a.isoformat(), "end": b.isoformat(),
            "objectif": (pcfg["obj"].get(str(n)) if isinstance(pcfg["obj"], dict) else "") or "",
            "fres": _detag((pcfg["nar"].get(str(n), {}) or {}).get("fres", "")),
            "fout": _detag((pcfg["nar"].get(str(n), {}) or {}).get("fout", "")),
            "tot": tot, "bugs": bugs, "ntk": len(rs), "estTotal": estTotal,
            "jiraUrl": pcfg["jira"],
            "poles": {pl: pole_block(rs, pl, n) for pl in POLES},
            "tickets": [{"k": t["k"], "s": t["s"], "p": t["p"], "e": t["e"], "r": t["r"],
                         "est": t.get("est"), "st": t["st"], "d": bool(t["d"]),
                         "ne": bool(t["ne"]), "ph": t["ph"]} for t in rs],
            "burn": burndown(rs, a, b, today),
        })

    return {
        "meta": {
            "brand": pcfg["brand"], "today": today.isoformat(),
            "freeze": freeze.isoformat(), "mep": mep.isoformat(),
            "jira": pcfg["jira"], "links": pcfg["links"], "nav": pcfg["nav"],
            "release_link": pcfg["release_link"],
        },
        "report": {
            "kpi": {"v1_pct": round(r1v / c1 * 100) if c1 else 0, "v1_real": r1v,
                    "v1_charge": c1, "v1_reste": rest1},
            "poles": poles, "poles_v11": v11, "v11": {"reste": restN},
            "v1_total": {"charge": c1, "real": r1v, "reste": rest1,
                         "pct": round(r1v / c1 * 100) if c1 else 0,
                         "weeks": max(poles[p]["weeks"] for p in POLES)},
            "timeline": {"v1_end": v1_end.isoformat(),
                         "overshoot_weeks": round(P._biz_days(freeze, v1_end) / dpw, 1)},
            "avail_weeks": avail_weeks, "freeze": freeze.isoformat(),
            "burn_v1": burn_v1(),
        },
        "sprints": sprints,
    }


def _detag(s):
    if not s:
        return s
    return s.replace("&#8594;", "").replace("&#8217;", "'").replace("&#183;", "·").strip()


def main(argv):
    if not argv:
        sys.exit(__doc__)
    mission = argv[0]
    out = "plan.html"
    json_only = None
    rest = argv[1:]
    if rest and rest[0] == "--json":
        json_only = rest[1] if len(rest) > 1 else "plan.json"
    elif rest:
        out = rest[0]
    cfg = P.load_config(mission)
    pcfg = load_plan_cfg(mission)
    J, rows = fetch_rows(mission, cfg, pcfg)
    alloc, nsp = allocate(rows, cfg, pcfg)
    data = build_datajson(mission, cfg, pcfg, rows, alloc, nsp)
    if json_only:
        json.dump(data, open(json_only, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"écrit {json_only} | {nsp} sprints")
    else:
        n = R.render(data, out)
        print(f"écrit {out} | {n} octets | {nsp} sprints")
    print("CONTROLE V1 reste =", data["report"]["v1_total"]["reste"],
          "| V1.1 reste =", data["report"]["v11"]["reste"])


if __name__ == "__main__":
    main(sys.argv[1:])
