# Catalogue des skills du framework

Index unique de **tous** les composants du framework : générateurs, skills (tons et chartes), routines,
agents. Le détail vit dans le `SKILL.md` (ou la fiche d'agent) de chaque composant ; cette page sert
d'annuaire. Les noms sont les noms canoniques : ceux de `python3 framework/pm.py list` et des dossiers.

Catalogues liés : tons -> `framework/REDACTION.md` · agents -> `framework/AGENTS.md` · routines ->
`framework/routines/README.md` · livrables et exports -> `docs/GUIDE.md` §4 bis · partenaires ->
`profiles/<mission>/partenaires.yml`.

## Générateurs (`framework/generators/`, `pm run <nom> <mission>`)

| Commande | Ce qu'elle fait | Écriture |
|---|---|---|
| `projection` | charge restante vs capacite -> date de fin V1 | lecture seule |
| `plan` | plan de sprints (page « Avancement et sprints ») depuis Jira, config-driven ; design reutilisable (template + contrat + render + validate) | lecture seule |
| `risks` | registre des risques (lecture ; ecriture gardee) | lecture seule |
| `raci` | matrice RACI + extraits par role (depuis raci.yml) | lecture seule |
| `poc` | POC React + Material UI depuis les recits (launcher auto) | écriture gardée |
| `archi` | harness du schema d'archi (validate, lecture seule) | lecture seule |
| `activity` | suivi d'activite : collect / check / weekly / sync (dry-run) | lecture seule |
| `planning` | planning technique : Gantt PPTX + slide echeances derivee (sync) + situation (statut/levier) + tableaux ; Gantt Excel en alternative | lecture seule |
| `deck-gate` | contenu du deck GATE (slides markdown/JSON ; assemblage pptx garde) | lecture seule |
| `transcripts` | normalise transcriptions/CR vers {date,title,url,text} (--dump|--files) | lecture seule |
| `omi-sync` | pendentif Omi -> Notion perso : --fetch / --import (classes, fusionnes) ; --unlock complete les pages verrouillees | écriture gardée |
| `slack` | normalise un export Slack (canaux+DM, threads) vers {date,author,channel,thread,text,url} ; lecture via Claude in Chrome, jamais d'ecriture | lecture seule |
| `dossier` | dossier projet 16:9 (charte slide-style) : --build json -> PPTX editable + HTML ; --sync PPTX retouche -> json -> HTML (garde-fou anti-ecrasement) | lecture seule |
| `traceability` | matrice de couverture IADT pre-remplie (xlsx a listes deroulantes, ou schema Notion) depuis un backlog/des exigences | lecture seule |
| `partner-report` | mail de suivi d'un call partenaire (--input ; rendu texte, jamais d'envoi) | lecture seule |
| `jira-images` | images des tickets Jira via API (check ; --apply garde) | écriture gardée |
| `jira-changes-audit` | qui a modifie quels tickets, quand, quoi (sections perdues) | lecture seule |
| `jira-sprints-audit` | audit des sprints Jira (charge, estimations, blocages) | lecture seule |
| `notion-topics-audit` | valide le FORMAT d'un sujet Notion (--body ; lecture seule) | lecture seule |
| `notion-scaffold` | arbo Notion miroir : pages manquantes (--emit-plan) | lecture seule |
| `drive-scaffold` | arbo Drive : ce qui manque (--apply cree les dossiers) | écriture gardée |
| `docs-coherence-audit` | coherence docs : une sortie est-elle a jour vs ses sources | lecture seule |
| `gate` | score les portes (gates) d'une mission et RECOMMANDE ; franchissement = acte humain | lecture seule |
| `method` | montre la methode de la mission en donnee (baremes, seuils, trames, tracabilite) | lecture seule |
| `templates` | registre des templates (objet x solution : sujets/planning/raci/risks, notion/excel) | lecture seule |
| `office` | cree un xlsx depuis un template excel si absent, l'edite chirurgicalement si present (OneDrive) | écriture gardée |
| `weekly-report` | CR hebdo du projet (par semaine, archive) depuis les prompts + mails + artefacts ; demande la semaine | lecture seule |
| `trace-audit` | ruptures de la chaine de tracabilite (besoin->ticket->POC->test) ; dit ou aller (lecture seule) | lecture seule |
| `console` | consoles de gestion en direct sur localhost : plugin (/) et projet (/projet) ; lecture seule | lecture seule |
| `cockpit` | porte d'entree : ou en est la mission, que fait-on ? (etat calcule + suite priorisee) | lecture seule |
| `tones` | aligne le ton des agents sur pipeline.yml (dry-run) | lecture seule |
| `init` | amorce une mission : cree le profil depuis les gabarits (create-si-absent ; dry-run, --apply ecrit) | écriture gardée |
| `setup` | onboarding : champs manquants d'un profil + suggestions (lecture seule) | lecture seule |
| `preflight` | verifie qu'on est connecte aux BONS systemes (Notion/SharePoint/Jira) avant d'ecrire | lecture seule |
| `reset` | TEST : remet a zero un dossier de projet (backup oblige ; dry-run ; --apply supprime) | écriture gardée |
| `agent` | lance une sous-tache sur un agent : --account (connecteurs) / --model / --agent (specialite) | lecture seule |

## Skills (`framework/skills/`) : tons, chartes, parcours

| Skill | Pour quoi |
|---|---|
| `demo` | Lance le faux projet et simule toutes les fonctionnalités du framework (aucune écriture). |
| `list` | Liste les générateurs du pm-framework et les missions (profils) du projet courant. |
| `run` | Lance un générateur du pm-framework sur une mission (lecture seule / dry-run par défaut). |
| `setup` | Onboarding guidé d'un profil de mission - détecte les champs manquants, propose des valeurs, puis écrit après validation. |
| `slide-style` | Charte de TOUS les livrables du pm-framework rendus en slides 16:9 (HTML du dossier projet et export PPTX) - titres courts, légende explicative sous chaque titre, unités en jours, style noir / ivoire à aplats, logo du client. |
| `technical-planning` | Produire ou mettre à jour le PPT « Technical planning » d'une mission (Gantt, slide des échéances toujours synchronisée, slides de situation Sujet / Statut / Situation / Levier / Échéance, tableau des responsabilités) dans le gabarit PowerPoint de l'entreprise, à partir d'une seule source de données (planning.json) alimentée par le suivi des sujets. |
| `voice-adservio` | Profil de rédaction ET de schématisation à la charte éditoriale Adservio, dérivé du dossier de fond "AI-DLC" (reference/rapport-aidlc.html). |
| `voice-casual` | Ton décontracté "jeune adulte" à employer quand on demande d'écrire un contenu (fichier, commentaire, message) dans ce ton — minuscule en début de phrase, phrases courtes, familier et chaleureux, petites libertés de langue. |
| `voice-deliverable` | Style rédactionnel des livrables SINBAD — écriture simple, claire, en prose, reprenant la terminologie du projet, comme la spécification, les one-pagers et l'onglet Terminologie. |
| `voice-maximilien` | Écrire à la voix de Maximilien Borne (TEM / TPM SINBAD) : mails, messages Slack et Teams, commentaires Jira, comptes rendus, notes d'annonce, tout ce qu'il signe lui-même. |
| `voice-slides` | Ton des slides du dossier projet (HTML 16:9 et PPTX) - titres courts sans verbe, légende explicative en prose posée dans le ton du CR partenaire, unités en jours. |

## Routines (`framework/routines/`) - détail dans `README.md`

| Routine | Ce qu'elle fait |
|---|---|
| `align-sprint-goals` | Dépréciée - pointeur vers publish-projection en mode goals-only (aligne les objectifs des sprints Jira sur le JSON éditorial, aucun ticket déplacé). |
| `audit-scope` | Audite le périmètre V1/V2 et la couverture des exigences contre Jira, et la cohérence du plan de sprints ; ne fait que proposer, cellule par cellule. |
| `collect-activity` | Transforme les requêtes Claude Code du jour qui ont modifié le projet en activités datées, versées dans un store local et une DB Notion privée, et résumables en bloc Weekly report. |
| `draft-followups` | Routine config-driven - prepare les relances pour obtenir les reponses attendues sur les sujets de suivi. |
| `morning-digest` | Routine config-driven - chaque matin, poste dans UN canal Slack dedie (et lui seul) le recap exhaustif des sujets a faire avancer, a partir du tracker de suivi, des sources de la veille et de l'agenda du jour. |
| `omi-sync` | Routine transverse (hors mission) - rapatrie les nouvelles conversations du pendentif Omi dans le Notion PERSO, classees pro / perso et fusionnees par echange. |
| `publish-projection` | Publie les pages d'avancement (gh-pages) puis le même HTML sur les artefacts Claude, aligne les objectifs des sprints du tracker sur le JSON éditorial, et signale tout texte de sprint périmé ; mode goals-only pour n'aligner que les objectifs. |
| `review-risks` | Routine config-driven - relit le registre de risques, le confronte aux sujets de suivi et a la projection de livrabilite, montre le registre actualise, puis met a jour le fichier en place apres validation en seance. |
| `review-topics` | Routine config-driven - passe en revue les sujets du tracker de suivi, propositions affichees et validees dans la conversation (transcriptions, mails et Slack en appui), applique ce qui est valide, puis enchaine sur la revue des risques. |
| `track-progress` | Pousse l'avancement V1 (un seul nombre, lu dans la projection) dans un seul champ d'une seule page du tracker Notion. |

## Agents (`framework/agents/`) - détail dans `AGENTS.md`

| Agent | Ce qu'il fait |
|---|---|
| `adservio-writer` | Produit un document ou un schéma complet à la charte éditoriale Adservio (style soigné du dossier de référence). |
| `archi-audit` | Monte un schéma d'architecture interactif (stack-imagery, model-first) à partir d'une description en langage naturel OU d'un modèle existant. |
| `doc-writer` | Rédige les chapitres d'un livrable structuré (plan qualité, dossier contractuel...) dont l'utilisateur est Content Owner ou relecteur, à partir des sources du projet. |
| `front-audit` | Audit en lecture seule du front d'une mission. |
| `jira-changes-audit` | Dit qui a modifié quels tickets du tracker, quand et quoi, sur une fenêtre de temps (depuis ce matin, depuis hier soir, depuis une heure donnée). |
| `jira-sprints-audit` | Audit en lecture seule du plan de sprints contre le board du tracker. |
| `jira-tickets-audit` | Détecte et répare les régressions de description des tickets du tracker - un brouillon périmé enregistré par-dessus la version à jour, qui fait reculer un ticket de plusieurs jours (symptôme fréquent : l'image du ticket n'est plus la bonne). |
| `notion-topics-audit` | Lecture seule des pages de la base de suivi (Notion) pour préparer une revue des sujets. |

> Ajouter ici toute nouvelle brique (le vérificateur `framework/harness/verifier.py` contrôle que chaque
> dossier de générateur a son `SKILL.md` et sa commande). Un skill de type partenaire s'ajoute aussi à
> `profiles/<mission>/partenaires.yml`.
