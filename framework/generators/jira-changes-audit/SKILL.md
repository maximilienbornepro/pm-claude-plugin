---
name: ticket-changes
description: Dit qui a modifié quels tickets du tracker, quand et quoi, sur une fenêtre de temps, et repère les écrasements de description (une version enregistrée par-dessus une autre). Config-driven par le profil. Lecture seule.
---

# Générateur ticket-changes (modifications et écrasements de tickets)

Générique et config-driven : projet, board et identifiants viennent du profil de mission et de
l'environnement (`framework/lib/jira.py`). Repère surtout les **écrasements de description** -
une version enregistrée par-dessus une autre, typiquement un onglet resté ouvert en édition -
via les **sections perdues**. N'écrit jamais.

## Usage
```
python3 framework/pm.py run ticket-changes <mission>                  # depuis ce matin 00h00
python3 framework/pm.py run ticket-changes <mission> --since 10:30     # depuis aujourd'hui 10h30
python3 framework/pm.py run ticket-changes <mission> --since 2026-09-22T17:00
python3 framework/pm.py run ticket-changes <mission> --last-point      # depuis 10h30 la veille ouvrée
python3 framework/pm.py run ticket-changes <mission> --me              # inclut l'auteur "assistant"
python3 framework/pm.py run ticket-changes <mission> --self "Nom"      # auteur assistant à exclure
```

L'auteur **assistant** exclu par défaut (ses passes d'outillage noient le signal) est pris dans
l'ordre : `--self`, puis le profil `jira.assistant_author`, puis l'env `PMF_JIRA_SELF`.

## Quand l'utiliser
Point du matin, après une campagne de modifications en masse, quand un ticket « n'est plus à
jour », ou quand on demande ce qui a bougé dans le backlog.

## Garde-fous
Lecture seule : ne modifie jamais un ticket. La réparation d'un écrasement (relire, réappliquer
sur la version courante) reste une étape gardée, hors de ce générateur.
