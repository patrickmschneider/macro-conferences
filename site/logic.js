export const day = d => new Date(d+'T12:00:00Z');
export const today = () => new Date().toISOString().slice(0,10);
export function effectiveState(call,now=new Date()) {
 if (call.state==='withdrawn') return 'withdrawn';
 if(call.deadline && call.deadline_time && call.deadline_timezone){
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:call.deadline_timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).map(p=>[p.type,p.value]));
  const local=`${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
  if(local>`${call.deadline}T${call.deadline_time}`) return 'closed';
 } else if (call.deadline && call.deadline < now.toISOString().slice(0,10)) return 'closed';
 return call.state;
}
export function actionable(event,call,now=new Date()){
 const age=(now-new Date(event.last_verified))/86400000;
 return effectiveState(call,now)==='open' && !!call.deadline && event.health!=='needs_verification' && event.event_state==='announced' && age<=14;
}
export function filtered(items,{search='',topic='',region='',organizer=''}={}){
 const words=search.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
 return items.filter(r=>words.every(w=>[r.name,...r.topics,...(r.organizers||[r.organizer]),r.city||'',r.country||''].join(' ').toLocaleLowerCase().includes(w)) && (!topic||r.topics.includes(topic)) && (!region||r.region===region) && (!organizer||(r.organizers||[r.organizer]).includes(organizer)));
}
