#!/usr/bin/env python3
"""set_tone - aligne le ton de chaque agent sur la config du pipeline.

Source de vérité : `profiles/<mission>/pipeline.yml`, table `agents` (nom -> ton | null).
Pour chaque agent, on garantit que le champ `skills:` de son fichier d'agent préchargue le
bon ton (mécanisme natif Claude Code), sans toucher au reste. Les autres tons éventuels sont
retirés (un seul ton par agent) ; les skills non-ton sont conservés.

    python3 set_tone.py <mission> [--agents-dir DIR] [--apply]
Dry-run par défaut (montre l'écart, n'écrit rien). --apply réécrit la ligne `skills:`.
"""
import sys, re, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile as prof  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
# Les tons = les skills de redaction du framework (dossiers de framework/skills/) : decouverte
# dynamique, aucune liste de tons codee en dur -> portable d'une mission a l'autre.
_SKILLS = ROOT / "framework" / "skills"
TONES = {p.name for p in _SKILLS.iterdir() if p.is_dir()} if _SKILLS.is_dir() else set()


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else None


def _skills_in(fm):
    if fm is None:
        return None
    m = re.search(r"^skills:\s*\[(.*?)\]\s*$", fm, re.M)
    if m:
        return [s.strip().strip("'\"") for s in m.group(1).split(",") if s.strip()]
    m = re.search(r"^skills:\s*(\S+)\s*$", fm, re.M)
    if m:
        return [m.group(1).strip("'\"")]
    return []  # frontmatter sans ligne skills


def desired(current, tone):
    base = [s for s in (current or []) if s not in TONES]
    return base + ([tone] if tone else [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mission")
    ap.add_argument("--agents-dir", default=str(ROOT / "framework" / "agents"))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    agents = prof.load(args.mission)["pipeline"].get("agents", {})
    adir = Path(args.agents_dir)
    print(f"Mission {args.mission} - agents dir: {adir}\n")

    changed = 0
    for name, tone in agents.items():
        f = adir / f"{name}.md"
        if not f.exists():
            print(f"  [absent]  {name:24s} ton visé: {tone}  (pas de fichier d'agent)")
            continue
        text = f.read_text(encoding="utf-8")
        cur = _skills_in(_frontmatter(text))
        want = desired(cur, tone)
        if (cur or []) == want:
            print(f"  [ok]      {name:24s} ton: {tone}")
            continue
        changed += 1
        print(f"  [à régler]{name:24s} {cur} -> {want}")
        if args.apply:
            fm = _frontmatter(text)
            line = f"skills: [{', '.join(want)}]" if want else "skills: []"
            if re.search(r"^skills:.*$", fm, re.M):
                newfm = re.sub(r"^skills:.*$", line, fm, count=1, flags=re.M)
            else:
                newfm = fm + "\n" + line
            f.write_text(text.replace(fm, newfm, 1), encoding="utf-8")
    print(f"\n{changed} agent(s) à régler." + ("" if args.apply else "  (dry-run, rien écrit)"))


if __name__ == "__main__":
    main()
