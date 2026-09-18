import test from 'node:test';import assert from 'node:assert/strict';
import {effectiveState,actionable,filtered} from '../site/logic.js';
test('exact cutoffs respect source timezone',()=>{const c={state:'open',deadline:'2026-10-08',deadline_time:'23:59',deadline_timezone:'America/New_York'};assert.equal(effectiveState(c,new Date('2026-10-09T03:58:00Z')),'open');});
test('missing deadlines and stale facts are not actionable',()=>{assert.equal(actionable({last_verified:'2026-08-01',health:'verified',event_state:'announced'},{state:'open',deadline:'2026-10-01'},new Date('2026-09-18')),false);});
test('multi-word search and topic intersection',()=>{const r={name:'Household finance meeting',organizers:['NBER'],topics:['Household finance'],region:'North America'};assert.equal(filtered([r],{search:'nber household',topic:'Household finance'}).length,1);assert.equal(filtered([r],{topic:'Growth'}).length,0);});

test('cutoff closes once local deadline passes',()=>{assert.equal(effectiveState({state:'open',deadline:'2026-10-08',deadline_time:'23:59',deadline_timezone:'America/New_York'},new Date('2026-10-09T04:01:00Z')),'closed')});
