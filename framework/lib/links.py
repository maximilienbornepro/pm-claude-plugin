"""Liens vers un dossier / fichier de l'espace de pilotage, selon le `file_store` du profil.

- sharepoint : lien NAVIGATEUR (jamais un lien de telechargement).
    dossier -> Forms/AllItems.aspx?id=... (encode)
    fichier -> URL directe encodee + ?web=1 (edition en ligne Office)
- onedrive / local : chemin local (synchronise ou non).

Un axe du modele a deux axes `pm_front` (notion|drive) x `file_store` (sharepoint|onedrive|local).
"""
import urllib.parse


def _store(profile):
    s = (profile.get("file_store") or profile.get("drive", {}).get("kind", "") or "").lower()
    if "sharepoint" in s:
        return "sharepoint"
    if "onedrive" in s:
        return "onedrive"
    return s or "local"


def _ws(profile):
    return (profile.get("drive", {}).get("web_site") or "").rstrip("/")   # host/sites/Site


def folder_link(profile, rel_path):
    """rel_path : chemin du dossier relatif a la racine documentaire (ex. '02 - Project Management/06 - Risques')."""
    store = _store(profile)
    if store == "sharepoint":
        ws = _ws(profile)
        site_rel = "/" + ws.split("/", 1)[1] if "/" in ws else ""
        idp = f"{site_rel}/Shared Documents/{rel_path}"
        return f"https://{ws}/Shared%20Documents/Forms/AllItems.aspx?id=" + urllib.parse.quote(idp)
    root = (profile.get("drive", {}).get("root") or "").rstrip("/")
    return f"{root}/{rel_path}" if root else rel_path


def file_link(profile, rel_path):
    """rel_path : chemin du fichier relatif a la racine documentaire."""
    store = _store(profile)
    if store == "sharepoint":
        ws = _ws(profile)
        return f"https://{ws}/Shared%20Documents/" + urllib.parse.quote(rel_path) + "?web=1"
    root = (profile.get("drive", {}).get("root") or "").rstrip("/")
    return f"{root}/{rel_path}" if root else rel_path
