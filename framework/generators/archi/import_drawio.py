#!/usr/bin/env python3
"""import_drawio - fichier .drawio (mxGraph) -> model.json (schema model-first, SCHEMA.md).

Symetrique de export_drawio.py : relit un .drawio (genere par le framework OU dessine a la main
dans draw.io) et reconstruit le modele - zones, entites, flux, vues + membres - pret a passer au
harness et a build_html. Le round-trip est fidele sur les .drawio produits par le framework
(memes ids, conteneurs zone-<id>, aretes). Sur un .drawio dessine a la main, c'est un point de
depart a reprendre (les logos ne sont pas recuperables depuis un data-URI : logo=null).

    python3 import_drawio.py mon_schema.drawio [-o model.json] [--logos-from <schema.html|model.json|logos/>]

Sur un draw.io dessine a la main : zones deduites par imbrication geometrique, fleches posees sans
accroche rattachees au plus petit sommet sous leur extremite, libelles de fleches (edgeLabel) repris,
logos deduits des libelles (bibliotheque partagee + source de reference, ex. le schema par defaut).

Gere les pages draw.io en XML clair ET compressees (base64 + deflate brut, defaut de l'appli).
Lecture seule cote source : lit le .drawio, ecrit UNIQUEMENT le model.json de sortie.
"""
import sys, os, re, json, base64, zlib, html
from urllib.parse import unquote
import xml.etree.ElementTree as ET


def _decode_diagram(text):
    t = (text or "").strip()
    if t.startswith("<"):
        return t
    try:
        raw = base64.b64decode(t)
        return unquote(zlib.decompress(raw, -15).decode("utf-8"))
    except Exception:
        return t


def _label_sub(value):
    """'<b>BFF</b><br><font ...>API</font>' -> ('BFF', 'API'). Tolere le texte brut."""
    v = (value or "").replace("<br/>", "<br>").replace("<br />", "<br>")
    parts = v.split("<br>", 1)
    clean = lambda t: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()
    label = clean(parts[0])
    sub = clean(parts[1]) if len(parts) > 1 else ""
    return label, sub


def _is_container(style):
    return "container=1" in (style or "")


def _is_edge_style(style):
    return "edgeStyle" in (style or "") or "endArrow" in (style or "")


def _kind(style):
    return "pull" if "startArrow=classic" in (style or "") else "call"


def _cells(model_root):
    """Normalise objects (cellules liees) et mxCell bruts en dicts homogenes."""
    inner = {id(o.find("mxCell")) for o in model_root.iter("object") if o.find("mxCell") is not None}
    out = []
    for o in model_root.iter("object"):
        c = o.find("mxCell")
        if c is None:
            continue
        out.append({"id": o.get("id"), "value": o.get("label", ""), "style": c.get("style", ""),
                    "parent": c.get("parent"), "vertex": c.get("vertex"), "edge": c.get("edge"),
                    "source": c.get("source"), "target": c.get("target"), "geo": c.find("mxGeometry")})
    for c in model_root.iter("mxCell"):
        if id(c) in inner:
            continue
        out.append({"id": c.get("id"), "value": c.get("value", ""), "style": c.get("style", ""),
                    "parent": c.get("parent"), "vertex": c.get("vertex"), "edge": c.get("edge"),
                    "source": c.get("source"), "target": c.get("target"), "geo": c.find("mxGeometry")})
    return out


def _geo(c):
    g = c.get("geo")
    if g is None or g.get("relative") == "1":
        return None
    f = lambda k: float(g.get(k, 0) or 0)
    return f("x"), f("y"), f("width"), f("height")


def _abs_rects(cells):
    """Rectangles ABSOLUS des sommets (les coordonnees draw.io sont relatives au parent)."""
    by_id = {c["id"]: c for c in cells}
    memo = {}

    def rect(cid, depth=0):
        if cid in memo:
            return memo[cid]
        c = by_id.get(cid)
        r = _geo(c) if c else None
        if r is None or depth > 30:
            memo[cid] = None
            return None
        x, y, w, h = r
        p = c.get("parent")
        if p and p in by_id and by_id[p].get("vertex") == "1":
            pr = rect(p, depth + 1)
            if pr:
                x, y = x + pr[0], y + pr[1]
        memo[cid] = (x, y, w, h)
        return memo[cid]

    return {c["id"]: rect(c["id"]) for c in cells if c.get("vertex") == "1"}


def _inside(inner, outer, tol=4):
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    return (ix >= ox - tol and iy >= oy - tol and ix + iw <= ox + ow + tol and iy + ih <= oy + oh + tol
            and iw * ih < ow * oh)


def _at_point(pt, rects, ids):
    """Plus petit sommet (parmi ids) qui contient le point : extremite d'une fleche posee sans accroche."""
    best = None
    for i in ids:
        r = rects.get(i)
        if not r or not r[2]:
            continue
        x, y, w, h = r
        if x - 6 <= pt[0] <= x + w + 6 and y - 6 <= pt[1] <= y + h + 6:
            if best is None or w * h < best[1]:
                best = (i, w * h)
    return best[0] if best else None


def build_model(data):
    diagrams = re.findall(r'<diagram([^>]*)>(.*?)</diagram>', data, re.S)
    if not diagrams:
        diagrams = [("", data)]
    zones, entities, flows, views = {}, {}, [], []
    seen_flow = set()
    for attrs, body in diagrams:
        vid = (re.search(r'id="([^"]*)"', attrs) or [None, None])[1]
        name = (re.search(r'name="([^"]*)"', attrs) or [None, None])[1]
        try:
            root = ET.fromstring(_decode_diagram(body))
        except Exception as e:
            print(f"page '{name or vid}': illisible ({e})", file=sys.stderr)
            continue
        cells = _cells(root)
        by_id = {c["id"]: c for c in cells}
        edge_ids = {c["id"] for c in cells if c.get("edge") == "1" or _is_edge_style(c["style"])}
        # libelles portes par des cellules « edgeLabel » enfants d'une fleche
        edge_label = {}
        for c in cells:
            if c.get("vertex") == "1" and c.get("parent") in edge_ids:
                t, _ = _label_sub(c["value"])
                if t:
                    edge_label.setdefault(c["parent"], t)
        rects = _abs_rects(cells)

        # sommets utiles : ni plaque/logo du framework, ni libelle de fleche, ni fond vide
        verts = []
        for c in cells:
            cid = c["id"]
            if not cid or cid in ("0", "1") or c.get("vertex") != "1" or cid in edge_ids:
                continue
            if cid.endswith("--plate") or cid.endswith("--logo") or c.get("parent") in edge_ids:
                continue
            verts.append(c)
        framework_made = any(c["id"].startswith("zone-") for c in verts)

        # zones : conteneurs declares (framework) OU, sur un draw.io dessine a la main,
        # un sommet titre qui en contient d'autres geometriquement
        is_zone = {}
        for c in verts:
            label, _ = _label_sub(c["value"])
            if _is_container(c["style"]) or c["id"].startswith("zone-"):
                is_zone[c["id"]] = True
            elif not framework_made and label and rects.get(c["id"]):
                r = rects[c["id"]]
                is_zone[c["id"]] = any(o is not c and rects.get(o["id"]) and _inside(rects[o["id"]], r)
                                       for o in verts)

        def zid_of(cid):
            return cid[5:] if cid.startswith("zone-") else cid

        def zone_parent(c):
            p = c.get("parent") or ""
            if p.startswith("zone-") or is_zone.get(p):
                return zid_of(p)
            if framework_made or not rects.get(c["id"]):
                return None
            best = None
            for o in verts:
                if is_zone.get(o["id"]) and o is not c and rects.get(o["id"]) and _inside(rects[c["id"]], rects[o["id"]]):
                    a = rects[o["id"]][2] * rects[o["id"]][3]
                    if best is None or a < best[1]:
                        best = (o["id"], a)
            return zid_of(best[0]) if best else None

        members = []
        for c in verts:
            label, sub = _label_sub(c["value"])
            if is_zone.get(c["id"]):
                zid = zid_of(c["id"])
                zones.setdefault(zid, {"id": zid, "label": label, "parent": zone_parent(c)})
                continue
            if not label:
                continue                      # forme vide (fond, decor)
            members.append(c["id"])
            entities.setdefault(c["id"], {"id": c["id"], "label": label, "sub": sub,
                                          "zone": zone_parent(c), "logo": None})

        targets = members + [c["id"] for c in verts if is_zone.get(c["id"])]
        for c in cells:
            if c["id"] not in edge_ids:
                continue
            a, b = c.get("source"), c.get("target")
            g = c.get("geo")
            pts = {}
            if g is not None:
                for p in g.findall("mxPoint"):
                    if p.get("as") in ("sourcePoint", "targetPoint"):
                        pts[p.get("as")] = (float(p.get("x", 0) or 0), float(p.get("y", 0) or 0))
            a = a if a in by_id else (_at_point(pts["sourcePoint"], rects, targets) if "sourcePoint" in pts else None)
            b = b if b in by_id else (_at_point(pts["targetPoint"], rects, targets) if "targetPoint" in pts else None)
            if not a or not b or a == b:
                continue
            a, b = (zid_of(x) if is_zone.get(x) else x for x in (a, b))
            lbl = _label_sub(c["value"])[0] or edge_label.get(c["id"], "")
            key = (a, b, lbl)
            if key not in seen_flow:
                seen_flow.add(key)
                flows.append({"from": a, "to": b, "label": lbl, "kind": _kind(c["style"])})
        if vid or name:
            views.append({"id": vid or re.sub(r"\W+", "_", name or "vue").strip("_"),
                          "label": name or vid, "members": members})
    model = {
        "meta": {"project": "import", "owner": "", "theme": "dark"},
        "palette": {"bg": "#000000", "surface": "#171b22", "ink": "#e8ebf0", "ink2": "#a2abba",
                    "accent": "#6fa2d6", "border": "#2a303b"},
        "logos": {},
        "zones": list(zones.values()),
        "entities": list(entities.values()),
        "flows": flows,
        "views": views,
    }
    return model


# --------------------------------------------------------------- logos deduits
# mot-cle (dans label / sub, en minuscules) -> cle de logo. Les cles techno existent dans
# framework/assets/logos/ ; les cles de marque (airbus, ksat...) viennent d'une source de reference
# (--logos-from : le schema par defaut d'une mission, son model.json ou son dossier logos/).
LOGO_KEYWORDS = [
    ("airflow", ("airflow", " dag")), ("keycloak", ("keycloak", "identity broker")),
    ("kubernetes", ("kubernetes", "eks", "k8s")), ("prometheus", ("prometheus",)),
    ("redis", ("redis",)), ("terraform", ("terraform",)), ("argocd", ("argo",)), ("argo", ("argo",)),
    ("fluxcd", ("flux",)), ("flux", ("flux",)), ("react", ("frontend", "react")),
    ("aws", ("aws", "s3", "bucket", "rds", "amazon")), ("user", ("end-user", "utilisateur", "user")),
    ("airbus", ("airbus", "change monitoring")), ("ksat", ("ksat", "maritim")), ("iceye", ("iceye",)),
    ("nato", ("nato", "otan")), ("enix", ("enix",)), ("safran", ("safran",)),
]
_MIME = {".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def _logos_from_dir(d):
    out = {}
    if d and os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            k, ext = os.path.splitext(f)
            if ext.lower() in _MIME:
                raw = open(os.path.join(d, f), "rb").read()
                out[k] = f"data:{_MIME[ext.lower()]};base64," + base64.b64encode(raw).decode("ascii")
    return out


def _logos_from_file(p):
    """window.LOGOS d'un HTML de schema, ou `logos` d'un model.json."""
    txt = open(p, encoding="utf-8").read()
    if p.endswith(".json"):
        return dict(json.loads(txt).get("logos") or {})
    m = re.search(r"window\.LOGOS\s*=\s*(\{.*?\})\s*;?\s*</script>", txt, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except ValueError:
        return {}


def logo_sources(extra=()):
    """Logos disponibles : bibliotheque partagee du framework + sources fournies (fichier ou dossier)."""
    here = os.path.dirname(os.path.abspath(__file__))
    lib = os.path.normpath(os.path.join(here, "..", "..", "assets", "logos"))
    avail = _logos_from_dir(lib)
    for src in extra or ():
        if not src:
            continue
        try:
            avail.update(_logos_from_dir(src) if os.path.isdir(src) else _logos_from_file(src))
        except OSError:
            pass
    return avail


def deduce_logos(model, available):
    """Affecte un logo aux entites sans logo d'apres leur libelle ; embarque les data-URI utilisees.
    Retourne la liste (entite, cle). N'invente rien : seulement des cles presentes dans `available`."""
    done = []
    for e in model.get("entities") or []:
        if e.get("logo"):
            continue
        text = f" {e.get('label', '')} {e.get('sub') or ''} ".lower()
        for key, words in LOGO_KEYWORDS:
            if key in available and any(w in text for w in words):
                e["logo"] = key
                model.setdefault("logos", {})[key] = available[key]
                done.append((e["id"], key))
                break
    return done


def main():
    if len(sys.argv) < 2:
        print("usage: python3 import_drawio.py mon_schema.drawio [-o model.json]")
        sys.exit(1)
    src = sys.argv[1]
    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None
    data = open(src, encoding="utf-8").read()
    model = build_model(data)
    srcs = []
    if "--logos-from" in sys.argv:
        i = sys.argv.index("--logos-from")
        srcs = [x for x in sys.argv[i + 1:] if not x.startswith("-")][:3]
    deduced = deduce_logos(model, logo_sources(srcs))
    out = out or os.path.splitext(src)[0] + ".model.json"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(model, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Ecrit : {out}")
    print(f"Modele : {len(model['zones'])} zone(s), {len(model['entities'])} entite(s), "
          f"{len(model['flows'])} flux, {len(model['views'])} vue(s)")
    print(f"Logos deduits des libelles : {len(deduced)} " + ", ".join(f"{e}={k}" for e, k in deduced[:12]))
    print("A relire (logos, zones, flux), puis --render + harness.")


if __name__ == "__main__":
    main()
