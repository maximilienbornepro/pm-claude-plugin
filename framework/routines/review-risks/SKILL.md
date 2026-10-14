---
name: revue-risques
description: Routine config-driven - relit le registre de risques, le confronte aux sujets de suivi et a la projection de livrabilite, montre le registre actualise, puis met a jour le fichier en place apres validation en seance. Aucune notification.
schedule: config   # voir routines.yml > routines.revue-risques.schedule (manuel par defaut ; planifiable)
---

Routine de revue des **risques**. Elle relit le registre, le confronte a l'etat reel du projet, **montre le registre actualise dans la conversation**, puis, apres confirmation en seance, **met a jour le fichier en place** avec les garde-fous ci-dessous. Elle ne touche jamais le tracker de suivi et n'envoie aucune notification. Reponds dans la langue du profil (`profile.yml > lang`).

Tout le propre-a-la-mission (classeur, mapping des colonnes, echelle, sources annexees) vit dans **`profiles/<mission>/risks.yml`** (le generateur `risks` ne lit que lui) et dans **`routines.yml > routines.revue-risques`**. Ce SKILL porte la methode et les garde-fous.

**Racine projet** : resolue de facon portable (voir `routines.yml > project_root_env`). Jamais de chemin propre a un poste.

## Ce qu'elle enchaine

`chains: [risks, projection]` - deux generateurs du framework en lecture seule :

- **`risks`** lit le registre selon `risks.yml` (chemin, colonnes `label/probability/impact/detail`, echelle). Il ne fait que lire et proposer : son `write.enabled` reste `false`.
- **`projection`** fournit la livrabilite V1 (reste par pole, chemin critique) qui sert le risque de livraison.

## Etape 1 : lire le registre (lecture seule)

Via le generateur `risks` et `risks.yml`. Lecture en decompressant le XML du classeur (`sharedStrings.xml` + la feuille), jamais via openpyxl (il detruirait dessins et mise en forme).

## Etape 2 : lire les sujets et l'etat projet

- Base de suivi (`routines.yml > ...revue-risques.reads.sujets_data_source`) : un sujet termine baisse ou clot son risque ; bloque ou non demarre sur un prerequis le maintient ou le releve ; un sujet nouveau peut faire emerger un risque.
- Projection (generateur `projection`) : livrabilite V1.
- Absences connues (`reads.absences`) pesant sur la fenetre avant la mise en service.

## Etape 3 : reevaluer chaque risque

Rapprocher chaque ligne du ou des sujets qui la portent et ajuster : sujet termine -> baisse/clos ; en cours -> maintien, detail au present ; bloque/non demarre sur un prerequis -> releve ; risque caduc -> proposer de le retirer ; sujet critique sans risque -> proposer un nouveau risque.

## Etape 4 : rendre le registre actualise (propositions)

Afficher dans la conversation le tableau complet actualise : par risque, Probabilite et Impact (avant -> apres si ca change), un detail court au present, la justification (sujet lie et statut). Lister a part les risques releves, baisses/clos, retires, nouveaux. Details factuels, au present, sans nom de personne dans le libelle publie (le registre part dans le deck), echelle de `risks.yml > scale` uniquement.

## Etape 5 : mettre a jour le fichier (apres confirmation en seance)

Montrer d'abord le tableau (etape 4) et attendre le **go de l'utilisateur dans la session**. Ensuite, mise a jour via le harness Office du framework (`onedrive_xlsx.py`), avec **toutes** les gardes de `routines.yml > ...revue-risques.writes[].guard` :

- **Fraicheur SharePoint d'abord** : date du jour ou posterieure a la copie locale = quelqu'un est dedans, **on n'ecrit pas**, on transmet a la personne qui a la main.
- **Sauvegarde horodatee** avant d'ecrire (`backup_dir_env`).
- **Ecriture chirurgicale dans le XML**, uniquement les cellules Probabilite/Impact/Detail et les lignes de risque ajoutees ou retirees.
- **Une seule ecriture** en place (jamais `rm` puis copie, jamais `mv`), fichier ferme.
- **Comparer ensuite la taille locale et SharePoint** et prevenir en cas d'ecart.

## Ce que cette routine ne fait jamais

- **`notifies: none`** : ni mail, ni message, ni mention ; personne n'est notifie.
- Elle ne modifie pas le tracker de suivi ni une autre page.
- Elle n'ecrit pas le fichier Office sans confirmation en seance, et jamais s'il a ete touche le jour meme.
