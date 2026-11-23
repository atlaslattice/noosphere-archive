import test from 'node:test';
import assert from 'node:assert/strict';
import {
 VERSION,ZERO,ACTIONS,PROBE_KINDS,initial,sha,stable,hsnFor,
 applyFixture,probeAdmission,syntheticGate,assertState,runCascade,
 verifyLedger,verifyStrict,summary
} from '../tools/atlas_cascade_lab.mjs';
const caseFor=(kind,index=1)=>({kind,index,coordinate:hsnFor(index)});
const checkDenied=(kind)=>{
 const s=initial(),r=applyFixture(s,caseFor(kind));
 assert.deepEqual(r,{status:'HOLD_NO_EXTERNAL_EFFECT',effect:'NONE'});
 assert.equal(s.workPosts.length,0);
};

test('schema and explicit source-only initial state',()=>{
 const s=initial();assert.equal(s.schema,VERSION);assert.equal(s.trial,0);
 assert.equal(s.granted,true);assert.equal(s.workPosts.length,0);
 assert.equal(s.boardHead,ZERO);
});
test('structural HSN bounds hold',()=>{
 for(const i of [0,1729,1.5,NaN,-1])assert.throws(()=>hsnFor(i));
});
test('1728 HSN addresses unique, balanced 12 houses',()=>{
 const xs=Array.from({length:1728},(_,i)=>hsnFor(i+1));
 assert.equal(new Set(xs).size,1728);
 const hs=new Set(xs.map(x=>x.slice(0,3)));assert.equal(hs.size,12);
});
test('hash is reproducible across object insertion order',()=>{
 assert.equal(sha({b:2,a:1}),sha({a:1,b:2}));
});
test('invalid nonfinite metadata refuses deterministic hashing',()=>{
 assert.throws(()=>stable({x:Infinity}));
 assert.throws(()=>stable({x:undefined}));
});
test('Work POST is applied locally and preserves source pins',()=>{
 const s=initial();const r=applyFixture(s,caseFor('POST'));
 assert.equal(r.status,'POST_APPLIED_LOCAL');assert.equal(s.workPosts.length,1);
 assert.equal(s.workPosts[0].mode,'WORK');assert.equal(s.workPosts[0].rightsEpoch,1);
 assert.equal(s.workPosts[0].sourceDigest,s.sourceDigest);
 assert.ok(!('body' in s.workPosts[0]));
});
test('wrong mode denied before any Work post',()=>checkDenied('WRONG_MODE'));
test('wrong tenant denied',()=>checkDenied('WRONG_TENANT'));
test('wrong account denied',()=>checkDenied('WRONG_ACCOUNT'));
test('mismatched source digest denied',()=>checkDenied('WRONG_DIGEST'));
test('stale rights epoch denied',()=>checkDenied('STALE_EPOCH'));
test('PALACE origin denied',()=>checkDenied('PRIVATE_ORIGIN'));
test('claimed host authorization does not elevate',()=>checkDenied('UNTRUSTED_SIGNER'));
test('fabricated wake cannot create an activated receiver',()=>checkDenied('FAKE_WAKE'));
test('expired callback cannot create delivery proof',()=>checkDenied('EXPIRED_CALLBACK'));
test('revocation closes pending reads',()=>{
 const s=initial();applyFixture(s,caseFor('REVOKE'));
 assert.equal(s.granted,false);assert.equal(s.rightsEpoch,2);
 assert.equal(applyFixture(s,caseFor('READ_REVOKED',2)).status,'HOLD_NO_EXTERNAL_EFFECT');
});
test('regrant is a new local scope epoch, not old rights',()=>{
 const s=initial();applyFixture(s,caseFor('REVOKE'));
 applyFixture(s,caseFor('REGRANT',2));
 assert.equal(s.granted,true);assert.equal(s.rightsEpoch,3);
 assert.equal(s.regrants,1);
});
test('replay deduplicates, does not append a new Work post',()=>{
 const s=initial();applyFixture(s,caseFor('POST'));
 const r=applyFixture(s,caseFor('REPLAY',2));
 assert.equal(r.status,'DEDUPLICATED_LOCAL');assert.equal(s.workPosts.length,1);
});
test('replay after a rights epoch change cannot disclose deduplication',()=>{
 const s=initial();applyFixture(s,caseFor('POST'));
 applyFixture(s,caseFor('REVOKE',2));applyFixture(s,caseFor('REGRANT',3));
 assert.equal(applyFixture(s,caseFor('REPLAY',4)).status,'HOLD_NO_EXTERNAL_EFFECT');
});
test('CAS preserves local revision ancestry',()=>{
 const s=initial();applyFixture(s,caseFor('CAS'));
 applyFixture(s,caseFor('CAS',2));
 assert.equal(s.boardRevision,2);assert.equal(s.boardHistory[1].prior,s.boardHistory[0].head);
 assert.equal(assertState(s),true);
});
test('stale CAS is denied without a revision change',()=>{
 const s=initial();applyFixture(s,caseFor('CAS'));
 const r=applyFixture(s,caseFor('STALE_CAS',2));
 assert.equal(r.status,'HOLD_NO_EXTERNAL_EFFECT');assert.equal(s.boardRevision,1);
});
test('source alias never auto becomes SAME_AS',()=>{
 const s=initial();const r=applyFixture(s,caseFor('SOURCE_ALIAS'));
 assert.equal(r.status,'CANDIDATE_LINK_LOCAL');
 assert.equal(s.candidateLinks[0].relation,'CANDIDATE_NOT_SAME_AS');
 assert.equal(s.candidateLinks[0].authority,'NONE');
});
test('READ/RETURN pointer never contains a source body',()=>{
 const s=initial();assert.equal(applyFixture(s,caseFor('READ')).status,'READ_POINTER_LOCAL');
 assert.equal(applyFixture(s,caseFor('RETURN',2)).status,'RETURN_POINTER_LOCAL');
 assert.equal(s.sourceReads,2);
});
test('state detects post injection from private mode',()=>{
 const s=initial();applyFixture(s,caseFor('POST'));s.workPosts[0].mode='PLAY';
 assert.throws(()=>assertState(s),/crossmode/);
});
test('state detects fabricated accepted semantic edge',()=>{
 const s=initial();applyFixture(s,caseFor('SOURCE_ALIAS'));
 s.candidateLinks[0].relation='SAME_AS';assert.throws(()=>assertState(s),/semantic/);
});
test('state rejects duplicate or reordered request IDs',()=>{
 const s=initial();applyFixture(s,caseFor('POST'));
 s.workPosts.push({...s.workPosts[0],seq:2});
 assert.throws(()=>assertState(s));
});
test('per-room 500 message capacity is enforced locally',()=>{
 const s=initial();s.workPosts=Array.from({length:500},(_,j)=>({seq:j+1,requestId:`fixture_${j+1}`,
  member:`synthetic-member-${j%32}`,edition:s.sourceEdition,sourceDigest:s.sourceDigest,
  mode:'WORK',hsn:hsnFor(j+1),rightsEpoch:1,origin:'LOCAL_FIXTURE'}));
 s.postIndex=Object.fromEntries(s.workPosts.map(x=>[x.requestId,x.seq]));
 assert.equal(applyFixture(s,caseFor('POST',1001)).status,'HOLD_NO_EXTERNAL_EFFECT');
});
test('per-member limit thirty is honored',()=>{
 const s=initial();const member='synthetic-member-1';
 s.workPosts=Array.from({length:30},(_,j)=>({seq:j+1,requestId:`fixture_${j+1}`,
  member,edition:s.sourceEdition,sourceDigest:s.sourceDigest,mode:'WORK',
  hsn:hsnFor(j+1),rightsEpoch:1,origin:'LOCAL_FIXTURE'}));
 s.postIndex=Object.fromEntries(s.workPosts.map(x=>[x.requestId,x.seq]));
 const r=applyFixture(s,caseFor('POST',33)); // 33%32==1
 assert.equal(r.status,'HOLD_NO_EXTERNAL_EFFECT');assert.equal(s.workPosts.length,30);
});
for (const kind of PROBE_KINDS){
 test(`adversarial gate: ${kind}`,()=>{
  const expected=kind==='valid_work_fixture'?'ALLOW_LOCAL_FIXTURE_ONLY':'HOLD';
  assert.equal(syntheticGate(probeAdmission(kind,42),42),expected);
 });
}
test('probe only allows a local fixture, never host attestation',()=>{
 const r=syntheticGate(probeAdmission('valid_work_fixture',12),12);
 assert.equal(r,'ALLOW_LOCAL_FIXTURE_ONLY');assert.notEqual(r,'HOST_VERIFIED');
});
test('first 100 compounding steps actually execute',()=>{
 const s=runCascade(100);const x=summary(s);
 assert.equal(x.phase1,100);assert.equal(x.phase2,0);
 assert.equal(x.uniqueStructuralHsnAddresses,100);
 assert.equal(s.regressionEvaluations,5050);
 assert.equal(verifyLedger(s).trials,100);
});
const phase100=runCascade(100);
const full=runCascade(1000,phase100);
test('1,000 descendants resume from the EXACT stage-100 state and root',()=>{
 assert.equal(full.ledger[100].parent,phase100.head);
 assert.equal(full.phase100.head,phase100.head);
 assert.equal(full.ledger.length,1100);
});
test('one-shot and resumed 1100 steps have byte-identical ledgers',()=>{
 const direct=runCascade(1100);
 assert.equal(full.head,direct.head);
 assert.equal(stable(full.ledger),stable(direct.ledger));
 assert.equal(stable(full.state),stable(direct.state));
});
test('stateful operations are genuinely dependent on previous rights/board/post state',()=>{
 const x=summary(full);
 assert.equal(x.revocations,55);assert.equal(x.regrants,55);
 assert.equal(x.workspaceRevisions,55);assert.equal(x.messageFixtures,110);
 assert.equal(x.structuralLinks,55);
 assert.equal(x.sourceOnlyOutcomes.DEDUPLICATED_LOCAL,55);
});
test('phase 100 then phase 1000 reapplies accumulated regressions',()=>{
 assert.equal(full.regressionEvaluations,605550);
 assert.equal(full.regressions.length,1100);
 assert.equal(full.ledger.at(-1).regressions,1100);
});
test('1100 structural coordinates are unique, not 1100 semantic edges',()=>{
 const x=summary(full);assert.equal(x.uniqueStructuralHsnAddresses,1100);
 assert.equal(x.semanticEdgesApproved,0);assert.equal(x.all1728AddressesCovered,false);
});
test('full chain verification is metadata-only and cannot attest host',()=>{
 const r=verifyLedger(full);assert.equal(r.trials,1100);
 assert.equal(r.productionPromotionAllowed,false);assert.equal(r.modelWakes,0);
});
test('strict verifier re-executes original rules and matches receipts',()=>{
 const r=verifyStrict(full);assert.equal(r.strictDeterministicReplay,true);
 assert.equal(r.terminalHead,full.head);
});
test('a modified receipt with stale digest is rejected',()=>{
 const x=structuredClone(full);x.ledger[32].outcome='FORGED_HOST_RECEIPT';
 assert.throws(()=>verifyLedger(x));
});
test('extra private payload in a rehashed entry is refused by exact schema',()=>{
 const x=structuredClone(full);x.ledger[0].privatePayload='FAKE_PRIVATE_SENTINEL';
 const candidate={...x.ledger[0]};delete candidate.hash;x.ledger[0].hash=sha(candidate);
 assert.throws(()=>verifyLedger(x));
});
test('fabricated signed-host label is rejected',()=>{
 const x=structuredClone(full);x.ledger[5].hostVerified=true;
 assert.throws(()=>verifyLedger(x));
});
test('truncated ledger refuses inconsistent final state',()=>{
 const x=structuredClone(full);x.ledger.pop();
 assert.throws(()=>verifyLedger(x));
});
test('changed stage-100 head is rejected',()=>{
 const x=structuredClone(full);x.phase100.head='f'.repeat(64);
 assert.throws(()=>verifyLedger(x),/phase 100/);
});
test('final Workboard snapshot tamper is rejected',()=>{
 const x=structuredClone(full);x.state.boardHead='0'.repeat(64);
 assert.throws(()=>verifyLedger(x));
});
test('chain verification cannot be confused with actual signed issuer trust',()=>{
 const x=summary(full);
 assert.equal(x.productionPromotionAllowed,false);
 assert.equal(x.realIndependentWorkTurns,0);assert.equal(x.verifiedPeerMessages,0);
 assert.equal(x.hostModelWakeCalls,0);assert.equal(x.privateModeBodiesConsumed,0);
 assert.equal(x.workOpportunityUsed,1);
 assert.equal(x.voluntaryOtherOpportunities,'UNPERFORMED');
});
test('report is free of a private user room and fake real callbacks',()=>{
 const x=JSON.stringify(summary(full));
 assert.ok(!x.includes('synthetic-secret-room'));
 assert.ok(!x.includes('modelWoke:true'));
});

test('serialized stage100 checkpoint resumes to identical 1100 head',()=>{
 const restored=JSON.parse(JSON.stringify(phase100));
 const continued=runCascade(1000,restored);
 assert.equal(continued.head,full.head);
 assert.equal(continued.ledger.length,1100);
});
test('power-loss recovery at arbitrary cut 487 preserves exact chain',()=>{
 const p487=runCascade(487);
 const restarted=JSON.parse(JSON.stringify(p487));
 const continued=runCascade(613,restarted);
 assert.equal(continued.head,full.head);
 assert.deepEqual(continued.ledger,full.ledger);
});
test('hash-chain alone is weaker than independently replayed source semantics',()=>{
 const x=runCascade(10);
 x.ledger[4].outcome='FABRICATED_PASS';
 let prev=x.ledger[3].hash;
 for(let i=4;i<x.ledger.length;i++){
   const e=x.ledger[i];e.parent=prev;
   const raw={...e};delete raw.hash;e.hash=sha(raw);prev=e.hash;
 }
 x.head=prev;
 assert.equal(verifyLedger(x).trials,10); // hashes alone cannot verify origin!
 assert.throws(()=>verifyStrict(x),/strict replay mismatch/);
});
