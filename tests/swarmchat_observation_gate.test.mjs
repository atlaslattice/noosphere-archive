import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectBrokerMessage,inspectBrokerStatus,reconcileEvidence}
  from '../tools/swarmchat_observation_gate.mjs';

const expected={roomId:'synthetic-work',seq:23,requestId:'synthetic-post-1'};
function fixture(){return {structuredContent:{
  room:{roomId:'synthetic-work',kind:'work',status:'open'},
  messageEvidence:{roomId:'synthetic-work',seq:23,requestId:'synthetic-post-1',
    memberId:'self-declared-synthetic',delivery:[],receipts:[],reads:[],replies:[]}
}};}
const inspect=(r=fixture(),x=expected)=>inspectBrokerMessage(r,x);
test('broker-shaped record proves only shape, not host storage',()=>{
 const x=inspect();assert.equal(x.status,'BROKER_REPORT_SHAPE_VALIDATED_NOT_ATTESTED');
 assert.equal(x.storedMessage,true);assert.equal(x.deliveryVerified,false);
 assert.equal(x.receiverActivatedVerified,false);assert.equal(x.independentConversationVerified,false);
});
test('empty delivery/readback is not proof',()=>{
 const x=inspect();assert.equal(x.deliveryRecords,'NONE_RECORDED');
 assert.equal(x.explicitReadRecords,'NONE_RECORDED');
});
test('delivery record does not prove signed arrival',()=>{
 const r=fixture();r.structuredContent.messageEvidence.delivery.push({status:'sent'});
 const x=inspect(r);assert.equal(x.deliveryRecords,'BROKER_RECORDED_NOT_HOST_ATTESTED');
 assert.equal(x.deliveryVerified,false);
});
test('self-reported read/reply does not prove an independent recipient',()=>{
 const r=fixture();r.structuredContent.messageEvidence.reads.push({by:'self'});
 r.structuredContent.messageEvidence.replies.push({by:'same'});
 const x=inspect(r);assert.equal(x.independentConversationVerified,false);
 assert.equal(x.receiverActivatedVerified,false);
});
test('wrong room holds',()=>{const r=fixture();r.structuredContent.room.roomId='wrong';
 assert.equal(inspect(r).storedMessage,false);});
test('wrong evidence room holds',()=>{const r=fixture();r.structuredContent.messageEvidence.roomId='wrong';
 assert.equal(inspect(r).storedMessage,false);});
test('wrong seq holds',()=>{const r=fixture();r.structuredContent.messageEvidence.seq=24;
 assert.equal(inspect(r).storedMessage,false);});
test('wrong requestId holds',()=>{const r=fixture();r.structuredContent.messageEvidence.requestId='wrong';
 assert.equal(inspect(r).storedMessage,false);});
test('private Play room cannot be Work proof',()=>{const r=fixture();r.structuredContent.room.kind='play';
 assert.equal(inspect(r).storedMessage,false);});
test('missing mandatory records hold',()=>{const r=fixture();delete r.structuredContent.messageEvidence.delivery;
 assert.equal(inspect(r).storedMessage,false);});
test('ill-typed mandatory records hold',()=>{const r=fixture();r.structuredContent.messageEvidence.receipts={};
 assert.equal(inspect(r).storedMessage,false);});
test('bad seq and requestId input types hold',()=>{
 assert.equal(inspect(fixture(),{...expected,seq:'23'}).storedMessage,false);
 assert.equal(inspect(fixture(),{...expected,requestId:[]}).storedMessage,false);
});
test('expired rooms can be read but not activated',()=>{
 const r=fixture();r.structuredContent.room.status='expired';
 const x=inspect(r);assert.equal(x.storedMessage,true);
 assert.equal(x.roomLifecycle,'expired');assert.equal(x.receiverActivatedVerified,false);
});
test('report never echoes source bodies, identifiers or requestId',()=>{
 const r=fixture();r.structuredContent.messageEvidence.body='SYNTHETIC_SECRET_CANARY';
 r.structuredContent.messageEvidence.memberId='private-person-label';
 const out=JSON.stringify(inspect(r));
 for(const secret of ['SYNTHETIC_SECRET_CANARY','private-person-label',
   'synthetic-work','synthetic-post-1'])assert.ok(!out.includes(secret));
});
test('two-world perturbation cannot change public response',()=>{
 const a=fixture(),b=fixture();a.structuredContent.messageEvidence.privateTitle='red';
 b.structuredContent.messageEvidence.privateTitle='blue';
 b.structuredContent.messageEvidence.privateCount=500;
 assert.deepEqual(inspect(a),inspect(b));
});
test('broker account login and member claims never attest a resident',()=>{
 const r=inspectBrokerStatus({accountAuthenticated:true,residentAuthenticated:true,
  liveParticipantsVerified:22,eventsAdvertised:true,modelWakesVerified:true});
 assert.equal(r.accountAuthenticatedReported,true);
 assert.equal(r.identity,'UNVERIFIED');assert.equal(r.activation,'UNVERIFIED');
 assert.equal(r.releaseEligible,false);
});
test('advertised event is not model activation',()=>{
 const r=inspectBrokerStatus({eventsAdvertised:true});
 assert.equal(r.eventsAdvertisedReported,true);assert.equal(r.activation,'UNVERIFIED');
});
test('synthetic signed proofs remain explicitly incomplete',()=>{
 const p={gates:{a2a:{status:'SYNTHETIC_OR_NONPRODUCTION_ONLY'},
  identity:{status:'SYNTHETIC_OR_NONPRODUCTION_ONLY'}},rejected:[]};
 assert.equal(reconcileEvidence(inspect(),p).declaredSignedChain,'NOT_ESTABLISHED');
});
test('even claimed real signatures are not host or owner authorization',()=>{
 const p={gates:{a2a:{status:'CORROBORATED_SIGNED_RECEIPTS'},
  identity:{status:'CORROBORATED_SIGNED_RECEIPTS'}},rejected:[]};
 const x=reconcileEvidence(inspect(),p);
 assert.equal(x.declaredSignedChain,'ISSUER_CLAIMS_CORROBORATED');
 assert.equal(x.independentlyVerifiedWake,false);assert.equal(x.productionReady,false);
});
test('missing source is an explicit hold',()=>{
 const x=reconcileEvidence(inspect(null));assert.equal(x.status,'SOURCE_NOT_OBSERVED');
 assert.equal(x.brokerStored,false);
});
