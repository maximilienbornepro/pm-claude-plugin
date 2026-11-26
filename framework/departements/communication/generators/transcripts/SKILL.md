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

## Sources declarees par le profil

Le profil liste ses sources dans `routines.yml > transcripts_sources` (ex. SINBAD : meeting notes Notion + Omi).
Toute routine ou generateur qui lit des reunions les lit **toutes**, pas seulement la premiere.

## Forme normalisee

Chaque transcription devient `{date, title, url, text}` (date = AAAA-MM-JJ). Le lecteur tolere les cles du
connecteur (`Title`, `Created time`, `url`, `text`) comme un `{"results": [...]}`, un tableau, du JSONL, ou
un enregistrement unique.

## Sources (pluggables)

- `--dump <f.json|f.jsonl>` : export Notion meeting notes (defaut framework).
- `--files <dossier>` : fichiers `.md`/`.txt` locaux ; date d'un frontmatter `date:` ou du nom de fichier
  (AAAA-MM-JJ), titre d'un `# titre` ou du nom de fichier. Permet d'autres sources sans changer l'aval.
- `--notion-db <id>` : base Notion lue **par l'API officielle** (integration interne, jeton `NOTION_TOKEN` ou
  `~/.config/pm-framework/notion.env`), filtree sur la colonne multi-select `Catégorie` (`--category`, `Omi`
  par defaut). C'est la source des **transcriptions du pendentif Omi** : elles sont importees dans la base
  « Notes de réunion » du **Notion perso** (une page par conversation : resume Omi puis transcription,
  colonnes Durée, Langue, Thème Omi, Import Omi, Mission, Exploité PM, Omi ID). Ce jeton ne sert qu'a Omi ;
  tout le reste de la mission passe par le connecteur Notion habituel.
  Une conversation « Verrouillé (plan payant) » n'a que ses metadonnees : ne rien en deduire (avec
  l'abonnement Omi, `omi_sync.py --unlock --apply` la complete). Import et classement : generateur et
  routine `omi-sync`.

```bash
python3 read_transcripts.py --notion-db 3aa6826e1f4b8044b30ec378dd5eaa0d --since 2026-10-13 --until 2026-10-19
```

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
