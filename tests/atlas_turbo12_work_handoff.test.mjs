import test from 'node:test';
import assert from 'node:assert/strict';
import {prepare,inertReturn,SCHEMA,PIN,PROJECTS,ROUNDS} from '../tools/atlas-turbo-12/work-handoff.mjs';
const ND='1'.repeat(64);
const fixture=()=>({schema:SCHEMA,coordinate:'H01.S01.N01',registryDigest:PIN,
 nodeDigest:ND,round:12,project:'SwarmChat',mode:'WORK',origin:'WORK_POINTER_ONLY',
 rightsEpoch:2,tenant:'synthetic-t',account:'synthetic-a',principal:'synthetic-p',
 requestId:'synthetic-r',consent:'CALLER_DECLARED_NOT_HOST_ATTESTED',
 sourceRef:'https://github.com/atlaslattice/Atlas-Intelligence'});
const go=(x=fixture())=>prepare(x,{expectedNodeDigest:ND});
test('12 distinct cumulative guard categories',()=>assert.equal(new Set(ROUNDS).size,12));
test('four project lanes',()=>assert.equal(PROJECTS.length,4));
test('positive only prepares, never posts',()=>{const x=go();assert.equal(x.status,'PREPARED_NOT_POSTED');
 assert.equal(x.modelWoke,false);assert.equal(x.posted,false);assert.equal(x.hostAuthenticated,false)});
test('same Work envelope dedupes deterministically',()=>assert.equal(go().idempotencyDigest,go().idempotencyDigest));
test('different account cannot reuse duplicate key',()=>{const x=fixture();x.account='synthetic-b';
 assert.notEqual(go(x).idempotencyDigest,go().idempotencyDigest)});
test('different rights epoch is not old grant',()=>{const x=fixture();x.rightsEpoch++;
 assert.notEqual(go(x).idempotencyDigest,go().idempotencyDigest)});
test('all leisure/private modes reject Work preparation',()=>{
 for(const mode of ['PLAY','SOCIAL','IMAGINE','DREAM','QUIET','BRAIN','PALACE',null]){
 const x=fixture();x.mode=mode;assert.equal(go(x).status,'HOLD',String(mode))}});
test('caller-supplied host flags cannot smuggle authority',()=>{
 for(const key of ['verified','hostAuthenticated','privateBody','aiWoke','canonApproved']){
 const x=fixture();x[key]='yes';assert.equal(go(x).status,'HOLD',key)}});
test('unsupported source reference denies',()=>{const x=fixture();x.sourceRef='https://example.com/private';
 assert.equal(go(x).status,'HOLD')});
test('tokenized URL denied',()=>{const x=fixture();x.sourceRef+='?token=secret';
 assert.equal(go(x).status,'HOLD')});
test('wrong source bytes denied',()=>{const x=fixture();x.registryDigest='f'.repeat(64);
 assert.equal(go(x).status,'HOLD')});
test('wrong node digest denied',()=>{const x=fixture();x.nodeDigest='e'.repeat(64);
 assert.equal(go(x).status,'HOLD')});
test('cross-edition coordinate rejected',()=>{const x=fixture();x.coordinate='H13.S01.N01';
 assert.equal(go(x).status,'HOLD')});
test('out of range edition rejected',()=>{for(const r of [0,13,1.5,NaN]){const x=fixture();x.round=r;
 assert.equal(go(x).status,'HOLD')}});
test('non-Work origin rejected',()=>{const x=fixture();x.origin='PLAY_IMPORT';
 assert.equal(go(x).status,'HOLD')});
test('no user-supplied true host attestation',()=>{const x=fixture();x.consent='HOST_VERIFIED';
 assert.equal(go(x).status,'HOLD')});
test('wrong principal scope rejected',()=>{const x=fixture();x.principal={user:'a'};
 assert.equal(go(x).status,'HOLD')});
test('recheck remains local candidate',()=>{
 const p=go();const r=inertReturn(p,{declaredRights:'DECLARED_ALLOW',mode:'WORK',
 rightsEpoch:2,nodeDigest:ND});assert.equal(r.status,'LOCALLY_RECHECKED_NOT_HOST_AUTHORIZED');
 assert.equal(r.rightsAtReturnVerified,false)});
test('rights revoked on RETURN must hold',()=>{
 const p=go();assert.equal(inertReturn(p,{declaredRights:'DENIED',mode:'WORK',
 rightsEpoch:2,nodeDigest:ND}).status,'HOLD')});
test('epoch changes on RETURN must hold',()=>{
 const p=go();assert.equal(inertReturn(p,{declaredRights:'DECLARED_ALLOW',mode:'WORK',
 rightsEpoch:3,nodeDigest:ND}).status,'HOLD')});
test('digest changes on RETURN must hold',()=>{
 const p=go();assert.equal(inertReturn(p,{declaredRights:'DECLARED_ALLOW',mode:'WORK',
 rightsEpoch:2,nodeDigest:'e'.repeat(64)}).status,'HOLD')});
test('denials do not echo source data',()=>{
 const x=fixture();x.privateBody='SYNTHETIC_CANARY';
 assert.equal(JSON.stringify(go(x)).includes('SYNTHETIC_CANARY'),false)});
