# pm-framework : ce que le plugin sait faire, et ce qu'il vaut

État au 23/11/2026, version 0.1.40 + générateur `planning`. Document écrit pour transférer la méthode
SINBAD sur un autre projet.

## En une phrase

Un plugin Claude Code qui transporte **la façon de piloter** un projet (CR, sujets, risques, planning,
RACI, décks, routines) d'une mission à l'autre : le moteur ne change pas, seul le **profil de mission**
(`profiles/<mission>/`) change.

## Ce qu'il couvre, besoin par besoin

| Besoin | Brique | Maturité | Preuve |
|---|---|---|---|
| **CR d'un call partenaire** (mail de suivi) | `partner-report` + skill de ton `voice-maximilien` | **Mûr** | format validé sur 10+ CR KSAT / Airbus ; langue par partenaire ; brouillon Outlook sur demande, jamais d'envoi |
| **CR de réunion interne → sujets Notion** | routine `review-topics` + `transcripts` + `slack` | **Mûr** | revue des sujets dans la conversation, sujet d'essai, fraîcheur avant écriture ; nouveau gabarit Statut / Contexte / Action attendue / Repères aligné sur le deck |
| **CR hebdo / weekly report** | `weekly-report` + `activity` | Utilisable | collecte prompts + mails + artefacts ; contrôle de couverture des thèmes |
| **Planning technique en PPT** (Gantt + échéances + situation + tableaux) | **`planning`** (nouveau) | **Mûr** | régénère le planning SINBAD complet ; la slide des échéances est **dérivée** du Gantt (sync garantie) ; 5 contrôles ; test `test_planning.py` |
| **Planning en Excel** (alternative) | `planning --xlsx` + template Gantt | Utilisable | remplit le template (120 lignes) ; barres par mise en forme conditionnelle, recalcul à l'ouverture |
| **Tableau de situation** (sujet / statut / levier) | `planning` (slides `status`) | **Mûr** | statuts normalisés (OK, En cours, Prévu, À risque, En discussion) ; levier obligatoire hors OK |
| **Tableau des responsabilités / charge** | `planning` (slides `tables`) | **Mûr** | tableau TPM de SINBAD reproduit |
| **RACI** | `raci` | Utilisable | matrice + extrait par rôle + plan de cellules ; l'écriture du classeur reste manuelle-assistée |
| **Registre des risques** (BUILD / RUN) | `risks` + routine `review-risks` | Utilisable | formulaire puis écriture chirurgicale (clone du registre de référence) |
| **Deck GATE** | `deck-gate` | Partiel | contenu (markdown / JSON) ; l'assemblage sur le template reste manuel |
| **Avancement / projection Jira** | `projection`, `plan`, `jira-sprints-audit`, `jira-changes-audit` | **Mûr** | reproduit la projection SINBAD au jour près ; pages publiées gh-pages + artefact |
| **Tickets Jira** (texte + image) | `jira-images` + hooks | Mûr | image par API, anti-écrasement de description |
| **Cohérence des documents** | `docs-coherence-audit` | Utilisable | dit quelle sortie est périmée vs ses sources |
| **Gates / méthode / traçabilité** | `gate`, `method`, `trace-audit`, `cockpit` | Utilisable | score des portes, ruptures besoin → ticket → test |
| **Démarrer une mission** | `init`, `setup`, `preflight`, `drive-scaffold`, `notion-scaffold` | Mûr | profil depuis gabarits, onboarding guidé, vérif des bons connecteurs avant écriture |
| **Routines planifiées** | 9 routines (`publish-projection`, `morning-digest`, `review-topics`...) | Mûr | tournent chaque jour sur SINBAD |
| **Schéma d'architecture** | `archi` | **Expérimental** | rendu automatique « éclaté » : **on le construit à la main par prompting** ; le modèle sert d'inventaire et d'export draw.io |

## Les garde-fous (ce qui fait sa valeur autant que les générateurs)

- **Lecture seule par défaut** : toute écriture (Notion, Jira, Office, gh-pages) est derrière un flag et un oui.
- **Aucune notification** : jamais de mention, partage, invitation ou envoi du fait d'une action.
- **Office** : une seule écriture par fichier, fraîcheur SharePoint vérifiée, sauvegarde, XML chirurgical
  (hook `garde_office` qui refuse l'écriture brute).
- **Jira** : relire avant d'écrire, refus si la description a bougé (`pas_ecraser_jira`).
- **Notion** : jamais de page créée ou déplacée hors de l'espace de pilotage (`garde_suppression`).
- **Preflight** : vérifie qu'on écrit dans le **bon** Notion / SharePoint / Jira quand plusieurs sont connectés.

## Ce qu'il vaut, honnêtement

**Note globale : 7 / 10.**

Points forts :
- La méthode est **réellement portable** : tout le propre-à-la-mission est dans le profil ; un projet fictif
  (`pm demo`) simule 18 actions sans rien écrire.
- **Testé** : 11 suites de tests + un vérificateur (meta, nomenclature, templates) passent à chaque publication.
- Les livrables qui comptent en comité (planning, situation, CR, avancement) sont **générés depuis une source
  unique**, ce qui supprime les incohérences entre documents.
- Les garde-fous viennent d'incidents réels (31 mails Notion partis, fichiers OneDrive bloqués, descriptions
  Jira écrasées) : ils protègent vraiment.

Limites à connaître :
- **Très « SINBAD »** : vocabulaire, gabarits et routines sont calqués sur un projet (Jira + Notion +
  SharePoint + Slack). Une mission sans Notion ou sans Jira demande d'adapter le profil et de désactiver des
  routines.
- **Dépend des connecteurs Claude** (Atlassian, Notion, Microsoft 365, Chrome pour Slack) : sans eux, les
  générateurs tournent mais ne lisent rien de vivant.
- **Les décks générés ont un thème neutre** : pour un deck d'entreprise, on copie les slides dans le template
  (copier / coller en ligne). Le deck GATE n'est pas encore assemblé automatiquement.
- **Excel / PowerPoint sans bibliothèque** (pas d'openpyxl ni python-pptx en session) : tout passe par du XML
  brut. C'est robuste pour ce qui est couvert, mais chaque nouveau format demande du travail.
- **Archi** : générateur non fiable, à traiter comme un atelier assisté, pas comme une génération.
- Le dépôt a des modifications non publiées (archi) ; la version marketplace n'inclut pas encore `planning`
  tant que `./publish.sh` n'a pas été lancé.

## Transférer sur un nouveau projet

1. Installer le plugin : `claude plugin marketplace add <dépôt>` puis `claude plugin install pm-framework@...`
   (ou décompresser l'archive et pointer Claude Code dessus).
2. `python3 framework/pm.py run init <mission>` puis `run setup <mission>` : le profil se remplit champ par champ.
3. `python3 framework/pm.py run preflight <mission>` avant toute écriture.
4. Planning : copier `framework/generators/planning/planning.example.json` dans
   `profiles/<mission>/planning.json`, l'adapter, puis `run planning <mission> --pptx planning.pptx`.
5. Les règles apprises sur SINBAD (dossier `exemple-sinbad/regles-apprises/` de l'archive) se relisent une
   fois : beaucoup sont devenues des garde-fous, les autres sont des préférences de rédaction.
