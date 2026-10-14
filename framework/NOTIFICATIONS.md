# Cartographie des notifications - framework

Règle d'or : **aucune action du framework ne déclenche de notification vers un tiers** sans validation
explicite. Avant toute écriture, consulter cette carte : qui serait notifié ? Au moindre doute, on décrit
et on attend. Une notification partie ne se rattrape pas.

Cette carte couvre **toutes les cibles**. La carte détaillée du scaffold (Drive + Notion) reste dans
`framework/generators/scaffold/NOTIFICATIONS.md` ; les hooks qui *appliquent* ces règles sont dans
`framework/hooks/` (`garde_office.py`, `garde_suppression.py`, `pas_ecraser_jira.py`).

## Drive (SharePoint / OneDrive consortium)

| Action | Notifie ? | Verdict |
|---|---|---|
| Créer un dossier absent (via synchro locale) | non | ✅ créer-si-absent |
| `rm` / `mv` / `rmdir` / `trash` d'un fichier ou dossier synchronisé | - | ❌ **jamais** (casse la synchro ; un Office recréé perd son item SharePoint). Hook `garde_suppression.py`. On réécrit **en place** (`cat copie > fichier`). |
| Écriture d'un classeur Office | non (si en place) | ✅ seulement via le helper `onedrive_xlsx.py`, après contrôle de fraîcheur. Hook `garde_office.py`. |
| Partager / inviter sur un dossier | **oui** | ❌ jamais |

## Notion

| Action | Notifie ? | Verdict |
|---|---|---|
| Créer une page **privée (draft)** | **non** (page workspace-level, aucun abonné) | ✅ voie sûre (prouvé) |
| Créer une page sous une page existante (du dossier de pilotage) | pas de mail ; résiduel in-app pour un abonné du parent | ✅ créer-si-absent (créer une sous-page n'envoie pas de mail) |
| **Déplacer** une page vers un autre conteneur ou la racine | **oui** (droits recréés -> mail « invité(e) dans… » à tous les membres) | ❌ **jamais**. Hook `garde_suppression.py` (refuse `notion-move-pages`). Pour retirer d'une base : **proposer la suppression** à l'utilisateur. |
| `@mention`, commentaire, partage, attribution de tâche | **oui** | ❌ jamais ; noms en **texte simple** |
| Supprimer une page | non | on ne le fait pas (le connecteur ne sait pas) ; on **propose**, l'utilisateur supprime |

## Jira

| Action | Notifie ? | Verdict |
|---|---|---|
| Lire (JQL, get) | non | ✅ |
| Éditer une description | watchers/assignee **oui** | ✅ seulement sous garde-fou anti-écrasement (`pas_ecraser_jira.py` : relire avant d'écrire, refuser si la version a changé) ; **jamais** le texte des tickets des **auteurs protégés** du profil (`PMF_JIRA_PROTECTED`) |
| Créer / transitionner un ticket, poser un lien | **oui** (watchers) | ⚠️ seulement sur demande, pilote d'abord |
| `@mention`, commentaire | **oui** | ⚠️ seulement sur demande |
| **Déplacer** un ticket entre sprints | oui | ❌ aucune routine ne déplace un ticket |
| Image / pièce jointe | - | via l'API (jamais le connecteur, qui efface les médias) ; l'image ne doit jamais sauter |

## Mails / Outlook

| Action | Notifie ? | Verdict |
|---|---|---|
| Lire (recherche, lecture) | non | ✅ connecteur en lecture seule |
| **Envoyer** un mail / répondre / inviter | **oui** | ❌ **jamais d'envoi**. On **rend le texte**, l'utilisateur l'envoie. Au plus : un brouillon ouvert en rédaction (mailto) ou une copie `.eml` locale. |

## Teams

| Action | Notifie ? | Verdict |
|---|---|---|
| Lister / lire canaux et messages | non | ✅ |
| **Envoyer** / répondre dans un canal ou un chat | **oui** | ❌ **jamais**. Messages rendus à copier. |

## Artefacts Claude / GitHub Pages

| Action | Notifie ? | Verdict |
|---|---|---|
| Publier un **artefact privé** | **non** (privé à l'utilisateur) | ✅ |
| Pousser sur **gh-pages** | non | ✅ (règle : toujours **doublé d'un artefact Claude**, les deux à jour - voir FRAMEWORK.md) |
| **Partager** un artefact / rendre public | action de l'utilisateur | ⚠️ l'utilisateur décide (menu Share) |
