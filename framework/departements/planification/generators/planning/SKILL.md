---
name: planning
description: Planning technique d'une mission depuis UNE source (planning.json) - Gantt PPTX + slide « Échéances » dérivée du Gantt (toujours synchronisée) + slides de situation (Sujet / Statut / Situation / Levier / Échéance) + tableaux libres (responsabilités, RACI résumée) ; et en alternative un Gantt Excel (template Gantt fourni). Sans dépendance. Écrit seulement les fichiers demandés, en local.
meta:
  produces: planning-deck
  consumes: [notion-topics, raci]
  mcp_deps: []
  cost: light
  writes: local-file
  status: stable
---

# Générateur `planning`

Le planning technique que l'on montre en comité : un **Gantt**, la **liste des échéances**, l'**état de
chaque sujet** avec son **levier**, et les tableaux d'accompagnement (responsabilités du TPM, RACI
résumée...). Tout sort d'**une seule source de données** : on ne maintient plus deux slides à la main.

## Pourquoi une seule source
Leçon SINBAD (11/2026) : le Gantt et la slide des échéances doivent **toujours** dire la même chose. Ici
la slide « Échéances » est **calculée** à partir du Gantt (élément par élément, dans l'ordre des
couloirs) : impossible qu'elles divergent. Idem pour le Gantt Excel.

## Données : `profiles/<mission>/planning.json` (ou `--input`)
```json
{
 "title": "...", "subtitle": "...", "client": "...", "project": "...",
 "start": "2026-10-05", "weeks": 15,
 "lanes": [ {"name": "Environments", "rows": [ [ {"type": "bar", "start": "2026-11-16", "end": "2026-11-27", "label": "Preprod / QA", "label_out": true} ] ] } ],
 "vlines": [ {"date": "2026-11-27", "label": "Signing", "kind": "orange", "in_table": false} ],
 "echeances_title": "Le message clé de la slide", "echeances_subtitle": "...",
 "status": {"subtitle": "Situation technique au JJ/MM", "slides": [ {"title": "Titre = message clé", "sections": [ {"domain": "Plateforme", "rows": [ {"subject": "...", "status": "En cours", "situation": "...", "lever": "...", "due": "27/11"} ] } ] } ]},
 "tables": [ {"title": "...", "subtitle": "...", "header": ["Responsabilité", "Ce que ça recouvre", "Charge"], "widths": [26, 43, 14], "rows": [["...", "...", "..."]], "bold_last": true} ],
 "theme": {"primary": "1F3864", "header": "2E75B6", "bar": "8EC1FF", "footer": "C2 - Confidential"}
}
```
- **Éléments d'un couloir** (une ligne = une liste d'éléments) : `bar` (start, end), `milestone` (date ;
  `kind` blue / orange / black / red / diamond), `note` (texte seul à une date), `run` (flèche « Run » jusqu'au bout).
  Options : `label`, `side: "l"` (libellé à gauche), `label_out` (libellé à droite de la barre), `color`,
  `in_table: false` (exclu de la slide des échéances, ex. les sprints).
- **Statuts** (fixés, couleurs nettement distinctes) : `OK`, `En cours`, `Prévu`, `À risque`, `En discussion`.
  Un statut autre que OK **doit** avoir un levier (contrôle).
- Excel : police **Calibri** partout (ou `theme.xlsx_font`) ; colonnes facultatives `owner` (Porteur), `team` (Équipe), `entity` (Entité), `progress` (0..1) sur les éléments.

## Usage
```bash
python3 framework/pm.py run planning <mission>                          # relecture markdown + contrôles
python3 framework/pm.py run planning <mission> --pptx planning.pptx     # deck : Gantt, échéances, situation, tableaux
python3 framework/pm.py run planning <mission> --xlsx gantt.xlsx        # Gantt Excel (template fourni)
python3 framework/pm.py run planning <mission> --xlsx g.xlsx --template mon_template.xlsx
python3 framework/pm.py run planning <mission> --json                   # données + échéances + contrôles
```
Sans profil, le générateur prend `planning.example.json` (projet fictif) : `pm run planning demo`.

## Contrôles (affichés à chaque rendu)
Dates hors fenêtre, fin avant début, libellés en double, statut inconnu, levier manquant.

## Le deck produit
1. **Gantt** : mois + semaines, couloirs, barres, jalons, traits verticaux (aujourd'hui, signature,
   ouverture), légende des traits en bas.
2. **Échéances** : deux tableaux côte à côte (Domaine / Élément / Date), couloirs jamais coupés,
   pagination automatique.
3. **Situation** : une slide par groupe de sujets, titre = message clé (règle : jamais un titre descriptif).
4. **Tableaux libres** : responsabilités et charge, RACI résumée, etc.

Sans gabarit, le deck est **autonome** (thème neutre, police Arial).

## Dans le gabarit de l'entreprise (`--pptx-template`)

Pour sortir le deck **dans le PowerPoint de l'entreprise** (logo, pied de page, police et couleur des titres) :

```bash
python3 framework/pm.py run planning <mission> --pptx out.pptx --pptx-template gabarit.pptx --layout "Titre seul"
```

- `gabarit.pptx` : **n'importe quel PPT de l'entreprise** (un deck existant suffit) : on garde ses masques,
  mises en page, thème et médias, et on retire ses slides.
- `--layout` : la mise en page à utiliser (nom affiché dans PowerPoint). Sans `--layout`, la première
  mise en page qui a un emplacement titre. Un nom inconnu affiche la liste des mises en page disponibles.
- Le **titre** de chaque slide va dans l'emplacement titre de la mise en page (style du gabarit) ; le
  contenu (Gantt, tableaux) est **recalé** dans la zone utile : sous le titre et son trait décoratif,
  jusqu'au bas de la zone de texte de la mise en page.
- À mettre une fois pour toutes dans `planning.json` :
  `"template": {"pptx": "templates/mon_gabarit.pptx", "layout": "Titre seul"}` (chemin relatif au
  fichier de données) ; option `"box": [x, y, largeur, hauteur]` en EMU pour forcer la zone utile.
- `"gantt_title"` : titre-message de la slide Gantt (sinon `title`).

Pour intégrer une slide dans un autre deck en ligne : **clic droit > Copier** sur la miniature, puis
coller dans le deck cible (le Ctrl/Cmd+C clavier ne remplit pas toujours le presse-papier de
PowerPoint Online : vérifier avant de coller).

Skill de bout en bout (sources, mise à jour, rendu, relecture, dépôt) : `framework/departements/planification/skills/technical-planning`.

## Le Gantt Excel (alternative au PPT)
`templates/gantt_template.xlsx` : une ligne par **tâche**, regroupées par **section** (le couloir du Gantt).
Colonnes : Section (fusionnée) | Tâche | Équipe | Porteur | Entité | Avancement | Début | Fin (pas de
notion de chapitre : les colonnes « chapter / sub-chapter » du template sont masquées). Les barres, le jour courant et les week-ends viennent de
la mise en forme conditionnelle du template ; Excel recalcule à l'ouverture. 120 lignes disponibles,
les inutilisées sont masquées. Un autre template au même gabarit se passe par `--template`.

## Règles de rédaction (reprises de SINBAD)
- KSAT / Airbus (ou tout partenaire) : **jamais « partenaires » en bloc**, une ligne par partenaire.
- Sujets qui parlent au projet, pas des composants ; situation en phrases complètes ; levier pour tout ce
  qui n'est pas OK ; ne jamais citer « la slide de X » comme source.
- Toute modification du Gantt : **proposer d'abord** (le planning est chargé), puis régénérer : les deux
  slides restent synchronisées d'office.
- Le statut et le contexte des sujets Notion reprennent mot pour mot la slide de situation (voir
  `routines/review-topics`).

## Garde-fous
Écrit uniquement les fichiers demandés, en local. Le report dans un deck ou un classeur **partagé** suit le
déroulé Office (`framework/garde-fous/_deroule-office.md`) : fraîcheur SharePoint, sauvegarde, une seule écriture.
