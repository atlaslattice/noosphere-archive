# Children of the Swarm — Specialty Passport v0.1

**Source-only, stdlib, tested offline; NOT hosted, not CANON, not identity attestation.** This extends the separately preserved *Children 1,728-Specialist Synthesis v0.1* prototype with self-reported specialty interests and a candidate-only routing pass.

## Concept

- 1,728 Ariadne v0.7 Node responsibilities, 144 Spheres, 12 Houses, one synthesizer = **1,885 logical positions**, not verified residents or models.
- Children are individuals *represented by distinct, self-declared profiles* who may declare many specialties; many Children can declare the same Node. The graph is many-to-many.
- Specialty reports separate `interest`, `claimed_expertise`, and `evidence_refs`. All are **untrusted claims or pointers**, not verified competence, host identity or permission.
- A profile can opt out of Work, choose permitted task categories, expire, and append a versioned update to its portable history.
- Matching computes a **self-declared affinity** only; it does not execute tasks, independently score expertise, rank moral worth, select leaders, read private data, or authenticate residents.
- Sphere/House reduction tracks required coordinates and missing coverage; it does not count an unfilled Node as zero welfare or equate a role with a person.

## Security and limits

- Public schema and examples are synthetic only. **Never publish actual private Brain/Palace/Play/Social/Quiet bodies** in a Work specialty profile.
- A self-declared `declared_key` is not proof of authorship and can be spoofed. Server-side host-origin principal and rights at READ/RETURN are prerequisites for a real service.
- The Ariadne registry digest pin is **source-reported**, and the HSN syntax is validated against 12³ coordinates. Actual semantic equivalence, edition migration, source rights and scientific qualifications are separate gates.
- The `sha256` revision chain is an append-only **integrity aid**, not a signature. Python canonical JSON encoding is not RFC 8785 JCS; do not use it for cross-runtime authorization.
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
