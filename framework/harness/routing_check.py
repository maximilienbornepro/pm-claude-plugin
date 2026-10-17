#!/usr/bin/env python3
"""routing_check - compare le routage DÉRIVÉ des métadonnées au routage DÉCLARÉ dans routing.yml.

A1 (plan d'action). Le compte d'un générateur se DÉRIVE de son `cost` (meta du SKILL.md) :
heavy-local -> compte « lourd » (perso) ; sinon -> compte par défaut. Ce harnais montre, par
générateur : le coût, les connecteurs, le compte déclaré (routing.yml), le compte dérivé, et l'état :
  · AUTO       : rien de déclaré, la dérivation suffit ;
  · redondant  : déclaré == dérivé -> l'entrée de routing.yml peut être retirée ;
  · EXCEPTION  : déclaré != dérivé -> override assumé, à GARDER dans routing.yml (et à vérifier) ;
Il signale aussi un générateur dérivé « perso » qui a pourtant des mcp_deps (le preflight devra
vérifier ces connecteurs sur le compte perso).

    python3 framework/harness/routing_check.py [mission]      # défaut : demo
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof          # noqa: E402
import generator_meta as gm     # noqa: E402


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "demo"
    try:
        p = prof.load(mission)["profile"]
    except Exception as e:
        print(f"[!] profil '{mission}' illisible : {e}"); return 2
    orch = p.get("orchestration") or {}
    default_account = orch.get("default_account")
    heavy_account = orch.get("heavy_account") or "perso"
    policy = orch.get("routing_policy") or "by-connector"

    routing = {}
    try:
        routing = (prof._load_yaml(prof.mission_dir(mission) / "routing.yml") or {}).get("routing") or {}
    except Exception:
        pass

    gens = gm.load_all()
    avec_meta = {n: g for n, g in gens.items() if g["meta"]}

    print(f"Mission : {mission}   politique={policy}   défaut={default_account}   lourd={heavy_account}")
    print(f"Générateurs avec meta : {len(avec_meta)} / {len(gens)}\n")
    print(f"{'générateur':22} {'cost':11} {'mcp_deps':16} {'déclaré':8} {'dérivé':8} état")
    print("-" * 78)

    redondants, exceptions, sans_meta_declares = [], [], []
    for n in sorted(avec_meta):
        meta = avec_meta[n]["meta"]
        deps = ",".join(meta.get("mcp_deps") or []) or "-"
        declared = routing.get(n)
        derived = gm.derive_account(meta, default_account, heavy_account, policy)
        if declared is None:
            etat = "AUTO (dérivé suffit)"
        elif declared == derived:
            etat = "redondant -> retirable"; redondants.append(n)
        else:
            etat = f"EXCEPTION ({declared} assumé)"; exceptions.append(n)
        note = "  ⚠ perso + connecteurs" if derived == heavy_account and (meta.get("mcp_deps")) else ""
        print(f"{n:22} {str(meta.get('cost')):11} {deps:16} {str(declared or '-'):8} {str(derived or '-'):8} {etat}{note}")

    # entrées de routing.yml qui n'ont aucun générateur à meta (restent à migrer)
    for n in sorted(routing):
        if n not in avec_meta and n in gens:
            sans_meta_declares.append(n)

    print("\nBilan :")
    print(f"  · {len(redondants)} entrée(s) routing.yml REDONDANTE(S) (dérivées à l'identique) : "
          + (", ".join(redondants) or "aucune"))
    print(f"  · {len(exceptions)} EXCEPTION(S) à garder dans routing.yml : " + (", ".join(exceptions) or "aucune"))
    if sans_meta_declares:
        print(f"  · {len(sans_meta_declares)} générateur(s) routés mais SANS meta (à équiper au déploiement) : "
              + ", ".join(sans_meta_declares))
    print("\n→ Une fois toutes les meta posées, routing.yml ne garde que les EXCEPTIONS ci-dessus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
