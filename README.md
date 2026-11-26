# pm-framework

Framework de gestion de projet portable, extrait de SINBAD. **Une mission = un profil** ;
le moteur ne change pas. Le SINBAD d'origine (`~/Documents/Sinbad`) tourne tel quel et n'est
pas modifié : on bâtit ici, à côté, par copies généralisées.

- **Guide d'utilisation (capacités, captures, pas à pas, prompts)** : [docs/GUIDE.md](docs/GUIDE.md)
- **Guide web (même contenu, catalogue filtrable, prompts à copier)** : [docs/index.html](docs/index.html), à ouvrir dans un navigateur
- **Cadrage** : [FRAMEWORK.md](FRAMEWORK.md) · **Feuille de route / état** : [ROADMAP.md](ROADMAP.md)
- **Profils de mission** : [profiles/README.md](profiles/README.md) (SINBAD = exemple de référence)
- **Nouvelle mission en 10 min** : [docs/nouvelle-mission.md](docs/nouvelle-mission.md)
- **Agents** : [framework/AGENTS.md](framework/AGENTS.md) · **Tons/rédaction** : [REDACTION.md](REDACTION.md)
- **Garde-fous d'écriture** : [framework/HARNESS.md](framework/HARNESS.md), [framework/NOTIFICATIONS.md](framework/NOTIFICATIONS.md)

## Installer le plugin Claude Code (et les mises à jour)

Hébergé sur git : l'install et les mises à jour se font en **une commande**, **sans zip**.

```bash
# 1. une fois : ajouter le marketplace (le dépôt) puis installer
claude plugin marketplace add maximilienbornepro/pm-claude-plugin
claude plugin install pm-framework@pm-framework-market

# 2. à chaque fois : récupérer les nouveautés
claude plugin update pm-framework@pm-framework-market
```

> Dépôt **privé** → ce poste doit avoir un accès git au repo (clé SSH / compte autorisé).
> Dépôt **public** → les commandes ci-dessus marchent partout, sans aucune auth (recommandé si
> aucune donnée sensible, ce qui est le cas ici : le profil réel est exclu).

Les commandes du plugin s'invoquent ensuite sous `/pm-framework:` : `list`, `demo`, `run`, `setup`, `technical-planning`.

**Côté mainteneur** (livrer une nouvelle version) : depuis le dépôt de travail,
```bash
./publish.sh "ce qui a changé"
```
Il incrémente la version, synchronise le moteur **sans `profiles/sinbad`**, refuse de pousser s'il
reste un identifiant interne, puis pousse. Les consommateurs n'ont plus qu'à `claude plugin update`.

## Utilisation

```
python3 framework/pm.py list                 # tous les generateurs + les missions
python3 framework/pm.py run <gen> <mission>  # lance un generateur (lecture seule / dry-run par defaut)
python3 framework/pm.py demo [mission]       # faux projet : simule tout, n'ecrit rien
python3 framework/pm.py missions             # liste les profils
```

Tout est **lecture seule / dry-run par défaut**. Les chemins d'écriture (Jira, Notion, Office,
gh-pages) restent derrière un flag explicite (`--apply`…) et la validation en session.

## Les générateurs

Chaque générateur lit le **profil** (où est le Jira, le Drive, les dates…) et le **pipeline**
(quel ton, quel schéma). Un `SKILL.md` par générateur décrit son usage et ses garde-fous.

| Générateur | Rôle | Config de mission |
|---|---|---|
| `projection` | charge restante vs capacité → date de fin V1 | `projection.yml` |
| `jira-sprints-audit` | audit des sprints Jira (charge, estimations, blocages) | profil `jira` |
| `jira-changes-audit` | qui a modifié quels tickets, quand, quoi (écrasements) | profil `jira` |
| `jira-images` | images des tickets via API (check ; `--apply` gardé) | `jira_ticket.yml` |
| `planning` | planning technique : Gantt PPTX + slide échéances **dérivée du Gantt** (toujours synchro) + situation (statut / levier) + tableaux (responsabilités, RACI) ; **Gantt Excel** en alternative | `planning.json` |
| `deck-gate` | contenu du deck GATE (slides ; assemblage pptx gardé) | `gate_deck.yml` |
| `poc` | POC React + Material UI depuis les récits (launcher auto) | `poc.yml` |
| `raci` | matrice RACI + extraits par rôle | `raci.yml` |
| `risks` | registre des risques (lecture ; écriture gardée) | `risks.yml` |
| `archi` | harness du schéma d'archi (validate, export draw.io). **Expérimental** : le schéma se construit à la main par prompting, le rendu auto n'est pas fiable | `architecture.yml` |
| `activity` | suivi d'activité : collect / check / weekly / sync | `activity.yml` |
| `partner-report` | mail de suivi d'un call partenaire (`--input` ; jamais d'envoi) | `cr_partenaire.yml` |
| `notion-topics-audit` | valide le format d'un sujet Notion (`--body`) | `notion_sujets.yml` |
| `transcripts` | normalise transcriptions/CR (`--dump`/`--files`) | profil |
| `omi-sync` | pendentif Omi -> Notion perso (`--fetch`/`--import`, `--unlock` apres abonnement) | `~/.config/pm-framework` |
| `docs-coherence-audit` | une sortie est-elle à jour vs ses sources | `coherence.yml` |
| `gate` | score les portes (GTF : 7 gates) et recommande ; franchissement = acte humain | `gate.yml` |
| `method` | montre la méthode en donnée (barèmes, seuils, trames, traçabilité) | `method.yaml` |
| `templates` | registre des templates (objet × solution : sujets/planning/raci/risks, notion/excel) | `templates/trackers/` |
| `office` | crée un xlsx depuis un template excel si absent, l'édite chirurgicalement si présent | `trackers/excel/` |
| `trace-audit` | ruptures de la chaîne besoin → ticket → POC → test ; dit où aller | `method.yaml` + `tracabilite.yml` |
| `init` | amorce une mission : profil depuis les gabarits (create-si-absent ; dry-run) | `config/*.example.yml` |
| `cockpit` | (option) où en est la mission, que fait-on ? état calculé + suite priorisée | `gate.yml` + `tracabilite.yml` |
| `drive-scaffold` | arbo Drive : ce qui manque (`--apply` crée) | `templates/` |
| `notion-scaffold` | arbo Notion miroir : pages manquantes (`--emit-plan`) | `templates/` |
| `tones` | aligne le ton des agents sur `pipeline.yml` | `pipeline.yml` |
| `agent` | lance une sous-tache sur un agent : --account (connecteurs) / --model / --agent (specialite) | `pipeline.yml` |
| `console` | consoles de gestion en direct sur localhost : plugin (/) et projet (/projet) ; lecture seule | profil |
| `dossier` | dossier projet 16:9 (charte slide-style) : --build json -> PPTX editable + HTML ; --sync PPTX retouche -> json -> HTML (garde-fou anti-ecrasement) | `dossier/dossier.json` |
| `plan` | plan de sprints (page « Avancement et sprints ») depuis Jira, config-driven ; design reutilisable (template + contrat + render + validate) | `plan.yml` + `projection.yml` |
| `preflight` | verifie qu'on est connecte aux BONS systemes (Notion/SharePoint/Jira) avant d'ecrire | profil `connections` |
| `reset` | TEST : remet a zero un dossier de projet (backup oblige ; dry-run ; --apply supprime) | — |
| `setup` | onboarding : champs manquants d'un profil + suggestions (lecture seule) | profil |
| `slack` | normalise un export Slack (canaux+DM, threads) vers {date,author,channel,thread,text,url} ; lecture via Claude in Chrome, jamais d'ecriture | profil `slack` |
| `traceability` | matrice de couverture IADT pre-remplie (xlsx a listes deroulantes, ou schema Notion) depuis un backlog/des exigences | items yml/json/csv |
| `weekly-report` | CR hebdo du projet (par semaine, archive) depuis les prompts + mails + artefacts ; demande la semaine | profil `weekly_themes` |

`partner-report`, `notion-topics-audit`, `transcripts` et `docs-coherence-audit` prennent leurs entrées par **flags**
(`--input`, `--body`, `--dump`/`--files`, `--root`) plutôt qu'en positionnel ; la mission est `--mission`
(défaut : `$PMF_MISSION`, sinon `demo`). Les autres suivent `run <gen> <mission> [args]`.

## Espace de pilotage à deux axes

Une mission ne suppose pas Notion. Deux axes indépendants dans `profile.yml` :
`pm_front` (`notion` | `drive`) × `file_store` (`sharepoint` | `onedrive` | `local`).
Couvre SINBAD (Notion/SharePoint), Drive/SharePoint, Notion/Drive. Détail dans
[profiles/README.md](profiles/README.md).

## Règles d'or

1. On ne refactore pas SINBAD en place (vélocité préservée).
2. On n'écrase jamais l'existant : tout outil d'écriture est créer-si-absent + réconcilier,
   `--dry-run` d'abord, **aucune notification sans accord**.
3. Toute page gh-pages a un **artefact Claude miroir**, les deux toujours à jour.
