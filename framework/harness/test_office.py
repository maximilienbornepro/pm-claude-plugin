#!/usr/bin/env python3
"""Tests - writer xlsx stdlib + rendu des templates excel. python3 framework/harness/test_office.py"""
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "harness"))
os.environ["PMF_PROFILES"] = str(ROOT / "profiles")
import templates as TPL      # noqa: E402
import xlsx_write            # noqa: E402
import onedrive_xlsx as OX   # noqa: E402

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _rows(path):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    return [["".join(t.text or "" for t in c.iter(f"{NS}t")) for c in r.iter(f"{NS}c")]
            for r in root.iter(f"{NS}row")]


def test_rows_from_template_register():
    tpl = TPL.load("excel", "risks")
    rows = xlsx_write.rows_from_template(tpl, projet="ACME")
    assert rows[0] == ["ACME · Risks"]                      # <Projet> remplacé
    assert ["Risk", "Probability", "Impact", "Detail"] in rows  # l'en-tête
    assert any("Contractual" in (r[0] if r else "") for r in rows)


def test_rows_from_template_matrix():
    tpl = TPL.load("excel", "raci")
    rows = xlsx_write.rows_from_template(tpl, projet="ACME")
    # l'en-tête = row_header + rôles + colonnes extra
    header = next(r for r in rows if r and r[0] == "Activity")
    assert "TPM" in header and "Comment" in header


def test_write_produit_un_xlsx_valide():
    tpl = TPL.load("excel", "risks")
    rows = xlsx_write.rows_from_template(tpl, projet="ACME")
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "r.xlsx")
        xlsx_write.write(p, "Risks", rows)
        z = zipfile.ZipFile(p)
        assert "[Content_Types].xml" in z.namelist() and "xl/worksheets/sheet1.xml" in z.namelist()
        got = _rows(p)
        assert any("Risk" in (c or "") for r in got for c in r)


def test_append_chirurgical_preserve_et_ajoute():
    tpl = TPL.load("excel", "risks")
    rows = xlsx_write.rows_from_template(tpl, projet="ACME")
    with tempfile.TemporaryDirectory() as d:
        p = str(Path(d) / "r.xlsx")
        xlsx_write.write(p, "Risks", rows)
        n0 = len([r for r in _rows(p) if any(r)])
        data = OX.append_row(p, {"A": "AI: drift", "B": "Medium", "C": "High", "D": "Monitor"})
        open(p, "wb").write(data)
        got = _rows(p)
        n1 = len([r for r in got if any(r)])
        assert n1 == n0 + 1
        assert any("AI: drift" in (c or "") for r in got for c in r)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  FAIL {fn.__name__}: {e or 'assertion'}")
        except Exception as e:
            print(f"  ERR  {fn.__name__}: {e}"); traceback.print_exc()
    print(f"\n{ok}/{len(fns)} tests OK")
    sys.exit(0 if ok == len(fns) else 1)
