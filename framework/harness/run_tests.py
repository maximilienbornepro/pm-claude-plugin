#!/usr/bin/env python3
"""run_tests - the single test entry point: verifier + every framework/harness/test_*.py.

    python3 framework/pm.py test            # everything (what CI and the pre-commit hook run)
    python3 framework/pm.py test --quick    # verifier + unit tests, without the slow end-to-end suites
    python3 framework/pm.py test planning   # only test files whose name contains "planning"
    python3 framework/pm.py test --install-hook   # run `test --quick` before every git commit

Exit code 0 only if everything passes. Nothing is written outside a temporary folder.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
H = ROOT / "framework" / "harness"
SLOW = {"test_livrables.py", "test_smoke.py"}      # end-to-end: every generator, for real
HOOK = """#!/bin/sh
# pm-framework: tests before every commit (python3 framework/pm.py test --install-hook).
# Skip once with: git commit --no-verify
python3 framework/pm.py test --quick || {
  echo "pm-framework : tests en echec, commit annule (voir ci-dessus)." >&2
  exit 1
}
"""


def install_hook():
    git = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=ROOT, capture_output=True, text=True)
    if git.returncode:
        raise SystemExit("pas un depot git : hook non installe")
    hooks = (ROOT / git.stdout.strip()).resolve()
    hooks.mkdir(parents=True, exist_ok=True)
    p = hooks / "pre-commit"
    if p.exists() and "pm-framework" not in p.read_text(errors="ignore"):
        raise SystemExit(f"{p} existe deja (hook d'un autre outil) : non remplace")
    p.write_text(HOOK)
    p.chmod(0o755)
    print(f"ok : {p} lance `pm test --quick` avant chaque commit")
    return 0


def main(argv):
    if "--install-hook" in argv:
        return install_hook()
    quick = "--quick" in argv
    only = [a for a in argv if not a.startswith("-")]
    files = sorted(H.glob("test_*.py"))
    if only:
        files = [f for f in files if any(o in f.name for o in only)]
    elif quick:
        files = [f for f in files if f.name not in SLOW]
    steps = ([("verifier", [sys.executable, str(H / "verifier.py")])] if not only else []) + \
            [(f.stem, [sys.executable, str(f)]) for f in files]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    failed = []
    t0 = time.time()
    for name, cmd in steps:
        t = time.time()
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
        tail = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]
        if p.returncode == 0:
            print(f"  ok    {name:22s} {time.time() - t:5.1f} s   {tail[-1][:70] if tail else ''}")
        else:
            failed.append(name)
            print(f"  ECHEC {name:22s} {time.time() - t:5.1f} s")
            for ln in [x for x in tail if "FAIL" in x or "ERR" in x or "erreur" in x.lower()][:15] or tail[-15:]:
                print(f"          {ln[:160]}")
    print(f"\n{len(steps) - len(failed)}/{len(steps)} suites OK en {time.time() - t0:.0f} s"
          + (f" - en echec : {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
