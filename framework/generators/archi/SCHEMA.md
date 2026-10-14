# Contrat du modèle d'architecture (model-first)

Le **modèle est la source de vérité unique**. On ne dessine plus de HTML à la main : on déclare le
modèle, puis le framework **génère** le HTML interactif (validé par le harness) et **exporte** le
draw.io par écran. Résultat : partir de 0 et monter un schéma complexe par un process net.

## Fichier modèle (`model.json`)

```jsonc
{
  "meta":   { "project": "NOM", "owner": "…", "theme": "dark" },
  "palette":{ "bg":"#000", "surface":"#171b22", "ink":"#e8ebf0", "ink2":"#a2abba",
              "accent":"#6fa2d6", "border":"#2a303b" },      // -> tokens :root (harness)

  "logos":  { "airbus": "data:image/webp;base64,…", … },     // id -> data-URI (window.LOGOS)

  "zones":  [ { "id":"cloud", "label":"AWS eu-west-1", "parent": null },
              { "id":"ns",    "label":"Namespace SINBAD", "parent":"cloud", "link":"donnees" } ],
              // zone.link (optionnel) = id de vue cible : le CADRE devient cliquable (drill-down)

  "entities":[ { "id":"bff", "label":"BFF", "sub":"API", "zone":"ns", "logo": null },
               { "id":"airbus","label":"Airbus","sub":"EO","zone":null,"logo":"airbus" },
               { "id":"api","label":"Service","sub":"métier","zone":"ns","logo":null,"link":"donnees" } ],
               // entity.link (optionnel) = id de vue cible : le NOEUD devient cliquable (drill-down)

  "flows":  [ { "from":"frontend", "to":"bff", "label":"HTTPS", "kind":"call" },
              { "from":"bff", "to":"db", "label":"récupère", "kind":"pull" } ],  // pull/read = double flèche

  "views":  [
    { "id":"overview", "label":"Vue d'ensemble", "members":["frontend","bff","db","airbus"] },
    { "id":"data", "label":"Données", "members":["airbus","s3","aifa"],
      "layout": { "airbus":[40,40], "s3":[300,40], "aifa":[300,200] } }   // positions optionnelles
  ]
}
```

## Règles (alignées sur le harness `validate.py`)

- **`palette`** → tokens couleur sur `:root` (invariant « Tokens dans :root »).
- **`logos`** → `window.LOGOS` (invariant « Logos résolus ») ; plate blanche automatique.
- **`views[].id`** → une vue HTML `id="v-<id>"` + une page draw.io ; la navigation (`data-go`, `names`,
  `back()`) est générée (invariant « Navigation »).
- **`flows`** → flèches **rectilignes** (H/V) ; `kind` ∈ {call, pull, read, write, auth} ; `pull`/`read`
  = double flèche (convention `KNOWLEDGE.md`). Marqueurs à **id unique par vue** (invariant « Marqueurs »).
- **`zones`** (imbricables via `parent`) → cadres de regroupement ; `entities[].zone` place l'entité.
- **`views[].members`** = ce qui est **dans l'écran** (c'est ce qui manquait au modèle artisanal) ; les
  flux affichés = ceux dont `from` et `to` sont tous deux membres, sauf override.
- **`layout`** optionnel par vue : positions explicites, sinon **auto-placement** (par zone puis grille).
- **`link`** optionnel sur une **entity** ou une **zone** = id d'une **autre vue** : le nœud (ou le cadre
  de zone) devient **cliquable** et renvoie vers cette vue (**drill-down inter-schémas**). En HTML :
  `data-go="<vue cible>"` + liseré accent et petit « › » (le clic appelle `go()`). En draw.io : lien
  **cross-page** `link="data:page/id,<vue cible>"` sur le shape (chaque `<diagram>` porte un `id`= id de
  vue). Un `link` qui pointe vers une vue inexistante, ou vers la vue courante, est ignoré (aucun effet).
- Chaque vue a un **`viewBox`** (invariant « viewBox »), et l'équilibre SVG/`<g>` est tenu par le
  générateur (invariant « Équilibre »).

## Le process, de 0 à un schéma

1. Copier `model.example.json` → la mission, le remplir (entités, flux, vues+membres).
2. `pm run architecture <mission> --render`  → HTML interactif généré.
3. `pm run architecture <mission>`            → harness (7 invariants) : doit tout passer.
4. `pm run architecture <mission> --export drawio` → une page draw.io par écran.
5. Publier (écriture gardée) : 3 cibles au même md5.

Le draw.io **par écran** est automatique : il lit `views[].members`.
