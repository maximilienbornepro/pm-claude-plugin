"""agence - l'écran « agence » de la console : qui (agent) utilise quoi (skill, générateur, connecteur), en direct.

Le plan de l'agence est CALCULÉ depuis le plugin : agents (framework/agents + agents génériques de Claude
Code), skills (framework/skills), générateurs (pm.py) et routines (framework/routines). Chaque composant est
rangé dans un bureau par la table BUREAUX ci-dessous ; ce qui n'est rangé nulle part tombe à l'accueil.

Les événements viennent de `.claude/activity.log`, écrit par le hook journal_activite (demande, début et fin
de chaque action). Lecture seule.
"""
from __future__ import annotations

import fnmatch
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# bureau -> agents (personnages) et motifs des postes (skills, générateurs, routines, connecteurs, outils)
BUREAUX = [
    {"id": "accueil", "label": "Accueil", "sub": "Claude principal : reçoit la demande, lit, écrit, lance",
     "agents": ["claude"],
     "postes": ["tool:Read", "tool:Edit", "tool:Write", "tool:MultiEdit", "tool:Bash", "tool:Grep", "tool:Glob",
                "tool:WebSearch", "tool:WebFetch", "tool:ToolSearch", "tool:TodoWrite", "tool:AskUserQuestion",
                "skill:list", "skill:run", "skill:demo", "skill:setup", "connector:*update_plan*", "connector:*wrap_up*"]},
    {"id": "pilotage", "label": "Pilotage", "sub": "planning, projection, gates",
     "agents": [],
     "postes": ["generator:planning", "generator:projection", "generator:gate", "generator:cockpit", "generator:method",
                "generator:preflight", "generator:init", "generator:setup", "generator:templates", "generator:agent", "generator:trace-audit",
                "skill:technical-planning", "routine:publish-projection", "routine:track-progress",
                "routine:align-sprint-goals", "routine:audit-scope", "connector:*scheduled-tasks*"]},
    {"id": "jira", "label": "Bureau Jira", "sub": "sprints, tickets, audits",
     "agents": ["jira-sprints-audit", "jira-changes-audit", "jira-tickets-audit", "front-audit"],
     "postes": ["generator:jira-*", "generator:plan", "connector:*Jira*", "connector:*Confluence*", "connector:*Atlassian*",
                "connector:*Compass*", "connector:*atlassian*"]},
    {"id": "notion", "label": "Notion et suivi", "sub": "sujets, weekly, Omi, Slack",
     "agents": ["notion-topics-audit"],
     "postes": ["generator:notion-*", "generator:omi-sync", "generator:transcripts", "generator:weekly-report",
                "generator:activity", "generator:slack", "routine:review-topics", "routine:collect-activity",
                "routine:morning-digest", "routine:omi-sync", "connector:*notion-*", "connector:*omi-memory*",
                "connector:*slack*", "skill:omi"]},
    {"id": "office", "label": "Office", "sub": "risques, RACI, Excel, SharePoint",
     "agents": [],
     "postes": ["generator:risks", "generator:raci", "generator:office", "generator:traceability", "generator:drive-scaffold",
                "generator:docs-coherence-audit", "routine:review-risks", "skill:*xlsx", "skill:*docx", "skill:*pptx",
                "skill:*pdf", "connector:*sharepoint*", "connector:*outlook*", "connector:*teams*", "connector:*get_me*",
                "connector:*read_resource*", "connector:*_file*"]},
    {"id": "studio", "label": "Studio", "sub": "architecture, dossier, slides",
     "agents": ["archi-audit"],
     "postes": ["generator:archi", "generator:dossier", "generator:poc", "generator:deck-gate", "generator:console",
                "skill:slide-style", "skill:*frontend-design", "skill:artifact-*", "skill:figma:*", "tool:Artifact",
                "connector:*visualize*", "connector:*Claude_Browser*", "connector:*figma*"]},
    {"id": "redaction", "label": "Rédaction", "sub": "tons, comptes rendus, relances",
     "agents": ["doc-writer", "adservio-writer"],
     "postes": ["skill:voice-*", "skill:*voice-*", "generator:partner-report", "generator:tones", "routine:draft-followups",
                "skill:*docs"]},
    {"id": "renforts", "label": "Renforts", "sub": "agents génériques appelés en appui",
     "agents": ["Explore", "general-purpose", "Plan", "claude-code-guide", "web-fetch"],
     "postes": ["tool:Agent", "tool:Task"]},
]


def _gen_names():
    spec = importlib.util.spec_from_file_location("pmf_pm", ROOT / "framework" / "pm.py")
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    return list(pm.GEN)


def catalogue():
    """Bureaux avec leurs agents et leurs postes, tels qu'ils existent dans le plugin."""
    agents = [p.stem for p in (ROOT / "framework" / "agents").glob("*.md")]
    items = ([("generator", g) for g in _gen_names()]
             + [("skill", p.parent.name) for p in (ROOT / "framework" / "skills").glob("*/SKILL.md")]
             + [("routine", p.parent.name) for p in (ROOT / "framework" / "routines").glob("*/SKILL.md")])
    out = []
    placed = set()
    for b in BUREAUX:
        postes = []
        for kind, name in items:
            if any(fnmatch.fnmatch(f"{kind}:{name}", pat) for pat in b["postes"]) and (kind, name) not in placed:
                postes.append({"kind": kind, "name": name}); placed.add((kind, name))
        team = [a for a in b["agents"] if a in agents or b["id"] in ("accueil", "renforts")]
        out.append({**{k: b[k] for k in ("id", "label", "sub")}, "agents": team, "postes": postes})
    rest = [{"kind": k, "name": n} for k, n in items if (k, n) not in placed]
    out[0]["postes"].extend(rest)
    return out


AGENT_BUREAU = {a: b["id"] for b in BUREAUX for a in b["agents"]}


def bureau_of(ev):
    """Bureau d'un événement : celui de l'agent appelé, sinon celui du poste utilisé."""
    if ev.get("kind") == "agent":
        return AGENT_BUREAU.get(ev.get("name"), "renforts")
    key = f"{ev.get('kind')}:{ev.get('name')}"
    for b in BUREAUX:
        if any(fnmatch.fnmatch(key, pat) for pat in b["postes"]):
            return b["id"]
    return "accueil"


def read_events(log: Path, limit=400):
    if not log.exists():
        return []
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-limit * 3:]
    seen, out = set(), []
    for ln in lines:
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        key = (ev.get("ev"), ev.get("id") or ev.get("ts")[:19], ev.get("name"), ev.get("detail"))
        if key in seen:  # plugin + project hooks both log: keep one
            continue
        seen.add(key)
        ev["bureau"] = bureau_of(ev)
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
@keyframes pulse{0%,100%{box-shadow:0 0 0 3px rgba(214,40,40,.35)}50%{box-shadow:0 0 0 10px rgba(214,40,40,0)}}
.bubble{position:absolute;bottom:58px;left:0;background:var(--rouge);color:#fff;font:400 12px var(--sans);padding:5px 9px;max-width:260px;white-space:normal;width:max-content;z-index:3}
.bubble:after{content:"";position:absolute;top:100%;left:14px;border:6px solid transparent;border-top-color:var(--rouge)}
.postes{display:flex;flex-wrap:wrap;gap:4px}
.p{font-size:11px;padding:2px 7px;background:var(--ivoire);border:1px solid var(--filet);color:#4a4643;transition:all .25s}
.p.k-skill{border-style:solid}.p.k-generator{border-style:dashed}.p.k-routine{border-style:dotted}.p.k-connector,.p.k-tool{background:#fff}
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
<span><span class="p k-routine">routine</span></span><span><span class="p k-connector">connecteur ou outil</span></span>
<span><span class="p on">en cours</span></span><span><span class="p recent">utilisé pour cette demande</span></span></div>
</div>
<script>
const CAT = __CATALOGUE__;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ini = n => n === "claude" ? "C" : n.split(/[-_ ]/).filter(Boolean).map(w => w[0]).join("").slice(0,3).toUpperCase();
function short(kind, name){ if(kind==="connector"){ const p=name.split("__"); return p[p.length-1]; } return name; }
function build(){
  document.getElementById("plan").innerHTML = CAT.map(b => `
   <section class="room ${b.id==="accueil"?"wide":""}" id="r-${b.id}">
    <h2>${esc(b.label)} <span class="n" id="n-${b.id}"></span></h2><div class="sub">${esc(b.sub)}</div>
    <div class="lbl">Agents</div><div class="team" id="t-${b.id}">${b.agents.length?"":'<span class="none">pas d\'agent dédié : Claude principal y travaille</span>'}${b.agents.map(a=>`
      <div class="agent" data-a="${esc(a)}"><div class="av" title="${esc(a)}">${esc(ini(a))}</div><div class="nm">${esc(a)}</div></div>`).join("")}</div>
    <div class="lbl">Skills</div><div class="postes" id="p-${b.id}">${b.postes.map(p=>`
      <span class="p k-${p.kind}" data-k="${p.kind}:${esc(p.name)}" title="${p.kind}">${esc(p.name)}</span>`).join("")}</div>
   </section>`).join("");
}
function poste(bureau, kind, name){
  const box = document.getElementById("p-"+bureau); if(!box) return null;
  let el = box.querySelector(`[data-k="${CSS.escape(kind+":"+name)}"]`);
  if(!el){ el = document.createElement("span"); el.className = "p k-"+kind; el.dataset.k = kind+":"+name;
           el.textContent = short(kind, name); el.title = name; box.appendChild(el); }
  return el;
}
function agentEl(bureau, a){
  let el = document.querySelector(`.agent[data-a="${CSS.escape(a)}"]`);
  if(!el){ const t = document.getElementById("t-"+bureau); if(!t) return null;
    el = document.createElement("div"); el.className="agent"; el.dataset.a=a;
    el.innerHTML=`<div class="av" title="${esc(a)}">${esc(ini(a))}</div><div class="nm">${esc(a)}</div>`; t.appendChild(el); }
  return el;
}
function render(s){
  document.getElementById("demande").innerHTML = s.prompt ? `Demande : <b>${esc(s.prompt.detail)}</b>` : "En attente d'une demande…";
  document.querySelectorAll(".on").forEach(e=>e.classList.remove("on"));
  document.querySelectorAll(".bubble").forEach(e=>e.remove());
  document.querySelectorAll(".p.recent").forEach(e=>e.classList.remove("recent"));
  CAT.forEach(b => { const c = s.counts[b.id]; document.getElementById("n-"+b.id).textContent = c ? c+" action"+(c>1?"s":"") : ""; });
  const pTs = s.prompt ? s.prompt.ts : "";
  s.feed.filter(e => e.ev==="start" && e.ts >= pTs && e.kind!=="agent").forEach(e => { const el = poste(e.bureau, e.kind, e.name); if(el) el.classList.add("recent"); });
  s.active.forEach(e => {
    document.getElementById("r-"+e.bureau)?.classList.add("on");
    const who = e.kind==="agent" ? e.name : (e.agent || "claude");
    const whoB = e.kind==="agent" ? e.bureau : (CAT.find(b=>b.agents.includes(who))?.id || "accueil");
    const a = agentEl(whoB, who);
    if(a){ a.classList.add("on"); const bb=document.createElement("div"); bb.className="bubble";
      bb.textContent = e.kind==="agent" ? (e.detail || "au travail") : `${short(e.kind,e.name)}${e.detail? " · "+e.detail:""}`.slice(0,60); a.appendChild(bb); }
    if(e.kind!=="agent"){ const p = poste(e.bureau, e.kind, e.name); p && p.classList.add("on"); }
    if(whoB !== e.bureau) document.getElementById("r-"+whoB)?.classList.add("on");
  });
  const now = document.getElementById("now");
  if(s.active.length){ now.classList.add("show");
    now.innerHTML = s.active.slice(-3).reverse().map(e => {
      const who = e.kind==="agent" ? e.name : (e.agent||"claude");
      const what = e.kind==="agent" ? "agent appelé" : short(e.kind,e.name);
      return `<span>En cours : <b>${esc(who)}</b> <span class="sep">→</span> <b>${esc(what)}</b> <span class="k">${esc(e.kind)} · ${esc(CAT.find(b=>b.id===e.bureau)?.label||"")}${e.running===false?" · terminé":""}</span></span>`;
    }).join('<span class="sep">|</span>');
  } else { now.classList.remove("show"); now.innerHTML = ""; }
  const liveIds = new Set(s.active.map(e=>e.id));
  document.getElementById("feed").innerHTML = s.feed.slice().reverse().map(e => e.ev==="prompt"
    ? `<li class="prompt"><span class="t">${e.ts.slice(11,19)}</span><span class="w"><b>Demande</b><span class="d">${esc(e.detail)}</span></span></li>`
    : `<li class="${liveIds.has(e.id)?"live":""}"><span class="t">${e.ts.slice(11,19)}</span><span class="w"><b>${esc(e.kind==="agent"?e.name:(e.agent||"claude"))}</b> → ${esc(short(e.kind,e.name))}
       <span class="d">${esc(CAT.find(b=>b.id===e.bureau)?.label||"")}${e.detail?" · "+esc(e.detail):""}</span></span></li>`).join("");
}
let demoUntil = 0;
async function tick(){ if(Date.now() > demoUntil){ try{ const r = await fetch("/agence/state.json",{cache:"no-store"}); render(await r.json()); }catch(e){} } setTimeout(tick, 500); }
const SCEN = [
  {kind:"prompt", detail:"Fais-moi le dossier projet du comité de jeudi"},
  {kind:"skill", name:"slide-style", bureau:"studio", agent:"claude", detail:"charte des slides"},
  {kind:"agent", name:"jira-sprints-audit", bureau:"jira", detail:"audit du plan de sprints"},
  {kind:"connector", name:"mcp__atlassian__searchJiraIssuesUsingJql", bureau:"jira", agent:"jira-sprints-audit", detail:"tickets du sprint 3"},
  {kind:"agent", name:"notion-topics-audit", bureau:"notion", detail:"relire les sujets"},
  {kind:"connector", name:"mcp__notion__notion-query-data-sources", bureau:"notion", agent:"notion-topics-audit", detail:"base Suivi des sujets"},
  {kind:"generator", name:"risks", bureau:"office", agent:"claude", detail:"registre des risques"},
  {kind:"agent", name:"archi-audit", bureau:"studio", detail:"vue macro de l'architecture"},
  {kind:"generator", name:"archi", bureau:"studio", agent:"archi-audit", detail:"rendu golden"},
  {kind:"skill", name:"voice-slides", bureau:"redaction", agent:"claude", detail:"légendes des slides"},
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
