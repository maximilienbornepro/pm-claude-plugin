# pm-framework - instructions de session

Framework de gestion de projet portable (voir [FRAMEWORK.md](FRAMEWORK.md), [README.md](README.md),
[ROADMAP.md](ROADMAP.md)). **Une mission = un profil** (`profiles/<mission>/`) ; le moteur ne change pas.
Langue : **français**.

## Au premier prompt d'une session : onboarding

Avant toute autre tâche sur une mission, vérifier que son profil est complet :

```bash
python3 framework/pm.py run setup <mission>
```

- S'il **liste des champs à renseigner** → dérouler le skill **`setup`** (onboarding step by step) :
  formulaire cliquable, un champ à la fois, **pré-rempli avec la suggestion**, éditable au clic ;
  puis écriture chirurgicale dans `profiles/<mission>/*.yml` **après validation** ; relancer `setup`
  jusqu'à « Profil complet », puis proposer `pm run demo <mission>`.
- S'il affiche **« Profil complet »** → enchaîner directement sur la demande de l'utilisateur.

La mission par défaut est `sinbad` (l'exemple de référence). Pour une nouvelle mission :
`cp -r profiles/sinbad profiles/<mission>` puis onboarding.

## Avant TOUTE écriture : preflight sur TOUS les connecteurs

Un même compte Claude peut avoir **plusieurs Notion / SharePoint / Figma connectés**. Risque réel
d'écrire au **mauvais** endroit. Donc, avant toute écriture externe sur une mission :

```bash
python3 framework/pm.py run preflight <mission>
```

**Règle dure** : on n'écrit sur un connecteur **que si** son identité est **renseignée dans le profil**
(`profile.connections`) **et** que le compte **réellement connecté correspond**. Pour chaque connecteur,
confirmer l'identité connectée avec son outil :
- **Notion** → `notion-get-self` : `workspace.id` + `workspace.name` == profil. (Un `notion-fetch` 404 sur la
  racine = mauvais workspace.)
- **Microsoft 365** (SharePoint/OneDrive/Outlook/Teams) → `get_me` : le `mail`/tenant == profil.
- **Figma** → `whoami` : `email` + `team_key` == profil.
- **Jira / Atlassian** → `getAccessibleAtlassianResources` : un `cloudId` == profil.

Si un connecteur est **non renseigné** dans le profil, **ou** si l'identité connectée **ne correspond
pas**, ou si le preflight renvoie **BLOQUANT** → **on n'écrit pas** sur ce connecteur. On renseigne
d'abord le profil (avec l'identité relevée) et/ou on demande de basculer la connexion, puis on re-preflight.
Une écriture Office reste en plus **sous `drive.root`** et sur le bon `web_site`.

## Règles d'or (rappel)

1. **On ne touche jamais au SINBAD d'origine** (`~/Documents/Sinbad`) : le framework se construit à côté.
   `profiles/sinbad/` est une **copie de référence**, pas le projet SINBAD.
2. **Rien ne s'écrit dehors sans validation** : tout générateur est lecture seule / dry-run par défaut ;
   l'écriture (Jira, Notion, Office, gh-pages) est derrière un flag explicite et l'accord en session.
3. **Aucune notification** à qui que ce soit du fait d'une action : au doute, décrire et attendre.
4. Les hooks (`garde_office`, `garde_suppression`, `pas_ecraser_jira`, `journal_usage`) sont actifs via
   `.claude/settings.json` et refusent toute écriture Office/Drive/Jira non voulue.
5. Chemins d'un poste : paramétrés par variables d'env déclarées dans les YAML de la mission
   (`${VAR:-défaut}`, ex. `CLAUDE_PROJECTS`, `PMF_JIRA_ENV`) ; un clone frais exporte ces vars, n'édite pas les YAML.

## Tests : systématiques

- `python3 framework/pm.py test` : vérificateur + toutes les suites, dont **chaque livrable généré pour de vrai**
  sur la mission de test `framework/harness/fixtures/profiles/test/` (fausses données, rien n'est écrit dehors).
- Après toute modification de code : lancer `pm test` avant de dire que c'est fait.
- Tout nouveau générateur (ou nouvelle option de sortie) ajoute son cas dans `framework/harness/test_livrables.py` ;
  le vérificateur échoue sinon. Un bug corrigé ajoute le cas qui l'aurait attrapé.
- Automatique : GitHub Actions à chaque push et PR (`.github/workflows/tests.yml`) ; en local,
  `pm test --install-hook` lance `pm test --quick` avant chaque commit.

## Commandes

```bash
python3 framework/pm.py list                 # tous les generateurs + les missions
python3 framework/pm.py run <gen> <mission>  # lance un generateur (lecture seule par defaut)
python3 framework/pm.py run setup <mission>  # etat de configuration du profil
python3 framework/pm.py demo [mission]       # faux projet : simule tout, n'ecrit rien
python3 framework/pm.py test [--quick]       # verificateur + tous les tests (avant de dire « c'est fait »)
```
