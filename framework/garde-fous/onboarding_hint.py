#!/usr/bin/env python3
"""Hook SessionStart : si le projet courant a un dossier `profiles/`, rappelle discretement
qu'on peut verifier la config d'une mission avec /pm-framework:setup avant d'ecrire.
N'ecrit rien, ne bloque rien ; sa sortie stdout est ajoutee au contexte de session."""
import os, sys, json

try:
    json.load(sys.stdin)
except Exception:
    pass

prof = os.path.join(os.getcwd(), "profiles")
if os.path.isdir(prof):
    try:
        missions = sorted(d for d in os.listdir(prof) if os.path.isdir(os.path.join(prof, d)))
    except Exception:
        missions = []
    liste = ", ".join(missions) if missions else "aucune"
    print(f"[pm-framework] Profils detectes dans ce projet ({liste}). "
          f"Avant toute ecriture, verifier la config d'une mission avec /pm-framework:setup <mission> "
          f"(onboarding guide si des champs manquent). Tout est lecture seule par defaut.")
sys.exit(0)
