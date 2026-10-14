#!/usr/bin/env python3
"""Ecriture sure des classeurs Office synchronises (xlsx) - generique.

Pourquoi : openpyxl detruit images et dessins de ces classeurs ; on ecrit donc
chirurgicalement dans le XML du zip. Ce module est la SEULE implementation a
utiliser pour ecrire un .xlsx synchronise (OneDrive/SharePoint/GDrive), afin de
ne jamais casser la mise en forme ni la synchro.

Garde-fous portes ici :
- ecriture chirurgicale cellule par cellule (styles, fusions, images preserves) ;
- sauvegarde horodatee avant d'ecrire ;
- reecriture EN PLACE (inode preserve, jamais rm/mv) en une seule fois ;
- rapport de taille avant/apres.

Garde-fou NON porte ici (a faire en session, via le connecteur du Drive) : le
CONTROLE DE FRAICHEUR distant (lastModifiedDateTime). Toujours le verifier AVANT
d'appeler save() : date du jour = quelqu'un est dedans, on n'ecrit pas.

API Python :
    from onedrive_xlsx import read_cells, set_cells, append_row, backup, save
    cells = read_cells(path)                 # {"A7": "...", ...} (1re feuille)
    xml   = set_cells(path, {"D7": "x"})     # -> bytes du xlsx modifie
    xml   = append_row(xml_or_path, {"A": "..","B": ".."})  # ligne en fin de table
    backup(path, dossier)                    # copie horodatee
    save(path, xml, dossier)                 # sauvegarde + ecriture en place + tailles

CLI :
    python3 onedrive_xlsx.py read  <file>
    python3 onedrive_xlsx.py set   <file> A7=valeur D7="autre" [--backup DIR] [--apply]
    python3 onedrive_xlsx.py check <file>    # structure (dimension, feuilles)
Sans --apply, `set` ecrit une copie <file>.new.xlsx et n'edite pas l'original.
"""
import zipfile, re, html, os, sys, shutil, datetime, io
from xml.etree import ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def _first_sheet(z):
    names = [n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n)]
    return sorted(names)[0]


def _colnum(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    c = 0
    for ch in m.group(1):
        c = c * 26 + (ord(ch) - 64)
    return c, int(m.group(2))


def _esc(t):
    return html.escape(t or '', quote=False)


def _as_zip(x):
    """x est un chemin (str) ou des bytes d'un xlsx."""
    if isinstance(x, (bytes, bytearray)):
        return zipfile.ZipFile(io.BytesIO(x))
    return zipfile.ZipFile(x)


def read_cells(path_or_bytes, sheet=None):
    """Retourne {ref: texte} de la feuille (1re par defaut), valeurs resolues."""
    z = _as_zip(path_or_bytes)
    sst = []
    if 'xl/sharedStrings.xml' in z.namelist():
        r = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in r.findall(f'{NS}si'):
            sst.append(''.join(t.text or '' for t in si.iter(f'{NS}t')))
    sh = sheet or _first_sheet(z)
    r = ET.fromstring(z.read(sh))
    out = {}
    for c in r.iter(f'{NS}c'):
        v = c.find(f'{NS}v'); isv = c.find(f'{NS}is'); val = ''
        if c.get('t') == 's' and v is not None:
            val = sst[int(v.text)]
        elif isv is not None:
            val = ''.join(x.text or '' for x in isv.iter(f'{NS}t'))
        elif v is not None:
            val = v.text or ''
        if val != '':
            out[c.get('r')] = val
    return out


def _cell_xml(ref, style, text):
    if text == '':
        return f'<c r="{ref}" s="{style}"/>'
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{_esc(text)}</t></is></c>'


def set_cells(path_or_bytes, updates):
    """Pose {ref: texte} dans la 1re feuille, en preservant les styles.
    La cellule existante est remplacee ; sinon elle est inseree dans sa ligne
    (la ligne doit exister). Renvoie les bytes du xlsx modifie."""
    z = _as_zip(path_or_bytes)
    sh = _first_sheet(z)
    s = z.read(sh).decode('utf-8')

    def row_style(rn):
        m = re.search(rf'<c r="A{rn}" s="(\d+)"', s) or re.search(rf'<c r="[A-Z]+{rn}" s="(\d+)"', s)
        return m.group(1) if m else "0"

    for ref, text in updates.items():
        rn = int(re.match(r'[A-Z]+(\d+)', ref).group(1))
        m = re.search(rf'<c r="{ref}" s="(\d+)"', s)
        st = m.group(1) if m else row_style(rn)
        cell = _cell_xml(ref, st, text)
        if re.search(rf'<c r="{ref}"[^>]*/>', s):
            s = re.sub(rf'<c r="{ref}"[^>]*/>', cell, s)
        elif re.search(rf'<c r="{ref}"[^>]*>.*?</c>', s):
            s = re.sub(rf'<c r="{ref}"[^>]*>.*?</c>', cell, s, flags=re.S)
        else:
            if not re.search(rf'<row r="{rn}"', s):
                raise ValueError(f"ligne {rn} absente : utiliser append_row pour {ref}")
            s = re.sub(rf'(<row r="{rn}"[^>]*>)(.*?)(</row>)',
                       lambda mo: mo.group(1) + mo.group(2) + cell + mo.group(3), s, flags=re.S)
    return _repack(z, sh, s)


def append_row(path_or_bytes, cells, style=None):
    """Ajoute une ligne en fin de table. `cells` = {col_lettre: texte}.
    Style herite de la derniere ligne de donnees si non fourni."""
    z = _as_zip(path_or_bytes)
    sh = _first_sheet(z)
    s = z.read(sh).decode('utf-8')
    rownums = [int(m.group(1)) for m in re.finditer(r'<row r="(\d+)"', s)]
    last = max(rownums); new = last + 1
    if style is None:
        m = re.search(rf'<c r="A{last}" s="(\d+)"', s)
        style = m.group(1) if m else "0"
    cols = sorted(cells, key=lambda L: _colnum(L + "1")[0])
    inner = ''.join(_cell_xml(f"{L}{new}", style, cells[L]) for L in cols)
    span = f"{_colnum(cols[0]+'1')[0]}:{_colnum(cols[-1]+'1')[0]}"
    rowxml = f'<row r="{new}" spans="{span}">{inner}</row>'
    s = re.sub(r'(</sheetData>)', rowxml + r'\1', s)
    s = re.sub(r'<dimension ref="([A-Z]+)\d+:([A-Z]+)\d+"/>',
               lambda mo: f'<dimension ref="{mo.group(1)}1:{mo.group(2)}{new}"/>', s)
    return _repack(z, sh, s)


def _repack(zin, sheetname, sheetxml):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zo:
        for it in zin.infolist():
            b = zin.read(it.filename)
            if it.filename == sheetname:
                b = sheetxml.encode('utf-8')
            zo.writestr(it, b)
    return buf.getvalue()


def backup(path, dossier):
    os.makedirs(dossier, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    dst = os.path.join(dossier, f"{os.path.splitext(os.path.basename(path))[0]}.backup-{ts}.xlsx")
    shutil.copy2(path, dst)
    return dst


def save(path, xml_bytes, dossier):
    """Sauvegarde horodatee, puis reecriture EN PLACE (inode preserve)."""
    avant = os.path.getsize(path)
    b = backup(path, dossier)
    with open(path, 'wb') as f:   # reecriture en place, jamais rm/mv
        f.write(xml_bytes)
    apres = os.path.getsize(path)
    return {"backup": b, "avant": avant, "apres": apres}


def _main(argv):
    if len(argv) < 2:
        print(__doc__); return 1
    cmd, path = argv[0], argv[1]
    sp = os.environ.get("CLAUDE_SCRATCHPAD", "/tmp")
    if cmd == "read":
        for ref, v in sorted(read_cells(path).items(), key=lambda kv: _colnum(kv[0])[::-1]):
            print(f"{ref}: {v}")
    elif cmd == "check":
        z = _as_zip(path); s = z.read(_first_sheet(z)).decode()
        print("feuilles:", [n for n in z.namelist() if 'worksheets/sheet' in n])
        print(re.search(r'<dimension ref="[^"]+"', s).group(0))
    elif cmd == "set":
        rest = argv[2:]; apply = "--apply" in rest
        bdir = sp
        if "--backup" in rest:
            bdir = rest[rest.index("--backup") + 1]
        updates = {}
        for tok in rest:
            if "=" in tok and not tok.startswith("--"):
                k, v = tok.split("=", 1); updates[k] = v
        xml = set_cells(path, updates)
        if apply:
            info = save(path, xml, bdir); print("ecrit en place:", info)
        else:
            out = path + ".new.xlsx"; open(out, "wb").write(xml); print("ecrit (copie):", out)
    else:
        print("commande inconnue:", cmd); return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
