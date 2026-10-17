---
name: preflight
description: Vérifie que TOUS les connecteurs de la session (Notion, Microsoft 365/SharePoint/OneDrive, Figma, Jira) pointent bien le compte de la mission avant toute écriture. On n'écrit sur un connecteur que s'il est renseigné dans le profil ET que l'identité connectée correspond. Lecture seule.
meta:
  produces: null
  consumes: []
  mcp_deps: [jira, notion, m365]
  cost: light
  status: stable
---

# preflight (bons connecteurs avant d'écrire)

Problème : un même compte Claude peut avoir **plusieurs Notion / SharePoint / Figma connectés**. Sans
garde, un générateur peut écrire au **mauvais** endroit. Le profil ancre l'identité attendue de chaque
connecteur (`profile.connections`) ; ce preflight la confronte au compte réellement connecté.

## Usage
```
python3 framework/pm.py run preflight <mission>
```

## Règle (stricte)
On n'écrit sur un connecteur **que si** :
1. son identité est **renseignée** dans `profile.connections.<connecteur>`, **et**
2. le compte **réellement connecté correspond** (vérif par Claude avec l'outil d'identité).

Sinon (non renseigné, champ manquant, ou identité différente) → **BLOQUANT** : aucune écriture sur ce
connecteur. On renseigne d'abord le profil avec l'identité relevée, et/ou on demande de basculer la
connexion, puis on relance le preflight.

## Outils d'identité par connecteur
- **Notion** → `notion-get-self` (workspace id + nom + compte). Backstop : `notion-fetch` de la racine
  `project_management_root` ; un **404** = mauvais workspace.
- **Microsoft 365** (SharePoint/OneDrive/Outlook/Teams) → `get_me` (mail + tenant) ; `get_granted_scopes`.
- **Figma** → `whoami` (email + team).
- **Jira / Atlassian** → `getAccessibleAtlassianResources` (cloudId + url).

## Renseigner le profil
Si un connecteur n'est pas renseigné, appeler son outil d'identité, **noter l'identité relevée** dans
`profile.connections.<connecteur>`, puis re-preflight. Tant que ce n'est pas fait, pas d'écriture dessus.
La racine Drive locale (`drive.root`) et le `web_site` sont vérifiés en plus pour toute écriture Office.
