---
name: archi
description: harness du schema d'archi interactif (model-first) : rend, valide, exporte draw.io.
meta:
  produces: architecture-schema
  consumes: []
  mcp_deps: []
  cost: heavy-local
  status: stable
---

# Générateur : architecture (stack-imagery, model-first)

Schéma d'architecture interactif + export draw.io, **générés depuis un modèle unique**. On ne dessine
plus de HTML à la main : on déclare le modèle, le framework rend et valide.

## Point de départ : l'exemple de référence

Avant d'écrire un modèle, **partir de l'exemple de référence** - un vrai schéma, pas un gabarit vide :

- **Modèle d'exemple** : `profiles/demo/architecture/model.json` (entités, zones, flux, vues, entités
  d'exploitation). On copie, on adapte. Une mission a son propre modèle dans
  `profiles/<mission>/architecture/model.json`, pointé par sa config.
- **Style visuel cible** : `showcase.html` (dans ce dossier) - un schéma complet et rendu, qui montre le
  niveau de finition attendu (mise en page, sélecteur de vues, logos). On s'en inspire pour le rendu.
- **Logos techno communs** (AWS, Kubernetes, Keycloak, Prometheus, Redis, Terraform, ArgoCD, FluxCD,
  React, shadcn...) : bibliothèque **partagée** `framework/assets/logos/`, réutilisable telle quelle.
  Les technos sont les mêmes d'un projet à l'autre. Seuls les logos de **marque** (Safran, partenaires)
  vont dans `profiles/<mission>/logos/`.
- **Gabarit vierge** : `model.example.json`, uniquement pour un départ de zéro.

## Deux façons de déclarer le modèle

1. **Éditer le modèle** : partir de l'exemple démo (ou copier `model.example.json`), le remplir selon
   `SCHEMA.md` (entités, flux, zones, **vues + membres + layout**).
2. **Dicter en prompt** : décrire l'archi en langage naturel (« un frontend qui appelle un BFF,
   qui appelle un service métier, qui lit une base… vues : overview, données, identité »). L'agent
   `architecture` en produit un `model.json` **conforme à `SCHEMA.md`**, qu'on relit avant de rendre.

Dans les deux cas, la suite est identique.

## Le pipeline

```
pm run architecture <mission> --render          # modèle -> HTML interactif (généré)
pm run architecture <mission>                   # harness : 7 invariants, doit tout passer
pm run architecture <mission> --export drawio   # une page draw.io PAR ÉCRAN (lit views[].members)
pm run architecture <mission> --import x.drawio # draw.io -> model.json reconstruit (scratchpad)
pm run architecture <mission> --import x.drawio --enrich --page "Big Picture"   # + style par défaut
pm run architecture <mission> --suggest         # questions d'abstraction à poser (public, couches)
pm run architecture <mission> --render --public direction --set aifa=abstrait,exploitation=masque
# puis publication (écriture gardée) : 3 cibles au même md5
```

## Construire la vue d'ensemble avec la personne

Le modèle déclare des **couches** (`layers`, voir `SCHEMA.md`). Chaque couche peut être **dépliée**,
**abstraite** (un bloc avec loupe, détail au clic) ou **masquée** dans la vue d'ensemble. Le générateur
ne tranche pas seul : `--suggest` produit les **questions** (public d'abord, puis chaque couche) avec sa
**proposition motivée** (public, densité, chemin principal de la donnée). On les pose à la personne
(formulaire de questions), puis on applique ses réponses avec `--public` / `--set`. Les choix sont
gardés dans `abstraction.json` à côté du modèle et relus à chaque rendu.

Une couche du chemin principal (`main: true`) ne peut pas être masquée.

## Style (repris du schéma SINBAD par défaut)

- **Loupe** sur tout élément cliquable (`link`), drill-down vers la vue cible.
- **Couleurs de rôle** via `color` : `core` violet, `service` vert, `auth` rose, `storage` orange,
  `db` bleu, `cluster` bleu k8s, `risk` rouge, `ops` ambre, `partner` cyan, `ext` gris.
- **Encarts d'équipe** : `zone.style: "team"` (tirets colorés, titre gras).
- **Animations** : flux `main: true` animés, apparition des vues, survol des blocs ; `prefers-reduced-motion` respecté.

## Importer un draw.io (symétrique de l'export)

`--import <fichier.drawio>` reconstruit un `model.json` conforme à `SCHEMA.md` depuis un draw.io
(généré par le framework **ou** dessiné à la main) : zones, entités (label/sub/zone), flux
(`kind` déduit : double flèche -> `pull`), vues + membres (une page draw.io = une vue). Gère les
pages en XML clair **et** compressées. Le round-trip modèle -> draw.io -> modèle est fidèle.

- **Sortie dans le scratchpad** par défaut ; ne touche jamais le modèle de la mission.
- **Logos déduits des libellés** (« keycloak », « S3 », « Airbus »…) depuis la bibliothèque partagée
  `framework/assets/logos/`, le **schéma par défaut de la mission** (`source_html`, son `window.LOGOS`)
  et `profiles/<mission>/logos/` ; `--logos-from <html|model.json|dossier>` ajoute une source. Rien
  n'est inventé : une entité sans correspondance garde `logo: null`.
- **draw.io dessiné à la main** : zones déduites par **imbrication géométrique**, flèches posées sans
  accroche rattachées au plus petit bloc sous leur extrémité, libellés de flèches (`edgeLabel`) repris,
  entités HTML (`&nbsp;`) décodées, formes vides ignorées.
- Point de départ, pas pixel-exact : on relit (et on déclare les couches) avant de rendre.

## Enrichir un import (`--enrich`, module `enrich.py`)

Un import brut rendu tel quel sort un **squelette plat** (ni rôle, ni couleur, ni loupe, ni chemin
principal) : c'est attendu, un draw.io ne porte pas ces informations. `--enrich` ajoute ce qu'on
ajouterait à la main, **sans rien inventer** :

- **Rôle et couleur** par zone et entité, déduits de mots-clés (AIFA/DAG → `core`, services/modules →
  `service`, S3/inbox → `storage`, pipeline → `ops`, importeurs partenaires → `partner`, Keycloak/SSO →
  `auth`, RDS → `db`) ; l'entrée API (gateway, BFF) ressort en `core`. Non déduit = neutre.
- **Chemin principal animé** : flux qui partent du traitement ou arrivent sur l'API.
- **Loupe + vue détail** sur chaque zone d'au moins 2 entités (sauf la zone qui contient toute la page).
- **Cadre Kubernetes (EKS) > Namespace** autour de la plateforme, posé **dans** la zone englobante si
  elle existe (« SAI INFRASTRUCTURE » = le compte AWS) ; `--no-cluster` pour s'en passer.
- **Mise en page en étages** de haut en bas dans le sens de la donnée (stockage/pipeline → traitement →
  services → API et partenaires → front), en positions explicites (`views[].layout`).
- **Couches + questions systématiques**, toujours posées à la personne : Kubernetes / cluster /
  namespace, Exploitation, REST API / BFF, SSO / identité. Une couche absente de la page donne sa
  question (« l'ajouter ou la laisser à une autre vue ? ») : jamais de nœud fabriqué.

`--page` choisit la page draw.io (une page = une vue) ; une page inconnue est refusée avec la liste.

## Les pièces

- **Contrat** : `SCHEMA.md` (structure du modèle, alignée sur le harness).
- **Moteur générique** : `build_html.py` (modèle → HTML validé), `validate.py` (7 invariants),
  `export_drawio.py` (modèle → .drawio par écran), `import_drawio.py` (.drawio → modèle, logos déduits),
  `enrich.py` (import brut → rôles, couleurs, chemin principal, loupes, cadre EKS, étages, questions),
  `abstraction.py` (couches : modes, propositions, questions), `render.py`/`KNOWLEDGE.md` (primitives, conventions).
- **Tests** : `framework/harness/test_archi.py` (couches, loupes, couleurs, aller-retour et import draw.io).
- **Config de mission** : `profiles/<mission>/architecture.yml` (chemin du modèle, artefacts, cibles).
- **Artefacts** : le `model.json` et le HTML vivent côté mission ; la config les pointe.

## Garde-fous

- La **source de vérité est le modèle** : on régénère, on ne patche pas le HTML.
- Rien n'est publié sans validation ; les 7 invariants doivent passer.
- Le draw.io par écran découle de `views[].members` - aucune invention de contenu de vue.
