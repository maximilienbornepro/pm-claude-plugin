---
name: coherence
description: Contrôle de cohérence des documents (lecture seule) : vérifie qu'une sortie dérivée est à jour vis-à-vis de ses sources (cas GATE deck ← Excel ← PNG dérivés, ou tout artefact généré depuis d'autres). La carte des dépendances vit dans profiles/<mission>/coherence.yml. N'écrit rien.
---

# Générateur coherence (cohérence des documents)

Vérifie qu'une **sortie** (derived) est bien **à jour** vis-à-vis de ses **sources** : cas typique
GATE deck ← Excel sources ← PNG dérivés, ou tout artefact produit à partir d'autres. N'écrit rien :
il signale ce qui est **périmé** ou **manquant**.

## Données (`profiles/<mission>/coherence.yml` > `chains`)
Deux règles par chaîne :
- `newer` : la sortie doit exister et être **plus récente** que toutes ses sources ;
- `identical` : la sortie doit avoir le **même md5** qu'une source unique (copie exacte).

## Usage
```
python3 framework/pm.py run coherence <mission> [--root /chemin/racine]
```
`--root` préfixe les chemins (sinon `coherence.yml > root`, sinon chemins tels quels).

## Quand l'utiliser
Après **toute** modification d'un document de pilotage relié (GATE ↔ Excel sources ↔ PowerPoint
d'une slide ↔ PNG dérivés) : l'audit dit lesquels sont désormais en retard sur leur source.

## Garde-fous
Lecture seule. Il ne régénère ni ne réécrit aucune sortie : la mise à jour d'un dérivé périmé
reste l'affaire du générateur concerné (gate-deck, risks, projection…) et de son écriture gardée.
