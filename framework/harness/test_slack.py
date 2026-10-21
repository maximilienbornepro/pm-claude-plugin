#!/usr/bin/env python3
"""Tests - generateur `slack` (normaliseur, LECTURE SEULE).
python3 framework/harness/test_slack.py

Hors-ligne : valide la normalisation et le filtre de fenetre sur des fixtures. Ne parle jamais a Slack.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "generators" / "slack"))
import read_slack as S  # noqa: E402


def _dump(obj):
    f = Path(tempfile.mkdtemp()) / "slack.json"
    f.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(f)


def test_alias_des_champs():
    rows = S.load_dump(_dump([
        {"ts": "2026-10-13T11:04:00Z", "user": "Guillaume", "channel": "sinbad-sw-squad",
         "text": "metadata TR29-37", "permalink": "https://x"},
        {"date": "2026-10-15", "from": "Pierre", "in": "sinbad-sw-squad", "message": "releasability",
         "thread_ts": "123"},
    ]))
    assert rows[0] == {"date": "2026-10-13", "author": "Guillaume", "channel": "sinbad-sw-squad",
                       "thread": False, "text": "metadata TR29-37", "url": "https://x"}
    assert rows[1]["author"] == "Pierre" and rows[1]["thread"] is True and rows[1]["date"] == "2026-10-15"


def test_enveloppes_tolerees():
    assert len(S.load_dump(_dump({"messages": [{"date": "2026-10-13", "text": "a"}]}))) == 1
    assert len(S.load_dump(_dump({"results": [{"date": "2026-10-13", "text": "a"}]}))) == 1
    assert len(S.load_dump(_dump({"date": "2026-10-13", "text": "seul"}))) == 1


def test_fenetre_de_dates():
    rows = [{"date": "2026-10-11", "text": "avant"}, {"date": "2026-10-13", "text": "dans"},
            {"date": "2026-10-19", "text": "apres"}, {"date": "", "text": "sans date"}]
    rows = [S._norm(r) for r in rows]
    w = S.in_window(rows, "2026-10-12", "2026-10-18")
    assert [r["text"] for r in w] == ["dans"], "fenetre + exclusion des sans-date"


def test_jsonl():
    f = Path(tempfile.mkdtemp()) / "s.jsonl"
    f.write_text('{"date":"2026-10-13","text":"a"}\n{"date":"2026-10-14","text":"b"}\n', encoding="utf-8")
    assert len(S.load_dump(str(f))) == 2


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
