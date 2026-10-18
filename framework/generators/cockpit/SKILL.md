---
name: cockpit
description: Porte d'entrée OPTIONNELLE d'une mission déjà amorcée : « où en est-on, que fait-on ? ». Calcule l'état depuis la donnée (portes/gates A6, chaîne de traçabilité A5) et en déduit une suite d'actions priorisées, chacune avec sa commande pm run et, en multi-compte, le compte vers lequel elle route (A1). Lecture seule : il montre et route, il n'exécute rien. Ne remplace pas init/setup et ne désactive aucun autre générateur.
meta:
  produces: null
  consumes: [gate.yml, method.yaml, tracabilite.yml]
  mcp_deps: []
  cost: light
  status: stable
---

# Générateur cockpit (orchestrateur, optionnel)

« Porte unique, menu calculé » - mais **une option, pas une obligation**. Le cockpit **calcule**
l'état d'une mission depuis la **donnée** et en **déduit** la suite ; il ne recalcule rien de mémoire
et ne décide rien. On peut tout aussi bien appeler chaque générateur directement : le cockpit dit
simplement lequel, et dans quel ordre.

## Ce qu'il lit (l'état, déjà déclaré)

- **Portes** (`gate.yml`, A6) : classées franchies / ⛔ bloquées / ⚠ seuil atteint sans acte / en cours / à venir.
- **Traçabilité** (`method.yaml` > `tracabilite` + `tracabilite.yml`, A5) : phase courante, items en rupture.
- **Routage** (A1) : pour chaque action proposée, le compte vers lequel sa commande route, en multi-compte.

## Ce qu'il produit

Une **suite d'actions priorisées** (bloquant de porte → acte humain → critères → ruptures → porte suivante),
chacune avec la commande `pm run …` exacte. Rien d'inventé : chaque action vient d'un état mesuré.

## Usage

```
python3 framework/pm.py run cockpit <mission>
```

Sur une **mission encore vierge** (ni `gate.yml`, ni chaîne), il n'invente pas d'état : il renvoie vers
le **parcours classique d'amorçage** (`pm run init`, puis `setup`, puis les scaffold).

## Ce qu'il n'est pas

- **Pas la seule porte.** Les autres générateurs restent appelables directement ; le cockpit ne les met
  **pas** en `disable-model-invocation`. `init` reste le point de départ classique d'un projet.
- **Pas un exécuteur.** Il n'ouvre aucune porte, ne modifie aucun ticket, n'écrit rien : il montre et route.
