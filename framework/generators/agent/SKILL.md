---
name: agent
description: Lance une sous-tâche sur l'agent choisi selon 3 axes - compte Claude (connecteurs isolés via CLAUDE_CONFIG_DIR), modèle (opus/sonnet/haiku/fable), et spécialité (framework/agents). Permet, dans un même projet, de router du travail vers un compte/un modèle/une spécialité différents, avec isolation physique des connecteurs.
---

# agent (router compte / modèle / spécialité)

Dans un même projet, on ne peut pas changer le compte de la session en cours. Mais la session peut
**déléguer** une sous-tâche à un worker Claude lancé sur **un autre compte** (donc d'autres connecteurs),
**un autre modèle**, ou avec **une spécialité** - et récupérer le résultat.

## Usage
```
pm run agent --account perso  --model haiku  "resume ce doc public"
pm run agent --account safran --model opus   "analyse l'impact du ticket SIN-..."
pm run agent --agent jira-changes-audit --model sonnet "..."     # specialite + modele
pm run agent --dry-run "..."                                      # montre la commande, ne lance rien
```

## Les 3 axes
- **`--account <nom>`** → `config/accounts.yml > accounts.<nom>.config_dir` → `CLAUDE_CONFIG_DIR`. Le compte
  porte **ses** connecteurs : l'isolation est **physique** (un worker perso n'a pas les connecteurs pro).
  Défaut : `profile.orchestration.default_account` ; sinon la **session courante** (mono-compte).
- **`--model <alias>`** → `opus / sonnet / haiku / fable` (ou `opus-5.5`…). Défaut : profil puis session.
- **`--agent <nom>`** → charge `framework/agents/<nom>.md` (ses instructions) en contexte de la tâche.

## Configuration (voir `config/accounts.example.yml`)
- **Mono-compte** : rien à configurer. `pm run agent --model … "…"` tourne sur la session courante.
- **Multi-compte** : `config/accounts.yml` (chemins des config dirs + sensibilité) + se logger **une fois**
  dans chaque (`CLAUDE_CONFIG_DIR=$HOME/.claude-safran claude`), + `orchestration` dans le profil.
  `config/accounts.yml` est **gitignore** (jamais publié).

## Sécurité
- **Isolation physique** : une sous-tâche mal routée vers le compte perso ne peut pas toucher les données
  consortium (connecteurs absents).
- **Défense en profondeur** : chaque worker fait tourner `preflight` dans sa session.
- Ce générateur **n'écrit rien** lui-même : il délègue à `claude -p`. Le worker reste soumis à ses propres
  permissions et au preflight.
