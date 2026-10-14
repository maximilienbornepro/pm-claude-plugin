# Agents du framework - valeur et configurabilité

Deux familles d'agents. Ceux qui **produisent de la prose** (le ton compte, donc **configurable**) et
ceux qui **analysent ou dessinent** (pas de ton à régler, mais à forte valeur). La config du ton est
portée par `profiles/<mission>/pipeline.yml` (table `agents`) et appliquée par `framework/lib/set_tone.py`.

## Famille A - agents producteurs de contenu (ton CONFIGURABLE)

Forte valeur ajoutée, et le **ton se change par la config** (un seul endroit : `pipeline.yml`).

| Agent | Ce qu'il produit | Ton par défaut | Autres réglages (config) |
|---|---|---|---|
| `qap-redaction` | Chapitres du PAQ (anglais, style Master) | `voice-deliverable` | langue, chapitres possédés, sources |
| `cr-partenaire` | Mail de suivi hebdo partenaire | `voice-deliverable` | langue par partenaire (KSAT en, Airbus fr) |
| `notion-sujets` | Sujets Notion (Contexte/Action) | `voice-maximilien` | format contexte-action, base Sujets |
| `gate-deck` | Deck GATE | `voice-adservio` | style de schéma, template |
| `voice-adservio` | Note/dossier/one-pager éditorial | `voice-adservio` | - (le ton EST l'agent) |

Changer le ton d'un de ces agents = éditer une ligne de `pipeline.yml` puis lancer `set_tone.py`.
Tons disponibles : `voice-deliverable`, `voice-casual`, `voice-maximilien`, `voice-adservio`.

## Famille B - agents d'analyse / visuels (pas de ton, forte valeur)

Portés dans `framework/agents/` (génériques, config-driven, aucune constante de mission en dur) :

| Agent | Ce qu'il fait | Réglages (profil) |
|---|---|---|
| `sprint-plan-audit` | Audit du plan de sprints vs board du tracker (lecture seule) | board, cibles de capacité |
| `front-audit` | Écarts POC ↔ tickets ↔ contrat d'API/BFF (lecture seule) | chemins POC, epics, réponse backend |
| `ticket-audit` | Régressions de description du tracker (réparation gardée) | projet, auteurs protégés |
| `ticket-changes` | Qui a modifié quels tickets, quand, quoi (lecture seule) | projet, auteur « assistant » exclu |
| `sujets-read` | Relit la base de suivi mot pour mot (lecture seule) | base (data source), filtre de périmètre |
| `architecture` | Schéma d'archi interactif (model-first) | palette, logos, model.json |

Ces agents n'ont pas de ton rédactionnel (ligne `null` dans `pipeline.yml`) ; leur valeur vient de
l'exactitude et des garde-fous. Reste à porter en agents génériques : `doc-redaction` (chapitres de
livrable, ex `sinbad-qap-redaction`) et `voice-adservio` (actuellement skill) - famille A.

## Le mécanisme de configuration du ton

1. `profiles/<mission>/pipeline.yml`, table `agents` : `nom-agent: <ton | null>`.
2. `framework/lib/set_tone.py <mission>` : lit cette table et aligne le champ **`skills:`** (préchargement
   natif Claude Code) de chaque agent sur le ton voulu. `--dry-run` par défaut (montre l'écart), `--apply`
   écrit. On ne touche jamais au code de l'agent, seulement sa ligne de ton.
3. Résultat : un seul fichier de vérité pour « quel agent parle avec quel ton », changeable en une ligne.
