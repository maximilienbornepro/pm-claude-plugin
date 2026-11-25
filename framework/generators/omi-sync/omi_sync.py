#!/usr/bin/env python3
"""Synchro Omi -> Notion perso (base « Notes de réunion », Catégorie = Omi).

Incrementale et idempotente : ne cree une page que pour une conversation Omi terminee
et jamais importee (cle = Omi ID). Recopie le resume Omi et la transcription brute,
sans analyse. Lecture seule cote Omi ; cote Notion, n'ecrit que dans la base cible.

Config (hors depot, droits 600) :
  ~/.config/pm-framework/omi.env            OMI_MCP_KEY=omi_mcp_...
  ~/.config/pm-framework/notion.env         NOTION_TOKEN=ntn_...   (integration perso, Omi uniquement)
  ~/.config/pm-framework/omi-sync-state.json {db, done{omi_id: url}, last_sync}

    python3 omi_sync.py --fetch    # 1) nouvelles conversations -> ~/.config/pm-framework/omi-pending/ (JSON a classer)
    # 2) Claude classe chaque id -> omi-classif.json {id: {mission: <MISSION>|Autre|Perso|A classer, groupe: <sujet>}}
    #    meme `groupe` sur des conversations QUI SE SUIVENT = fusion en une seule page (ecart <= GAP_MIN)
    python3 omi_sync.py --import   # 3) pro -> Notes de reunion (Categorie Omi) ; Perso / A classer -> base perso
    python3 omi_sync.py --unlock [--apply]   # complete les pages « Verrouille (plan payant) » (abonnement Omi actif)
"""
import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CFG = Path.home() / ".config" / "pm-framework"
STATE = CFG / "omi-sync-state.json"
PARIS = ZoneInfo("Europe/Paris")
CATS = {"social", "technology", "work", "business", "personal", "other", "entertainment", "news", "travel",
        "politics", "philosophy", "legal", "history", "education", "finance", "weather", "family", "science"}


def env(name, file):
    if os.environ.get(name):
        return os.environ[name]
    for line in (CFG / file).read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{name} introuvable dans {CFG / file}")


# ---------- Omi (MCP Streamable HTTP) ----------
OMI_URL = "https://api.omi.me/v1/mcp"
OMI_H = {"Authorization": "Bearer " + env("OMI_MCP_KEY", "omi.env"), "Content-Type": "application/json",
         "Accept": "application/json, text/event-stream"}
_sid, _n = None, [1]


def _post(payload, notify=False):
    global _sid
    h = dict(OMI_H)
    if _sid:
        h["Mcp-Session-Id"] = _sid
    for att in range(8):
        try:
            r = urllib.request.urlopen(urllib.request.Request(OMI_URL, json.dumps(payload).encode(), h), timeout=120)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (att + 1)); continue
            raise
    else:
        raise RuntimeError("Omi : limite de debit persistante")
    if not _sid:
        _sid = r.headers.get("Mcp-Session-Id")
    t = r.read().decode()
    if notify or not t.strip():
        return None
    m = re.findall(r"^data: (.*)$", t, re.M)
    return json.loads(m[-1] if m else t)


def omi_init():
    _post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
           "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pm-framework-omi-sync", "version": "1"}}})
    _post({"jsonrpc": "2.0", "method": "notifications/initialized"}, True)


def omi(tool, args):
    time.sleep(3)
    _n[0] += 1
    d = _post({"jsonrpc": "2.0", "id": _n[0], "method": "tools/call", "params": {"name": tool, "arguments": args}})
    if "error" in d:
        raise RuntimeError(str(d["error"])[:200])
    txt = d["result"]["content"][0]["text"]
    if d["result"].get("isError"):
        raise RuntimeError(txt[:200])
    return json.loads(txt)


# ---------- Notion (API officielle) ----------
N_H = {"Authorization": "Bearer " + env("NOTION_TOKEN", "notion.env"), "Notion-Version": "2022-06-28",
       "Content-Type": "application/json"}


def notion(method, path, data=None):
    for att in range(8):
        time.sleep(0.35)
        req = urllib.request.Request("https://api.notion.com/v1" + path,
                                     json.dumps(data).encode() if data is not None else None, N_H, method=method)
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 * (att + 1)); continue
            raise RuntimeError(f"Notion {e.code} {e.read().decode()[:200]}")
    raise RuntimeError("Notion indisponible")


def rt(text):
    return [{"type": "text", "text": {"content": text[i:i + 1900]}} for i in range(0, len(text), 1900)][:100] or \
           [{"type": "text", "text": {"content": ""}}]


def blocks(overview, transcript, locked):
    out = [{"type": "heading_2", "heading_2": {"rich_text": rt("Résumé Omi")}}]
    for line in (overview or "Aucun résumé fourni par Omi.").splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        if re.match(r"^#{1,3} ", s):
            out.append({"type": "heading_3", "heading_3": {"rich_text": rt(re.sub(r"^#{1,3} ", "", s))}})
        elif re.match(r"^\s*- ", s):
            out.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": rt(re.sub(r"^\s*- ", "", s))}})
        else:
            out.append({"type": "paragraph", "paragraph": {"rich_text": rt(s)}})
    out.append({"type": "heading_2", "heading_2": {"rich_text": rt("Transcription")}})
    if locked:
        out.append({"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content":
                    "Transcription non accessible : Omi demande un abonnement payant pour cette conversation."},
                    "annotations": {"italic": True}}]}})
    else:
        out += [{"type": "paragraph", "paragraph": {"rich_text": rt(l)}} for l in transcript.splitlines() if l.strip()]
    return out


GAP_MIN = 20   # ecart max (minutes) entre la fin d'un morceau et le debut du suivant pour fusionner


def segment_blocks(title, start_iso, overview, transcript, locked):
    """Blocs d'un morceau ajoute a une page fusionnee : intertitre horodate, resume, transcription."""
    hhmm = datetime.fromisoformat(start_iso).astimezone(PARIS).strftime("%H:%M")
    out = [{"type": "divider", "divider": {}},
           {"type": "heading_2", "heading_2": {"rich_text": rt(f"Suite - {hhmm} - {title or 'Conversation'}")}}]
    for b in blocks(overview, transcript, locked):
        if b["type"] == "heading_2":
            b = {"type": "heading_3", "heading_3": b["heading_2"]}
        out.append(b)
    return out


def append_to_page(page_url, segs, new_title=None):
    """Ajoute des morceaux (deja tries) a une page existante et met a jour titre, duree et Omi ID."""
    pid = re.search(r"([0-9a-f]{32})", page_url).group(1)
    pg = notion("GET", f"/pages/{pid}")
    props = pg["properties"]
    ids = "".join(t["plain_text"] for t in props["Omi ID"]["rich_text"])
    dur = props["Durée (min)"]["number"] or 0
    for sg in segs:
        b = segment_blocks(sg["title"], sg["start"], sg["overview"], sg["transcript"], sg["locked"])
        for i in range(0, len(b), 100):
            notion("PATCH", f"/blocks/{pid}/children", {"children": b[i:i + 100]})
        ids += ", " + sg["id"]
        dur += sg["minutes"]
    upd = {"Omi ID": {"rich_text": rt(ids)}, "Durée (min)": {"number": round(dur, 1)}}
    if new_title:
        upd["Nom de la réunion"] = {"title": rt(new_title)}
    notion("PATCH", f"/pages/{pid}", {"properties": upd})


PENDING = CFG / "omi-pending"
CLASSIF = CFG / "omi-classif.json"
NON_PRO = {"Perso", "À classer"}     # toute autre mission (nom de la mission, Autre) -> base pro ; sinon -> base perso


def fetch(st):
    """Etape 1 : lit les nouvelles conversations terminees et les met en attente (rien dans Notion)."""
    PENDING.mkdir(exist_ok=True)
    known = set(st["done"]) | set(st.get("perso", {})) | {p.stem for p in PENDING.glob("*.json")}
    since = (datetime.fromisoformat(st["last_sync"]) - timedelta(days=1)).date().isoformat()
    today = datetime.now(PARIS).date().isoformat()
    omi_init()
    convs, cur = [], None
    for _ in range(50):
        a = {"limit": 100, "start_date": since, "end_date": today}
        if cur:
            a["cursor"] = cur
        r = omi("get_conversations", a)
        convs += r.get("conversations", [])
        cur = r.get("next_cursor")
        if not cur:
            break
    new = [c for c in convs if c["id"] not in known and c.get("status") == "completed" and not c.get("discarded")]
    for c in new:
        locked, transcript, parts, cur = False, [], None, None
        try:
            for _ in range(50):
                a = {"conversation_id": c["id"], "format": "lines", "max_chars": 100000}
                if cur:
                    a["cursor"] = cur
                r = omi("get_conversation_by_id", a)
                conv = r.get("conversation", {})
                parts = parts or conv
                transcript.append(conv.get("transcript", ""))
                cur = r.get("next_cursor")
                if not r.get("truncated") or not cur:
                    break
        except RuntimeError as e:
            if "paid_plan" not in str(e):
                raise
            locked = True
        (PENDING / f"{c['id']}.json").write_text(json.dumps(
            {"list": c, "locked": locked, "duration": (parts or {}).get("duration_seconds"),
             "transcript": "\n".join(transcript).strip()}, ensure_ascii=False))
    st["last_sync"] = today
    STATE.write_text(json.dumps(st))
    waiting = []
    for p in sorted(PENDING.glob("*.json")):
        d = json.loads(p.read_text()); c = d["list"]; stc = c.get("structured") or {}
        start = datetime.fromisoformat(c.get("started_at") or c["created_at"]).astimezone(PARIS)
        end = datetime.fromisoformat(c["finished_at"]).astimezone(PARIS) if c.get("finished_at") else start
        waiting.append({"id": c["id"], "debut": start.isoformat(timespec="minutes"), "fin": end.isoformat(timespec="minutes"),
                        "titre": stc.get("title"), "theme": stc.get("category"),
                        "resume": re.sub(r"\s+", " ", stc.get("overview") or "")[:500]})
    print(json.dumps({"nouvelles": len(new), "derniere_importee": st.get("last"), "a_classer": waiting},
                     ensure_ascii=False, indent=1))


def do_import(st):
    """Etape 2 : importe les conversations en attente classees (omi-classif.json), dans l'ordre.

    Fusion : une conversation est AJOUTEE a la page de la precedente seulement si elles se suivent
    (aucune autre conversation entre elles), avec la meme mission, le meme `groupe` et au plus
    GAP_MIN minutes d'ecart. Une conversation non classee bloque la suite (on ne saute jamais).
    """
    classif = json.loads(CLASSIF.read_text()) if CLASSIF.exists() else {}
    pend = []
    for p in PENDING.glob("*.json"):
        d = json.loads(p.read_text()); d["_file"] = p; pend.append(d)
    pend.sort(key=lambda d: d["list"].get("started_at") or d["list"]["created_at"])
    ok = merged = err = 0
    for d in pend:
        c = d["list"]
        k = classif.get(c["id"])
        if not k:
            break                                   # garder l'ordre : on n'importe rien apres un trou
        if isinstance(k, str):
            k = {"mission": k}
        mission = (k.get("mission") or "").strip() or "À classer"
        if mission in ("A classer", "a classer"):
            mission = "À classer"
        groupe = (k.get("groupe") or "").strip()
        try:
            stc = c.get("structured") or {}
            start = c.get("started_at") or c["created_at"]
            end = c.get("finished_at") or start
            dur = d.get("duration") or c.get("duration_seconds")
            if not dur and c.get("finished_at"):
                dur = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
            pro = mission not in NON_PRO
            last = st.get("last") or {}
            gap = (datetime.fromisoformat(start) - datetime.fromisoformat(last["fin"])).total_seconds() / 60 if last else 1e9
            if last and groupe and last.get("groupe") == groupe and last.get("mission") == mission and -5 <= gap <= GAP_MIN:
                append_to_page(last["url"], [{"id": c["id"], "title": stc.get("title"), "start": start,
                                              "overview": stc.get("overview"), "transcript": d["transcript"],
                                              "locked": d["locked"], "minutes": (dur or 0) / 60}], new_title=groupe)
                url = last["url"]; merged += 1
                print(f"~ fusion dans « {groupe} » | {start[:16]} {stc.get('title')}")
            else:
                lang = c.get("language") if c.get("language") in ("fr", "en") else "autre"
                props = {"Nom de la réunion": {"title": rt((stc.get("title") or groupe or "Conversation sans titre").strip())},
                         "Date": {"date": {"start": datetime.fromisoformat(start).astimezone(PARIS).isoformat(timespec="minutes")}},
                         "Durée (min)": {"number": round((dur or 0) / 60, 1)},
                         "Langue": {"select": {"name": lang}},
                         "Import Omi": {"select": {"name": "Verrouillé (plan payant)" if d["locked"] else "Complet"}},
                         "Mission": {"select": {"name": mission}},
                         "Omi ID": {"rich_text": rt(c["id"])}}
                if pro:
                    props["Catégorie"] = {"multi_select": [{"name": "Omi"}]}
                if stc.get("category") in CATS:
                    props["Thème Omi"] = {"select": {"name": stc["category"]}}
                b = blocks(stc.get("overview"), d["transcript"], d["locked"])
                body = {"parent": {"database_id": st["db"] if pro else st["perso_db"]}, "properties": props, "children": b[:100]}
                if stc.get("emoji"):
                    body["icon"] = {"type": "emoji", "emoji": stc["emoji"]}
                try:
                    pg = notion("POST", "/pages", body)
                except RuntimeError as e:
                    if "icon" not in str(e) and "emoji" not in str(e):
                        raise
                    body.pop("icon"); pg = notion("POST", "/pages", body)
                for i in range(100, len(b), 100):
                    notion("PATCH", f"/blocks/{pg['id']}/children", {"children": b[i:i + 100]})
                url = pg["url"]; ok += 1
                print(f"+ {mission} | {start[:16]} {stc.get('title')}")
            st["done" if pro else "perso"][c["id"]] = url
            st["last"] = {"id": c["id"], "fin": end, "mission": mission, "groupe": groupe, "url": url,
                          "titre": stc.get("title")}
            STATE.write_text(json.dumps(st))
            d["_file"].unlink()
        except Exception as e:
            err += 1
            print("ECHEC", c["id"], str(e)[:200])
            break
    left = len(list(PENDING.glob("*.json")))
    print(f"Importees : {ok} nouvelles pages, {merged} fusionnees ; echecs : {err} ; en attente : {left} ; "
          f"pro : {len(set(st['done'].values()))} pages ; perso : {len(set(st.get('perso', {}).values()))} pages")


LOCKED = "Verrouillé (plan payant)"
PLACEHOLDER = "Transcription non accessible"


def _children(pid):
    res, cur = [], None
    while True:
        r = notion("GET", f"/blocks/{pid}/children?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
        res += r["results"]
        if not r.get("has_more"):
            return res
        cur = r["next_cursor"]


def _btext(b):
    v = b.get(b["type"], {})
    return "".join(r.get("plain_text", "") for r in v.get("rich_text", [])) if isinstance(v, dict) else ""


def _transcript(cid):
    parts, cur = [], None
    for _ in range(50):
        a = {"conversation_id": cid, "format": "lines", "max_chars": 100000}
        if cur:
            a["cursor"] = cur
        r = omi("get_conversation_by_id", a)
        parts.append(r.get("conversation", {}).get("transcript", ""))
        cur = r.get("next_cursor")
        if not r.get("truncated") or not cur:
            break
    return "\n".join(parts).strip()


def unlock(st, apply=False, limit=None):
    """Complete les pages importees « Verrouille (plan payant) » une fois l'abonnement Omi actif.

    Dans chaque page (pro et perso), remplace le paragraphe « Transcription non accessible » par la
    transcription, au meme endroit (n-ieme intertitre « Transcription » = n-ieme Omi ID de la page,
    pages fusionnees comprises), puis passe « Import Omi » a « Complet ». Le resume n'est pas touche.
    Sans --apply : dry-run (liste ce qui serait ecrit). Une conversation encore verrouillee reste en l'etat.
    """
    pages = []
    for db in (st["db"], st.get("perso_db")):
        if not db:
            continue
        cur = None
        while True:
            body = {"page_size": 100, "filter": {"property": "Import Omi", "select": {"equals": LOCKED}}}
            if cur:
                body["start_cursor"] = cur
            r = notion("POST", f"/databases/{db}/query", body)
            for p in r["results"]:
                pr = p["properties"]
                ids = [i.strip() for i in "".join(t["plain_text"] for t in pr["Omi ID"]["rich_text"]).split(",") if i.strip()]
                pages.append({"id": p["id"], "url": p["url"], "ids": ids,
                              "title": "".join(t["plain_text"] for t in pr["Nom de la réunion"]["title"])})
            if not r.get("has_more"):
                break
            cur = r["next_cursor"]
    print(f"Pages verrouillees : {len(pages)} ; conversations : {sum(len(p['ids']) for p in pages)}")
    if limit:
        pages = pages[:limit]
    if pages:
        omi_init()
    done = still = bad = 0
    for p in pages:
        seg, todo = -1, []
        for b in _children(p["id"]):
            if b["type"] in ("heading_2", "heading_3") and _btext(b) == "Transcription":
                seg += 1
            elif b["type"] == "paragraph" and _btext(b).startswith(PLACEHOLDER):
                todo.append((b["id"], seg))
        if todo and max(s for _, s in todo) >= len(p["ids"]):
            print("INCOHERENT (plus de segments que d'Omi ID)", p["url"]); bad += 1
            continue
        locked_left = 0
        for bid, s in todo:
            try:
                lines = [l for l in _transcript(p["ids"][s]).splitlines() if l.strip()]
            except RuntimeError as e:
                if "paid_plan" not in str(e):
                    raise
                locked_left += 1
                continue
            if apply:
                new = [{"type": "paragraph", "paragraph": {"rich_text": rt(l)}} for l in lines] or \
                      [{"type": "paragraph", "paragraph": {"rich_text": rt("(transcription vide)")}}]
                after = bid
                for i in range(0, len(new), 100):
                    r = notion("PATCH", f"/blocks/{p['id']}/children", {"children": new[i:i + 100], "after": after})
                    after = r["results"][-1]["id"] if r.get("results") else after
                notion("DELETE", f"/blocks/{bid}")
        if locked_left:
            still += 1
            print("encore verrouillee :", p["url"])
            continue
        if apply:
            notion("PATCH", f"/pages/{p['id']}", {"properties": {"Import Omi": {"select": {"name": "Complet"}}}})
        done += 1
        print(("complete : " if apply else "a completer : ") + f"{p['title']} | {p['url']}")
    print(f"Deverrouillage : {done} pages {'completees' if apply else 'a completer (dry-run)'} ; "
          f"encore verrouillees : {still} ; incoherentes : {bad}")


def main():
    st = json.loads(STATE.read_text())
    st.setdefault("perso", {})
    if "--fetch" in sys.argv:
        fetch(st)
    elif "--import" in sys.argv:
        do_import(st)
    elif "--unlock" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
        unlock(st, apply="--apply" in sys.argv, limit=lim)
    else:
        sys.exit("Usage : omi_sync.py --fetch  puis  omi_sync.py --import (apres classification dans omi-classif.json)\n"
                 "        omi_sync.py --unlock [--apply] [--limit N]  (complete les pages verrouillees, abonnement actif)")


if __name__ == "__main__":
    main()
