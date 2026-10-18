# pm-framework

Framework de gestion de projet portable, extrait de SINBAD. **Une mission = un profil** ;
le moteur ne change pas. Le SINBAD d'origine (`~/Documents/Sinbad`) tourne tel quel et n'est
pas modifié : on bâtit ici, à côté, par copies généralisées.

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

Les commandes du plugin s'invoquent ensuite sous `/pm-framework:` : `list`, `demo`, `run`, `setup`.

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
| `sprint-audit` | audit des sprints Jira (charge, estimations, blocages) | profil `jira` |
| `ticket-changes` | qui a modifié quels tickets, quand, quoi (écrasements) | profil `jira` |
| `jira-image` | images des tickets via API (check ; `--apply` gardé) | `jira_ticket.yml` |
| `gate-deck` | contenu du deck GATE (slides ; assemblage pptx gardé) | `gate_deck.yml` |
| `poc` | POC React + Material UI depuis les récits (launcher auto) | `poc.yml` |
| `raci` | matrice RACI + extraits par rôle | `raci.yml` |
| `risks` | registre des risques (lecture ; écriture gardée) | `risks.yml` |
| `architecture` | harness du schéma d'archi (validate, lecture seule) | `architecture.yml` |
| `suivi` | suivi d'activité : collect / check / weekly / sync | `suivi.yml` |
| `cr-partenaire` | mail de suivi d'un call partenaire (`--input` ; jamais d'envoi) | `cr_partenaire.yml` |
| `notion-sujets` | valide le format d'un sujet Notion (`--body`) | `notion_sujets.yml` |
| `transcripts` | normalise transcriptions/CR (`--dump`/`--files`) | profil |
| `coherence` | une sortie est-elle à jour vs ses sources | `coherence.yml` |
| `gate` | score les portes (GTF : 7 gates) et recommande ; franchissement = acte humain | `gate.yml` |
| `method` | montre la méthode en donnée (barèmes, seuils, trames, traçabilité) | `method.yaml` |
| `templates` | registre des templates (objet × solution : sujets/planning/raci/risks, notion/excel) | `templates/trackers/` |
| `trace-audit` | ruptures de la chaîne besoin → ticket → POC → test ; dit où aller | `method.yaml` + `tracabilite.yml` |
| `init` | amorce une mission : profil depuis les gabarits (create-si-absent ; dry-run) | `config/*.example.yml` |
| `cockpit` | (option) où en est la mission, que fait-on ? état calculé + suite priorisée | `gate.yml` + `tracabilite.yml` |
| `scaffold-drive` | arbo Drive : ce qui manque (`--apply` crée) | `templates/` |
| `scaffold-notion` | arbo Notion miroir : pages manquantes (`--emit-plan`) | `templates/` |
| `tone` | aligne le ton des agents sur `pipeline.yml` | `pipeline.yml` |

`cr-partenaire`, `notion-sujets`, `transcripts` et `coherence` prennent leurs entrées par **flags**
(`--input`, `--body`, `--dump`/`--files`, `--root`) plutôt qu'en positionnel ; la mission est `--mission`
(défaut `sinbad`). Les autres suivent `run <gen> <mission> [args]`.

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
