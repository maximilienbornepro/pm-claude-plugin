#!/usr/bin/env python3
"""Génère showcase.html : copie générique de l'architecture SINBAD (labels de marque
neutralisés, logos de marque remplacés par un SVG générique). Déterministe, lecture seule sur la source."""
import base64, os, re, sys

SRC = os.environ.get("SINBAD_ARCHI_SRC", os.path.expanduser(
    "~/Documents/Sinbad/stack-imagery/architecture_sinbad.html"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "showcase.html")

BRAND_LOGOS = ["airbus", "iceye", "ksat", "nato", "safran", "enix"]

SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
       '<rect x="2" y="2" width="60" height="60" rx="12" fill="#9aa0a6"/>'
       '<circle cx="32" cy="24" r="9" fill="#f1f3f4"/>'
       '<path d="M14 50c2-10 10-15 18-15s16 5 18 15z" fill="#f1f3f4"/></svg>')
GENERIC = "data:image/svg+xml;base64," + base64.b64encode(SVG.encode()).decode()

# Ordre = du plus spécifique au plus général. (motif, remplacement), insensible à la casse.
RULES = [
    (r"auj\.\s*Safran\.AI\s+Entra", "auj. Corp IdP"),
    (r"IDP\s+OTAN", "Org IdP"),
    (r"Change\s+Monitoring", "Alert App"),
    (r"Geo\s*Warning", "Alert App"),
    # NB : « Maritime App » contiendrait « maritim » et ferait échouer le grep de vérification
    (r"Maritim\w*\s+Awareness", "Sea App"),
    (r"Maritim\w*", "Sea"),
    (r"\bVpK\b", "Partner App"),
    (r"\bVake\b", "Partner App"),
    (r"\bADS\b", "Provider A"),
    (r"Airbus\s*\(EO\)", "Provider A (EO)"),
    (r"ICEYE\s*\(SAR\)", "Provider B (SAR)"),
    (r"Airbus", "Provider A (EO)"),
    (r"ICEYE", "Provider B (SAR)"),
    (r"\bSAI\b", "Company"),
    (r"KSAT", "Partner C"),
    (r"NATO|OTAN", "Org IdP"),
    (r"Safran\.AI|Safran|Preligens", "Company"),
    (r"Enix", "Managed Ops"),
    (r"\bCIP\b", "Platform core"),
    (r"eu-west-1", "region-1"),
    (r"\bEntra\b", "Corp IdP"),
]

s = open(SRC, encoding="utf-8").read()

# 1. logos de marque -> SVG générique (avant les remplacements texte)
n_logo = 0
for k in BRAND_LOGOS:
    s, n = re.subn(r'("%s"\s*:\s*")data:image/[^"]+(")' % k, lambda m: m.group(1) + GENERIC + m.group(2), s)
    n_logo += n
assert n_logo == len(BRAND_LOGOS), n_logo

# 2. texte : on ne touche pas aux payloads base64
parts = re.split(r'(data:image/[^;]+;base64,[A-Za-z0-9+/=]+)', s)
for i in range(0, len(parts), 2):
    for pat, rep in RULES:
        parts[i] = re.sub(pat, rep, parts[i], flags=re.I)
open(OUT, "w", encoding="utf-8").write("".join(parts))
print("écrit", OUT, os.path.getsize(OUT), "octets")
