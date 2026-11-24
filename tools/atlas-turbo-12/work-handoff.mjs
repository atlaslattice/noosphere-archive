/**
 * Atlas Turbo ×12: inert native Work handoff admission boundary (public-safe).
 * NO broker calls, identity minting, room creation, subscriptions or publishing.
 * Its hashed preparation ID is NOT a capability or an authorization.
 */
import {createHash} from 'node:crypto';
export const SCHEMA='atlas.turbo12.public-work-envelope/v1';
export const PIN='07533cf7a6b6f567259962bf73efee9b22b47cbacb429499787800e07864e5a6';
export const PROJECTS=Object.freeze(['SwarmChat','Atlas','Ariadne','Iron Empire']);
export const ROUNDS=Object.freeze([
 'source_pin','work_mode','platform_identity','receiver_activation',
 'semantic_relation','falsifier','ledger_closure','accessible_range',
 'resilience','consent_rights','canon_human','served_release']);
const FIELDS=new Set(['schema','coordinate','registryDigest','nodeDigest','round',
 'project','mode','origin','rightsEpoch','tenant','account','principal','requestId',
 'consent','sourceRef']);
const ID=/^[A-Za-z0-9._:-]{1,80}$/;
const SHA=/^[a-f0-9]{64}$/;
const COORD=/^H(0[1-9]|1[0-2])\.S(0[1-9]|1[0-2])\.N(0[1-9]|1[0-2])$/;
const ref=v=>typeof v==='string'&&v.length<=350
 && ['https://github.com/','https://drive.google.com/','https://docs.google.com/']
  .some(p=>v.startsWith(p))&&!/[?#@\r\n%]/.test(v);
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)
 && (Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null);
const hold=()=>Object.freeze({schema:SCHEMA,status:'HOLD',authorityEffect:'NONE',
  hostAuthenticated:false,modelWoke:false,posted:false,canon:false});
export function prepare(record,{expectedNodeDigest}={}){
 try{
  if(!plain(record)||Object.keys(record).length!==FIELDS.size||
      Object.keys(record).some(k=>!FIELDS.has(k)))return hold();
  if(record.schema!==SCHEMA||record.registryDigest!==PIN||!SHA.test(record.nodeDigest)
   ||record.nodeDigest!==expectedNodeDigest||!COORD.test(record.coordinate))return hold();
  if(!Number.isInteger(record.round)||record.round<1||record.round>12||
     !PROJECTS.includes(record.project))return hold();
  if(record.mode!=='WORK'||record.origin!=='WORK_POINTER_ONLY'||
    record.consent!=='CALLER_DECLARED_NOT_HOST_ATTESTED')return hold();
  if(!['tenant','account','principal','requestId'].every(k=>typeof record[k]==='string'&&ID.test(record[k]))
   ||!Number.isSafeInteger(record.rightsEpoch)||record.rightsEpoch<0||!ref(record.sourceRef))return hold();
  // Scope the *local* duplicate key by account and rights epoch; not a credential.
  const tuple=[record.tenant,record.account,record.principal,record.rightsEpoch,
    record.coordinate,record.project,record.round,record.requestId];
  const key=createHash('sha256').update(JSON.stringify(tuple)).digest('hex');
  return Object.freeze({schema:SCHEMA,status:'PREPARED_NOT_POSTED',
   coordinate:record.coordinate,round:record.round,project:record.project,
   sourceNodeDigest:record.nodeDigest,idempotencyDigest:key,
   rightsEpoch:record.rightsEpoch,hostAuthenticated:false,modelWoke:false,
   posted:false,sourceRead:false,rightsAtReturnVerified:false,
   semanticEdgeAccepted:false,canon:false,authorityEffect:'NONE'});
 }catch{return hold()}
}
export function inertReturn(prepared,current){
 if(!plain(prepared)||prepared.status!=='PREPARED_NOT_POSTED'||!plain(current)
   ||Object.keys(current).sort().join('|')!=='declaredRights|mode|nodeDigest|rightsEpoch'
   ||current.mode!=='WORK'||current.declaredRights!=='DECLARED_ALLOW'
   ||current.rightsEpoch!==prepared.rightsEpoch
   ||current.nodeDigest!==prepared.sourceNodeDigest)return hold();
 return Object.freeze({schema:SCHEMA,status:'LOCALLY_RECHECKED_NOT_HOST_AUTHORIZED',
  rightsAtReturnVerified:false,modelWoke:false,posted:false,
  authorityEffect:'NONE',canon:false});
}