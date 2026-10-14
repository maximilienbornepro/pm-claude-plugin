---
name: brouillons-relances
description: Routine config-driven - prepare les relances pour obtenir les reponses attendues sur les sujets de suivi. Partenaire externe -> brouillon de mail (.eml non envoye, destinataires releves dans les fils). Interne -> message Slack a copier-coller, a la voix du TPM. Formulaire modifiable au clic ; rien n'est envoye ni poste. Aucune notification.
schedule: config   # voir routines.yml > routines.brouillons-relances.schedule (manuel par defaut)
---

Routine de **relances**. Reponds dans la langue du profil (`profile.yml > lang`). **Rien ne part : aucun mail
envoye, aucun brouillon cree cote serveur, aucun message poste.** Le connecteur mail n'a que des droits de lecture ;
les mails sont des fichiers `.eml` locaux marques non envoyes, que l'utilisateur ouvre, relit et envoie lui-meme ;
les messages Slack sont rendus en texte, a copier-coller.

Elle est **independante** de `revue-sujets` : elle ne modifie pas la base de suivi, ne touche pas aux risques.

Tout le propre-a-la-mission (base de suivi, partenaires et leur langue, membres internes, copies imposees, skill
de voix, dossier de sortie) vit dans **`routines.yml > routines.brouillons-relances`**. Ce SKILL porte la methode.

**Racine projet** : resolue de facon portable (voir `routines.yml > project_root_env`).

## Etape 1 : reperer les reponses attendues (lecture seule)

- **Base de suivi** (`reads.sujets_data_source`), sujets non termines, filtre `reads.filtre` (ex. suivi TPM
  uniquement). On retient les actions dont **la reponse doit venir de quelqu'un d'autre** : partenaire
  (`channels.mail.partners`) ou interne (`channels.slack.internes`), et les questions ouvertes du corps
  (« a confirmer », « Confirmer... », « Obtenir de... »).
- **Mails depuis la derniere passe** (recherche mail puis lecture des fils utiles) : **ne pas proposer une relance
  deja faite ou deja repondue**. Verifier aussi les envoyes : une relance reprend la suite du dernier message, elle
  ne le repete pas.
- **Transcriptions recentes** (`reads.transcriptions_window_days`) pour les engagements pris en reunion.

## Etape 2 : rediger une relance par destinataire et par sujet

**Le canal depend du destinataire** :

- **Partenaire externe** : un **brouillon de mail**.
  - Un brouillon = un fil : `RE: <objet du fil>` si un fil existe, sinon `channels.mail.subject_format`.
  - Destinataires **releves dans les en-tetes des mails deja echanges** (A et Cc du fil), jamais devines.
    Introuvable : la carte le dit (« destinataire a confirmer ») et propose le plus probable. Ajouter les copies
    imposees (`channels.mail.cc_rules`).
  - Langue par partenaire (`channels.mail.partners[].lang`). Ton : voix du TPM (`voice_skill`), format court du
    CR partenaire : une phrase de contexte, les questions numerotees, l'echeance explicite, la formule de fin.
  - Rien de confidentiel interne dans un mail partenaire (debats internes, programmes internes, juridique).
- **Interne** : un **message Slack** a copier-coller, pas de mail.
  - Registre Slack du skill de voix (`voice_skill`, section Slack) : minuscule en debut de message, phrases
    courtes, pas de liste a puces, pas de gras, pas de titre ; connecteurs familiers admis.
  - Prenom du destinataire en texte simple en tete, **jamais de mention `@` generee** (l'utilisateur la pose
    lui-meme s'il le veut). Une ou deux questions, l'echeance dans la phrase. Pas d'objet ni de formule de mail.
  - Plusieurs sujets pour la meme personne peuvent tenir dans un seul message.

Partout : tiret classique, jamais de tiret cadratin ; aucune decision inventee, ce qui n'est pas sur se formule en
question.

## Etape 3 : le formulaire (toujours)

Un widget interactif, deux groupes de cartes : **Mails partenaires** (`M<n>`) puis **Slack interne** (`S<n>`).

- Titre `M<n>. <Destinataire> - <sujet>` ou `S<n>. <Prenom> - <sujet>` ; en petit, le sujet de suivi et la source.
- Mail : brouillon complet (`A :`, `Cc :`, `Objet :`, ligne vide, corps). Slack : le message seul.
  Zone en lecture, **modifiable au clic** (Appliquer / Annuler, badge « Modifie »). Carte Slack : bouton « Copier ».
- Boutons Oui / Non ; bouton final « Creer les brouillons valides » qui renvoie les reponses et le texte complet
  des cartes modifiees. **C'est le texte modifie qui fait foi.** Rien n'est cree au clic.
- Technique : cartes construites une seule fois (pas de re-rendu au clic), ecouteur delegue, etat choisi force
  en style inline avec un libelle « Valide / Ecarte » et un compteur en tete (le style par defaut des boutons
  masque une classe CSS : « Oui » semblait sans effet).

## Etape 4 : produire les relances validees

- **Slack** : rien a creer. Rendre chaque message valide (texte final) dans son propre bloc de code, precede du
  destinataire, pour un copier-coller direct.
- **Mails** : pour chaque oui, avec le texte final :
  `python3 framework/routines/brouillons-relances/creer_eml.py --dir <channels.mail.out_dir>/<AAAA-MM-JJ> --file <M1.txt> ...`
  qui ecrit un `.eml` par brouillon (`X-Unsent: 1`, UTF-8, expediteur vide) garde en copie locale, puis ouvre chaque message dans le client mail en fenetre de redaction via un lien `mailto:` (expediteur = compte de l'utilisateur, brouillon enregistre a la fermeture) ; jamais le .eml ouvert directement (pas d'expediteur, pas de brouillon).
  Aucune piece jointe : si le texte en annonce une, le signaler. Restituer la liste et les destinataires.
- **Relance dans un fil existant (`RE:`)** : un `mailto:` ouvre toujours un **nouveau fil**, il ne se rattache pas.
  Le nouvel Outlook ne se pilote pas (pas d'AppleScript) et le connecteur mail est en lecture seule. Pour ces
  brouillons : reperer le **dernier message du fil** (expediteur, date, `webLink`) et proposer a l'utilisateur
  1) la voie manuelle : corps copie dans le presse-papiers (`pbcopy`), il ouvre ce message, « Repondre a tous »,
     colle, ferme (brouillon enregistre dans le fil) ; un message a la fois ;
  2) la voie navigateur : Outlook web via Claude in Chrome (`webLink` du dernier message, « Repondre a tous »,
     coller, fermer sans envoyer), **seulement si Chrome est deja connecte au bon compte** ; on ne se connecte
     jamais a sa place.
  Pas de `mailto:` pour un `RE:` (doublon dans Brouillons).

## Ce que cette routine ne fait jamais

- **`notifies: none`** : envoyer, transferer ou repondre a un mail ; creer un brouillon dans la boite via le
  connecteur ; poster sur Slack ou Teams ; mentionner, commenter, inviter.
- Modifier le tracker, Jira, le Drive ou SharePoint.
