# Le déroulé commun d'écriture Office (OneDrive ↔ SharePoint)

Tout générateur qui écrit un fichier Office d'un OneDrive synchronisé (xlsx, pptx, docx) suit CE
déroulé, écrit ici **une seule fois** (A2). Chaque générateur garde une ligne qui le nomme et renvoie
ici, plus ses paramètres propres (quel fichier, quelles cellules / slides). Rien ne change dans ce que
fait un générateur : seul l'endroit où la procédure est écrite a bougé.

Les garde-fous mécaniques sont tenus par le hook `framework/hooks/garde_office.py` (refuse toute écriture
Office brute : `cat >`, `rm`/`mv`, openpyxl, `.save()`) et, pour le xlsx, par le helper
`framework/harness/onedrive_xlsx.py` (écriture chirurgicale dans le XML du zip, jamais openpyxl qui
détruirait images et mise en forme).

**Rien n'est écrit sans validation.** Le générateur ne fait que produire le CONTENU (lecture seule) ;
l'écriture se fait en session, après avoir montré le contenu exact (ou un `--dry-run`) et reçu le oui.

Dans l'ordre, en session :

1. **Fraîcheur distante AVANT toute écriture** (`lastModifiedDateTime` via le connecteur du Drive) :
   date du jour ou postérieure à la copie locale = quelqu'un est dans le fichier → **on n'écrit pas**,
   on transmet les changements à la personne qui a la main. La copie locale étant en retard, les
   coordonnées de cellule relevées dessus sont de toute façon fausses. (Contrôle en session, pas dans
   le helper.)
2. **Préparer sur une COPIE** (scratchpad de session), jamais directement dans le dossier synchronisé.
3. **Sauvegarde horodatée** de l'existant dans le scratchpad de session (pas de dossier de sauvegardes
   permanent dans le projet).
4. **Montrer** le contenu / le `--dry-run`, puis écrire **seulement après le oui**.
5. **Une seule écriture EN PLACE** (inode préservé, écriture chirurgicale ; **jamais** `rm` puis copie,
   jamais `mv` : un fichier Office recréé perd son identifiant SharePoint et cesse de se synchroniser).
   Fichier fermé dans Office. Jamais d'enregistrements successifs dans le dossier synchronisé.
6. **Comparer la taille** locale vs SharePoint quelques minutes après, et **prévenir en cas d'écart**
   (la synchro peut rester bloquée à l'envoi).

Jamais de suppression ni de déplacement d'un fichier synchronisé. (Côté mission, ce déroulé peut être
porté par un skill dédié d'édition OneDrive ; ici c'est la version framework, générique.)
