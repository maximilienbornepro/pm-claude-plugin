---
date: 2026-11-26
status: en cours (phases 1 à 4 faites le 26/11/2026)
slug: audit-harmonisation
---

# 001 · Audit du plugin et harmonisation des livrables

## Principe directeur

**Un livrable = une source JSON + trois rendus.**

```
profiles/<mission>/data/<livrable>.json      ← source unique (validée par un schéma)
        │
        ├── HTML  : page du « dossier projet », découpée en blocs 16:9 (1 bloc = 1 slide)
        ├── PPTX  : slides natives (tables/graphiques éditables) dans le gabarit de l'entreprise
        └── XLSX  : seulement pour les registres (risques, RACI, traçabilité, Gantt)
```

Règles du format :
- **Tout est potentiellement une slide** : chaque bloc HTML a un cadre 16:9 fixe (pas de scroll, pas
  d'état interactif nécessaire pour comprendre), un titre = message clé, ≤ 8-10 lignes, pagination auto.
- Le PPTX réutilise le moteur 16:9 existant de `planning.py` (`load_template`, tables paginées),
  sorti dans `framework/lib/slides.py` et partagé par tous les générateurs.
- Chaque bloc HTML a un bouton « Copier en image » (PNG 1920×1080) pour un collage rapide.
- Graphiques en **SVG** (plus de Chart.js/canvas par CDN) : rendu hors ligne et exportable.
- **Une seule charte** (tokens communs HTML ↔ PPTX), statuts et niveaux avec les mêmes couleurs partout.

## Le dossier projet HTML

Arborescence calquée sur `templates/project-management-tree.yml` (déjà la référence Drive ↔ Notion) :

```
<sortie>/<mission>/
├── index.html                 ← cockpit : jalons, avancement, top risques, gates, liens
├── 01-cadrage/      scope, RACI
├── 02-planning/     gantt, échéances, situation, sprints, projection
├── 03-risques/      registre, matrice P×I, évolutions
├── 04-gates/        checklist, deck GATE
├── 05-comptes-rendus/  CR partenaire, agendas, weekly
├── 06-architecture/ schémas (vues SVG)
├── assets/          charte.css, slides.js (copie PNG), logos
└── exports/         *.pptx, *.xlsx générés
```

Généré par une commande unique : `pm run dossier <mission>` (lecture seule, écrit en local).

## Constat de l'audit (26/11)

### Code
- `console` et `traceability` fonctionnent mais ne sont ni déclarés dans `pm.py` ni documentés ;
  le vérificateur ne les voit pas (il ne parcourt que `*/SKILL.md`).
- À supprimer : `archi/genericize_showcase.py`, ~10 imports inutilisés, 3 fonctions mortes
  (`links.file_link`, `profile.tone_for`, `profile.tone_for_agent`).
- SINBAD dans le moteur : `--mission` vaut `sinbad` par défaut dans 17 scripts (trace d'erreur sans
  argument), « Namespace Sinbad » en dur dans `archi/enrich.py`, noms SINBAD dans `setup` et `reset`,
  skills `voice-deliverable` / `voice-maximilien` liées à SINBAD dans le moteur.
- Doublons à regrouper dans `lib/` : client Notion (×3), lecture `.env` (×4), writer xlsx
  (`traceability` vs `lib/xlsx_write`), `harness/onedrive_xlsx.py` et `routing_check.py` (prod, pas test).
- Bugs : `omi_sync.py --help` plante sans `omi.env` ; drapeau « lecture seule » incohérent dans `GEN` ;
  `lib/profile.py` masque le module standard `profile`.
- Doc périmée : `framework/SKILLS.md` (anciens noms, 18 générateurs absents), README, `AGENTS.md`,
  `REDACTION.md` (alias), `agents/adservio-writer.md` (chemin inexistant).

### Routines
- 8/10 ont un `name:` français et un dossier anglais ; docs mélangées.
- Références cassées : `review-topics` → `revue-risques`, `draft-followups` → mauvais chemin de
  `creer_eml.py`, `collect-activity` → `generators/suivi/`.
- Aucun `writes` / `notifies` / `chains` en frontmatter, aucune étape preflight, pas d'accents.
- Doublons : `align-sprint-goals` ⊂ `publish-projection` ; Weekly produit deux fois.
- Aucun profil n'a de `routines.yml`.

### Livrables
- Seul `planning.py` produit de vraies slides 16:9.
- Risques : 5 représentations sans modèle commun, échelles divergentes (3 niveaux EN, 4 FR, Fort/Forte),
  classeur créé par `office` illisible par `risks.py` (en-tête ligne 4 vs 6) et sans styles, aucun HTML.
- Avancement/sprints : page HTML verticale (1040×2200), sombre, Chart.js en CDN, interactive : non
  injectable. Projection : calcul sans rendu. La slide GATE « avancement » a été faite à la main.
- Deck GATE : contenu découpé en slides mais aucun PPTX généré.
- Quatre palettes différentes (Adservio, guide, page avancement, PPTX planning).

## Phases

| # | Phase | Livrable de fin de phase | Validation |
|---|---|---|---|
| 1 | Audit | ce document | ✅ fait |
| 2 ✅ | Nettoyage code (lots : suppressions, `--mission`, `lib/`, doc) — reste : client Notion et lecture `.env` à regrouper dans `lib/` | commits par lot, `pm list` + `pm demo` + verifier verts | liste cochée par toi |
| 3 ✅ | Routines : gabarit unique, noms = dossiers, preflight, fusions — reste : migrer les clés et tâches SINBAD vers les noms anglais | 10 SKILL migrés, README/SKILLS/GUIDE alignés, `profiles/demo/routines.yml` | revue du gabarit |
| 4a ✅ | Socle livrables : charte (`slide-style`), `lib/slides.py`, générateur `dossier` (PPTX éditable + HTML + synchro retour) | maquette HTML 16:9 + PPTX du **pilote** | **on valide le format ensemble** |
| 4b ✅ | Pilote **risques** + **avancement/sprints** (sur données de démo) | registre HTML/PPTX/XLSX, slides avancement, sprint, projection | relecture sur la démo |
| 5 | Généralisation (planning, RACI, gates, deck GATE, CR, agenda, weekly, archi) | dossier projet complet de `demo` | revue finale |
| 6 | Doc + guide web | GUIDE.md, docs/index.html, captures | — |

## Décisions à prendre (avant la phase 4a)

1. **Charte** : Adservio (noir/royal 0033FF) ou gabarit PowerPoint de l'entreprise de la mission
   (profil) avec Adservio par défaut ?
2. **Échelle des risques** : 4 niveaux FR (faible / moyen / élevé / critique) partout, XLSX traduit ?
3. **Modèle risque** : id, libellé, catégorie, probabilité, impact, niveau (calculé), mitigation,
   responsable, échéance, statut, sujet lié, tendance (↑ ↓ =).
4. Renommages verbe-objet des routines (re-enregistrement des tâches planifiées) : oui / non.
