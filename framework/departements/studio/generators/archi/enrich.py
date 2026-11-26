#!/usr/bin/env python3
"""enrich.py - enrichissement automatique d'un modele importe (draw.io) vers le style par defaut.

Un import draw.io brut ne porte ni roles, ni couleurs, ni chemin principal, ni loupes : rendu tel
quel, il sort un squelette plat. Ce module ajoute ce qu'un humain ajouterait a la main :

  1. role / couleur par zone et par entite, deduits de mots-cles (AIFA -> coeur violet, services ->
     vert, S3 -> orange, partenaires -> cyan, identite -> rose, exploitation -> ambre...) ;
  2. chemin principal anime (flux qui touchent le traitement ou qui arrivent sur l'API) ;
  3. loupe + drill-down sur chaque zone d'au moins 2 entites (une vue detail par zone) ;
  4. cadre Kubernetes (EKS) > Namespace autour de la plateforme (option, a confirmer par la personne) ;
  5. mise en page en etages, de haut en bas dans le sens de la donnee (stockage -> traitement ->
     services -> API -> front), positions explicites (`views[].layout`) : plus d'etalement en grille ;
  6. couches (`layers`) + questions SYSTEMATIQUES : Kubernetes / cluster / namespace, Exploitation,
     REST API / BFF, SSO / identite. Une couche absente de la page donne quand meme sa question
     (« aucun noeud ... sur cette page : l'ajouter ? ») : on ne fabrique jamais de noeud.

Rien n'est invente : un role non deduit reste neutre, un logo non trouve reste vide.

    python3 enrich.py in.model.json -o out.model.json [--page "Big Picture"] [--no-cluster]
"""
import argparse
import json
import re
import sys

# --- regles de role (premiere regle qui matche gagne) ----------------------------------------
# (couleur de rendu = cle de ROLE_COLORS de build_html, role de couche = abstraction.py, regex)
RULES = [
    ("partner", "partners", r"etl alert|importer|partner|\bairbus\b|\bksat\b|iceye|vake|vpk"),
    ("auth", "identity", r"keycloak|\bsso\b|oidc|\bidp\b|identity|identit|\bauth"),
    ("ops", "ops", r"prometheus|grafana|\bflux\b|argo|enix|terraform|teleport|observabilit|exploitation|supervision"),
    ("db", "data", r"\brds\b|postgres|database|event ?store|\bdb\b"),
    ("core", "processing", r"aifa|\bdag\b|processing|inference|detector|d[ée]tecteur|\bmodel"),
    ("storage", "data", r"\bs3\b|scanner|bucket|inbox|outbox|raster|stockage|storage"),
    ("ops", "processing", r"pipeline|queue|kafka|notify"),
    ("core", "api", r"api gateway|\bbff\b|rest api|\bapi\b|gateway"),
    ("service", "processing", r"service|module|repository|consumer|gallery|geo"),
    (None, "front", r"frontend|\bfront\b|dashboard|portal|\bui\b|\bweb\b|monitoring|awareness"),
]
# rang dans le sens de la donnee (haut -> bas)
RANK = {"data": 0, "processing": 1, "api": 2, "partners": 2, "identity": 3, "front": 3, "ops": 4}
SYSTEMATIC = [
    ("cluster", "Kubernetes / cluster / namespace"),
    ("ops", "Exploitation"),
    ("api", "REST API / BFF"),
    ("identity", "SSO / identité"),
]
NODE_W, NODE_H, GAP, ZPAD, ZTITLE = 164, 62, 36, 26, 32   # alignes sur build_html
MAXW = 1500                                                 # largeur max d'un etage avant repli
# logo de zone (devant le titre), pris seulement dans les logos disponibles : rien n'est invente
ZONE_LOGOS = [("airflow", r"aifa|\bdag\b|airflow"), ("aws", r"\bs3\b|bucket|\baws\b"),
              ("kubernetes", r"kubernetes|\beks\b|\bk8s\b"), ("keycloak", r"keycloak|\bsso\b|\bidp\b"),
              ("prometheus", r"prometheus|monitoring stack"), ("redis", r"redis")]


def _available_logos():
    try:
        import import_drawio as I
        return I.logo_sources()
    except Exception:
        return {}


NOTE_RX = re.compile(r"^\s*\d+[.)]\s|^\s*(we |the |if |each |then )", re.I)


def is_note(label):
    """Etape numerotee ou phrase de commentaire (diagramme de sequence) : une note, pas un composant."""
    t = (label or "").strip()
    return bool(NOTE_RX.search(t)) or len(t) > 60


def classify(label):
    t = (label or "").lower()
    for color, role, rx in RULES:
        if re.search(rx, t):
            return color, role
    return None, None


def _pad(hz):
    """Marge d'un cadre de zone selon la profondeur de sous-zones (meme formule que build_html)."""
    return ZPAD + hz * (ZPAD // 2 + 6)


def enrich(model, page=None, cluster=True):
    ns_name = ((model.get("meta") or {}).get("project") or "applicatif").strip()
    m = json.loads(json.dumps(model))  # copie
    views = m.get("views") or []
    if page:
        sel = [v for v in views if v.get("label") == page or v.get("id") == page]
        if not sel:
            raise ValueError(f"page introuvable : {page} ({', '.join(v.get('label', '') for v in views)})")
        views = sel
    view = dict(views[0])
    members = [x for x in view.get("members", [])]
    ent = {e["id"]: e for e in m.get("entities", [])}
    members = [x for x in members if x in ent]
    mset = set(members)
    zones = m.get("zones", [])
    zid = {z["id"]: z for z in zones}

    # zones utiles = celles des membres + leurs ancetres
    keep = set()
    for x in members:
        z = ent[x].get("zone")
        while z and z in zid and z not in keep:
            keep.add(z)
            z = zid[z].get("parent")
    zones = [z for z in zones if z["id"] in keep]
    zid = {z["id"]: z for z in zones}

    # 1. roles
    zrole = {}
    for z in zones:
        c, r = classify(z.get("label"))
        zrole[z["id"]] = r
        if c:
            z["color"] = c
    erole = {}
    notes = {x for x in members if is_note(ent[x].get("label"))}
    for x in members:
        e = ent[x]
        if x in notes:
            e["color"] = "ext"
            continue
        c, r = classify(e.get("label"))
        zr = zrole.get(e.get("zone"))
        zc = zid.get(e.get("zone"), {}).get("color")
        if r == "api":                      # l'entree API ressort, ou qu'elle soit
            e["color"], erole[x] = c, r
        else:
            erole[x] = zr or r
            if not e.get("logo") and (zc or c):
                e["color"] = zc or c

    # 2. chemin principal
    api_ids = {x for x in members if erole.get(x) == "api"}
    core_ids = {x for x in members if x not in api_ids
                and zid.get(ent[x].get("zone"), {}).get("color") == "core"}
    flows = [f for f in m.get("flows", []) if f.get("from") in mset and f.get("to") in mset]
    for f in flows:
        if f["from"] in core_ids or f["to"] in api_ids:
            f["main"] = True

    # 3. loupes + vues detail par zone
    detail, used_vids = [], {"overview"}
    for z in zones:
        zm = [x for x in members if ent[x].get("zone") == z["id"]]
        sub = [s for s in zones if s.get("parent") == z["id"]]
        def under(x, zz=z["id"]):
            c, seen = ent[x].get("zone"), set()
            while c and c not in seen:
                if c == zz:
                    return True
                seen.add(c)
                c = zid.get(c, {}).get("parent")
            return False
        if all(under(x) for x in members):
            continue
        if len(zm) + sum(1 for x in members if ent[x].get("zone") in {s["id"] for s in sub}) >= 2:
            base = "z-" + re.sub(r"[^a-z0-9]+", "-", (z.get("label") or z["id"]).lower()).strip("-")
            vid, k = base, 2
            while vid in used_vids:
                vid, k = f"{base}-{k}", k + 1
            used_vids.add(vid)
            allm = [x for x in members if ent[x].get("zone") in {z["id"]} | {s["id"] for s in sub}]
            z["link"] = vid
            detail.append({"id": vid, "label": z.get("label") or vid, "members": allm})

    # 4. cadre Kubernetes (EKS) > Namespace autour de la plateforme
    roots = [z for z in zones if not z.get("parent")]
    # zone englobante unique sans entite propre (ex. « SAI INFRASTRUCTURE » = le compte AWS) : le
    # cluster se pose DEDANS, comme « Safran.AI - AWS > Kubernetes (EKS) > Namespace » du schema par defaut
    host = None
    if len(roots) == 1 and not any(ent[x].get("zone") == roots[0]["id"] for x in members):
        host = roots[0]
        roots = [z for z in zones if z.get("parent") == host["id"]]
    if cluster and roots:
        zones.append({"id": "z-eks", "label": "Kubernetes (EKS)", "parent": host["id"] if host else None,
                      "color": "cluster"})
        zones.append({"id": "z-ns", "label": f"Namespace {ns_name}", "parent": "z-eks", "color": "service"})
        for z in roots:
            z["parent"] = "z-ns"
        zid = {z["id"]: z for z in zones}
        head = ([host["id"]] if host else []) + ["z-eks", "z-ns"]
        zones = [zid[i] for i in head] + [z for z in zones if z["id"] not in head]

    # 5. mise en page en etages
    def zrank(z):
        r = zrole.get(z["id"])
        subs = [s for s in zones if s.get("parent") == z["id"]]
        rs = [RANK.get(zrole.get(s["id"]), 9) for s in subs] + ([RANK.get(r, 9)] if r else [])
        if any(erole.get(x) == "api" and ent[x].get("zone") == z["id"] for x in members):
            return RANK["api"]
        return min(rs) if rs else 9

    def height(z):
        kids = [s for s in zones if s.get("parent") == z["id"]]
        return 0 if not kids else 1 + max(height(k) for k in kids)

    def block(z):
        """Retourne (w, h, placements[(id, x, y)]) d'une zone, positions relatives au coin du cadre."""
        hz = height(z)
        pad, top = _pad(hz), _pad(hz) + ZTITLE * (1 + hz)
        subs = sorted([s for s in zones if s.get("parent") == z["id"]], key=zrank)
        own = [x for x in members if ent[x].get("zone") == z["id"]]
        items = []                                   # (w, h, placements, rang)
        if own:
            if subs:
                cols = min(3, len(own))
            else:
                cols = 1 if len(own) <= 2 else 2
            rows = -(-len(own) // cols)
            pl = [(x, (i % cols) * (NODE_W + GAP), (i // cols) * (NODE_H + GAP)) for i, x in enumerate(own)]
            items.append((cols * NODE_W + (cols - 1) * GAP, rows * NODE_H + (rows - 1) * GAP, pl,
                          RANK.get(zrole.get(z["id"]), 9)))
        for s in subs:
            w, h, pl = block(s)
            items.append((w, h, pl, zrank(s)))
        if not items:
            return 2 * pad, top + pad, []
        # etages : le namespace, ou toute zone de regroupement pur (que des sous-zones, au moins 2)
        layered = z["id"] == "z-ns" or (not own and len(subs) >= 2)
        out = []
        if layered:                                  # etages : un rang par ligne, centre
            by = {}
            for it in items:
                by.setdefault(it[3], []).append(it)
            lines = []
            for k in sorted(by):                     # un etage trop large se replie sur plusieurs lignes
                cur, w = [], 0
                for it in by[k]:
                    if cur and w + GAP + it[0] > MAXW:
                        lines.append(cur); cur, w = [], 0
                    cur.append(it); w += (GAP if w else 0) + it[0]
                lines.append(cur)
            widths = [sum(i[0] for i in L) + GAP * (len(L) - 1) for L in lines]
            W = max(widths)
            y = top
            for L, lw in zip(lines, widths):
                x = pad + (W - lw) / 2
                for w, h, pl, _ in L:
                    out += [(i, x + px, y + py) for i, px, py in pl]
                    x += w + GAP
                y += max(i[1] for i in L) + GAP * 2
            return W + 2 * pad, y - GAP * 2 + pad, out
        items.sort(key=lambda it: it[3])             # sinon : en ligne, sens de la donnee
        x, H = pad, max(i[1] for i in items)
        for w, h, pl, _ in items:
            out += [(i, x + px, top + (H - h) / 2 + py) for i, px, py in pl]
            x += w + GAP
        return x - GAP + pad, top + H + pad, out

    layout = {}
    if cluster and roots:
        _, _, pl = block(host if host else zid["z-eks"])
        for i, x, y in pl:
            layout[i] = [round(x), round(y)]
    else:  # pas de cadre : etages au niveau racine via une zone virtuelle
        zones.append({"id": "z-ns", "label": "", "parent": None})
        for z in roots:
            z["parent"] = "z-ns"
        _, _, pl = block({"id": "z-ns"})
        for z in roots:
            z["parent"] = None
        zones = [z for z in zones if z["id"] != "z-ns"]
        for i, x, y in pl:
            layout[i] = [round(x), round(y)]
    # hors zone : sous le reste
    yb = max([v[1] for v in layout.values()] + [0]) + NODE_H + GAP * 3
    loose = [x for x in members if x not in layout]
    cols = max(1, min(6, int(MAXW // (NODE_W + GAP))))
    for k, x in enumerate(loose):                    # hors zone : en grille sous le reste
        layout[x] = [(k % cols) * (NODE_W + GAP), yb + (k // cols) * (NODE_H + GAP)]

    view = {"id": "overview", "label": view.get("label") or "Vue d'ensemble", "members": members, "layout": layout}

    # 6. couches + questions systematiques
    groups = {}
    for x in members:
        if x in notes:
            continue
        groups.setdefault(erole.get(x) or "autres", []).append(x)
    LAYER_COLOR = {"processing": "core", "data": "storage", "api": "core", "partners": "partner",
                   "identity": "auth", "ops": "ops"}
    LABELS = {"data": "Données et stockage", "processing": "Traitement", "api": "REST API / BFF",
              "partners": "Partenaires", "identity": "SSO / identité", "front": "Front",
              "ops": "Exploitation", "autres": "Autres"}
    layers = []
    for r, xs in groups.items():
        layers.append({"id": r, "label": LABELS.get(r, r), "members": xs, "role": r if r != "autres" else None,
                       "color": LAYER_COLOR.get(r), "main": r in ("processing", "api"), "default": "detail"})
    q = []
    for key, label in SYSTEMATIC:
        if key == "cluster":
            n = len([x for x in members if ent[x].get("zone") in keep])
            q.append({"couche": label, "present": bool(cluster), "question":
                      f"Encadrer la plateforme ({n} entités) dans « Kubernetes (EKS) > Namespace {ns_name} » ? "
                      "Puis : la replier en un seul bloc dans la vue d'ensemble, ou la laisser dépliée ?",
                      "proposition": "encadrer, laisser déplié (c'est la vue détaillée)"})
            continue
        xs = groups.get(key, [])
        if xs:
            noms = ", ".join(list(dict.fromkeys(ent[x].get("label", x) for x in xs))[:4])
            q.append({"couche": label, "present": True, "question":
                      f"Replier « {label} » ({noms}) en un bloc avec loupe dans la vue d'ensemble ?",
                      "proposition": "replier" if key != "api" else "laisser déplié (chemin principal)"})
        else:
            q.append({"couche": label, "present": False, "question":
                      f"Aucun nœud « {label} » sur cette page. Ajouter une section {label} (à nommer par toi), "
                      "ou la laisser à une autre vue ?",
                      "proposition": "laisser à une autre vue (rien n'est inventé)"})

    m["zones"] = zones
    m["entities"] = [ent[x] for x in members]
    m["flows"] = flows
    m["views"] = [view] + detail
    m["layers"] = layers
    # logos de zone : modele d'abord (logos deduits a l'import), sinon bibliotheque partagee
    avail = None
    for z in zones:
        if z.get("logo"):
            continue
        for key, rx in ZONE_LOGOS:
            if re.search(rx, (z.get("label") or "").lower()):
                if key not in (m.get("logos") or {}):
                    avail = avail if avail is not None else _available_logos()
                    if key not in avail:
                        break
                    m.setdefault("logos", {})[key] = avail[key]
                z["logo"] = key
                break
    m.pop("palette", None)   # palette du modele importe (souvent noir pur) : on laisse le defaut
    m["meta"] = {**(m.get("meta") or {}), "project": view["label"]}
    return m, q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("-o", dest="out", required=True)
    ap.add_argument("--page")
    ap.add_argument("--no-cluster", action="store_true")
    a = ap.parse_args()
    m, q = enrich(json.load(open(a.model, encoding="utf-8")), a.page, not a.no_cluster)
    json.dump(m, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"ecrit": a.out, "questions": q}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
