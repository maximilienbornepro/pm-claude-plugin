# pm-framework - plan complet

Tout ce qu'il y a à faire pour transformer SINBAD en framework de gestion de projet portable.
`[x]` fait · `[~]` en cours · `[ ]` à faire. Règle permanente : **SINBAD reste intact**, tout se
construit à côté ; **rien n'écrit dehors sans dry-run + validation + carte des notifications**.

---

## Lot 0 - Fondations  `[x] fait`

- [x] Dépôt git voisin `~/Documents/pm-framework`
- [x] Cadrage `FRAMEWORK.md` (deux couches moteur/profil, règles d'or)
- [x] Config centrale `pipeline.yml` : livrable → ton + schéma + générateur ; agent → ton
- [x] Profil SINBAD `profile.yml` (Jira, Notion root, dates…) + gabarits `config/*.example.yml`
- [x] Loader sans dépendance `framework/lib/profile.py` (portabilité prouvée)
- [x] Logos rangés/renommés dans `profiles/sinbad/logos/`
- [x] Template arbo + miroir Notion↔SharePoint `templates/project-management-tree.yml`

## Lot 1 - Socle d'outillage  `[x]`

- [x] CLI unifiée `framework/pm.py` (`list` / `run <gen> <mission>` / `missions`) - dispatch vers les
      6 générateurs, lecture seule par défaut
- [x] `set_tone.py` : aligne le champ `skills:` de chaque agent sur la table `agents` du `pipeline.yml`
      (ton par agent), dry-run par défaut ; catalogue de valeur des agents dans `framework/AGENTS.md`
- [x] `palette.json` du profil (couleurs de marque + sémantiques + 3 thèmes, extraits de la chrome et du
      schéma) ; logos résolus par `profile.yml > identity.logos`
- [x] Doc « créer une nouvelle mission en 10 minutes » (`docs/nouvelle-mission.md`)
- [x] **Harnais de démo** `framework/demo.py` + `pm.py demo [mission]` : lance un **faux projet**
      (profil `demo`) et **simule toutes les fonctionnalités** (annonce ce qu'il créerait : Notion, Jira,
      Office, gh-pages, artefacts), **sans aucune écriture réelle** ; exécute pour de vrai les validateurs
      hors-ligne (harness d'archi). Testé : 17 actions simulées, archi réelle OK, 0 écriture.
- [x] **Exemples SINBAD disponibles comme contexte de départ** : `profiles/sinbad/architecture/model.json`
      (modèle d'archi réel, portable), `templates/project-management-tree.yml` (arbo Notion/Drive). SKILLs
      pointés dessus. Convention dans `profiles/README.md` (SINBAD = exemple de référence, conservé complet).
- [x] **Bibliothèque de logos techno partagée** `framework/assets/logos/` (AWS, Kubernetes, Keycloak,
      Prometheus, Redis, Terraform, ArgoCD, FluxCD, React, shadcn + UI) : réutilisable par toute mission ;
      les logos de marque restent dans `profiles/<mission>/logos/`. Catalogue dans son `README.md`.
- [x] **Espace de pilotage à deux axes** : `pm_front` (`notion` | `drive`) × `file_store` (`sharepoint` |
      `onedrive` | `local`), indépendants dans `profile.yml`. Couvre SINBAD (Notion/SharePoint), Drive/SharePoint
      et Notion/Drive. `framework/lib/links.py` (`folder_link`/`file_link`) s'adapte au `file_store` (testé sur
      les 3 stores) ; `scaffold_notion` ne tourne que si `pm_front: notion`. Documenté dans `profiles/README.md`.

## Lot 2 - Garde-fous & règles (AVANT toute écriture)  `[x]`

- [x] Cartographie des notifications du scaffold (`generators/scaffold/NOTIFICATIONS.md`)
- [x] Porter le harness Office : anti-écrasement brut (`garde_office.py`, généralisé par
      `PMF_SYNC_MARKER`) + écriture chirurgicale xlsx (`onedrive_xlsx.py`) + `HARNESS.md` (testés)
- [x] Étendre la cartographie : Jira, mails/Outlook, Teams, Notion, artefacts/gh-pages
      (`framework/NOTIFICATIONS.md`, carte globale)
- [x] Porter le hook anti-écrasement Jira (`pas_ecraser_jira.py`, auteurs via `PMF_JIRA_PROTECTED`,
      testé). L'écriture versionnée (relire avant d'écrire) vient avec `jira-ticket` (Lot 3/4).
- [x] Porter le journal d'usage (`journal_usage.py`) + `settings.json` du framework qui branche les
      3 hooks (garde_office, pas_ecraser_jira, journal) - JSON validé, journal testé
- [x] Règle « jamais de suppression/déplacement » sur Drive consortium et sur page Notion, codée en dur
      (`garde_suppression.py` : refuse rm/mv/trash sur Drive synchronisé + `notion-move-pages` ; testé ;
      branché dans `.claude/settings.json`)

## Lot 3 - Générateurs en lecture seule / dry-run  `[x]`

- [x] scaffold Drive - dry-run (compare arbo, ne crée rien)
- [x] scaffold Notion - dry-run (`generators/scaffold/scaffold_notion.py`, lecture seule : compare un
      instantane de pages au miroir ; testé : SINBAD 17/17 attendues présentes, SPV `à confirmer` à arbitrer,
      détecte une page manquante). L'instantané des pages vient du connecteur (étape Claude).
- [x] **rapport de projection** `generators/projection/project.py` + `profiles/sinbad/projection.yml` :
      config-driven (capacité/staff, epics-pôles, règles V1/V1.1, modèle charge/réel/reste, jours ouvrés),
      lecture seule. **Reproduit exactement** la référence `serve.py` : fin V1 01/12/2026, pôles et
      semaines au chiffre près. Le rendu HTML + publication gh-pages restent à faire (Lot 4, écriture).
- [x] **client Jira générique** `framework/lib/jira.py` : base/projet/board lus du profil, identifiants
      de l'env (ou `PMF_JIRA_ENV`), lecture seule - prouvé sur SINBAD (7 sprints, 242 tickets SIN)
- [x] **audit de sprints générique** `generators/jira-sprints-audit/audit_sprints.py` : charge par sprint,
      tickets sans estimation, blocages inversés, dates - prouvé sur SINBAD (a trouvé SIN-238→SIN-237).
      La réconciliation liée au plan de mission (objectifs, versions V1/V1.1) reste au niveau du profil.
- [x] **architecture (stack-imagery), model-first** `generators/archi/` : contrat `SCHEMA.md`,
      starter `model.example.json`, générateur `build_html.py` (modèle → HTML interactif validé 7/7),
      harness `validate.py`, export `export_drawio.py` (1 page par écran), **liens inter-schémas**
      (drill-down : `link` sur entité/zone → `data-go` HTML + lien cross-page draw.io). Deux entrées :
      édition du modèle ou **gros prompt** (agent `architecture`). `pm run architecture <mission>
      [--render|--export drawio]`. Publication 3 cibles = écriture gardée. Reste : re-modéliser SINBAD.
- [x] Entrées **transcriptions** (imposées par le framework) : lecteur `generators/transcripts/read_transcripts.py`
      (sources pluggables - dump Notion meeting notes par défaut, ou dossier de fichiers), normalise vers
      `{date, title, url, text}` et filtre par fenêtre ; sortie `--json` pour sujets / CR / risques / synthèse.
      Emplacement canonique = miroir Notion sous Gouvernance (documenté dans le SKILL). Testé.

## Lot 4 - Générateurs en écriture (chacun derrière validation + notifications)  `[ ]`

- [x] scaffold Drive écriture : `scaffold_drive.py --apply` (`mkdir` créer-si-absent, idempotent, jamais
      d'écrasement/suppression/déplacement). Testé sur dossier jetable.
- [~] scaffold Notion : `scaffold_notion.py --emit-plan` rend la **spec de création** par page manquante
      (titre, parent, lien SharePoint + description) **sans appeler le connecteur** ; la création reste une
      étape Claude gardée par le **test « page jetable »** (absence de notification) et faite sous le parent,
      jamais à la racine. SKILL `scaffold/SKILL.md`.
- [ ] scaffold **Office** (3e couche) : manifeste `office` par dossier dans le template ; le scaffold signale
      les fichiers Office standards manquants et peut les créer par copie de modèle (garde-fou Office). Le
      contenu reste produit par les générateurs dédiés (risks, gate-deck, projection…).
- [x] **gate-deck** `generators/deck-gate/gate_deck.py` + `profiles/sinbad/deck-gate.yml` : rend le **contenu**
      du deck GATE (slides en markdown/JSON, ton Adservio), jalons **auto depuis `key_dates`** (T0 / gel 15/11 /
      MEP 30/11). Testé. L'assemblage pptx sur le template (schémas PNG, une seule écriture OneDrive) reste
      l'étape **gardée** via la cohérence des docs, hors de ce générateur. SKILL `gate_deck/SKILL.md`.
- [x] **jira-ticket (deux outils)** `generators/jira-images/jira_image.py` + `profiles/sinbad/jira-images.yml` :
      connecteur pour le **texte** (sous garde-fou), **API pour l'upload/vérif d'images** (impossible via
      le connecteur) - config-driven, lecture seule prouvée (liste les pièces jointes SIN-105/SIN-87),
      `--apply` gardé derrière flag. Reste : la capture POC (skill `poc-captures`) et le choix section « Rendu ».
- [x] **notion-sujets** `generators/notion-topics-audit/` : config `notion_sujets.yml` (data source, filtre TPM,
      ton, seuils de structure) + `check_sujet.py` (validateur de format : sections Contexte/Action, pas de
      liste à plat ≥3, pas de prose au kilomètre, pas de mention ; testé) + SKILL (écriture connecteur gardée).
      Condensation de l'existant : routine `revue-sujets`, mode `condensation`.
- [~] notion-planning : report planning (+ slide deck), écriture gardée « demander avant » (SKILL + `notion_planning.yml` faits ; pas de validateur dédié, écriture par le connecteur)
- [x] **cr-partenaire** `generators/partner-report/cr_partenaire.py` + `profiles/sinbad/partner-report.yml` : mail KSAT (EN) / Airbus (FR), format par partenaire, rendu texte **sans envoi** (testé)
- [x] **raci** `generators/raci/raci.py` + `profiles/sinbad/raci.yml` : RACI data-driven (rôles = colonnes,
      activités en flow inline), rend la matrice + un extrait par rôle (markdown/JSON) + un plan de cellules
      (`--cells`) pour l'onglet matrice. Testé. Écriture Office gardée (helper `onedrive_xlsx.py`), onglets de
      rôle régénérés depuis la sortie. Lot sécurité/plateforme encodé (supervision, Keycloak, pentest, SOC, NATS, go-live).
- [x] **risks-register** `generators/risks/risks.py` + `profiles/sinbad/risks.yml` : lit le registre
      (config-driven, lecture seule prouvée sur le vrai Excel, 12 risques), flux formulaire → proposition →
      écriture gardée via le helper Office (jamais exécutée ici). Reste : annexe structurée des sujets Notion.

- [x] **suivi d'activité** `generators/activity/{collect,build_weekly,sync_notion}.py` + `profiles/sinbad/activity.yml`
      + routine `suivi` (quotidienne, 19h) : prompts Claude Code **pertinents** (= ayant modifié le projet) →
      store JSONL curé → DB Notion **privée** (4 catégories : produit / attendu de moi / j'attends des autres /
      bloquant) + bloc Weekly report (modèle actuel). DB privée créée et peuplée ; routine câblée dans routines.yml.

## Lot 5 - Tons, rédaction & agents  `[~]`

- [x] Porter les tons génériques : `voice-deliverable`, `voice-casual`, `voice-maximilien`,
      `voice-adservio` (présents dans `framework/skills/` ; gabarits/schémas Adservio à enrichir)
- [x] `REDACTION.md` catalogue dans le framework (tons, règles de langue, par support)
- [x] Porter/généraliser les agents, chacun lisant son ton depuis `pipeline.yml` (`framework/agents/`,
      génériques, ton aligné par `set_tone.py`). Famille B (audits/visuels, ton `null`) : `architecture`,
      `front-audit`, `sprint-plan-audit`, `sujets-read`, `ticket-changes`, `ticket-audit`. Famille A (prose,
      ton configurable) : `doc-redaction` (ex qap-redaction) et `voice-adservio`.

## Lot 6 - Routines planifiées  `[x]`

- [x] Définitions `routines/` paramétrées par profil : **une routine = une tâche**. 8 routines mono-tâche
      (`publication-projection`, `objectifs-sprints`, `avancement-tracker`, `audit-perimetre`, `revue-sujets`,
      `revue-risques`, `slide-planning`, `suivi`) dans `routines.yml` + un SKILL générique chacune
- [x] Doc de ré-activation portable (`framework/routines/README.md` : pointeur mince app -> SKILL, procédure)

## Lot 7 - Cohérence & audits  `[~]`

- [x] Porter `sinbad-coherence-docs` (GATE ↔ Excel ↔ PPT ↔ PNG) généralisé : `generators/docs-coherence-audit/check_coherence.py`
      + `profiles/sinbad/docs-coherence.yml` (carte des dépendances, états PERIME / OK / DIFFERENT / MANQUANT)
- [x] Porter l'audit **modifs du jour / sections perdues** : `generators/jira-changes-audit/changes.py` (générique,
      client Jira du framework, auteur « assistant » exclu via profil `jira.assistant_author`), `pm run ticket-changes
      <mission>`, back l'agent `ticket-changes`. Repère les écrasements de description (sections perdues ⚠).
- [ ] Optionnel : porter les audits de **qualité de texte des tickets** (liste à plat, prose longue, références
      croisées, uniformité) - spécifiques au modèle de tickets SINBAD, à généraliser si une 2e mission en a besoin.

## Lot 8 - POC / app de mission  `[~]`

- [x] **Générateur de POC** `generators/poc/poc.py` + `profiles/sinbad/poc.yml` : depuis les **récits**
      (liste d'écrans), produit un POC React runnable **stack définie Vite + TS + React Router + Material UI**,
      un écran-stub par récit, nav Material, et **met à jour la `launch.json`** de la mission (launcher auto).
      Dry-run par défaut ; testé (11 fichiers générés, TSX valide, launcher créé). `pm run poc <mission>`.
- [ ] Étape suivante : **scaffold Figma** des écrans depuis la même liste (connecteur Figma).
- [x] `launch.json` (preview) par mission : mise à jour automatique par le générateur POC (fusion par `name`).

## Lot 9 - Bascule finale  `[~]`

- [x] **Audit de portabilité du moteur** (`framework/`) : aucune constante de mission dans la LOGIQUE.
      Seule fuite réelle = la liste de tons codée en dur dans `set_tone.py` → **corrigée** (découverte
      dynamique depuis `framework/skills/`). Le reste des mentions SINBAD sont des **exemples** (KNOWLEDGE/
      SCHEMA d'archi, docstrings, catalogues) conservés volontairement (SINBAD = exemple de référence).
- [x] **2e mission d'essai** amorcée : profil `demo` + harnais `pm demo` (14 fonctionnalités simulées,
      validateur d'archi réel). Prouve la portabilité sans risque.
- [ ] Optionnel (de-SINBADisation plus poussée) : renommer le ton de base `voice-deliverable` en générique ;
      déplacer les spécifiques SINBAD de `architecture/KNOWLEDGE.md`+`SCHEMA.md` vers le profil ; aligner la
      table `agents` de `profiles/sinbad/pipeline.yml` sur les nouveaux noms d'agents génériques.
- [ ] Rejouer de bout en bout sur une **vraie 2e mission** (au-delà de `demo`) quand elle se présentera.

---

### Ordre conseillé
Lot 2 (garde-fous) et Lot 3 (lecture seule) d'abord : on sécurise et on prouve sans risque. Puis Lot 4
une écriture à la fois, chacune précédée de sa carte de notifications et d'un essai sur cible jetable.
Lots 5-6 en parallèle (tons/agents/routines). Lot 9 quand le moteur a tourné sur une 2e mission.
