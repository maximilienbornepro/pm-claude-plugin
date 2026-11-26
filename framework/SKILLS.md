# Catalogue du plugin, par département

Généré depuis `framework/organisation.yml` (`python3 framework/lib/organisation.py --catalogue`) : ne pas
éditer à la main. Le plugin s'organise comme un PMO aligné sur le fonctionnement réel de Claude Code
(voir `framework/ORGANISATION.md`) : Claude principal est le chef de projet ; les skills sont des
classeurs qu'il suit, les générateurs des machines qu'il lance, les sous-agents les seuls vrais collègues.

## Direction de projet - Chef de projet

Cadrer la demande, préparer la mission, vérifier les connexions, décider des gates.

| Composant | Type | Ce qu'il fait |
|---|---|---|
| `setup` | Classeur | Onboarding guidé d'un profil de mission - détecte les champs manquants, propose des valeurs, puis écrit après validation. |
| `list` | Classeur | Liste les générateurs du pm-framework et les missions (profils) du projet courant. |
| `run` | Classeur | Lance un générateur du pm-framework sur une mission (lecture seule / dry-run par défaut). |
| `demo` | Classeur | Lance le faux projet et simule toutes les fonctionnalités du framework (aucune écriture). |
| `setup` | Machine | onboarding : champs manquants d'un profil + suggestions (lecture seule) |
| `init` | Machine | amorce une mission : cree le profil depuis les gabarits (create-si-absent ; dry-run, --apply ecrit) |
| `preflight` | Machine | verifie qu'on est connecte aux BONS systemes (Notion/SharePoint/Jira) avant d'ecrire |
| `cockpit` | Machine | porte d'entree : ou en est la mission, que fait-on ? (etat calcule + suite priorisee) |
| `method` | Machine | montre la methode de la mission en donnee (baremes, seuils, trames, tracabilite) |
| `gate` | Machine | score les portes (gates) d'une mission et RECOMMANDE ; franchissement = acte humain |
| `templates` | Machine | registre des templates (objet x solution : sujets/planning/raci/risks, notion/excel) |
| `agent` | Machine | lance une sous-tache sur un agent : --account (connecteurs) / --model / --agent (specialite) |
| `drive-scaffold` | Machine | arbo Drive : ce qui manque (--apply cree les dossiers) |
| `notion-scaffold` | Machine | arbo Notion miroir : pages manquantes (--emit-plan) |
| `console` | Machine | consoles de gestion en direct sur localhost : plugin (/) et projet (/projet) ; lecture seule |
| `reset` | Machine | TEST : remet a zero un dossier de projet (backup oblige ; dry-run ; --apply supprime) |

## Planification - PMO planning

Planning, plan de sprints, projection de fin, objectifs de sprint.

| Composant | Type | Ce qu'il fait |
|---|---|---|
| `jira-sprints-audit` | Collègue | Audit en lecture seule du plan de sprints contre le board du tracker. |
| `technical-planning` | Classeur | Produire ou mettre à jour le PPT « Technical planning » d'une mission (Gantt, slide des échéances toujours synchronisée, slides de situation Sujet / Statut / Situation / Levier / Échéance, tableau des responsabilités) dans le gabarit PowerPoint de l'entreprise, à partir d'une seule source de données (planning.json) alimentée par le suivi des sujets. |
| `planning` | Machine | planning technique : Gantt PPTX + slide echeances derivee (sync) + situation (statut/levier) + tableaux ; Gantt Excel en alternative |
| `plan` | Machine | plan de sprints (page « Avancement et sprints ») depuis Jira, config-driven ; design reutilisable (template + contrat + render + validate) |
| `projection` | Machine | charge restante vs capacite -> date de fin V1 |
| `jira-sprints-audit` | Machine | audit des sprints Jira (charge, estimations, blocages) |
| `notion-planning` | Machine | Construit et tient a jour le planning de reference de la mission - une PAGE NOTION avec un GANTT (vue timeline), pas un Excel. |
| `publish-projection` | Chef de garde | Publie les pages d'avancement (gh-pages) puis le même HTML sur les artefacts Claude, aligne les objectifs des sprints du tracker sur le JSON éditorial, et signale tout texte de sprint périmé ; mode goals-only pour n'aligner que les objectifs. |
| `align-sprint-goals` | Chef de garde | Dépréciée - pointeur vers publish-projection en mode goals-only (aligne les objectifs des sprints Jira sur le JSON éditorial, aucun ticket déplacé). |
| `track-progress` | Chef de garde | Pousse l'avancement V1 (un seul nombre, lu dans la projection) dans un seul champ d'une seule page du tracker Notion. |
| `audit-scope` | Chef de garde | Audite le périmètre V1/V2 et la couverture des exigences contre Jira, et la cohérence du plan de sprints ; ne fait que proposer, cellule par cellule. |

## Suivi et gouvernance - Responsable du suivi

Sujets, risques, RACI, traçabilité, cohérence des documents.

| Composant | Type | Ce qu'il fait |
|---|---|---|
| `notion-topics-audit` | Collègue | Lecture seule des pages de la base de suivi (Notion) pour préparer une revue des sujets. |
| `risks` | Machine | registre des risques (lecture ; ecriture gardee) |
| `raci` | Machine | matrice RACI + extraits par role (depuis raci.yml) |
| `traceability` | Machine | matrice de couverture IADT pre-remplie (xlsx a listes deroulantes, ou schema Notion) depuis un backlog/des exigences |
| `trace-audit` | Machine | ruptures de la chaine de tracabilite (besoin->ticket->POC->test) ; dit ou aller (lecture seule) |
| `docs-coherence-audit` | Machine | coherence docs : une sortie est-elle a jour vs ses sources |
| `notion-topics-audit` | Machine | valide le FORMAT d'un sujet Notion (--body ; lecture seule) |
| `review-topics` | Chef de garde | Passe en revue les sujets du tracker de suivi à partir des transcriptions, mails et Slack, propose dans la conversation, applique ce qui est validé, aligne les supports dépendants, puis enchaîne sur la revue des risques ; mode condensation pour les sujets à rallonge. |
| `review-risks` | Chef de garde | Relit chaque registre de risques, le confronte aux sujets de suivi et à la projection de livrabilité, montre le registre actualisé, puis met à jour le fichier en place après validation en séance. |

## Qualité du backlog - Responsable qualité

Tickets propres et à jour, écarts maquette / tickets / contrat d'API.

| Composant | Type | Ce qu'il fait |
|---|---|---|
| `jira-changes-audit` | Collègue | Dit qui a modifié quels tickets du tracker, quand et quoi, sur une fenêtre de temps (depuis ce matin, depuis hier soir, depuis une heure donnée). |
| `jira-tickets-audit` | Collègue | Détecte et répare les régressions de description des tickets du tracker - un brouillon périmé enregistré par-dessus la version à jour, qui fait reculer un ticket de plusieurs jours (symptôme fréquent : l'image du ticket n'est plus la bonne). |
| `front-audit` | Collègue | Audit en lecture seule du front d'une mission. |
| `jira-changes-audit` | Machine | qui a modifie quels tickets, quand, quoi (sections perdues) |
| `jira-images` | Machine | images des tickets Jira via API (check ; --apply garde) |

## Communication - Chargé de communication

Comptes rendus, weekly, ordres du jour, relances, transcriptions.

| Composant | Type | Ce qu'il fait |
|---|---|---|
| `partner-report` | Machine | mail de suivi d'un call partenaire (--input ; rendu texte, jamais d'envoi) |
| `weekly-report` | Machine | CR hebdo du projet (par semaine, archive) depuis les prompts + mails + artefacts ; demande la semaine |
| `meeting-agenda` | Machine | Prépare l'agenda d'une réunion (weekly partenaire, kick-off, atelier technique, point interne) - 4 à 6 points numérotés, 2 ou 3 sous-points de 10 mots maximum, rien de plus. |
| `activity` | Machine | suivi d'activite : collect / check / weekly / sync (dry-run) |
| `transcripts` | Machine | normalise transcriptions/CR vers {date,title,url,text} (--dump|--files) |
| `slack` | Machine | normalise un export Slack (canaux+DM, threads) vers {date,author,channel,thread,text,url} ; lecture via Claude in Chrome, jamais d'ecriture |
| `omi-sync` | Machine | pendentif Omi -> Notion perso : --fetch / --import (classes, fusionnes) ; --unlock complete les pages verrouillees |
| `draft-followups` | Chef de garde | Prépare les relances pour obtenir les réponses attendues sur les sujets de suivi : brouillon de mail pour un partenaire externe (.eml local non envoyé, ouvert en rédaction), message Slack à copier pour un interne ; formulaire modifiable au clic. |
| `morning-digest` | Chef de garde | Chaque matin, poste dans UN canal Slack dédié (et lui seul) le récap exhaustif des sujets à faire avancer, à partir du tracker de suivi, des sources de la veille et de l'agenda du jour. |
| `collect-activity` | Chef de garde | Transforme les requêtes Claude Code du jour qui ont modifié le projet en activités datées, versées dans un store local et une DB Notion privée, et résumables en bloc Weekly report. |
| `omi-sync` | Chef de garde | Rapatrie les nouvelles conversations du pendentif Omi dans le Notion perso, classées pro / perso et fusionnées par échange (générateur omi-sync). |

## Studio - Designer

Mettre en forme les livrables (dossier projet, deck, architecture, documents, POC).

| Composant | Type | Ce qu'il fait |
|---|---|---|
| `archi-audit` | Collègue | Monte un schéma d'architecture interactif (stack-imagery, model-first) à partir d'une description en langage naturel OU d'un modèle existant. |
| `doc-writer` | Collègue | Rédige les chapitres d'un livrable structuré (plan qualité, dossier contractuel...) dont l'utilisateur est Content Owner ou relecteur, à partir des sources du projet. |
| `adservio-writer` | Collègue | Produit un document ou un schéma complet à la charte éditoriale Adservio (style soigné du dossier de référence). |
| `dossier` | Machine | dossier projet 16:9 (charte slide-style) : --build json -> PPTX editable + HTML ; --sync PPTX retouche -> json -> HTML (garde-fou anti-ecrasement) |
| `deck-gate` | Machine | contenu du deck GATE (slides markdown/JSON ; assemblage pptx garde) |
| `archi` | Machine | harness du schema d'archi (validate, lecture seule) |
| `poc` | Machine | POC React + Material UI depuis les recits (launcher auto) |
| `office` | Machine | cree un xlsx depuis un template excel si absent, l'edite chirurgicalement si present (OneDrive) |

## Charte et tons (transverse)

La forme de tous les livrables (slides, tons de rédaction).

| Composant | Type | Ce qu'il fait |
|---|---|---|
| `slide-style` | Classeur | Charte de TOUS les livrables du pm-framework rendus en slides 16:9 (HTML du dossier projet et export PPTX) - titres courts, légende explicative sous chaque titre, unités en jours, style noir / ivoire à aplats, logo du client. |
| `voice-slides` | Classeur | Ton des slides du dossier projet (HTML 16:9 et PPTX) - titres courts sans verbe, légende explicative en prose posée dans le ton du CR partenaire, unités en jours. |
| `voice-deliverable` | Classeur | Style rédactionnel des livrables SINBAD — écriture simple, claire, en prose, reprenant la terminologie du projet, comme la spécification, les one-pagers et l'onglet Terminologie. |
| `voice-maximilien` | Classeur | Écrire à la voix de Maximilien Borne (TEM / TPM SINBAD) : mails, messages Slack et Teams, commentaires Jira, comptes rendus, notes d'annonce, tout ce qu'il signe lui-même. |
| `voice-casual` | Classeur | Ton décontracté "jeune adulte" à employer quand on demande d'écrire un contenu (fichier, commentaire, message) dans ce ton — minuscule en début de phrase, phrases courtes, familier et chaleureux, petites libertés de langue. |
| `voice-adservio` | Classeur | Profil de rédaction ET de schématisation à la charte éditoriale Adservio, dérivé du dossier de fond "AI-DLC" (reference/rapport-aidlc.html). |
| `tones` | Machine | aligne le ton des agents sur pipeline.yml (dry-run) |

## Renforts (agents génériques de Claude Code)

Agents génériques de Claude Code ; ils vont travailler dans le département qui les appelle.

`Explore`, `general-purpose`, `Plan`, `claude-code-guide`, `web-fetch`

## Garde-fous (hooks)

| Hook | Contrôle | Peut bloquer |
|---|---|---|
| `garde_office` | écriture d'un fichier Office synchronisé (OneDrive, SharePoint) | oui |
| `garde_suppression` | suppression ou déplacement dans un Drive synchronisé, déplacement de page Notion | oui |
| `pas_ecraser_jira` | écrasement d'une description de ticket Jira modifiée entre-temps | oui |
| `archi_kit` | kit du générateur d'architecture tenu à jour après modification | non |
| `onboarding_hint` | rappel du profil à compléter à l'ouverture de session | non |
| `journal_usage` | journal des skills et agents appelés (.claude/usage.log) | non |
| `journal_activite` | journal de chaque action pour l'écran agence (.claude/activity.log) | non |

## Services partagés (connecteurs)

Atlassian (Jira, Confluence), Notion, Omi, Slack, Microsoft 365, Google Drive, Figma, Navigateur, Visualisation, Tâches planifiées, App Claude.
