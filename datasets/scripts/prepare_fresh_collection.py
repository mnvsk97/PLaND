#!/usr/bin/env python3
"""Prepare one approved fresh dataset, excluding recorded historical exposure."""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = Path('/Users/saikrishna/dev/deterministic-skills')
EARLIER = Path('/Users/saikrishna/.codex/worktrees/7f06/deterministic-skills')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def historical_exposure(roots, dataset):
    """Include aggregate-only pilot identities and interrupted fresh runs."""
    opened, evidence, seen = set(), [], set()
    suffix = 'email-classification' if dataset == 'spamassassin' else 'text-classification'
    for root in roots:
        experiment = root/f'experiments/{dataset}-{suffix}'
        paths = list((experiment/'results').rglob('*.json'))
        paths += list((root/'tmp').glob(f'fresh-paper-*/runs/{dataset}/*.json'))
        subset = experiment/'paper-subset.json'
        if subset.is_file() and (experiment/'results/summary.json').is_file():
            paths.append(subset)
        for path in sorted(paths):
            digest = sha(path)
            if digest in seen:
                continue
            seen.add(digest)
            value = json.loads(path.read_text())
            if not isinstance(value, dict):
                continue
            cases = value.get('selected', []) if path == subset else value.get('cases', [])
            if not isinstance(cases, list):
                continue
            ids = {str(c.get('id', c.get('case_id'))) for c in cases
                   if isinstance(c, dict) and (c.get('id') or c.get('case_id'))}
            if ids:
                opened.update(ids)
                item = {'path': str(path), 'sha256': digest, 'cases': len(ids)}
                if path == subset:
                    summary = experiment/'results/summary.json'
                    item['execution_evidence'] = {'path': str(summary), 'sha256': sha(summary)}
                evidence.append(item)
    return opened, evidence

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    dataset, = plan['datasets']
    if args.output.exists():
        raise ValueError('output already exists')
    sources = {
        'ledgar': MAIN/'tmp/enterprise-datasets/ledgar/sources',
        'cfpb': MAIN/'tmp/confirmatory-datasets/cfpb/sources',
        'spamassassin': MAIN/'tmp/enterprise-datasets/spamassassin/sources',
    }
    source = sources[dataset]
    lock = json.loads((ROOT/'datasets/sources.lock.json').read_text())
    custody = []
    for item in lock['sources'][dataset]['files']:
        path = source/Path(item['path']).name
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise ValueError(f'source custody failed: {path}')
        custody.append({'path': str(path), 'sha256': item['sha256'], 'bytes': item['bytes']})

    original = MAIN/f'tmp/confirmatory-datasets/{dataset}'
    later = EARLIER/f'tmp/quality-first-datasets/{dataset}'
    opened = set()
    for directory, splits in [(original, {'development','validation','test'} if dataset == 'ledgar'
                               else {'development','validation'}),
                              (later, {'development','validation'})]:
        with (directory/'evals.csv').open() as handle:
            opened.update(r['id'] for r in csv.DictReader(handle) if r['split'] in splits)
    historical, evidence = historical_exposure([ROOT, MAIN, EARLIER], dataset)
    opened.update(historical)

    lookup = {}
    prior_paths = []
    for root in [MAIN/'tmp', EARLIER/'tmp', ROOT/'tmp']:
        for path in sorted(root.rglob('evals.csv')):
            if dataset not in str(path):
                continue
            prior_paths.append({'path': str(path), 'sha256': sha(path)})
            with path.open() as handle:
                for row in csv.DictReader(handle):
                    if row['id'] in opened:
                        data = (path.parent/row['input']).resolve()
                        if data.is_file():
                            lookup[row['id']] = dict(row, input=str(data))
    missing = opened-set(lookup)
    if missing:
        raise ValueError(f'Cannot recover prior opened input identities: {sorted(missing)[:10]}')
    exclusions = args.output.with_name(args.output.name+'-prior-opened')
    if exclusions.exists():
        raise ValueError(f'exclusions already exist: {exclusions}; inspect previous attempt')
    exclusions.mkdir(parents=True)
    with (exclusions/'evals.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['id','split','input','output'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(lookup[k] for k in sorted(lookup))
    command = [sys.executable, str(ROOT/'datasets/scripts/prepare_data.py'), dataset,
               '--output', str(args.output), '--source', str(source/'complaints-api.json' if dataset == 'cfpb' else source),
               '--labels-from', str(original/'selection.json'), '--exclude-dataset', str(exclusions),
               '--seed', str(plan['seeds']['dataset']), '--development-cases', '500',
               '--validation-cases', '1000', '--test-cases', '500']
    print(json.dumps({'argv': command}), flush=True)
    subprocess.run(command, check=True, cwd=ROOT)
    receipt = {'source_custody': custody, 'prior_opened_cases': len(opened),
               'historical_runs': evidence, 'prior_dataset_index': prior_paths,
               'exclusions_evals_sha256': sha(exclusions/'evals.csv'),
               'plan_sha256': sha(args.plan), 'evals_sha256': sha(args.output/'evals.csv'),
               'selection_sha256': sha(args.output/'selection.json'),
               'splits': plan['splits'], 'seed': plan['seeds']['dataset']}
    (args.output/'freshness-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
