# Guide d'utilisation - plugin pm-framework

Le plugin **pm-framework** outille un chef de projet technique (TPM / PMO) dans Claude Code : il produit
les livrables de pilotage (planning, avancement, risques, RACI, schéma d'architecture, comptes rendus…)
à partir des sources du projet (Jira, Notion, SharePoint / OneDrive, Slack, transcriptions), et il le fait
**en conversation** : on demande, Claude prépare, montre, et n'écrit qu'après accord.

Ce guide couvre tout le plugin : ce qu'il sait faire, comment on s'en sert, quels prompts utiliser.

**Sommaire**

1. [L'essentiel en deux minutes](#1-lessentiel-en-deux-minutes)
2. [Installer et démarrer](#2-installer-et-démarrer)
3. [Comment on s'en sert : parler à Claude](#3-comment-on-sen-sert--parler-à-claude)
4. [Catalogue de ce que sait faire le plugin](#4-catalogue)
5. [Guides pas à pas](#5-guides-pas-à-pas)
6. [Les routines (tâches planifiées)](#6-les-routines)
7. [Les agents](#7-les-agents)
8. [Les tons de rédaction](#8-les-tons-de-rédaction)
9. [Les garde-fous](#9-les-garde-fous)
10. [Modèles de prompts](#10-modèles-de-prompts)
11. [Dépannage](#11-dépannage)

---

## 1. L'essentiel en deux minutes

- **Une mission = un profil.** Tout ce qui est propre à un projet (où est le Jira, le Notion, le
  SharePoint, les dates, l'équipe, les partenaires) vit dans `profiles/<mission>/` du dossier projet.
  Le moteur (le plugin) ne change pas d'une mission à l'autre.
- **Des générateurs.** Chaque livrable a son générateur (`planning`, `plan`, `risks`, `raci`, `archi`…).
  Ils se lancent par `pm run <générateur> <mission>` ou, plus simplement, en le demandant à Claude.
- **Lecture seule par défaut.** Un générateur lit et rend un résultat (fichier local, aperçu, markdown).
  Toute écriture dans un système partagé (Jira, Notion, Office, GitHub Pages) passe par un flag explicite
  et **votre accord dans la conversation**.
- **Aucune notification ne part à cause de l'outil** : pas de mention, pas de partage, pas de mail envoyé.
  Les mails sont des **brouillons**, les messages Slack du **texte à copier**.
- **Une démo sans risque** : `/pm-framework:demo` joue tout sur un projet fictif sans rien écrire.

---

## 2. Installer et démarrer

### Installer (une fois) et mettre à jour

```bash
claude plugin marketplace add maximilienbornepro/pm-claude-plugin
claude plugin install pm-framework@pm-framework-market
claude plugin update pm-framework@pm-framework-market      # à chaque nouvelle version
```

Redémarrer Claude Code (ou l'app) après une mise à jour.

### Les commandes du plugin

| Commande | Ce qu'elle fait |
|---|---|
| `/pm-framework:list` | liste tous les générateurs et les missions disponibles |
| `/pm-framework:demo` | rejoue tout le framework sur un projet fictif, **sans aucune écriture** |
| `/pm-framework:run <générateur> <mission>` | lance un générateur (lecture seule / dry-run par défaut) |
| `/pm-framework:setup <mission>` | onboarding : détecte les champs manquants du profil, propose, écrit après accord |
| `/pm-framework:technical-planning <mission>` | produit ou met à jour le PPT de planning technique |

En ligne de commande, l'équivalent : `python3 framework/pm.py list | run | demo | missions`.

![pm list](img/cmd-list.png)

![pm demo : tout le framework sur un projet fictif, sans écriture](img/cmd-demo.png)

### Démarrer une nouvelle mission

1. Ouvrir Claude Code dans le dossier du projet.
2. Demander : *« Amorce une nouvelle mission "atlas" avec le pm-framework. »* (générateur `init` : crée
   `profiles/atlas/` depuis les gabarits, en dry-run puis après accord).
3. Demander : *« Lance le setup de la mission atlas. »* (`setup` liste ce qui manque : Jira, Notion,
   SharePoint, dates, équipe, et propose des valeurs).
4. Avant la première écriture : *« Vérifie qu'on est connecté aux bons systèmes. »* (`preflight`).

![Preflight : aucune écriture tant que les connecteurs ne sont pas renseignés](img/cmd-preflight.png)

Détail : [`docs/nouvelle-mission.md`](nouvelle-mission.md).

---

## 3. Comment on s'en sert : parler à Claude

On n'a pas besoin de connaître les commandes : on décrit le résultat voulu, Claude choisit le générateur,
le lance, **montre** ce qu'il propose, puis applique après accord.

Le cycle est toujours le même :

```
Vous demandez  ->  Claude lit les sources  ->  il propose (aperçu, avant / après, tableau)
               ->  vous validez (« ok », « ok sauf 3 », ou vous corrigez)  ->  il écrit, puis relit
```

Ce qui rend une demande efficace :

- **Nommer le livrable et la mission** : « le planning technique de la mission atlas ».
- **Dire ce qui change**, pas comment le faire : « le pentest est décalé au 08/12 ».
- **Donner la source** si elle est précise : un mail, un call, une transcription, un fichier.
- **Dire jusqu'où aller** : « propose d'abord », « applique directement », « ne publie pas ».

Exemples de demandes à la section [10](#10-modèles-de-prompts).

---

## 4. Catalogue

`[lecture]` = ne fait que lire et rendre ; `[écriture gardée]` = peut écrire, uniquement avec un flag
explicite et après accord.

### Pilotage et planning

| Générateur | Ce qu'il produit | Exemple de demande |
|---|---|---|
| `planning` `[lecture]` | **Planning technique** : Gantt PPTX, slide des échéances **calculée** depuis le Gantt (jamais désynchronisée), slides de situation (statut / levier), tableaux ; dans le **gabarit PowerPoint de l'entreprise** ; Gantt Excel en alternative | « Refais le planning technique au 02/12. » |
| `projection` `[lecture]` | Charge restante vs capacité de l'équipe → date de fin projetée | « À ce rythme, quand finit la V1 ? » |
| `plan` `[lecture]` | Page web « Avancement et sprints » : avancement V1, pôles, burn-down, plan de sprints, depuis Jira | « Régénère la page d'avancement. » |
| `gate` `[lecture]` | Score des 7 portes GTF et recommandation (le franchissement reste un acte humain) | « Où en est-on sur la gate 2 ? » |
| `cockpit` `[lecture]` | Porte d'entrée : où en est la mission et que faire ensuite (suite priorisée) | « Fais-moi le cockpit de la mission. » |
| `method` `[lecture]` | Montre la méthode de la mission (barèmes, seuils, trames, traçabilité) | « Rappelle-moi les barèmes des risques. » |
| `trace-audit` `[lecture]` | Ruptures de la chaîne besoin → ticket → POC → test, et où agir | « Quelles exigences n'ont pas de ticket ? » |
| `weekly-report` `[lecture]` | CR hebdo du projet depuis les prompts, mails et artefacts de la semaine | « Fais le weekly report de la semaine 47. » |

### Architecture

| Générateur / agent | Ce qu'il produit | Exemple de demande |
|---|---|---|
| `archi` + agent `archi-audit` | Schéma d'architecture **interactif** (HTML navigable, vues cliquables, thème clair / sombre, logos), contrôlé par un harness (7 invariants), export / import draw.io. **Pas d'éditeur graphique** : tout se fait en conversation | « Ajoute un flux du BFF vers Redis sur la vue Données. » |

### Jira

| Générateur / agent | Ce qu'il fait | Exemple de demande |
|---|---|---|
| `jira-sprints-audit` + agent `jira-sprints-audit` | Audit du plan de sprints vs le board : charge, estimations, blocages inversés | « Le plan de sprints est-il cohérent avec Jira ? » |
| `jira-changes-audit` + agent | Qui a modifié quels tickets, quand, quoi (repère les écrasements) | « Qu'est-ce qui a bougé dans le backlog depuis hier soir ? » |
| agent `jira-tickets-audit` | Détecte et répare les régressions de description (réparation après accord) | « Le ticket X n'est plus à jour, vérifie. » |
| `jira-images` `[écriture gardée]` | Images des tickets via l'API (contrôle ; pose avec `--apply`) | « Remets les maquettes dans les tickets du sprint. » |
| agent `front-audit` | Écarts POC ↔ tickets ↔ contrat d'API | « Qu'est-ce qui manque côté front ? » |

### Notion, suivi et communication

| Générateur / agent | Ce qu'il fait | Exemple de demande |
|---|---|---|
| `notion-topics-audit` + agent | Contrôle le format des sujets de suivi (Contexte / Action attendue) | « Relis les sujets modifiés cette semaine. » |
| `notion-scaffold` `[lecture]` | Arborescence Notion miroir : pages manquantes | « Quelles pages manquent dans l'espace projet ? » |
| `transcripts` `[lecture]` | Normalise transcriptions et CR (Notion, fichiers, pendentif Omi) | « Récupère la transcription du call de ce matin. » |
| `slack` `[lecture]` | Normalise les conversations Slack lues (canaux, DM, fils) ; jamais d'écriture | « Fais le point sur Slack depuis lundi. » |
| `omi-sync` `[écriture gardée]` | Pendentif Omi → Notion perso (classé pro / perso, fusionné par échange) | « Synchronise mes conversations Omi. » |
| `partner-report` `[lecture]` | Mail de suivi d'un call partenaire (texte, jamais envoyé) | « Fais le CR du weekly avec le partenaire A. » |
| `activity` `[lecture]` | Suivi d'activité : ce que vous avez fait avec Claude, vers une base Notion privée | « Résume mon activité de la semaine. » |

### Office et documents

| Générateur | Ce qu'il produit | Exemple de demande |
|---|---|---|
| `risks` `[écriture gardée]` | Registre des risques : revue proposée en formulaire, écriture chirurgicale du xlsx après accord | « Passe en revue les risques après le call d'hier. » |
| `raci` `[lecture]` | Matrice RACI + extraits par rôle | « Sors la RACI du rôle SRE. » |
| `deck-gate` `[lecture]` | Contenu d'un deck GATE (slides) | « Prépare le contenu du deck de la gate 2. » |
| `office` `[écriture gardée]` | Crée un xlsx depuis un template ou l'édite chirurgicalement (sans casser images et mises en forme) | « Crée le tracker de risques depuis le template. » |
| `docs-coherence-audit` `[lecture]` | Une sortie est-elle à jour par rapport à ses sources ? | « Le deck GATE est-il aligné sur les Excel ? » |
| `drive-scaffold` `[écriture gardée]` | Arborescence Drive / SharePoint : ce qui manque (création avec `--apply`) | « Vérifie l'arborescence du SharePoint projet. » |
| `templates` `[lecture]` | Registre des templates disponibles (sujets, planning, RACI, risques ; Notion / Excel) | « Quels templates ai-je pour le planning ? » |

### Mise en place et outillage

| Générateur | Ce qu'il fait |
|---|---|
| `init` | Amorce une mission depuis les gabarits (dry-run, `--apply` écrit) |
| `setup` | Champs manquants d'un profil et suggestions |
| `preflight` | Vérifie qu'on est connecté aux **bons** espaces (Notion, SharePoint, Jira) avant d'écrire |
| `tones` | Aligne le ton des agents sur la config de la mission |
| `agent` | Lance une sous-tâche sur un autre compte, modèle ou agent spécialisé |
| `poc` | POC React + Material UI depuis les récits (lanceur automatique) |
| `reset` | (test) remet à zéro un dossier de projet, sauvegarde obligatoire |

---

## 4 bis. Livrables et exports

Pour chaque livrable : la source, l'agent, le skill et le ton qui le produisent, le fichier de référence
auquel chaque slide renvoie, et ses formats. **Gras** = existe aujourd'hui ; *(proposé)* = prévu par
l'harmonisation (dossier projet HTML 16:9 et export PowerPoint, skill `slide-style`, ton `voice-slides`).
Chaque format renvoie à sa capture ou à la slide de la [maquette du dossier projet](maquette/index.html) ;
la version PowerPoint ([Atlas_dossier_projet.pptx](maquette/Atlas_dossier_projet.pptx)) sort de
`pm run dossier demo --build` ; retouchée à la main, `pm run dossier demo --sync` reporte les retouches dans
`dossier.json` et régénère le HTML.
Un livrable qui n'a de sens que dans Notion ou par mail le reste.

| Livrable | Source / générateur | Agent | Skill | Ton | Fichier rattaché | Exports |
|---|---|---|---|---|---|---|
| État des lieux (synthèse du comité) | cockpit, projection, suivi des sujets | `notion-topics-audit` | slide-style | voice-slides | Notion · suivi des sujets | [**Terminal**](img/cmd-cockpit.png) · [HTML *(proposé)*](maquette/index.html#etat-des-lieux) · [PPT *(proposé)*](maquette/index.html#etat-des-lieux) — Indicateurs du comité et sujets qui conditionnent la date. |
| Chantiers transverses | à créer : chantiers.yml (reflet du Project dashboard) | — | slide-style | voice-slides | Project_dashboard_<MISSION>.pptx · chantiers.yml | Notion *(proposé)* · [HTML *(proposé)*](maquette/index.html#chantiers) · [PPT *(proposé)*](maquette/index.html#chantiers) — barre d'avancement, statut en 4 couleurs, porteur, commentaire |
| Avancement V1 et burn-down du plan | plan, projection (Jira) | `jira-sprints-audit` | slide-style | voice-slides | page Avancement et sprints | [**HTML**](img/plan-avancement.png) · [PPT *(proposé)*](maquette/index.html#avancement) — La page web existe ; slides 16:9 à produire depuis le même JSON. |
| Tableau des états des tickets | plan (Jira) | `jira-sprints-audit` | slide-style | voice-slides | Jira | [HTML *(proposé)*](maquette/index.html#tableau-des-etats) · [PPT *(proposé)*](maquette/index.html#tableau-des-etats) — Nouveau : par pôle, à faire / en cours / en test / bloqué / fermé. |
| Sprint en cours et historique des sprints | plan (Jira), routine publish-projection (mode goals-only) | `jira-sprints-audit` | slide-style | voice-slides | Jira · plan.json | [**HTML**](img/plan-avancement.png) · [PPT *(proposé)*](maquette/index.html#sprint-en-cours) · **Jira** — Objectifs de sprint écrits dans Jira (champ texte). |
| Projection par pôle | projection (Jira), routine track-progress | — | slide-style | voice-slides | page Avancement et sprints | [**Terminal**](img/gate-slide1.png) · **Notion** · [HTML *(proposé)*](maquette/index.html#projection) · [PPT *(proposé)*](maquette/index.html#projection) — Notion : le seul pourcentage d'avancement V1. |
| Planning technique (Gantt, échéances) | planning (planning.json) | — | technical-planning, slide-style | voice-slides | Planning_<MISSION>.pptx, Gantt Excel | [**PPT**](img/planning-gantt.png) · **Excel** · [HTML *(proposé)*](maquette/index.html#planning) · **Notion** — Notion : vue timeline via notion-planning. |
| État des sujets (situation technique) | base Notion des sujets, routine review-topics | `notion-topics-audit` | technical-planning, slide-style | voice-maximilien (sujets), voice-slides (slide) | Notion · suivi des sujets (pas d'Excel) | [**Notion**](img/revue-sujets.png) · [**PPT**](img/planning-situation.png) · [HTML *(proposé)*](maquette/index.html#situation-technique) — La source reste Notion ; la slide de situation la reflète mot pour mot. |
| Suivi technique (météo des domaines) | base Notion des sujets | `notion-topics-audit` | slide-style | voice-slides | Notion · suivi des sujets | [HTML *(proposé)*](maquette/index.html#suivi-technique) · [PPT *(proposé)*](maquette/index.html#suivi-technique) — Nouveau : agrège les sujets par domaine. |
| Registre des risques | risks, office, routine review-risks | — | slide-style | voice-deliverable | Risks_<MISSION>.xlsx | [**Excel**](img/xlsx-risks.png) · **Notion** · [HTML *(proposé)*](maquette/index.html#risques) · [PPT *(proposé)*](maquette/index.html#registre-des-risques) — Excel = référence ; revue en séance : voir la capture revue-risques. |
| RACI | raci (raci.yml), office | — | slide-style | voice-deliverable | RACI_<MISSION>.xlsx (onglet par rôle) | [**Excel**](img/xlsx-raci.png) · **Notion** · [HTML *(proposé)*](maquette/index.html#raci) · [PPT *(proposé)*](maquette/index.html#raci) — Le lien vers l'Excel est toujours donné : l'onglet par rôle n'existe que là. |
| Responsabilités inter-équipes | à créer : schéma de dépendances (GATE 1) | — | slide-style | voice-slides | Dependances_inter-equipes_<MISSION>.drawio | [HTML *(proposé)*](maquette/index.html#responsabilites-inter-equipes) · [PPT *(proposé)*](maquette/index.html#responsabilites-inter-equipes) · draw.io *(proposé)* — Schéma de blocs et de flèches : qui doit quoi à qui, qui travaille avec qui. |
| Staffing par trimestre | à créer : plan de staffing | — | slide-style | voice-slides | Staffing_plan_<MISSION>.xlsx | Excel *(proposé)* · [HTML *(proposé)*](maquette/index.html#staffing) · [PPT *(proposé)*](maquette/index.html#staffing) — Une ligne par ressource, T1 / T2 / T3, trimestre en cours toujours présent. |
| Gate (checklist et deck) | gate, deck-gate (gate.yml) | — | slide-style | voice-deliverable | Notion · checklist de la gate | [**Terminal**](img/cmd-gate.png) · [PPT *(proposé)*](maquette/index.html#gate-2) · [HTML *(proposé)*](maquette/index.html#gate-2) — Le contenu du deck existe ; l'assemblage PPTX est encore manuel. |
| Matrice de traçabilité | traceability, trace-audit | — | — | voice-deliverable | traceability.xlsx | [**Terminal**](img/cmd-trace.png) · **Excel** · **Notion** — Registre long : extrait en slide si besoin. |
| Weekly report | weekly-report | — | slide-style | voice-maximilien | Notion · page de suivi · weekly-reports/<AAAA-Www>.md | [**Markdown**](img/weekly-report.png) · **Notion** · [HTML *(proposé)*](maquette/index.html#weekly-report) · [PPT *(proposé)*](maquette/index.html#weekly-report-2) — Bloc de la page Notion de suivi ; la slide le reflète à l'identique. |
| Compte rendu partenaire | partner-report | — | slide-style | voice-maximilien (FR ou EN selon le partenaire) | Notion · page du partenaire | [**Mail**](img/cr-partenaire.png) · [HTML *(proposé)*](maquette/index.html#compte-rendu-partenaire) · [PPT *(proposé)*](maquette/index.html#compte-rendu-partenaire) — Rendu texte, jamais envoyé ; brouillon Outlook sur demande. |
| Ordre du jour | meeting-agenda | — | slide-style | voice-maximilien | Notion · page de la réunion | [**Conversation**](img/agenda.png) · [HTML *(proposé)*](maquette/index.html#ordre-du-jour) · [PPT *(proposé)*](maquette/index.html#ordre-du-jour) |
| Relances | routine draft-followups | — | — | voice-maximilien | fichiers .eml locaux | **Mail (.eml)** · **Slack** — Pas de slide : sans objet. |
| Morning digest | routine morning-digest | — | — | voice-casual | canal Slack dédié | **Slack** — Pas de slide : sans objet. |
| Schéma d'architecture | archi (model.json) | `archi-audit` | voice-adservio (schéma), slide-style | voice-adservio | architecture_<MISSION>.html, vues .drawio | [**HTML**](img/archi-showcase.png) · [HTML dossier *(proposé)*](maquette/architecture.html) · **draw.io** · [PPT *(proposé)*](maquette/index.html#architecture) — PPT : la vue macro seulement, avec un lien vers le HTML et ses sous-vues |
| Note de fond, dossier | — | `adservio-writer` | voice-adservio | voice-adservio | fichier HTML autonome | **HTML** · Notion *(proposé)* |
| Chapitres d'un livrable contractuel | sources du projet | `doc-writer` | — | voice-deliverable | document du livrable | **Document Office** — Plan qualité, dossier contractuel. |

---

## 5. Guides pas à pas

### 5.1 Le planning technique (PPT)

Un deck de comité **tout calculé depuis une seule source** (`profiles/<mission>/planning.json`), dans le
gabarit PowerPoint de l'entreprise.

**1. Le Gantt** : couloirs par équipe ou partenaire, barres, jalons, traits verticaux (aujourd'hui,
signature, ouverture).

![Gantt](img/planning-gantt.png)

**2. Les échéances** : calculées depuis le Gantt, élément par élément. Elles ne peuvent pas diverger.

![Échéances](img/planning-echeances.png)

**3. La situation** : Domaine / Sujet / Statut / Situation / Levier en cours / Échéance. Les lignes
viennent du suivi des sujets ; le titre de chaque slide dit **le message clé**.

![Situation](img/planning-situation.png)

**4. Les tableaux** : responsabilités et charge, RACI résumée…

![Tableau](img/planning-tableau.png)

**Comment faire**

1. *« Refais le planning technique de la mission atlas au 02/12 à partir des sujets. »*
2. Claude relit `planning.json`, la version en ligne du deck et les sujets modifiés, met à jour la
   source, génère le deck et vous montre les aperçus et ce qui a changé (**toute date qui bouge est
   signalée**).
3. Vous validez ; il dépose le deck (une seule écriture, ou report en ligne si quelqu'un a modifié le
   fichier entre-temps).

**Dans le gabarit de l'entreprise** : déposer n'importe quel PPT de l'entreprise dans
`profiles/<mission>/templates/` et déclarer dans `planning.json` :
`"template": {"pptx": "templates/gabarit.pptx", "layout": "Titre seul"}`. Le titre de chaque slide va
dans l'emplacement titre de la mise en page (logo, police, pied de page de l'entreprise), le contenu est
recalé dans la zone utile.

Skill complet : `/pm-framework:technical-planning` (`framework/skills/technical-planning/SKILL.md`).

### 5.2 La page d'avancement et le plan de sprints

Une page web publiée (GitHub Pages) qui répond à : **la V1 tient-elle la date, à capacité réelle ?**
Jalons, avancement V1 et par pôle, burn-down, plan de sprints avec charge par pôle, burn-down par sprint.

![Avancement et sprints](img/plan-avancement.png)

**Comment faire**

- *« Régénère la page d'avancement et montre-moi ce qui a bougé depuis la dernière publication. »*
- *« Le ticket X passe au sprint 5 : déplace-le et réécris le texte des sprints concernés. »*
- *« Publie la page. »* (après relecture locale)

Règle : la page suit Jira pour les tickets, **pas pour le texte** : tout déplacement de tickets
s'accompagne de la réécriture du texte des sprints, dans le même passage.

Contrat de données et design réutilisable : `framework/generators/plan/` (`CONTRACT.md`,
`plan_design.tmpl.html`, `render.py --example`).

### 5.3 Le schéma d'architecture interactif

Un HTML unique, navigable (une vue par zone, loupe pour entrer dans le détail, fil d'Ariane), thémable,
avec les logos des technos et des partenaires.

![Schéma d'architecture](img/archi-showcase.png)

**Comment faire** : tout passe par la conversation, **il n'y a pas d'éditeur graphique** (aucun
déplacement de bloc à la souris, aucun bouton d'import).

- *« Sur la vue Données, ajoute un flux du service d'alertes vers Redis, libellé "cache". »*
- *« Déplace le bloc Keycloak sous le BFF et aligne-le à gauche. »*
- *« Remplace le logo de Keycloak par celui-ci. »* (joindre l'image)
- *« Importe ce draw.io comme nouvelle vue "Exploitation". »*
- *« Vérifie le schéma et publie-le. »*

Après chaque modification, Claude passe le **harness** (7 invariants : SVG équilibré, flèches droites,
marqueurs résolus, couleurs déclarées, navigation cohérente, logos résolus, viewBox) avant de proposer la
publication. Démarrage d'un schéma : depuis une description en langage naturel, un draw.io ou un modèle
existant (agent `archi-audit`). Un exemple plus simple, au rendu de départ :

![Vue d'ensemble de démo](img/archi-vue-ensemble.png)

### 5.4 Les gates, le cockpit et la méthode

![Cockpit](img/cmd-cockpit.png)

![Portes (gates)](img/cmd-gate.png)

![Traçabilité](img/cmd-trace.png)

![Contenu du deck GATE](img/deck-gate.png)

![Méthode de la mission](img/cmd-method.png)

- *« Fais-moi le cockpit de la mission. »*
- *« Prépare la checklist de la gate 2 avec ce qui est couvert, partiel ou à faire. »*

Le générateur **recommande** ; le franchissement d'une porte reste un acte humain tracé.

### 5.5 Le suivi des sujets, les CR et les relances

- **Revue des sujets** : *« Récupère les derniers mails et messages Slack et mets à jour les sujets. »*
  Claude lit mails, Slack (lecture seule), transcriptions ; propose un bloc par sujet (statut, actions
  faites barrées, nouvelles actions) ; écrit après votre « ok tout » / « ok sauf 3 », puis relit.
- **CR partenaire** : *« Fais le CR du weekly avec le partenaire A. »* (texte prêt à envoyer, une
  ligne de situation et une prochaine étape datée par sujet, dans la langue du partenaire).
- **Relances** : *« Prépare les relances de la semaine. »* (brouillons de mail non envoyés, messages
  Slack à copier).

![Revue des sujets dans la conversation](img/revue-sujets.png)

![CR de call partenaire](img/cr-partenaire.png)

![Agenda de réunion](img/agenda.png)

### 5.6 Les risques et la RACI

- *« Passe en revue le registre des risques à partir des sujets qui ont bougé. »* : propositions en
  formulaire (probabilité, impact avant → après, justification), puis écriture chirurgicale du xlsx
  après accord (sauvegarde, contrôle de fraîcheur, une seule écriture).
- *« Sors la RACI du rôle SRE. »*

![Revue des risques](img/revue-risques.png)

![Matrice RACI](img/raci.png)

### 5.7 Les transcriptions et le weekly report

- *« Récupère la transcription du call de ce matin et reporte les décisions dans les sujets. »*
- *« Synchronise mes conversations Omi. »* (pendentif Omi : classement pro / perso, fusion des
  morceaux d'un même échange, import dans le Notion **perso**).
- *« Fais le weekly report de la semaine 47. »* (depuis prompts, mails et artefacts ; couverture de
  chaque thème contrôlée).

---

## Galerie : ce que génère chaque outil

Toutes les captures viennent du projet fictif livré avec le plugin. Dans le guide web ([index.html](index.html)), chaque ligne du catalogue a un bouton « Voir le rendu ».

**Planning : le Gantt (couloirs, barres, jalons, traits aujourd'hui et ouverture).**

![Planning : le Gantt (couloirs, barres, jalons, traits aujourd'hui et ouverture).](img/planning-gantt.png)

**Planning : les échéances, calculées depuis le Gantt.**

![Planning : les échéances, calculées depuis le Gantt.](img/planning-echeances.png)

**Situation technique : état des lieux de chaque sujet (statut, situation, levier, échéance).**

![Situation technique : état des lieux de chaque sujet (statut, situation, levier, échéance).](img/planning-situation.png)

**Planning : tableau des responsabilités.**

![Planning : tableau des responsabilités.](img/planning-tableau.png)

**Page web Avancement et sprints : jalons, avancement V1 par pôle, burn-down, plan de sprints.**

![Page web Avancement et sprints : jalons, avancement V1 par pôle, burn-down, plan de sprints.](img/plan-avancement.png)

**Deck GATE : avancement V1, burn-down et projection de fin.**

![Deck GATE : avancement V1, burn-down et projection de fin.](img/gate-slide1.png)

**Deck GATE : couverture des exigences.**

![Deck GATE : couverture des exigences.](img/gate-slide2.png)

**Deck GATE : checklist de la porte.**

![Deck GATE : checklist de la porte.](img/gate-slide3.png)

**Deck GATE : risques et leviers.**

![Deck GATE : risques et leviers.](img/gate-slide4.png)

**deck-gate : le contenu des slides généré depuis le profil (avant assemblage).**

![deck-gate : le contenu des slides généré depuis le profil (avant assemblage).](img/deck-gate.png)

**Schéma d'architecture interactif : vue d'ensemble avec logos.**

![Schéma d'architecture interactif : vue d'ensemble avec logos.](img/archi-showcase.png)

**Schéma d'architecture : couches techniques repliées en blocs cliquables.**

![Schéma d'architecture : couches techniques repliées en blocs cliquables.](img/archi-vue-ensemble.png)

**Registre des risques créé par office (contenu du classeur).**

![Registre des risques créé par office (contenu du classeur).](img/xlsx-risks.png)

**Revue des risques proposée dans la conversation (exemple fictif).**

![Revue des risques proposée dans la conversation (exemple fictif).](img/revue-risques.png)

**RACI créée par office depuis le gabarit Excel (contenu du classeur).**

![RACI Excel](img/xlsx-raci.png)

**Matrice RACI et extrait par rôle.**

![Matrice RACI et extrait par rôle.](img/raci.png)

**CR de call partenaire en français (rendu texte, jamais envoyé).**

![CR de call partenaire en français (rendu texte, jamais envoyé).](img/cr-partenaire.png)

**CR de call partenaire en anglais.**

![CR de call partenaire en anglais.](img/cr-partenaire-en.png)

**Agenda de réunion (exemple fictif).**

![Agenda de réunion (exemple fictif).](img/agenda.png)

**Weekly report rédigé depuis la matière de la semaine (exemple fictif).**

![Weekly report rédigé depuis la matière de la semaine (exemple fictif).](img/weekly-report.png)

**Revue des sujets proposée dans la conversation (exemple fictif).**

![Revue des sujets proposée dans la conversation (exemple fictif).](img/revue-sujets.png)

**notion-topics-audit : défauts de format d'un sujet avant écriture.**

![notion-topics-audit : défauts de format d'un sujet avant écriture.](img/cmd-topics.png)

**cockpit : état de la mission et prochaines actions.**

![cockpit : état de la mission et prochaines actions.](img/cmd-cockpit.png)

**gate : score des 7 portes et alertes.**

![gate : score des 7 portes et alertes.](img/cmd-gate.png)

**trace-audit : exigences en rupture et qui doit agir.**

![trace-audit : exigences en rupture et qui doit agir.](img/cmd-trace.png)

**method : barèmes, seuils, trames, traçabilité.**

![method : barèmes, seuils, trames, traçabilité.](img/cmd-method.png)

**preflight : aucune écriture tant que les connecteurs ne sont pas vérifiés.**

![preflight : aucune écriture tant que les connecteurs ne sont pas vérifiés.](img/cmd-preflight.png)

**templates : registre objet × solution.**

![templates : registre objet × solution.](img/cmd-templates.png)

**init : amorcer une mission depuis les gabarits.**

![init : amorcer une mission depuis les gabarits.](img/cmd-init.png)

**notion-scaffold : arborescence Notion attendue.**

![notion-scaffold : arborescence Notion attendue.](img/cmd-notion-scaffold.png)

**drive-scaffold : dossiers et fichiers attendus.**

![drive-scaffold : dossiers et fichiers attendus.](img/cmd-drive-scaffold.png)

**tones : ton de chaque agent.**

![tones : ton de chaque agent.](img/cmd-tones.png)

**setup : champs manquants du profil, avec une suggestion pour chacun.**

![setup](img/cmd-setup.png)

**pm list : tous les générateurs.**

![pm list : tous les générateurs.](img/cmd-list.png)

**pm demo : le framework rejoué sur un projet fictif.**

![pm demo : le framework rejoué sur un projet fictif.](img/cmd-demo.png)

---

## 6. Les routines

Des tâches planifiées qui rejouent un générateur à heure fixe, définies une fois dans le plugin
(`framework/routines/<nom>/SKILL.md`) et paramétrées par mission (`profiles/<mission>/routines.yml`).
Aucune n'envoie de notification à l'équipe.

| Routine | Ce qu'elle fait | Écrit (après garde) |
|---|---|---|
| `publish-projection` | publie la page d'avancement (et l'avancement par exigence), aligne les objectifs des sprints, alerte si un texte de sprint est périmé ; mode `goals-only` : objectifs seuls | gh-pages, artefacts, objectifs de sprint Jira |
| `align-sprint-goals` | dépréciée : renvoie vers `publish-projection`, mode `goals-only` | objectifs de sprint Jira |
| `audit-scope` | audite périmètre, couverture des exigences et plan de sprints | rien (lecture seule) |
| `track-progress` | reporte l'avancement dans le planning Notion | un champ Notion |
| `collect-activity` | suivi d'activité du jour vers une base Notion privée | store local, DB Notion privée |
| `review-topics` | revue des sujets depuis transcriptions, mails et Slack, puis enchaîne `review-risks` | base de suivi, page de synthèse, deck (après oui) |
| `review-risks` | revue du registre des risques | registre Office (après oui) |
| `draft-followups` | brouillons de relances (mails non envoyés, messages à copier) | `.eml` locaux, fenêtre de rédaction |
| `morning-digest` | récap du matin des sujets ouverts dans un canal privé | un canal Slack privé |
| `omi-sync` | synchro du pendentif Omi vers Notion perso (toutes les 5 min, hors mission) | bases Notion perso |

Le nom de la routine est celui de son dossier ; l'instance de mission s'appelle `<projet>-<nom>` (ex.
`atlas-publish-projection`) dans `profiles/<mission>/routines.yml` et dans l'app. Toute routine qui écrit
commence par le préflight des connecteurs ; aucune n'envoie de notification.

Activer : *« Enregistre les routines de la mission atlas selon leur planning. »* Première exécution :
approuver une fois les permissions demandées (« Always allow »), sinon la tâche reste bloquée.

---

## 7. Les agents

Des sous-agents spécialisés, appelés par Claude quand une tâche le justifie.

| Agent | Ce qu'il fait |
|---|---|
| `archi-audit` | monte et fait évoluer le schéma d'architecture (modèle, rendu, harness, draw.io) |
| `jira-sprints-audit` | audit du plan de sprints vs le board (lecture seule) |
| `jira-changes-audit` | qui a modifié quels tickets, quand, quoi (lecture seule) |
| `jira-tickets-audit` | régressions de description ; réparation après accord |
| `front-audit` | écarts POC ↔ tickets ↔ contrat d'API (lecture seule) |
| `notion-topics-audit` | relit beaucoup de sujets d'un coup, mot pour mot (lecture seule) |
| `doc-writer` | rédige les chapitres d'un livrable (plan qualité…) chapitre par chapitre |
| `adservio-writer` | note de fond / dossier à la charte éditoriale Adservio |

---

## 8. Les tons de rédaction

| Ton | Pour quoi |
|---|---|
| `voice-deliverable` | livrables, tickets, pages de référence : sobre, factuel |
| `voice-maximilien` | sujets de suivi, CR, messages signés par la personne (sa voix) |
| `voice-casual` | échanges informels, messages courts |
| `voice-adservio` | notes de fond, dossiers, decks à la charte Adservio |
| `voice-slides` | slides du dossier projet : titre court, légende qui explique la slide, en jours |

*« Écris ce mail dans le ton voice-casual. »* Le ton par défaut de chaque agent se règle dans
`profiles/<mission>/pipeline.yml`.

---

## 9. Les garde-fous

- **Rien n'est écrit sans validation** (Jira, Notion, SharePoint / OneDrive, Teams, mails) : Claude
  montre le contenu exact ou un aperçu avant d'appliquer.
- **Aucune notification** : pas de mention, pas de partage, pas d'invitation ; mails en brouillon,
  Slack en lecture seule (jamais de saisie dans une zone de message).
- **Office** : jamais d'écriture dans un fichier modifié récemment par quelqu'un d'autre (contrôle de la
  date en ligne) ; une sauvegarde, puis **une seule écriture** par fichier ; écriture chirurgicale des
  xlsx (sans détruire images et dessins) ; contrôle de la taille en ligne après synchronisation.
- **Jira** : relecture juste avant toute écriture de description, refus si elle a changé ; une image
  vérifiée après chaque modification de ticket.
- **Modification en masse** : toujours un élément d'essai d'abord, montré et validé, puis le reste.
- **Secrets** : jetons dans des fichiers locaux hors dépôt, jamais affichés ni committés.
- **Ne rien inventer** : un inconnu s'écrit « à confirmer ».

---

## 10. Modèles de prompts

**Lire et faire le point**

- « Fais-moi un état des lieux du projet : sujets critiques, ce qui a bougé, ce qui est bloqué. »
- « Récupère les discussions Slack depuis lundi et dis-moi si les tests de charge ont été faits. »
- « Qui a modifié les tickets du sprint depuis ce matin ? »

**Mettre à jour (proposer d'abord)**

- « Mets à jour les sujets à partir des derniers mails et de Slack. Propose avant d'écrire. »
- « Le partenaire A a livré son plan de test : mets à jour le sujet et la slide de situation. »
- « Décale la mise en production au 18/12 dans le planning, et montre-moi ce que ça change. »

**Produire un livrable**

- « Refais le planning technique au 02/12 dans le gabarit de l'entreprise. »
- « Génère quatre slides pour la gate : exigences, avancement V1, avancement par exigence, checklist. »
- « Fais le CR du weekly avec le partenaire B, en anglais. »
- « Rédige une page de documentation sur la livraison des images. »

**Modifier un rendu**

- « Sur la slide de situation, remplace le titre par le message clé. »
- « Dans le schéma d'archi, ajoute le logo de Redis à côté du cache. »
- « Rends la slide plus lisible : phrases courtes, pas de chiffres sans explication. »

**Contrôler avant de publier**

- « Vérifie que le schéma passe le harness et publie-le. »
- « Le Gantt et la slide des échéances sont-ils cohérents ? »
- « Relis le deck en ligne : quelqu'un l'a-t-il modifié depuis ma dernière version ? »

---

## 11. Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| Une routine reste « en attente » | permissions jamais approuvées : l'ouvrir, « Run now », puis « Always allow » |
| Une commande du plugin est inconnue | redémarrer Claude Code après `claude plugin update` |
| Le deck planning déborde | une slide de situation a trop de lignes : la scinder (le contrôle le signale) |
| « Mise en page absente du gabarit » | le message liste les mises en page disponibles : reprendre le nom exact |
| Une page publiée ne change pas | GitHub Pages met 1 à 2 minutes ; recharger sans cache (Cmd+Maj+R) |
| Un fichier Office ne se synchronise pas | ne pas le réécrire plusieurs fois ; comparer la taille locale et en ligne, attendre la synchro |
| Slack non lu | l'extension Chrome doit être connectée dans le profil où Slack est ouvert |
