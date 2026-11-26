---
name: slide-style
description: Charte de TOUS les livrables du pm-framework rendus en slides 16:9 (HTML du dossier projet et export PPTX) - titres courts, légende explicative sous chaque titre, unités en jours, style noir / ivoire à aplats, logo du client. À appliquer avant de générer ou de modifier n'importe quelle slide ou page de livrable (avancement, sprints, planning, risques, suivi technique, RACI, gates, weekly, CR, agenda, architecture), et quand on demande « fais la slide », « refais le deck », « mets ça au format du dossier projet ».
user-invocable: true
---

# Charte des slides (dossier projet HTML et PPTX)

Export PowerPoint : générateur `dossier` (`pm run dossier <mission> --pptx out.pptx`), depuis
`profiles/<mission>/dossier.json`.

Tout livrable est **potentiellement une slide PPT** : chaque bloc HTML est un cadre 16:9 fixe, et l'export
PPTX en reprend la mise en page à l'identique. Maquette de référence :
`docs/maquette/index.html` (publiée avec le guide).

## 0. Une slide = le reflet d'un format qui existe déjà (règle dure)

Aucune slide n'invente sa mise en forme ni son contenu. Chaque slide est **la représentation fidèle** d'un
livrable, d'un générateur ou d'un agent du plugin, avec **la même structure, le même ordre, le même ton et
le même niveau de détail** (verbeux si la source l'est). Les deux restent liés : la source change, la
slide change.

| Slide | Reflet de | Ce qui est repris tel quel |
|---|---|---|
| Weekly report | générateur `weekly-report` + bloc publié dans la page Notion de suivi | « Semaine du JJ/MM - CR du JJ/MM », les 3 sections (Activités réalisées / Difficultés - Points d'attention / Plan d'action - sujets à cadrer), puces imbriquées par thème, voix du porteur |
| Compte rendu partenaire | générateur `partner-report` (mail) | objet, intro, un sujet par paragraphe (titre, situation, une seule prochaine étape avec jalon en gras), conclusion, signature |
| Situation technique, État des lieux | suivi des sujets (Notion) via `review-topics` / `technical-planning` | Sujet, Statut, Situation (= Contexte), Levier (= Action attendue), Échéance |
| Risques, Registre | registre des risques (`risks`, `review-risks`) | champs et niveaux du registre |
| Avancement, burn-down, états, sprints, projection | `plan` / `projection` (Jira) | chiffres du JSON de `plan` |
| Chantiers | slide « Build workstreams » du Project dashboard (**source à créer** : `chantiers.yml` ou base Notion des chantiers) | une ligne par chantier transverse (développement, interfaces partenaires, qualité, recette, contrat…) : n°, chantier, porteur, échéance, **barre d'avancement en %**, **pastille de statut en 4 couleurs** (vert dans les temps, jaune à clarifier, orange risque de retard ou de non-conformité, rouge en retard ou bloqué), commentaire « où en est-on », étoile = priorité de la semaine |
| Planning, jalons | `planning.json` (`technical-planning`) | couloirs, jalons, traits verticaux |
| RACI | `raci` (`raci.yml`) | activités × rôles |
| Gate | `gate` / `deck-gate` (`gate.yml`) | critères, statut, preuve ou action |
| Ordre du jour | `meeting-agenda` | points, porteur, durée |
| Architecture | `archi` (`model.json`), rendu de référence `golden` | **la vue macro seulement** (la page d'accueil du schéma), convertie en formes natives avec ses logos, zones et flux ; les sous-vues ne sont jamais sur la slide : un lien « Vue interactive et sous-vues » ouvre le HTML (gabarit dossier, `dossier_skin.py`) |
| Responsabilités inter-équipes | schéma de dépendances de la GATE 1 (**source à créer** : `teams.yml` ou `.drawio`) | **schéma** de blocs (une équipe par bloc, rôle en sous-titre) reliés par des flèches : pleine = doit un livrable ou une décision, avec l'activité ; pointillée = collaboration avec un partenaire extérieur ; **deux slides, toujours les deux** : (1) vue en réseau, pilotage au centre, client en haut, extérieurs en bas ; (2) **variante hiérarchique**, profils rangés par niveau selon leur nombre d'activités R ou A au RACI (pastille), flèches descendantes à angle droit par barres horizontales, échanges de même niveau à l'horizontale, aucun croisement. Jamais un tableau |
| Staffing | plan de staffing (**source à créer** : `Staffing_plan_<MISSION>.xlsx`) | **une ligne par ressource** (nom, rôle), une colonne par trimestre (T1, T2, T3… avec l'année), **trimestre en cours toujours présent et marqué**, valeurs en ETP, besoin sans nom = « À staffer », total ETP et capacité en jours. Pas de phases en en-tête |

Si aucune source n'existe, on ne fabrique pas la slide de tête : on crée d'abord la source (fichier du
profil ou générateur), puis la slide qui la reflète.

## 0 bis. Lien vers la source (toujours)

Chaque slide porte, en pied de page, un lien **« Source · <fichier ou page> ↗ »** vers le document de
référence : lien cliquable en HTML, lien hypertexte dans le PPTX. Le fichier reste la référence complète ;
la slide n'en montre qu'une vue.

| Slide | Fichier rattaché |
|---|---|
| RACI | `RACI_<MISSION>.xlsx` - **toujours**, il porte l'onglet par rôle |
| Risques, Registre | `Risks_<MISSION>.xlsx` |
| Staffing | `Staffing_plan_<MISSION>.xlsx` |
| Planning, Jalons | deck `Planning_<MISSION>.pptx`, Gantt Excel |
| Situation technique, Suivi technique, État des lieux | page Notion du suivi des sujets (pas d'Excel) |
| Weekly report | page Notion de suivi (section Weekly report) et `weekly-reports/<AAAA-Www>.md` |
| CR partenaire, Ordre du jour, Gate | page Notion correspondante |
| Avancement, sprints, projection | page « Avancement et sprints » (Jira) |
| Chantiers | deck `Project_dashboard_<MISSION>.pptx` et `chantiers.yml` |
| Architecture | page HTML interactive et vues `.drawio` |
| Responsabilités inter-équipes | `.drawio` du schéma de dépendances |

Les chemins et URL viennent du profil de la mission (`drive.root`, pages Notion déclarées) ; jamais de
chemin propre à un poste.

## 1. Titres : courts, jamais descriptifs

Le titre d'une slide est un **libellé court** qui dit **de quoi** parle la slide, pas ce qu'elle montre.

| Oui | Non |
|---|---|
| Planning | « Le front et la recette se chevauchent sur les deux dernières semaines » |
| État des lieux | « Le projet tient la date, sous réserve de l'API partenaire » |
| Tableau des états | « 142 tickets : 58 fermés, 9 bloqués dont 6 côté front » |
| Burn-down du plan | « À J+38, il reste 227 jours : la tendance finit à J+61 » |

- 1 à 4 mots, sans verbe, sans chiffre, sans conclusion.
- Le sur-titre (casse normale, gris) situe la slide : `Section · précision` (« Sprint 3 · du 17 au
  28 novembre »). Il peut porter une date ou une période, jamais une conclusion.
- Les slides noires de section portent le nom de la section, en casse normale.
- **Casse normale partout** (décision du 26/11/2026) : aucun texte en capitales, ni sur-titre, ni en-tête de
  tableau, ni légende, ni pied de page ; espacement des lettres très léger. Réglage unique : `CAPS` dans
  `framework/lib/slides.py` (PPTX) et la feuille de style de `html_render.py` (HTML).

## 2. Sous le titre : une légende qui explique la slide

Sous chaque titre, un **texte de deux à quatre phrases** qui explique **ce que la slide représente et
comment la lire** : ce que montrent les axes, les couleurs, les colonnes, d'où viennent les données, à quelle
date elles sont arrêtées, ce que signifient les repères (aujourd'hui, gel, ouverture).

- Ton : celui du **CR partenaire** (`generators/partner-report`) - phrases complètes, posées, précises,
  vouvoiement implicite, aucun jargon non expliqué.
- **Ne jamais recopier les chiffres** déjà visibles dans la slide (« 142 tickets dont 58 fermés ») : le
  tableau les donne, la légende dit comment le lire.
- Pas de conclusion ni d'opinion : ce qui est à retenir se dit à l'oral ou dans le CR.

Exemple, tableau des états :

> Ce tableau présente, pour chaque pôle, la répartition des tickets de la version 1 selon leur état dans
> le tracker, arrêtée au jour du comité. La dernière colonne reprend cette répartition en barre, de
> l'à-faire au fermé, pour comparer les pôles d'un coup d'œil ; la ligne de total couvre l'ensemble du
> périmètre.

## 3. Unités : toujours des jours

- On parle **en jours**, jamais en points. Convention actuelle : **1 point = 1 jour** (à réévaluer plus
  tard ; la conversion se fait à la lecture des données, pas dans le texte).
- Charge, reste, capacité, vélocité, burn-down : en jours (« 31 j restants », « capacité 50 j »).
- Le temps se repère en **J+n** depuis le démarrage, avec la date à côté (« J+38 · 26/11 »). Les courbes
  ont un axe gradué en jours, la zone des jours écoulés grisée et un repère « aujourd'hui ».

## 4. Style

- **Slide noire** pour chaque titre de section : texte blanc, filet doré, logo du client en blanc.
- **Slides de contenu** sur fond ivoire `#F7F4EF`, encre `#1A1A1A`.
- **Typo sans empattement, très légère** (Helvetica Neue Light/UltraLight ; repli Segoe UI Light en PPTX).
  Jamais de serif.
- **Aplats de couleur**, sans dégradé ni ombre : sable `#E9DFD1`, taupe `#B7A99A`, sauge `#A9B5A0`,
  ardoise `#5E6670`, noir `#0B0B0B` ; **bordeaux `#7A1F23` réservé au critique / bloqué** ; or `#B8975A`
  pour les filets et jalons.
- Mêmes couleurs partout pour un même sens : niveau de risque, statut de sujet, état de ticket.
- Tableaux sans grille, un filet fin entre les lignes, 6 à 10 lignes au plus ; au-delà, pagination.

## 5. Logo du client

Déclaré dans le profil (`profiles/<mission>/logos/`) en quatre variantes transparentes :
`client-noir.png`, `client-blanc.png`, `client-noir-texte.png`, `client-blanc-texte.png`.

- Couverture : logo complet blanc, grand, centré.
- Slides noires : logo complet blanc, en haut à gauche.
- Slides de contenu : logo texte noir, petit, en haut à droite.
- Mêmes emplacements dans l'export PPTX.

## 6. Pied de page

`<Projet> · <section>` à gauche, numéro de slide à droite, en gris, casse normale.
