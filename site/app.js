import {day,today,effectiveState,actionable,filtered} from './logic.js';
const $=s=>document.querySelector(s);
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const link=u=>{try{return new URL(u).protocol==='https:'?escape(u):'#'}catch{return '#'}};
const fmt=d=>d?new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(day(d)):'To be announced';
const stateLabel={open:'Open',closed:'Submissions closed',not_yet_open:'Call not yet open',unknown:'Call unconfirmed',withdrawn:'Withdrawn'};
let events=[],series=[],status={},view='open';
const tags=r=>`<div class="tags">${r.topics.map(t=>`<span class="tag">${escape(t)}</span>`).join('')}</div>`;
const dates=r=>r.event_start?fmt(r.event_start)+(r.event_end&&r.event_end!==r.event_start?' – '+fmt(r.event_end):''):'Dates unannounced';
function deadlineCell(r,c){
 const state=effectiveState(c);const days=c.deadline?Math.round((day(c.deadline)-day(today()))/86400000):null;
 const urgency=state==='open'&&days<=7?'urgent':state==='open'&&days<=30?'soon':'';
 return `<div class="deadline ${urgency}">${c.deadline?fmt(c.deadline):'—'}</div>${state==='open'&&days!==null?`<span class="countdown ${urgency}">${days===0?'Due today':days===1?'1 day left':days+' days left'}</span>`:`<span class="badge">${stateLabel[state]||'Unconfirmed'}</span>`}${c.deadline_time?`<span class="meta">${escape(c.deadline_time)} ${escape(c.deadline_timezone||'(zone unspecified)')}</span>`:''}${view==='open'?`<p class="call-kind">${escape(c.kind)}</p>`:''}`;
}
function render(){
 const filters=Object.fromEntries(['search','topic','region','organizer'].map(k=>[k,$('#'+k).value]));
 $('#sort-control').hidden=view==='series';
 $('.filters label:nth-child(4)').hidden=view==='series';
 let records=filtered(view==='series'?series:events,view==='series'?{...filters,organizer:''}:filters);
 const problems=events.filter(r=>r.health!=='verified').length;
 $('#notice').hidden=!problems;
 $('#notice').textContent=`${problems} event source${problems===1?' needs':'s need'} another check. Failed fetches keep the last verified facts; disputed dates and records unverified for over 14 days are excluded from open calls.`;
 if(view==='series'){
  records.sort((a,b)=>a.name.localeCompare(b.name));
  $('#result-count').textContent=`${records.length} conference series and coverage leads`;
  $('#results').innerHTML=records.length?`<div class="series-grid">${records.map(s=>{const editions=events.filter(e=>e.series_id===s.id && (e.event_end||e.event_start)>=today());return `<article class="series-card"><h2><a href="${link(s.url)}" target="_blank" rel="noopener">${escape(s.name)} ↗</a></h2><div class="organizer">${escape(s.organizer)}</div>${tags(s)}<p>${escape(s.inclusion_rationale)}</p><span class="badge">${s.review_status==='pending'?'Coverage lead · not yet verified':editions.length?`${editions.length} upcoming edition${editions.length>1?'s':''}`:'No next edition verified'}</span><span class="meta">${escape(s.monitoring)}</span></article>`}).join('')}</div>`:empty(); return;
 }
 records=records.filter(r=>(r.event_end||r.event_start||'9999')>=today());
 const rows=view==='open'?records.flatMap(r=>r.calls.filter(c=>actionable(r,c)).map(c=>({r,c}))):records.map(r=>({r,c:r.calls.find(c=>actionable(r,c))||r.calls[0]||{state:'unknown'}}));
 const sort=$('#sort').value;
 rows.sort((a,b)=>sort==='name'?a.r.name.localeCompare(b.r.name):((sort==='deadline'?a.c.deadline:a.r.event_start)||'9999').localeCompare((sort==='deadline'?b.c.deadline:b.r.event_start)||'9999')||a.r.name.localeCompare(b.r.name));
 $('#result-count').textContent=`${rows.length} ${view==='open'?'open submission opportunities':'upcoming events'} · ${sort==='deadline'?'earliest deadlines first':sort==='event'?'earliest events first':'alphabetical'}`;
 $('#results').innerHTML=rows.length?`<div class="table-wrap"><table><thead><tr><th scope="col">Submission deadline</th><th scope="col">Conference</th><th scope="col">Event dates</th><th scope="col">Location</th><th scope="col">Source</th></tr></thead><tbody>${rows.map(({r,c})=>`<tr><td class="deadline-cell">${deadlineCell(r,c)}</td><td class="event-cell"><a class="event-title" href="${link(r.source_url)}" target="_blank" rel="noopener">${escape(r.name)}</a><div class="organizer">${escape(r.organizers.join(' / '))}</div>${tags(r)}${r.notes||r.calls.length>1?`<details class="notes"><summary>Submission details</summary><p>${escape(r.notes)}${r.calls.length>1?'<br>'+r.calls.map(call=>`${escape(call.kind)}: ${fmt(call.deadline)} (${stateLabel[effectiveState(call)]})`).join('<br>'):''}</p></details>`:''}${r.event_state!=='announced'?`<span class="badge warning">${escape(r.event_state)}</span>`:''}</td><td class="dates-cell">${dates(r)}</td><td class="location-cell">${escape(r.city||'Location unconfirmed')}<span class="meta">${escape(r.country||'')}</span></td><td class="source-cell"><a class="source-link" href="${link(c.source_url||r.source_url)}" target="_blank" rel="noopener">${view==='open'?'View call':'View source'} ↗</a><span class="meta">Verified ${fmt(r.last_verified?.slice(0,10))}</span>${r.health!=='verified'?`<span class="meta warning">${r.health==='fetch_failed'?'Latest fetch failed':'Reverification needed'}</span>`:''}</td></tr>`).join('')}</tbody></table></div>`:empty();
}
function empty(){return `<div class="empty"><h2>No matches here</h2><p>Try a broader topic or region, or check upcoming events for calls that have not opened yet.</p></div>`}
function options(id,values){[...new Set(values.filter(Boolean))].sort().forEach(value=>{const o=document.createElement('option');o.value=value;o.textContent=value;$('#'+id).append(o)})}
async function init(){
 try{
  [events,series,status]=await Promise.all(['conferences','series','run-status'].map(async name=>{const r=await fetch(`data/${name}.json`);if(!r.ok)throw Error('Data unavailable');return r.json()}));
  options('topic',[...events,...series].flatMap(r=>r.topics));options('region',[...events,...series].map(r=>r.region));options('organizer',events.flatMap(r=>r.organizers));
  $('#open-count').textContent=events.flatMap(r=>r.calls.filter(c=>actionable(r,c))).length;
  $('#freshness').textContent=(status.last_run?`Last collection attempt ${fmt(status.last_run.slice(0,10))}. `:'')+status.message;
  $('#source-health').innerHTML=status.sources?.length?`<details><summary>Source check results (${status.sources.length})</summary><table><tbody>${status.sources.map(s=>`<tr><td><a target="_blank" rel="noopener" href="${link(s.url)}">${escape(s.name)}</a></td><td>${escape(s.mode||'')}</td><td>${s.state==='ok'?'Fetched':'Fetch failed'}</td></tr>`).join('')}</tbody></table></details>`:'';
  for(const id of ['search','topic','region','organizer','sort']) $('#'+id).addEventListener(id==='search'?'input':'change',render);
  $('#clear').addEventListener('click',()=>{for(const id of ['search','topic','region','organizer'])$('#'+id).value='';render()});
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.view;document.querySelectorAll('[data-view]').forEach(t=>{t.classList.toggle('active',t===b);t.setAttribute('aria-pressed',String(t===b))});$('#sort').value=view==='open'?'deadline':'event';render()}));
  render();
 }catch(e){$('#result-count').textContent='Unable to load conference data';$('#results').innerHTML='<div class="empty"><h2>The data could not be loaded</h2><p>Please reload the page. <a href="https://github.com/patrickmschneider/macro-conferences/tree/main/data" target="_blank" rel="noopener">Browse the source data</a>.</p></div>';$('#freshness').textContent='Update status unavailable.'}
}
init();
