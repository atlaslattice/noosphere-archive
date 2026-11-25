import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync, sign} from 'node:crypto';
import {canonical,evaluate,ROLE,SCHEMA} from '../tools/swarmchat_proof_gate.mjs';

function fixture({environment='production', synthetic=false, privacyBuild='b', deploymentBuild='b'}={}) {
 const identities = Object.fromEntries([...new Set(Object.values(ROLE))].map(role=>{
  const {privateKey,publicKey}=generateKeyPairSync('ed25519');
  return [role,{privateKey,kid:role+'-fixture',publicKeyPem:publicKey.export({format:'pem',type:'spki'}).toString()}];
 }));
 const trust={schema:SCHEMA,keys:Object.fromEntries(Object.entries(identities).map(([role,o])=>[o.kid,{role,synthetic,publicKeyPem:o.publicKeyPem}]))};
 const bundle={schema:SCHEMA,environment,tenant:'tenant-A',room:'work-release',runId:'synthetic-fixture',receipts:[]};
 function put(kind, extra={}) {
  const role=ROLE[kind], key=identities[role];
  const record={schema:SCHEMA,kind,environment,tenant:bundle.tenant,room:bundle.room,runId:bundle.runId,occurredAt:1000,...extra};
  const bytes=Buffer.from(canonical(record));
  bundle.receipts.push({kid:key.kid,payload_b64:bytes.toString('base64url'),sig_b64:sign(null,bytes,key.privateKey).toString('base64url')});
 }
 // NOTE: all data synthetic; production only tests how the verifier would label claims from trusted keys.
 put('PLATFORM_BIND',{subject:'sender',assurance:'PLATFORM_SESSION',originMode:'WORK',conversationId:'thread-a',principalId:'principal-a',memberId:'member-a'});
 put('PLATFORM_BIND',{subject:'receiver',assurance:'PLATFORM_SESSION',originMode:'WORK',conversationId:'thread-b',principalId:'principal-b',memberId:'member-b'});
 put('SESSION_AUDIT',{conversationId:'thread-a',principalId:'principal-a',memberId:'member-a'});
 put('SESSION_AUDIT',{conversationId:'thread-b',principalId:'principal-b',memberId:'member-b'});
 put('POST_STORE',{conversationId:'thread-a',originMode:'WORK',seq:7,requestId:'request-1',occurredAt:1005});
 put('CALLBACK_DELIVERED',{conversationId:'thread-b',seq:7,requestId:'request-1',nonce:'nonce-12345678901234567890',leaseExpiresAt:1300,occurredAt:1100});
 put('MODEL_ACTIVATED',{conversationId:'thread-b',nonce:'nonce-12345678901234567890',occurredAt:1120});
 put('RECEIVER_ACK',{conversationId:'thread-b',nonce:'nonce-12345678901234567890',requestId:'request-1',seq:7,occurredAt:1130});
 put('REPLY_STORE',{conversationId:'thread-b',seq:8,parentSeq:7,requestId:'reply-1',occurredAt:1150});
 put('REPLY_READBACK',{seq:8,parentSeq:7,requestId:'reply-1',occurredAt:1200});
 put('WORKSPACE_APPEND',{itemId:'candidate-a',revision:1,digest:'a'.repeat(64)});
 put('WORKSPACE_READBACK',{itemId:'candidate-a',revision:1,digest:'a'.repeat(64)});
 put('WORKSPACE_RACE_TEST',{itemId:'candidate-a',disposable:true,passed:['stale_write_rejected','conflict_preserved','lost_ack_idempotent','revoked_write_rejected']});
 const privacy={disposable:true,suiteId:'privacy-fixture-1',buildSha:privacyBuild.repeat(64),unauthorizedStoreTouches:0,passed:['wrong_tenant','revoked_after_read','private_denied_before_query','hidden_world_noninterference','cache_scope_isolation','return_rights_rechecked']};
 put('PRIVACY_HOST_TEST',privacy);put('PRIVACY_AUDIT_TEST',privacy);
 const release={deploymentId:'deploy-x',host:'staging.example.invalid',buildSha:deploymentBuild.repeat(64)};
 put('PUBLISH',release);put('SERVED',release);
 put('ROLLBACK_CHECK',{...release,disposable:true,passed:true});
 put('OWNER_APPROVAL',{...release,approved:true});
 return {bundle,trust,put};
}

test('matched signed metadata chain may only corroborate signer claims, never promote',()=>{
 const {bundle,trust}=fixture();let x=evaluate(bundle,trust);
 assert.equal(x.acceptedReceiptCount,19);assert.equal(x.rejected.length,0);
 assert.equal(x.gates.privacy.status,'CORROBORATED_SIGNED_RECEIPTS');
 assert.equal(x.gates.deployment.status,'CORROBORATED_SIGNED_RECEIPTS');
 assert.equal(x.allEvidenceChainsPresent,true);
 assert.equal(x.productionPromotionAllowed,false);
});

test('DIFFERENT PRIVACY AND DEPLOYMENT BUILD must not corroborate a single release',()=>{
 const {bundle,trust}=fixture({privacyBuild:'b',deploymentBuild:'c'});
 const x=evaluate(bundle,trust);
 assert.equal(x.rejected.length,0);
 assert.equal(x.gates.privacy.status,'HOLD_INCOMPLETE_OR_MISMATCH');
 assert.notEqual(x.gates.deployment.status,'CORROBORATED_SIGNED_RECEIPTS',
   'Release deployment claim incorrectly reuses privacy proof on a different code build');
 assert.equal(x.allEvidenceChainsPresent,false);
});

function replaceKind(f,kind,data) {
 f.bundle.receipts=f.bundle.receipts.filter(e=>
   JSON.parse(Buffer.from(e.payload_b64,'base64url').toString()).kind!==kind);
 f.put(kind,data);
}

test('rollback proof for a different build must not count for published bytes',()=>{
 const f=fixture();
 replaceKind(f,'ROLLBACK_CHECK',{deploymentId:'deploy-x',host:'staging.example.invalid',
   buildSha:'c'.repeat(64),disposable:true,passed:true});
 const x=evaluate(f.bundle,f.trust);
 assert.equal(x.gates.deployment.status,'HOLD_INCOMPLETE_OR_MISMATCH');
 assert.equal(x.allEvidenceChainsPresent,false);
});

test('approval for a different host must not be counted against this release',()=>{
 const f=fixture();
 replaceKind(f,'OWNER_APPROVAL',{deploymentId:'deploy-x',host:'other.example.invalid',
   buildSha:'b'.repeat(64),approved:true});
 const x=evaluate(f.bundle,f.trust);
 assert.equal(x.gates.deployment.status,'HOLD_INCOMPLETE_OR_MISMATCH');
 assert.equal(x.allEvidenceChainsPresent,false);
});

test('multiple different signed build pins within one runId are ambiguous, not a release proof',()=>{
 const f=fixture();
 f.put('PUBLISH',{deploymentId:'deploy-y',host:'another.example.invalid',
   buildSha:'c'.repeat(64),occurredAt:1300});
 const x=evaluate(f.bundle,f.trust);
 assert.equal(x.gates.deployment.status,'HOLD_INCOMPLETE_OR_MISMATCH');
 assert.equal(x.gates.privacy.status,'HOLD_INCOMPLETE_OR_MISMATCH');
 assert.equal(x.allEvidenceChainsPresent,false);
});

test('signed mismatched privacy audit fails rather than borrowing a matching host claim',()=>{
 const f=fixture();
 replaceKind(f,'PRIVACY_AUDIT_TEST',{disposable:true,suiteId:'privacy-fixture-1',
   buildSha:'c'.repeat(64),unauthorizedStoreTouches:0,passed:[
    'wrong_tenant','revoked_after_read','private_denied_before_query',
    'hidden_world_noninterference','cache_scope_isolation','return_rights_rechecked']});
 const x=evaluate(f.bundle,f.trust);
 assert.equal(x.gates.privacy.status,'HOLD_INCOMPLETE_OR_MISMATCH');
 assert.equal(x.gates.deployment.status,'HOLD_INCOMPLETE_OR_MISMATCH');
 assert.equal(x.allEvidenceChainsPresent,false);
});

test('all build evidence coherent but approval has a wrong deploymentId',()=>{
 const f=fixture();
 replaceKind(f,'OWNER_APPROVAL',{deploymentId:'deploy-wrong',host:'staging.example.invalid',
   buildSha:'b'.repeat(64),approved:true});
 assert.equal(evaluate(f.bundle,f.trust).gates.deployment.status,'HOLD_INCOMPLETE_OR_MISMATCH');
});

test('independently signed privacy-only chain remains valid for original build when deployment missing',()=>{
 const {bundle,trust}=fixture();bundle.receipts=bundle.receipts.filter(e=>{
   const p=JSON.parse(Buffer.from(e.payload_b64,'base64url'));return !['PUBLISH','SERVED','ROLLBACK_CHECK','OWNER_APPROVAL'].includes(p.kind);
 });
 const x=evaluate(bundle,trust);
 assert.equal(x.gates.privacy.status,'CORROBORATED_SIGNED_RECEIPTS');
 assert.equal(x.gates.deployment.status,'NOT_OBSERVED');
});

test('staging synthetic matching fixture never claims signed production corroboration',()=>{
 const {bundle,trust}=fixture({environment:'staging',synthetic:true});
 const x=evaluate(bundle,trust);for(const g of Object.values(x.gates)) assert.equal(g.status,'SYNTHETIC_OR_NONPRODUCTION_ONLY');
 assert.equal(x.allEvidenceChainsPresent,false);
});
