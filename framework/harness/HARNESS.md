# Harness du pm-framework

Comment les automatisations (skills, agents, routines, generateurs) sont encadrees :
une **boucle de controle**, des **garde-fous**, du **contexte**. But : agir sur Jira,
Notion, Drive/SharePoint et GitHub Pages sans rien casser, sans rien ecraser, et sans
qu'aucune notification ne parte vers l'equipe.

## 1. Boucle de controle (patron de « run »)

Toute action qui ecrit quelque part suit ce patron :

1. **Preparer sur copie** (scratchpad), jamais directement sur la cible.
2. **Verifier** : relecture, diff, controle d'integrite.
3. **Garde-fou fraicheur** : la cible n'a pas bouge depuis la lecture (voir §2).
4. **Ecrire une seule fois**, en place (inode preserve), jamais `rm`/`mv`.
5. **Re-verifier** apres ecriture (relecture, taille locale <-> distante).
6. **Journaliser**.

## 2. Garde-fous

### a) Hooks bloquants (`framework/hooks/`)
Le vrai filet : executes par le harness, independants de la bonne volonte.

| Hook | Evenement | Role | Etat |
|---|---|---|---|
| `garde_office.py` | PreToolUse `Bash` | **bloque** toute ecriture Office synchronisee hors helper | ✅ porte |
| `pas_ecraser_jira.py` | PreToolUse `editJiraIssue` | **bloque** toute ecriture de description par le connecteur (auteurs proteges via `PMF_JIRA_PROTECTED`) | ✅ porte |
| journal d'usage | PreToolUse `Skill`/`Agent` | trace d'usage | ⏳ a porter |

L'ecriture versionnee Jira (relecture avant ecriture, abandon si la description a change)
est portee avec le generateur `jira-ticket` (Lot 3/4).

Le `garde_office.py` vise par defaut les chemins contenant `OneDrive` ; variable
`PMF_SYNC_MARKER` pour une autre racine synchronisee.

### b) Helper d'ecriture Office (`framework/harness/onedrive_xlsx.py`)
**Seule** facon d'ecrire un `.xlsx` synchronise : ecriture chirurgicale dans le XML
(jamais openpyxl, styles/images/fusions preserves), sauvegarde horodatee, reecriture
en place une seule fois, rapport de taille. Le hook renvoie vers ce helper.

### c) Controle de fraicheur distant
Le helper ne verifie pas le Drive (il n'a pas le connecteur). Avant tout `save()`,
en session : lire `lastModifiedDateTime`. Date du jour ou posterieure a la copie
locale = quelqu'un est dedans -> on n'ecrit pas, on transmet a la personne qui a la main.

### d) Validation humaine + notifications
Avant toute action **notifiante ou irreversible** (Jira, Notion, Drive, mail) :
montrer le contenu exact / un diff, attendre la validation. Jamais de `@` reel, de
partage, de deplacement de page qui notifie. Carte des notifications par generateur
(ex. `framework/generators/scaffold/NOTIFICATIONS.md`).

## 3. Contexte

Chaque run charge le profil de mission (`profiles/<mission>/profile.yml` + `pipeline.yml`),
le cadrage (`FRAMEWORK.md`) et les regles. Garde-fou de contexte : ne jamais agir sur
une donnee perimee (relire avant d'ecrire, lire la fraicheur distante).

## Etendre le harness

- **Nouveau garde-fou** : un hook (lit le JSON du PreToolUse sur stdin, ecrit une
  decision `allow`/`deny` sur stdout, sinon rien), branche dans `settings.json`. Ne
  jamais faire echouer un outil pour un simple journal (try/except, exit 0).
- **Nouvelle ecriture Office** : passer par `onedrive_xlsx.py` (sinon `garde_office.py`
  la bloque).
- **Nouveau generateur qui ecrit dehors** : livrer d'abord sa carte de notifications et
  sa version dry-run, avant toute ecriture.
