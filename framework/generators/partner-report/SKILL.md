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
