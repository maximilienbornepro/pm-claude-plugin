# Profils de mission

Un **profil** = toutes les valeurs d'une mission (Jira, Notion, Drive, dates, capacité, tons, routines).
Le moteur générique vit dans `framework/` ; un profil ne contient **que des données**, jamais du code.

## Espace de pilotage : deux axes

Une mission ne suppose **pas** Notion. L'espace de pilotage se règle par **deux axes indépendants** dans
`profile.yml` :

- **`pm_front`** - où vit la connaissance : `notion` ou `drive` (une arbo de dossiers + un index par dossier).
- **`file_store`** - où vivent les fichiers : `sharepoint`, `onedrive` ou `local`.

Les combinaisons couvrent les cas réels :

| `pm_front` | `file_store` | Exemple |
|---|---|---|
| `notion` | `sharepoint` | **SINBAD** (pages Notion miroir d'un SharePoint) |
| `drive` | `sharepoint` | pilotage dans les dossiers SharePoint (pas de Notion) |
| `notion` | `onedrive` / `local` | Notion + fichiers sur un OneDrive ou en local |

Ce que ça pilote :
- **`scaffold_notion`** ne tourne que si `pm_front: notion` (sinon il le dit et s'arrête) ;
  `scaffold_drive` crée l'arbo dans tous les cas (et, à terme, un index par dossier quand `pm_front: drive`).
- **Les liens** (`framework/lib/links.py`, `folder_link` / `file_link`) s'adaptent au `file_store` :
  lien navigateur `AllItems.aspx` (SharePoint), ou chemin local synchronisé (OneDrive / local).

## `sinbad/` est l'exemple de référence - on le garde complet

`profiles/sinbad/` n'est pas un profil jetable : c'est l'**exemple de travail canonique** du framework,
rempli avec de vraies valeurs. On le **conserve complet** pour deux raisons :

- **Bootstrap d'une nouvelle mission par copie** : on part de SINBAD et on adapte, plutôt que de
  remplir des gabarits vides. C'est le chemin le plus rapide (voir `docs/nouvelle-mission.md`).
- **Référence vivante** : quand on se demande « à quoi ressemble un `projection.yml` correct »,
  « comment se déclare une routine », « quelle forme a un `partner-report.yml` », la réponse est dans
  `sinbad/`, à jour parce que c'est une mission réelle.

**Règle** : on ne « désinbadise » jamais `profiles/sinbad/` pour le rendre générique. Le générique,
c'est `framework/` + les gabarits commentés `config/*.example.yml`. Le profil SINBAD, lui, **reste
l'exemple réel** - complet, non expurgé.

## Amorcer une nouvelle mission

```bash
cp -r profiles/sinbad profiles/<mission>      # on copie l'exemple
# puis on adapte la COPIE ; profiles/sinbad reste intact comme référence
```

On adapte le copie fichier par fichier. Ce qui est **propre à la mission** (à changer) et ce qui est
**réutilisable presque tel quel** (structure, conventions, à ajuster à la marge) :

| Fichier | Rôle | À l'amorçage |
|---|---|---|
| `profile.yml` | identité mission : Jira, Notion, Drive, `key_dates`, équipe | **tout adapter** |
| `pipeline.yml` | livrable → générateur / ton / schéma / cibles ; table `agents` → ton | adapter les cibles et les tons ; structure réutilisable |
| `palette.json` | couleurs de marque + sémantiques + thèmes | **adapter** aux couleurs de la mission |
| `logos/` | logos des entités (schéma d'archi) | **remplacer** par les logos de la mission |
| `projection.yml` | capacité/staff, epics↔pôles, règles de versions, jours ouvrés | adapter staff et mapping epics ; règles réutilisables |
| `archi.yml` | source du schéma d'archi (model-first) | repartir du modèle de la mission |
| `partner-report.yml` | format du CR par partenaire, langue | adapter partenaires et langues ; gabarit réutilisable |
| `partenaires.yml` | partenaires de la mission | **adapter** |
| `notion-topics.yml` | base Sujets : data source, filtre, ton, seuils | adapter data source et filtre ; seuils réutilisables |
| `notion-planning.yml` | report du planning Notion (+ slide) | adapter les cibles Notion |
| `jira-images.yml` | section image, racine des images, règles | adapter racine/section ; règles réutilisables |
| `risks.yml` | registre (fichier + schéma de colonnes) | adapter le chemin du registre ; schéma réutilisable |
| `docs-coherence.yml` | carte des dépendances docs (GATE↔Excel↔PPT↔PNG) | adapter à la cartographie de la mission |
| `routines.yml` | horaires, enchaînements, écritures gardées | adapter horaires et périmètres ; structure réutilisable |
| `activity.yml` | suivi d'activité : transcripts, store, DB privée | adapter la DB Notion privée |

Les champs inconnus au moment de l'amorçage se marquent **`à confirmer`** plutôt que d'être inventés.

## Gabarits génériques

`config/pipeline.example.yml` et `config/profile.example.yml` sont les deux gabarits commentés, vides de
toute valeur de mission. Pour les autres fichiers, l'exemple **est** le profil SINBAD : pas de gabarit
vide en double, on lit `sinbad/` et on copie.
