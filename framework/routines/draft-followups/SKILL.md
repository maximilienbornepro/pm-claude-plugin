---
name: draft-followups
description: "Prépare les relances pour obtenir les réponses attendues sur les sujets de suivi : brouillon de mail pour un partenaire externe (.eml local non envoyé, ouvert en rédaction), message Slack à copier pour un interne ; formulaire modifiable au clic. Écrit : local (.eml), mail-draft (fenêtre de rédaction ouverte, jamais envoyée). Aucune notification."
meta:
  kind: routine
  scope: mission
  schedule: config          # routines.yml > routines.<projet>-draft-followups.schedule (manuel par défaut)
  chains: []
  writes: [local, mail-draft]
  validation: form
  default_mode: dry-run     # rien n'est créé avant le bouton « Créer les brouillons validés »
  output: html-widget
  notifies: none
  mcp_deps: [notion, m365, claude-in-chrome]
  status: stable
---

# draft-followups - brouillons de relances

**Rien ne part : aucun mail envoyé, aucun brouillon créé côté serveur, aucun message posté.** Le
connecteur mail n'a que des droits de lecture ; les mails sont des fichiers `.eml` locaux marqués non
envoyés, ouverts en fenêtre de rédaction, que l'utilisateur relit et envoie lui-même ; les messages
Slack sont rendus en texte, à copier-coller. Réponds dans la langue du profil (`profile.yml > lang`).

Elle est **indépendante** de `review-topics` : elle ne modifie pas la base de suivi, ne touche pas aux
risques.

## Déclencheur et modes

Manuel par défaut. Toujours avec le formulaire (étape 4) ; rien n'est créé sans validation.

## Entrées

Clé d'instance `routines.<projet>-draft-followups` ; à défaut, l'ancienne clé (voir `framework/routines/README.md`, colonne « Anciennement »).

Instance `routines.<projet>-draft-followups` de `profiles/<mission>/routines.yml` :

- `reads.sujets_data_source`, `reads.filtre` (ex. le seul suivi du rôle de l'utilisateur),
  `reads.transcriptions_window_days` ;
- `channels.mail` : `partners[]` (et leur `lang`), `cc_rules`, `subject_format`, `out_dir` ;
- `channels.slack.internes` ;
- `voice_skill` : skill de voix (registre mail et section Slack).

Profil : `transcripts_sources` (toutes, Omi compris). Racine projet : `routines.yml >
project_root_env`, puis replis.

## Enchaînements

Aucun générateur. Script local : `framework/routines/draft-followups/creer_eml.py`.

## Déroulé

0. **Préflight** : `python3 framework/pm.py run preflight <mission>`, puis `get_me` (`mail` / tenant ==
   profil) : les brouillons s'ouvrent sur le compte de la mission. Identité différente : on rend les
   textes à copier, sans ouvrir de fenêtre de rédaction.
1. **Lire** (lecture seule) les réponses attendues :
   - **base de suivi**, sujets non terminés, filtre `reads.filtre`. On retient les actions dont **la
     réponse doit venir de quelqu'un d'autre** : partenaire (`channels.mail.partners`) ou interne
     (`channels.slack.internes`), et les questions ouvertes du corps (« à confirmer », « Confirmer... »,
     « Obtenir de... ») ;
   - **mails depuis la dernière passe** (recherche puis lecture des fils utiles) : **ne pas proposer une
     relance déjà faite ou déjà répondue**. Vérifier aussi les envoyés : une relance reprend la suite du
     dernier message, elle ne le répète pas ;
   - **transcriptions récentes** pour les engagements pris en réunion.
2. **Rédiger** une relance par destinataire et par sujet. **Le canal dépend du destinataire** :
   - **Partenaire externe : un brouillon de mail.** Un brouillon = un fil : `RE: <objet du fil>` si un
     fil existe, sinon `channels.mail.subject_format`. Destinataires **relevés dans les en-têtes des
     mails déjà échangés** (À et Cc du fil), jamais devinés ; introuvable : la carte le dit
     (« destinataire à confirmer ») et propose le plus probable. Ajouter les copies imposées
     (`channels.mail.cc_rules`). Langue par partenaire. Ton : `voice_skill`, format court du CR
     partenaire (une phrase de contexte, les questions numérotées, l'échéance explicite, la formule de
     fin). Rien de confidentiel interne (débats internes, programmes internes, juridique).
   - **Interne : un message Slack** à copier-coller, pas de mail. Registre Slack du `voice_skill` :
     minuscule en début de message, phrases courtes, pas de liste à puces, pas de gras, pas de titre ;
     connecteurs familiers admis. Prénom du destinataire en texte simple en tête, **jamais de mention `@`
     générée**. Une ou deux questions, l'échéance dans la phrase. Plusieurs sujets pour la même personne
     peuvent tenir dans un seul message.
   - Partout : tiret classique, jamais de tiret cadratin ; aucune décision inventée, ce qui n'est pas sûr
     se formule en question.
3. **Proposer** : un widget interactif, deux groupes de cartes, **Mails partenaires** (`M<n>`) puis
   **Slack interne** (`S<n>`).
   - Titre `M<n>. <Destinataire> - <sujet>` ou `S<n>. <Prénom> - <sujet>` ; en petit, le sujet de suivi
     et la source.
   - Mail : brouillon complet (`À :`, `Cc :`, `Objet :`, ligne vide, corps). Slack : le message seul.
     Zone en lecture, **modifiable au clic** (Appliquer / Annuler, badge « Modifié »). Carte Slack :
     bouton « Copier ».
   - Technique : cartes construites une seule fois (pas de re-rendu au clic), écouteur délégué, état
     choisi forcé en style inline avec un libellé « Validé / Écarté » et un compteur en tête.
4. **Valider** : boutons Oui / Non, puis « Créer les brouillons validés » qui renvoie les réponses et le
   texte complet des cartes modifiées. **C'est le texte modifié qui fait foi.** Rien n'est créé au clic.
5. **Écrire** les relances validées :
   - **Slack** : rien à créer. Rendre chaque message validé dans son propre bloc de code, précédé du
     destinataire.
   - **Mails** (nouveau fil) : pour chaque oui, avec le texte final,
     `python3 framework/routines/draft-followups/creer_eml.py --dir <channels.mail.out_dir>/<AAAA-MM-JJ> --file <M1.txt> ...`
     écrit un `.eml` par brouillon (`X-Unsent: 1`, UTF-8, expéditeur vide) gardé en copie locale, puis
     ouvre chaque message dans le client mail en fenêtre de rédaction via un lien `mailto:` (expéditeur
     = compte de l'utilisateur, brouillon enregistré à la fermeture) ; jamais le `.eml` ouvert
     directement (pas d'expéditeur, pas de brouillon). Aucune pièce jointe : si le texte en annonce une,
     le signaler.
   - **Relance dans un fil existant (`RE:`)** : un `mailto:` ouvre toujours un **nouveau fil** ; pas de
     `mailto:` pour un `RE:` (doublon dans Brouillons). Repérer le **dernier message du fil**
     (expéditeur, date, `webLink`) et proposer 1) la voie manuelle : corps copié dans le presse-papiers
     (`pbcopy`), l'utilisateur ouvre ce message, « Répondre à tous », colle, ferme (brouillon enregistré
     dans le fil), un message à la fois ; 2) la voie navigateur : Outlook web via Claude in Chrome
     (`webLink`, « Répondre à tous », coller, fermer sans envoyer), **seulement si Chrome est déjà
     connecté au bon compte** ; on ne se connecte jamais à sa place.
6. **Vérifier** : restituer la liste des brouillons, leurs destinataires et les chemins `.eml`.

## Sortie

Formulaire interactif (widget HTML), puis blocs Slack à copier et liste des brouillons mail ouverts.

## Garde-fous

- **`notifies: none`** : jamais envoyer, transférer ou répondre à un mail ; jamais créer un brouillon
  dans la boîte via le connecteur ; jamais poster sur Slack ou Teams ; jamais mentionner, commenter,
  inviter.
- Ne modifie ni le tracker, ni Jira, ni le Drive, ni SharePoint.

## Décisions datées

- Anciennement nommée `brouillons-relances` (le script vit désormais dans
  `framework/routines/draft-followups/`).
- Le style par défaut des boutons masquait une classe CSS (« Oui » semblait sans effet) : d'où l'état
  forcé en style inline.
