(() => {
"use strict";
const state={payload:null,group:"",decisions:new Map()};
const esc=v=>String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;");
function render(payload){
 state.payload=payload; const s=payload.summary||{};
 document.querySelector('[data-kind="safe"]').textContent=`Sicher: ${s.safe||0}`;
 document.querySelector('[data-kind="review"]').textContent=`Review: ${s.review||0}`;
 document.querySelector('[data-kind="conflict"]').textContent=`Konflikt: ${s.conflict||0}`;
 groups(); rows();
}
function groups(){
 const el=document.getElementById("mh-preview-groups"); if(!el||!state.payload)return;
 el.innerHTML=state.payload.groups.map(g=>`<button type="button" data-group="${esc(g.key)}">${esc(g.label)} (${g.count})</button>`).join("");
 el.querySelectorAll("[data-group]").forEach(b=>b.onclick=()=>{state.group=b.dataset.group||"";rows();});
}
function rows(){
 const body=document.getElementById("mh-preview-rows"); if(!body||!state.payload)return;
 const term=(document.getElementById("mh-preview-filter")?.value||"").toLowerCase();
 const list=state.payload.rows.filter(r=>{
   const key=r.media_type==="series"?`series:season:${String(r.season||"00").padStart(2,"0")}`:r.media_type;
   if(state.group&&key!==state.group)return false;
   return !term||`${r.current_name} ${r.suggested_name} ${r.relation_type}`.toLowerCase().includes(term);
 });
 body.innerHTML=list.map(r=>`<tr data-id="${esc(r.id)}"><td>${esc(r.status)}</td><td>${esc(r.current_name)}</td><td>${esc(r.suggested_name||"—")}</td><td>${esc(r.relation_type)}</td><td>${Math.round((r.confidence||0)*100)}%</td><td><select data-decision="${esc(r.id)}"><option value="pending">Offen</option><option value="accepted">Übernehmen</option><option value="ignored">Ignorieren</option><option value="manual">Manuell</option><option value="review">Prüfen</option></select></td></tr>`).join("");
 body.querySelectorAll("tr[data-id]").forEach(tr=>tr.onclick=e=>{if(e.target.closest("select"))return;detail(tr.dataset.id);});
 body.querySelectorAll("[data-decision]").forEach(sel=>sel.onchange=()=>state.decisions.set(sel.dataset.decision,sel.value));
}
function detail(id){
 const r=state.payload?.rows.find(x=>x.id===id),el=document.getElementById("mh-preview-detail"); if(!r||!el)return;
 el.innerHTML=`<p><strong>${esc(r.current_name)}</strong></p><p>Relation: ${esc(r.relation_type)}</p><p>Profil: ${esc(r.profile_name)}</p><p>Aktion: ${esc(r.recommended_action)}</p><p>Begleitdateien: ${r.companion_count}</p><ul>${(r.warnings||[]).map(w=>`<li>${esc(w)}</li>`).join("")||"<li>Keine Warnungen</li>"}</ul>`;
}
document.addEventListener("DOMContentLoaded",()=>document.getElementById("mh-preview-filter")?.addEventListener("input",rows));
window.MediaHubSmartRenamerPreview={render};
})();