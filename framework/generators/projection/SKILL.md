---
name: projection
summary: Calcul generique du rapport de projection - charge Jira restante par pole vs capacite, date de fin projetee par pole et date de fin V1 confrontee au gel/MEP. Lecture seule, pilote par la config.
---

# Generateur `projection`

Porte le coeur de calcul du rapport de projection SINBAD
(`scan-jira/projection/serve.py`) en un module **generique** et **pilote par la
config**. Il ne connait aucune valeur de mission : capacite de l'equipe, affectation
aux poles, regles de version et dates viennent toutes de
`profiles/<mission>/projection.yml`. Le Jira (base, projet, board) vient du profil.

**Lecture seule absolue** : uniquement des requetes Jira de lecture (POST `search/jql`).
Rien n'est ecrit (ni Jira, ni Office, ni Notion), aucune notification. Le **rendu HTML**
n'est pas porte ici : ce module ne fait que le calcul.

## Ce qu'il calcule

- Charge **estimee / realisee / restante** par pole (back, front, sre) sur le perimetre V1.
- **Capacite nette** de chaque pole d'ici le gel (ETP x jours ouvres - absences anterieures),
  confrontee au reste a faire (`ecart = net - reste`).
- **Date de fin projetee par pole** : `ceil((reste + absences) / capacite ETP)` jours ouvres
  poses a partir d'aujourd'hui (week-ends sautes).
- **Date de fin V1** = le pole le plus tardif (**chemin critique**), confrontee au gel du
  code et a la MEP, avec le depassement en jours ouvres et en semaines.

## Lancer

```sh
cd pm-framework
PMF_JIRA_ENV=/chemin/vers/.env python3 framework/generators/projection/project.py <mission>
```

- `<mission>` : dossier sous `profiles/` (defaut `sinbad`).
- Identifiants Jira : via l'environnement (`JIRA_EMAIL`, `JIRA_TOKEN`, `JIRA_BASE` optionnel)
  ou via `PMF_JIRA_ENV` qui pointe un fichier `.env` (ex. celui de scan-jira). Les secrets
  ne sont jamais affiches.

Pour reutiliser le calcul ailleurs (rendu, publication, routine) :

```python
import sys; sys.path.insert(0, "framework/generators/projection")
import project
d = project.compute("sinbad")   # dict : poles, v1, v1_end, crit_pole, overshoot...
```

## Faire evoluer via la config (jamais le code)

Tout se regle dans `profiles/<mission>/projection.yml`. Gabarit vierge commente :
`framework/generators/projection/projection.example.yml`.

| Besoin | Cle a modifier |
|---|---|
| Changer la capacite / les absences | `capacity.staff` (une ligne par poste : `pole`, `dispo`, `off`, `off_after_deadline`) |
| Une absence tombe apres l'echeance | `off_after_deadline: true` sur ce poste |
| Reaffecter un epic a un pole | `poles.back_epics` / `poles.sre_epics` (defaut : front) |
| Sortir une version du reste V1 | `versions.next_version` (nom de fixVersion) |
| Reporter des epics/tickets en version suivante | `versions.v2_epics`, `versions.forced_v11` |
| Statuts et poids d'avancement | `workflow.*`, `workflow.status_weights` |
| Dates de gel / MEP | `dates.code_freeze`, `dates.mep` (reprises du `profile.yml`) |

## Correspondance avec SINBAD (verifie)

Sur le Jira SINBAD, `project.py` reproduit **a l'identique** les sorties de
`scan-jira/projection/serve.py` : charge/realise/reste par pole, V1 totale, V1.1,
semaines, date de fin par pole, date de fin V1, depassement, capacite nette/ecart.
Seul le compteur de tickets affiche un perimetre different (voir plus bas), sans effet
sur la projection.

## Portabilite

Pour une autre mission : copier `projection.example.yml` vers
`profiles/<mission>/projection.yml`, le remplir, puis lancer la meme commande. Aucune
ligne de code a toucher.
