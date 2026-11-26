---
name: review-risks
description: "Relit chaque registre de risques, le confronte aux sujets de suivi et à la projection de livrabilité, montre le registre actualisé, puis met à jour le fichier en place après validation en séance. Écrit : office (registre, après oui). Aucune notification."
meta:
  kind: routine
  scope: mission
  schedule: config          # routines.yml > routines.<projet>-review-risks.schedule (manuel par défaut ; planifiable)
  chains: [risks, projection]
  writes: [office]
  validation: chat
  default_mode: dry-run     # propositions seulement tant que le oui n'est pas donné
  output: chat-md
  notifies: none
  mcp_deps: [m365]
  status: stable
---

# review-risks - revue du registre des risques

Elle relit **chaque registre déclaré dans `risks.yml > registres`**, le confronte à l'état réel du
projet, **montre le registre actualisé dans la conversation**, puis, après confirmation en séance,
**met à jour chaque fichier en place** avec les garde-fous ci-dessous. Elle ne touche jamais le tracker
de suivi. Réponds dans la langue du profil (`profile.yml > lang`).

## Déclencheur et modes

- Manuel (ou planifiée), ou **enchaînée par `review-topics`** pour répercuter les sujets qui viennent de
  changer.
- Sans le oui en séance, la routine s'arrête à l'étape 4 (propositions).

## Entrées

Clé d'instance `routines.<projet>-review-risks` ; à défaut, l'ancienne clé (voir `framework/routines/README.md`, colonne « Anciennement »).

- `profiles/<mission>/risks.yml` (le générateur `risks` ne lit que lui) : `registres` (chemin, mapping
  de colonnes `label/probability/impact/detail`, plus `mitigation/owner` s'ils existent), `scale`.
- Instance `routines.<projet>-review-risks` : `reads.sujets_data_source`, `reads.absences`,
  `writes[].guard`, `backup_dir_env`.
- Racine projet : `routines.yml > project_root_env`, puis replis. Jamais de chemin propre à un poste.

**Plusieurs registres** (ex. BUILD et RUN) : tous ceux de `risks.yml > registres`, traités dans la même
passe (montrer, valider, écrire), chacun avec les mêmes garde-fous Office. Pour un registre dont les
colonnes sont `a_confirmer`, **lire la ligne d'en-tête du classeur avant d'écrire** et mapper depuis les
libellés lus. Ne jamais inventer une position de colonne.

## Enchaînements

`chains: [risks, projection]` : deux générateurs en lecture seule.

- **`risks`** lit chaque registre. Il ne fait que lire et proposer : son `write.enabled` reste `false`.
- **`projection`** fournit la livrabilité V1 (reste par pôle, chemin critique) qui sert le risque de
  livraison.

## Déroulé

0. **Préflight** : `python3 framework/pm.py run preflight <mission>`, puis `get_me` : `mail` / tenant ==
   profil. BLOQUANT ou identité différente : on s'arrête aux propositions (étape 4). L'écriture reste
   sous `drive.root` et sur le bon `web_site`.
1. **Lire le registre** : via `python3 framework/pm.py run risks <mission>`. Lecture en décompressant le
   XML du classeur (`sharedStrings.xml` + la feuille), jamais via openpyxl (il détruirait dessins et mise
   en forme).
2. **Lire les sujets et l'état projet** :
   - base de suivi (`reads.sujets_data_source`) : un sujet terminé baisse ou clôt son risque ; bloqué ou
     non démarré sur un prérequis le maintient ou le relève ; un sujet nouveau peut faire émerger un
     risque ;
   - projection : `python3 framework/pm.py run projection <mission>` (livrabilité V1) ;
   - absences connues (`reads.absences`) pesant sur la fenêtre avant la mise en service.
3. **Réévaluer chaque risque** : rapprocher chaque ligne du ou des sujets qui la portent ; sujet terminé
   -> baisse / clos ; en cours -> maintien, détail au présent ; bloqué / non démarré sur un prérequis ->
   relevé ; risque caduc -> proposer de le retirer ; sujet critique sans risque -> proposer un nouveau
   risque.
4. **Proposer** : afficher dans la conversation le tableau complet actualisé : par risque, Probabilité et
   Impact (avant -> après si ça change), un détail court au présent, la justification (sujet lié et
   statut). Lister à part les risques relevés, baissés / clos, retirés, nouveaux. Détails factuels, au
   présent, sans nom de personne dans le libellé publié (le registre part dans le deck), échelle de
   `risks.yml > scale` uniquement.
5. **Valider** : attendre le **go de l'utilisateur dans la session**.
6. **Écrire** via le harness Office (`framework/harness/onedrive_xlsx.py`), avec **toutes** les gardes de
   `writes[].guard` :
   - **fraîcheur SharePoint d'abord** : date du jour ou postérieure à la copie locale = quelqu'un est
     dedans, **on n'écrit pas**, on transmet à la personne qui a la main ;
   - **sauvegarde horodatée** avant d'écrire (`backup_dir_env`) ;
   - **écriture chirurgicale dans le XML**, uniquement les cellules Probabilité / Impact / Détail et les
     lignes de risque ajoutées ou retirées ;
   - **une seule écriture** en place (jamais `rm` puis copie, jamais `mv`), fichier fermé.
7. **Vérifier** : comparer la taille locale et SharePoint, et prévenir en cas d'écart.

## Sortie

Le registre actualisé (Markdown) dans la conversation, puis ce qui a été écrit, par registre.

## Garde-fous

- **`notifies: none`** : ni mail, ni message, ni mention ; personne n'est notifié.
- Elle ne modifie pas le tracker de suivi ni une autre page.
- Elle n'écrit pas le fichier Office sans confirmation en séance, et jamais s'il a été touché le jour
  même.
