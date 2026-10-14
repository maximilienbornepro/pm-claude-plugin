#!/usr/bin/env python3
"""
Harness de validation d'une "stack imagery" (schéma d'infra interactif, un seul HTML).

Encode les invariants durement acquis sur le schéma SINBAD. Chacun correspond à un
bug réel rencontré pendant la construction : si on les respecte, le rendu ne casse pas.

    python3 validate.py <fichier.html>
    python3 validate.py reference/architecture_sinbad.golden.html

Sortie : une ligne par invariant (OK / ECHEC) + le détail des violations.
Code retour 0 si tout passe, 1 sinon. Aucune dépendance externe (stdlib only).
"""
import re, sys

# ---------------------------------------------------------------- utilitaires
def svgs(h):
    """Retourne la liste des (début, fin, contenu) de chaque <svg>...</svg>."""
    out = []
    for m in re.finditer(r'<svg\b.*?</svg>', h, re.S):
        out.append((m.start(), m.end(), m.group(0)))
    return out

def paths_in(seg):
    """Chemins <path ...> hors <defs>/<marker>, avec leurs attributs bruts."""
    # on retire les blocs <marker>...</marker> (pointes de flèches, volontairement diagonales)
    clean = re.sub(r'<marker\b.*?</marker>', '', seg, flags=re.S)
    return re.findall(r'<path\b([^>]*)>', clean)

def seg_points(d):
    """Points d'une polyligne droite absolue (M/L). None si courbe ou relatif (exempté)."""
    # courbes et arcs = tracés volontaires (boucles de type "session réutilisée") -> exemptés
    if re.search(r'[CcSsQqTtAa]', d):
        return None
    # 'l'/'m' relatifs (poignée de loupe) -> exemptés
    if re.search(r'[ml]', d):
        return None
    pts = []
    for t in re.findall(r'[ML][^MLZz]*', d):
        nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', t)]
        for i in range(0, len(nums) - 1, 2):
            pts.append((nums[i], nums[i+1]))
    return pts

# ------------------------------------------------------------------- checks
def check_balance(h):
    v = []
    if h.count('<svg') != h.count('</svg>'):
        v.append(f"svg déséquilibré : {h.count('<svg')} ouverts / {h.count('</svg>')} fermés")
    for i, (_, _, seg) in enumerate(svgs(h)):
        o = len(re.findall(r'<g[\s>]', seg)); c = seg.count('</g>')
        if o != c:
            lab = re.search(r'aria-label="([^"]{0,30})', seg)
            v.append(f"<g> déséquilibré dans svg[{lab.group(1) if lab else i}] : {o}/{c}")
    return v

def check_rectilinear(h):
    """Toute flèche (path avec marker-end, hors loupe/marker) est horizontale ou verticale."""
    v = []
    for i, (_, _, seg) in enumerate(svgs(h)):
        lab = re.search(r'aria-label="([^"]{0,30})', seg)
        name = lab.group(1) if lab else str(i)
        for at in paths_in(seg):
            if 'marker-end' not in at: continue
            if 'class="zoom"' in at: continue
            dm = re.search(r'\bd="([^"]+)"', at)
            if not dm: continue
            pts = seg_points(dm.group(1))
            if pts is None: continue
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                if abs(x1 - x2) > 0.5 and abs(y1 - y2) > 0.5:
                    v.append(f"flèche diagonale dans svg[{name}] : {dm.group(1)[:50]}")
                    break
    return v

def check_markers(h):
    """ids de marqueurs uniques sur tout le document ; chaque url(#id) résout dans son svg."""
    v = []
    all_ids = re.findall(r'<marker\b[^>]*\bid="([^"]+)"', h)
    seen = {}
    for mid in all_ids:
        seen[mid] = seen.get(mid, 0) + 1
    for mid, n in seen.items():
        if n > 1:
            v.append(f"id de marqueur dupliqué : '{mid}' défini {n} fois (pointes invisibles garanties)")
    for i, (_, _, seg) in enumerate(svgs(h)):
        defined = set(re.findall(r'<marker\b[^>]*\bid="([^"]+)"', seg))
        used = set(re.findall(r'marker-end="url\(#([^)]+)\)"', seg))
        used |= set(re.findall(r'marker-start="url\(#([^)]+)\)"', seg))
        miss = used - defined
        if miss:
            lab = re.search(r'aria-label="([^"]{0,30})', seg)
            v.append(f"svg[{lab.group(1) if lab else i}] référence un marqueur absent de ce svg : {sorted(miss)}")
    return v

def check_tokens(h):
    """Tout var(--x) utilisé DANS LES SVG est défini dans le :root de base.
    (Les variables de chrome propres à un composant - ex. .xnav - sont scopées
    hors :root et légitimes ; seul le rendu du diagramme exige le :root de base.)"""
    v = []
    svg_text = " ".join(seg for _, _, seg in svgs(h))
    used = set(re.findall(r'var\((--[\w-]+)\)', svg_text))
    mroot = re.search(r':root\s*\{([^}]*)\}', h)  # premier :root = base
    base = set(re.findall(r'(--[\w-]+)\s*:', mroot.group(1))) if mroot else set()
    miss = sorted(used - base)
    if miss:
        v.append(f"tokens SVG utilisés mais absents du :root de base (invisibles en thème par défaut) : {miss}")
    return v

def check_navigation(h):
    """Chaque data-go a une vue v-<id> et une entrée dans le dictionnaire names."""
    v = []
    gos = set(re.findall(r'data-go="([a-z0-9_-]+)"', h))
    mnames = re.search(r'\bnames\s*=\s*\{([^}]*)\}', h)
    names = set(re.findall(r'["\']?([\w-]+)["\']?\s*:', mnames.group(1))) if mnames else set()
    for g in sorted(gos):
        if g in ('overview', 'home'): continue
        if f'id="v-{g}"' not in h:
            v.append(f"data-go=\"{g}\" sans vue correspondante (id=\"v-{g}\" manquant)")
        if g not in names:
            v.append(f"data-go=\"{g}\" sans libellé dans names (fil d'Ariane cassé)")
    if 'function back(' not in h and 'data-back' in h:
        v.append("bouton data-back présent mais pas de fonction back() : retour non géré")
    return v

def check_logos(h):
    """Chaque data-logo référencé existe dans window.LOGOS (sinon logo invisible)."""
    v = []
    used = set(re.findall(r'data-logo="([^"]+)"', h))
    m = re.search(r'window\.LOGOS\s*=\s*\{', h)
    keys = set()
    if m:
        start = h.index('{', m.start())
        depth, i = 0, start
        while i < len(h):
            if h[i] == '{': depth += 1
            elif h[i] == '}':
                depth -= 1
                if depth == 0: break
            i += 1
        keys = set(re.findall(r'["\']([\w.\- ]+)["\']\s*:', h[start:i+1]))
    elif not used:
        return v  # ni logos ni table : rien à vérifier
    miss = sorted(used - keys)
    if miss:
        v.append(f"logos référencés mais absents de window.LOGOS : {miss}")
    return v

def check_viewbox(h):
    """Chaque <svg> a un viewBox (sinon rendu imprévisible)."""
    v = []
    for i, (s0, _, seg) in enumerate(svgs(h)):
        head = seg[:seg.index('>') + 1] if '>' in seg else seg[:200]
        if 'viewBox=' not in head:
            lab = re.search(r'aria-label="([^"]{0,30})', seg)
            v.append(f"svg[{lab.group(1) if lab else i}] sans viewBox")
    return v

def _subtitles(h):
    """Textes des sous-titres de nœuds (<text class="s" ...>...</text>)."""
    out = []
    for m in re.findall(r'<text class="s"[^>]*>(.*?)</text>', h, re.S):
        t = re.sub(r'<[^>]+>', '', m)
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            out.append(t)
    return out

def check_subtitles_on_demand(h, golden_h):
    """RÈGLE : un sous-titre n'est JAMAIS généré automatiquement ; il n'est ajouté
    que sur demande EXPLICITE. Ce contrôle refuse tout sous-titre présent ici mais
    absent du golden (= ajouté depuis la dernière référence). Les sous-titres
    légitimement demandés s'acquittent en recalant le golden après validation."""
    from collections import Counter
    cur, gold = Counter(_subtitles(h)), Counter(_subtitles(golden_h))
    added = [s for s, n in cur.items() if n - gold.get(s, 0) > 0]
    return [f"sous-titre ajouté sans demande explicite : « {s} »  (sous-titres = sur demande uniquement)"
            for s in sorted(added)]

CHECKS = [
    ("Équilibre SVG / <g>",                check_balance),
    ("Flèches rectilignes (H/V)",          check_rectilinear),
    ("Marqueurs uniques et résolus",       check_markers),
    ("Tokens couleur définis dans :root",  check_tokens),
    ("Navigation (data-go / names / back)",check_navigation),
    ("Logos résolus (window.LOGOS)",       check_logos),
    ("viewBox présent par vue",            check_viewbox),
]

def main():
    args = sys.argv[1:]
    golden = None
    if "--golden" in args:
        i = args.index("--golden")
        golden = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    if not args:
        print("usage: python3 validate.py <fichier.html> [--golden <ref.golden.html>]"); sys.exit(2)
    h = open(args[0], encoding="utf-8").read()
    checks = list(CHECKS)
    if golden:
        gh = open(golden, encoding="utf-8").read()
        checks.append(("Sous-titres sur demande (aucun ajout auto vs golden)",
                       lambda hh, _g=gh: check_subtitles_on_demand(hh, _g)))
    ok = True
    for titre, fn in checks:
        viol = fn(h)
        if viol:
            ok = False
            print(f"ECHEC  {titre}")
            for x in viol[:20]:
                print(f"       - {x}")
            if len(viol) > 20:
                print(f"       … (+{len(viol)-20} autres)")
        else:
            print(f"OK     {titre}")
    print("\n" + ("TOUT PASSE — publication autorisée." if ok else "DES INVARIANTS SONT CASSES — ne pas publier."))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
