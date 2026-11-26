# stack-imagery

Outillage du **schéma d'architecture SINBAD interactif** (un seul HTML navigable et thémable) :
source canonique versionnée, modèle sémantique, bibliothèque de primitives, harness de validation.
Pensé aussi pour **reproduire un schéma équivalent sur une autre infra**.

## Le choix de conception (important)

Le schéma est **artisanal** : chaque vue est du SVG placé à la main pour un rendu propre (positions au
pixel, doubles flèches, encarts d'équipe, entrées par le haut). On **n'a pas** de générateur déclaratif
qui reproduit tout : ce serait un gouffre et on perdrait en finesse. À la place :

- **La source de vérité, c'est le HTML** : [`architecture_sinbad.html`](architecture_sinbad.html). On l'édite.
- **Le sens est capturé en déclaratif** dans [`model.json`](model.json) (acteurs, zones, composants, stores,
  flux) + [`KNOWLEDGE.md`](KNOWLEDGE.md) (le pourquoi, les décisions). C'est **ça** qui change quand l'infra
  change, et **ça** qu'on forke.
- **Les primitives** ([`render.py`](render.py)) rendent l'édition/reconstruction d'une vue rapide et conforme
  aux conventions.
- **Le harness** ([`validate.py`](validate.py)) refuse une publication qui casse un invariant.

## Fichiers

| Fichier | Rôle |
|---|---|
| `architecture_sinbad.html` | **Source canonique** (thème original par défaut). On édite ici. |
| `architecture_sinbad_theme.html` | Variante « Light » (dérivée à la publication). |
| `model.json` | Modèle sémantique (le QUOI) - **forkable** pour une autre infra. |
| `KNOWLEDGE.md` | Faits et décisions d'architecture (le pourquoi). |
| `render.py` | Primitives de dessin (A, box, card, team, db, roundtrip, dashed_in, svg, shell...). |
| `validate.py` | Harness : 7 invariants, exit 0/1. |
| `publish.sh` | Dérive le thème Light + pousse gh-pages (rappelle les artefacts). |
| `reference/architecture_sinbad.golden.html` | Dernier état publié (pour diff). |

## Boucle de travail (à chaque modification)

```bash
cd stack-imagery
# 1. éditer architecture_sinbad.html (remplacement de chaîne unique, ou régénérer une vue avec render.py)
python3 validate.py architecture_sinbad.html     # 2. harness : doit être tout vert
./publish.sh                                      # 3a. dérive Light + pousse gh-pages
# 3b. publier les 2 artefacts Claude (voir model.json > publish) - via l'outil Artifact
```

**Toujours les 3 cibles ensemble** (artefact original + artefact Light + gh-pages), puis recaler le golden.
Prévisualisation locale : `python3 -m http.server` dans ce dossier.

## Les 7 invariants du harness (bugs réels à ne jamais réintroduire)

1. Équilibre `<svg>` / `<g>`.
2. **Flèches rectilignes** (H/V) ; courbes de boucle et poignées de loupe exemptées.
3. **Id de marqueur unique** par document ; chaque `url(#id)` résout.
4. **Tokens couleur dans le `:root` de base** (sinon invisibles en thème par défaut).
5. **Navigation** : chaque `data-go` a une vue `v-<id>` et un libellé `names` ; `back()` géré.
6. **Logos résolus** : chaque `data-logo` existe dans `window.LOGOS`.
7. **viewBox** présent sur chaque vue.

## Conventions de rendu (voir `model.json > conventions`)

- **Double flèche** quand un composant TIRE la donnée (BFF récupère, Frontend appelle) : demande d'un côté,
  donnée en retour de l'autre.
- **Métriques** : de l'applicatif vers Prometheus (scrape), jamais d'Enix vers Prometheus.
- Entrée d'un flux externe **par le haut** en tiretés ; base de données = **cylindre PostgreSQL**.
- **Encarts d'équipe** (CIP / Devs / Enix) : l'encart porte le nom, donc pas de suffixe ni de logo
  d'appartenance sur les outils dedans.
- Tiret classique `-`, jamais de tiret cadratin. Inconnu = « à confirmer ».

## Reproduire sur une autre infra

1. Copier `model.json` et y mettre les nouveaux acteurs / zones / composants / stores / flux.
2. Reconstruire les vues à la main avec `render.py` (une vue = `svg(viewBox, corps, mid, aria)` ; assembler
   la page avec `shell(...)`), en suivant les conventions ci-dessus.
3. `validate.py` à chaque étape, puis publier.

L'agent `stack-imagery` (dans `.claude/agents/`) automatise la maintenance : il lit les sources de vérité
(transcriptions, draw.io, Jira), propose un diff par vue, applique via les primitives, valide, et rend la
main pour publication. Il n'écrit et ne publie **jamais** sans validation.
