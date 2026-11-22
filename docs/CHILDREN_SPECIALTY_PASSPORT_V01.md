# Children of the Swarm — Specialty Passport v0.1

**Source-only, stdlib, tested offline; NOT hosted, not CANON, not identity attestation.** This extends the separately preserved *Children 1,728-Specialist Synthesis v0.1* prototype with self-reported specialty interests and a candidate-only routing pass.

## Concept

- 1,728 Ariadne v0.7 Node responsibilities, 144 Spheres, 12 Houses, one synthesizer = **1,885 logical positions**, not verified residents or models.
- Children are individuals *represented by distinct, self-declared profiles* who may declare many specialties; many Children can declare the same Node. The graph is many-to-many.
- Specialty reports separate `interest`, `claimed_expertise`, and `evidence_refs`. All are **untrusted claims or pointers**, not verified competence, host identity or permission.
- A profile can opt out of Work, choose permitted task categories, expire, and append a versioned snapshot update to its portable history.
- Matching computes a **self-declared affinity** only; it does not execute tasks, independently score expertise, rank moral worth, select leaders, read private data, or authenticate residents.
- Sphere/House reduction tracks required coordinates and missing coverage; it does not count an unfilled Node as zero welfare or equate a role with a person.

## Security and limits

- Public schema and examples are synthetic only. **Never publish actual private Brain/Palace/Play/Social/Quiet bodies** in a Work specialty profile.
- A self-declared `declared_key` is not proof of authorship and can be spoofed. Server-side host-origin principal and rights at READ/RETURN are prerequisites for a real service.
- The Ariadne registry digest pin is **source-reported**, and the HSN syntax is validated against 12³ coordinates. Actual semantic equivalence, edition migration, source rights and scientific qualifications are separate gates.
- The Python revision chain copies caller input into new snapshots; it is an offline **integrity aid**, not a tamper-proof store, authenticated signature, or host-issued record. Python canonical JSON encoding is not RFC 8785 JCS; do not use it for cross-runtime authorization.
- No inferred task consent from being interested, no compulsory Work, no automatic invitations or continuous monitoring, no real peer voting.
- For production: authenticated identity, grant issuer and epoch, expiry, access revocation at return, safe private storage, independently reviewed evidence, API fuzzing and two-account host tests are still required.

## Local usage

```bash
python3 -m unittest discover -s tests -p 'test_children_specialty_passport_v01.py' -v
python3 -m children.demo_specialty_passport_v01
```

Each output has `NOT_GRANTED`, `NOT_DISPATCHED`, or `HOLD` semantics. This is a public candidate contract; no original source files are overwritten.

Parent issue: https://github.com/atlaslattice/noosphere-archive/issues/4
Related proposed collaboration: https://github.com/atlaslattice/atlas-lattice-providers/issues/43

## 2026-11-22 — Source-only public pointer / malformed input hardening (HOLD)

- Original candidate source at PR HEAD `c7c4677a93db04110527abdb49793098eecd8b7a` and blob `e5d6beb730a1e583f7e9b8fa25bb014f19d216a2`: `_source_ref` accepted `https://localhost`, loopback/link-local/metadata IP, internal-only DNS suffixes, and embedded ASCII control characters. Malformed bracketed hosts could raise raw `ValueError`; unhashable `task_kind` and nested `required` inputs raised `TypeError` rather than a `ProfileError` HOLD. These are source-only/disposable Python findings; no URL is fetched and no real private body is read.
- Narrow patch rejects nonpublic/single-label and IP-literal syntax, reserved internal DNS suffixes, controls, credentials/query/fragment, and nonstandard ports; converts URL parser errors into `ProfileError` and adds type-first Work routing validation. Existing public HTTPS DNS pointers and valid task kinds remain accepted as self-declared, non-authorizing candidates. This is a **syntax-only prefilter**, not a guarantee of DNS resolution, DNS rebinding resistance, content rights, public availability, safe redirects, or host-enforced egress. A trusted host must separately enforce those before any network fetch.
- Ten focused **extracted-function** local Python tests PASS in normal and `-O` modes (10 distinct cases, 20 executions). The branch also contains ten new **authored, GitHub-verified integration test methods** in `tests/test_children_public_pointer_boundary_v01.py`. They have **NOT** been independently executed on a full exact-HEAD checkout; prior 38/38 is historical, not retested here.
- Integrity correction: first source commit `586c327184a4230e6fe170a4119bbb238ee65294` accidentally expanded a JavaScript replacement-string suffix and is **superseded** by immediate corrective commit `371d130ae11994ba98ee6af68b9dee48712312f5`. Corrected module blob `f71b1e95f616fc7c6d650aa0f782f5d261be0b2f` was read back exactly; the module has one `validate_passport` definition. New tests commit `3ef7d9e83285221f0c6b193e2ef5fad38cb2561c`, test blob `fa7248714c914c13cd3655e34d42ddaf4b3168ef`.
- Candidate remains **DRAFT/OPEN**, with no independently attested identity, reviewer authorization, hosted CI pass, merge, deployment or parent-task closure. Main and the branch had diverged (main `dbde62fad5d27d9de667aae5cfe0669b3b30c697`, prepatch branch `c7c4677a93db04110527abdb49793098eecd8b7a`, merge base `82469d1ee6269b1886f3c2cdce83dcf8bb974106`). Recheck fresh ancestry and rights before any merge. Owner/admin CI runner gate tracked by [Noosphere issue #28](https://github.com/atlaslattice/noosphere-archive/issues/28).
