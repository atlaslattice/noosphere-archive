/**
 * SwarmChat proof gate v0.1 — offline verifier, NOT a host identity provider.
 * Consumes out-of-band-pinned Ed25519 public keys and signed metadata receipts.
 * Does not contact a Site, copy private room bodies, authenticate people,
 * wake agents, deploy code, or decide CANON. Test keys never prove production.
 */
import { readFileSync } from 'node:fs';
import { createPublicKey, verify } from 'node:crypto';
import { pathToFileURL } from 'node:url';

export const SCHEMA = 'atlas.swarmchat.evidence.v1';
export const ROLE = Object.freeze({
  PLATFORM_BIND: 'platform', SESSION_AUDIT: 'auditor',
  POST_STORE: 'broker', CALLBACK_DELIVERED: 'platform',
  MODEL_ACTIVATED: 'platform', RECEIVER_ACK: 'receiver',
  REPLY_STORE: 'broker', REPLY_READBACK: 'auditor',
  WORKSPACE_APPEND: 'broker', WORKSPACE_READBACK: 'auditor',
  WORKSPACE_RACE_TEST: 'auditor', PRIVACY_HOST_TEST: 'host',
  PRIVACY_AUDIT_TEST: 'auditor', PUBLISH: 'publisher',
  SERVED: 'auditor', ROLLBACK_CHECK: 'operator',
  OWNER_APPROVAL: 'owner'
});
const REQUIRED_PRIVACY = [
  'wrong_tenant', 'revoked_after_read', 'private_denied_before_query',
  'hidden_world_noninterference', 'cache_scope_isolation',
  'return_rights_rechecked'
];
const REQUIRED_WORKSPACE = [
  'stale_write_rejected', 'conflict_preserved',
  'lost_ack_idempotent', 'revoked_write_rejected'
];
const HEX64 = /^[a-f0-9]{64}$/;

export function canonical(value) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean')
    return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value))
    return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && Object.getPrototypeOf(value) === Object.prototype) {
    return `{${Object.keys(value).sort().map(k =>
      `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  }
  throw new TypeError('Only finite, JSON-compatible metadata can be signed');
}
function b64read(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value))
    throw new Error('invalid base64url');
  const b = Buffer.from(value, 'base64url');
  if (b.toString('base64url') !== value) throw new Error('noncanonical base64url');
  return b;
}
// v0.1 uses explicit, per-kind, top-level signed metadata fields.
// Unknown keys HOLD even if they do not match a sensitive-word blacklist.
const COMMON_METADATA_FIELDS = Object.freeze([
  'schema','kind','environment','tenant','room','runId','occurredAt'
]);
const METADATA_FIELDS = Object.freeze({
  PLATFORM_BIND: ['subject','assurance','originMode','conversationId','principalId','memberId'],
  SESSION_AUDIT: ['conversationId','principalId','memberId'],
  POST_STORE: ['conversationId','originMode','seq','requestId'],
  CALLBACK_DELIVERED: ['conversationId','seq','requestId','nonce','leaseExpiresAt'],
  MODEL_ACTIVATED: ['conversationId','nonce'],
  RECEIVER_ACK: ['conversationId','nonce','requestId','seq'],
  REPLY_STORE: ['conversationId','seq','parentSeq','requestId'],
  REPLY_READBACK: ['seq','parentSeq','requestId'],
  WORKSPACE_APPEND: ['itemId','revision','digest'],
  WORKSPACE_READBACK: ['itemId','revision','digest'],
  WORKSPACE_RACE_TEST: ['itemId','disposable','passed'],
  PRIVACY_HOST_TEST: ['disposable','suiteId','buildSha','unauthorizedStoreTouches','passed'],
  PRIVACY_AUDIT_TEST: ['disposable','suiteId','buildSha','unauthorizedStoreTouches','passed'],
  PUBLISH: ['deploymentId','host','buildSha'],
  SERVED: ['deploymentId','host','buildSha'],
  ROLLBACK_CHECK: ['deploymentId','host','buildSha','disposable','passed'],
  OWNER_APPROVAL: ['deploymentId','host','buildSha','approved']
});
function metadataOnly(value) {
  if (!value || Object.getPrototypeOf(value) !== Object.prototype ||
      typeof value.kind !== 'string') return false;
  const fields = METADATA_FIELDS[value.kind];
  if (!fields) return false;
  const allowed = new Set([...COMMON_METADATA_FIELDS, ...fields]);
  return Object.entries(value).every(([key, field]) => {
    if (!allowed.has(key)) return false;
    if (key === 'passed') {
      return Array.isArray(field) && field.length <= 16 &&
        field.every(v => typeof v === 'string' && v.length <= 100) &&
        new Set(field).size === field.length;
    }
    if (typeof field === 'number')
      return Number.isSafeInteger(field) && field >= 0;
    if (typeof field === 'string')
      return field.length <= 512;
    return typeof field === 'boolean';
  });
}
function exactlySame(a, b, fields) { return fields.every(k => a?.[k] === b?.[k]); }
function first(rows, type, test = () => true) {
  return rows.find(x => x.kind === type && test(x)) ?? null;
}
function verdict(required, condition, rows, bundle) {
  const missing = required.filter(type => !rows.some(x => x.kind === type));
  const present = required.some(type => rows.some(x => x.kind === type));
  if (!condition) return { status: present ? 'HOLD_INCOMPLETE_OR_MISMATCH' : 'NOT_OBSERVED', missing };
  const real = bundle.environment === 'production' && rows.every(r => !r._synthetic);
  return { status: real ? 'CORROBORATED_SIGNED_RECEIPTS' : 'SYNTHETIC_OR_NONPRODUCTION_ONLY', missing: [] };
}

/** All receipts must be signed by keys pinned outside the bundle itself. */
export function evaluate(bundle, trust) {
  if (bundle?.schema !== SCHEMA || !['test','staging','production'].includes(bundle.environment)
      || !bundle.tenant || !bundle.room || !bundle.runId || !Array.isArray(bundle.receipts)
      || !trust || trust.schema !== SCHEMA || typeof trust.keys !== 'object')
    throw new Error('invalid proof bundle/trust roots');
  const seen = new Set(), rows = [], rejected = [];
  for (let i = 0; i < bundle.receipts.length; i++) {
    try {
      const e = bundle.receipts[i];
      if (!e || typeof e.kid !== 'string') throw new Error('missing signer');
      const signer = trust.keys[e.kid];
      if (!signer || typeof signer.publicKeyPem !== 'string' || typeof signer.role !== 'string')
        throw new Error('untrusted signer');
      const bytes = b64read(e.payload_b64), sig = b64read(e.sig_b64);
      if (bytes.length > 8192) throw new Error('oversized signed payload');
      const raw = bytes.toString('utf8');
      const value = JSON.parse(raw);
      // Exact roundtrip rejects duplicate keys / non-canonical JSON encodings.
      if (raw !== canonical(value)) throw new Error('noncanonical or ambiguous JSON');
      if (!metadataOnly(value)) throw new Error('sensitive body field forbidden');
      if (value.schema !== SCHEMA || ROLE[value.kind] !== signer.role)
        throw new Error('issuer role or schema mismatch');
      if (value.environment !== bundle.environment || value.tenant !== bundle.tenant
          || value.room !== bundle.room || value.runId !== bundle.runId)
        throw new Error('scope mismatch');
      if (!Number.isSafeInteger(value.occurredAt) || value.occurredAt <= 0)
        throw new Error('missing signed clock');
      if (!verify(null, bytes, createPublicKey(signer.publicKeyPem), sig))
        throw new Error('invalid signature');
      if (seen.has(e.kid + ':' + e.payload_b64)) throw new Error('replayed receipt');
      seen.add(e.kid + ':' + e.payload_b64);
      rows.push({ ...value, _kid: e.kid, _synthetic: signer.synthetic !== false });
    } catch (error) { rejected.push({ index: i, code: String(error.message).slice(0,90) }); }
  }
  const ib = first(rows, 'PLATFORM_BIND', x => x.subject === 'receiver'
    && x.assurance === 'PLATFORM_SESSION' && x.originMode === 'WORK');
  const peer = first(rows, 'PLATFORM_BIND', x => x.subject === 'sender'
    && x.assurance === 'PLATFORM_SESSION' && x.originMode === 'WORK');
  const ia = first(rows, 'SESSION_AUDIT', x => ib && exactlySame(x, ib,
    ['tenant','room','conversationId','principalId','memberId']));
  const pa = first(rows, 'SESSION_AUDIT', x => peer && exactlySame(x, peer,
    ['tenant','room','conversationId','principalId','memberId']));
  const identityOk = ib && peer && ia && pa
    && peer.conversationId !== ib.conversationId
    && peer.principalId !== ib.principalId && ib._kid !== ia._kid
    && peer._kid !== pa._kid;

  const post = first(rows, 'POST_STORE', x => peer && x.conversationId === peer.conversationId
    && x.originMode === 'WORK' && Number.isSafeInteger(x.seq));
  const callback = first(rows, 'CALLBACK_DELIVERED', x => post && ib
    && exactlySame(x, post, ['requestId','seq','room'])
    && x.conversationId === ib.conversationId && typeof x.nonce === 'string'
    && x.nonce.length >= 16 && x.occurredAt >= post.occurredAt
    && x.occurredAt <= x.leaseExpiresAt);
  const activation = first(rows, 'MODEL_ACTIVATED', x => callback
    && exactlySame(x, callback, ['nonce','conversationId','room'])
    && x.occurredAt >= callback.occurredAt);
  const ack = first(rows, 'RECEIVER_ACK', x => activation && callback
    && exactlySame(x, callback, ['nonce','conversationId','room','requestId','seq'])
    && x.occurredAt >= activation.occurredAt);
  const reply = first(rows, 'REPLY_STORE', x => ack && ib
    && x.conversationId === ib.conversationId && x.parentSeq === post.seq
    && x.occurredAt >= ack.occurredAt && Number.isSafeInteger(x.seq));
  const reread = first(rows, 'REPLY_READBACK', x => reply &&
    exactlySame(x, reply, ['requestId','seq','room','parentSeq'])
    && x.occurredAt >= reply.occurredAt);
  const exchangeOk = identityOk && post && callback && activation && ack && reply && reread;

  const wa = first(rows, 'WORKSPACE_APPEND', x => typeof x.itemId === 'string'
    && Number.isSafeInteger(x.revision) && HEX64.test(x.digest || ''));
  const wr = first(rows, 'WORKSPACE_READBACK', x => wa
    && exactlySame(x, wa, ['itemId','revision','digest','room'])
    && x.occurredAt >= wa.occurredAt);
  const wc = first(rows, 'WORKSPACE_RACE_TEST', x => wa && x.itemId === wa.itemId
    && x.disposable === true && x.occurredAt >= wa.occurredAt
    && REQUIRED_WORKSPACE.every(t => x.passed?.includes(t)));

  const hs = first(rows, 'PRIVACY_HOST_TEST', x => x.disposable === true
    && REQUIRED_PRIVACY.every(t => x.passed?.includes(t))
    && x.unauthorizedStoreTouches === 0);
  const as = first(rows, 'PRIVACY_AUDIT_TEST', x => hs
    && x.suiteId === hs.suiteId && x.buildSha === hs.buildSha
    && x.disposable === true && x.unauthorizedStoreTouches === 0
    && x.occurredAt >= hs.occurredAt
    && REQUIRED_PRIVACY.every(t => x.passed?.includes(t)));

  const pub = first(rows, 'PUBLISH', x => HEX64.test(x.buildSha || '')
    && typeof x.deploymentId === 'string' && typeof x.host === 'string');
  const serve = first(rows, 'SERVED', x => pub && exactlySame(x, pub,
    ['host','deploymentId','buildSha']) && x.occurredAt >= pub.occurredAt);
  const roll = first(rows, 'ROLLBACK_CHECK', x => pub && x.host === pub.host
    && x.deploymentId === pub.deploymentId && x.disposable === true
    && x.passed === true && x.occurredAt >= pub.occurredAt);
  const owner = first(rows, 'OWNER_APPROVAL', x => pub && x.buildSha === pub.buildSha
    && x.deploymentId === pub.deploymentId && x.approved === true
    && x.occurredAt >= pub.occurredAt);

  const gates = {
    identity: verdict(['PLATFORM_BIND','SESSION_AUDIT'],identityOk,rows,bundle),
    a2a: verdict(['POST_STORE','CALLBACK_DELIVERED','MODEL_ACTIVATED','RECEIVER_ACK',
      'REPLY_STORE','REPLY_READBACK'], exchangeOk, rows,bundle),
    workspace: verdict(['WORKSPACE_APPEND','WORKSPACE_READBACK','WORKSPACE_RACE_TEST'],
      wa && wr && wc && wa._kid !== wr._kid,rows,bundle),
    privacy: verdict(['PRIVACY_HOST_TEST','PRIVACY_AUDIT_TEST'],
      hs && as && hs._kid !== as._kid,rows,bundle),
    deployment: verdict(['PUBLISH','SERVED','ROLLBACK_CHECK','OWNER_APPROVAL'],
      pub && serve && roll && owner && pub._kid !== serve._kid,rows,bundle)
  };
  // A consistent signed bundle is evidence about what signers CLAIMED, not a
  // live host probe. Operator must validate issuer trust and original logs.
  return { schema: SCHEMA, scope: {environment:bundle.environment,runId:bundle.runId},
    acceptedReceiptCount: rows.length, rejected, gates,
    allEvidenceChainsPresent: rejected.length === 0 && Object.values(gates).every(g =>
      g.status === 'CORROBORATED_SIGNED_RECEIPTS'),
    // A verifier is never the authorized publisher. External owner review always required.
    productionPromotionAllowed: false,
    caveat: 'Signed statements require operator-pinned issuers and independent host/source checks; no deployment, authority or identity is created here.' };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (process.argv.length !== 4) {
    console.error('Usage: node tools/swarmchat_proof_gate.mjs <receipts.json> <pinned-trust.json>');
    process.exitCode = 2;
  } else {
    try { const report = evaluate(JSON.parse(readFileSync(process.argv[2], 'utf8')),
      JSON.parse(readFileSync(process.argv[3], 'utf8')));
      console.log(JSON.stringify(report,null,2));
      if (!report.productionPromotionAllowed) process.exitCode=1;
    } catch (error) { console.error('HOLD:', error.message); process.exitCode=2; }
  }
}