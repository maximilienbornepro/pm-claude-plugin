# Rédaction - catalogue des tons et règles d'écriture (générique)

Les **tons** sont des skills dans `framework/skills/`. Le **ton par livrable et par agent** est déclaré dans
`profiles/<mission>/pipeline.yml` (`deliverables.<x>.tone`, table `agents`). `set_tone.py` aligne le champ
`skills:` de chaque agent sur cette table. On **propose le ton avant d'écrire** un contenu.

Tout ce qui est **propre à une mission** (langue par partenaire, auteurs dont on ne touche pas le texte,
conventions de tickets, glossaire) vit dans le **profil**, pas ici. Cette page ne porte que le générique.

## Les tons de base

| Skill (`framework/skills/`) | Pour quoi | Voix |
|---|---|---|
| `voice-deliverable` | livrables projet, tickets, pages de référence | sobre, factuel, structuré |
| `voice-maximilien` | suivi, CR internes, écrits à la 1re personne | « on » pour l'équipe, « je » pour ses engagements, phrases avec un verbe |
| `voice-casual` | échanges informels, messages courts | détendu, direct |
| `voice-adservio` | notes de fond, dossiers, one-pagers, decks | charte éditoriale Adservio (soignée) ; `schema_style: adservio` pour les visuels |

(Les noms portant encore une marque de mission seront généralisés au Lot 9.)

## Règles de langue (transverses, tous tons)

- **Langue de la mission** (`profile.yml > lang`). **Langue par partenaire** : selon
  `profiles/<mission>/partenaires.yml` (`partners.<x>.lang`), systématiquement.
- **Jamais de tiret cadratin ni de point médian** : séparateur toujours `-`.
- **Structurer plutôt que rédiger au kilomètre** : dès trois points, ranger par thème (intitulé en gras,
  détail en sous-puces), **un seul niveau** d'indentation. Vaut pour tickets, pages, CR et livrables.
- **Ne rien inventer** : acronyme, chiffre ou capacité inconnus -> « à confirmer ».
- Les **exigences (TR) se citent mot pour mot**, jamais reformulées.
- **Pas de vraie mention `@`** dans un écrit : le nom en texte simple (sinon notification).

## Par support

| Support | Ton | Points clés (génériques) |
|---|---|---|
| Ticket (gestionnaire) | `voice-deliverable` | modèle de ticket du profil (générateur `jira-ticket`) ; pas d'historique barré ; image via API, jamais le connecteur |
| Page de suivi / sujets | `voice-maximilien` | structure Contexte / Action attendue ; ne traiter que ce que le profil attribue à son rôle |
| CR partenaire | générateur `cr-partenaire` | mail de suivi, langue par partenaire ; **rendu texte, jamais d'envoi** |
| Livrable / dossier / deck | `voice-adservio` | charte Adservio ; visuels `schema_style: adservio` ; palette `profiles/<mission>/palette.json` |
| Mail / message | ton du contexte | **jamais d'envoi** : on rend le texte, l'utilisateur envoie (voir `NOTIFICATIONS.md`) |

## Schématisation

Les visuels de livrable suivent la charte du profil (couleurs de `palette.json`). Le schéma d'architecture
interactif est un cas à part (générateur `architecture`, harness `validate.py`).
