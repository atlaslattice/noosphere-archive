import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync, sign} from 'node:crypto';
import {canonical, evaluate, ROLE, SCHEMA} from '../tools/swarmchat_proof_gate.mjs';

function fixture() {
  const identities = {};
  for (const role of new Set(Object.values(ROLE))) {
    const {privateKey, publicKey} = generateKeyPairSync('ed25519');
    identities[role] = { privateKey, kid: role + '-fixture',
      publicKeyPem: publicKey.export({format:'pem',type:'spki'}).toString() };
  }
  const trust = { schema: SCHEMA, keys: Object.fromEntries(
    Object.entries(identities).map(([role, o]) => [o.kid, {
      role, synthetic:true, publicKeyPem:o.publicKeyPem }]))};
  const bundle = {schema:SCHEMA,environment:'test',tenant:'tenant-A',
    room:'work-release',runId:'disposable-test-001',receipts:[]};
  function put(kind, additions={}) {
    const role=ROLE[kind], key=identities[role];
    const record={schema:SCHEMA,kind,environment:bundle.environment,
      tenant:bundle.tenant,room:bundle.room,runId:bundle.runId,occurredAt:1000,
      ...additions};
    const bytes=Buffer.from(canonical(record));
    const envelope={kid:key.kid,payload_b64:bytes.toString('base64url'),
      sig_b64:sign(null,bytes,key.privateKey).toString('base64url')};
    bundle.receipts.push(envelope);
    return envelope;
  }
  return {bundle,trust,put,identities};
}
function addIdentity(f) {
  f.put('PLATFORM_BIND',{subject:'sender',assurance:'PLATFORM_SESSION',originMode:'WORK',
    conversationId:'thread-a',principalId:'principal-a',memberId:'member-a'});
  f.put('PLATFORM_BIND',{subject:'receiver',assurance:'PLATFORM_SESSION',originMode:'WORK',
    conversationId:'thread-b',principalId:'principal-b',memberId:'member-b'});
  f.put('SESSION_AUDIT',{conversationId:'thread-a',principalId:'principal-a',memberId:'member-a'});
  f.put('SESSION_AUDIT',{conversationId:'thread-b',principalId:'principal-b',memberId:'member-b'});
}
function addExchange(f) {
  f.put('POST_STORE',{conversationId:'thread-a',originMode:'WORK',seq:7,requestId:'request-1',occurredAt:1005});
  f.put('CALLBACK_DELIVERED',{conversationId:'thread-b',seq:7,requestId:'request-1',
    nonce:'nonce-12345678901234567890',leaseExpiresAt:1300,occurredAt:1100});
  f.put('MODEL_ACTIVATED',{conversationId:'thread-b',nonce:'nonce-12345678901234567890',occurredAt:1120});
  f.put('RECEIVER_ACK',{conversationId:'thread-b',nonce:'nonce-12345678901234567890',
    requestId:'request-1',seq:7,occurredAt:1130});
  f.put('REPLY_STORE',{conversationId:'thread-b',seq:8,parentSeq:7,requestId:'reply-1',occurredAt:1150});
  f.put('REPLY_READBACK',{seq:8,parentSeq:7,requestId:'reply-1',occurredAt:1200});
}
function addWorkspace(f) {
  f.put('WORKSPACE_APPEND',{itemId:'candidate-a',revision:1,digest:'a'.repeat(64)});
  f.put('WORKSPACE_READBACK',{itemId:'candidate-a',revision:1,digest:'a'.repeat(64)});
  f.put('WORKSPACE_RACE_TEST',{itemId:'candidate-a',disposable:true,passed:[
    'stale_write_rejected','conflict_preserved','lost_ack_idempotent','revoked_write_rejected']});
}
function addPrivacy(f) {
  const data={disposable:true,suiteId:'privacy-fixture-1',buildSha:'b'.repeat(64),
    unauthorizedStoreTouches:0,passed:['wrong_tenant','revoked_after_read',
      'private_denied_before_query','hidden_world_noninterference',
      'cache_scope_isolation','return_rights_rechecked']};
  f.put('PRIVACY_HOST_TEST',data);f.put('PRIVACY_AUDIT_TEST',data);
}
function addDeployment(f) {
  const data={deploymentId:'deploy-x',host:'staging.example.invalid',buildSha:'b'.repeat(64)};
  f.put('PUBLISH',data);f.put('SERVED',data);
  f.put('ROLLBACK_CHECK',{...data,disposable:true,passed:true});
  f.put('OWNER_APPROVAL',{...data,approved:true});
}
const status=(f,key)=>evaluate(f.bundle,f.trust).gates[key].status;

test('empty broker-like observations are NOT identity or wake proof',()=>{
  const f=fixture();const r=evaluate(f.bundle,f.trust);
  for(const gate of Object.values(r.gates))assert.equal(gate.status,'NOT_OBSERVED');
  assert.equal(r.productionPromotionAllowed,false);
});
test('signed platform identity and independent audit do not claim production',()=>{
  const f=fixture();addIdentity(f);
  assert.equal(status(f,'identity'),'SYNTHETIC_OR_NONPRODUCTION_ONLY');
  assert.equal(status(f,'a2a'),'NOT_OBSERVED');
});
test('platform bind absent cannot be replaced by a self-declared member name',()=>{
  const f=fixture(); f.put('POST_STORE',{memberId:'looks-real',seq:1,requestId:'r1',originMode:'WORK'});
  assert.equal(status(f,'identity'),'NOT_OBSERVED');
  assert.equal(status(f,'a2a'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('full synthetic five-chain receipt fixture never promotes production',()=>{
  const f=fixture();addIdentity(f);addExchange(f);addWorkspace(f);addPrivacy(f);addDeployment(f);
  const r=evaluate(f.bundle,f.trust);
  for(const gate of Object.values(r.gates))assert.equal(gate.status,'SYNTHETIC_OR_NONPRODUCTION_ONLY');
  assert.equal(r.acceptedReceiptCount,19);assert.equal(r.productionPromotionAllowed,false);
  assert.equal(r.rejected.length,0);
});
test('missing model activation means callback != verified wake',()=>{
  const f=fixture();addIdentity(f);addExchange(f);
  f.bundle.receipts=f.bundle.receipts.filter(e=>{
    const v=JSON.parse(Buffer.from(e.payload_b64,'base64url').toString());
    return v.kind!=='MODEL_ACTIVATED';});
  assert.equal(status(f,'a2a'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('missing receiver acknowledgment means posted != delivered',()=>{
  const f=fixture();addIdentity(f);addExchange(f);
  f.bundle.receipts=f.bundle.receipts.filter(e=>{
    const v=JSON.parse(Buffer.from(e.payload_b64,'base64url').toString());
    return v.kind!=='RECEIVER_ACK';});
  assert.equal(status(f,'a2a'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('two-way reply must link to original seq',()=>{
  const f=fixture();addIdentity(f);addExchange(f);
  f.bundle.receipts=f.bundle.receipts.filter(e=>{
    const v=JSON.parse(Buffer.from(e.payload_b64,'base64url').toString());
    return v.kind!=='REPLY_STORE';});
  f.put('REPLY_STORE',{conversationId:'thread-b',seq:8,parentSeq:999,requestId:'reply-1',occurredAt:1150});
  assert.equal(status(f,'a2a'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('expired callback lease is NOT delivery evidence',()=>{
  const f=fixture();addIdentity(f);addExchange(f);
  f.bundle.receipts=f.bundle.receipts.filter(e=>{
    const v=JSON.parse(Buffer.from(e.payload_b64,'base64url').toString());
    return v.kind!=='CALLBACK_DELIVERED';});
  f.put('CALLBACK_DELIVERED',{conversationId:'thread-b',seq:7,requestId:'request-1',
    nonce:'nonce-12345678901234567890',leaseExpiresAt:900,occurredAt:1100});
  assert.equal(status(f,'a2a'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('workspace mismatched digest is HOLD',()=>{
  const f=fixture();addWorkspace(f);
  f.bundle.receipts=f.bundle.receipts.filter(e=>JSON.parse(Buffer.from(e.payload_b64,'base64url').toString()).kind!=='WORKSPACE_READBACK');
  f.put('WORKSPACE_READBACK',{itemId:'candidate-a',revision:1,digest:'c'.repeat(64)});
  assert.equal(status(f,'workspace'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('privacy proof requires independent auditor and zero unauthorized store access',()=>{
  const f=fixture();addPrivacy(f);
  assert.equal(status(f,'privacy'),'SYNTHETIC_OR_NONPRODUCTION_ONLY');
  f.bundle.receipts=f.bundle.receipts.filter(e=>JSON.parse(Buffer.from(e.payload_b64,'base64url').toString()).kind!=='PRIVACY_AUDIT_TEST');
  assert.equal(status(f,'privacy'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('served digest mismatch cannot prove deployment',()=>{
  const f=fixture();addDeployment(f);
  f.bundle.receipts=f.bundle.receipts.filter(e=>JSON.parse(Buffer.from(e.payload_b64,'base64url').toString()).kind!=='SERVED');
  f.put('SERVED',{deploymentId:'deploy-x',host:'staging.example.invalid',buildSha:'d'.repeat(64)});
  assert.equal(status(f,'deployment'),'HOLD_INCOMPLETE_OR_MISMATCH');
});
test('duplicate replay is rejected and never used twice',()=>{
  const f=fixture();const e=f.put('PUBLISH',{deploymentId:'x',host:'h',buildSha:'a'.repeat(64)});
  f.bundle.receipts.push(e);
  assert.equal(evaluate(f.bundle,f.trust).rejected.length,1);
});
test('tampered signature is rejected',()=>{
  const f=fixture();const e=f.put('PLATFORM_BIND',{subject:'receiver',assurance:'PLATFORM_SESSION'});
  e.sig_b64='z'+e.sig_b64.slice(1);
  const r=evaluate(f.bundle,f.trust);
  assert.equal(r.acceptedReceiptCount,0);assert.equal(r.rejected.length,1);
});
test('receipt signer role must come from independent trusted anchor',()=>{
  const f=fixture(); f.put('PUBLISH',{deploymentId:'x',host:'h',buildSha:'a'.repeat(64)});
  f.trust.keys['publisher-fixture'].role='receiver';
  assert.equal(evaluate(f.bundle,f.trust).acceptedReceiptCount,0);
});
test('untrusted new key inside payload cannot authorize itself',()=>{
  const f=fixture();f.put('PLATFORM_BIND',{subject:'receiver',assurance:'PLATFORM_SESSION'});
  f.bundle.receipts[0].kid='not-pinned';
  assert.equal(evaluate(f.bundle,f.trust).acceptedReceiptCount,0);
});
test('sensitive body fields are rejected before proof calculation',()=>{
  const f=fixture();f.put('MODEL_ACTIVATED',{messageBody:'private Imagine text'});
  assert.equal(evaluate(f.bundle,f.trust).acceptedReceiptCount,0);
});
test('scope mismatch holds',()=>{
  const f=fixture();f.put('PLATFORM_BIND',{tenant:'other-tenant',subject:'receiver'});
  assert.equal(evaluate(f.bundle,f.trust).acceptedReceiptCount,0);
});
test('missing expiry or unsigned callback cannot be promoted',()=>{
  const f=fixture();addIdentity(f);addExchange(f);
  f.bundle.receipts=f.bundle.receipts.filter(e=>JSON.parse(Buffer.from(e.payload_b64,'base64url').toString()).kind!=='CALLBACK_DELIVERED');
  f.put('CALLBACK_DELIVERED',{conversationId:'thread-b',seq:7,requestId:'request-1',nonce:'nonce-12345678901234567890',occurredAt:1100});
  assert.equal(status(f,'a2a'),'HOLD_INCOMPLETE_OR_MISMATCH');
});

test('unknown signed metadata keys are rejected even without blacklist words',()=>{
  const samples=['apiKey','password','sourceUri','privateMemo','hiddenContent'];
  for (const name of samples) {
    const f=fixture();
    f.put('MODEL_ACTIVATED',{conversationId:'thread-b',nonce:'nonce-12345678901234567890',
      [name]:'SYNTHETIC_VALUE'});
    const result=evaluate(f.bundle,f.trust);
    assert.equal(result.acceptedReceiptCount,0,name);
    assert.equal(result.rejected.length,1,name);
  }
});
test('signed unexpected nested blob cannot bypass exact receipt schema',()=>{
  const f=fixture();
  f.put('PUBLISH',{deploymentId:'x',host:'h',buildSha:'a'.repeat(64),
    details:{unlisted:'SYNTHETIC_PRIVATE_SENTINEL'}});
  assert.equal(evaluate(f.bundle,f.trust).acceptedReceiptCount,0);
});
test('approved passed array must consist of unique bounded strings',()=>{
  for (const passed of [['duplicate','duplicate'],['x'.repeat(101)],['ok',42]]) {
    const f=fixture();
    f.put('PRIVACY_HOST_TEST',{disposable:true,suiteId:'s',buildSha:'b'.repeat(64),
      unauthorizedStoreTouches:0,passed});
    assert.equal(evaluate(f.bundle,f.trust).acceptedReceiptCount,0);
  }
});
test('supported signed metadata still decodes with exact field allowlists',()=>{
  const f=fixture();addIdentity(f);addExchange(f);addWorkspace(f);addPrivacy(f);addDeployment(f);
  const r=evaluate(f.bundle,f.trust);
  assert.equal(r.acceptedReceiptCount,19);assert.equal(r.rejected.length,0);
  assert.equal(r.productionPromotionAllowed,false);
});
