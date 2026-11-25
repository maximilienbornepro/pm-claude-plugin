---
name: technical-planning
description: Produire ou mettre à jour le PPT « Technical planning » d'une mission (Gantt, slide des échéances toujours synchronisée, slides de situation Sujet / Statut / Situation / Levier / Échéance, tableau des responsabilités) dans le gabarit PowerPoint de l'entreprise, à partir d'une seule source de données (planning.json) alimentée par le suivi des sujets. À utiliser pour « refais le planning technique », « mets à jour le Gantt », « décale tel jalon », « ajoute une ligne au planning », « régénère les slides de situation », ou pour monter ce type de deck sur une nouvelle mission.
argument-hint: "<mission> [ce qui change]"
user-invocable: true
---

# Planning technique (PPT)

Un deck de comité en 4 parties, **toutes calculées depuis une seule source** :

| Slide | Contenu | D'où ça vient |
|---|---|---|
| 1. Gantt | couloirs (équipes / partenaires), barres, jalons, traits verticaux (aujourd'hui, signature, ouverture) | `lanes`, `vlines` de `planning.json` |
| 2. Échéances | deux tableaux Domaine / Élément / Date | **dérivé du Gantt** : jamais saisi, donc jamais désynchronisé |
| 3+. Situation | une slide par groupe de sujets : Domaine, Sujet, Statut, Situation, Levier en cours, Échéance ; titre = message clé | `status` de `planning.json`, rempli depuis le suivi des sujets |
| Fin. Tableaux | responsabilités et charge, RACI résumée… | `tables` de `planning.json` |

Moteur : générateur `planning` (`framework/generators/planning/planning.py`, sans dépendance).
Contrat de données détaillé : `framework/generators/planning/SKILL.md`. Exemple complet :
`framework/generators/planning/planning.example.json`.

## Les sources

1. **`profiles/<mission>/planning.json`** : la source unique du deck (Gantt + situation + tableaux).
2. **Le suivi des sujets** (base Notion « Sujets », ou tout tracker de la mission) : chaque sujet donne une
   ligne de situation. Correspondance :
   - `subject` = titre court du sujet (ce qu'on cherche à obtenir) ;
   - `status` = un des 5 statuts du deck : `OK`, `En cours`, `Prévu`, `À risque`, `En discussion` ;
   - `situation` = le Contexte du sujet, en phrases complètes (une ou deux) ;
   - `lever` = la **prochaine action** (« Qui fait quoi »), obligatoire pour tout statut autre que OK ;
   - `due` = l'échéance (« 27/11 », « à confirmer ») ;
   - `domain` = le couloir du Gantt (Plateforme, Chaîne de traitement, partenaire…).
3. **Le planning de référence en ligne** (le deck publié) : à relire avant toute réécriture, il est
   souvent modifié à la main par d'autres (voir « Déposer »).
4. **Le gabarit** : un PPT de l'entreprise (`template.pptx` + `template.layout` dans `planning.json`).

## Déroulé

1. **Relire l'existant** : `planning.json`, la version en ligne du deck (date et auteur de la dernière
   modification) et les sujets modifiés depuis la dernière génération.
2. **Mettre à jour `planning.json`** selon la demande :
   - une date ou un jalon bouge : modifier l'élément du couloir (la slide des échéances suit seule) ;
   - une ligne de situation : la réécrire depuis le sujet (Contexte → situation, prochaine action → levier) ;
   - le titre de chaque slide = **le message clé** (« On ouvre le 18/12 seulement si… »), jamais un titre
     descriptif ; `subtitle` / `status.subtitle` portent la date de situation (« au JJ/MM »).
   **Toute modification d'une date du planning se signale explicitement** à l'utilisateur.
3. **Générer et contrôler** :
   ```bash
   python3 framework/pm.py run planning <mission> --pptx /tmp/planning.pptx
   ```
   (gabarit pris dans `planning.json` ; sinon `--pptx-template gabarit.pptx --layout "<mise en page>"`).
   Les contrôles s'affichent : dates hors fenêtre, fin avant début, doublons, statut inconnu, **levier
   manquant**, et une alerte si une slide de situation déborde (la scinder en deux).
4. **Montrer** : aperçus PNG des slides (macOS : `qlmanage -t -s 1400 -o <dossier> <fichier.pptx>` sur
   une copie d'une seule slide) et liste de ce qui a changé (dates, lignes, titres).
5. **Déposer** seulement après accord :
   - fichier en ligne modifié par quelqu'un d'autre depuis la dernière génération : on ne l'écrase pas ;
     on reporte les changements en ligne (PowerPoint pour le web, Rechercher / Remplacer) ou on transmet ;
   - sinon : **une seule écriture** du fichier dans le dossier synchronisé, puis comparer la taille locale
     et en ligne.

## Exemples de demandes

- « Refais le planning technique au 02/12 à partir des sujets. »
- « Le pentest est décalé au 08/12 : mets à jour le Gantt et les échéances. »
- « Ajoute dans le couloir KSAT un jalon "Endpoint de prod" le 30/11. »
- « La reprise par l'infogérant passe à risque : mets à jour la slide de situation. »
- « Donne aux slides de situation des titres qui disent le message, pas le sujet. »
- « Monte ce planning pour la mission X avec le gabarit de l'entreprise Y. »

## Monter ce deck sur une nouvelle mission

1. Copier `framework/generators/planning/planning.example.json` dans `profiles/<mission>/planning.json`.
2. Déposer un PPT de l'entreprise dans `profiles/<mission>/templates/` et renseigner
   `"template": {"pptx": "templates/<fichier>.pptx", "layout": "<mise en page>"}` ; pour connaître les
   mises en page, lancer avec un nom bidon : la liste s'affiche.
3. Remplir les couloirs, les traits (`vlines`), la situation depuis le suivi des sujets, les tableaux.
4. Générer, relire, déposer (déroulé ci-dessus).

## Règles de rédaction

- Un partenaire = une ligne (jamais « les partenaires » en bloc).
- Situation en phrases complètes ; levier = qui fait quoi ; inconnu = « à confirmer ».
- Statuts : exactement les 5 libellés du deck (couleurs fixes et distinctes).
- Pas de tiret cadratin ; ne jamais citer « la slide de X » comme source.
