---
name: gate-deck
description: Rend le contenu du deck GATE d'une mission (slides en markdown/JSON, ton du profil) depuis profiles/<mission>/gate_deck.yml. Le slide « jalons » se remplit depuis key_dates. Ne produit pas le .pptx : l'assemblage sur le template reste une étape gardée.
meta:
  produces: deck-gate
  consumes: []
  mcp_deps: [m365]
  cost: heavy-local
  status: stable
---

# Générateur gate-deck (contenu du deck GATE)

Produit le **contenu** du deck GATE d'une mission, config-driven, dans le ton du profil
(ex. `voice-adservio`). **Il ne génère pas le binaire pptx** (pas de `python-pptx` en session) :
il rend des **slides prêtes à relire** (markdown) et une sortie **JSON** pour l'assemblage.

## Données (`profiles/<mission>/gate_deck.yml`)
- `template` : le gabarit pptx de la mission. `output` : dossier des decks. `tone` : le ton.
- `slides` : le plan, **en flow inline** (pas de virgule dans les chaînes : `/` ou `;`). Types :
  - `title` : `{ type: title, title, subtitle }`
  - `bullets` : `{ type: bullets, title, bullets: [...] }`
  - `jalons` : `{ type: jalons, title }` → rempli **automatiquement** depuis `key_dates` (T0 / gel / MEP)
  - `schema` : `{ type: schema, title, image }` → référence l'image à insérer (ex. le schéma d'archi)

## Usage
```
python3 framework/pm.py run gate-deck <mission>          # le deck en markdown (relecture)
python3 framework/pm.py run gate-deck <mission> --json   # le deck en JSON (pour l'assemblage)
```

## Assemblage pptx (étape gardée, hors de ce générateur)
Le contenu validé s'applique sur le **template pptx** via la **cohérence des docs** (skill
`sinbad-coherence-docs`) : préparation sur une copie, **une seule écriture** OneDrive (fichier fermé),
sauvegarde horodatée, contrôle de taille, après validation. Les slides `schema` reçoivent les PNG
dérivés du schéma d'archi (stack-imagery).

## Garde-fous
Lecture seule ici ; aucune écriture pptx par ce générateur. Ne rien inventer (chiffres/dates depuis
les sources : `key_dates`, projection, risques). Jalons toujours tirés de `key_dates`, jamais saisis à la main.
