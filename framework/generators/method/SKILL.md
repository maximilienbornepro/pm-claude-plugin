---
name: method
description: Montre la MÉTHODE d'une mission, déclarée en donnée dans profiles/<mission>/method.yaml - barèmes de cotation, seuils-pivots, trames de livrables, chaîne de traçabilité. Principe du framework : ce qui se calcule ne se raconte pas ; les outils lisent la méthode ici et calculent, le modèle ne produit que la preuve. Lecture seule : il affiche et signale ce qui reste en prose.
meta:
  produces: null
  consumes: [method.yaml]
  mcp_deps: []
  cost: light
  status: stable
---

# Générateur method (la méthode en donnée)

**« Ce qui se calcule ne se raconte pas. »** Tout ce qui relève de la méthode d'une mission et qui
se **calcule** - un barème de cotation, un seuil à comparer, l'ordre des sections d'un livrable, la
chaîne besoin → ticket → POC → test - vit en **donnée** dans `profiles/<mission>/method.yaml`, jamais
dans la prose d'un skill ni en dur dans un script. Les outils **lisent** cette donnée et calculent ;
le modèle ne produit que la **preuve**. Résultats reproductibles et **opposables** (COPIL, OTAN) :
ils ne sont pas « calculés par un modèle ».

## Les sections de `method.yaml`

| Section | Contenu | Lu par |
|---|---|---|
| `baremes` | échelles de cotation (ex. risque : niveaux + libellés) | `risks`, revue des risques |
| `seuils` | valeurs-pivots comparées (ex. `gate_defaut: 90`, capacité de sprint) | `gate`, projection |
| `trames` | ordre des sections d'un livrable (deck, CR…) | générateurs de livrables |
| `tracabilite` | la chaîne besoin/TR → ticket → POC → test (A5) | `trace-audit` |

Une section **absente** rend un défaut : rien ne casse. La migration est **incrémentale**, livrable
par livrable : on sort de la prose ce qui se calcule, au fil de l'eau.

## Usage

```
python3 framework/pm.py run method <mission>            # toutes les sections (vides signalées)
python3 framework/pm.py run method <mission> <section>  # baremes | seuils | trames | tracabilite
```

## Lire la méthode depuis un générateur

Ne pas reparser `method.yaml` à la main : passer par `framework/lib/method.py`.

```python
import method
sd = method.seuil(mission, "gate_defaut", 90)   # un seuil, avec défaut
ba = method.bareme(mission, "risque")            # un barème (dict)
tr = method.trame(mission, "deck_gate")          # une trame (liste de sections), [] si absente
```

Exemple en place : `gate` lit `seuils.gate_defaut` comme seuil par défaut d'une porte qui ne fixe
pas le sien (`profiles/demo/method.yaml`).

## Ce qu'il ne fait pas

- Il n'écrit **rien** et ne rend **aucun verdict** : il montre la méthode et dit ce qui reste en prose.
- Il ne remplace pas les configs spécifiques d'un générateur (`risks.yml`, `gate.yml`…) : `method.yaml`
  porte le **transverse** et les valeurs partagées entre plusieurs outils.
