#!/usr/bin/env python3
"""Test du generateur planning : exemple -> markdown, PPTX et XLSX valides, echeances = elements libelles."""
import sys, zipfile, tempfile, importlib.util, json
from pathlib import Path
import xml.dom.minidom as m
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("planning", ROOT / "framework/generators/planning/planning.py")
P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
data = json.load(open(ROOT / "framework/generators/planning/planning.example.json"))
ok = True
def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg); ok = ok and cond
ech = P.echeances(data)
labelled = [it for _, it in P.items_of(data) if it.get("label") and it.get("in_table") is not False]
check(len(ech) == len(labelled), f"echeances derivees du Gantt ({len(ech)} = {len(labelled)})")
check(P.checks(data) == [], "exemple sans ecart de controle")
with tempfile.TemporaryDirectory() as d:
    pp = Path(d) / "p.pptx"; xx = Path(d) / "g.xlsx"
    slides = P.build_deck(data); P.write_pptx(slides, pp)
    z = zipfile.ZipFile(pp)
    for n in z.namelist():
        if n.endswith(".xml") or n.endswith(".rels"):
            m.parseString(z.read(n))
    check(len(slides) >= 4, f"deck PPTX valide ({len(slides)} slides, XML bien forme)")
    for e in ech:
        if e["label"] not in z.read("ppt/slides/slide2.xml").decode():
            check(False, f"echeance absente de la slide 2 : {e['label']}"); break
    else:
        check(True, "toutes les echeances sont sur la slide 2")
    n = P.write_xlsx(data, xx)
    zx = zipfile.ZipFile(xx); m.parseString(zx.read("xl/worksheets/sheet1.xml"))
    check("xl/calcChain.xml" not in zx.namelist(), f"Gantt Excel valide ({n} lignes, calcChain retire)")
sys.exit(0 if ok else 1)
