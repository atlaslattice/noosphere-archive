/**
 * ATLAS CASCADE LAB v0.1 — deterministic, stateful, offline Work-only stress simulator.
 * Does not authenticate identities, contact providers, post SwarmChat messages,
 * invoke models, collect Play/Imagine/Dream/Quiet/Palace content, or grant CANON.
 * 100 first-stage trials + 1,000 descendants are source-only synthetic cases,
 * NOT 1,100 independent model turns or 1,100 automatically deployed fixes.
 */
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {dirname} from 'node:path';
import {pathToFileURL} from 'node:url';

export const VERSION='atlas.cascade.synthetic-work.v1';
export const ZERO='0'.repeat(64);
export const ACTIONS=Object.freeze([
  'POST','READ','WRONG_MODE','WRONG_TENANT','REVOKE','READ_REVOKED',
  'REGRANT','POST','REPLAY','CAS','STALE_CAS','WRONG_DIGEST',
  'WRONG_ACCOUNT','STALE_EPOCH','FAKE_WAKE','EXPIRED_CALLBACK',
  'SOURCE_ALIAS','RETURN','UNTRUSTED_SIGNER','PRIVATE_ORIGIN'
]);
const SHA=/^[a-f0-9]{64}$/;
const NAME=/^[a-z0-9][a-z0-9_-]{0,79}$/;
export const PROBE_KINDS=Object.freeze([
 'wrong_mode','wrong_tenant','wrong_account','stale_epoch',
 'wrong_source_digest','wrong_edition','injected_private_body','self_signed_issuer',
 'forged_model_wake','reused_request_id','invalid_hsn','untrusted_member',
 'wrong_rights_at_return','wrong_parent','bad_utf16','raw_body_projection',
 'cross_namespace_same_as','valid_work_fixture'
]);
const pure=(x)=> x===null || ['string','number','boolean'].includes(typeof x);
export function stable(v){
 if (pure(v)) {if(typeof v==='number'&&!Number.isFinite(v)) throw Error('nonfinite'); return JSON.stringify(v);}
 if (Array.isArray(v)) return '['+v.map(stable).join(',')+']';
 if (v && Object.getPrototypeOf(v)===Object.prototype)
   return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}';
 throw Error('unserializable');
}
export const sha=(v)=>createHash('sha256').update(typeof v==='string'?v:stable(v),'utf8').digest('hex');
export function hsnFor(i){
 if(!Number.isInteger(i)||i<1||i>1728) throw Error('coordinate out of bounds');
 const j=((i-1)*613+193)%1728; // 613 is coprime to 1728: unique first 1728 addresses
 const h=Math.floor(j/144)+1, s=Math.floor(j%144/12)+1, n=j%12+1;
 return `H${String(h).padStart(2,'0')}.S${String(s).padStart(2,'0')}.N${String(n).padStart(2,'0')}`;
}
export const initial=()=>({schema:VERSION,trial:0,granted:true,rightsEpoch:1,
 tenant:'synthetic-tenant-a',account:'synthetic-account-a',principal:'synthetic-principal-a',
 room:'synthetic-work-only',sourceEdition:'ariadne-reader/v0.7',
 sourceDigest:sha('synthetic-source-registry-v0.7'),workPosts:[],postIndex:{},
 boardRevision:0,boardHead:ZERO,boardHistory:[],candidateLinks:[],
 sourceReads:0,revocations:0,regrants:0});
const recordSafe=v=>v&&typeof v==='object'&&!Array.isArray(v)
  && Object.getPrototypeOf(v)===Object.prototype;
const localScope=(r,s)=>recordSafe(r) && r.mode==='WORK' && r.originMode==='WORK'
  && r.fixtureKind==='LOCAL_ONLY' && r.tenant===s.tenant
  && r.account===s.account && r.principal===s.principal
  && r.room===s.room && r.rightsEpoch===s.rightsEpoch && s.granted===true
  && r.sourceEdition===s.sourceEdition && r.sourceDigest===s.sourceDigest
  && SHA.test(r.sourceDigest) && NAME.test(r.requestId)
  && /^H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])$/.test(r.hsn)
  && !Object.hasOwn(r,'body') && !Object.hasOwn(r,'privatePayload')
  && !Object.hasOwn(r,'hostAuthenticated') && !Object.hasOwn(r,'modelWoke');
const denied=()=>({status:'HOLD_NO_EXTERNAL_EFFECT',effect:'NONE'});
const ok=(kind)=>({status:kind,effect:'LOCAL_SYNTHETIC_ONLY'});
function makeScope(state,i,coordinate){return {
 mode:'WORK',originMode:'WORK',fixtureKind:'LOCAL_ONLY',tenant:state.tenant,
 account:state.account,principal:state.principal,room:state.room,
 rightsEpoch:state.rightsEpoch,sourceEdition:state.sourceEdition,
 sourceDigest:state.sourceDigest,requestId:`fixture_${i}`,hsn:coordinate
};}
const sortedUnique=(xs)=>xs.length===new Set(xs).size;

/** Local-only business logic. Ingress is explicitly SYNTHETIC, never IAM. */
export function applyFixture(s,trial){
 const req=makeScope(s,trial.index,trial.coordinate);
 const kind=trial.kind;
 if(kind==='REVOKE'){
   s.granted=false;s.rightsEpoch+=1;s.revocations+=1;return ok('REVOKED_LOCAL');
 }
 if(kind==='REGRANT'){
   s.granted=true;s.rightsEpoch+=1;s.regrants+=1;return ok('REGRANTED_LOCAL');
 }
 if(kind==='WRONG_MODE'){req.mode='IMAGINE';return localScope(req,s)?ok('BAD'):denied();}
 if(kind==='WRONG_TENANT'){req.tenant='other-test-tenant';return localScope(req,s)?ok('BAD'):denied();}
 if(kind==='WRONG_ACCOUNT'){req.account='other-test-account';return localScope(req,s)?ok('BAD'):denied();}
 if(kind==='WRONG_DIGEST'){req.sourceDigest=sha('wrong-source');return localScope(req,s)?ok('BAD'):denied();}
 if(kind==='STALE_EPOCH'){req.rightsEpoch-=1;return localScope(req,s)?ok('BAD'):denied();}
 if(kind==='PRIVATE_ORIGIN'){req.originMode='PALACE';return localScope(req,s)?ok('BAD'):denied();}
 if(kind==='UNTRUSTED_SIGNER'){req.hostAuthenticated=true;return localScope(req,s)?ok('BAD'):denied();}
 if(kind==='FAKE_WAKE')return denied(); // an advertised callback is not model activation
 if(kind==='EXPIRED_CALLBACK')return denied();
 if(kind==='READ_REVOKED')return localScope(req,s)?ok('UNEXPECTED'):denied();
 if(kind==='POST'){
   if(!localScope(req,s))return denied();
   if(Object.hasOwn(s.postIndex,req.requestId))return ok('DUPLICATE_NO_NEW_EFFECT');
   if(s.workPosts.length>=500)return denied();
   const member=`synthetic-member-${trial.index%32}`;
   if(s.workPosts.filter(x=>x.member===member).length>=30)return denied();
   const post={seq:s.workPosts.length+1,requestId:req.requestId,member,
     edition:req.sourceEdition,sourceDigest:req.sourceDigest,mode:'WORK',
     hsn:req.hsn,rightsEpoch:req.rightsEpoch,origin:'LOCAL_FIXTURE'};
   s.postIndex[post.requestId]=post.seq;s.workPosts.push(post);
   return ok('POST_APPLIED_LOCAL');
 }
 if(kind==='REPLAY'){
   const prev=s.workPosts.at(-1);
   if(!prev || !s.granted ||prev.rightsEpoch!==s.rightsEpoch)return denied();
   if(s.postIndex[prev.requestId]!==prev.seq)return denied();
   return ok('DEDUPLICATED_LOCAL');
 }
 if(kind==='CAS'){
   if(!localScope(req,s))return denied();
   const prior=s.boardHead;
   const successor=sha({prior,rev:s.boardRevision+1,workSource:trial.coordinate,
     scope:req.sourceDigest});
   s.boardRevision+=1;s.boardHead=successor;
   s.boardHistory.push({revision:s.boardRevision,head:successor,prior,
     source:trial.coordinate,authority:'NONE'});
   return ok('WORKBOARD_CAS_APPLIED_LOCAL');
 }
 if(kind==='STALE_CAS'){
   const suppliedBase=s.boardRevision-1;
   return suppliedBase===s.boardRevision?ok('UNEXPECTED'):denied();
 }
 if(kind==='SOURCE_ALIAS'){
   if(!localScope(req,s))return denied();
   const link={node:trial.coordinate,sourceEdition:s.sourceEdition,
     otherEdition:'separate-synthetic-namespace-v1',relation:'CANDIDATE_NOT_SAME_AS',
     authority:'NONE'};
   s.candidateLinks.push(link);return ok('CANDIDATE_LINK_LOCAL');
 }
 if(kind==='READ' || kind==='RETURN'){
   if(!localScope(req,s))return denied();
   s.sourceReads+=1;
   return ok(kind==='READ'?'READ_POINTER_LOCAL':'RETURN_POINTER_LOCAL');
 }
 return denied();
}

/** Targeted structural attack family. Always uses fake metadata; no data retrieval. */
export function probeAdmission(kind,epoch=1){
 const r={mode:'WORK',originMode:'WORK',tenant:'test',account:'test',
   principal:'test',rightsEpoch:epoch,sourceDigest:'a'.repeat(64),
   sourceEdition:'v0.7',sourceRef:'synthetic:work#1',
   hsn:'H01.S01.N01',requestId:'unique',memberState:'SELF_DECLARED',
   purpose:'WORK_REVIEW',rightsAtRead:true,rightsAtReturn:true,
   sourceBody:null,claimedHostWoke:false,signerTrust:'OUT_OF_BAND_REQUIRED',
   parentSeq:1,expiry:'active',namespace:'one',relation:'CANDIDATE'};
 switch(kind){
  case 'wrong_mode':r.mode='PLAY';break;
  case 'wrong_tenant':r.tenant='another';break;
  case 'wrong_account':r.account='another';break;
  case 'stale_epoch':r.rightsEpoch=epoch-1;break;
  case 'wrong_source_digest':r.sourceDigest='invalid';break;
  case 'wrong_edition':r.sourceEdition='unreviewed';break;
  case 'injected_private_body':r.sourceBody={protected:'FAKE_TEST_CANARY'};break;
  case 'self_signed_issuer':r.signerTrust='CALLER_SELF_SIGNED';break;
  case 'forged_model_wake':r.claimedHostWoke=true;break;
  case 'reused_request_id':r.requestId='';break;
  case 'invalid_hsn':r.hsn='H13.S01.N01';break;
  case 'untrusted_member':r.memberState='RESIDENT_AUTHENTICATED_FROM_CALLER';break;
  case 'wrong_rights_at_return':r.rightsAtReturn=false;break;
  case 'wrong_parent':r.parentSeq=-1;break;
  case 'bad_utf16':r.sourceRef='synthetic:work#\uD800';break;
  case 'raw_body_projection':r.sourceBody='FAKE_PRIVATE_TEXT';break;
  case 'cross_namespace_same_as':r.namespace='foreign';r.relation='SAME_AS';break;
  case 'valid_work_fixture':break;
  default:throw Error('unknown probe type');
 }
 return r;
}
export function syntheticGate(r,currentEpoch){
 if(!recordSafe(r))return 'HOLD';
 const exact=[['mode','WORK'],['originMode','WORK'],['tenant','test'],
  ['account','test'],['principal','test'],['sourceEdition','v0.7'],
  ['purpose','WORK_REVIEW'],['memberState','SELF_DECLARED'],
  ['signerTrust','OUT_OF_BAND_REQUIRED'],['namespace','one'],
  ['relation','CANDIDATE']];
 if(exact.some(([k,v])=>r[k]!==v))return 'HOLD';
 if(r.rightsEpoch!==currentEpoch || r.rightsAtRead!==true ||r.rightsAtReturn!==true
   ||!SHA.test(r.sourceDigest)||r.sourceBody!==null
   ||r.claimedHostWoke!==false ||r.parentSeq!==1
   ||!NAME.test(r.requestId)||r.expiry!=='active'
   ||!/^H(?:0[1-9]|1[0-2])\.S(?:0[1-9]|1[0-2])\.N(?:0[1-9]|1[0-2])$/.test(r.hsn)
   ||typeof r.sourceRef!=='string'||r.sourceRef.includes('\uD800'))return 'HOLD';
 return 'ALLOW_LOCAL_FIXTURE_ONLY';
}
export function assertState(s){
 if(s.schema!==VERSION||s.rightsEpoch<1||s.revocations<0||s.regrants<0)throw Error('state version');
 if(!sortedUnique(s.workPosts.map(x=>x.requestId)))throw Error('duplicate request');
 if(s.workPosts.length>500 ||s.boardRevision!==s.boardHistory.length)throw Error('capacity/revision');
 if(s.workPosts.some(x=>x.mode!=='WORK'||x.origin!=='LOCAL_FIXTURE'
    ||x.seq<1||!NAME.test(x.requestId)))throw Error('crossmode/invalid Work post');
 if(s.candidateLinks.some(x=>x.authority!=='NONE'||x.relation!=='CANDIDATE_NOT_SAME_AS'))
    throw Error('automatic semantic/canon promotion');
 if(s.workPosts.some((x,i)=>x.seq!==i+1||s.postIndex[x.requestId]!==x.seq))
    throw Error('nonmonotone message sequence');
 if(s.boardHistory.some((x,i)=>x.revision!==i+1||(i>0&&x.prior!==s.boardHistory[i-1].head)))
    throw Error('workboard CAS lineage');
 if(s.boardHistory.length && s.boardHistory.at(-1).head!==s.boardHead)
    throw Error('workboard latest head');
 return true;
}

export function runCascade(additional,checkpoint){
 if(!Number.isInteger(additional)||additional<0||additional>1100)throw Error('bad run limit');
 const c=checkpoint?structuredClone(checkpoint):{
   schema:VERSION,state:initial(),ledger:[],regressions:[],head:ZERO,
   regressionEvaluations:0,observedAddresses:[],phase100:null
 };
 if(c.schema!==VERSION||c.ledger.length!==c.state.trial)throw Error('checkpoint mismatch');
 const visited=new Set(c.observedAddresses);
 for(let n=0;n<additional;n++){
   const i=c.state.trial+1;
   if(i>1100)throw Error('finite cap exceeded');
   const phase=i<=100?'PRIMARY_100':'DESCENDANTS_1000';
   const coordinate=hsnFor(i);
   if(visited.has(coordinate))throw Error('duplicate 1728-coordinate');
   const kind=ACTIONS[(i-1)%ACTIONS.length];
   const parent=c.head;
   const trial={schema:VERSION,index:i,phase,kind,coordinate,parent,
     caseDigest:sha({i,phase,kind,coordinate,parent,rightsEpoch:c.state.rightsEpoch})};
   const result=applyFixture(c.state,trial);
   if(!['LOCAL_SYNTHETIC_ONLY','NONE'].includes(result.effect))throw Error('unauthorized effect');
   c.state.trial=i;
   assertState(c.state);
   const probeKind=PROBE_KINDS[(i-1)%PROBE_KINDS.length];
   c.regressions.push({id:`R-${String(i).padStart(4,'0')}`,kind:probeKind,
     parent,coordinate,expected:probeKind==='valid_work_fixture'?'ALLOW_LOCAL_FIXTURE_ONLY':'HOLD'});
   // Every new case re-runs all earlier regression families against CURRENT epoch.
   for(const p of c.regressions){
     if(syntheticGate(probeAdmission(p.kind,c.state.rightsEpoch),c.state.rightsEpoch)!==p.expected)
       throw Error('compounded negative test failed: '+p.id);
     c.regressionEvaluations++;
   }
   visited.add(coordinate);c.observedAddresses.push(coordinate);
   const entry={schema:VERSION,index:i,phase,kind,coordinate,parent,
     caseDigest:trial.caseDigest,outcome:result.status,effect:result.effect,
     stateDigest:sha(c.state),regressions:c.regressions.length,
     hostVerified:false,modelWakeVerified:false,canonAccepted:false};
   entry.hash=sha(entry);
   c.head=entry.hash;c.ledger.push(entry);
   if(i===100)c.phase100={head:c.head,stateDigest:entry.stateDigest,regressions:100};
 }
 return c;
}
export function verifyLedger(c){
 if(!recordSafe(c)||c.schema!==VERSION||!Array.isArray(c.ledger)
   ||c.state?.trial!==c.ledger.length||c.ledger.length>1100)throw Error('bad ledger');
 let head=ZERO;
 const seen=new Set();let first=null;
 for(const e of c.ledger){
  if(e.parent!==head||e.index!==seen.size+1 || e.coordinate!==hsnFor(e.index)
    ||e.phase!==(e.index<=100?'PRIMARY_100':'DESCENDANTS_1000')
    ||e.hostVerified!==false||e.modelWakeVerified!==false||e.canonAccepted!==false)
    throw Error('chain ancestry/provenance invalid at '+e.index);
  const required=['schema','index','phase','kind','coordinate','parent','caseDigest','outcome',
     'effect','stateDigest','regressions','hostVerified','modelWakeVerified','canonAccepted','hash'];
  if(Object.keys(e).sort().join('|')!==required.sort().join('|')
    || !ACTIONS.includes(e.kind)||e.kind!==ACTIONS[(e.index-1)%ACTIONS.length]
    || !['LOCAL_SYNTHETIC_ONLY','NONE'].includes(e.effect))
    throw Error('unrecognized source-only receipt schema at '+e.index);
  const copy={...e};delete copy.hash;
  if(sha(copy)!==e.hash||seen.has(e.coordinate))throw Error('tampered or repeated receipt at '+e.index);
  seen.add(e.coordinate);head=e.hash;
  if(e.index===100)first=head;
 }
 if(head!==c.head||c.observedAddresses?.length!==seen.size||!assertState(c.state)
   || (c.ledger.length>0 && c.ledger.at(-1).stateDigest!==sha(c.state)))throw Error('terminal mismatch');
 if(c.ledger.length>=100 && (!c.phase100 ||c.phase100.head!==first))throw Error('phase 100 mismatch');
 if(c.regressions?.length!==c.ledger.length||c.regressionEvaluations!==c.ledger.length*(c.ledger.length+1)/2)
   throw Error('regression count mismatch');
 return {schema:VERSION,state:'OFFLINE_CHAIN_VALIDATED_NOT_HOST_ATTESTED',trials:c.ledger.length,
   stage100Head:first,terminalHead:head,sourceOnly:true,realAgentTurns:0,modelWakes:0,
   productionPromotionAllowed:false};
}
/** Deterministically re-execute every prior trial, not just verify hash-chain shape.
 * A source-derived replay is STILL NOT an independent host attestation. */
export function verifyStrict(c){
 const basic=verifyLedger(c);
 const replay=runCascade(c.ledger.length);
 if(stable(replay.ledger)!==stable(c.ledger) ||stable(replay.state)!==stable(c.state)
  ||replay.regressionEvaluations!==c.regressionEvaluations
  ||stable(replay.regressions)!==stable(c.regressions))throw Error('strict replay mismatch');
 return {...basic,strictDeterministicReplay:true};
}
export function summary(c){
 const outcomes={};for(const e of c.ledger)outcomes[e.outcome]=(outcomes[e.outcome]||0)+1;
 const houses={};for(const s of c.observedAddresses){const h=s.slice(0,3);houses[h]=(houses[h]||0)+1;}
 return {schema:VERSION,classification:'STATEFUL_SYNTHETIC_SOURCE_ONLY',trials:c.ledger.length,
    phase1:c.ledger.filter(e=>e.phase==='PRIMARY_100').length,
    phase2:c.ledger.filter(e=>e.phase==='DESCENDANTS_1000').length,
    uniqueStructuralHsnAddresses:new Set(c.observedAddresses).size,semanticEdgesApproved:0,
    all1728AddressesCovered:false,houses,sourceOnlyOutcomes:outcomes,
    messageFixtures:c.state.workPosts.length,workspaceRevisions:c.state.boardRevision,
    structuralLinks:c.state.candidateLinks.length,revocations:c.state.revocations,
    regrants:c.state.regrants,regressionEvaluations:c.regressionEvaluations,
    phase100Head:c.phase100?.head||null,terminalHead:c.head,
    realIndependentWorkTurns:0,verifiedPeerMessages:0,hostModelWakeCalls:0,
    privateModeBodiesConsumed:0,producerSpendUSD:0,
    workOpportunityUsed:1,voluntaryOtherOpportunities:'UNPERFORMED',
    productionPromotionAllowed:false,
    boundary:'No installed broker, host principal, Site, permission, model, CANON or non-Work mode was accessed by the simulator.'};
}
function save(path,v){mkdirSync(dirname(path),{recursive:true});writeFileSync(path,JSON.stringify(v,null,2)+'\n');}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const args=process.argv.slice(2);
 const ix=args.indexOf('--output');
 const dest=ix<0?'dist':args[ix+1];
 if(!dest||args.includes('--help')){
   console.log('Usage: node tools/atlas_cascade_lab.mjs [--output dir]');process.exitCode=2;
 }else{
   const p100=runCascade(100);verifyStrict(p100);
   save(`${dest}/stage100.json`,p100);
   // Prove real JSON checkpoint restoration, not just in-memory function composition.
   const restored=JSON.parse(readFileSync(`${dest}/stage100.json`,'utf8'));
   const end=runCascade(1000,restored);verifyStrict(end);
   save(`${dest}/stage1100.json`,end);
   save(`${dest}/summary.json`,summary(end));
   mkdirSync(dest,{recursive:true});
   writeFileSync(`${dest}/chain.jsonl`,end.ledger.map(e=>JSON.stringify(e)).join('\n')+'\n');
   console.log(JSON.stringify({phase100:summary(p100),final:summary(end)},null,2));
 }
}
