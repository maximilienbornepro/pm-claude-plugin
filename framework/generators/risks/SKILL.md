---
name: risks
description: Générateur de registre des risques du pm-framework, générique et piloté par la config. Lit le classeur des risques (lecture seule, mapping de colonnes dans profiles/<mission>/risks.yml), rend le registre courant, et définit le flux de mise à jour piloté par formulaire — proposition d'abord, écriture chirurgicale unique ensuite, seulement après validation. Aucune notification.
---

Générateur **risques** du pm-framework. Il porte, en version générique et pilotée par la config, le
flux que SINBAD tient dans sa routine `sinbad-revue-risques` : relire le registre, le confronter à
l'état réel (sujets de suivi, projection), **montrer le registre actualisé**, puis mettre à jour le
fichier **seulement après le « oui » d'un formulaire de validation**. Rien n'est écrit sans ce oui,
et **aucune notification** ne part.

Tout le propre-à-la-mission est dans `profiles/<mission>/risks.yml` (gabarit commenté :
`risks.example.yml`). Changer de mission = remplir ce fichier, jamais toucher au code.

## Ce que le générateur sait faire

- `python3 risks.py <mission>` : lit le classeur et **rend le registre courant** (en-têtes + risques),
  via le seul mapping de colonnes de la config. Aucune coordonnée de cellule n'est en dur.
- `python3 risks.py <mission> --raw` : dump brut `{cellule: valeur}` (contrôle du mapping).
- `python3 risks.py <mission> --propose` : décrit le flux de proposition et **s'arrête sur le
  garde-fou d'écriture** (voir plus bas). Rien n'est écrit.

La localisation du fichier est portable (jamais de chemin propre à un poste) : `$PMF_RISKS_FILE`
(absolu), sinon `$PMF_DRIVE_ROOT` + `file.path`, sinon recherche du motif `file.glob` sous
`~/Library/CloudStorage`.

## Le flux piloté par formulaire (formulaire → proposition → écriture gardée)

1. **Lire le registre** (lecture seule) — `read_register`, via le mapping de la config.
2. **Annexer les sources** (lecture seule) : base de suivi Notion « Sujets »
   (`annexe.notion_sujets_data_source`) et projection Jira (`annexe.jira_projection`, reste par pôle,
   livrabilité V1). Un sujet **Done** baisse ou clôt le risque qu'il porte ; **Bloqued / Todo** sur un
   prérequis le maintient ou le relève ; un sujet critique sans risque fait émerger un nouveau risque.
3. **Proposer** : construire, cellule par cellule, le tableau actualisé — Probabilité et Impact
   (avant → après si ça change), détail court au présent, justification (sujet lié + statut) ;
   lister à part les risques **relevés / baissés / clos / retirés / nouveaux**.
4. **Formulaire de validation** : afficher la proposition et **attendre le OUI explicite en session**.
   Rien n'est écrit sans ce oui. C'est le pendant du formulaire de la routine SINBAD.
5. **Écriture gardée** (seulement après le oui) : voir « Garde-fous Office » ci-dessous.

Dans la passe actuelle, l'écriture n'est **ni implémentée ni exécutée** : `--propose` prouve la lecture
et le rendu, puis s'arrête. Le flag `write.enabled` de la config vaut `false` ; le chemin d'écriture
refuse de partir tant qu'il est à `false`, et même à `true` la fonction s'arrête (garde-fou en dur)
parce que l'écriture se fait en session, pas en autonomie.

## Garde-fous Office (chemin d'écriture, quand il sera activé)

L'écriture passe **toujours** par `framework/harness/onedrive_xlsx.py` (écriture chirurgicale dans le
XML du zip, jamais openpyxl qui détruirait images et mise en forme). Dans l'ordre, en session :

1. **Contrôle de fraîcheur distant** (`lastModifiedDateTime` via le connecteur du Drive) **avant**
   toute écriture : date du jour ou postérieure à la copie locale = quelqu'un est dans le fichier,
   **on n'écrit pas**, on transmet les changements à la personne qui a la main. Ce contrôle n'est pas
   porté par le helper : il se fait en session.
2. **Sauvegarde horodatée** (`backup`) dans le dossier de `write.backup_dir_env` (scratchpad de session).
3. **Écriture chirurgicale** : `set_cells` ne touche que les cellules Probabilité / Impact / Détail,
   `append_row` ajoute une ligne de risque ; styles, fusions et images sont préservés.
4. **Une seule écriture en place** (`save`, inode préservé, jamais `rm`/`mv`), fichier fermé dans Excel.
5. **Comparaison des tailles** locale vs SharePoint quelques minutes après, et alerte en cas d'écart.

Rappels : l'échelle part telle quelle dans le deck GATE (libellés réels du fichier, voir `scale`) ;
pas de référence à des tickets dans les libellés ; détails factuels au présent.

## Faire évoluer via la config

- **Nouvelle colonne** (id, description, owner, catégorie…) : l'ajouter sous `columns:` avec sa lettre ;
  le générateur la lit et l'affiche sans changement de code. Un champ absent reste commenté / « à confirmer ».
- **Autre disposition** (ligne d'en-tête, première/dernière ligne) : ajuster `layout:`.
- **Autre échelle** : adapter `scale.levels` (ordre croissant) et, pour l'affichage, `scale.labels_fr`.
- **Autre classeur / autre mission** : copier `risks.example.yml` en `profiles/<mission>/risks.yml`.

## Ce que ce générateur ne fait jamais

- Il ne modifie ni la base « Sujets » ni une autre page Notion.
- Il n'écrit pas le fichier Office sans validation en session, et jamais s'il a été touché le jour même.
- Il n'envoie ni mail, ni message, ni mention : personne n'est notifié.
