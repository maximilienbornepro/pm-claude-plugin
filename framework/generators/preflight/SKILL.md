---
name: preflight
description: Vérifie qu'on est connecté aux BONS systèmes (Notion, SharePoint, Jira) d'une mission avant toute écriture. Évite d'écrire dans le mauvais Notion quand plusieurs espaces sont connectés sur le même compte. Lecture seule.
---

# preflight (bon espace connecté avant d'écrire)

Problème : un même compte Claude peut avoir **plusieurs Notion/SharePoint connectés**. Sans garde, un
générateur peut écrire dans le **mauvais** espace. Le profil **ancre l'identité attendue** ; ce preflight
la confronte au système réellement connecté.

## Usage
```
python3 framework/pm.py run preflight <mission>
```

## Ce qu'il vérifie
- **Notion** (par Claude, via le connecteur - **obligatoire**) : `notion-fetch` de la racine
  `project_management_root` du profil.
  - **404 / introuvable** → mauvais workspace connecté (message Notion : « authenticated to the correct
    workspace »). **Ne rien écrire.**
  - **Titre ≠ `expect_pm_title`** → mauvais espace. **Ne rien écrire.**
  - Trouvé + bon titre → workspace correct.
- **Drive / SharePoint** (par script) : la racine locale `drive.root` existe ; le `web_site` doit
  correspondre à la mission. Un fichier Office s'écrit **sous cette racine**, jamais ailleurs.
- **Jira** (par script si identifiants en env) : le `project_key` du profil est accessible ; sinon
  `cloud_id` + `project_key` du profil font foi.

## Règle
Tant que le preflight Notion n'est pas **vert** (racine trouvée + bon titre), **aucune écriture Notion**.
À lancer au début d'une session d'écriture, et dès qu'on change de mission ou de connexion. En cas de
mismatch : décrire le problème, demander de basculer la connexion, **ne pas écrire**.
