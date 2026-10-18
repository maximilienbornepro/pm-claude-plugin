# Templates ClickUp (à prévoir)

Dossier réservé à la solution **ClickUp**. Vide pour l'instant : aucun adaptateur ClickUp n'est encore
écrit. L'emplacement existe pour qu'ajouter ClickUp (ou toute autre solution) se fasse **sans toucher au
reste** - on dépose ici un fichier par objet, au même esprit que `trackers/notion/` et `trackers/excel/`.

## Pour ajouter ClickUp

1. Créer un fichier par objet voulu : `sujets.yml`, `planning.yml`, `raci.yml`, `risks.yml`.
2. Décrire l'objet dans le vocabulaire ClickUp (Space / List / champs personnalisés / statuts), sur le
   modèle des templates existants : un `object`, un `solution: clickup`, les champs et leurs options
   (états, thématiques…), des exemples.
3. Dans un profil, `profile.yml > pm_tracker: clickup` fera lire ces templates.
4. Écrire l'adaptateur de création (un `clickup-scaffold`, pendant de `notion-scaffold`).

Les **valeurs réelles** d'une mission (états, thématiques, barèmes) restent dans son profil, jamais ici.
