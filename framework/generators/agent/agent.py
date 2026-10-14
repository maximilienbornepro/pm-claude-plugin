#!/usr/bin/env python3
"""agent - lance une sous-tache sur l'agent choisi : COMPTE (connecteurs isoles), MODELE, SPECIALITE.

Trois axes, combinables :
  --account <nom>   compte Claude a utiliser (via CLAUDE_CONFIG_DIR) -> son jeu de connecteurs.
                    L'isolation est PHYSIQUE : le compte perso n'a pas les connecteurs du compte pro.
  --model   <alias> opus / sonnet / haiku / fable (ou opus-5.5 ...). Defaut : profil puis session.
  --agent   <nom>   une specialite de framework/agents/<nom>.md (ses instructions en contexte).

Resolution du compte : --account -> profile.orchestration.default_account -> session courante.
Les comptes (chemins de config dir) vivent dans config/accounts.yml (niveau POSTE), jamais dans le profil.
Mono-compte : pas de accounts.yml / pas de --account -> tout tourne sur la session courante (no-op compte).

    pm run agent [--account N] [--model M] [--agent A] [--mission m] [--dry-run] "<tache>"

Securite : chaque worker fait tourner le preflight de SA session ; un worker perso ne peut pas toucher
les donnees du compte pro (connecteurs absents). Rien n'est ecrit par ce script : il delegue a `claude -p`.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402

MODELS = {"opus": "opus", "sonnet": "sonnet", "haiku": "haiku",
          "fable": "claude-fable-5-1",
          "opus-5.5": "claude-opus-5-5", "sonnet-5.5": "claude-sonnet-5-5",
          "haiku-5.5": "claude-haiku-5-5", "fable-5.1": "claude-fable-5-1"}


def _accounts():
    for p in (ROOT / "config" / "accounts.yml", Path.home() / ".pm-accounts.yml"):
        if p.exists():
            try:
                return prof._load_yaml(p) or {}
            except Exception:
                return {}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task", nargs="*", help="la sous-tache (prompt)")
    ap.add_argument("--account")
    ap.add_argument("--model")
    ap.add_argument("--agent")
    ap.add_argument("--command", help="nom d'une commande -> compte via la table de routage (mode multi)")
    ap.add_argument("--mission", default="sinbad")
    ap.add_argument("--dry-run", action="store_true", help="montre la commande, ne lance rien")
    a = ap.parse_args()

    task = " ".join(a.task).strip()
    if not task:
        print('usage: pm run agent [--account N] [--model M] [--agent A] "<tache>"'); return 2

    acc_cfg = _accounts()
    accounts = acc_cfg.get("accounts") or {}
    orch = {}
    try:
        orch = prof.load(a.mission)["profile"].get("orchestration") or {}
    except Exception:
        pass

    # --- compte -> config_dir ---
    # Ordre : --account explicite -> table de routage (commande, mode multi) -> defaut mission -> session.
    cmd_name = a.command or a.agent
    routed = prof.account_for(a.mission, cmd_name) if cmd_name else None
    acct = a.account or routed or orch.get("default_account")
    explicit = bool(a.account)
    config_dir = None
    if acct:
        info = accounts.get(acct)
        if not info:
            if explicit:
                print(f"[!] compte '{acct}' absent de config/accounts.yml "
                      f"(comptes: {', '.join(accounts) or 'aucun'}). Le definir d'abord."); return 2
            print(f"(compte par defaut '{acct}' non defini dans accounts.yml -> session courante)")
            acct = None
        else:
            config_dir = os.path.expanduser(str(info.get("config_dir", "")))

    # --- modele ---
    model = a.model or orch.get("default_model") or acc_cfg.get("default_model")
    model_id = MODELS.get(model, model) if model else None

    # --- prompt (+ specialite) ---
    prompt = task
    if a.agent:
        apath = ROOT / "framework" / "agents" / f"{a.agent}.md"
        if not apath.exists():
            print(f"[!] agent '{a.agent}' introuvable dans framework/agents/."); return 2
        prompt = (f"Tu agis selon l'agent « {a.agent} ». Suis ses instructions ci-dessous.\n\n"
                  + apath.read_text(encoding="utf-8") + f"\n\n--- TACHE ---\n{task}")

    print(f"agent  : {a.agent or '(aucun)'}")
    print(f"compte : {acct or '(session courante)'}" + (f"  [{config_dir}]" if config_dir else ""))
    print(f"modele : {model_id or '(defaut de la session)'}")

    if config_dir and not Path(config_dir).exists():
        print(f"\n[!] config dir absent : {config_dir}")
        print(f"    se logger d'abord une fois : CLAUDE_CONFIG_DIR={config_dir} claude"); return 2

    cmd = ["claude"]
    if model_id:
        cmd += ["--model", model_id]
    cmd += ["-p", prompt]
    env = dict(os.environ)
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = config_dir

    if a.dry_run:
        shown = f"CLAUDE_CONFIG_DIR={config_dir} " if config_dir else ""
        shown += "claude " + (f"--model {model_id} " if model_id else "") + '-p "<tache>"'
        print("\nDRY-RUN. Commande equivalente :\n  " + shown); return 0

    r = subprocess.run(cmd, env=env, text=True, capture_output=True)
    sys.stdout.write(r.stdout or "")
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
