/** Read-only broker-shaped record validator. Not a host or identity attestor.
 * No network, storage, notifications, modes crossover or deployment actions.
 * A caller can forge the input file: source authenticity must come from
 * independent authenticated connector readback and host-signed receipts. */
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';

const HOLD=Object.freeze({schema:'atlas.swarmchat.observation.v1',
  status:'HOLD_UNVERIFIED_SOURCE',storedMessage:false,deliveryVerified:false,
  receiverActivatedVerified:false,independentConversationVerified:false,
  releaseEligible:false});
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.getPrototypeOf(v)===Object.prototype;
const text=v=>typeof v==='string'&&v.length>0&&v.length<=80;
const seq=v=>Number.isSafeInteger(v)&&v>0&&v<=500;
const stage=a=>a.length?'BROKER_RECORDED_NOT_HOST_ATTESTED':'NONE_RECORDED';

export function inspectBrokerMessage(read,expected){
  if(!obj(expected)||!text(expected.roomId)||!seq(expected.seq)||!text(expected.requestId))
    return {...HOLD};
  const v=obj(read?.structuredContent)?read.structuredContent:read;
  if(!obj(v)||!obj(v.room)||!obj(v.messageEvidence))return {...HOLD};
  const r=v.room,e=v.messageEvidence;
  if(!['open','stopped','expired'].includes(r.status)||r.kind!=='work'
    ||r.roomId!==expected.roomId||e.roomId!==expected.roomId
    ||e.seq!==expected.seq||e.requestId!==expected.requestId
    ||!seq(e.seq)||!text(e.memberId))return {...HOLD};
  for(const k of ['delivery','receipts','reads','replies'])
    if(!Object.hasOwn(e,k)||!Array.isArray(e[k])||e[k].length>200)return {...HOLD};
  return {schema:HOLD.schema,status:'BROKER_REPORT_SHAPE_VALIDATED_NOT_ATTESTED',
    sourceSeq:e.seq,roomLifecycle:r.status,storedMessage:true,
    deliveryRecords:stage(e.delivery),receiptRecords:stage(e.receipts),
    explicitReadRecords:stage(e.reads),directReplyRecords:stage(e.replies),
    deliveryVerified:false,receiverActivatedVerified:false,
    independentConversationVerified:false,releaseEligible:false};
}

/** Account-authenticated broker state is not independently bound resident IAM. */
export function inspectBrokerStatus(status){
  const v=obj(status?.structuredContent)?status.structuredContent:status;
  if(!obj(v))return {schema:'atlas.swarmchat.broker-status-observation.v1',
    status:'HOLD_UNVERIFIED_SOURCE',identity:'UNVERIFIED',
    activation:'UNVERIFIED',releaseEligible:false};
  return {schema:'atlas.swarmchat.broker-status-observation.v1',
    status:'BROKER_STATUS_OBSERVED_ONLY',
    accountAuthenticatedReported:v.accountAuthenticated===true,
    identity:'UNVERIFIED',activation:'UNVERIFIED',
    eventsAdvertisedReported:v.eventsAdvertised===true,
    independentParticipants:'NOT_VERIFIED',releaseEligible:false};
}

/** A complete signature set is a set of issuer CLAIMS, not host verification. */
export function reconcileEvidence(observation,signedReport=null){
  const stored=observation?.status==='BROKER_REPORT_SHAPE_VALIDATED_NOT_ATTESTED'
    && observation.storedMessage===true;
  const signatureClaims=signedReport?.gates?.a2a?.status==='CORROBORATED_SIGNED_RECEIPTS'
    && signedReport?.gates?.identity?.status==='CORROBORATED_SIGNED_RECEIPTS'
    && Array.isArray(signedReport.rejected)&&signedReport.rejected.length===0;
  return {schema:'atlas.swarmchat.evidence-reconciliation.v1',
    brokerStored:stored,
    declaredSignedChain:signatureClaims?'ISSUER_CLAIMS_CORROBORATED':'NOT_ESTABLISHED',
    independentlyVerifiedWake:false,independentlyVerifiedIdentity:false,
    productionReady:false,
    status:stored?'SOURCE_CLAIM_VALIDATED_HOST_PROOF_HELD':'SOURCE_NOT_OBSERVED',
    requiredNext:'PLATFORM_SESSION_ATTESTATION_AND_ONE_OPTED_IN_RECEIVER'};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  if(process.argv.length!==4){
    console.error('Usage: node tools/swarmchat_observation_gate.mjs <broker-read.json> <expected.json>');
    process.exitCode=2;
  } else {
    try{
      const read=JSON.parse(readFileSync(process.argv[2],'utf8'));
      const expected=JSON.parse(readFileSync(process.argv[3],'utf8'));
      console.log(JSON.stringify(inspectBrokerMessage(read,expected),null,2));
      process.exitCode=1; // Untrusted file is NEVER host evidence.
    }catch(_e){console.log(JSON.stringify({...HOLD},null,2));process.exitCode=2;}
  }
}
