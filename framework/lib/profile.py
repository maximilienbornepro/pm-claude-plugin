#!/usr/bin/env python3
"""Loader de profil/pipeline du pm-framework - SANS dependance.

Lit profiles/<mission>/profile.yml et pipeline.yml et expose les valeurs resolues.
Repli automatique sur PyYAML s'il est installe, sinon mini-parseur YAML integre
(sous-ensemble suffisant pour nos fichiers de config). N'ecrit rien, n'appelle rien.
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # .../pm-framework

# ---------------------------------------------------------------- portabilite
# Expansion des chemins dans TOUTE valeur chaine des YAML de config :
#   ${VAR}            -> os.environ['VAR']        (vide si absent)
#   ${VAR:-defaut}    -> os.environ['VAR'] sinon 'defaut'   (defaut = chemin actuel)
#   $VAR              -> os.environ['VAR']
#   ~ en tete         -> repertoire personnel
# Permet a un clone frais de pointer les donnees SINBAD via une variable d'env
# (SINBAD_ROOT, SINBAD_PM_ROOT, CLAUDE_PROJECTS...) sans editer les fichiers de config.
_ENVPAT = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}|\$([A-Za-z_][A-Za-z0-9_]*)')


def _expand(s):
    if not isinstance(s, str) or ('$' not in s and not s.startswith('~')):
        return s

    def sub(m):
        if m.group(1) is not None:                       # ${VAR} ou ${VAR:-defaut}
            return os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else '')
        return os.environ.get(m.group(3), '')            # $VAR

    out = _ENVPAT.sub(sub, s)
    if out.startswith('~'):
        out = os.path.expanduser(out)
    return out


def _expand_tree(obj):
    if isinstance(obj, dict):
        return {k: _expand_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_tree(v) for v in obj]
    return _expand(obj)

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except Exception:
    _HAVE_YAML = False


# ---------------------------------------------------------------- mini-YAML
def _strip_comment(line):
    out, q = [], None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in ('"', "'"):
            q = ch
            out.append(ch)
        elif ch == '#':
            break
        else:
            out.append(ch)
    return ''.join(out).rstrip()


def _scalar(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    low = s.lower()
    if low in ('', 'null', '~'):
        return None
    if low == 'true':
        return True
    if low == 'false':
        return False
    try:
        return int(s)
    except ValueError:
        pass
    return s


def _skip_ws(s, i):
    while i < len(s) and s[i] in ' \t':
        i += 1
    return i


def _flow_value(s, i):
    i = _skip_ws(s, i)
    if i >= len(s):
        return None, i
    if s[i] == '{':
        return _flow_map(s, i)
    if s[i] == '[':
        return _flow_list(s, i)
    buf, q, j = '', None, i
    while j < len(s):
        ch = s[j]
        if q:
            buf += ch
            if ch == q:
                q = None
        elif ch in ('"', "'"):
            q = ch
            buf += ch
        elif ch in ',]}':
            break
        else:
            buf += ch
        j += 1
    return _scalar(buf), j


def _flow_key(s, i):
    buf, q = '', None
    while i < len(s):
        ch = s[i]
        if q:
            buf += ch
            if ch == q:
                q = None
        elif ch in ('"', "'"):
            q = ch
            buf += ch
        elif ch == ':':
            break
        else:
            buf += ch
        i += 1
    k = buf.strip()
    if len(k) >= 2 and k[0] == k[-1] and k[0] in ('"', "'"):
        k = k[1:-1]
    return k, i


def _flow_map(s, i):
    i += 1
    d = {}
    while i < len(s):
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == '}':
            return d, i + 1
        k, i = _flow_key(s, i)
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ':':
            i += 1
        v, i = _flow_value(s, i)
        d[k] = v
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ',':
            i += 1
        elif i < len(s) and s[i] == '}':
            return d, i + 1
    return d, i


def _flow_list(s, i):
    i += 1
    arr = []
    while i < len(s):
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ']':
            return arr, i + 1
        v, i = _flow_value(s, i)
        arr.append(v)
        i = _skip_ws(s, i)
        if i < len(s) and s[i] == ',':
            i += 1
        elif i < len(s) and s[i] == ']':
            return arr, i + 1
    return arr, i


def _parse_flow(val):
    v, _ = _flow_value(val, 0)
    return v


def _lines(text):
    out = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if line.strip() == '':
            continue
        indent = len(line) - len(line.lstrip(' '))
        out.append((indent, line.strip()))
    return out


def _parse_block(lines, i, indent):
    if lines[i][1].startswith('- '):
        arr = []
        while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith('- '):
            item = lines[i][1][2:].strip()
            arr.append(_parse_flow(item) if item[:1] in '[{' else _scalar(item))
            i += 1
        return arr, i
    d = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith('- '):
        key, _, val = lines[i][1].partition(':')
        key, val = key.strip(), val.strip()
        if val == '':
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                sub, i = _parse_block(lines, i + 1, lines[i + 1][0])
                d[key] = sub
            else:
                d[key] = None
                i += 1
        else:
            d[key] = _parse_flow(val) if val[0] in '[{' else _scalar(val)
            i += 1
    return d, i


def _mini_parse(text):
    lines = _lines(text)
    if not lines:
        return {}
    obj, _ = _parse_block(lines, 0, lines[0][0])
    return obj


# ---------------------------------------------------------------- API
def _load_yaml(path):
    text = Path(path).read_text(encoding='utf-8')
    obj = yaml.safe_load(text) if _HAVE_YAML else _mini_parse(text)
    return _expand_tree(obj)


def profiles_root():
    """Ou vivent les profils. En plugin, ils sont dans le PROJET de l'utilisateur, pas dans le
    framework installe. Ordre : $PMF_PROFILES -> <cwd>/profiles -> <framework>/profiles."""
    env = os.environ.get('PMF_PROFILES')
    if env and Path(os.path.expanduser(env)).is_dir():
        return Path(os.path.expanduser(env))
    cwd = Path.cwd() / 'profiles'
    if cwd.is_dir():
        return cwd
    return ROOT / 'profiles'


def mission_dir(mission):
    return profiles_root() / mission


def mission_file(mission, name):
    """Chemin d'un fichier de config d'une mission (ex. 'raci.yml'), resolu via profiles_root()."""
    return mission_dir(mission) / name


def load(mission):
    base = mission_dir(mission)
    return {
        'profile': _load_yaml(base / 'profile.yml'),
        'pipeline': _load_yaml(base / 'pipeline.yml'),
    }


def board(mission):
    """Le board Jira, lu DEPUIS LE PROFIL (plus aucune constante en dur)."""
    return load(mission)['profile']['jira']['board']


def tone_for(mission, deliverable):
    d = load(mission)['pipeline']['deliverables'].get(deliverable, {})
    return d.get('tone')


def tone_for_agent(mission, agent):
    return load(mission)['pipeline']['agents'].get(agent)


# ---------------------------------------------------------------- demo
if __name__ == '__main__':
    import sys
    m = sys.argv[1] if len(sys.argv) > 1 else 'sinbad'
    data = load(m)
    p, pipe = data['profile'], data['pipeline']
    print(f"Profil        : {p['name']}  (parseur: {'PyYAML' if _HAVE_YAML else 'integre, 0 dep'})")
    print(f"Jira          : {p['jira']['instance']}  projet={p['jira']['project_key']}  board={p['jira']['board']}")
    print(f"Dates cles    : {p['key_dates']}")
    print()
    print("Ton par livrable (depuis pipeline.yml) :")
    for name, cfg in pipe['deliverables'].items():
        print(f"  - {name:20s} -> ton={cfg.get('tone')!s:22s} schema={cfg.get('schema_style', '-')}")
    print()
    print("Ton par agent :")
    for ag, tone in pipe['agents'].items():
        print(f"  - {ag:24s} -> {tone}")
    print()
    print(f">>> board() renvoie {board(m)} : lu du profil, PLUS de 2371 en dur.")
