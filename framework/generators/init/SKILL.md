---
name: init
description: Amorce une mission - crée les fichiers de profiles/<mission>/ qui manquent à partir des gabarits du moteur (profile.yml, pipeline.yml, gate.yml, method.yaml, tracabilite.yml, routing.yml). Parcours classique de démarrage d'un projet, create-si-absent et idempotent : il ne touche jamais un fichier existant. Dry-run par défaut ; --apply écrit.
meta:
  produces: profil
  consumes: []
  mcp_deps: []
  cost: light
  status: stable
---

# Générateur init (amorçage d'une mission)

Le **point de départ classique** d'un projet : poser le squelette de `profiles/<mission>/` pour pouvoir
commencer. Indépendant de l'orchestrateur `cockpit` (qui n'est qu'une **option** pour résumer l'état
d'une mission déjà amorcée).

## Ce qu'il pose (create-si-absent)

Depuis les gabarits du moteur, uniquement les fichiers **manquants** :

| Fichier | Source |
|---|---|
| `profile.yml` | `config/profile.example.yml` |
| `pipeline.yml` | `config/pipeline.example.yml` |
| `gate.yml` | `framework/generators/gate/gtf.sample.yml` (les 7 portes GTF) |
| `method.yaml` | squelette (baremes / seuils / trames / tracabilite) |
| `tracabilite.yml` | squelette (phase_courante + items) |
| `routing.yml` | squelette (exceptions de routage seulement) |

**Jamais d'écrasement** : un fichier déjà présent est laissé tel quel (cf. FRAMEWORK « ne jamais
écraser l'existant »). Relancer `init` sur une mission déjà amorcée ne crée que ce qui manque.

## Usage

```
python3 framework/pm.py run init <mission>            # plan : ce qui serait créé (dry-run)
python3 framework/pm.py run init <mission> --apply     # crée les fichiers manquants
```

## La suite du parcours

1. `pm run init <mission>` - poser le squelette.
2. `pm run setup <mission>` - compléter le profil champ par champ (onboarding guidé).
3. `pm run drive-scaffold <mission>` / `notion-scaffold <mission>` - l'arborescence (create-si-absent).
4. `pm run cockpit <mission>` - **option** : où en est la mission, que fait-on ?

Détail du parcours manuel : `docs/nouvelle-mission.md`.
