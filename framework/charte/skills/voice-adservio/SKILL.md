---
name: voice-adservio
description: >
  Profil de rédaction ET de schématisation à la charte éditoriale Adservio, dérivé du dossier de fond
  "AI-DLC" (reference/rapport-aidlc.html). À utiliser pour tout texte, note, dossier ou schéma à produire
  dans ce style soigné "Apple-like" : livrable HTML autonome (charte complète), ou contenu Notion/SharePoint
  (on transpose le ton et la structure). Profil spécifique, invocable par l'utilisateur.
---

# redaction-adservio

Charte complète : [`STYLE.md`](STYLE.md). Référence qui fait foi : [`reference/rapport-aidlc.html`](reference/rapport-aidlc.html).
CSS des composants : [`charte.css`](charte.css). Gabarit d'un nouveau document : [`template.html`](template.html).

## Quand l'employer

- L'utilisateur demande un texte « dans le style du dossier AI-DLC / Adservio », ou invoque ce profil.
- Un **dossier de fond, une note, un one-pager, une synthèse** à partager, surtout destiné à Notion/SharePoint.
- Un **schéma** à dessiner « à la charte » (palette royal/sky/corail, coins arrondis, légende).

## Le ton (résumé, détail dans STYLE.md)

Français éditorial, dense et net. On affirme, on définit par contraste, on cite les chiffres avec leur
source, on ancre avec une analogie forte par idée. Termes clés en **gras**, emphase forte en medium noir
(jamais d'italique criard). Les listes de principes : **intitulé en gras** puis une phrase. Pas de remplissage.

## La structure

Avant-titre (petit label) · Titre court et fort · Sous-titre léger · Colophon (métadonnées) · Sommaire
numéroté · Sections numérotées (numéro + h2 + chapeau + corps) · encadrés, cartes, tuiles-chiffre, tableaux,
figures/diagrammes · pied + sources. Adapter : une note courte garde juste avant-titre, titre, chapeau, corps.

## Deux cas de production

1. **Livrable HTML autonome** : partir de `template.html`, inliner `charte.css` et les `@font-face`
   'Adservio' depuis la référence (base64) pour le rendu de police exact. Schémas en SVG à la charte
   (réutiliser `stack-imagery/render.py` en basculant la palette sur celle d'Adservio).
2. **Notion / SharePoint** (cas principal) : on **transpose le ton et la structure**, pas le HTML. Avant-titre
   → intro en gras ; sections numérotées ; principes en gras + explication ; encadré → callout/citation ;
   chiffres sourcés. Les composants visuels deviennent tableaux/listes/callouts ; un schéma reste une image.
   On applique **en plus** les règles du support : `sinbad-notion` (structurer dès trois points, un niveau
   d'indentation, pas de mention `@` réelle) et les garde-fous OneDrive/SharePoint.

## Règles non négociables

- **Tiret classique `-`** (règle projet), jamais le tiret cadratin de la charte d'origine. Jamais de point médian.
- **Ne rien inventer** : chiffre, acronyme ou capacité inconnus → « à confirmer ».
- Respecter la langue du contexte (français par défaut ; voir le catalogue `REDACTION.md`).
- Rien n'est écrit dans Notion/SharePoint/Office sans validation et sans les garde-fous des skills dédiés.

## À ne pas confondre

Profil **esthétique/éditorial** (mise en forme soignée, charte). Pour la **voix de Maximilien** (mails,
Slack, CR qu'il signe) c'est `redaction-maximilien` ; pour le **ton pro neutre** des livrables Sinbad c'est
`sinbad-redaction`. Les deux peuvent se combiner avec cette charte (le ton de la personne, la forme Adservio).
