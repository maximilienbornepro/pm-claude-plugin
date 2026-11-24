---
name: meeting-agenda
description: Prépare l'agenda d'une réunion (weekly partenaire, kick-off, atelier technique, point interne) - 4 à 6 points numérotés, 2 ou 3 sous-points de 10 mots maximum, rien de plus. Langue selon le partenaire (config de mission). Matière tirée du dernier CR, des sujets ouverts et des derniers échanges. RENDU TEXTE dans la conversation, jamais d'envoi ni d'invitation.
meta:
  produces: meeting-agenda
  consumes: [transcripts, slack]
  mcp_deps: [notion, m365]
  cost: light
  exec: skill
  status: stable
---

# Agenda de réunion

Un agenda **n'est pas un document** : c'est la liste courte de ce qu'on va traiter, lisible en dix
secondes. Règle posée par le porteur (kick-off pentest, 19/11/2026) : « un agenda en 5 points avec
potentiellement 2-3 sous-annotations et c'est tout ». Puis (weekly KSAT) : « bullet points et 10 mots
par ligne ».

## Le format (règle dure)

```
<Organisation> x <Partenaire> - <nom de la réunion>, JJ/MM

1. **<Thème>**
   - <sous-point, 10 mots maximum>
   - <sous-point>
2. **<Thème>**
   - ...
N. **Next steps and AOB** / **Prochaines étapes et divers**
```

- **4 à 6 points numérotés**, titre du point en gras, un groupe nominal.
- **2 ou 3 sous-points** par point au plus, **10 mots maximum** chacun, pas de phrase rédigée.
- Le **dernier point** est toujours « Next steps and AOB » (ou « Prochaines étapes et divers »).
- Pas d'introduction, pas d'objectif de réunion en paragraphe, pas de tableau, pas de durées sauf demande.
- Un sous-point dit **ce qu'on attend** de la réunion (« KSAT shares IP ranges… »), pas un historique.
- Pas de secret, de lien de réunion, de mot de passe ni de valeur technique sensible (clé, JWKS, sub).

## La langue

Selon le partenaire, depuis la config de mission (même règle que `partner-report`) : un partenaire
anglophone en **anglais**, un partenaire francophone en **français**, une réunion interne dans la langue
du profil. Systématiquement, même si l'échange précédent était dans l'autre langue.

## La matière (dans cet ordre, lecture seule)

1. **Le dernier CR** de la même réunion (mail de suivi envoyé, transcription) : ses « prochaines
   étapes » sont la colonne vertébrale de l'agenda.
2. **Les sujets ouverts** de la section du partenaire dans la base de suivi (actions attendues).
3. **Les derniers mails** du fil avec le partenaire (depuis le dernier CR) : questions posées, valeurs
   demandées, engagements datés (« I'll send it on Monday »).
4. **Slack** en appui pour les faits internes (lecture seule, jamais de saisie dans un composer).
5. **Les changements d'interlocuteur** (départ, passation) : un point « Handover » s'ils existent.

## Après l'agenda (une à trois lignes, hors agenda)

Signaler au porteur ce qui doit être prêt **avant** la réunion : une valeur promise et pas encore
envoyée, un fichier annoncé pour une date passée, une confusion possible (ex. identifiant de dev au lieu
de prod). Pas plus de trois lignes.

## Garde-fous

- **Rendu texte dans la conversation uniquement** : aucun mail, aucune invitation, aucun message posté,
  aucune modification d'agenda Outlook.
- **Rien d'inventé** : un sous-point tient à un CR, un sujet, un mail ou un message ; sinon on l'omet.
- Corrections du porteur (« structure mieux », « enlève X ») : on réapplique le format, on ne rallonge pas.
