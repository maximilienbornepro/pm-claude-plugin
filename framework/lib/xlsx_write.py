#!/usr/bin/env python3
"""xlsx_write - écrit un .xlsx VALIDE à partir d'un template Excel du registre, SANS dépendance.

Pendant Excel de `notion-scaffold` : le registre `trackers/excel/<objet>.yml` décrit la structure
(colonnes ou matrice, lignes de titre, légende, exemples) ; ce module la rend en classeur réel.

Stdlib uniquement (zipfile + XML, chaînes « inline ») : pas d'openpyxl (absent, et destructeur sur les
classeurs OneDrive) - donc portable ET compatible avec le garde-fou Office (qui refuse openpyxl /
`.save()` / `rm`/`mv`, pas un écrivain stdlib). Le fichier se construit ici, puis se POSE dans le dossier
synchronisé en session (déroulé Office : fraîcheur, écriture unique, jamais d'écrasement d'autrui).

    import xlsx_write
    rows = xlsx_write.rows_from_template(tpl, projet="SINBAD")   # tpl = templates.load("excel", "risks")
    xlsx_write.write(path, sheet_name=tpl.get("sheet", "Feuille"), rows=rows)
"""
import zipfile
from xml.sax.saxutils import escape


def _colref(i):
    s = ""
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def rows_from_template(tpl, projet="<Projet>"):
    """Rend la liste des lignes (chaque ligne = liste de cellules) d'un template Excel.

    - registre (colonnes) : lignes de titre, (blanc), en-tête de colonnes, puis exemples ;
    - matrice (RACI) : lignes de titre, légende, (blanc), en-tête (row_header + rôles + extra), puis exemples.
    """
    rows = []
    for h in (tpl.get("header_rows") or []):
        rows.append([str(h).replace("<Projet>", projet)])
    if tpl.get("legend"):
        rows.append([str(tpl["legend"])])

    if tpl.get("layout") == "matrix":
        roles = (tpl.get("legende") or {}).get("roles") or []
        extra = tpl.get("extra_columns") or []
        header = [tpl.get("row_header", "")] + list(roles) + list(extra)
        rows.append([])                                   # ligne blanche
        rows.append(header)
        for ex in (tpl.get("exemples") or []):
            line = [ex.get(tpl.get("row_header", ""), "")]
            line += [ex.get(r, "") for r in roles]
            line += [ex.get(c, "") for c in extra]
            rows.append(line)
    else:
        cols = tpl.get("columns") or []
        rows.append([])                                   # ligne blanche
        rows.append(list(cols))
        for ex in (tpl.get("exemples") or []):
            rows.append([ex.get(c, "") for c in cols])
    return rows


def _cell(ref, text):
    return (f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
            f'{escape(str(text))}</t></is></c>')


def write(path, sheet_name, rows):
    """Écrit un xlsx minimal et valide : une feuille `sheet_name`, les `rows` (listes de cellules)."""
    xml_rows = []
    for rn, cells in enumerate(rows, start=1):
        cs = "".join(_cell(f"{_colref(i + 1)}{rn}", v) for i, v in enumerate(cells) if v != "")
        if cs:
            xml_rows.append(f'<row r="{rn}">{cs}</row>')
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetData>' + "".join(xml_rows) + '</sheetData></worksheet>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wbr = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
           '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbr)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return path
