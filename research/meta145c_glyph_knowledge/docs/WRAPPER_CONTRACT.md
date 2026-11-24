# Atlas META145C reasoning wrapper / plugin-filter contract (GF8)

The intended architecture is **pre-processing + source-typed computations + bounded retrieval + post-processing + persistent external memory**. GPT receives a context packet and drafts a response; the underlying neural weights and system model do not change.

```text
AUTHENTICATED WORK REQUEST (provided by host, not model)
        |
        v
  Input boundary: human/project coordinates, source rights at READ
        |
        +--- Ariadne exact HSN snapshot (edition+SHA) -----------+
        +--- GF7 positional navigation -------------------------+ |
        +--- GF8 plate physics and lab-data comparator --------+  |
        +--- OpenAlex/Wikimedia evidence (revision+licensing) -+   |
        +--- Work-only external review-memory chain -----------+    |
        v                                                     |    |
  Bounded `prepare_reasoning_context` (untrusted DATA, not policy)   |
        |   numerical and provenance typed, no private modes             |
        v                                                               |
  Project LLM call (only after host authorization; not in this package) |
        |                                                               |
        v                                                               |
  `postflight_claim_gate` structured numerical/epistemic check         |
        |                                                               |
        v                                                               |
  Host READ+RETURN revocation, citations and release review  <---------+
        |
        v
  User-visible result; separate review note / explicit retraction to memory
```

## GF8 context contract

- `schema`: `atlas.gf8.reasoning-filter/v1` and canonical payload SHA-256.
- Source identity: exact original Ariadne v0.7 SHA-256 and HSN; GF7 remains a *positional analogy*; actual material/geometry and predicted frequency are distinct.
- Mathematical output: nearest computed plate eigenmode, driving frequency, damping, boundary assumptions, analytic status, no raw 2D grids in model prompt.
- Memory: only a SHA-linked pointer to external source-controlled Work-only review events; an event can change retrieval ordering, not accepted truth.
- Host: *must* independently check permissions at READ and RETURN, account scope and revocation; the local `LocalMemory.verify()` hash chain is not a digital signer or authenticated reviewer identity.
- Output checker: structured claim must match the independently computed numerical prediction and cannot call an unmeasured mode measured, approved or enacted. Free prose is not validated by this numerical checker.
- Privacy: reject Play, Social, Imagine, Dream, Quiet, Brain, Palace and untrusted personal source material by default; permit only consented Work research records in this interface.

## What appears as learning

1. A new licensed source or measured frequency changes **the retrieved context**, not the base model.
2. A corrected plate specification or boundary model changes **the numerical calculation**, not the base model.
3. An explicit reviewed event changes **candidate priority**, survives restart, and can be retracted without deleting the underlying source.
4. A constrained postflight checker stops numerical or status overclaims.
5. Over time, the *system* may deliver measurably better task answers, shorter prompts or faster retrieval, but these are observable application gains and must be benchmarked, not assumed.

This package contains **zero GPT calls, zero model training, zero live Plugin deployment, zero host subscriptions, zero CANON promotion, and zero resident identity grants**. It is source-only plugin-filter candidate code to integrate with the existing Atlas ONE publisher, not a parallel authorization or task scheduler.
