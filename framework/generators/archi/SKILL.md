---
name: archi
description: harness du schema d'archi interactif (model-first) : rend, valide, exporte draw.io.
meta:
  produces: architecture-schema
  consumes: []
  mcp_deps: []
  cost: heavy-local
  status: draft
---

> **Statut (23/11/2026) : expérimental.** Le rendu automatique depuis le modèle n'est pas fiable (« éclaté »
> sur un vrai schéma). **Méthode recommandée : construire le schéma à la main, par prompting**, en partant
> de la source HTML artisanale de référence (agent `archi-audit` / skill `stack-imagery` de la mission),
> puis valider avec `validate.py`. Le modèle reste utile comme inventaire et pour l'export draw.io.

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

## Style : celui du schéma de référence, à l'identique (`golden.py`, depuis le 13/11/2026)

Le rendu par défaut reprend **exactement** le schéma d'architecture publié sur gh-pages : même feuille de
style (`golden_style.css`, copiée telle quelle, on ne la retouche pas, on étend en fin de `_EXTRA_CSS`), même
coquille (menu, thème clair / sombre, fil d'Ariane, scène), même vocabulaire SVG (`g.blk` + `rect.bg`,
`.box`, `.flow` animé, `.arr`, `.auth`, `.lbl`, `.t`, `.tm`, `.s`). L'ancien rendu reste accessible par
`meta.style: "legacy"`.

- **Harmonie de la vue d'ensemble** : colonne centrale = le compte cloud (stockage en tête, puis cadre
  Kubernetes avec son onglet, namespace, blocs empilés pleine largeur dans l'ordre des flux, deux petits
  blocs côte à côte) ; à gauche les sources ; à droite exploitation, API et applications externes, alignées
  sur le bloc qu'elles touchent ; en bas les acteurs (flèches qui montent).
- **Toute la zone est cliquable** : une zone qui a sa vue devient une carte `g.blk` entière, avec loupe.
- **Sous-vues** : bouton retour, légende en tête, **flèche pointillée « depuis … »** qui vient du haut
  (amont de la vue, sinon la vue parente), chaîne de traitement de gauche à droite, sorties en dessous,
  la suite cliquable en bout de chaîne ; les zones filles qui ont leur vue sont repliées en cartes.
- **Diagrammes de séquence** : vue `kind: "sequence"` (`participants`, `messages` avec `kind: auth|return`,
  `caption`, `notes`), rendue comme « Applications partenaires » : en-têtes, lignes de vie pointillées,
  messages numérotés, échanges d'authentification en rose pointillé.
- **Import draw.io par vue** : toujours **figé dans le modèle**, jamais dans le navigateur (aucun bouton) ;
  un diagramme de séquence (`umlLifeline`) est rendu en séquence, sinon en boîtes et zones :
  `python3 import_view.py model.json --view <id> fichier.drawio [--page N|nom] [-o sortie.json]`.
- **Couleurs de rôle** via `color` : `core` violet, `service` vert, `auth` rose, `storage` orange,
  `db` bleu (cylindre), `cluster` bleu k8s, `risk` rouge, `ops` ambre, `partner` cyan, `ext` gris.
- **Logos** : ceux du modèle, complétés par la bibliothèque partagée (`framework/assets/logos`).

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

## Pas d'interface d'édition (décision du 24/11/2026)

Le schéma se construit **uniquement par prompt, avec un template** : on décrit (ou on importe un draw.io
par la commande `import`), on obtient le modèle (`SCHEMA.md`), `build_html.py` le rend au style de
référence. Aucun éditeur graphique, aucun bouton d'import ni d'édition dans la page rendue : un import
draw.io se fige dans le modèle (`import-view`), jamais dans le navigateur. L'ancien éditeur (`editor/`,
13/11) a été retiré du plugin et du kit.

## Le kit à envoyer (`dist/archi-kit.zip`)

Un zip autonome pour qu'une autre personne utilise le générateur sans le plugin : Python 3.9+, aucune
dépendance, `LISEZMOI.md` (démarrage, import draw.io, modèle, séquences, import par vue, export,
contrôle), `archi.py` (point d'entrée : `demo`, `build`, `import`, `import-view`, `export`, `check`),
exemples. Aucune donnée de mission (garde-fou), et le kit se teste lui-même (il doit générer sa démo)
avant d'être écrit.

- **Toujours à jour, sans action** : le hook `PostToolUse` du plugin (`framework/hooks/archi_kit.py`)
  relance `pack_kit.py --if-stale` après toute modification du générateur, des logos partagés ou du
  modèle de démo ; `publish.sh` le reconstruit à chaque version. Copie sur le Bureau
  (`~/Desktop/archi-kit.zip`, ou `ARCHI_KIT_COPY`).
- À la main : `python3 framework/generators/archi/pack_kit.py`.
- **Toute évolution du générateur met à jour le `LISEZMOI.md` du kit** (texte dans `pack_kit.py`) si
  une commande, une option ou un comportement visible change.

## Les pièces

- **Contrat** : `SCHEMA.md` (structure du modèle, alignée sur le harness).
- **Moteur générique** : `build_html.py` (modèle → HTML validé, délègue à `golden.py` + `golden_style.css` + `golden_import.js`), `import_view.py` (fige un draw.io dans une vue), `validate.py` (7 invariants),
  `export_drawio.py` (modèle → .drawio par écran), `import_drawio.py` (.drawio → modèle, logos déduits),
  `enrich.py` (import brut → rôles, couleurs, chemin principal, loupes, cadre EKS, étages, questions),
  `abstraction.py` (couches : modes, propositions, questions), `render.py`/`KNOWLEDGE.md` (primitives, conventions).
- **Tests** : `framework/harness/test_archi.py` (couches, loupes, style de référence, séquences, import figé, aller-retour et import draw.io).
- **Config de mission** : `profiles/<mission>/architecture.yml` (chemin du modèle, artefacts, cibles).
- **Artefacts** : le `model.json` et le HTML vivent côté mission ; la config les pointe.

## Garde-fous

- La **source de vérité est le modèle** : on régénère, on ne patche pas le HTML.
- Rien n'est publié sans validation ; les 7 invariants doivent passer.
- Le draw.io par écran découle de `views[].members` - aucune invention de contenu de vue.

## Deux gabarits HTML

- **Rendu de référence** (`golden.py`) : inchangé, le schéma interactif tel qu'on le publie.
- **Gabarit dossier projet** (`dossier_skin.py`) : le même schéma habillé à la charte des slides (logo du
  client, sur-titre, titre, légende, typo légère, fond ivoire), vue macro en tête, sous-vues toujours
  accessibles. `python3 framework/generators/archi/dossier_skin.py <mission> -o architecture.html`.
- **Slide PowerPoint** : le générateur `dossier` (type `archi`) convertit la vue macro en formes natives
  (`framework/lib/svg2pptx.py`) et met un lien vers ce gabarit.
