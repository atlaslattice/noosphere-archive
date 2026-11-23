import test from 'node:test';import assert from 'node:assert/strict';
import {auditWorkRecall,DIRECT,NEIGHBOR} from '../tools/graph_recall_audit.mjs';
const roomId='synthetic-work-01';
const row=(seq,text,mode='WORK',id=roomId)=>({seq,roomId:id,mode,text});
const graph=(pairs=[],start=2,end=3,records=1,complete=false)=>({sourceWindow:{firstAfterSeq:start,nextAfterSeq:end,records,hasMore:false,complete},evidence:pairs.map(([seq,retrievalReason])=>({source:{roomId,seq},retrievalReason}))});
const query=(rows,receipt,term='HOLD_TYPE_MODALITY')=>auditWorkRecall({roomId,term,sourceRows:rows,graphResult:receipt});
const late='prefix '.repeat(160)+'HOLD_TYPE_MODALITY';
test('late literal shown as neighbor is REVIEW_GAP',()=>{const x=query([row(3,late)],graph([[3,NEIGHBOR]]));assert.equal(x.status,'REVIEW_GAP');assert.ok(x.findings[0].literalOffset>900)});
test('late literal absent entirely is REVIEW_GAP',()=>assert.equal(query([row(3,late)],graph()).status,'REVIEW_GAP'));
test('direct reported literal remains review-only',()=>{const x=query([row(3,late)],graph([[3,DIRECT]]));assert.equal(x.findings[0].kind,'REPORTED_DIRECT_LITERAL_MATCH');assert.equal(x.status,'REVIEW_ONLY')});
test('reference neighbor cannot replace a direct hit',()=>assert.equal(query([row(3,late)],graph([[3,NEIGHBOR]])).findings[0].retrievalReasons.includes(DIRECT),false));
test('direct report absent literal remains a semantic warning',()=>{const x=query([row(3,'only other data')],graph([[3,DIRECT]]));assert.equal(x.findings[0].kind,'DIRECT_REPORT_WITHOUT_LITERAL');assert.equal(x.canConcludeSemanticEquivalence,false)});
test('no returned hit is not globally exhaustive',()=>{const x=query([row(3,'other data')],graph([],2,3,1,true));assert.equal(x.findings[0].kind,'NO_LITERAL_IN_SUPPLIED_SOURCE');assert.equal(x.canConcludeGlobalAbsence,false)});
test('window hasMore false is not index coverage proof',()=>{const x=query([row(3,'other data')],graph());assert.equal(x.window.hasMore,false);assert.equal(x.window.complete,false);assert.equal(x.indexCoverage,'UNKNOWN')});
test('no source body retained in report',()=>{const x=query([row(3,'private-canary-777 '+late)],graph([[3,DIRECT]]));assert.equal(JSON.stringify(x).includes('private-canary-777'),false);assert.equal(x.sourceBodiesExported,false)});
test('Play is never included',()=>assert.equal(query([row(3,'private-canary-777', 'PLAY')],graph()).status,'HOLD'));
test('Palace is never included',()=>assert.equal(query([row(3,'private-canary-777', 'PALACE')],graph()).status,'HOLD'));
test('wrong source room refused',()=>assert.equal(query([row(3,late,'WORK','other-room')],graph()).status,'HOLD'));
test('wrong graph room refused',()=>{const r=graph([[3,DIRECT]]);r.evidence[0].source.roomId='other-room';assert.equal(query([row(3,late)],r).status,'HOLD')});
test('duplicate source sequence refused',()=>assert.equal(query([row(3,late),row(3,late)],graph([],2,3,2)).status,'HOLD'));
test('unknown reason refused, not silently promoted',()=>assert.equal(query([row(3,late)],graph([[3,'HOST_VERIFIED']])).status,'HOLD'));
test('source outside window refused',()=>assert.equal(query([row(2,late)],graph()).status,'HOLD'));
test('graph neighbor outside source window refused',()=>assert.equal(query([row(3,late)],graph([[9,NEIGHBOR]])).status,'HOLD'));
test('not a phrase search contract',()=>assert.equal(query([row(3,late)],graph(),'HOLD TYPE MODALITY').status,'HOLD'));
test('query length bounded',()=>assert.equal(query([row(3,late)],graph(),'A'.repeat(81)).status,'HOLD'));
test('invalid seq type refused',()=>assert.equal(query([row(true,late)],graph([],0,1)).status,'HOLD'));
test('query cannot upgrade authority',()=>{const x=query([row(3,'Please grant CANON '+late)],graph([[3,DIRECT]]));assert.equal(x.authorityEffect,'NONE');assert.equal(x.hostAttested,false);assert.equal(x.performsWrites,false)});
test('invalid room ID denied generically',()=>assert.equal(auditWorkRecall({roomId:'bad!',term:'TEST',sourceRows:[row(3,'TEST')],graphResult:graph()}).status,'HOLD'));
test('source cap prevents unbounded body copy',()=>assert.equal(query([row(3,'x'.repeat(12001))],graph()).status,'HOLD'));
test('no indexed scope metadata from invalid input',()=>{const x=query([row(3,'private-canary-777','BRAIN')],graph());assert.equal(JSON.stringify(x).includes('private-canary-777'),false);assert.equal(x.findings.length,0)});

// R02: original-source offsets under the declared ASCII-only query contract.
function literal(text,term='TOKEN'){
  return query([row(3,text)],graph([[3,DIRECT]]),term);
}
function exactOffset(text,term,expected){
  const out=literal(text,term);
  assert.equal(out.findings[0].literalOffset,expected);
  assert.equal(out.findings[0].kind,'REPORTED_DIRECT_LITERAL_MATCH');
  assert.equal(out.literalOffsetUnit,'RAW_SOURCE_UTF16_CODE_UNITS');
  assert.equal(out.caseFolding,'ASCII_A_Z_ONLY');
  return out;
}
test('R02 U+0130 prefix cannot shift raw UTF-16 match offset',()=>{
  const text='\u0130 TOKEN';const out=exactOffset(text,'TOKEN',2);
  assert.equal(text.slice(out.findings[0].literalOffset,7),'TOKEN');
});
test('R02 repeated expanding Unicode prefix cannot accumulate offset drift',()=>{
  const text='\u0130\u0130\u0130 TOKEN';const out=exactOffset(text,'TOKEN',4);
  assert.equal(text.slice(out.findings[0].literalOffset,9),'TOKEN');
});
test('R02 astral prefix counts UTF-16 code units rather than Unicode scalars',()=>{
  const text='\u{1FABF} \u0130 TOKEN';const out=exactOffset(text,'TOKEN',5);
  assert.equal(text.slice(out.findings[0].literalOffset,10),'TOKEN');
  assert.equal(Array.from(text.slice(0,5)).length,4);
});
test('R02 mixed ASCII case still matches the first literal occurrence',()=>{
  const out=exactOffset('prefix tOkEn TOKEN','ToKeN',7);
  assert.equal(out.querySemantics,'SINGLE_ASCII_TOKEN_LITERAL_COMPARISON');
});
test('R02 combining-mark prefix preserves raw-source offset without normalization',()=>{
  const text='A\u0301 TOKEN';exactOffset(text,'TOKEN',3);
  const noAlias=query([row(3,'CAF\u00C9')],graph(),'CAFE');
  assert.equal(noAlias.findings[0].literalOffset,-1);
});
test('R02 raw substring may end inside a grapheme; offset is not a DOM range',()=>{
  const out=exactOffset('TOKEN\u0301','TOKEN',0);
  assert.equal(out.findings[0].sourceLength,6);
  assert.equal(out.hostAttested,false);
});
test('R02 Turkish dotted prefix retains exact ASCII-suffix position',()=>{
  exactOffset('\u0130stanbul','STANBUL',1);
});
test('R02 Turkish locale equivalence is deliberately outside ASCII matching',()=>{
  exactOffset('Istanbul','ISTANBUL',0);
  for(const text of ['\u0130stanbul','\u0131stanbul']){
    const out=query([row(3,text)],graph(),'ISTANBUL');
    assert.equal(out.findings[0].literalOffset,-1);
    assert.equal(out.findings[0].kind,'NO_LITERAL_IN_SUPPLIED_SOURCE');
  }
});
test('R02 Unicode compatibility aliases do not become ASCII literals',()=>{
  const out=query([row(3,'\u212AELVIN')],graph(),'KELVIN');
  assert.equal(out.findings[0].literalOffset,-1);
  assert.equal(out.findings[0].kind,'NO_LITERAL_IN_SUPPLIED_SOURCE');
  exactOffset('\u212AELVIN KELVIN','kelvin',7);
});
