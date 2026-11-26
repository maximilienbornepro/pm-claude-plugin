#!/usr/bin/env python3
"""abstraction - profondeur de chaque COUCHE d'un schéma, décidée AVEC la personne.

Un modèle peut déclarer des couches (`layers`, voir SCHEMA.md) : des groupes d'entités qu'on peut,
dans la vue d'ensemble (première vue), montrer de trois façons :

    detail    : les entités de la couche sont affichées telles quelles ;
    abstrait  : la couche devient UN bloc cliquable (loupe) qui mène à sa vue de détail ;
    masque    : la couche n'apparaît pas (ni ses flux).

Le module ne décide pas seul : il PROPOSE une profondeur par couche, avec la raison, et produit
les QUESTIONS à poser (public d'abord, puis couche par couche). Les réponses sont enregistrées dans
`abstraction.json`, à côté du modèle.

    apply(model, modes)            -> nouveau modèle (vue d'ensemble transformée)
    questions(model, modes, public)-> liste de questions (dict) prêtes à poser
    load(path) / save(path, ...)   -> lecture / écriture de abstraction.json
"""
import copy
import json
from pathlib import Path

MODES = ("detail", "abstrait", "masque")

# Préréglages par public. Ils s'appuient sur le `role` des couches (optionnel) :
#   data, processing, api, identity, front, partners, ops, actors
PUBLICS = {
    "direction": {
        "label": "Direction / COPIL",
        "why": "lecture en 30 secondes : des blocs, le détail au clic",
        "rule": lambda L: "masque" if L.get("role") == "ops" else "abstrait",
    },
    "tech": {
        "label": "Équipe technique",
        "why": "le chemin de la donnée déplié quand il reste lisible",
        "rule": lambda L: ("detail" if L.get("main") and _size(L) <= 3 else "abstrait"),
    },
    "exploitation": {
        "label": "Exploitation / sécurité",
        "why": "l'exploitation dépliée, le reste en blocs",
        "rule": lambda L: "detail" if L.get("role") == "ops" else "abstrait",
    },
    "partenaires": {
        "label": "Partenaires",
        "why": "les partenaires dépliés, l'exploitation masquée",
        "rule": lambda L: ("detail" if L.get("role") == "partners"
                           else "masque" if L.get("role") == "ops" else "abstrait"),
    },
}

DENSE_NODES = 4   # à partir de 4 entités...
DENSE_FLOWS = 5   # ...ou 5 flux internes, une couche est trop dense pour la vue d'ensemble


def _pl(n, mot):
    return f"{n} {mot}{'s' if n > 1 else ''}"


def _size(layer):
    return len(layer.get("members") or [])


def layers(model):
    return [L for L in (model.get("layers") or []) if isinstance(L, dict) and L.get("id")]


def internal_flows(model, layer):
    m = set(layer.get("members") or [])
    return [f for f in model.get("flows") or [] if f.get("from") in m and f.get("to") in m]


def maskable(layer):
    """Une couche du chemin principal ne se masque pas (sinon le schéma ment)."""
    return layer.get("maskable", not layer.get("main", False))


def suggest(model, layer, public=None):
    """(mode proposé, raison) pour une couche."""
    n, f = _size(layer), len(internal_flows(model, layer))
    if public in PUBLICS:
        p = PUBLICS[public]
        mode = p["rule"](layer)
        if mode == "masque" and not maskable(layer):
            mode = "abstrait"
        return mode, f"public « {p['label']} » : {p['why']} ({_pl(n, 'élément')}, {_pl(f, 'flux interne')})."
    if n >= DENSE_NODES or f >= DENSE_FLOWS:
        return "abstrait", f"{_pl(n, 'élément')} et {_pl(f, 'flux interne')} : trop dense pour la vue d'ensemble, le détail reste au clic."
    if layer.get("main"):
        return "detail", f"seulement {_pl(n, 'élément')}, sur le chemin principal de la donnée : les montrer aide à lire le flux."
    if maskable(layer):
        return "abstrait", f"hors chemin principal ({_pl(n, 'élément')}) : un bloc suffit ; à masquer si ce public n'en a pas besoin."
    return "abstrait", "un bloc par défaut."


def default_modes(model):
    return {L["id"]: (L.get("default") if L.get("default") in MODES else "abstrait") for L in layers(model)}


def questions(model, modes=None, public=None):
    """Questions à poser, dans l'ordre : le public, puis chaque couche (proposition + raison)."""
    modes = modes or default_modes(model)
    out = [{"id": "_public", "question": "Pour quel public construit-on la vue d'ensemble ?",
            "actuel": public, "proposition": public or "direction",
            "raison": "le public oriente toutes les propositions suivantes",
            "options": {k: v["label"] for k, v in PUBLICS.items()}}]
    for L in layers(model):
        mode, why = suggest(model, L, public)
        opts = [m for m in MODES if m != "masque" or maskable(L)]
        out.append({"id": L["id"], "question": f"Couche « {L.get('label', L['id'])} » : quelle profondeur au niveau 1 ?",
                    "actuel": modes.get(L["id"]), "proposition": mode, "raison": why, "options": opts})
    return out


def load(path):
    """abstraction.json -> (public, modes). Absent ou illisible -> (None, {})."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None, {}
    return d.get("_public"), {k: v for k, v in d.items() if not k.startswith("_") and v in MODES}


def save(path, public, modes):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    json.dump({"_public": public, **modes}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def parse_set(model, text, modes):
    """'couche=mode,couche=mode' -> modes mis à jour. Lève ValueError si invalide."""
    by_id = {L["id"]: L for L in layers(model)}
    for kv in [x for x in (text or "").split(",") if x.strip()]:
        k, _, v = kv.strip().partition("=")
        if k not in by_id:
            raise ValueError(f"couche inconnue : {k} (couches : {', '.join(by_id) or 'aucune'})")
        if v not in MODES:
            raise ValueError(f"mode inconnu : {v} ({', '.join(MODES)})")
        if v == "masque" and not maskable(by_id[k]):
            raise ValueError(f"la couche {k} est sur le chemin principal : elle ne peut pas être masquée")
        modes[k] = v
    return modes


def apply(model, modes=None, view_index=0):
    """Applique les modes à la vue `view_index` (la vue d'ensemble par défaut).

    - abstrait : les membres de la couche présents dans la vue sont remplacés par une entité
      synthétique `couche-<id>` (label, sub, logo, color de la couche) cliquable vers la vue de
      détail de la couche ; les flux sont rebranchés sur ce bloc, les flux internes retirés, les
      doublons fusionnés. Si la couche ne déclare pas de `link` vers une vue existante, une vue de
      détail `couche-<id>` est créée (membres de la couche) pour que le clic mène quelque part.
    - masque   : membres et flux de la couche retirés de la vue.
    - detail   : rien ne change.
    """
    Ls = layers(model)
    if not Ls or not model.get("views"):
        return model
    m = copy.deepcopy(model)
    modes = {**default_modes(m), **(modes or {})}
    views = m["views"]
    view_ids = {v["id"] for v in views}
    target = views[view_index]
    members = list(target.get("members") or [])
    layout = dict(target.get("layout") or {})
    ent_by_id = {e["id"]: e for e in m.get("entities") or []}
    remap, hidden = {}, set()

    for L in Ls:
        mode = modes.get(L["id"], "abstrait")
        lm = [x for x in (L.get("members") or []) if x in members]
        if mode == "detail" or not lm:
            continue
        if mode == "masque" and maskable(L):
            hidden.update(lm)
            members = [x for x in members if x not in lm]
            continue
        sid = f"couche-{L['id']}"
        link = L.get("link") if L.get("link") in view_ids else None
        if not link:
            link = sid
            if sid not in view_ids:
                views.append({"id": sid, "label": L.get("label", L["id"]), "members": list(L.get("members") or [])})
                view_ids.add(sid)
        zones_of = {ent_by_id[x].get("zone") for x in lm if x in ent_by_id}
        zone = zones_of.pop() if len(zones_of) == 1 else L.get("zone")
        # la couche recouvre toute la zone dans cette vue : le bloc remonte d'un cran, sinon le cadre
        # de zone n'entourerait plus que lui (doublon visuel)
        if zone and all(x in lm for x in members if ent_by_id.get(x, {}).get("zone") == zone):
            zone = {z["id"]: z for z in m.get("zones") or []}.get(zone, {}).get("parent")
        ent = {"id": sid, "label": L.get("label", L["id"]), "sub": L.get("sub"),
               "logo": L.get("logo"), "color": L.get("color"), "link": link, "zone": zone}
        m.setdefault("entities", []).append(ent)
        ent_by_id[sid] = ent
        first = members.index(lm[0])
        members = [x for x in members if x not in lm]
        members.insert(min(first, len(members)), sid)
        if lm[0] in layout and sid not in layout:
            layout[sid] = layout[lm[0]]
        for x in lm:
            remap[x] = sid

    # Les flux d'origine restent (les vues de détail en ont besoin ; dans la vue d'ensemble ils ne
    # s'affichent plus car leurs extrémités n'y sont plus membres). On AJOUTE les flux rebranchés
    # sur les blocs de couche, réservés à la vue d'ensemble (`_only_in`).
    flows, seen = list(m.get("flows") or []), {}
    for f in m.get("flows") or []:
        a, b = f.get("from"), f.get("to")
        if a in hidden or b in hidden:
            continue
        a2, b2 = remap.get(a, a), remap.get(b, b)
        if (a2, b2) == (a, b) or a2 == b2:
            continue                       # inchangé, ou interne à une couche abstraite
        key = (a2, b2)
        if key in seen:
            prev = seen[key]               # plusieurs flux fusionnés en une flèche : libellés réunis
            labels = [x for x in (prev.get("label") or "").split(" · ") if x]
            if f.get("label") and f["label"] not in labels:
                labels.append(f["label"])
            prev["label"] = " · ".join(labels[:3])
            prev["main"] = prev.get("main") or f.get("main")
            if prev.get("kind") != f.get("kind"):
                prev["kind"] = "call"
            continue
        g = dict(f, **{"from": a2, "to": b2, "_only_in": target["id"]})
        seen[key] = g
        flows.append(g)
    m["flows"] = flows
    target["members"] = members
    if layout:
        target["layout"] = {k: v for k, v in layout.items() if k in members}
    return m
