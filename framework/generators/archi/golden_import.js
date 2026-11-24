/* golden_import.js - sequences et import draw.io par vue, au style du schema de reference.
   - window.SEQ[vid] : vues `kind: sequence` du modele, rendues ici (participants, lignes de vie, messages numerotes).
   - aucun bouton ni import cote navigateur : tout passe par le modele (prompt + template).
   - window.IMPORTS[vid] : import fige dans le modele (views[].drawio), applique au chargement. */
(function(){
  var A=window.__archi||{}, L=window.LOGOS||{};
  function esc(t){return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function N(v){return Math.round(v*10)/10;}
  function tw(t,k){return String(t||'').length*({t:8.4,tm:7.5,s:6.4,lbl:6.7}[k||'tm']);}
  var ROLE={core:'var(--sai)',service:'var(--grn)',auth:'var(--kc)',storage:'var(--s3)',db:'var(--rds)',cluster:'#326CE5',risk:'var(--soc)',ops:'var(--amb)',partner:'var(--air)',partner2:'var(--ksatc)',ext:'var(--ext)'};
  function tok(c){if(!c)return null;c=String(c);if(c[0]==='#'||c.indexOf('var(')===0)return c;return ROLE[c]||('var(--'+c+')');}
  function marker(id){return '<defs><marker id="'+id+'" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M2 2 L8 5 L2 8" fill="none" stroke="context-stroke" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>';}
  function lbl(x,y,t,anchor,col){if(!t)return '';return '<text class="lbl" x="'+N(x)+'" y="'+N(y)+'" text-anchor="'+(anchor||'middle')+'" style="fill:'+(col||'var(--muted)')+'">'+esc(t)+'</text>';}
  function guessLogo(label){var s=' '+String(label||'').toLowerCase()+' ',best=null;Object.keys(L).forEach(function(k){if(best||k.length<3||k==='user')return;var kk=k.replace(/[^a-z0-9]/g,'');if(new RegExp('[^a-z0-9]'+kk+'[^a-z0-9]').test(s))best=k;});return best;}
  function guessRole(label){var s=String(label||'').toLowerCase();if(/keycloak|oidc|idp|sso|auth/.test(s))return 'auth';if(/postgres|rds|database|base de donn/.test(s))return 'db';if(/\bs3\b|bucket|stockage/.test(s))return 'storage';if(/user|utilisateur|analyst|op[ée]rat/.test(s))return 'ext';return null;}
  function plate(x,y,w,h,k,pad){pad=pad==null?3:pad;if(!k||!L[k])return '';return '<rect x="'+N(x)+'" y="'+N(y)+'" width="'+N(w)+'" height="'+N(h)+'" rx="5" fill="#ffffff"/><image data-logo="'+esc(k)+'" x="'+N(x+pad)+'" y="'+N(y+pad)+'" width="'+N(w-2*pad)+'" height="'+N(h-2*pad)+'" preserveAspectRatio="xMidYMid meet"/>';}
  function wrap(t,w,k,max){var cap=Math.max(4,Math.floor(w/({t:8.4,tm:7.5,s:6.4,lbl:6.7}[k||'tm']))),ws=String(t||'').split(/\s+/),ls=[],c='';ws.forEach(function(x){if(!x)return;if(!c)c=x;else if((c+' '+x).length<=cap)c+=' '+x;else{ls.push(c);c=x;}});if(c)ls.push(c);max=max||2;if(ls.length>max){ls=ls.slice(0,max);ls[max-1]=ls[max-1].slice(0,cap-1)+'…';}return ls.map(function(l){return l.length>cap?l.slice(0,cap-1)+'…':l;});}

  /* ---------------- sequence (meme dessin que « Applications partenaires ») */
  function seqSVG(spec,id){
    var P=spec.participants||[],M=spec.messages||[],mid='sq-'+String(id).replace(/[^A-Za-z0-9_-]/g,'');
    var n=P.length,xs=[],lo=120,hi=n<=4?960:1080,i;
    if(n===1)xs=[590];else for(i=0;i<n;i++)xs.push(lo+i*(hi-lo)/Math.max(1,n-1));
    var gap=n>1?(hi-lo)/(n-1):400,idx={},o=[],top=44;
    var roles=[];P.forEach(function(p,k){idx[p.id]=k;roles[k]=p.color||guessRole(p.label);});
    if(spec.caption)o.push(lbl(40,24,spec.caption,'start',spec.caption_color||'var(--kc)'));
    P.forEach(function(p,k){
      var cx=xs[k],logo=p.logo||guessLogo(p.label),hasL=!!(logo&&L[logo]),role=p.color||guessRole(p.label);
      var w=Math.min(Math.max(100,tw(p.label)+40+(hasL?40:0)),Math.max(100,gap-16)),x=cx-w/2,col=tok(role);
      if(role==='auth')o.push('<rect x="'+N(x)+'" y="'+(top-4)+'" width="'+N(w)+'" height="48" rx="8" fill="var(--kc-bg)" stroke="var(--kc)" stroke-width="1.3"/>');
      else o.push('<rect class="box" x="'+N(x)+'" y="'+top+'" width="'+N(w)+'" height="40" rx="8"'+(col&&role!=='ext'?' style="stroke:'+col+'"':'')+'/>');
      var tx=cx;
      if(role==='ext'&&!hasL){o.push('<circle cx="'+N(x+22)+'" cy="'+(top+20)+'" r="13" fill="#5f6b7a"/>'+(L.user?'<image data-logo="user" x="'+N(x+12)+'" y="'+(top+10)+'" width="20" height="20" preserveAspectRatio="xMidYMid meet"/>':''));tx=cx+14;}
      if(hasL){o.push(plate(x+9,top+(role==='auth'?3:4),32,32,logo));tx=cx+20;}
      o.push('<text class="tm" x="'+N(tx)+'" y="'+(top+25)+'" text-anchor="middle"'+(role==='auth'?' style="fill:var(--kc)"':'')+'>'+esc(wrap(p.label,w-(hasL?50:16),'tm',1)[0])+'</text>');
    });
    var y1=top+50,yEnd=y1+28+M.length*44+8;
    xs.forEach(function(x){o.push('<line x1="'+N(x)+'" y1="'+y1+'" x2="'+N(x)+'" y2="'+yEnd+'" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 4"/>');});
    M.forEach(function(m,k){
      var a=idx[m.from],b=idx[m.to];if(a==null||b==null)return;
      var au=m.kind==='auth'||(m.kind!=='return'&&!m.dashed&&(roles[a]==='auth'||roles[b]==='auth'));
      var y=y1+28+k*44,cls=au?'auth':'arr',dash=(m.kind==='return'||m.dashed)?' stroke-dasharray="5 4"':'',t=(k+1)+'. '+(m.label||'');
      if(a===b){var x=xs[a];o.push(lbl(x+20,y,t,'start'));o.push('<path class="'+cls+'" d="M'+N(x-8)+' '+(y+8)+' C'+N(x-40)+' '+(y+4)+' '+N(x-40)+' '+(y+24)+' '+N(x-8)+' '+(y+20)+'" fill="none"'+dash+' marker-end="url(#'+mid+')"/>');}
      else{var x1=xs[a],x2=xs[b],d=x2>x1?1:-1;o.push(lbl((x1+x2)/2,y,t));o.push('<path class="'+cls+'" d="M'+N(x1)+' '+(y+8)+' L'+N(x2-2*d)+' '+(y+8)+'" fill="none"'+dash+' marker-end="url(#'+mid+')"/>');}
    });
    var notes=spec.notes||[];
    notes.forEach(function(t,k){o.push('<text class="s" x="590" y="'+(yEnd+30+22*k)+'" text-anchor="middle" style="fill:var(--muted)">'+esc(t)+'</text>');});
    var H=yEnd+(notes.length?30+22*notes.length:24);
    return '<svg viewBox="0 0 1180 '+H+'" role="img" aria-label="Diagramme de séquence">'+marker(mid)+o.join('')+'</svg>';
  }

  /* ---------------- lecture d'un .drawio */
  function inflate(b64){
    var bin=atob(b64),u=new Uint8Array(bin.length);for(var i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
    var s=new Blob([u]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
    return new Response(s).text().then(function(t){try{return decodeURIComponent(t);}catch(e){return t;}});
  }
  function pages(xml){
    var doc=new DOMParser().parseFromString(xml,'text/xml'),ds=[].slice.call(doc.getElementsByTagName('diagram'));
    if(!ds.length){var g=doc.getElementsByTagName('mxGraphModel')[0];return Promise.resolve(g?[{name:'Page 1',model:g}]:[]);}
    return Promise.all(ds.map(function(d){
      var g=d.getElementsByTagName('mxGraphModel')[0],nm=d.getAttribute('name')||'Page';
      if(g)return Promise.resolve({name:nm,model:g});
      var t=(d.textContent||'').trim();if(!t)return Promise.resolve(null);
      return inflate(t).then(function(x){var gd=new DOMParser().parseFromString(x,'text/xml');return {name:nm,model:gd.getElementsByTagName('mxGraphModel')[0]};}).catch(function(){return null;});
    })).then(function(a){return a.filter(function(p){return p&&p.model;});});
  }
  function clean(v){if(!v)return '';var d=document.createElement('div');d.innerHTML=String(v).replace(/<br\s*\/?>/gi,' ').replace(/<\/(div|p|li)>/gi,' ');return (d.textContent||'').replace(/\s+/g,' ').trim();}
  function cellsOf(model){
    var out={};
    [].slice.call(model.getElementsByTagName('mxCell')).forEach(function(c){
      var p=c.parentNode,id=c.getAttribute('id'),val=c.getAttribute('value');
      if(p&&(p.tagName==='UserObject'||p.tagName==='object')){id=p.getAttribute('id');val=p.getAttribute('label');}
      var g=c.getElementsByTagName('mxGeometry')[0],geo=null;
      if(g){geo={x:+(g.getAttribute('x')||0),y:+(g.getAttribute('y')||0),w:+(g.getAttribute('width')||0),h:+(g.getAttribute('height')||0),sp:null,tp:null};
        [].slice.call(g.getElementsByTagName('mxPoint')).forEach(function(pt){var as=pt.getAttribute('as'),P={x:+(pt.getAttribute('x')||0),y:+(pt.getAttribute('y')||0)};if(as==='sourcePoint')geo.sp=P;else if(as==='targetPoint')geo.tp=P;});}
      out[id]={id:id,value:clean(val),style:c.getAttribute('style')||'',parent:c.getAttribute('parent'),vertex:c.getAttribute('vertex')==='1',edge:c.getAttribute('edge')==='1',source:c.getAttribute('source'),target:c.getAttribute('target'),geo:geo};
    });
    function abs(c,d){if(c._abs)return c._abs;var g=c.geo||{x:0,y:0,w:0,h:0},p=out[c.parent],ox=0,oy=0;if(p&&p.vertex&&d<30){var a=abs(p,d+1);ox=a.x;oy=a.y;}c._abs={x:g.x+ox,y:g.y+oy,w:g.w,h:g.h};return c._abs;}
    Object.keys(out).forEach(function(k){if(out[k].vertex)abs(out[k],0);});
    Object.keys(out).forEach(function(k){var c=out[k];if(c.vertex&&/edgeLabel/.test(c.style)&&out[c.parent]&&out[c.parent].edge&&!out[c.parent].value)out[c.parent].value=c.value;});
    return out;
  }
  var RX_LIFE=/umlLifeline|shape=umlActor|participant=/;
  function toSeq(cells,title){
    var all=Object.keys(cells).map(function(k){return cells[k];});
    var lifes=all.filter(function(c){return c.vertex&&RX_LIFE.test(c.style);});
    if(lifes.length<2)lifes=all.filter(function(c){return c.vertex&&c._abs&&c.value&&!/edgeLabel|text;/.test(c.style)&&!(cells[c.parent]&&(cells[c.parent].vertex||cells[c.parent].edge));});
    lifes.sort(function(a,b){return a._abs.x-b._abs.x;});
    var lifeIds={};lifes.forEach(function(l){lifeIds[l.id]=1;});
    var P=lifes.map(function(c){return {id:c.id,label:c.value||'?',color:/umlActor/.test(c.style)?'ext':null};});
    function lifeOf(id,pt){var c=cells[id],d=0;while(c&&d<30){if(lifeIds[c.id])return c.id;c=cells[c.parent];d++;}
      if(pt){var best=null,bd=1e9;lifes.forEach(function(l){var cx=l._abs.x+l._abs.w/2,dd=Math.abs(cx-pt.x);if(dd<bd){bd=dd;best=l.id;}});return best;}return null;}
    var msgs=[];
    all.filter(function(c){return c.edge;}).forEach(function(e,k){
      var s=cells[e.source],t=cells[e.target],g=e.geo||{};
      var sp=g.sp||(s&&s._abs?{x:s._abs.x+s._abs.w/2,y:s._abs.y}:null),tp=g.tp||(t&&t._abs?{x:t._abs.x+t._abs.w/2,y:t._abs.y}:null);
      var a=lifeOf(e.source,sp),b=lifeOf(e.target,tp);if(!a||!b)return;
      var y=(g.sp&&g.sp.y)||(g.tp&&g.tp.y)||(s&&s._abs?s._abs.y+(/exitY=([0-9.]+)/.test(e.style)?s._abs.h*+RegExp.$1:0):0)||k;
      msgs.push({from:a,to:b,label:e.value,kind:/dashed=1/.test(e.style)?'return':null,y:y,k:k});
    });
    msgs.sort(function(a,b){return (a.y-b.y)||(a.k-b.k);});
    return {caption:'Séquence importée'+(title?' - '+title:''),caption_color:'var(--muted)',participants:P,messages:msgs};
  }
  function frameColor(t){t=String(t||'').toLowerCase();if(/kubernetes|\beks\b|cluster/.test(t))return ['#326CE5','4 4'];if(/namespace/.test(t))return ['var(--grn)','6 5'];if(/aws|infra|cloud|vpc|compte/.test(t))return ['var(--sai)','6 5'];return null;}
  function boxesSVG(cells,title,id){
    var all=Object.keys(cells).map(function(k){return cells[k];}),mid='im-'+String(id).replace(/[^A-Za-z0-9_-]/g,'');
    var V=all.filter(function(c){return c.vertex&&c._abs&&c._abs.w>0&&c._abs.h>0&&!/edgeLabel/.test(c.style)&&!(cells[c.parent]&&cells[c.parent].edge);});
    if(!V.length)return null;
    function inside(a,b){return a!==b&&a._abs.x>=b._abs.x-1&&a._abs.y>=b._abs.y-1&&a._abs.x+a._abs.w<=b._abs.x+b._abs.w+1&&a._abs.y+a._abs.h<=b._abs.y+b._abs.h+1;}
    V.forEach(function(c){c._txt=/(^|;)text;/.test(c.style)||(/strokeColor=none/.test(c.style)&&/fillColor=none/.test(c.style));
      c._cont=/swimlane|group|container=1/.test(c.style)||V.some(function(o){return o!==c&&(o.parent===c.id||(!o._txt&&inside(o,c)));});});
    var x0=Math.min.apply(null,V.map(function(c){return c._abs.x;})),y0=Math.min.apply(null,V.map(function(c){return c._abs.y;}));
    var x1=Math.max.apply(null,V.map(function(c){return c._abs.x+c._abs.w;})),y1=Math.max.apply(null,V.map(function(c){return c._abs.y+c._abs.h;}));
    var leaves=V.filter(function(c){return !c._cont&&!c._txt&&c.value;}).map(function(c){return (tw(c.value)/2+24)/Math.max(20,c._abs.w);}).sort(function(a,b){return a-b;});
    var sText=leaves.length?leaves[Math.floor(leaves.length*0.6)]:1;
    var s=Math.max(Math.min(1.3,1100/Math.max(1,x1-x0)),Math.min(3,sText)),VW=Math.max(1180,80+(x1-x0)*s);
    function T(r){return {x:40+(r.x-x0)*s,y:70+(r.y-y0)*s,w:r.w*s,h:r.h*s};}
    var o=[lbl(40,36,'Schéma importé'+(title?' - '+title:''),'start')],ar=[];
    V.filter(function(c){return c._cont;}).sort(function(a,b){return b._abs.w*b._abs.h-a._abs.w*a._abs.h;}).forEach(function(c){
      var r=T(c._abs),fc=frameColor(c.value);
      if(fc)o.push('<rect x="'+N(r.x)+'" y="'+N(r.y)+'" width="'+N(r.w)+'" height="'+N(r.h)+'" rx="14" fill="none" stroke="'+fc[0]+'" stroke-width="1.4" stroke-dasharray="'+fc[1]+'"/>');
      else o.push('<rect class="zone" x="'+N(r.x)+'" y="'+N(r.y)+'" width="'+N(r.w)+'" height="'+N(r.h)+'" rx="14"/>');
      if(c.value)o.push(lbl(r.x+14,r.y+20,c.value,'start',fc?fc[0]:'var(--muted)'));
    });
    V.filter(function(c){return !c._cont;}).forEach(function(c){
      var r=T(c._abs);
      if(c._txt){if(c.value)o.push(lbl(r.x+r.w/2,r.y+r.h/2+4,c.value));return;}
      var role=guessRole(c.value),col=tok(role),logo=guessLogo(c.value),ls=wrap(c.value,r.w-12,'tm',r.h>=48?2:1);
      if(role==='db'){var cx=r.x+r.w/2,cy=r.y+r.h/2-12,cc='var(--rds)';
        o.push('<ellipse cx="'+N(cx)+'" cy="'+N(cy+24)+'" rx="15" ry="5" fill="'+cc+'"/><rect x="'+N(cx-15)+'" y="'+N(cy)+'" width="30" height="24" fill="'+cc+'"/><ellipse cx="'+N(cx)+'" cy="'+N(cy+12)+'" rx="15" ry="5" fill="#7badde" stroke="'+cc+'"/><ellipse cx="'+N(cx)+'" cy="'+N(cy)+'" rx="15" ry="5" fill="#9cc2e8" stroke="'+cc+'"/><text class="tm" x="'+N(cx)+'" y="'+N(cy+44)+'" text-anchor="middle" style="fill:'+cc+'">'+esc(ls[0])+'</text>');return;}
      o.push('<rect class="box" x="'+N(r.x)+'" y="'+N(r.y)+'" width="'+N(r.w)+'" height="'+N(r.h)+'" rx="10"'+(col&&role!=='ext'?' style="stroke:'+col+'"':'')+'/>');
      if(logo&&r.w>=110&&r.h>=50)o.push(plate(r.x+8,r.y+8,40,16,logo,2));
      var ty=r.y+r.h/2+5-(ls.length-1)*9;
      ls.forEach(function(l,k){o.push('<text class="tm" x="'+N(r.x+r.w/2)+'" y="'+N(ty+k*18)+'" text-anchor="middle"'+(role==='auth'?' style="fill:var(--kc)"':'')+'>'+esc(l)+'</text>');});
    });
    all.filter(function(c){return c.edge;}).forEach(function(e){
      var S=cells[e.source],G=cells[e.target],g=e.geo||{};
      var a=S&&S._abs?T(S._abs):(g.sp?T({x:g.sp.x,y:g.sp.y,w:0,h:0}):null),b=G&&G._abs?T(G._abs):(g.tp?T({x:g.tp.x,y:g.tp.y,w:0,h:0}):null);
      if(!a||!b)return;
      var sx=a.x+a.w/2,sy=a.y+a.h/2,tx=b.x+b.w/2,ty=b.y+b.h/2,pts;
      var ox0=Math.max(a.x,b.x),ox1=Math.min(a.x+a.w,b.x+b.w),oy0=Math.max(a.y,b.y),oy1=Math.min(a.y+a.h,b.y+b.h);
      if(ox1-ox0>12){var x=(ox0+ox1)/2;pts=ty>sy?[[x,a.y+a.h],[x,b.y-2]]:[[x,a.y],[x,b.y+b.h+2]];}
      else if(oy1-oy0>12){var y=(oy0+oy1)/2;pts=tx>sx?[[a.x+a.w,y],[b.x-2,y]]:[[a.x,y],[b.x+b.w+2,y]];}
      else{var xa=tx>sx?a.x+a.w:a.x;pts=[[xa,sy],[tx,sy],[tx,ty>sy?b.y-2:b.y+b.h+2]];}
      var cls=/dashed=1/.test(e.style)?'arr" stroke-dasharray="5 4':'arr';
      ar.push('<path class="'+cls+'" d="M'+pts.map(function(p){return N(p[0])+' '+N(p[1]);}).join(' L')+'" fill="none" marker-end="url(#'+mid+')"/>');
      if(e.value){var bi=0,bl=-1;for(var i=0;i<pts.length-1;i++){var l=Math.abs(pts[i+1][0]-pts[i][0])+Math.abs(pts[i+1][1]-pts[i][1]);if(l>bl){bl=l;bi=i;}}
        var p=pts[bi],q=pts[bi+1],hz=Math.abs(q[1]-p[1])<1;ar.push(lbl((p[0]+q[0])/2+(hz?0:10),(p[1]+q[1])/2+(hz?-8:4),e.value,hz?'middle':'start'));}
    });
    var H=70+(y1-y0)*s+50;
    return '<svg viewBox="0 0 '+N(VW)+' '+N(H)+'" role="img" aria-label="Schéma importé">'+marker(mid)+o.join('')+ar.join('')+'</svg>';
  }
  /* mode : 'schema' (defaut) ou 'sequence' ; jamais choisi a la place de la personne, seulement suggere */
  function renderXML(xml,pageIdx,name,id,mode){
    return pages(xml).then(function(ps){
      if(!ps.length)throw new Error('vide');
      var p=ps[Math.min(pageIdx||0,ps.length-1)],cells=cellsOf(p.model),title=name+(ps.length>1?' / '+p.name:'');
      var nLife=Object.keys(cells).filter(function(k){return cells[k].vertex&&RX_LIFE.test(cells[k].style);}).length;
      var isSeq=(mode==='sequence');
      var svg=isSeq?seqSVG(toSeq(cells,title),id):boxesSVG(cells,title,id);
      if(!svg)throw new Error('vide');
      return {svg:svg,pages:ps.map(function(q){return q.name;}),seq:isSeq,suggestSeq:nLife>=2};
    });
  }

  /* ---------------- branchement des vues : rendu seul (sequences + imports figes dans le modele).
     Aucune edition ni import cote navigateur (24/11/2026 : le schema se construit par prompt + template). */
  var SEQ=window.SEQ||{},IMP=window.IMPORTS||{};
  document.querySelectorAll('svg[data-seq]').forEach(function(sv){var id=sv.getAttribute('data-seq');if(SEQ[id]){var d=document.createElement('div');d.innerHTML=seqSVG(SEQ[id],id);sv.parentNode.replaceChild(d.firstChild,sv);}});
  if(A.logos)A.logos(document);
  document.querySelectorAll('.view').forEach(function(v){
    var vid=v.id.slice(2),box=v.querySelector('.vsvg'),imp=IMP[vid];if(!box||!imp)return;
    renderXML(imp.xml,imp.page||0,imp.name,vid,imp.mode||'schema').then(function(r){
      box.innerHTML=r.svg;if(A.logos)A.logos(box);if(A.bind)A.bind(box);
    }).catch(function(){});
  });
  window.__archiImport={seqSVG:seqSVG,renderXML:renderXML};
})();
