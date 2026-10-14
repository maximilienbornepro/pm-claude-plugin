---
name: slide-planning
description: Routine config-driven - reporte le planning du tracker sur une slide du deck, en ecriture en place avec sauvegarde et garde-fou anti-ecrasement. Sens unique tracker -> deck. Aucune notification.
schedule: config   # voir routines.yml > routines.slide-planning.schedule (manuel par defaut)
---

Reporte le planning depuis le tracker de suivi sur une slide du deck. Reponds dans la langue du profil (`profile.yml > lang`). **Le sens est toujours tracker -> deck**, jamais l'inverse.

Tout le propre-a-la-mission (base du planning, deck cible, script, table de traduction des libelles, slide a toucher) vit dans **`profiles/<mission>/routines.yml`**, cle `routines.slide-planning`. Ce SKILL porte le deroule et les garde-fous.

**Racine projet** : resolue de facon portable (voir `routines.yml > project_root_env`). Le deck se resout par **glob** (`reads.deck_glob` : le dossier Drive contient un horodatage qui varie d'un poste a l'autre). Verifie qu'un seul fichier correspond ; sinon, arrete-toi et liste les candidats.

## Ce qu'elle enchaine

`chains: []` - pas de generateur en lecture seule. La routine lit le planning du tracker et ecrit une seule slide du deck via le script de mission (`reads.script`) et le harness Office du framework. Elle est proche de la famille `gate-deck` (ecriture pptx chirurgicale), mais limitee a une slide.

## Etape 1 : lire le planning dans le tracker

Via le connecteur, sur `reads.tracker_data_source` : les lignes du planning (libelle, groupe, periode debut/fin). Ecarte les lignes marquees a supprimer et les sous-elements (parent renseigne). Separe les jalons (groupe de dates) des activites. **Traduis les libelles** avec la table de `reads.label_table_skill` ; un libelle absent de la table reste tel quel et est signale.

## Etape 2 : ecrire le JSON d'entree du script

Format attendu : `{"activites": [{"nom","debut","fin"}], "jalons": [{"nom","date"}]}`. Une activite sans dates garde son seul `nom`.

## Etape 3 : sauvegarder, puis verifier qui a la main

Copie le deck dans `backup_dir_env` sous un nom horodate et **verifie que le SHA-256 de la copie est identique a l'original**. Puis regarde la date de modification du deck : **si elle est posterieure a la derniere sauvegarde, quelqu'un a touche le fichier depuis le dernier passage -> arrete-toi**, produis le fichier dans un chemin temporaire, livre-le, et explique que l'ecriture en place n'a pas ete faite pour ne pas ecraser le travail de quelqu'un. Ne force jamais.

## Etape 4 : produire, puis ecrire en place

Lance `reads.script` (`--deck <le deck> --data <le json> --out <temp>`). Le script refuse d'ecrire si l'etalonnage du calendrier a change, si un separateur traverse un libelle, ou si une autre entree d'archive que `reads.target_slide` est modifiee. S'il sort en erreur, arrete-toi et rapporte le message tel quel.

Ensuite, ecriture **en place** et rien d'autre : `cat <temp> > <le deck>`. **Jamais `cp` vers la cible, jamais `mv`, jamais `rm` puis copie** : un fichier Office supprime puis recree perd son identifiant d'element SharePoint et cesse de se synchroniser. Releve l'inode (`stat -f %i`) avant et apres : il doit etre identique. Une seule ecriture.

## Etape 5 : rapporter

Quatre lignes maximum : nombre d'activites et de jalons poses ; activites tronquees et jalons hors calendrier avec leurs dates ; confirmation que l'inode est inchange ; toute anomalie (script en echec, deck modifie par un autre, libelle sans traduction, deck ouvert dans l'editeur).

## Garde-fous

- **`notifies: none`** : pas de mail, pas de message, pas de commentaire.
- **Sens unique tracker -> deck.** Si les deux different, le tracker fait foi et on le signale, on ne corrige pas le tracker depuis la slide.
- **Une seule slide change** (`reads.target_slide`) ; le script le verifie.
- Ne modifie rien dans le tracker : lecture seule sur la base.
- Respecte chaque `routines.yml > ...slide-planning.writes[].guard`.
