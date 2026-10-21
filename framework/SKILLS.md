# Catalogue des skills du framework

Index unique de **tous** les composants du framework : générateurs, tons, routines, agents. Le détail
vit ailleurs (un `SKILL.md` par composant) ; cette page sert d'annuaire. La colonne **Tags** marque les
usages (dont `partenaire` - le sous-ensemble partenaire est aussi dans `profiles/<mission>/partenaires.yml`).

Catalogues liés : tons -> `framework/REDACTION.md` · agents -> `framework/AGENTS.md` · routines ->
`framework/routines/README.md` · partenaires -> `profiles/<mission>/partenaires.yml`.

## Générateurs (`framework/generators/`)

| Skill | Ce qu'il produit | Tags |
|---|---|---|
| `architecture` (stack-imagery) | schéma d'archi interactif (modèle -> HTML validé, export draw.io, 3 cibles) | archi, publication |
| `projection` (projection-report) | rapport de projection (charge/réalisé/reste, par version) | jira, publication |
| `plan` (plan-sprints) | page « Avancement et sprints » : design réutilisable (gabarit + contrat + render + validate) + pipeline Jira config-driven, burn-downs réels | jira, publication |
| `sprint-plan` / `sprint-audit` | plan de sprints + audit plan vs board (lecture seule) | jira, publication |
| `jira-ticket` | tickets Jira : texte (garde-fou) + image via API | jira |
| `risks` (risks-register) | registre des risques (formulaire -> écriture Office gardée) | office |
| `scaffold` | miroir Drive + Notion, **dry-run** (scaffold_drive, scaffold_notion) | drive, notion |
| `suivi` | suivi d'activité : requêtes Claude -> store -> DB Notion privée + rapport hebdo | notion |
| `transcripts` | lecteur de transcriptions / CR (sources pluggables), alimente l'aval | lecture seule |
| `cr-partenaire` | mail de suivi après un call partenaire (rendu texte, sans envoi) | **partenaire** |

## Tons (`framework/skills/`) - détail dans `REDACTION.md`

| Skill | Pour quoi | Tags |
|---|---|---|
| `voice-deliverable` | livrables, tickets, pages de référence (sobre, factuel) | ton |
| `voice-maximilien` | sujets de suivi, CR internes (voix de Maximilien) | ton |
| `voice-casual` | échanges informels, messages courts | ton |
| `voice-adservio` | notes de fond, dossiers, decks (charte Adservio) | ton |

## Routines (`framework/routines/`) - détail dans `README.md`

| Routine | Tâche (une seule) | Tags |
|---|---|---|
| `publication-projection` | publier rapport + plan (gh-pages + artefact) | jira, publication |
| `objectifs-sprints` | aligner les objectifs des sprints dans Jira | jira |
| `avancement-tracker` | pousser l'avancement V1 (un champ) dans Notion | notion |
| `audit-perimetre` | auditer périmètre V1/V2 + couverture TR (lecture seule) | jira, office |
| `revue-sujets` | revue des sujets (formulaire) | notion |
| `revue-risques` | actualiser le registre des risques | office || `suivi` | suivi d'activité quotidien -> DB privée | notion |
| `brouillons-relances` | brouillons de relances (rendu texte, sans envoi) | **partenaire**, mail |

## Agents (`framework/agents/`) - détail dans `AGENTS.md`

| Agent | Ce qu'il fait | Tags |
|---|---|---|
| `qap-redaction` | chapitres du plan qualité | rédaction |
| `cr-partenaire` | mail de suivi hebdo partenaire | **partenaire** |
| `notion-sujets` | sujets Notion (Contexte/Action) | notion |
| `gate-deck` | deck GATE (style Adservio) | office |
| `sprint-audit` | audit plan de sprints vs Jira (lecture seule) | jira |
| `audit-front` | écarts maquette <-> tickets <-> contrat d'API (lecture seule) | jira |
| `audit-tickets` | régressions de description Jira | jira |
| `architecture` / `stack-imagery` | schéma d'archi interactif | archi |
| `risks` | registre des risques (formulaire -> écriture gardée) | office |

> Ajouter ici toute nouvelle brique. Un skill de type partenaire se tague `partenaire` et s'ajoute aussi à
> `profiles/<mission>/partenaires.yml`.
