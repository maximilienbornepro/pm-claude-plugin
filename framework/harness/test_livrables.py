#!/usr/bin/env python3
"""test_livrables - every deliverable, generated for real on the test mission, output checked.

    python3 framework/harness/test_livrables.py          # all deliverables
    python3 framework/harness/test_livrables.py risks    # only the cases whose name contains "risks"

The test mission lives in framework/harness/fixtures/profiles/test/ (versioned, fake data). Each run
copies it to a throw-away folder (PMF_PROFILES), so nothing in the repo or outside is written. No
connector, no Jira: generators that need Jira must answer with a clear message, never a traceback.

RULE: every `pm run` command must have at least one case in CASES. The verifier enforces it.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "framework" / "harness" / "fixtures" / "profiles"
M = "test"
TIMEOUT = 120


# --- output checks ---------------------------------------------------------------------------------
def pptx_slides(path):
    with zipfile.ZipFile(path) as z:
        return sum(1 for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))


def xlsx_sheets(path):
    with zipfile.ZipFile(path) as z:
        assert "xl/workbook.xml" in z.namelist(), "xlsx sans xl/workbook.xml"
        return sum(1 for n in z.namelist() if n.startswith("xl/worksheets/sheet"))


def is_html(path):
    t = Path(path).read_text(encoding="utf-8")
    return "<html" in t.lower() and "</html>" in t.lower()


def make_risks_xlsx(path):
    """Minimal register (header row 6, data from row 7) - zip + XML, same as real workbooks."""
    rows = {6: ["Risque", "Probabilité", "Impact", "Détail"],
            7: ["Capacité équipe", "High", "Medium", "deux départs en décembre"],
            8: ["Accès production", "Medium", "High", "en attente du SRE"]}
    cells = "".join(
        f'<row r="{r}">' + "".join(f'<c r="{chr(65 + i)}{r}" t="inlineStr"><is><t>{v}</t></is></c>'
                                   for i, v in enumerate(vals)) + "</row>" for r, vals in rows.items())
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    files = {
        "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": f'<?xml version="1.0"?><workbook {ns} {rel}><sheets><sheet name="Risques" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": f'<?xml version="1.0"?><worksheet {ns}><sheetData>{cells}</sheetData></worksheet>',
    }
    with zipfile.ZipFile(path, "w") as z:
        for n, c in files.items():
            z.writestr(n, c)


# --- cases: (name, args, check(out, stdout) -> None) -------------------------------------------------
# `{out}` in args is replaced by the throw-away output folder. A check raises AssertionError.
def contains(*words):
    def check(out, text):
        for w in words:
            assert w in text, f"sortie sans « {w} »"
    return check


def file_check(rel, kind, minimum=1):
    def check(out, text):
        p = out / rel
        assert p.is_file() and p.stat().st_size > 0, f"{rel} absent ou vide"
        if kind == "pptx":
            n = pptx_slides(p)
            assert n >= minimum, f"{rel} : {n} slide(s), attendu >= {minimum}"
        elif kind == "xlsx":
            assert xlsx_sheets(p) >= minimum, f"{rel} : pas de feuille"
        elif kind == "html":
            assert is_html(p), f"{rel} : HTML incomplet"
        elif kind == "json":
            json.loads(p.read_text(encoding="utf-8"))
    return check


def both(*checks):
    def check(out, text):
        for c in checks:
            c(out, text)
    return check


def json_out(*keys):
    def check(out, text):
        d = json.loads(text[text.index("{") if "{" in text else 0:] if text.lstrip()[:1] != "[" else text)
        for k in keys:
            assert k in d, f"JSON sans clé « {k} »"
    return check


def clean_refusal(word):
    """Generator needing Jira / a connector: a clear message, exit != 0, no traceback."""
    def check(out, text):
        assert word.lower() in text.lower(), f"message attendu (« {word} ») absent"
    return check, "refus"


CR = {"partner": "partenaire_b", "meeting": "Point hebdo", "date": "2026-11-26",
      "points": [{"title": "Accès API", "situation": "Clé reçue.", "next_step": "tester l'appel", "deadline": "02/12"}]}

CASES = [
    # Planification
    ("projection", ["projection", M], clean_refusal("identifiants Jira")),
    ("plan", ["plan", M, "{out}/plan.html"], clean_refusal("identifiants Jira")),
    ("planning", ["planning", M], contains("aucun ecart")),
    ("planning-json", ["planning", M, "--json"], json_out()),
    ("planning-pptx", ["planning", M, "--pptx", "{out}/planning.pptx"], file_check("planning.pptx", "pptx", 2)),
    ("planning-xlsx", ["planning", M, "--xlsx", "{out}/gantt.xlsx"], file_check("gantt.xlsx", "xlsx")),
    ("jira-sprints-audit", ["jira-sprints-audit", M], clean_refusal("identifiants Jira")),
    # Suivi et gouvernance
    ("risks", ["risks", M], contains("Capacité équipe", "Accès production")),
    ("raci", ["raci", M], contains("| Activite |", "Architecture")),
    ("raci-role", ["raci", M, "--role", "Architecte"], contains("Architecture")),
    ("raci-cells", ["raci", M, "--cells"], contains("RACI")),
    ("raci-json", ["raci", M, "--json"], json_out()),
    ("traceability", ["traceability", "--example", "{out}/trace.xlsx"], file_check("trace.xlsx", "xlsx")),
    ("trace-audit", ["trace-audit", M], contains("lecture seule")),
    ("docs-coherence-audit", ["docs-coherence-audit", "--mission", M, "--root", "{out}"], contains("Tout est coherent")),
    ("notion-topics-audit", ["notion-topics-audit", "--help"], contains("usage")),
    # Qualité du backlog
    ("jira-changes-audit", ["jira-changes-audit", M], clean_refusal("identifiants Jira")),
    ("jira-images", ["jira-images", M], clean_refusal("identifiants Jira")),
    # Communication
    ("partner-report", ["partner-report", "--input", "{out}/cr.json"], contains("Accès API")),
    ("partner-report-absent", ["partner-report", "--input", "{out}/absent.json"], clean_refusal("introuvable")),
    ("weekly-report", ["weekly-report", "--list"], None),
    ("activity", ["activity", M, "check"], contains("store vide")),
    ("transcripts", ["transcripts", "--files", "{out}/notes"], None),
    ("slack", ["slack", "--help"], contains("usage")),
    ("omi-sync", ["omi-sync", "--help"], contains("Omi")),
    # Studio
    ("dossier-build", ["dossier", M, "--build"], None),
    ("dossier-sync", ["dossier", M, "--sync", "--dry-run"], None),
    ("archi", ["archi", M], contains("TOUT PASSE")),
    ("archi-drawio", ["archi", M, "--export", "drawio"], contains("Pages")),
    ("deck-gate", ["deck-gate", M], contains("GATE 1", "Jalons")),
    ("deck-gate-json", ["deck-gate", M, "--json"], json_out("slides")),
    ("poc", ["poc", M], None),
    ("office", ["office", "--mission", M, "risks", "--out", "{out}/risks-copie.xlsx"], None),
    # Direction de projet
    ("setup", ["setup", M], None),
    ("init", ["init", "nouvelle-mission"], contains("dry-run")),
    ("preflight", ["preflight", M], clean_refusal("BLOQUANT")),
    ("cockpit", ["cockpit", M], contains("ne décide ni n'exécute")),
    ("gate", ["gate", M], contains("RECOMMANDE")),
    ("method", ["method", M], None),
    ("templates", ["templates"], None),
    ("agent", ["agent", "--dry-run", "test"], None),
    ("drive-scaffold", ["drive-scaffold", "--mission", M, "--pm", "{out}/drive"], None),
    ("notion-scaffold", ["notion-scaffold", "--mission", M, "--emit-plan"], None),
    ("console", ["console", "--help"], contains("usage")),
    ("reset", ["reset", "--target", "{out}/a-vider"], contains("Rien du framework")),
    # Charte
    ("tones", ["tones", M], None),
]
# Dossier: the build must leave a 16:9 deck and its HTML in the mission folder.
DOSSIER_FILES = ("dossier/dossier.pptx", "dossier/index.html")


def setup(tmp):
    prof = tmp / "profiles"
    shutil.copytree(FIXTURE, prof)
    out = tmp / "out"
    (out / "notes").mkdir(parents=True)
    (out / "notes" / "2026-11-26-point.md").write_text("# Point hebdo\n\nAccès API : clé reçue.\n", encoding="utf-8")
    (out / "a-vider").mkdir()
    (out / "drive").mkdir()
    (out / "images").mkdir()
    (out / "images" / "TEST-1 maquette.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (out / "source.md").write_text("source", encoding="utf-8")
    (out / "sortie.md").write_text("sortie", encoding="utf-8")
    (out / "cr.json").write_text(json.dumps(CR), encoding="utf-8")
    make_risks_xlsx(out / "Risks_TEST.xlsx")
    env = dict(os.environ, PMF_PROFILES=str(prof), PMF_JIRA_ENV="/nonexistent", PMF_TEST_OUT=str(out),
               PMF_RISKS_FILE=str(out / "Risks_TEST.xlsx"), PMF_PROJECT_ROOT=str(out / "projet"),
               CLAUDE_PROJECT_DIR=str(tmp), JIRA_EMAIL="", JIRA_TOKEN="", JIRA_BASE="")
    return prof, out, env


def run_case(name, args, check, out, env):
    is_refusal = isinstance(check, tuple)
    fn = check[0] if is_refusal else check
    argv = [a.replace("{out}", str(out)) for a in args]
    p = subprocess.run([sys.executable, str(ROOT / "framework" / "pm.py"), "run"] + argv, cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=TIMEOUT)
    text = p.stdout + p.stderr
    assert "Traceback" not in text, "traceback :\n" + "\n".join(text.splitlines()[-6:])
    if not is_refusal:
        assert p.returncode == 0, f"code de sortie {p.returncode} :\n" + "\n".join(text.splitlines()[-4:])
    if fn:
        fn(out, text)


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    cases = [c for c in CASES if not only or any(o in c[0] for o in only)]
    tmp = Path(tempfile.mkdtemp(prefix="pmf-livrables-"))
    ok = 0
    try:
        prof, out, env = setup(tmp)
        for name, args, check in cases:
            try:
                run_case(name, args, check, out, env)
                if name == "dossier-build":
                    for f in DOSSIER_FILES:
                        p = prof / M / f
                        assert p.is_file(), f"{f} absent après --build"
                    assert pptx_slides(prof / M / "dossier" / "dossier.pptx") >= 20, "dossier : moins de 20 slides"
                    assert is_html(prof / M / "dossier" / "index.html"), "dossier : HTML incomplet"
                print(f"  PASS {name}")
                ok += 1
            except subprocess.TimeoutExpired:
                print(f"  FAIL {name}: plus de {TIMEOUT} s")
            except AssertionError as e:
                print(f"  FAIL {name}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{ok}/{len(cases)} tests OK")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
