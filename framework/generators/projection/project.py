#!/usr/bin/env python3
"""Rapport de projection generique - calcul seul, LECTURE SEULE, pilote par la config.

Porte le coeur du rapport de projection SINBAD (scan-jira/projection/serve.py) en un
calcul generique qui ne connait AUCUNE valeur de mission : tout vient de la config
`profiles/<mission>/projection.yml` (capacite de l'equipe, affectation aux poles,
regles de version V1/V1.1, workflow, dates) et du profil Jira. Le rendu (HTML) n'est
pas porte ici : ce module ne fait que le calcul.

A partir du Jira (requetes de lecture seule via framework/lib/jira.py), il etablit :
  - la charge estimee / realisee / restante par pole (back, front, sre) sur le perimetre V1 ;
  - la capacite nette de chaque pole d'ici le gel, confrontee au reste a faire ;
  - la date de fin projetee par pole (reste + absences / capacite ETP, posee en jours
    ouvres a partir d'aujourd'hui) ;
  - la date de fin V1 = le pole le plus tardif (chemin critique), confrontee au gel et a la MEP.

    PMF_JIRA_ENV=<.../.env> python3 project.py <mission>

N'ecrit rien, n'envoie rien, aucune requete d'ecriture.
"""
import sys, math, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
import profile as prof   # noqa: E402  (loader de config, sans dependance)
import jira as jira_mod  # noqa: E402  (client Jira generique, lecture seule)

POLES = ("back", "front", "sre")


# ------------------------------------------------------------------ coercions
# Le mini-parseur YAML integre au framework ne lit ni les flottants ni les dates
# (il les laisse en texte) ; PyYAML, lui, les typerait. On coerce donc toujours,
# quel que soit le parseur qui a charge la config.
def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _date(v):
    if isinstance(v, datetime.date):
        return v
    return datetime.date.fromisoformat(str(v)[:10])


def _set(v):
    return set(v or [])


# ------------------------------------------------------------------ config
def load_config(mission):
    """Config de projection de la mission (profiles/<mission>/projection.yml)."""
    path = prof.mission_dir(mission) / "projection.yml"
    if not path.exists():
        raise SystemExit(f"Config absente : {path}")
    cfg = prof._load_yaml(path)

    est = cfg.get("estimate") or {}
    hours_per_day = _f(est.get("hours_per_day"), 8.0)
    days_per_week = _f(est.get("days_per_week"), 5.0)

    staff = []
    for m in (cfg.get("capacity") or {}).get("staff") or []:
        staff.append({
            "pole": m.get("pole"),
            "dispo": _f(m.get("dispo"), 1.0),
            "off": _f(m.get("off"), 0.0),
            # absence posterieure a l'echeance : ne pese pas sur la capacite nette
            # d'ici le gel, mais compte dans la date de fin projetee si on la depasse.
            "off_after_deadline": bool(m.get("off_after_deadline")),
            "when": m.get("when") or "",
        })

    poles_cfg = cfg.get("poles") or {}
    versions = cfg.get("versions") or {}
    workflow = cfg.get("workflow") or {}
    dates = cfg.get("dates") or {}

    weights = {}
    for k, v in (workflow.get("status_weights") or {}).items():
        weights[k] = _f(v, 0.0)

    return {
        "day_seconds": hours_per_day * 3600.0,
        "days_per_week": days_per_week,
        "staff": staff,
        "back_epics": _set(poles_cfg.get("back_epics")),
        "sre_epics": _set(poles_cfg.get("sre_epics")),
        "next_version": versions.get("next_version"),
        "v2_epics": _set(versions.get("v2_epics")),
        "forced_v11": _set(versions.get("forced_v11")),
        "issue_types": list(workflow.get("issue_types") or ["Story", "Task"]),
        "excluded_statuses": _set(workflow.get("excluded_statuses")),
        "done_statuses": _set(workflow.get("done_statuses")),
        "status_weights": weights,
        "code_freeze": _date(dates["code_freeze"]),
        "mep": _date(dates["mep"]),
    }


# ------------------------------------------------------------------ capacite
def _cap_etp(cfg, pole):
    """Capacite du pole en equivalents temps plein (temps partiel compris)."""
    return sum(m["dispo"] for m in cfg["staff"] if m["pole"] == pole) or 1.0


def _off_total(cfg, pole):
    """Jours-homme d'indisponibilite du pole, toutes periodes confondues."""
    return sum(m["off"] for m in cfg["staff"] if m["pole"] == pole)


def _off_avant(cfg, pole):
    """Jours-homme d'indisponibilite anterieurs a l'echeance."""
    return sum(m["off"] for m in cfg["staff"]
               if m["pole"] == pole and not m["off_after_deadline"])


def _count(cfg, pole):
    return sum(1 for m in cfg["staff"] if m["pole"] == pole)


# ------------------------------------------------------------------ helpers
def _pole(cfg, epic):
    if epic in cfg["back_epics"]:
        return "back"
    if epic in cfg["sre_epics"]:
        return "sre"
    return "front"


def _biz_days(a, b):
    """Jours ouvres (lun-ven) entre a (inclus) et b (exclu) ; 0 si b <= a."""
    n, d = 0, a
    while d < b:
        if d.weekday() < 5:
            n += 1
        d += datetime.timedelta(days=1)
    return n


def _add_biz_days(start, n):
    """Pose n jours ouvres a partir de start (lendemain ouvre, week-ends sautes)."""
    d, c = start, 0
    while c < n:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            c += 1
    return d


# ------------------------------------------------------------------ Jira
def _fetch(cfg, mission):
    J = jira_mod.Jira(mission)
    types = ", ".join(cfg["issue_types"])
    jql = f"project={J.project} AND issuetype in ({types}) ORDER BY key"
    fields = ["summary", "issuetype", "status", "timeoriginalestimate",
              "parent", "labels", "fixVersions"]
    return J, J.search(jql, fields)


def _rows(cfg, issues):
    """Transforme les tickets Jira en lignes {k, pole, phase, est, status}."""
    rows = []
    for i in issues:
        f = i["fields"]
        st = (f.get("status") or {}).get("name", "")
        if st in cfg["excluded_statuses"]:
            continue
        epic = ((f.get("parent") or {}).get("fields", {}) or {}).get("summary") or "(sans epic)"
        fix = [v.get("name") for v in (f.get("fixVersions") or [])]
        is_next = (cfg["next_version"] in fix) or (epic in cfg["v2_epics"]) \
            or (i["key"] in cfg["forced_v11"])
        est_days = round((f.get("timeoriginalestimate") or 0) / cfg["day_seconds"], 2)
        rows.append({
            "k": i["key"], "epic": epic, "pole": _pole(cfg, epic),
            "phase": "next" if is_next else "V1", "est": est_days, "status": st,
            "done": st in cfg["done_statuses"],
        })
    return rows


# ------------------------------------------------------------------ calcul
def compute(mission):
    cfg = load_config(mission)
    J, issues = _fetch(cfg, mission)
    rows = _rows(cfg, issues)
    W = cfg["status_weights"]
    dpw = cfg["days_per_week"]
    freeze, mep = cfg["code_freeze"], cfg["mep"]
    today = datetime.date.today()
    biz_freeze = _biz_days(today, freeze)
    biz_mep = _biz_days(today, mep)

    def agg(rs):
        charge = sum(t["est"] for t in rs)
        real = sum(t["est"] * W.get(t["status"], 0.0) for t in rs)
        return round(charge, 1), round(real, 1), round(charge - real, 1)

    poles = {}
    for pl in POLES:
        rs = [t for t in rows if t["pole"] == pl and t["phase"] == "V1"]
        charge, real, reste = agg(rs)
        cap_etp = _cap_etp(cfg, pl)
        off_total = _off_total(cfg, pl)
        weeks = (reste + off_total) / cap_etp / dpw if reste else 0

        # capacite nette d'ici le gel, confrontee au reste (absences posterieures exclues)
        membres = [m for m in cfg["staff"] if m["pole"] == pl]
        brut = sum(m["dispo"] * biz_freeze for m in membres)
        nominal = _count(cfg, pl) * biz_freeze
        off_avant = _off_avant(cfg, pl)
        net = brut - off_avant

        # date de fin projetee du pole : reste + absences / capacite ETP, en jours ouvres
        wd = math.ceil((reste + off_total) / cap_etp) if reste > 0 else 0
        end = _add_biz_days(today, wd)

        poles[pl] = {
            "charge": charge, "real": real, "reste": reste,
            "pct": round(real / charge * 100) if charge else 0,
            "cap": _count(cfg, pl), "cap_etp": round(cap_etp, 2),
            "off_total": round(off_total, 1), "off_avant": round(off_avant, 1),
            "weeks": round(weeks),
            "net": round(net, 1), "nominal": round(nominal, 1),
            "ecart": round(net - reste, 1),
            "end": end,
        }

    v1_rows = [t for t in rows if t["phase"] == "V1"]
    next_rows = [t for t in rows if t["phase"] == "next"]
    c1, r1, rest1 = agg(v1_rows)
    cN, rN, restN = agg(next_rows)
    crit_pole = max(POLES, key=lambda p: poles[p]["weeks"])
    v1_end = max(poles[p]["end"] for p in POLES)

    return {
        "mission": mission, "project": J.project, "board": J.board,
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "today": today, "code_freeze": freeze, "mep": mep,
        "biz_days_freeze": biz_freeze, "biz_days_mep": biz_mep,
        "n_tickets": len(v1_rows),
        "poles": poles,
        "v1": {"charge": c1, "real": r1, "reste": rest1,
               "pct": round(r1 / c1 * 100) if c1 else 0},
        "next_version": {"charge": cN, "reste": restN, "name": cfg["next_version"]},
        "crit_pole": crit_pole,
        "v1_end": v1_end,
        "overshoot_days": _biz_days(freeze, v1_end),
        "overshoot_weeks": round(_biz_days(freeze, v1_end) / dpw, 1),
    }


# ------------------------------------------------------------------ CLI (preuve)
def _fdate(d):
    return d.strftime("%d/%m/%Y")


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "sinbad"
    d = compute(mission)
    print(f"Rapport de projection - {d['mission']}  "
          f"(projet {d['project']}, board {d['board']}, LECTURE SEULE)")
    print(f"Genere le {d['generated']}  -  {d['n_tickets']} tickets sur le perimetre V1\n")

    print(f"{'Pole':6s} {'charge':>8s} {'realise':>8s} {'reste':>7s} "
          f"{'ETP':>5s} {'off':>6s} {'net/gel':>8s} {'ecart':>7s} {'sem.':>5s}  fin projetee")
    for pl in POLES:
        p = d["poles"][pl]
        print(f"{pl:6s} {p['charge']:8.1f} {p['real']:8.1f} {p['reste']:7.1f} "
              f"{p['cap_etp']:5.2f} {p['off_total']:6.1f} {p['net']:8.1f} "
              f"{p['ecart']:7.1f} {p['weeks']:5d}  {_fdate(p['end'])}")

    v = d["v1"]
    print(f"\nV1 total : charge {v['charge']} j - realise {v['real']} j "
          f"({v['pct']}%) - reste {v['reste']} j")
    nx = d["next_version"]
    print(f"{nx['name'] or 'version suivante'} (hors V1) : "
          f"charge {nx['charge']} j - reste {nx['reste']} j")

    print(f"\nChemin critique : pole {d['crit_pole']}")
    print(f"Fin V1 projetee : {_fdate(d['v1_end'])}  (pole le plus tardif)")
    print(f"Gel du code     : {_fdate(d['code_freeze'])}  "
          f"({d['biz_days_freeze']} j ouvres)")
    print(f"MEP V1          : {_fdate(d['mep'])}  ({d['biz_days_mep']} j ouvres)")
    if d["v1_end"] > d["code_freeze"]:
        print(f">>> Depassement du gel : {d['overshoot_days']} j ouvres "
              f"(~{d['overshoot_weeks']} semaines).")
    else:
        print(">>> Dans les temps pour le gel.")


if __name__ == "__main__":
    main()
