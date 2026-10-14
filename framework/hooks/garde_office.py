#!/usr/bin/env python3
"""Hook PreToolUse (Bash) : garde-fou des ecritures Office synchronisees - generique.

Refuse une commande qui ecrit/supprime un classeur ou document Office d'un Drive
synchronise (xlsx/docx/pptx...) autrement que par le helper sur `onedrive_xlsx.py`.
But : empecher la betise classique (reecriture brute, openpyxl destructeur, rm/mv)
qui casse le fichier ou la synchro distante.

Autorise tout le reste (y compris la LECTURE de ces fichiers). Ne bloque jamais une
commande qui passe par le helper. Voir framework/harness/HARNESS.md.

Portabilite : par defaut le garde-fou vise les chemins contenant 'OneDrive'. Pour
une autre racine synchronisee (SharePoint monte, GDrive...), definir la variable
d'environnement PMF_SYNC_MARKER (ex. "CloudStorage") ; le marqueur est injecte dans
le motif de detection.
"""
import json, sys, re, os

MARKER = os.environ.get("PMF_SYNC_MARKER", "OneDrive")

# Chemins synchronises AVEC espaces (ex. « 06 - Risques ») : on exclut seulement
# les guillemets et separateurs shell, pas les espaces.
OFFICE = MARKER + r'[^"\'|>&;\n]*\.(?:xlsx|xlsm|xltx|docx|dotx|pptx|potx)'
PREFIX = r'[^"\'|>&;\n]*'  # prefixe de chemin (/Users/.../) jusqu'au marqueur

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Bash":
    sys.exit(0)
cmd = (data.get("tool_input") or {}).get("command", "")

# Les ecritures legitimes passent par le helper : on laisse faire.
if "onedrive_xlsx.py" in cmd:
    sys.exit(0)

reasons = []
if re.search(r'(?:>>?|\btee\b)\s+["\']?' + PREFIX + OFFICE, cmd):
    reasons.append("redirection (>) vers un fichier Office synchronise")
if re.search(r'\b(?:rm|mv)\b\s+["\']?' + PREFIX + OFFICE, cmd):
    reasons.append("rm/mv sur un fichier Office synchronise")
if "openpyxl" in cmd and re.search(OFFICE, cmd):
    reasons.append("openpyxl sur un classeur synchronise (detruit images et dessins)")
if ".save(" in cmd and re.search(OFFICE, cmd):
    reasons.append(".save() sur un classeur synchronise")

if reasons:
    msg = ("Ecriture Office synchronisee bloquee : " + " ; ".join(reasons) + ". "
           "Passe par le helper framework/harness/onedrive_xlsx.py (ecriture chirurgicale "
           "+ sauvegarde + une seule ecriture), et seulement APRES le controle de fraicheur "
           "distant (lastModifiedDateTime). Voir framework/harness/HARNESS.md.")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": msg,
    }}))
sys.exit(0)
