# Générateur : architecture (stack-imagery, model-first)

Schéma d'architecture interactif + export draw.io, **générés depuis un modèle unique**. On ne dessine
plus de HTML à la main : on déclare le modèle, le framework rend et valide.

## Point de départ : l'exemple SINBAD

Avant d'écrire un modèle, **partir de l'exemple de référence** - un vrai schéma, pas un gabarit vide :

- **Modèle SINBAD** : `profiles/sinbad/architecture/model.json` (entités, zones, flux, vues réelles).
  Donne au prompt un contexte pertinent : on copie, on adapte à la nouvelle mission.
- **Logos techno communs** (AWS, Kubernetes, Keycloak, Prometheus, Redis, Terraform, ArgoCD, FluxCD,
  React, shadcn...) : bibliothèque **partagée** `framework/assets/logos/`, réutilisable telle quelle.
  Les technos sont les mêmes d'un projet à l'autre. Seuls les logos de **marque** (Safran, partenaires)
  vont dans `profiles/<mission>/logos/`.
- **Gabarit vierge** : `model.example.json`, uniquement pour un départ de zéro.

## Deux façons de déclarer le modèle

1. **Éditer le modèle** : partir de l'exemple SINBAD (ou copier `model.example.json`), le remplir selon
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
# puis publication (écriture gardée) : 3 cibles au même md5
```

## Les pièces

- **Contrat** : `SCHEMA.md` (structure du modèle, alignée sur le harness).
- **Moteur générique** : `build_html.py` (modèle → HTML validé), `validate.py` (7 invariants),
  `export_drawio.py` (modèle → .drawio par écran), `render.py`/`KNOWLEDGE.md` (primitives, conventions).
- **Config de mission** : `profiles/<mission>/architecture.yml` (chemin du modèle, artefacts, cibles).
- **Artefacts** : le `model.json` et le HTML vivent côté mission ; la config les pointe.

## Garde-fous

- La **source de vérité est le modèle** : on régénère, on ne patche pas le HTML.
- Rien n'est publié sans validation ; les 7 invariants doivent passer.
- Le draw.io par écran découle de `views[].members` - aucune invention de contenu de vue.
