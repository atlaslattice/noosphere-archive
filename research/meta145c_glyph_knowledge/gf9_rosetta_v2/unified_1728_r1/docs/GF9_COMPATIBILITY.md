# GF9 R2 compatibility and incremental gain

The current source-only GF9 R2 generator (`src/protocol.py` in the predecessor) remains untouched. `atlas1728/gf9_cache.py` accepts its `make_message` as an injected factory. It builds a locally frozen, structured packet cache for each original module/chapter pair. It verifies exact structural parity before retrieving, and checks the source digest and generator **code digest** again at every read.

Run `examples/benchmark_current_gf9.py` against the exact existing private original. The resulting numbers are CPU times for 1,728 GF9 mathematical packet requests, not a model, network, browser or hosted endpoint. The cached version reserializes JSON on retrieval and does not cache authorization or scientific judgments. Bytes can be compared to the original source-generated canonical packet for each coordinate. The first iteration bears the cold compilation cost; continued equivalent computation can amortize that cost.

A fast cache is only valid if the source edition, generator code and policy are unchanged. **No client may supply a host rights epoch and treat that as verified.** The host must enforce rights atomically at actual RETURN, independently of this library. Historical HSN/AXG1/GF7/KG8/GF9 names are separate namespaces; no automatic translations or host authority emerge from a matching coordinate suffix.
