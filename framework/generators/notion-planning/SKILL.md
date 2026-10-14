---
name: notion-planning
description: Reporte le planning (dates / jalons) dans la base planning Notion, un seul sens (source -> Notion), ecriture GARDEE "demander-avant". Le report du meme planning sur la slide du deck est porte par la routine slide-planning. Aucune notification.
---

Tient a jour le **planning dans Notion** (dates, jalons) a partir de la source de verite de la mission.
**Sens unique** : source -> Notion, jamais l'inverse. Ecriture **gardee** : on montre, on attend le oui.
Voix du profil (`notion_planning.yml > tone`).

## Deroule

1. Lire la source de verite des dates (`notion_planning.yml > source` : roadmap / planning de la mission) et
   le planning actuel dans Notion (`planning_tracker`), en lecture seule.
2. Calculer le **diff** (dates/jalons qui changent). Si rien ne change, ne rien ecrire.
3. **Montrer le contenu exact** (avant/apres) et **attendre le oui** (`guard: demander-avant`).
4. Ecrire **uniquement** les champs valides, de maniere chirurgicale (`notion-update-page`, `update_content`
   ou `update_properties` cible ; jamais `replace_content`). Mentions en texte simple.
5. Relire (`notion-fetch`).

## Lien avec la slide

Le **meme** planning se reporte sur la slide du deck via la routine `slide-planning` (OneDrive, ecriture en
place, garde-fou anti-ecrasement). Les deux lisent la **meme source** : ne jamais corriger la source depuis
la slide ou depuis Notion, c'est l'inverse.

## Garde-fous

- `guard: demander-avant` : **rien sans validation**. Sens unique. Aucune notification (pas de mention,
  commentaire, partage, deplacement de page - hook `garde_suppression.py`).
- **Ne rien inventer** : une date inconnue reste "a confirmer". Les modifs manuelles de l'utilisateur sont
  prioritaires (on garde, on ajuste autour).
