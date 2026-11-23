/** Whole Macroturn R01: source-only, read-only Work search receipt auditor.
 * Input is an authorized caller's already-observed, bounded Work source cut.
 * No host rights, message retrieval, full-text index, semantic truth, or writes.
 */
import {createHash} from 'node:crypto';
const ROOM=/^[A-Za-z0-9_-]{3,80}$/;
const TOKEN=/^[A-Za-z0-9_]{3,80}$/;
export const DIRECT='QUERY_TOKEN_MATCH';
export const NEIGHBOR='EXPLICIT_REFERENCE_NEIGHBOR';
const denied=()=>({status:'HOLD',reason:'INVALID_OR_UNAUTHORIZED_INPUT',findings:[],sourceBodiesExported:false,authorityEffect:'NONE'});
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&(Object.getPrototypeOf(x)===Object.prototype||Object.getPrototypeOf(x)===null);
export function auditWorkRecall({roomId,term,sourceRows,graphResult}={}){
  if(typeof roomId!=='string'||!ROOM.test(roomId)||typeof term!=='string'||!TOKEN.test(term)||
     !Array.isArray(sourceRows)||sourceRows.length<1||sourceRows.length>100||!plain(graphResult))return denied();
  const w=graphResult.sourceWindow,ev=graphResult.evidence;
  if(!plain(w)||!Array.isArray(ev)||ev.length>100||!Number.isInteger(w.firstAfterSeq)||
     !Number.isInteger(w.nextAfterSeq)||w.firstAfterSeq<0||w.nextAfterSeq<w.firstAfterSeq||
     w.nextAfterSeq>500||w.records!==sourceRows.length||typeof w.hasMore!=='boolean'||typeof w.complete!=='boolean')return denied();
  const rows=new Map();
  for(const x of sourceRows){
    if(!plain(x)||x.roomId!==roomId||x.mode!=='WORK'||!Number.isInteger(x.seq)||
       x.seq<=w.firstAfterSeq||x.seq>w.nextAfterSeq||typeof x.text!=='string'||
       x.text.length>12000||rows.has(x.seq))return denied();
    rows.set(x.seq,x.text);
  }
  const reasons=new Map();
  for(const x of ev){
    if(!plain(x)||!plain(x.source)||x.source.roomId!==roomId||!rows.has(x.source.seq)||
       ![DIRECT,NEIGHBOR].includes(x.retrievalReason))return denied();
    if(!reasons.has(x.source.seq))reasons.set(x.source.seq,new Set());
    reasons.get(x.source.seq).add(x.retrievalReason);
  }
  const findings=[];
  for(const [seq,body] of [...rows].sort((a,b)=>a[0]-b[0])){
    const offset=body.toLowerCase().indexOf(term.toLowerCase());
    const why=reasons.get(seq)||new Set();
    const kind=offset>=0&&!why.has(DIRECT)?'MISSING_REPORTED_DIRECT_MATCH':
      offset<0&&why.has(DIRECT)?'DIRECT_REPORT_WITHOUT_LITERAL':
      offset>=0?'REPORTED_DIRECT_LITERAL_MATCH':
      why.has(NEIGHBOR)?'RELATED_NOT_DIRECT':'NO_LITERAL_IN_SUPPLIED_SOURCE';
    findings.push({seq,kind,literalOffset:offset,sourceLength:body.length,retrievalReasons:[...why].sort()});
  }
  return {schema:'atlas.work.graph-recall-candidate/v0.1',
    status:findings.some(x=>x.kind==='MISSING_REPORTED_DIRECT_MATCH')?'REVIEW_GAP':'REVIEW_ONLY',
    roomFingerprint:createHash('sha256').update(roomId).digest('hex').slice(0,20),term,
    window:{firstAfterSeq:w.firstAfterSeq,nextAfterSeq:w.nextAfterSeq,hasMore:w.hasMore,complete:w.complete},
    sourceRows:rows.size,findings,querySemantics:'SINGLE_ASCII_TOKEN_LITERAL_COMPARISON',
    indexCoverage:'UNKNOWN',canConcludeGlobalAbsence:false,canConcludeSemanticEquivalence:false,
    sourceBodiesExported:false,hostAttested:false,rightsAtReturnVerified:false,
    authorityEffect:'NONE',performsWrites:false};
}
