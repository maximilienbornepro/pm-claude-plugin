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

## Règle : le compte se déclare dans `routing.yml` (pas en dur)

Le **compte Claude** d'une commande ou d'une routine se déclare dans `profiles/<mission>/routing.yml`
(lu par `account_for`, en mode multi-compte). On route **dans la config**, jamais en dur dans un SKILL.

**Depuis l'app desktop** : la session tourne toujours sur le compte de l'app. L'app **injecte son auth
dans l'environnement** (`ANTHROPIC_BASE_URL`, `CLAUDE_CODE_ACCOUNT_UUID`, socket de messagerie…),
qu'un `claude -p` enfant hérite - il utiliserait donc le compte de l'app, **pas** le `CLAUDE_CONFIG_DIR`.
`pm run agent` **retire ces variables** (`HOST_ENV`) quand le config dir cible a son propre login
(`.claude.json`) : le worker bascule alors **vraiment** sur ce compte (vérifié : env strippé + config dir
safran → OK ; + config dir vide → « Not logged in »). Un config dir sans login autonome (ex. `~/.claude`,
géré par l'app) reste sur le compte hôte.

**`--exec`** : par défaut un worker délégué ne fait que lire/raisonner. `--exec` passe
`--dangerously-skip-permissions` pour qu'il **exécute** (scripts, écritures) en headless - à réserver aux
tâches dont la sûreté tient à leur **logique** (ex. une routine aux garde-fous internes).

**Faire tourner une routine sur un autre compte** : la déclarer dans `routing.yml`, puis en **Étape 0**
du SKILL déléguer la routine entière à ce compte via `pm run agent --command <routine> --exec`, avec un
drapeau (`PMF_ON_SAFRAN`) pour éviter la boucle et un **repli** sur le compte courant si le login manque.

## Bandeau de bascule de compte

Dès qu'une délégation bascule **effectivement** de compte (config dir avec login autonome, auth hôte
retirée), `pm run agent` imprime un **bandeau** `/!\ SWITCHING -> <COMPTE> CLAUDE (email)` avant de
lancer le worker. Côté **orchestrateur** (la session qui délègue), afficher le **même avertissement
bien visible dans la conversation**, avant le lancement et au retour sur le compte courant, en nommant
le compte cible. Objectif : voir sans ambiguïté quel compte **exécute et facture**, puisque la session
interactive reste sur le compte de l'app et que seules les délégations basculent.
