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

## Règles d'or (rappel)

1. **On ne touche jamais au SINBAD d'origine** (`~/Documents/Sinbad`) : le framework se construit à côté.
   `profiles/sinbad/` est une **copie de référence**, pas le projet SINBAD.
2. **Rien ne s'écrit dehors sans validation** : tout générateur est lecture seule / dry-run par défaut ;
   l'écriture (Jira, Notion, Office, gh-pages) est derrière un flag explicite et l'accord en session.
3. **Aucune notification** à qui que ce soit du fait d'une action : au doute, décrire et attendre.
4. Les hooks (`garde_office`, `garde_suppression`, `pas_ecraser_jira`, `journal_usage`) sont actifs via
   `.claude/settings.json` et refusent toute écriture Office/Drive/Jira non voulue.
5. Chemins d'un poste : paramétrés par variables d'env (`SINBAD_ROOT`, `SINBAD_PM_ROOT`,
   `CLAUDE_PROJECTS`, `PMF_JIRA_ENV`) avec défauts ; un clone frais exporte ces vars, n'édite pas les YAML.

## Commandes

```bash
python3 framework/pm.py list                 # tous les generateurs + les missions
python3 framework/pm.py run <gen> <mission>  # lance un generateur (lecture seule par defaut)
python3 framework/pm.py run setup <mission>  # etat de configuration du profil
python3 framework/pm.py demo [mission]       # faux projet : simule tout, n'ecrit rien
```
