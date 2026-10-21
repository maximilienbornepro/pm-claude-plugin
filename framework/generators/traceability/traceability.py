#!/usr/bin/env python3
"""Matrice de couverture IADT - génère un classeur Excel PRÉ-REMPLI à remplir par les équipes.

On part d'un **backlog** ou d'un jeu d'**exigences (TR)** et on produit une matrice où chaque ligne se
confronte à une méthode de vérification **IADT** (Inspection / Analyse / Démonstration / Test), un
**responsable** (équipe ou partenaire) et un **état de couverture**. Les colonnes à choix sont des
**listes déroulantes** Excel ; le reste est du texte libre.

  python3 traceability.py <items.(yml|json|csv)> [sortie.xlsx]   # matrice depuis une source
  python3 traceability.py --example [sortie.xlsx]                # matrice d'exemple (template)
  python3 traceability.py --notion [<items>]                     # schéma de la DB Notion équivalente (JSON)

Source d'items (une ligne = une exigence / un ticket) : liste d'objets avec au moins les colonnes
`prefill` du template (Réf, Req ID, Exigence, Phase). CSV : en-tête = noms de colonnes.

Lecture seule côté systèmes : n'écrit que le fichier de sortie (aucune écriture Office en place, aucune
notification). Le classeur est **nouveau** : on le remet ensuite où il doit aller.
"""
import sys, os, json, csv, io, zipfile, html, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import yamlmin  # noqa: E402  (parseur YAML du framework)

EXCEL_TPL = ROOT / "templates" / "trackers" / "excel" / "traceability.yml"
NOTION_TPL = ROOT / "templates" / "trackers" / "notion" / "traceability.yml"


def _load_yaml(path):
    return yamlmin.load(Path(path).read_text(encoding="utf-8"))


def load_items(src):
    """Charge les items depuis .yml/.json (liste d'objets) ou .csv (en-tête = colonnes)."""
    p = Path(src)
    if p.suffix.lower() == ".csv":
        with open(p, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))
    data = json.loads(p.read_text(encoding="utf-8")) if p.suffix.lower() == ".json" else _load_yaml(p)
    if isinstance(data, dict):
        for k in ("items", "exigences", "requirements", "rows"):
            if isinstance(data.get(k), list):
                return data[k]
    return data if isinstance(data, list) else []


# ----------------------------------------------------------------- xlsx (dropdowns)
def _esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def _colref(i):           # 0 -> A, 25 -> Z, 26 -> AA
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, text, style):
    return f'<c r="{ref}" t="inlineStr" s="{style}"><is><t xml:space="preserve">{_esc(text)}</t></is></c>'


def write_xlsx(path, tpl, items):
    cols = tpl["columns"]
    titles = tpl.get("header_rows") or []
    selects = tpl.get("selects") or {}
    widths = tpl.get("widths") or {}
    prefill = tpl.get("prefill") or []
    sheet_name = tpl.get("sheet") or "Matrice"

    hrow = len(titles) + 1                       # ligne d'en-tête des colonnes
    first_data = hrow + 1
    n_data = max(len(items), 1)
    last_data = hrow + n_data

    rows_xml = []
    # lignes de titre (fusionnées visuellement par la largeur ; style gras)
    for i, t in enumerate(titles, start=1):
        rows_xml.append(f'<row r="{i}">' + _cell(f"A{i}", t, 3) + "</row>")
    # en-tête des colonnes (gras)
    hc = "".join(_cell(f"{_colref(j)}{hrow}", c, 1) for j, c in enumerate(cols))
    rows_xml.append(f'<row r="{hrow}">{hc}</row>')
    # lignes de données (préremplies pour les colonnes `prefill`)
    for r, it in enumerate(items or [{}], start=first_data):
        cells = []
        for j, c in enumerate(cols):
            val = it.get(c, "") if c in prefill else ""
            cells.append(_cell(f"{_colref(j)}{r}", val, 2))
        rows_xml.append(f'<row r="{r}">{"".join(cells)}</row>')

    # colonnes : largeurs
    colsxml = ""
    if widths:
        parts = []
        for j, c in enumerate(cols):
            w = widths.get(c)
            if w:
                parts.append(f'<col min="{j+1}" max="{j+1}" width="{w}" customWidth="1"/>')
        colsxml = "<cols>" + "".join(parts) + "</cols>"

    # listes déroulantes (validation de données) sur les colonnes `selects`
    dvs = []
    for c, opts in selects.items():
        if c not in cols:
            continue
        j = cols.index(c)
        ref = f"{_colref(j)}{first_data}:{_colref(j)}{last_data}"
        f1 = _esc('"' + ",".join(opts) + '"')
        dvs.append(f'<dataValidation type="list" allowBlank="1" showInputMessage="1" '
                   f'showErrorMessage="1" sqref="{ref}"><formula1>{f1}</formula1></dataValidation>')
    dv_xml = f'<dataValidations count="{len(dvs)}">{"".join(dvs)}</dataValidations>' if dvs else ""

    pane = (f'<sheetView workbookViewId="0"><pane ySplit="{hrow}" topLeftCell="A{first_data}" '
            f'activePane="bottomLeft" state="frozen"/><selection pane="bottomLeft"/></sheetView>')

    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             f'<sheetViews>{pane}</sheetViews>'
             f'{colsxml}<sheetData>{"".join(rows_xml)}</sheetData>{dv_xml}</worksheet>')

    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<fonts count="3"><font><sz val="11"/><name val="Calibri"/></font>'
              '<font><b/><sz val="11"/><name val="Calibri"/></font>'
              '<font><b/><sz val="12"/><name val="Calibri"/></font></fonts>'
              '<fills count="3"><fill><patternFill patternType="none"/></fill>'
              '<fill><patternFill patternType="gray125"/></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FFEDEFF5"/></patternFill></fill></fills>'
              '<borders count="1"><border/></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="4">'
              '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'                                   # 0 defaut
              '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment vertical="center" wrapText="1"/></xf>'  # 1 en-tete
              '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf>'  # 2 donnees
              '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'                      # 3 titre
              '</cellXfs></styleSheet>')

    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          f'<sheets><sheet name="{_esc(sheet_name)[:31]}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
               '</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", styles)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return len(items or [])


def notion_schema(items):
    tpl = _load_yaml(NOTION_TPL)
    return {
        "title": tpl["title"],
        "properties": tpl["properties"],
        "options": tpl.get("options", {}),
        "views": tpl.get("views", []),
        "prefill": [{"Réf": it.get("Réf") or it.get("req_id") or it.get("Req ID"),
                     "Req ID": it.get("Req ID") or it.get("req_id"),
                     "Exigence": it.get("Exigence") or it.get("exigence"),
                     "Phase": it.get("Phase") or it.get("phase")}
                    for it in (items or [])],
        "note": ("Créer la base via le connecteur Notion (notion-create-database) sous Project Management, "
                 "puis importer les lignes `prefill`. Les équipes remplissent Méthode / Responsable / "
                 "Couverture (select) + les textes."),
    }


def main(argv):
    if not argv:
        sys.exit(__doc__)
    tpl = _load_yaml(EXCEL_TPL)

    if argv[0] == "--notion":
        items = load_items(argv[1]) if len(argv) > 1 and not argv[1].endswith(".json") else []
        if len(argv) > 1 and not argv[1].startswith("-"):
            try:
                items = load_items(argv[1])
            except Exception:
                items = []
        print(json.dumps(notion_schema(items), ensure_ascii=False, indent=2))
        return

    if argv[0] == "--example":
        items = tpl.get("exemples") or []
        out = argv[1] if len(argv) > 1 else "traceability.example.xlsx"
    else:
        items = load_items(argv[0])
        out = argv[1] if len(argv) > 1 else "traceability.xlsx"

    n = write_xlsx(out, tpl, items)
    print(f"écrit {out} | {n} exigences | listes déroulantes : {', '.join(tpl.get('selects', {}))}")
    print("À remplir par les équipes : Méthode / Responsable / Couverture (déroulantes) + réponse / évidence / test (libre).")


if __name__ == "__main__":
    main(sys.argv[1:])
