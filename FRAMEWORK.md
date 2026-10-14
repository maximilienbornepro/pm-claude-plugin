# PM Framework - cadrage

Framework de gestion de projet **portable**, extrait de SINBAD. Objectif : changer de mission
(autre entreprise, autre Jira, autre Notion, autre Drive) et retrouver **le même outillage**, en ne
changeant qu'**un profil**.

> Statut : squelette (phase 0). Document de référence, à valider puis à faire évoluer.

## Principe directeur : deux couches

- **Le moteur (générique, versionné)** : skills, agents, hooks, générateurs, harness, templates.
  Ne connaît **aucune** valeur de mission.
- **Le profil de mission (la seule chose qui change)** : `profiles/<mission>/` porte tout le
  propre-à-la-mission - Jira (cloud id, board, clé projet), espace Notion, racine Drive + synchro,
  palette + logos, équipe/RACI, dates clés, langue.

SINBAD devient **le premier profil**, pas le code.

## Règle d'or : on ne refactore pas SINBAD en place

Le SINBAD actuel (`~/Documents/Sinbad`) **continue de tourner tel quel**. Le framework se construit
**ici, à côté**, par extraction de copies généralisées. La bascule (SINBAD = profil du framework) ne
se fera qu'une fois le mécanisme prouvé. Rien dans SINBAD n'est modifié tant que ce n'est pas validé.

## Règle d'or : ne jamais écraser l'existant (idempotence)

Tout outil qui écrit dans un espace déjà en place (arborescence Drive, pages Notion, tickets Jira,
fichiers Office) est **créer-si-absent** et **réconcilier**, jamais **recréer** ni **remplacer** :

- il compare l'existant, liste ce qui manque, **propose**, et ne touche à rien qui existe déjà ;
- `--dry-run` d'abord, toujours ;
- aucune notification ne part (partage, invitation, mention, mail) sans validation explicite.

C'est le prolongement direct des garde-fous SINBAD (`garde_office.py`, `nettoyer_front.py`).

## Règle d'or : toute page gh-pages a un artefact Claude miroir

Tout livrable publié en **GitHub Pages** est **systématiquement** publié aussi en **artefact Claude**, et
les **deux doivent rester à jour en permanence** (même contenu). Raison : l'artefact reste accessible même
sans gh-pages, et sert de miroir partageable.

- Les cibles d'un livrable sont déclarées dans `pipeline.yml` (`targets: [gh-pages, artifact]`). L'archi
  publie trois cibles (`[artifact, artifact-light, gh-pages]`, même md5).
- Un script bash (gh-pages via git) **ne peut pas** publier un artefact : c'est l'**étape Claude / la
  routine** qui republie le **même HTML** sur l'URL d'artefact (fixe, créée une fois). Les URLs vivent dans
  la config de mission (`routines.yml > ...artifacts`, ou le `model.json` de l'archi).
- Après chaque push gh-pages, republier l'artefact dans la foulée. Jamais l'un sans l'autre.
- Artefacts **privés** : aucune notification. Le partage éventuel est une action de l'utilisateur.

## Nomenclature (convention de nommage)

Une seule casse pour tout identifiant : **`kebab-case`**, en **anglais**. Règles :

1. **Le dossier d'un générateur porte le nom exact de sa commande** (`pm run <nom>`). Fin du
   double vocabulaire clé ≠ dossier. Seule exception : `scaffold/` héberge `drive-scaffold` et
   `notion-scaffold` (un même paquet, deux commandes).
2. **On nomme par le livrable** (nom), pas par l'action. Un générateur **en lecture seule** prend
   le suffixe **`-audit`** ; celui qui produit garde le nom du livrable.
3. **Préfixe par domaine** quand l'outil vise un système : **`jira-*`, `notion-*`, `drive-*`,
   `deck-*`, `docs-*`**. `pm list` se lit alors par famille.
4. **Agents : `<objet>-<rôle>`**, rôle dans un vocabulaire fermé : `-audit` (lecture/contrôle),
   `-writer` (prose). Les agents d'audit portent le même nom que leur générateur.
5. **Skills de ton : préfixe `voice-`** (`voice-deliverable`, `voice-casual`, `voice-maximilien`,
   `voice-adservio`). Aucun préfixe de mission dans un identifiant du framework.
6. **Routines : `<verbe>-<objet>`** (`publish-projection`, `review-topics`, `collect-activity`…).
7. **Fichier de config d'une mission = nom du générateur** (`deck-gate.yml`, `jira-images.yml`…).

Les anciens noms de générateurs restent acceptés en **alias** dans `pm.py` (`GEN` + `ALIAS`) le
temps que tout soit migré, puis seront retirés.

## Arborescence réelle

```
pm-framework/
├── FRAMEWORK.md              ce document (cadrage + nomenclature)
├── README.md                 point d'entrée + table des générateurs
├── ROADMAP.md                feuille de route et état (fait / en cours / à faire)
├── config/
│   ├── profile.example.yml   gabarit d'un profil de mission
│   └── pipeline.example.yml  gabarit : livrable -> générateur/ton/schéma ; ton par agent
├── profiles/
│   ├── README.md             SINBAD = exemple de référence ; espace de pilotage à deux axes
│   ├── sinbad/               l'exemple canonique, complet (SINBAD d'origine intact, à côté)
│   │   ├── profile.yml       identité (Jira, Notion/Drive, dates, équipe, pm_front/file_store)
│   │   ├── pipeline.yml      livrables -> générateur/ton ; ton par agent
│   │   ├── <generateur>.yml  une config par générateur (deck-gate.yml, raci.yml, risks.yml…)
│   │   ├── palette.json · logos/ · architecture/
│   │   └── routines.yml      instances de routines de la mission
│   └── demo/                 faux projet neutre (pour `pm demo`)
├── framework/
│   ├── pm.py                 CLI unique (list / run / missions / demo)
│   ├── lib/                  loader de profil (0 dépendance), links, set_tone
│   ├── generators/<nom>/     un dossier par commande (== nom) + son SKILL.md
│   ├── agents/               agents portables (<objet>-audit, <x>-writer)
│   ├── skills/voice-*/       skills de ton
│   ├── routines/<verbe-objet>/  définitions de routines (SKILL.md) + README
│   ├── hooks/                garde_office, anti-écrasement Jira, journal d'usage
│   ├── assets/logos/         bibliothèque de logos techno partagée
│   ├── harness/              HARNESS.md, onedrive_xlsx.py
│   └── AGENTS.md · SKILLS.md · REDACTION.md · NOTIFICATIONS.md   catalogues et cartes
├── templates/
│   └── project-management-tree.yml   arbo standard + miroir Notion↔Drive
└── docs/
    └── nouvelle-mission.md   amorcer une mission en 10 min
```

## Les générateurs (un livrable = un générateur)

Table complète dans [README.md](README.md). Les principaux livrables :

| Générateur | Entrée | Sortie | Ton | Schéma |
|---|---|---|---|---|
| `drive-scaffold` / `notion-scaffold` | profil + template arbo | dossiers Drive / pages Notion (créer-si-absent) | - | - |
| `jira-images` | tickets + captures | images des tickets via API (jamais le connecteur) | - | - |
| `projection` | Jira (board) | rapport de projection (gh-pages + artefact) | `voice-deliverable` | adservio |
| `jira-sprints-audit` | Jira (board) | audit des sprints (lecture seule) | - | - |
| `archi` | source canonique (draw.io, TR, décision) | schéma d'archi interactif (3 cibles) | - | adservio |
| `deck-gate` | données de pilotage | contenu du deck GATE (assemblage pptx gardé) | `voice-adservio` | adservio |
| `raci` · `risks` · `poc` · `activity` · `partner-report` | config de mission | matrice / registre / POC / suivi / mail | selon pipeline | - |

Chaque générateur lit le **profil** (où est le Jira, le Drive…) et le **pipeline** (quel ton,
quel schéma). Un `SKILL.md` par générateur en décrit l'usage et les garde-fous.

## Le fichier de config central (`pipeline.yml`)

Deux tables, éditables à la main :

- **`deliverables`** : pour chaque type de livrable, quel générateur, quel ton, quel style de schéma,
  quelle cible, quelle langue.
- **`agents`** : quel ton chaque agent utilise par défaut. L'utilitaire `pm run tones <mission>`
  précâble le ton dans l'en-tête de l'agent (champ natif `skills:` de Claude Code).

Tons disponibles : `voice-deliverable` (livrables), `voice-casual` (informel),
`voice-maximilien` (voix de Maximilien), `voice-adservio` (charte Adservio).

## Portabilité : changer de mission

1. Copier `profiles/sinbad` -> `profiles/<mission>` (SINBAD = exemple de référence) et adapter la copie.
2. Ajuster `profile.yml` (Jira, `pm_front`/`file_store`, dates…) et `pipeline.yml` (tons/schémas).
3. `pm run drive-scaffold <mission>` / `notion-scaffold <mission>` : crée l'arbo **manquante** uniquement.
4. Les générateurs tournent sur le nouveau Jira/Drive sans changer une ligne de code.

## État

Les phases de démarrage sont faites (squelette, loader, profil SINBAD complet, générateurs,
garde-fous, routines). L'avancement détaillé lot par lot est dans [ROADMAP.md](ROADMAP.md).

## Ce qui reste à confirmer

- Identifiant de la page racine Notion « Project Management » (dans `profile.yml`).
- Nom définitif du framework / dépôt (`pm-framework` est provisoire).
