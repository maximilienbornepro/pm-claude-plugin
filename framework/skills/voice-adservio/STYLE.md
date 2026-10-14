# Charte de rédaction et de schématisation Adservio

Distillé du dossier de fond `reference/rapport-aidlc.html` (STEF × Adservio, « Le cycle de vie logiciel
piloté par l'IA »). C'est **la** référence de style pour tout texte et tout schéma produits avec ce profil.
Document HTML = charte complète (palette + typo + composants). Notion / SharePoint = on garde le **ton** et
la **structure** ; le visuel exact (police, bleu royal) ne s'applique qu'aux livrables HTML.

## Le ton

- **Français, éditorial, dense et net.** Pas de remplissage, pas d'adverbes faibles, pas de « il est
  important de ». Chaque phrase porte une idée. On affirme.
- **Analytique et sourcé.** On cite les chiffres avec leur source (« 2 410 milliards de dollars … 2022 »),
  on nomme les auteurs et les papiers (« défini chez AWS par Raja SP »), on distingue les faits des lectures.
- **Définitions crisp.** Un terme nouveau est défini en une phrase, souvent par contraste (« Ce n'est pas un
  outillage : c'est une réécriture… »). On oppose avant/après, hérité/nouveau.
- **Analogies fortes** pour ancrer une idée abstraite (le GPS, « des automobiles, pas des chariots à chevaux
  plus rapides »). Une par idée, jamais filée.
- **Hiérarchie de l'emphase** : `**gras**` pour les termes clés et les concepts nommés ; l'italique au sens
  « em » est en réalité du **medium noir non-italique** (voir `em` dans la charte) ; jamais de capitales
  criées dans le corps.
- **Listes de principes** : intitulé en gras (le nom du principe), puis une phrase d'explication. Jamais une
  liste à plat de fragments.
- **Tiret** : la charte d'origine emploie le tiret cadratin « — ». **Pour Sinbad, on garde le tiret classique
  `-`** (règle projet CLAUDE.md), entouré d'espaces, qui tient le même rôle de rupture. Jamais de point médian.

## La structure d'un document

Dans l'ordre, pour un dossier/note de fond :

1. **Avant-titre** (`.avant-titre`) : petite ligne capitale, le contexte (« STEF × Adservio - Dossier de fond »).
2. **Titre** (`h1`) : court, fort, ~22 caractères de large max, lettrage serré.
3. **Sous-titre** (`.sous-titre`) : une phrase légère (weight 300) qui résume le périmètre.
4. **Colophon** (`.colophon`) : métadonnées en ligne (relevé : date · corpus · méthode).
5. **Sommaire** (`.sommaire`) : numéroté `01, 02…` (decimal-leading-zero), deux colonnes.
6. **Sections** (`section`) : `.tete-section` = `.numero-section` (bleu royal) + `h2`, puis un **chapeau**
   (`.chapeau`, weight 300) qui pose la section en une phrase, puis le corps.
7. **Dans le corps** : `h3` (sous-partie), `h4` (petit label capitale), paragraphes (max ~76ch), `ul.liste`,
   `.encadre` (fond neige, pour une mise en exergue), `.carte`, `.tuile-chiffre` (grand chiffre + légende +
   source), `.bloc-table` (tableaux), `.figure` / `.diagramme` (schémas + légende).
8. **Pied** (`.pied`) et **Sources** (`.sources`) : références en mono atténué.

Adapter sans tout appliquer : une note courte = avant-titre + titre + chapeau + corps. Le colophon, le
sommaire et les onglets sont pour les dossiers longs.

## La palette (tokens de la charte)

| Rôle | Token | Valeur |
|---|---|---|
| Fond | `--blanc` / `--neige` | `#FFFFFF` / `#F5F5F7` |
| Bordure | `--bordure` | `#E8E8E8` |
| Titres / texte fort | `--noir` | `#1D1D1F` |
| Corps | `--corps` | `#6E6E73` |
| Atténué / labels | `--tertiaire` | `#86868B` |
| Accent | `--royal` | `#0033FF` |
| Accent clair | `--sky` | `#38B6FF` |
| Accent 2 | `--rose` | `#FF66C4` |
| Alerte | `--corail` | `#FF5757` |

Police **Adservio** (fallback `system-ui`). Corps 14px, interligne 1.65, `font-variant-numeric: tabular-nums`
implicite par la police. Beaucoup de blanc, coins arrondis 12px, bordures fines `1px`, aucune ombre lourde.

## La schématisation (diagrammes « à la charte »)

- SVG propre, fond blanc ou neige, **bordure fine arrondie (12px)**, dans la palette ci-dessus (noir pour le
  trait, bleu royal pour l'accent, sky/rose/corail pour différencier, tertiaire pour l'atténué).
- **Flèches rectilignes**, libellés courts, légende sous la figure (`.figure figcaption` / `.diagramme-legende`).
- Possibilité d'onglets `.paire` : **« original » vs « Adservio »** pour montrer un schéma source puis sa
  version redessinée à la charte.
- Les points de liste colorés : `.point` (noir), `.point-accent` (royal), `.point-attenue` (sky),
  `.point-doux` (tertiaire).
- Pour les schémas d'architecture interactifs, réutiliser `stack-imagery/render.py` en remplaçant la palette
  par celle-ci (le skin « adservio » du schéma d'archi Sinbad est déjà cette charte).

## Pour Notion / SharePoint (le cas d'usage principal)

Ces supports ne rendent ni la police ni la mise en page HTML. On **transpose** :
- Le **ton** et la **structure** (avant-titre → petit intro en gras ; titre ; chapeau ; sections numérotées ;
  principes en gras + explication ; encadrés → citation ou callout ; chiffres sourcés).
- Les **composants visuels** (tuiles, cartes, onglets, SVG) ne se transposent pas : on les rend en tableaux
  Notion, en listes structurées, en callouts. Un schéma reste une image/figure.
- On respecte en plus les règles Notion/SharePoint du projet (skills `sinbad-notion`, règles OneDrive) :
  structurer dès trois points, un seul niveau d'indentation, pas de mention `@` réelle, « à confirmer » pour
  l'inconnu, tiret classique.
- Un **livrable HTML autonome** (note de fond, dossier, one-pager à partager) : là, on applique la charte
  complète via `template.html` + `charte.css` (+ la police depuis la référence).

## Exemples de formulation (le ton, mot pour mot)

> Ce n'est pas un outillage : c'est une réécriture du cycle de vie logiciel à partir de premiers principes.

> Le constat central est que les méthodes existantes ont été conçues pour des processus longs pilotés par
> l'humain ; les y greffer bride l'IA et reconduit leurs inefficacités.

> Optimiste sur le potentiel, réaliste sur l'état courant.

Structure d'un principe (liste) :

> **Inverser le sens de la conversation** - L'IA initie et dirige les échanges : elle décompose les intentions,
> propose des arbitrages, pose les questions. Les humains deviennent approbateurs aux points de décision.
