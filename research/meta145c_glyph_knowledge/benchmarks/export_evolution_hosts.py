#!/usr/bin/env python3
"""Verify completed experiment/measurement artifacts and export native views.

Run only against explicitly selected companion source checkouts. This prepares
source files; it neither commits, pushes, deploys nor changes access controls.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.beast20.long_horizon import export_bundle, validate_report


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_module(name, value):
    return ('// Generated from verified artifacts by export_evolution_hosts.py.\n'
            'const freeze=x=>{if(x&&typeof x==="object"){for(const v of Object.values(x))freeze(v);Object.freeze(x);}return x;};\n'
            f'export const {name}=freeze({json.dumps(value, ensure_ascii=True, separators=(",", ":"))});\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--swarm-root', type=Path, required=True)
    parser.add_argument('--atlas-root', type=Path, required=True)
    args = parser.parse_args()
    folder = ROOT / 'benchmarks/native1728_evolution'
    manifest = json.loads((folder / 'LONG_HORIZON_MANIFEST.json').read_text())
    report_bytes = gzip.decompress((folder / 'LONG_HORIZON_REPORT.json.gz').read_bytes())
    if sha(report_bytes) != manifest['reportSha256']:
        raise ValueError('EVOLUTION_REPORT_HASH_MISMATCH')
    report = validate_report(json.loads(report_bytes))
    for field, path in [('engineSourceSha256', folder / 'engine.cpp'),
                        ('pythonSourceSha256', ROOT / 'src/beast20/long_horizon.py')]:
        if sha(path.read_bytes()) != report['execution'][field]:
            raise ValueError('EVOLUTION_IMPLEMENTATION_CHANGED')
    for filename, row in manifest['files'].items():
        if filename == 'LONG_HORIZON_REPORT.json':
            raw = report_bytes
        else:
            raw = (folder / filename).read_bytes()
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('EVOLUTION_ARTIFACT_HASH_MISMATCH')
    cascade_raw = (folder / 'CASCADE_UPGRADE_MEASURED.json').read_bytes()
    cascade = json.loads(cascade_raw)
    if cascade['schema'] != 'atlas.native1728.cascade-upgrade-measurement/v1' or cascade['repeats'] != 9:
        raise ValueError('MEASUREMENT_SCOPE_MISMATCH')
    expected_paths = {'benchmarks/bench_strategy1728.py', 'src/beast20/storage.py',
                      'src/beast20/execution.py', 'src/beast20/runtime.py', 'src/beast20/strategy_lab.py'}
    current = cascade['implementation_manifest']['candidate']
    if set(current) != expected_paths or any(sha((ROOT / path).read_bytes()) != digest for path, digest in current.items()):
        raise ValueError('MEASURED_IMPLEMENTATION_CHANGED')
    pairs = cascade['raw_pairs']
    if len(pairs) != 9 or any(pair['baseline']['output_sha256'] != pair['candidate']['output_sha256']
                             or pair['baseline']['counts'] != pair['candidate']['counts'] for pair in pairs):
        raise ValueError('MEASURED_OUTPUT_PARITY_FAILED')
    for lane in ('baseline', 'candidate'):
        if statistics.median(pair[lane]['elapsed_ns'] for pair in pairs) != cascade[lane + '_median_ns']:
            raise ValueError('MEASUREMENT_MEDIAN_MISMATCH')
    if cascade['baseline_median_ns'] / cascade['candidate_median_ns'] != cascade['measured_ratio_baseline_over_candidate']:
        raise ValueError('MEASUREMENT_RATIO_MISMATCH')
    implementation = {
        'schema': 'atlas.native1728.implementation-upgrade/v1',
        'status': 'IMPLEMENTED_AND_MEASURED_LOCALLY',
        'baselineSourceCommit': '2bea02211f93763bd753434676945c0f5bc7b8a7',
        'changes': [
            {'id': 'validated-scope-digest-cache', 'title': 'Reuse validated scope digests in a bounded 256-entry cache',
             'sourcePath': 'src/beast20/storage.py', 'sourceSha256': current['src/beast20/storage.py'],
             'preserved': 'Fresh scalar validation, source/edition/principal/rights/mode identity, authorization and per-read body integrity'},
            {'id': 'memo-expiry-index', 'title': 'Use an index for memo-expiry cleanup',
             'sourcePath': 'src/beast20/storage.py', 'sourceSha256': current['src/beast20/storage.py'],
             'preserved': 'Exact row counts, LRU counter/order, TTL boundary, transaction and migration behavior'},
        ],
        'cascade': cascade,
        'evidenceFiles': {
            'cascade': {'path': 'benchmarks/native1728_evolution/CASCADE_UPGRADE_MEASURED.json', 'sha256': sha(cascade_raw)},
            'storage': {'path': 'benchmarks/native1728_evolution/STORAGE_UPGRADE_MEASURED.json',
                        'sha256': sha((folder / 'STORAGE_UPGRADE_MEASURED.json').read_bytes())},
        },
        'scope': 'Python source implementation; measured local replay. Native hosts expose this evidence, not a hosted Python latency claim.',
        'hypothesisDisposition': {
            'memo-capacity': 'CURRENT_CONTROL_RETAINED_AND_REPLAYED',
            'batch-width': 'EXISTING_VERIFIED_BATCH_CONTROL_RETAINED',
            'workers': 'CURRENT_SERIAL_WORKER_CHOICE_RETAINED',
            'revision-invalidation': 'EXISTING_IMPLEMENTATION_AND_REGRESSIONS_RETAINED',
            'source-gate': 'EXISTING_HOST_FAILURE_PROPAGATION_RETAINED',
            'admission': 'SYNTHETIC_TOKEN_POLICY_ONLY_NOT_PROMOTED_TO_RUNTIME',
            'workload-partition': 'SEPARATE_REPRODUCIBLE_WORKLOAD_MEASUREMENTS_IMPLEMENTED',
            'scope-validation': 'IMPLEMENTED_AND_MEASURED_WITH_INTEGRITY_REGRESSIONS',
        },
        'limits': ['The long-horizon experiment retains the prior configuration; it establishes no additional configuration speedup.',
                   'The simulation generated no source patches or automatic promotions; storage changes were separately implemented and measured.',
                   'Nine full-cascade pairs include one slower candidate pair; all raw results remain available.',
                   'Small batch-control timing differences are not treated as general performance gains.'],
    }
    (folder / 'IMPLEMENTATION_UPGRADE.json').write_text(json.dumps(implementation, indent=2, sort_keys=True) + '\n')
    bundle = export_bundle(report)
    swarm = args.swarm_root.resolve(strict=True)
    atlas = args.atlas_root.resolve(strict=True)
    for root, project in [(swarm, 'appgprj_6af53c11e53481918824eabc8eede04a'),
                          (atlas, 'appgprj_6b02e16d290c8191a6c6405fc5227889')]:
        if json.loads((root / '.openai/hosting.json').read_text())['project_id'] != project:
            raise ValueError('COMPANION_SITE_IDENTITY_MISMATCH')
    swarm_file = swarm / 'lib/native1728-evolution-release.mjs'
    module = ('// Exact completed synthetic report, kept separate from the actual implementation measurement.\n'
              'export const native1728EvolutionBundle=Object.freeze(' + json.dumps(bundle, ensure_ascii=True, separators=(',', ':')) + ');\n'
              + source_module('native1728ImplementationEvidence', implementation))
    swarm_file.write_text(module, encoding='utf-8')
    # The actual companion adapter independently validates the full source index,
    # all hierarchy sums, selection and the exact frozen report before projection.
    code = ("import {pathToFileURL} from 'node:url';const base=process.argv[1];"
            "const {getEvolutionStatus}=await import(pathToFileURL(base+'/lib/native1728-evolution.mjs'));"
            "const {native1728EvolutionBundle,native1728ImplementationEvidence}=await import(pathToFileURL(base+'/lib/native1728-evolution-release.mjs'));"
            "process.stdout.write(JSON.stringify({...getEvolutionStatus(native1728EvolutionBundle),implementationEvidence:native1728ImplementationEvidence}));")
    projected = json.loads(subprocess.run(['node', '--input-type=module', '-e', code, str(swarm)],
                                         check=True, capture_output=True, text=True, timeout=60).stdout)
    projected['interface'] = 'https://swarmchat-private-broker-20261112.tdavesheldon.chatgpt.site/work/integration/evolution'
    atlas_file = atlas / 'librarian/hosting/native1728-evolution-evidence.mjs'
    atlas_file.write_text(source_module('native1728EvolutionEvidence', projected), encoding='utf-8')
    receipt = {'schema': 'atlas.native1728.host-export/v1', 'status': 'VERIFIED_SOURCE_EXPORTS',
               'reportSha256': bundle['reportSha256'], 'newHostOperations': 2,
               'swarm': {'path': 'lib/native1728-evolution-release.mjs', 'sha256': sha(swarm_file.read_bytes())},
               'atlas': {'path': 'librarian/hosting/native1728-evolution-evidence.mjs', 'sha256': sha(atlas_file.read_bytes())},
               'publicationPerformedByExporter': False, 'reportSchema': report['schema']}
    (folder / 'HOST_EXPORT_MANIFEST.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
