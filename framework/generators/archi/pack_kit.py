#!/usr/bin/env python3
"""pack_kit - fabrique le kit portable du generateur de schemas d'archi (un zip a envoyer).

    python3 pack_kit.py                 # reconstruit le zip
    python3 pack_kit.py --if-stale      # ne reconstruit que si une source a change (hook, rapide)
    python3 pack_kit.py --quiet         # silencieux (hook)

Sortie : <pm-framework>/dist/archi-kit.zip, copie sur le Bureau (~/Desktop/archi-kit.zip) si le
dossier existe (variable ARCHI_KIT_COPY pour un autre chemin, vide pour ne pas copier).
Le kit est autonome (Python 3.9+, aucune dependance) : generateur, feuille de style de reference,
moteur d'import draw.io, logos partages, exemples et LISEZMOI.md. Il ne contient AUCUNE donnee de
mission (garde-fou : refus si un identifiant sensible est trouve).

Le zip est tenu a jour automatiquement : hook PostToolUse du plugin (hooks/hooks.json) qui appelle
ce script en --if-stale apres chaque modification, et publish.sh qui le reconstruit a chaque version.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent                 # framework/generators/archi
FW = HERE.parents[1]                                   # framework
ROOT = FW.parent                                       # pm-framework
DIST = ROOT / "dist"
ZIP = DIST / "archi-kit.zip"

MODULES = ["abstraction.py", "build_html.py", "enrich.py", "export_drawio.py", "golden.py",
           "import_drawio.py", "import_view.py", "validate.py", "render.py",
           "golden_style.css", "golden_import.js", "SCHEMA.md"]
# motifs interdits dans le kit (assembles a l'execution pour ne pas figurer en clair dans ce fichier)
_PARTS = [("operation", "canard"), ("safranai", r"\.sharepoint"), ("/Users", "/[a-z]+"), ("claude", r"\.ai/artifact"),
          ("verbose", "-enigma"), ("c2fd", "2206")]
SENSITIVE = re.compile("|".join(x + y for x, y in _PARTS))

ARCHI_PY = r'''#!/usr/bin/env python3
"""archi.py - point d'entree du kit (voir LISEZMOI.md).

    python3 archi.py demo                                   # genere exemples/demo.html
    python3 archi.py build modele.json [-o schema.html]     # modele -> schema HTML interactif
    python3 archi.py import fichier.drawio [-o modele.json] [--enrich] [--page "Nom de page"]
    python3 archi.py import-view modele.json --view <id> fichier.drawio [--page N] [-o sortie.json]
    python3 archi.py export modele.json [-o schema.drawio]  # modele -> draw.io (une page par vue)
    python3 archi.py check schema.html                      # 7 invariants (avant de partager)
"""
import json, os, subprocess, sys
from pathlib import Path

K = Path(__file__).resolve().parent
A = K / "framework" / "generators" / "archi"
sys.path.insert(0, str(A))
sys.path.insert(0, str(K / "framework" / "lib"))


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def run(script, *args):
    return subprocess.call([sys.executable, str(A / script), *args])


def main(a):
    if not a or a[0] in ("-h", "--help", "help"):
        print(__doc__); return 0
    cmd, rest = a[0], a[1:]
    if cmd == "demo":
        out = str(K / "exemples" / "demo.html")
        rc = run("build_html.py", str(K / "exemples" / "model.json"), "-o", out)
        print("Ouvrir dans le navigateur :", out); return rc
    if cmd == "build":
        model = rest[0]
        out = opt(rest, "-o", str(Path(model).with_suffix(".html")))
        rc = run("build_html.py", model, "-o", out)
        if rc == 0:
            run("validate.py", out)
        return rc
    if cmd == "import":
        src = rest[0]
        out = opt(rest, "-o", str(Path(src).with_suffix("")) + ".model.json")
        rc = run("import_drawio.py", src, "-o", out)
        if rc == 0 and "--enrich" in rest:
            args = [out, "-o", out]
            if "--page" in rest:
                args += ["--page", opt(rest, "--page")]
            rc = run("enrich.py", *args)
        return rc
    if cmd == "import-view":
        return run("import_view.py", *rest)
    if cmd == "export":
        import export_drawio as X
        model = json.load(open(rest[0], encoding="utf-8"))
        xml, _, missing = X.build_xml(model)
        out = opt(rest, "-o", str(Path(rest[0]).with_suffix(".drawio")))
        Path(out).write_text(xml, encoding="utf-8")
        print("Ecrit :", out); return 0
    if cmd == "check":
        return run("validate.py", rest[0])
    print("Commande inconnue :", cmd); print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''

SEQ_EXAMPLE = """<mxfile><diagram name="Authentification"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="u" value="Utilisateur" style="shape=umlLifeline;perimeter=lifelinePerimeter;" vertex="1" parent="1"><mxGeometry x="40" y="40" width="100" height="320" as="geometry"/></mxCell>
<mxCell id="a" value="Application (front / BFF)" style="shape=umlLifeline;" vertex="1" parent="1"><mxGeometry x="240" y="40" width="160" height="320" as="geometry"/></mxCell>
<mxCell id="k" value="Keycloak" style="shape=umlLifeline;" vertex="1" parent="1"><mxGeometry x="460" y="40" width="120" height="320" as="geometry"/></mxCell>
<mxCell id="m1" value="ouvrir l'application" edge="1" parent="1" source="u" target="a"><mxGeometry relative="1" as="geometry"><mxPoint x="90" y="120" as="sourcePoint"/><mxPoint x="320" y="120" as="targetPoint"/></mxGeometry></mxCell>
<mxCell id="m2" value="redirection OIDC" edge="1" parent="1" source="a" target="k"><mxGeometry relative="1" as="geometry"><mxPoint x="320" y="160" as="sourcePoint"/><mxPoint x="520" y="160" as="targetPoint"/></mxGeometry></mxCell>
<mxCell id="m3" value="code d'autorisation" style="dashed=1;" edge="1" parent="1" source="k" target="a"><mxGeometry relative="1" as="geometry"><mxPoint x="520" y="200" as="sourcePoint"/><mxPoint x="320" y="200" as="targetPoint"/></mxGeometry></mxCell>
<mxCell id="m4" value="session ouverte" style="dashed=1;" edge="1" parent="1" source="a" target="u"><mxGeometry relative="1" as="geometry"><mxPoint x="320" y="240" as="sourcePoint"/><mxPoint x="90" y="240" as="targetPoint"/></mxGeometry></mxCell>
</root></mxGraphModel></diagram></mxfile>
"""

README = """# Kit du générateur de schémas d'architecture

Version {version} - fabriqué le {date}.

Ce kit produit un **schéma d'architecture interactif** : une seule page HTML, navigable (on clique
sur une zone pour descendre dans son détail), avec thème clair et sombre, diagrammes de séquence et
import de fichiers draw.io. La page s'ouvre dans n'importe quel navigateur et s'envoie telle quelle.

## Prérequis

- **Python 3.9 ou plus**, rien d'autre à installer. Vérifier : `python3 --version`.
- Un navigateur (Chrome, Edge, Firefox, Safari).

## Démarrer en 1 minute

```bash
cd archi-kit
python3 archi.py demo
```

Puis ouvrir `exemples/demo.html` dans le navigateur. Cliquer sur un bloc avec une loupe pour
descendre dans son détail ; le fil d'Ariane et le bouton retour ramènent à la vue d'ensemble.

## Le principe : par prompt, avec un template

Le schéma ne s'édite pas dans le navigateur. On le décrit (prompt) ou on part d'un draw.io, on obtient
un **modèle** (`model.json`, format `SCHEMA.md`), et `build` le rend au style de référence. Pour le
faire évoluer, on modifie le modèle (à la main ou en le demandant à Claude), puis on relance `build`.

## Les trois façons de faire un schéma

### 1. Depuis un draw.io existant

```bash
python3 archi.py import mon_schema.drawio -o mon_modele.json --enrich --page "Nom de la page"
python3 archi.py build mon_modele.json -o mon_schema.html
```

- `import` lit le draw.io (zones, boîtes, flèches, libellés) et en fait un modèle `mon_modele.json`.
- `--enrich` ajoute les rôles et couleurs, le chemin principal animé, les loupes, une vue de détail
  par zone et le cadre Kubernetes / namespace. Il affiche aussi les **questions à se poser**
  (Kubernetes, exploitation, REST API, SSO).
- `build` génère la page HTML, puis contrôle 7 invariants (flèches droites, navigation, logos…).

### 2. En écrivant le modèle

Partir de `exemples/model.json` : des `zones` (cadres, imbriquables par `parent`), des
`entities` (blocs, rangés dans une `zone`), des `flows` (flèches `from` → `to`, `label`,
`main: true` pour le chemin principal animé, `kind: auth` pour l'authentification) et des `views`
(la première est la vue d'ensemble, les suivantes les vues de détail). Le contrat complet est dans
`framework/generators/archi/SCHEMA.md`.

Couleurs de rôle (`color`) : `core` violet, `service` vert, `auth` rose, `storage` orange,
`db` bleu (cylindre), `cluster` bleu Kubernetes, `risk` rouge, `ops` ambre, `partner` cyan, `ext` gris.

Une zone qui a sa propre vue (`"link": "<id de la vue>"`) devient un bloc cliquable en entier.

### 3. Un diagramme de séquence

Dans le modèle, une vue `"kind": "sequence"` :

```json
{{"id": "auth", "label": "Authentification", "kind": "sequence",
 "caption": "Connexion par SSO (OIDC)",
 "participants": [{{"id": "u", "label": "Utilisateur", "color": "ext"}},
                  {{"id": "k", "label": "Keycloak", "color": "auth"}}],
 "messages": [{{"from": "u", "to": "k", "label": "se connecter"}},
              {{"from": "k", "to": "u", "label": "session ouverte", "kind": "return"}}],
 "notes": ["Une ligne de commentaire sous le diagramme."]}}
```

## Remplacer une vue par un draw.io

- Pas de bouton dans la page : l'import se fige **dans le modèle**, puis on regénère. Le draw.io est
  rendu en **schéma** (boîtes et zones) par défaut, `--sequence` pour un diagramme de séquence.
  Essai : `exemples/sequence.drawio`.

```bash
python3 archi.py import-view mon_modele.json --view <id_de_la_vue> mon_detail.drawio [--sequence] -o mon_modele.json
python3 archi.py build mon_modele.json -o mon_schema.html
```

## Repartir vers draw.io

```bash
python3 archi.py export mon_modele.json -o mon_schema.drawio
```

Une page draw.io par vue, éditable ensuite dans draw.io.

## Partager le résultat

La page HTML est autonome (styles, logos et scripts embarqués ; seules les polices viennent de
Google Fonts). On l'envoie par mail, on la dépose sur un SharePoint ou sur GitHub Pages. Avant de
partager : `python3 archi.py check mon_schema.html` doit afficher « TOUT PASSE ».

## Contenu du kit

- `archi.py` : point d'entrée (les commandes ci-dessus).
- `framework/generators/archi/` : le générateur (Python, sans dépendance), la feuille de style de
  référence (`golden_style.css`) et le moteur de rendu des séquences et des imports figés (`golden_import.js`).
- `framework/assets/logos/` : logos partagés (Kubernetes, AWS, Keycloak, React…). Pour un logo
  à vous, ajoutez-le au modèle dans `logos` (`"nom": "data:image/png;base64,..."`) et référencez-le
  par `"logo": "nom"`.
- `exemples/` : un modèle de démonstration et un draw.io de séquence.

## En cas de souci

- `python3: command not found` : installer Python 3 (python.org), ou essayer `python`.
- Un logo n'apparaît pas : la clé `logo` doit exister dans `logos` du modèle ou dans `framework/assets/logos`.
- Page blanche : ouvrir la console du navigateur ; regénérer avec `build`, puis `check`.
"""


def sources():
    files = [HERE / m for m in MODULES] + [FW / "lib" / "profile.py", Path(__file__).resolve(),
                                          ROOT / "profiles" / "demo" / "architecture" / "model.json"]
    files += sorted((FW / "assets" / "logos").glob("*"))
    return [f for f in files if f.is_file()]


def digest(files):
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


def version():
    try:
        return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version", "?")
    except Exception:
        return "?"


def stale(files):
    stamp = DIST / "archi-kit.stamp"
    return not ZIP.exists() or not stamp.exists() or stamp.read_text().strip() != digest(files)


def build(quiet=False):
    files = sources()
    tmp = Path(tempfile.mkdtemp())
    kit = tmp / "archi-kit"
    (kit / "framework" / "generators" / "archi").mkdir(parents=True)
    (kit / "framework" / "lib").mkdir(parents=True)
    (kit / "framework" / "assets" / "logos").mkdir(parents=True)
    (kit / "exemples").mkdir()
    for m in MODULES:
        if (HERE / m).exists():
            shutil.copy2(HERE / m, kit / "framework" / "generators" / "archi" / m)
    shutil.copy2(FW / "lib" / "profile.py", kit / "framework" / "lib" / "profile.py")
    for f in (FW / "assets" / "logos").glob("*"):
        if f.is_file():
            shutil.copy2(f, kit / "framework" / "assets" / "logos" / f.name)
    shutil.copy2(ROOT / "profiles" / "demo" / "architecture" / "model.json", kit / "exemples" / "model.json")
    (kit / "exemples" / "sequence.drawio").write_text(SEQ_EXAMPLE, encoding="utf-8")
    (kit / "archi.py").write_text(ARCHI_PY, encoding="utf-8")
    ver = version()
    (kit / "LISEZMOI.md").write_text(README.format(version=ver, date=time.strftime("%d/%m/%Y %H:%M")),
                                     encoding="utf-8")
    # garde-fou : aucune donnee de mission
    bad = []
    for f in kit.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".md", ".json", ".js", ".css", ".drawio"):
            if SENSITIVE.search(f.read_text(encoding="utf-8", errors="ignore")):
                bad.append(str(f.relative_to(kit)))
    if bad:
        print("[pack_kit] identifiant sensible trouve, zip NON produit :", ", ".join(bad), file=sys.stderr)
        return 1
    # essai a blanc : le kit doit generer la demo tout seul, hors du framework
    rc = subprocess.call([sys.executable, "-I", str(kit / "archi.py"), "demo"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(tmp))
    if rc != 0 or not (kit / "exemples" / "demo.html").exists():
        print("[pack_kit] le kit ne genere pas la demo, zip NON produit.", file=sys.stderr)
        return 1
    DIST.mkdir(exist_ok=True)
    part = ZIP.with_suffix(".zip.part")
    with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(kit.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                z.write(f, f.relative_to(tmp))
    os.replace(part, ZIP)
    (DIST / "archi-kit.stamp").write_text(digest(files))
    copy = os.environ.get("ARCHI_KIT_COPY", str(Path.home() / "Desktop" / "archi-kit.zip"))
    if copy and Path(copy).parent.is_dir():
        shutil.copy2(ZIP, copy)
    shutil.rmtree(tmp, ignore_errors=True)
    if not quiet:
        print(f"Kit : {ZIP} ({ZIP.stat().st_size // 1024} Ko, version {ver})" + (f" ; copie : {copy}" if copy else ""))
    return 0


def main(argv):
    quiet = "--quiet" in argv
    if "--if-stale" in argv and not stale(sources()):
        return 0
    return build(quiet)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
