---
name: cr-partenaire
description: Rend le mail de suivi apres un call partenaire (KSAT en anglais, Airbus en francais), au format valide. RENDU TEXTE uniquement, JAMAIS d'envoi ni de brouillon. Le fond vient d'un JSON (transcription + sujets) ; ce generateur ne fait que la mise en forme.
meta:
  produces: partner-mail
  consumes: [transcripts]
  mcp_deps: [notion]
  cost: light
  status: stable
---

Mail de suivi apres un call partenaire. **Langue par partenaire** (config de mission) : KSAT **anglais**,
Airbus **francais**, systematiquement. Le generateur **ne fait que la mise en forme** : le fond (sujets,
situations, prochaines etapes, jalons) vient d'un JSON produit par Claude depuis la transcription (lecteur
`generators/transcripts/`) et les sujets ouverts.

## Format (validé)

Objet · intro courte · **un point par sujet** (titre en gras, situation en une ligne, **une seule**
prochaine etape avec le **jalon en gras**) · conclusion · signature. Un sujet clos : « Next step: none,
this topic is closed. » / « Prochaine étape : aucune, ce point est clos. »

## Usage

```bash
python3 cr_partenaire.py --input call.json [--mission sinbad]
```

JSON : `{partner, meeting, date, intro?, closing?, points:[{title, situation, next_step, deadline} | {title, situation, closed:true}]}`.
Config de mission : `profiles/<mission>/cr_partenaire.yml` (langues, intro/closing par langue, signature).

## Garde-fous

- **RIEN n'est envoye** : pas de mail, pas de brouillon, pas de post Slack. On rend le texte, l'utilisateur
  l'envoie. (Voir `framework/NOTIFICATIONS.md` : envoyer un mail notifie -> jamais.)
- **Ne rien inventer** : une date deduite ou un nom incertain se signalent hors du mail.
- Un seul « next step » par sujet, le plus proche ; jalon en gras.

## Ce qu'on met, ce qu'on laisse (regles SINBAD)
- On met les sujets du call ou il y a une situation a acter ou une action attendue, y compris ceux qu'on clot.
- On **laisse** ce que porte le chef de projet client / le juridique (contrat, restrictions legales) et notre
  cuisine interne ; on le signale a l'utilisateur hors du mail.
- On **remercie nommement** quiconque a livre (« Merci David pour l'accord juridique »).
- Le fond vient de la **transcription** (pas du resume automatique, qui se trompe sur qui fait quoi), plus
  les sujets ouverts et les mails recus depuis le dernier call.

## Brouillons Outlook (uniquement sur demande explicite)
Par defaut : texte rendu dans la conversation. Si l'utilisateur demande « cree le brouillon » :
- **reponse a tous dans le fil existant** (garde l'historique et les destinataires), sinon nouveau mail avec
  le contact technique en A et le referent interne en copie ;
- jamais d'envoi ; un brouillon qui cite un message avec logo doit etre envoye depuis Outlook ;
- pour modifier un brouillon de reponse, on le **recree** (une mise a jour remplace aussi la citation) puis on
  met l'ancien a la corbeille (recuperable) ;
- configuration technique (URL, payload JSON public) : la recopier telle que fournie, ne jamais y mettre de
  secret ; annoncer les pieces a venir avec leur date (« deux fichiers lundi 23/11 »).

