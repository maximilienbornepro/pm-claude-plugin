#!/usr/bin/env python3
"""Helper image Jira generique du pm-framework - LECTURE SEULE / DRY-RUN par defaut.

Pourquoi ce helper existe
-------------------------
Le connecteur Jira (Atlassian) edite tres bien le TEXTE d'un ticket, mais il **ne sait pas
uploader de piece jointe ni poser une image**. Une mission serieuse utilise donc **deux outils
ensemble** :
  - le connecteur, pour le texte, sous garde-fou anti-ecrasement (framework/hooks/pas_ecraser_jira.py) ;
  - l'API REST (ce helper), pour UPLOADER et RETABLIR l'image d'un ticket.
Regle de mission : « l'image ne saute jamais ». Toute reecriture de description peut effacer la
section image ; apres chaque modification on re-verifie (`check`) et, si besoin, on remet l'image.

Ce que fait ce helper
---------------------
Pour chaque ticket qui a une image locale rangee dans le dossier de la mission :
  - CHECK  (defaut) : lit le ticket et dit si l'image attendue est affichee sous le titre de
            section configure. Aucune ecriture.
  - DRY-RUN : liste ticket -> fichier retenu, SANS AUCUN appel a Jira.
  - APPLY  (derriere le flag explicite --apply) : upload (ou reutilisation de la piece jointe du
            meme nom) puis insertion de l'image sous le titre de section. C'est le SEUL mode qui
            ecrit dans Jira ; il faut le demander explicitement.

Config
------
  - Jira (base, identifiants) : exactement comme framework/lib/jira.py
      JIRA_EMAIL / JIRA_TOKEN dans l'env, base JIRA_BASE optionnelle (sinon derivee de
      jira.instance du profil). A defaut d'identifiants dans l'env, pointer un fichier .env via
      PMF_JIRA_ENV (ex. scan-jira/.env). Les secrets ne sont jamais affiches.
  - Mission (titre de section, dossier d'images, nommage, garde-fou) :
      profiles/<mission>/jira_ticket.yml  (gabarit commente : jira_ticket.example.yml)

Usage (lecture seule par defaut)
--------------------------------
  PMF_JIRA_ENV=.../scan-jira/.env python3 jira_image.py <mission>                 # check, tous
  PMF_JIRA_ENV=.../scan-jira/.env python3 jira_image.py <mission> SIN-105 SIN-98  # check, cibles
  python3 jira_image.py <mission> --dry-run                                       # aucun appel Jira
  python3 jira_image.py <mission> --apply SIN-105                                 # ECRIT (sur accord)

Aucune dependance (Python 3 standard). Ne supprime jamais rien : les anciennes pieces jointes
restent attachees au ticket.
"""
import os
import re
import sys
import glob
import json
import time
import struct
import collections
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]                                   # .../pm-framework
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof                                   # noqa: E402
import jira as jira_mod                                  # noqa: E402


# ----------------------------------------------------------------- config mission
def load_image_cfg(mission):
    """Section `image` de profiles/<mission>/jira_ticket.yml, avec des defauts surs."""
    path = prof.mission_dir(mission) / "jira-images.yml"
    if not path.exists():
        sys.exit(f"Config mission introuvable : {path}\n"
                 f"Copier framework/generators/jira_ticket/jira_ticket.example.yml et l'adapter.")
    cfg = (prof._load_yaml(path) or {}).get("image", {}) or {}
    cfg.setdefault("section_title", "Figma / Prototype")
    cfg.setdefault("section_match", "figma")             # sous-chaine (minuscule) du titre existant
    cfg.setdefault("file_glob", "*.png")
    cfg.setdefault("key_pattern", r"[A-Z]+-\d+")          # clef lue dans le prefixe du nom de fichier
    cfg.setdefault("pick", "most_recent_mtime")
    cfg.setdefault("content_type", "image/png")
    cfg.setdefault("guard_media_single", True)           # le nb de mediaSingle ne doit pas baisser
    root = cfg.get("images_root")
    if not root:
        sys.exit("jira_ticket.yml : `image.images_root` est obligatoire (dossier des images).")
    cfg["images_root"] = os.path.expanduser(str(root))
    return cfg


# ----------------------------------------------------------------- client (auth comme lib/jira.py)
class ImageClient:
    """S'appuie sur framework/lib/jira.py pour base + identifiants (meme auth, meme env)."""

    def __init__(self, mission):
        j = jira_mod.Jira(mission)                       # charge l'env (PMF_JIRA_ENV) et l'auth
        self.base = j.base
        self._headers = {"Authorization": j.auth}
        self._no_redirect = urllib.request.build_opener(_NoRedirect)

    def _req(self, method, path, data=None, extra=None):
        h = {"Authorization": self._headers["Authorization"], "Accept": "application/json",
             "Content-Type": "application/json"}
        if extra:
            h.update(extra)
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        return urllib.request.urlopen(req, timeout=60)

    # -- lecture seule -------------------------------------------------
    def get_issue(self, key, fields):
        try:
            r = self._req("GET", f"/rest/api/3/issue/{key}?fields={fields}")
            return json.load(r), None
        except urllib.error.HTTPError as e:
            return None, f"{e.code} {e.read().decode()[:120]}"
        except Exception as e:                           # noqa: BLE001
            return None, str(e)

    def media_uuid(self, att_id):
        """L'ADF exige l'UUID Media Services (pas l'id numerique) : lu dans la redirection 303."""
        req = urllib.request.Request(self.base + f"/rest/api/3/attachment/content/{att_id}",
                                     headers={"Authorization": self._headers["Authorization"]})
        try:
            loc = self._no_redirect.open(req, timeout=30).headers.get("Location", "")
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location", "")
        m = re.search(r"/file/([0-9a-f-]{36})/", loc)
        return m.group(1) if m else None

    # -- ecriture (chemin garde, appele seulement en --apply) ----------
    def upload(self, key, fn, content_type):
        boundary = "----pmf" + str(time.time_ns())
        with open(fn, "rb") as f:
            content = f.read()
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{os.path.basename(fn)}\"\r\nContent-Type: {content_type}\r\n\r\n"
                ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        try:
            r = self._req("POST", f"/rest/api/3/issue/{key}/attachments", data=body,
                          extra={"X-Atlassian-Token": "no-check",
                                 "Content-Type": f"multipart/form-data; boundary={boundary}"})
            return json.load(r)[0]["id"], None
        except urllib.error.HTTPError as e:
            return None, f"{e.code} {e.read().decode()[:120]}"
        except Exception as e:                           # noqa: BLE001
            return None, str(e)

    def put_description(self, key, content):
        body = json.dumps({"fields": {"description":
                          {"type": "doc", "version": 1, "content": content}}}).encode()
        try:
            self._req("PUT", f"/rest/api/3/issue/{key}", data=body)
            return True, None
        except urllib.error.HTTPError as e:
            return False, f"{e.code} {e.read().decode()[:120]}"
        except Exception as e:                           # noqa: BLE001
            return False, str(e)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None


# ----------------------------------------------------------------- ADF / section image
def _heading_text(node):
    return "".join(x.get("text", "") for x in node.get("content", []))


def section_state(content, base, match):
    """Etat de la section image : (index du titre|None, 'ok'|'autre'|'manquante', alts vus)."""
    fidx = next((i for i, n in enumerate(content)
                 if n.get("type") == "heading" and match in _heading_text(n).lower()), None)
    if fidx is None:
        return None, "manquante", []
    alts = []
    for j in range(fidx + 1, min(fidx + 6, len(content))):
        n = content[j]
        if n.get("type") == "heading":
            break
        if n.get("type") == "mediaSingle":
            alts.append(n["content"][0]["attrs"].get("alt") or "?")
    if base in alts:
        return fidx, "ok", alts
    return fidx, ("autre" if alts else "manquante"), alts


def _count_media_single(content):
    return sum(1 for n in content if n.get("type") == "mediaSingle")


def _png_size(fn):
    with open(fn, "rb") as f:
        head = f.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">ii", head[16:24])
    return 1200, 800                                     # repli neutre si format inconnu


# ----------------------------------------------------------------- selection des cibles
def targets_for(cfg, only):
    byticket = collections.defaultdict(list)
    pat = re.compile(r"(" + cfg["key_pattern"] + r")")
    for f in glob.glob(os.path.join(cfg["images_root"], "**", cfg["file_glob"]), recursive=True):
        m = pat.match(os.path.basename(f))
        if m:
            byticket[m.group(1)].append(f)
    chosen = {k: max(v, key=os.path.getmtime) for k, v in byticket.items()}
    if only:
        chosen = {k: v for k, v in chosen.items() if k in only}
    return chosen


def _sort_keys(keys):
    def num(k):
        m = re.search(r"(\d+)$", k)
        return int(m.group(1)) if m else 0
    return sorted(keys, key=num)


# ----------------------------------------------------------------- operations
def op_check(cli, cfg, key, fn):
    data, e = cli.get_issue(key, "description")
    if not data:
        return "err", f"GET {e}"
    content = (data["fields"].get("description") or {}).get("content", [])
    fidx, state, alts = section_state(content, os.path.basename(fn), cfg["section_match"])
    if state == "ok":
        return "ok", "image en place"
    if state == "autre":
        return "autre", "autre image affichee : " + ", ".join(alts)
    return "manquante", ("pas de titre de section" if fidx is None else "titre sans image")


def op_apply(cli, cfg, key, fn):
    data, e = cli.get_issue(key, "description,attachment")
    if not data:
        return "err", f"GET {e}"
    desc = data["fields"].get("description") or {"type": "doc", "version": 1, "content": []}
    content = desc.get("content", [])
    base = os.path.basename(fn)
    fidx, state, _ = section_state(content, base, cfg["section_match"])
    if state == "ok":
        return "ok", "deja a jour"
    before = _count_media_single(content)

    att = next((a["id"] for a in data["fields"].get("attachment", []) if a["filename"] == base), None)
    if not att:
        att, e = cli.upload(key, fn, cfg["content_type"])
        if not att:
            return "err", f"upload {e}"
    uuid = cli.media_uuid(att)
    if not uuid:
        return "err", "uuid introuvable (reessayer dans quelques secondes)"
    w, h = _png_size(fn)
    media = {"type": "mediaSingle", "attrs": {"layout": "align-start"}, "content": [
        {"type": "media", "attrs": {"type": "file", "id": uuid, "alt": base,
                                    "collection": "", "width": w, "height": h}}]}
    if fidx is not None:
        c = list(content)
        j = fidx + 1
        while j < len(c) and c[j].get("type") == "mediaSingle":
            c.pop(j)
        newc = c[:fidx + 1] + [media] + c[fidx + 1:]
    else:
        section = [{"type": "heading", "attrs": {"level": 2},
                    "content": [{"type": "text", "text": cfg["section_title"]}]}, media]
        ins = next((i for i, n in enumerate(content) if n.get("type") == "heading" and i > 0),
                   len(content))
        newc = content[:ins] + section + content[ins:]

    # garde-fou : le nombre de mediaSingle ne doit jamais baisser (une image ne doit pas sauter).
    if cfg["guard_media_single"] and _count_media_single(newc) < before:
        return "err", f"garde-fou mediaSingle : {before} -> {_count_media_single(newc)}, ecriture refusee"
    ok, e = cli.put_description(key, newc)
    return ("done", base) if ok else ("err", f"PUT {e}")


# ----------------------------------------------------------------- CLI
def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        sys.exit("Usage : python3 jira_image.py <mission> [--dry-run|--apply] [CLE ...]")
    mission = args[0]
    args = args[1:]
    dry = "--dry-run" in args
    apply_ = "--apply" in args
    args = [a for a in args if a not in ("--dry-run", "--apply")]
    only = {a.upper() for a in args}
    if dry and apply_:
        sys.exit("--dry-run et --apply sont exclusifs.")

    cfg = load_image_cfg(mission)
    chosen = targets_for(cfg, only)
    if not chosen:
        sys.exit(f"Aucune image trouvee dans {cfg['images_root']} (glob {cfg['file_glob']}).")

    # DRY-RUN : aucun appel a Jira
    if dry:
        for k in _sort_keys(chosen):
            print(f"{k}: {os.path.relpath(chosen[k], cfg['images_root'])}")
        print(f"\n{len(chosen)} ticket(s), aucun appel a Jira (--dry-run)")
        return

    cli = ImageClient(mission)

    # APPLY : le SEUL mode qui ecrit dans Jira
    if apply_:
        done = ok = err = 0
        for k in _sort_keys(chosen):
            status, msg = op_apply(cli, cfg, k, chosen[k])
            if status == "done":
                print(f"{k}: RETABLIE  {msg}"); done += 1
            elif status == "ok":
                ok += 1
            else:
                print(f"{k}: ECHEC  {msg}"); err += 1
            time.sleep(0.3)
        print(f"\nResume : {done} retablie(s) · {ok} deja OK · {err} echec(s) · {len(chosen)} ticket(s)")
        return

    # DEFAUT : CHECK, lecture seule
    counts = collections.Counter()
    for k in _sort_keys(chosen):
        status, msg = op_check(cli, cfg, k, chosen[k])
        counts[status] += 1
        mark = {"ok": "[OK]", "autre": "[~]", "manquante": "[X]", "err": "[!]"}[status]
        print(f"{k}: {mark} {msg}  [{os.path.basename(chosen[k])}]")
        time.sleep(0.2)
    print(f"\nControle (lecture seule) : {counts['ok']} en place · {counts['autre']} autre image · "
          f"{counts['manquante']} manquante(s) · {counts['err']} erreur(s)")
    print("Pour ECRIRE (sur accord explicite) : relancer avec --apply.")


if __name__ == "__main__":
    main()
