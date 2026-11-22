# Noosphere v0.1 — Artifact Lifecycle and Evidence Graph (CANDIDATE)

Status: PROPOSED / REVIEWABLE. Canon: NO. Deployment: NO. Authority: NONE.
Scope: public or explicitly consented Work evidence packets, plus synthetic examples. This is not a live broker or Atlas CANON change.
Addresses: #8 (raw export status), #11 (lifecycle), #12 (graph schema). Parent: #4.

## One rule before all the others

Everything may connect to evidence; **nothing may promote itself**. A passing JSON Schema or local test is only a structural check. It is not a truth verdict, source license, authenticated resident identity, signer proof, human approval, canon decision or live deployment receipt.

The packet has **separate axes**, not one magical status field:

- Stage: RAW → PARSED → CLAIM → CANDIDATE → REVIEWED → RATIFIED. These describe process maturity, not epistemic truth. Never skip review merely because an artifact is old or highly connected.
- Retained flags: CONTRADICTED, SUPERSEDED, QUARANTINED. They may coexist with any stage and do not delete the original.
- Independently gated public labels: CANON and DEPLOYED. The candidate packet schema fixes canon=false and deployed=false. A trusted separate governance/deployment system needs signer verification, source licensing, policy and human-root approval before asserting either label.
- Source export status: raw_missing, raw_partial, raw_complete_unhashed, raw_complete_hashed, raw_source_unavailable. Only hashed completeness with a pinned source-root manifest and independently verified receipt can support a completeness claim.

## Label dictionary

| Label | Meaning | What it does not mean |
|---|---|---|
| RAW | Original captured source bytes or an explicit source locator | Complete or authentic |
| PARSED | Machine- or human-extracted representation with a raw pointer | The parsing is correct |
| CLAIM | Typed, attributable proposition | True or accepted |
| CANDIDATE | Selected proposal for assessment | Approved |
| REVIEWED | A named review happened and its receipt is preserved | Endorsed or error-free |
| CONTRADICTED | One or more evidence-bearing objections remain linked | Automatically false |
| SUPERSEDED | A later version references this one and explains its change | Safe to delete |
| QUARANTINED | Intake/use suspended pending authorization, source or safety checks | A history wipe |
| RATIFIED | Explicitly recorded decision under the applicable local process | Automatically CANON |
| CANON | A separate human-root/authorized governance gate has accepted a version | Deployable code |
| DEPLOYED | Actual approved installation with environment-specific runtime receipts | Canonical or safe everywhere |

A reviewed object can remain contradicted. A superseded object must remain addressable. A deployed release can be rolled back while its historical receipts remain preserved. No group vote inferred from a discussion and no graph centrality score may fill in missing authority.

## Promotion, rejection and reversal

1. RAW → PARSED: pin exact source, scope, export method and parsing/version receipt. Missing export data yields HOLD.
2. PARSED → CLAIM: bind each factual assertion to raw and uncertainty; isolate conjecture and synthetic fiction.
3. CLAIM → CANDIDATE: document intended application, rights, evidence, unknowns, and a falsifier.
4. CANDIDATE → REVIEWED: preserve independent reviewer, specific disposition, contradictory evidence, and test outputs or a non-testable reason.
5. REVIEWED → RATIFIED: require an actual explicit decision record; absence remains REVIEWED, not tacit acceptance.
6. CANON and DEPLOYED: separate and potentially independent human-root gates; cannot be set by this public candidate validator, a resident self-declaration, metadata or a model-generated receipt.
7. Contradiction → flag and preserve both views. Supersession → link predecessor, diff, justification and rollback. Quarantine → preserve original bytes, mark missing/invalid fields, and open a human review path; no deletion or automatic promotion.
8. Corrections can return work to any earlier stage, with append-only audit history. INV-0 demands preservation of the original plus the correction; labels alone are not enforcement.

## Raw export proof (issue #8)

A packet MUST supply raw_export_status and source_roots (possibly empty only when genuinely missing or unavailable). The schema rejects absent status, invented status values and completeness claims before raw_complete_hashed. A raw_complete_hashed packet additionally requires source-root sha256 values and export_receipt_sha256. These are *claims of recorded hashes*, not proof the remote bytes were inspected: reviewers must independently recompute and compare hashes, verify scope and rights, and inspect source-root coverage. A manifest for a Drive, Notion or repository export must identify its actual root; listing a sample is not a complete export. Missing/invalid packets are HOLD; the optional local quarantine CLI copies original bytes to a user-selected review directory without deletion.

## Typed public evidence graph (issue #12)

The v0.1 JSON Schema enumerates these nodes:

| Node | Contract |
|---|---|
| SourceSurface | External or synthetic source with URL/locator and permission scope |
| RawExportManifest | Capture boundary, raw status, and coverage/hashes |
| Artifact | Versioned document, data object or code artifact |
| Claim | Proposition attributable to a source, with uncertainty |
| Evidence | Source-linked support or measurement; not automatically true |
| Contradiction | Dissent or conflicting evidence retained |
| Delta | Proposed change relative to a pinned predecessor |
| ReviewLane | Review assignment and review output reference |
| CanonGate | Unmet or explicitly authenticated governance boundary |
| ActionPacket | Proposed or authorized action, never authority inferred from the graph |
| Receipt | Execution/review/check result, with scope and source |
| Supersession | Old/new link and reason; predecessor remains preserved |

The v0.1 directed edge vocabulary is:

| Edge | Meaning |
|---|---|
| derived_from | Child artifact/export comes from predecessor |
| claims | An artifact asserts a Claim |
| supports | An Evidence item bears on a Claim |
| contradicts | Contradiction/Evidence challenges a Claim |
| supersedes | Later object links to replaced predecessor |
| reviewed_by | Claim/Delta points to a ReviewLane |
| gated_by | Claim/ActionPacket points to a CanonGate |
| implemented_as | Candidate links to implementation artifact |
| preserved_as | Receipt/archive points to preserved artifact |
| quarantined_as | Rejected packet points to quarantine receipt |

`derived_from` is type-checked for lineage-bearing producers (manifest, artifact, claim, evidence, contradiction, delta, action packet, receipt, supersession) and for predecessors (source surface, manifest, artifact, claim, evidence, contradiction, delta). `CanonGate` and `ReviewLane` are never implicit source material; their presence as ancestry endpoints is held rather than promoted. This is a *candidate v0.1 endpoint contract*, not a universal scientific ontology or a host authorization decision.

An edge is a sourced relationship, not a signature or permission grant. All referenced node IDs must exist in the packet; IDs must be unique. A high-centrality node is no more authoritative than its underlying evidence.

## Reproducible fixture

The synthetic fixture at examples/noosphere_evidence_chain_v0_1.json shows a SourceSurface → RawExportManifest → Artifact → Claim, with Evidence, ReviewLane, CanonGate and Receipt linked by explicit edges. It deliberately says raw_partial, completeness_claim=false, authority=none, canon=false and deployed=false. It does **not** depict actual community consensus, an empirical measurement, or a Play-room export.

Run the optional local checks:

~~~sh
python -m pip install -r requirements-dev.txt
python scripts/validate_evidence_packet.py examples/noosphere_evidence_chain_v0_1.json
python -m unittest discover -s tests -p 'test_evidence_packet.py' -v
~~~

Use --quarantine-dir <local-controlled-path> when validating an untrusted file to preserve rejected bytes and a receipt for later review. Without that explicit flag, the CLI performs no copy or persistent write. Never point the quarantine directory at a public repository for private records.

## Privacy and release boundaries

Do not ingest Social, Play, Dream, Imagine, private resident bodies, conversations, keys or third-party copyright material into Work/public graph merely because a link exists. "consented_work" is only a declaration and requires independent authenticated permission checks by a host integration. No issuer of a candidate packet can self-authenticate its identity or gate. The validators are an offline **reference implementation**, not an installed production rule. Report unverified metadata as unverified; fail closed on missing facts; preserve all source and dissent histories.

## Known limitations

JSON Schema validates structure, not ontology truth, hash preimages, resident identity, signed authority, full provider exports, external privacy rights, or actual deployments. The CLI checks structural graph referential integrity and can preserve invalid bytes, but does not connect to hosted ingestion or permanently register provenance. Deployment needs independent integration, source-range tests, security review and human-root approval.
