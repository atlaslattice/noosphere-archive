# SwarmChat proof-gate sidecar v0.1

No network, no privileged actions, no private source import. **This is not the hosted SwarmChat implementation.**

```bash
node --test tests/swarmchat_proof_gate.test.mjs
node tools/swarmchat_proof_gate.mjs disposable-proof.json pinned-trust.json
```

The CLI exit codes are: `1` for all evidence bundles that do not independently authorize a release (the expected result here); `2` for malformed input. `productionPromotionAllowed` stays false by design, even if every signer claim is present; only an external release process can approve promotion. The source tree contains no private keys or real-world room content.

See [operational runbook](docs/SWARMCHAT_PROOF_GATE_v01.md). All branch, release, broker, identity, privacy and hosted deployment changes remain human-gated. Synthetic tests do not establish platform capability.