---
name: gate
description: Score les PORTES (gates) d'une mission, déclarées en donnée, et RECOMMANDE un franchissement sans jamais le prononcer. Les portes vivent dans profiles/<mission>/gate.yml (le GTF standard = 7 portes, Gate 0 à Gate 6). Chaque porte porte ses critères (0 / 0,5 / 1), son seuil, l'acte humain de franchissement et des waivers datés. Lecture seule : il compte, il ne valide pas.
meta:
  produces: null
  consumes: [gate.yml]
  mcp_deps: []
  cost: light
  status: stable
---

# Générateur gate (portes de projet)

**La méthode est une donnée.** Les portes d'une mission vivent dans `profiles/<mission>/gate.yml`,
jamais dans le code. Ce script **compte** l'état de chaque porte et **recommande** ; il ne franchit
rien. Le franchissement est un **acte humain tracé**.

## Le standard GTF : 7 portes

Le gabarit `gtf.sample.yml` porte les 7 portes du GTF (Global Technical Framework) :

| Porte | Nom | Ce qu'elle verrouille |
|---|---|---|
| Gate 0 | Technical Commitment review | faisabilité technique + viabilité commerciale avant engagement |
| Gate 1 | Project kickoff | objectifs, gouvernance, planning validés |
| Gate 2 | Implementation kickoff | exigences, périmètre, archi, RACI, approche de livraison |
| Gate 3 | Release freeze | périmètre gelé (IA / SW / HW), prêt pour la validation |
| Gate 4 | Deployment go/no-go | préparation au déploiement, acceptation métier |
| Gate 5 | Celebrate | adoption, KPI mesurés, clôture de l'itération |
| Gate 6 | Decommissioning review | plan de fin de vie, retrait sûr |

Une mission qui ne suit pas le GTF déclare ses propres portes de la même façon ; le script ne connaît
que la structure, pas les noms.

## La donnée (`profiles/<mission>/gate.yml` > `gates:`)

Une **liste** de portes. Chaque porte :

```yaml
gates:
  - id: gate2
    name: "Implementation kickoff"
    summary: "…"                     # une phrase, optionnelle
    threshold: 90                    # seuil en %, défaut 90
    criteria:
      - { id: G2.1, label: "Exigences validées", score: 1 }
      - { id: G2.5, label: "Approche de livraison", score: 0.5 }
      - { id: G2.6, label: "Non encore regardé" }        # pas de score = NON ÉVALUÉ
    acte_humain:                     # présent seulement quand la porte est franchie
      approbateur: "Sponsor"
      date: "2026-01-10"
      motif: "revue d'engagement en comité"
    waivers:                         # lever un bloquant (critère à 0), sous conditions
      - bloquant: G2.3
        approbateur: "CP/RSIA"
        date: "2026-08-01"
        motif: "risque assumé, recette en parallèle"
        echeance: "2026-09-01"       # DATE de péremption : un waiver expiré REDEVIENT un bloquant
        surveillance: "revue hebdo"
        remediation: "Testeur"
        cible: "plan de recette validé"
```

- **Échelle d'un critère** : `1` (fait), `0.5` (partiel), `0` (non fait = **bloquant**). Un critère
  **sans `score`** est **non évalué** : exclu du calcul (≠ 0). Une porte sans aucun score est « non entamée ».
- **Seuil** : le score est la moyenne des critères notés, en %. `threshold` est le seuil (défaut 90 %).
- **Waiver à 8 champs** : les 8 champs sont **obligatoires**, sinon le waiver est **invalide** et ne lève
  rien. Un waiver dont l'`echeance` est passée est **expiré** : le bloquant rouvre (fail-closed).

## Doctrine (ce que le script refuse de faire)

1. **Aucun franchissement automatique.** Seuil atteint **≠** porte franchie. Il faut un `acte_humain`
   (approbateur, date, motif). Sans lui, le script affiche « seuil atteint, mais aucun acte humain tracé ».
2. **Un bloquant se lève par un waiver, pas en le masquant.** Et un waiver est **daté** : il expire.
3. **« Waivé » n'est pas « recommandé ».** Le verdict change de nom (« WAIVÉ - franchissement assumé »),
   pas de nature : la trace reste au dossier.

## Usage

```
python3 framework/pm.py run gate <mission>            # vue d'ensemble des 7 portes
python3 framework/pm.py run gate <mission> <gate-id>  # détail d'une porte (ex. gate3)
```

Vue d'ensemble : une ligne par porte (score %, franchie, drapeaux `⚠` seuil atteint sans acte humain,
`⛔` bloquant ouvert). Détail : critères notés, bloquants ouverts, état de chaque waiver.

## Démarrer une mission

Copier `framework/generators/gate/gtf.sample.yml` vers `profiles/<mission>/gate.yml`, puis remplir au
fil de l'eau les `score`, et, quand une porte se franchit, son `acte_humain`. Exemple complet et noté :
`profiles/demo/gate.yml`.

## Ce qu'il ne fait pas

- Il n'écrit **rien** : ni Office, ni Jira, ni Notion. Il lit `gate.yml` et affiche.
- Il ne **prononce** aucun franchissement : il recommande, l'humain tranche et le trace dans `gate.yml`.
