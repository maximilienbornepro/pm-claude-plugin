#!/usr/bin/env python3
"""yamlmin - parseur YAML d'un SOUS-ENSEMBLE, SANS dépendance (ni PyYAML).

Gère ce dont les configs du framework ont besoin et que `profile._mini_parse` ne gère pas :
l'IMBRICATION profonde - une liste de maps dont une clé porte une autre liste (ex. `gates:` ->
chaque gate a `criteria:` -> liste de maps). Blocs (indentation), listes (`- `), maps/listes en
ligne (`{a: 1, b: [x, y]}`), scalaires quotés/nombres/bool/null. Pas d'ancres, pas de multi-docs.

    import yamlmin; data = yamlmin.load(open(path).read())
"""


def _strip_comment(line):
    out, q = [], None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch; out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _split_commas(s):
    parts, depth, q, cur = [], 0, None, ""
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch; cur += ch
        elif ch in "{[":
            depth += 1; cur += ch
        elif ch in "}]":
            depth -= 1; cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip() != "":
        parts.append(cur)
    return parts


def _scalar(v):
    v = v.strip()
    if v == "" or v in ("null", "~"):
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v[0] == "{" and v[-1] == "}":
        d = {}
        for p in _split_commas(v[1:-1]):
            if ":" in p:
                k, val = p.split(":", 1); d[k.strip()] = _scalar(val)
        return d
    if v[0] == "[" and v[-1] == "]":
        inner = v[1:-1].strip()
        return [_scalar(x) for x in _split_commas(inner)] if inner else []
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def load(text):
    rows = []
    for raw in text.splitlines():
        s = _strip_comment(raw)
        if s.strip() == "":
            continue
        rows.append((len(s) - len(s.lstrip(" ")), s.strip()))
    val, _ = _parse(rows, 0)
    return val


def _parse(rows, i):
    """Parse le bloc qui commence à rows[i] (map ou liste). Rend (valeur, index suivant)."""
    if i >= len(rows):
        return None, i
    base = rows[i][0]
    if rows[i][1].startswith("- "):
        lst = []
        while i < len(rows) and rows[i][0] == base and rows[i][1].startswith("- "):
            item = rows[i][1][2:].strip()
            if item == "" or item[0] in "{[" or ":" not in item:
                lst.append(_scalar(item)); i += 1
            else:
                # l'item est « clé: … » : première ligne d'une map ; on recolle les lignes plus
                # profondes et on reparse, en rebasant l'indentation sur la colonne de l'item.
                off = base + 2
                sub = [(0, item)]
                j = i + 1
                while j < len(rows) and rows[j][0] > base:
                    sub.append((rows[j][0] - off, rows[j][1])); j += 1
                m, _ = _parse(sub, 0); lst.append(m); i = j
        return lst, i
    d = {}
    while i < len(rows) and rows[i][0] == base and not rows[i][1].startswith("- "):
        line = rows[i][1]
        if ":" not in line:
            i += 1; continue
        k, val = line.split(":", 1); k, val = k.strip(), val.strip()
        if val != "":
            d[k] = _scalar(val); i += 1
        else:
            j = i + 1
            sub = []
            while j < len(rows) and rows[j][0] > base:
                sub.append(rows[j]); j += 1
            d[k] = _parse(sub, 0)[0] if sub else None
            i = j
    return d, i
