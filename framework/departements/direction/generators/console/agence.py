"""agence - l'écran « agence » de la console : qui (agent) utilise quoi (skill, générateur, connecteur), en direct.

Le plan vient du référentiel `framework/organisation.yml` (départements, rôles, rattachement de chaque
composant), aligné sur le fonctionnement de Claude Code : le chef de projet (Claude principal) et les rôles
métier des départements sont incarnés par Claude principal ; les sous-agents sont les seuls vrais collègues ;
les skills sont des classeurs, les générateurs des machines ; les connecteurs sont des services partagés ;
les hooks des garde-fous.

Les événements viennent de `.claude/activity.log`, écrit par le hook journal_activite (demande, début et fin
de chaque action). Lecture seule.
"""
from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import organisation as ORG  # noqa: E402

KIND = {"generators": "generator", "skills": "skill", "routines": "routine"}
TOOLS = ["Read", "Edit", "Write", "Bash", "Grep", "Glob", "WebSearch", "WebFetch", "ToolSearch", "AskUserQuestion"]


def catalogue():
    """Bureaux de l'agence depuis organisation.yml : agents (rôle métier + sous-agents) et postes par type."""
    org = ORG.load()
    out = []
    for d in org["departements"]:
        agents = [{"id": f"role:{d['id']}", "label": d["role"] + (" (Claude)" if d["id"] == "direction" else ""), "role": True}]
        agents += [{"id": a, "label": a} for a in d.get("agents") or []]
        postes = [{"kind": KIND[t], "name": n} for t in ("skills", "generators", "routines") for n in d.get(t) or []]
        if d["id"] == "direction":
            postes += [{"kind": "tool", "name": t} for t in TOOLS]
        out.append({"id": d["id"], "label": d["label"], "sub": d["mission"], "agents": agents, "postes": postes})
    ch = org["charte"]
    out.append({"id": "charte", "label": ch["label"], "sub": ch["mission"] + " (transverse)", "agents": [],
                "postes": [{"kind": KIND[t], "name": n} for t in ("skills", "generators") for n in ch.get(t) or []]})
    rf = org["renforts"]
    out.append({"id": "renforts", "label": rf["label"], "sub": rf["mission"],
                "agents": [{"id": a, "label": a} for a in rf["agents"]], "postes": []})
    out.append({"id": "services", "label": "Services partagés", "sub": "connecteurs externes, appelés par celui qui travaille",
                "agents": [], "postes": [{"kind": "connector", "name": s["label"]} for s in org["services"]]})
    out.append({"id": "garde_fous", "label": "Garde-fous", "sub": "hooks : contrôlent chaque action, peuvent la bloquer",
                "agents": [], "postes": [{"kind": "hook", "name": h["name"]} for h in org["garde_fous"]]})
    return out


def _index():
    org = ORG.load()
    asg = ORG.assignments(org)
    return org, asg


def connector_of(name, org=None):
    org = org or ORG.load()
    for s in org["services"]:
        if any(fnmatch.fnmatch(name, p) for p in s["motifs"]):
            return s["label"]
    return None


def bureau_of(ev, org=None, asg=None):
    """Département d'un événement : celui de l'agent appelé, du skill, de la machine ; services ; direction."""
    if org is None:
        org, asg = _index()
    k, n = ev.get("kind"), ev.get("name", "")
    if k == "agent":
        return asg.get(("agents", n), "renforts")
    if k == "hook":
        return "garde_fous"
    if k == "connector":
        lab = connector_of(n, org)
        if lab:
            ev["conn"] = lab
        return "services"
    if k in ("skill", "generator"):
        name = n.split(":")[-1]  # plugin-prefixed skills: pm-framework:slide-style
        return asg.get(("skills" if k == "skill" else "generators", name), "direction")
    return "direction"


def read_events(log: Path, limit=400):
    if not log.exists():
        return []
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-limit * 3:]
    seen, out = set(), []
    org, asg = _index()
    for ln in lines:
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        key = (ev.get("ev"), ev.get("id") or ev.get("ts")[:19], ev.get("name"), ev.get("detail"))
        if key in seen:  # plugin + project hooks both log: keep one
            continue
        seen.add(key)
        ev["bureau"] = bureau_of(ev, org, asg)
        if ev.get("kind") == "skill":
            ev["name"] = ev["name"].split(":")[-1]
        out.append(ev)
    return out[-limit:]


HOLD_S = 4  # an action stays lit at least this long, even when it ended sooner (most last < 1 s)


def state(project_root):
    """Ce que l'écran affiche : demande en cours, actions actives, fil des derniers événements."""
    import datetime as dt
    evs = read_events(Path(project_root) / ".claude" / "activity.log")
    prompt = next((e for e in reversed(evs) if e.get("ev") == "prompt"), None)
    ended = {e.get("id") for e in evs if e.get("ev") == "end" and e.get("id")}
    now = dt.datetime.now()
    horizon = (now - dt.timedelta(seconds=HOLD_S)).isoformat(timespec="milliseconds")
    stale = (now - dt.timedelta(minutes=2)).isoformat(timespec="milliseconds")         # failed calls log no end
    stale_agent = (now - dt.timedelta(minutes=30)).isoformat(timespec="milliseconds")  # agents work longer

    def unfinished(e):
        return e["id"] not in ended and e["ts"] >= (stale_agent if e.get("kind") == "agent" else stale)
    active = [e for e in evs if e.get("ev") == "start" and e.get("id")
              and (unfinished(e) or e["ts"] >= horizon)][-8:]
    for e in active:
        e["running"] = unfinished(e)
    since = [e for e in evs if prompt and e["ts"] >= prompt["ts"] and e.get("ev") == "start"]
    counts = {}
    for e in since:
        counts[e["bureau"]] = counts.get(e["bureau"], 0) + 1
    return {"prompt": prompt, "active": active, "feed": [e for e in evs if e.get("ev") in ("start", "prompt")][-60:],
            "counts": counts}


PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Agence · agents et skills en direct</title>
<style>
:root{--noir:#0B0B0B;--ivoire:#F7F4EF;--encre:#1A1A1A;--gris:#8A8580;--filet:#D9D3CA;--voile:#ECE6DD;--sable:#E9DFD1;
--taupe:#B7A99A;--sauge:#A9B5A0;--bordeaux:#7A1F23;--or:#B8975A;--rouge:#D62828;--sans:"Helvetica Neue","Avenir Next","Segoe UI",Arial,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--ivoire);color:var(--encre);font:300 14px/1.5 var(--sans)}
.wrap{display:grid;grid-template-columns:1fr 340px;gap:24px;padding:28px 32px;max-width:1500px;margin:0 auto}
header{grid-column:1/-1;display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--encre);padding-bottom:14px}
h1{font:200 30px var(--sans)}.eyebrow{color:var(--gris);font-size:13px}
.demande{font-size:16px;margin-top:6px}.demande b{font-weight:400}
.live{font-size:12px;color:var(--gris)}.live i{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--sauge);margin-right:6px}
.plan{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.room{background:#fff;border:1px solid var(--filet);padding:14px 16px;min-height:150px;position:relative;transition:border-color .3s, box-shadow .3s}
.room.wide{grid-column:1/-1}
.room.on{border-color:var(--rouge);box-shadow:0 0 0 3px var(--rouge),0 0 22px rgba(214,40,40,.35)}
.room.on h2{color:var(--rouge)}
.room h2{font:400 15px var(--sans);display:flex;justify-content:space-between}.room h2 .n{color:var(--or);font-weight:300}
.room .sub{color:var(--gris);font-size:12px;margin-bottom:10px}
.lbl{font-size:11px;color:var(--gris);margin:8px 0 4px}
.team{display:flex;gap:10px;flex-wrap:wrap}
.agent{display:flex;flex-direction:column;align-items:center;width:64px;position:relative}
.agent .av{width:34px;height:34px;border-radius:50%;background:var(--voile);display:flex;align-items:center;justify-content:center;font:400 12px var(--sans);transition:all .25s}
.agent .nm{font-size:10px;color:var(--gris);text-align:center;line-height:1.2;margin-top:3px;word-break:break-word}
.agent.on .av{background:var(--rouge);color:#fff;transform:scale(1.25);box-shadow:0 0 0 4px rgba(214,40,40,.25);animation:pulse 1s ease-in-out infinite}
.agent.on .nm{color:var(--rouge);font-weight:400}
.agent.role .av{background:#fff;border:1px dashed var(--taupe)}
.p.k-hook{background:#fff;border-color:var(--bordeaux);color:var(--bordeaux)}
@keyframes pulse{0%,100%{box-shadow:0 0 0 3px rgba(214,40,40,.35)}50%{box-shadow:0 0 0 10px rgba(214,40,40,0)}}
.bubble{position:absolute;bottom:58px;left:0;background:var(--rouge);color:#fff;font:400 12px var(--sans);padding:5px 9px;max-width:260px;white-space:normal;width:max-content;z-index:3}
.bubble:after{content:"";position:absolute;top:100%;left:14px;border:6px solid transparent;border-top-color:var(--rouge)}
.postes{display:flex;flex-wrap:wrap;gap:4px}
.p{font-size:11px;padding:2px 7px;background:var(--ivoire);border:1px solid var(--filet);color:#4a4643;transition:all .25s}
.p.k-skill{border-style:solid}.p.k-generator{border-style:dashed}.p.k-routine{border-style:dotted}.p.k-connector{background:#fff;border-color:var(--taupe)}.p.k-tool{background:#fff;color:var(--gris)}
.p.on{background:var(--rouge);border:1px solid var(--rouge);color:#fff;font-weight:400;transform:scale(1.15);box-shadow:0 0 0 3px rgba(214,40,40,.3);animation:pulse 1s ease-in-out infinite;position:relative;z-index:2}
.p.recent{background:var(--sable)}
aside h3{font:400 13px var(--sans);border-bottom:1px solid var(--encre);padding-bottom:8px;margin-bottom:8px}
.feed{list-style:none;max-height:78vh;overflow:auto}
.feed li{display:grid;grid-template-columns:54px 1fr;gap:8px;padding:6px 0;border-bottom:1px solid var(--filet);font-size:12px}
.feed .t{color:var(--gris);font-variant-numeric:tabular-nums}.feed .w b{font-weight:400}.feed .d{color:var(--gris);display:block}
.feed li.prompt{background:var(--voile)}
.feed li.live{background:#FCE8E8;border-left:3px solid var(--rouge);padding-left:6px}.feed li.live b{color:var(--rouge)}
.now{grid-column:1/-1;background:var(--rouge);color:#fff;font:300 18px var(--sans);padding:12px 18px;display:none;gap:14px;align-items:baseline;flex-wrap:wrap}
.now.show{display:flex}.now b{font-weight:500}.now .k{font-size:12px;opacity:.85;text-transform:none}.now .sep{opacity:.6}
.legend{grid-column:1/-1;display:flex;gap:18px;font-size:12px;color:var(--gris)}
.legend .p{pointer-events:none}
.grp:has(.postes:empty){display:none}
.none{font-size:11px;color:var(--gris)}
#demo{margin-left:12px;font:300 12px var(--sans);background:none;border:1px solid var(--encre);padding:2px 10px;cursor:pointer}
#demo:hover{background:var(--encre);color:#fff}
</style></head><body><div class="wrap">
<header><div><div class="eyebrow">Agence · agents et skills en direct <button id="demo">Rejouer une démo</button></div><h1>Qui fait quoi, maintenant</h1>
<div class="demande" id="demande">En attente d'une demande…</div></div><div class="live"><i></i>lu en direct depuis .claude/activity.log</div></header>
<div class="now" id="now"></div>
<main><div class="plan" id="plan"></div></main>
<aside><h3>Fil des actions</h3><ul class="feed" id="feed"></ul></aside>
<div class="legend"><span><span class="p k-skill">skill</span></span><span><span class="p k-generator">générateur</span></span>
<span><span class="p k-routine">routine</span></span><span><span class="p k-connector">connecteur</span></span><span><span class="p k-tool">outil</span></span>
<span><span class="p on">en cours</span></span><span><span class="p recent">utilisé pour cette demande</span></span></div>
</div>
<script>
const CAT = __CATALOGUE__;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ini = n => n.replace(/\(.*\)/,"").split(/[-_ ]/).filter(w => w && w.length > 1 && !["du","de","la","le"].includes(w)).map(w => w[0]).join("").slice(0,3).toUpperCase();
const DEPTS = new Set(CAT.filter(b => b.agents.some(a => a.role)).map(b => b.id));
const LABEL = Object.fromEntries(CAT.flatMap(b => b.agents.map(a => [a.id, a.label])));
const actor = e => e.kind==="agent" ? e.name : ((e.agent && e.agent!=="claude") ? e.agent : "role:"+(DEPTS.has(e.bureau) ? e.bureau : "direction"));
const labelOf = id => LABEL[id] || id;
function short(kind, name){ if(kind==="connector"){ const p=name.split("__"); return p[p.length-1]; } return name; }
function build(){
  document.getElementById("plan").innerHTML = CAT.map(b => `
   <section class="room ${["direction","services","garde_fous"].includes(b.id)?"wide":""}" id="r-${b.id}">
    <h2>${esc(b.label)} <span class="n" id="n-${b.id}"></span></h2><div class="sub">${esc(b.sub)}</div>
    ${b.agents.length ? `<div class="lbl">Agents</div><div class="team" id="t-${b.id}">${b.agents.map(a=>`
      <div class="agent ${a.role?"role":""}" data-a="${esc(a.id)}"><div class="av" title="${esc(a.role?"rôle tenu par Claude principal":"sous-agent")}">${esc(ini(a.label))}</div><div class="nm">${esc(a.label)}</div></div>`).join("")}</div>` : `<div class="team" id="t-${b.id}"></div>`}
    ${GROUPS.map(([k, lab]) => `<div class="grp"><div class="lbl">${lab}</div><div class="postes" id="p-${b.id}-${k}">${b.postes.filter(p=>p.kind===k).map(p=>`
      <span class="p k-${p.kind}" data-k="${p.kind}:${esc(p.name)}" title="${p.kind}">${esc(p.name)}</span>`).join("")}</div></div>`).join("")}
   </section>`).join("");
}
const GROUPS = [["skill","Skills"],["generator","Générateurs"],["routine","Routines"],["connector","Connecteurs"],["hook","Garde-fous"],["tool","Outils"]];
function poste(bureau, kind, name){
  const box = document.getElementById("p-"+bureau+"-"+kind); if(!box) return null;
  let el = box.querySelector(`[data-k="${CSS.escape(kind+":"+name)}"]`);
  if(!el){ el = document.createElement("span"); el.className = "p k-"+kind; el.dataset.k = kind+":"+name;
           el.textContent = short(kind, name); el.title = name; box.appendChild(el); }
  return el;
}
function agentEl(bureau, a){
  let el = document.querySelector(`.agent[data-a="${CSS.escape(a)}"]`);
  if(!el){ const t = document.getElementById("t-"+bureau); if(!t) return null;
    el = document.createElement("div"); el.className="agent"; el.dataset.a=a;
    el.innerHTML=`<div class="av" title="${esc(a)}">${esc(ini(labelOf(a)))}</div><div class="nm">${esc(labelOf(a))}</div>`; t.appendChild(el); }
  return el;
}
function render(s){
  document.getElementById("demande").innerHTML = s.prompt ? `Demande : <b>${esc(s.prompt.detail)}</b>` : "En attente d'une demande…";
  document.querySelectorAll(".on").forEach(e=>e.classList.remove("on"));
  document.querySelectorAll(".bubble").forEach(e=>e.remove());
  document.querySelectorAll(".p.recent").forEach(e=>e.classList.remove("recent"));
  CAT.forEach(b => { const c = s.counts[b.id]; document.getElementById("n-"+b.id).textContent = c ? c+" action"+(c>1?"s":"") : ""; });
  const pTs = s.prompt ? s.prompt.ts : "";
  s.feed.filter(e => e.ev==="start" && e.ts >= pTs && e.kind!=="agent").forEach(e => { const el = poste(e.bureau, e.kind, e.conn || e.name); if(el) el.classList.add("recent"); });
  s.active.forEach(e => {
    document.getElementById("r-"+e.bureau)?.classList.add("on");
    const who = actor(e);
    const whoB = CAT.find(b=>b.agents.some(a=>a.id===who))?.id || e.bureau;
    const a = agentEl(whoB, who);
    if(a){ a.classList.add("on"); const bb=document.createElement("div"); bb.className="bubble";
      bb.textContent = e.kind==="agent" ? (e.detail || "au travail") : `${short(e.kind,e.name)}${e.detail? " · "+e.detail:""}`.slice(0,60); a.appendChild(bb); }
    if(e.kind!=="agent"){ const p = poste(e.bureau, e.kind, e.conn || e.name); p && p.classList.add("on"); }
    if(whoB !== e.bureau) document.getElementById("r-"+whoB)?.classList.add("on");
  });
  const now = document.getElementById("now");
  if(s.active.length){ now.classList.add("show");
    now.innerHTML = s.active.slice(-3).reverse().map(e => {
      const who = labelOf(actor(e));
      const what = e.kind==="agent" ? "agent appelé" : (e.conn ? e.conn+" · "+short(e.kind,e.name) : short(e.kind,e.name));
      return `<span>En cours : <b>${esc(who)}</b> <span class="sep">→</span> <b>${esc(what)}</b> <span class="k">${esc(e.kind)} · ${esc(CAT.find(b=>b.id===e.bureau)?.label||"")}${e.running===false?" · terminé":""}</span></span>`;
    }).join('<span class="sep">|</span>');
  } else { now.classList.remove("show"); now.innerHTML = ""; }
  const liveIds = new Set(s.active.map(e=>e.id));
  document.getElementById("feed").innerHTML = s.feed.slice().reverse().map(e => e.ev==="prompt"
    ? `<li class="prompt"><span class="t">${e.ts.slice(11,19)}</span><span class="w"><b>Demande</b><span class="d">${esc(e.detail)}</span></span></li>`
    : `<li class="${liveIds.has(e.id)?"live":""}"><span class="t">${e.ts.slice(11,19)}</span><span class="w"><b>${esc(labelOf(actor(e)))}</b> → ${esc(short(e.kind,e.name))}
       <span class="d">${esc(CAT.find(b=>b.id===e.bureau)?.label||"")}${e.detail?" · "+esc(e.detail):""}</span></span></li>`).join("");
}
let demoUntil = 0;
async function tick(){ if(Date.now() > demoUntil){ try{ const r = await fetch("/agence/state.json",{cache:"no-store"}); render(await r.json()); }catch(e){} } setTimeout(tick, 500); }
const SCEN = [
  {kind:"prompt", detail:"Fais-moi le dossier projet du comité de jeudi"},
  {kind:"skill", name:"slide-style", bureau:"charte", agent:"claude", detail:"la chef de projet prend le classeur de la charte"},
  {kind:"agent", name:"jira-sprints-audit", bureau:"planification", detail:"brief : auditer le plan de sprints"},
  {kind:"connector", name:"mcp__atlassian__searchJiraIssuesUsingJql", conn:"Atlassian (Jira, Confluence)", bureau:"services", agent:"jira-sprints-audit", detail:"tickets du sprint 3"},
  {kind:"agent", name:"notion-topics-audit", bureau:"suivi", detail:"brief : relire les sujets"},
  {kind:"connector", name:"mcp__notion__notion-query-data-sources", conn:"Notion", bureau:"services", agent:"notion-topics-audit", detail:"base Suivi des sujets"},
  {kind:"generator", name:"risks", bureau:"suivi", agent:"claude", detail:"registre des risques"},
  {kind:"hook", name:"garde_office", bureau:"garde_fous", agent:"claude", detail:"écriture Office contrôlée"},
  {kind:"agent", name:"archi-audit", bureau:"studio", detail:"brief : vue macro de l'architecture"},
  {kind:"generator", name:"archi", bureau:"studio", agent:"archi-audit", detail:"rendu de référence"},
  {kind:"skill", name:"voice-slides", bureau:"charte", agent:"claude", detail:"légendes des slides"},
  {kind:"generator", name:"dossier", bureau:"studio", agent:"claude", detail:"--build : PPTX + HTML"},
];
document.getElementById("demo").onclick = () => {
  const t0 = new Date(); const feed = []; let i = 0;
  const ts = k => new Date(t0.getTime() + k*1000).toISOString().replace("Z","");
  demoUntil = Date.now() + SCEN.length*1600 + 4000;
  const step = () => {
    if(i >= SCEN.length) return;
    const e = Object.assign({ev: SCEN[i].kind==="prompt"?"prompt":"start", ts: ts(i), id:"demo"+i}, SCEN[i]);
    feed.push(e);
    const prompt = feed[0];
    const active = e.ev==="start" ? [e].concat(feed.filter(x=>x.kind==="agent" && x!==e).slice(-1)) : [];
    const counts = {}; feed.filter(x=>x.ev==="start").forEach(x=>counts[x.bureau]=(counts[x.bureau]||0)+1);
    render({prompt, active, feed: feed.slice(), counts});
    i++; setTimeout(step, 1600);
  };
  step();
};
build(); tick();
</script></body></html>"""


def page():
    return PAGE.replace("__CATALOGUE__", json.dumps(catalogue(), ensure_ascii=False))
