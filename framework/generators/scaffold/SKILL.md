---
name: scaffold
description: Monte l'arborescence d'une mission - dossiers Drive/SharePoint, pages Notion miroir, et (à terme) les fichiers Office standards de chaque dossier. Dry-run par défaut ; création create-si-absent, jamais d'écrasement, jamais de notification.
---

# Générateur scaffold (structure d'une mission)

L'arborescence d'une mission a **trois couches**, pas deux :

1. **Dossiers Drive / SharePoint** - l'ossature (`00 - Conception`, `02 - Project Management/01..18`).
2. **Pages Notion miroir** - une page par dossier de `02 - Project Management`, avec lien vers le dossier
   SharePoint + description courte.
3. **Fichiers Office dans chaque dossier** - les livrables eux-mêmes (le registre des risques, la roadmap,
   le plan de charge, le deck GATE, le plan qualité…). **Ce ne sont pas des dossiers vides.**

Le scaffold monte la **structure** (couches 1 et 2). Le **contenu Office** (couche 3) est produit et tenu
par les **générateurs dédiés** (`risks` → registre xlsx, `gate-deck` → deck pptx, `projection`/`sprint_plan`,
`coherence` qui surveille leurs dépendances), à partir des sources de la mission. Le scaffold peut, en option,
**signaler** quels fichiers Office standards manquent dans un dossier (manifeste `office` du template), et les
créer par **copie d'un modèle** (create-si-absent, sous le garde-fou Office) - étape gardée, jamais d'office.

## Drive (`scaffold_drive.py`)
```
python3 scaffold_drive.py --pm "<02 - Project Management>"            # dry-run : liste les dossiers manquants
python3 scaffold_drive.py --pm "<...>" --apply                        # cree les manquants (mkdir, create-si-absent)
```
Idempotent. `--apply` ne crée que les dossiers absents : **jamais** d'écrasement, de suppression ni de
déplacement (règle Drive consortium). Un dossier ne notifie personne.

## Notion (`scaffold_notion.py`)
```
python3 scaffold_notion.py --pages pages.json --mission <m>                 # dry-run : pages manquantes
python3 scaffold_notion.py --pages pages.json --mission <m> --emit-plan     # + spec de creation (JSON)
```
L'instantané des pages (`--pages`) est produit par Claude via le connecteur (un script ne peut pas l'appeler).
`--emit-plan` **n'écrit pas** : il rend, par page manquante, `{title, parent_root, drive_folder,
body_markdown}`. Le `body_markdown` est un **gabarit** que chaque page porte **à la création** :

- **un lien vers le dossier** (Drive/SharePoint/OneDrive selon `file_store` du profil), **toujours présent** -
  en tête, format `📁 Ouvrir le dossier dans <magasin>` ; s'il n'a pas pu être résolu, un placeholder de lien
  et une entrée « à compléter » le signalent ;
- **« À quoi sert cette page »** : le rôle de la page, en **placeholder** à remplir ;
- **« Contenu attendu »** : placeholders (dont le tableau `Titre | Fichier | Dossier | Contenu`) ;
- **« À compléter pour être legitime »** : une **checklist** de ce qui manque (lien, rôle réel, fichiers clés,
  responsable). Rien n'est inventé : tout reste explicitement à renseigner.

**Claude crée ensuite les pages via le connecteur, UNIQUEMENT** après : (1) validation du contenu,
(2) **test « page jetable »** confirmant qu'aucune notification ne part, (3) création **sous le parent**
`project_management_root`, **jamais à la racine** de l'espace (sortir une page d'un conteneur partagé
notifie tout l'espace).

## Garde-fous (toujours)
- Dry-run par défaut partout ; une écriture = un flag explicite + validation.
- **Aucune notification** : c'est le risque n°1 côté Notion (création/déplacement de page). Test jetable d'abord.
- Create-si-absent et idempotent : on ne recrée ni n'écrase l'existant ; on peut proposer d'ajouter un
  lien/description manquant à une page existante, jamais remplacer.
- Office : création par copie de modèle sous le garde-fou Office (une seule écriture, jamais `rm`/`mv`).
