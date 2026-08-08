(() => {
"use strict";
const gui={selected:new Set(),direction:"asc",visibleIds:[]};

function syncCount(){
 const el=document.getElementById("mh-selected-count");
 if(el) el.textContent=`${gui.selected.size} ausgewählt`;
}

function hookRows(){
 const body=document.getElementById("mh-preview-rows"); if(!body)return;
 const rows=[...body.querySelectorAll("tr[data-id]")];
 gui.visibleIds=rows.filter(r=>!r.hidden).map(r=>r.dataset.id);
 rows.forEach(row=>{
   if(!row.querySelector(".mh-preview-checkbox")){
     const cell=document.createElement("td");
     const box=document.createElement("input");
     box.type="checkbox"; box.className="mh-preview-checkbox";
     box.addEventListener("click",e=>e.stopPropagation());
     box.addEventListener("change",()=>{
       if(box.checked)gui.selected.add(row.dataset.id);else gui.selected.delete(row.dataset.id);
       row.classList.toggle("mh-preview-selected",box.checked); syncCount();
     });
     cell.appendChild(box); row.insertBefore(cell,row.firstChild);
   }
   const box=row.querySelector(".mh-preview-checkbox");
   box.checked=gui.selected.has(row.dataset.id);
   row.classList.toggle("mh-preview-selected",box.checked);
 });
 syncCount();
}

function statusFilter(){
 const wanted=document.getElementById("mh-status-filter")?.value||"all";
 document.querySelectorAll("#mh-preview-rows tr[data-id]").forEach(row=>{
   const status=(row.children[1]?.textContent||"").toLowerCase();
   row.hidden=wanted!=="all"&&!status.includes(wanted);
 });
 gui.visibleIds=[...document.querySelectorAll("#mh-preview-rows tr[data-id]:not([hidden])")].map(r=>r.dataset.id);
}

function selectVisible(){gui.visibleIds.forEach(id=>gui.selected.add(id));hookRows();}
function clearSelection(){gui.selected.clear();hookRows();}
function bulkDecision(state){
 document.querySelectorAll("#mh-preview-rows tr[data-id]").forEach(row=>{
   if(!gui.selected.has(row.dataset.id))return;
   const select=row.querySelector("[data-decision]");
   if(select){select.value=state;select.dispatchEvent(new Event("change",{bubbles:true}));}
 });
}
function sortRows(){
 const body=document.getElementById("mh-preview-rows");if(!body)return;
 const by=document.getElementById("mh-sort-by")?.value||"current_name";
 const col={current_name:2,confidence:5,relation_type:4,season:2,episode:2}[by]??2;
 const rows=[...body.querySelectorAll("tr[data-id]")];
 rows.sort((a,b)=>{
   const av=(a.children[col]?.textContent||"").trim(),bv=(b.children[col]?.textContent||"").trim();
   const cmp=av.localeCompare(bv,undefined,{numeric:true,sensitivity:"base"});
   return gui.direction==="asc"?cmp:-cmp;
 });
 rows.forEach(r=>body.appendChild(r));hookRows();statusFilter();
}

document.addEventListener("DOMContentLoaded",()=>{
 const body=document.getElementById("mh-preview-rows");
 if(body)new MutationObserver(hookRows).observe(body,{childList:true});
 hookRows();
 document.getElementById("mh-select-visible")?.addEventListener("click",selectVisible);
 document.getElementById("mh-clear-selection")?.addEventListener("click",clearSelection);
 document.querySelectorAll("[data-bulk-state]").forEach(b=>b.addEventListener("click",()=>bulkDecision(b.dataset.bulkState)));
 document.getElementById("mh-status-filter")?.addEventListener("change",statusFilter);
 document.getElementById("mh-sort-by")?.addEventListener("change",sortRows);
 document.getElementById("mh-sort-direction")?.addEventListener("click",()=>{
   gui.direction=gui.direction==="asc"?"desc":"asc";
   document.getElementById("mh-sort-direction").textContent=gui.direction==="asc"?"↑":"↓";
   sortRows();
 });
});

window.MediaHubSmartRenamerGUI={selectedIds:()=>[...gui.selected],selectVisible,clearSelection};
})();