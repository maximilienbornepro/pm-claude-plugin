---
name: transcripts
description: Lecteur de transcriptions / CR de reunion, lecture seule, sources pluggables. Normalise vers {date, title, url, text} et filtre sur une fenetre de dates ; alimente les generateurs aval (sujets, CR partenaires, revue des risques, synthese d'appel). N'ecrit rien.
meta:
  produces: transcripts
  consumes: []
  mcp_deps: [notion]
  cost: light
  status: stable
---

Entree **imposee par le framework** pour tout ce qui part d'une reunion : sujets, CR partenaires, revue
des risques, synthese d'appel. Un seul lecteur, une seule forme normalisee, des sources pluggables.

## Emplacement canonique

Les transcriptions / CR vivent dans le **miroir Notion, sous Gouvernance** (meeting notes). C'est la
**source par defaut**. Le connecteur Notion n'etant pas appelable depuis un script, Claude produit un
**export JSON/JSONL** (via `notion-query-meeting-notes` + fetch) que le lecteur consomme.

## Forme normalisee

Chaque transcription devient `{date, title, url, text}` (date = AAAA-MM-JJ). Le lecteur tolere les cles du
connecteur (`Title`, `Created time`, `url`, `text`) comme un `{"results": [...]}`, un tableau, du JSONL, ou
un enregistrement unique.

## Sources (pluggables)

- `--dump <f.json|f.jsonl>` : export Notion meeting notes (defaut framework).
- `--files <dossier>` : fichiers `.md`/`.txt` locaux ; date d'un frontmatter `date:` ou du nom de fichier
  (AAAA-MM-JJ), titre d'un `# titre` ou du nom de fichier. Permet d'autres sources sans changer l'aval.

## Usage

```bash
python3 read_transcripts.py --dump notes.json --since 2026-10-01 --until 2026-10-12
python3 read_transcripts.py --files ./transcriptions --date 2026-10-02 --json   # sortie pour l'aval
```

`--json` sort la liste normalisee telle quelle, a passer a un generateur aval. Sans `--json`, sortie
lisible (date, titre, url, extrait).

## Garde-fous

- **Lecture seule** : le lecteur ne cree, ne modifie, ne supprime rien. L'aval (sujets/CR/risques) garde
  ses propres validations et sa carte de notifications (`framework/NOTIFICATIONS.md`).
- **Ne rien inventer** : une date illisible exclut l'entree (plutot que de la dater au hasard).
