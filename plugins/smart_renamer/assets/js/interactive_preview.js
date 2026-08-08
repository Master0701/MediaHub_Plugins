(() => {
"use strict";
const state={payload:null,group:"",decisions:new Map(),selectedId:"",aiStatus:null};
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
 body.querySelectorAll("tr[data-id]").forEach(tr=>tr.onclick=e=>{
   if(e.target.closest("select"))return;
   state.selectedId=tr.dataset.id||"";
   body.querySelectorAll("tr[data-id]").forEach(x=>x.classList.toggle("mh-preview-selected",x.dataset.id===state.selectedId));
   detail(state.selectedId);
   updateAIButton();
 });
 body.querySelectorAll("[data-decision]").forEach(sel=>sel.onchange=()=>state.decisions.set(sel.dataset.decision,sel.value));
}
function detail(id){
 const r=state.payload?.rows.find(x=>x.id===id),el=document.getElementById("mh-preview-detail"); if(!r||!el)return;
 el.innerHTML=`<p><strong>${esc(r.current_name)}</strong></p><p>Relation: ${esc(r.relation_type)}</p><p>Profil: ${esc(r.profile_name)}</p><p>Aktion: ${esc(r.recommended_action)}</p><p>Begleitdateien: ${r.companion_count}</p><ul>${(r.warnings||[]).map(w=>`<li>${esc(w)}</li>`).join("")||"<li>Keine Warnungen</li>"}</ul>`;
}
async function loadAIStatus(){
 const statusEl=document.getElementById("mh-ai-review-status");
 try{
   const response=await fetch("/smart-renamer/api/ai-review/status",{cache:"no-store"});
   const data=await response.json();
   state.aiStatus=data;
   if(data.available){
     if(statusEl)statusEl.textContent=`verfügbar · ${data.provider||"Provider"}`;
   }else{
     if(statusEl)statusEl.textContent="nicht verfügbar · manueller Review bleibt aktiv";
   }
 }catch(error){
   state.aiStatus={available:false};
   if(statusEl)statusEl.textContent="Status nicht verfügbar";
 }
 updateAIButton();
}
function updateAIButton(){
 const button=document.getElementById("mh-ai-review-run");
 if(button)button.disabled=!(state.aiStatus?.available&&state.selectedId);
}
async function runAIReview(){
 const row=state.payload?.rows.find(x=>x.id===state.selectedId);
 const resultEl=document.getElementById("mh-ai-review-result");
 if(!row||!resultEl)return;
 resultEl.textContent="KI analysiert …";
 try{
   const response=await fetch("/smart-renamer/api/ai-review/analyze",{
     method:"POST",
     headers:{"Content-Type":"application/json"},
     body:JSON.stringify(row)
   });
   const data=await response.json();
   if(!response.ok||data.ok===false)throw new Error(data.error||("HTTP "+response.status));
   if(!data.available){
     resultEl.textContent="Kein KI-Provider verfügbar. Manueller Review bleibt aktiv.";
     return;
   }
   const warnings=(data.warnings||[]).join("; ");
   resultEl.innerHTML=
     `<strong>${esc(data.recommendation||"Vorschlag")}</strong>`+
     (data.suggested_name?`<br>Namensvorschlag: ${esc(data.suggested_name)}`:"")+
     `<br>Confidence: ${Math.round((Number(data.confidence)||0)*100)}%`+
     `<br>Begründung: ${esc(data.rationale||"—")}`+
     (warnings?`<br>Warnungen: ${esc(warnings)}`:"")+
     `<br><em>Nur Vorschlag · keine Dateiänderung · Benutzerbestätigung erforderlich.</em>`;
 }catch(error){
   resultEl.textContent="KI-Review fehlgeschlagen: "+error;
 }
}
document.addEventListener("DOMContentLoaded",()=>{
 document.getElementById("mh-preview-filter")?.addEventListener("input",rows);
 document.getElementById("mh-ai-review-run")?.addEventListener("click",runAIReview);
 loadAIStatus();
});
window.MediaHubSmartRenamerPreview={render};
})();