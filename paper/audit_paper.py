#!/usr/bin/env python3
"""Recompute the Gemini manuscript from saved cases; never call a model.

--write refreshes only marked numerical passages and the derived audit.
The default verifies them. --artifacts also verifies the rendered-file manifest.
Original collection outputs, plans, ledgers, and manifests are read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('experiments/gemini-3.5-flash-lite/2026-09-05-11-41-pm')
SPAM = Path('experiments/gemini-3.5-flash-lite/2026-09-06-01-10-am/spamassassin')
OUT = Path('experiments/gemini-3.5-flash-lite/2026-09-06-manuscript')
REPEATS = (20260903, 20260904, 20260905)
DATASETS = {'LEDGAR': BASE / 'ledgar-valid', 'CFPB': BASE / 'cfpb', 'SpamAssassin': SPAM}


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def close(a, b):
    if isinstance(a, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return math.isclose(a, b, abs_tol=1e-12, rel_tol=1e-12)


def quantile(values, q):
    values = sorted(values)
    x = (len(values) - 1) * q
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] * (hi - x) + values[hi] * (x - lo) if hi != lo else values[lo]


def intervals(pairs, samples, seed):
    # Independent implementation using primitive numbers, not stored correctness.
    differences = [int(h['actual'] == h['expected']) - int(b['actual'] == b['expected']) for b, h in pairs]
    bt = [b['total_tokens'] for b, _ in pairs]
    ht = [h['total_tokens'] for _, h in pairs]
    n = len(pairs)
    rng = random.Random(seed)
    quality = [sum(differences[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples)]
    rng = random.Random(seed + 1)
    tokens = []
    for _ in range(samples):
        bsum = hsum = 0
        for _ in range(n):
            i = rng.randrange(n)
            bsum += bt[i]
            hsum += ht[i]
        tokens.append((bsum - hsum) / bsum)
    return [quantile(quality, .025), quantile(quality, .975)], [quantile(tokens, .025), quantile(tokens, .975)]


def run_path(dataset, stage, repeat, arm):
    if dataset == 'LEDGAR':
        return BASE / 'ledgar/results' / f'valid-{stage}-repeat-{repeat}-{arm}.json'
    directory = BASE / 'spamassassin' if dataset == 'SpamAssassin' and stage == 'development' else DATASETS[dataset]
    return directory / 'results' / f'{stage}-repeat-{repeat}-{arm}.json'


def comparison_path(dataset, stage, repeat):
    directory = BASE / 'spamassassin' if dataset == 'SpamAssassin' and stage == 'development' else DATASETS[dataset]
    return directory / 'results' / f'{stage}-repeat-{repeat}-comparison.json'


def summarize(run):
    cases = run['cases']
    check(len({c['id'] for c in cases}) == len(cases), 'duplicate case ID')
    check(all(c['correct'] == (c['actual'] == c['expected']) for c in cases), 'stored correctness mismatch')
    check(all(c.get('parse_error') is None and c.get('step_trace', {}).get('command_error') is None for c in cases), 'case error')
    check(all(c['total_tokens'] == c['input_tokens'] + c['output_tokens'] for c in cases), 'case token mismatch')
    result = {'cases': len(cases), 'correct': sum(c['actual'] == c['expected'] for c in cases)}
    result['accuracy'] = result['correct'] / result['cases']
    for key in ('model_calls', 'input_tokens', 'output_tokens', 'total_tokens'):
        result[key] = sum(c[key] for c in cases)
    for key, value in result.items():
        check(close(value, run['summary'][key]), f'summary mismatch {key}')
    check(run['summary']['errors'] == {}, 'summary has errors')
    check(run['runtime']['seed_supported'] is False, 'inference-seed contract changed')
    check(run['runtime']['workers'] == 8, 'worker configuration changed')
    check(run['observed_providers'] == ['Google AI Studio'], 'provider changed')
    return result


def audit_pair(dataset, stage, repeat, plan):
    paths = [run_path(dataset, stage, repeat, arm) for arm in ('baseline', 'hybrid')]
    b, h = [read(p) for p in paths]
    for key in ('model', 'model_identity', 'runtime', 'invariants', 'evals_sha256', 'seed', 'split'):
        check(b[key] == h[key], f'{dataset} {stage}: invariant mismatch {key}')
    check(b['model_identity'] == plan['model']['identity'], 'plan model identity mismatch')
    bc, hc = ({c['id']: c for c in r['cases']} for r in (b, h))
    check(bc.keys() == hc.keys(), 'paired IDs differ')
    pairs = [(bc[i], hc[i]) for i in sorted(bc)]
    check(all(x['expected'] == y['expected'] for x, y in pairs), 'paired expected labels differ')
    bs, hs = summarize(b), summarize(h)
    expected_size = plan['splits'][{'development': 'development', 'selection': 'selection', 'final-test': 'final_test'}[stage]]
    check(bs['cases'] == hs['cases'] == expected_size, 'wrong case count')
    comparison = read(comparison_path(dataset, stage, repeat))
    reduction = (bs['total_tokens'] - hs['total_tokens']) / bs['total_tokens']
    accuracy_ci = token_ci = None
    if stage != 'development':
        accuracy_ci, token_ci = intervals(pairs, plan['acceptance']['bootstrap_samples'], plan['acceptance']['bootstrap_seed'])
        for key, value in [('accuracy_difference_bootstrap_95', accuracy_ci), ('token_reduction_bootstrap_95', token_ci)]:
            check(close(value, comparison['paired_statistics'][key]), f'{dataset} {stage} {repeat}: interval mismatch {key}')
        check(close(reduction, comparison['delta_hybrid_minus_nl']['token_reduction_fraction']), 'reduction mismatch')
    rules = [(x, y) for x, y in pairs if y['source'] == 'command']
    fallback = [(x, y) for x, y in pairs if y['source'] != 'command']
    check(all(y['model_calls'] == y['total_tokens'] == 0 for _, y in rules), 'command made model call')
    check(h['sop']['contract']['baseline_sop_sha256'] == b['sop_sha256'], 'fallback SOP changed')
    input_differences = [{'id': x['id'], 'baseline': x['input_tokens'], 'hybrid': y['input_tokens']}
                         for x, y in fallback if x['input_tokens'] != y['input_tokens']]
    acceptance = plan['acceptance']
    passed = (min(bs['accuracy'], hs['accuracy']) >= acceptance['quality_floor']
              and reduction >= acceptance['minimum_token_reduction'])
    if stage == 'development':
        assessment = read(comparison_path(dataset, stage, repeat).with_name(f'development-repeat-{repeat}-assessment.json'))
        check(passed and assessment['decision'] == 'eligible_for_validation' and not assessment['failed_checks'], 'development gate mismatch')
    else:
        passed = passed and accuracy_ci[0] >= -acceptance['noninferiority_margin'] - 1e-12 and token_ci[0] > 0
        check(passed == comparison['gate']['test_release_pass'], 'gate mismatch')
    routed_saved = sum(x['total_tokens'] - y['total_tokens'] for x, y in rules)
    fallback_saved = sum(x['total_tokens'] - y['total_tokens'] for x, y in fallback)
    check(routed_saved + fallback_saved == bs['total_tokens'] - hs['total_tokens'], 'mechanism total mismatch')
    return {'dataset': dataset, 'stage': stage, 'repeat': repeat, 'baseline': bs, 'hybrid': hs,
            'accuracy_difference': hs['accuracy'] - bs['accuracy'], 'accuracy_ci': accuracy_ci,
            'token_reduction': reduction, 'token_ci': token_ci, 'passed': passed,
            'command_cases': len(rules), 'command_precision': sum(y['correct'] for _, y in rules) / len(rules),
            'tokens_saved_by_bypass': routed_saved, 'tokens_saved_on_fallback': fallback_saved,
            'fallback_input_token_differences': input_differences,
            'baseline_sop_sha256': b['sop_sha256'], 'hybrid_sop_sha256': h['sop_sha256'],
            'classifier_sha256': h['sop']['classifier_sha256'], 'evals_sha256': b['evals_sha256'],
            'inputs': [{'path': str(p), 'sha256': sha(p)} for p in paths + [comparison_path(dataset, stage, repeat)]]}


def pct(x, digits=1):
    return f'{100*x:.{digits}f}'


def span(rows, key, digits=1, arm=None):
    values = [r[arm][key] if arm else r[key] for r in rows]
    lo, hi = pct(min(values), digits), pct(max(values), digits)
    return lo if lo == hi else f'{lo}–{hi}'


def mean_accuracy(rows, arm):
    """Descriptive mean of three same-split repeats, never a release gate."""
    check(len(rows) == len(REPEATS) and {r['repeat'] for r in rows} == set(REPEATS),
          'incomplete accuracy repeats')
    check(len({(r['dataset'], r['stage']) for r in rows}) == 1, 'mixed accuracy group')
    sizes = {r[arm]['cases'] for r in rows}
    check(len(sizes) == 1 and next(iter(sizes)) > 0, 'unequal or empty accuracy denominators')
    return math.fsum(r[arm]['correct'] / r[arm]['cases'] for r in rows) / len(rows)


def accuracy_summaries(rows):
    summaries = []
    for dataset, stage in dict.fromkeys((r['dataset'], r['stage']) for r in rows):
        group = [r for r in rows if (r['dataset'], r['stage']) == (dataset, stage)]
        summaries.append({'dataset': dataset, 'stage': stage, 'repeats': len(group),
                          'cases_per_repeat': group[0]['baseline']['cases'],
                          'baseline_mean_accuracy': mean_accuracy(group, 'baseline'),
                          'hybrid_mean_accuracy': mean_accuracy(group, 'hybrid')})
    return summaries


def passages(rows):
    def select(dataset, stage):
        return [r for r in rows if r['dataset'] == dataset and r['stage'] == stage]
    l, s, c = select('LEDGAR', 'final-test'), select('SpamAssassin', 'final-test'), select('CFPB', 'selection')
    blocks = {}
    blocks['abstract'] = (
        'Path to Least Non Determinism (PLaND) is an evaluation-driven methodology for replacing suitable language-model work with code. '
        'It starts with an English standard operating procedure (SOP). A host reasoning agent inspects development examples and execution records, proposes a revised SOP package, and tests whether an executable step can reduce model use while preserving quality within a stated tolerance. Unresolved inputs use the unchanged English baseline. '
        'We collected new LEDGAR, CFPB, and SpamAssassin subsets with 500 development, 1,000 selection, and 500 reserved final-test cases each. '
        'Each reached split received three paired baseline/hybrid executions using hosted Gemini 3.5 Flash Lite. Selection required both arms to reach 80% accuracy, a paired accuracy-interval lower bound of at least −2 percentage points, and at least 5% fewer tokens with a positive interval lower bound. '
        f'LEDGAR and SpamAssassin passed selection and final assessment in all repeats. Mean final-test accuracy across three runs changed from {pct(mean_accuracy(l,"baseline"),2)}% to {pct(mean_accuracy(l,"hybrid"),2)}% for LEDGAR, with {span(l,"token_reduction",2)}% fewer tokens. '
        f'SpamAssassin mean accuracy changed from {pct(mean_accuracy(s,"baseline"),2)}% to {pct(mean_accuracy(s,"hybrid"),2)}%, with {span(s,"token_reduction",2)}% fewer tokens. '
        f'CFPB hybrid mean selection accuracy was {pct(mean_accuracy(c,"hybrid"),2)}%; every run missed the floor, so its final test remained closed. '
        'Two provider-blocked selection emails were replaced under recorded amendments without reducing sample size. The study records package construction and evaluates frozen execution; it does not estimate autonomous discovery reliability across independent construction trials.'
    )
    blocks['selection_table'] = '| Dataset | Mean accuracy B → H (%) | Tokens saved (%) | Decision |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {d} | {pct(mean_accuracy(select(d,"selection"),"baseline"),2)} → {pct(mean_accuracy(select(d,"selection"),"hybrid"),2)} | {span(select(d,"selection"),"token_reduction",2)} | {"Accept" if all(r["passed"] for r in select(d,"selection")) else "Reject"} |' for d in DATASETS)
    blocks['final_table'] = '| Dataset | Mean accuracy B → H (%) | Calls B → H | Tokens saved (%) |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {d} | {pct(mean_accuracy(select(d,"final-test"),"baseline"),2)} → {pct(mean_accuracy(select(d,"final-test"),"hybrid"),2)} | {select(d,"final-test")[0]["baseline"]["model_calls"]} → {select(d,"final-test")[0]["hybrid"]["model_calls"]} | {span(select(d,"final-test"),"token_reduction",2)} |' for d in ('LEDGAR','SpamAssassin'))
    for name, group in [('ledgar', l), ('spam', s)]:
        r = group[0]
        blocks[f'{name}_result'] = (
            f'Across the three final-test executions, mean baseline accuracy was {pct(mean_accuracy(group,"baseline"),2)}%, and mean hybrid accuracy was {pct(mean_accuracy(group,"hybrid"),2)}%. '
            f'The rules answered {r["command_cases"]} of {r["baseline"]["cases"]} cases ({pct(r["command_cases"]/r["baseline"]["cases"])}%) without a model call. '
            f'Rule accuracy on those cases was {pct(r["command_precision"])}%. Total model-token use fell {span(group,"token_reduction",2)}%. '
            f'All three paired accuracy intervals stayed within the allowed lower bound; their lower endpoints were {", ".join(pct(x["accuracy_ci"][0]) for x in group)} percentage points. '
            'Every final-test comparison passed the recorded criteria.'
        )
    blocks['cfpb_result'] = (
        f'CFPB failed the absolute accuracy floor in every selection repeat. Across the three runs, mean baseline accuracy was {pct(mean_accuracy(c,"baseline"),2)}%, and mean hybrid accuracy was {pct(mean_accuracy(c,"hybrid"),2)}%. '
        f'The hybrid never reached the required 80%, despite reducing tokens by {span(c,"token_reduction",2)}%. Its paired accuracy intervals met the −2-point requirement, and its token intervals were positive. '
        'Those relative improvements could not compensate for failing the absolute floor. Selection rejection was terminal: no replacement candidate was created and the 500-case final test was not opened.'
    )
    blocks['mechanism'] = (
        'Fallback input-token counts matched the baseline on every corresponding final-test case. '
        f'In LEDGAR final-test repeat 1, the hybrid saved {l[0]["baseline"]["total_tokens"]-l[0]["hybrid"]["total_tokens"]:,} tokens: {l[0]["tokens_saved_by_bypass"]:,} from avoiding model calls and {l[0]["tokens_saved_on_fallback"]:,} from shorter model outputs on fallback cases. '
        f'In SpamAssassin final-test repeat 1, the corresponding amounts were {s[0]["baseline"]["total_tokens"]-s[0]["hybrid"]["total_tokens"]:,}, {s[0]["tokens_saved_by_bypass"]:,}, and {s[0]["tokens_saved_on_fallback"]:,} tokens. '
        'The measured savings therefore came almost entirely from bypassing model calls. They did not come from shortening the fallback prompt. '
        'For one SpamAssassin selection email, provider-reported input counts differed by '
        + ', '.join(str(abs(x['baseline']-x['hybrid'])) for r in rows for x in r['fallback_input_token_differences'])
        + ' tokens across the three pairs despite the unchanged prompt-construction contract. The saved receipts do not explain this small discrepancy; it is retained in the reported totals.'
    )
    blocks['repeat_table'] = '| Dataset and split | Run | Accuracy B → H (%) | Tokens B → H |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {r["dataset"]} {"selection" if r["stage"]=="selection" else "test"} | {REPEATS.index(r["repeat"])+1} | {pct(r["baseline"]["accuracy"])} → {pct(r["hybrid"]["accuracy"])} | {r["baseline"]["total_tokens"]:,} → {r["hybrid"]["total_tokens"]:,} |'
        for r in rows if r['stage'] != 'development')
    blocks['interval_table'] = '| Dataset and split | Run | Accuracy 95% interval (points) | Token saving 95% interval (%) |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {r["dataset"]} {"selection" if r["stage"]=="selection" else "test"} | {REPEATS.index(r["repeat"])+1} | [{pct(r["accuracy_ci"][0],2)}, {pct(r["accuracy_ci"][1],2)}] | [{pct(r["token_ci"][0],2)}, {pct(r["token_ci"][1],2)}] |'
        for r in rows if r['stage'] != 'development')
    blocks['development_table'] = '| Dataset | B attempts | H attempts | Mean accuracy B → H (%) |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {d} | 1 | {1 if d=="SpamAssassin" else 2} | {pct(mean_accuracy(select(d,"development"),"baseline"),2)} → {pct(mean_accuracy(select(d,"development"),"hybrid"),2)} |' for d in DATASETS)
    blocks['conclusion'] = (
        'PLaND provides a process for starting with English instructions, proposing executable replacements from development evidence, and accepting them only after a separate quality-and-token check. '
        f'In this study, LEDGAR and SpamAssassin passed selection and final assessment across all three paired executions, reducing final-test model tokens by {span(l,"token_reduction",2)}% and {span(s,"token_reduction",2)}%, respectively. '
        'CFPB failed the selection accuracy floor and did not proceed to final test. These results show that selective code execution can reduce model use under explicit quality limits, but that useful-looking rules do not always produce an acceptable workflow. Independent tests of the construction process and broader tasks are needed before making stronger claims.'
    )
    return blocks


def verify_index(path):
    index = read(path)
    for entry in index['files']:
        p = ROOT / entry['path']
        check(p.is_file(), f'missing {p}')
        check(p.stat().st_size == entry['bytes'] and sha(p) == entry['sha256'], f'hash mismatch {p}')
    return len(index['files'])


def write_index(path, paths):
    entries = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(set(paths))]
    (ROOT / path).write_text(json.dumps({'schema_version': 1, 'path_base': 'repository_root', 'files': entries}, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--artifacts', action='store_true')
    parser.add_argument('--freeze-artifacts', action='store_true')
    parser.add_argument('--freeze-evidence', action='store_true')
    args = parser.parse_args()
    if args.freeze_evidence:
        tracked = subprocess.check_output(['git', 'ls-files', '-z', 'experiments/gemini-3.5-flash-lite', 'experiments/collection', 'datasets/scripts', 'datasets/sources.lock.json', 'reproduce/uv.lock', 'reproduce/pyproject.toml', 'reproduce/.python-version', 'skills', '.codex/skills/pland-data-collection'], cwd=ROOT).decode().split('\0')
        paths = [ROOT / p for p in tracked if p and not p.startswith(str(OUT))]
        write_index(OUT / 'evidence-files.json', paths)
        print(f'Frozen {len(paths)} existing evidence/code files; no collection file changed.', flush=True)
        return
    if args.freeze_artifacts:
        paths = [ROOT/'paper'/f'PLaND.{ext}' for ext in ('md','docx','html','pdf')]
        paths += [ROOT/'paper/build_manuscript.py', ROOT/'paper/build_artifacts.cjs', ROOT/'paper/audit_paper.py',
                  ROOT/'paper/test_audit_paper.py', ROOT/'reproduce/verify.py', ROOT/'README.md']
        paths += [ROOT/OUT/name for name in ('manuscript.template.md', 'paper-calculations.json',
                  'evidence-files.json', 'provenance-addendum.md', 'review-response.md', 'visual-qa.json', 'finalize_artifacts.py')]
        paths += list((ROOT/'paper/figures').glob('*'))
        write_index(OUT / 'paper-artifacts.json', paths)
        print('Frozen rendered manuscript and builder hashes.', flush=True)
        return
    evidence_files = verify_index(OUT / 'evidence-files.json')
    plan = read(BASE / 'plan.json')
    check(plan['splits'] == {'development':500,'selection':1000,'final_test':500}, 'plan split changed')
    rows = []
    for dataset, directory in DATASETS.items():
        state = read(directory / 'collection-state.json')
        selection = state['decisions']['selection'][-1]['value']
        check(len(state['decisions']['baseline-development']) == 1, 'baseline attempt count changed')
        # Amendment controllers carry forward the frozen SpamAssassin package.
        check(len(state['decisions']['candidate-development']) == (1 if dataset == 'SpamAssassin' else 2), 'candidate attempt count changed')
        check(selection == ('reject' if dataset == 'CFPB' else 'accept'), 'selection decision changed')
        check(state['stages']['package-evidence'] == 'complete', 'evidence not packaged')
        stages = ['development', 'selection'] + ([] if selection == 'reject' else ['final-test'])
        if dataset == 'CFPB':
            check(state['stages']['final-test'] == 'pending', 'CFPB final test was opened')
            check(not list((ROOT/directory/'results').glob('final-test-repeat-*-baseline.json')), 'unexpected CFPB final outputs')
        for stage in stages:
            for repeat in REPEATS:
                rows.append(audit_pair(dataset, stage, repeat, plan))
            print(f'Checked {dataset} {stage}: three pairs' + (' and bootstrap intervals.' if stage != 'development' else ' and development assessments.'), flush=True)
    payload = {'schema_version':1, 'source_commit':'4ad24c9838922b3db777ac4ba4dbc34de7a449ae',
               'plan_sha256':sha(BASE/'plan.json'), 'model_identity':plan['model']['identity'],
               'evidence_files_verified':evidence_files, 'case_pairs':sum(r['baseline']['cases'] for r in rows),
               'paired_runs':len(rows), 'runs':rows,
               'accuracy_aggregation':'arithmetic mean of three per-run accuracies; descriptive only, not a gate',
               'accuracy_summaries':accuracy_summaries(rows)}
    target = ROOT/OUT/'paper-calculations.json'
    source = ROOT/'paper/PLaND.md'
    text = (ROOT/OUT/'manuscript.template.md').read_text()
    for name, content in passages(rows).items():
        pattern = rf'(<!-- audit:{name} -->\n).*?(\n<!-- /audit:{name} -->)'
        check(len(re.findall(pattern, text, flags=re.S)) == 1, f'missing or duplicate numeric block {name}')
        new = re.sub(pattern, lambda m:m[1]+content+m[2], text, flags=re.S)
        text = new
    check('qwen3:14b' not in text and 'f9aa707' not in text, 'stale historical results')
    if args.write:
        source.write_text(text)
        target.write_text(json.dumps(payload, indent=2)+'\n')
    else:
        check(source.read_text() == text, 'manuscript differs from audited template and calculations')
        check(read(target) == payload, 'saved calculations are stale')
    if args.artifacts:
        count = verify_index(OUT/'paper-artifacts.json')
        check(f'name="source-sha256" content="{sha(source)}"' in (ROOT/'paper/PLaND.html').read_text(), 'HTML source mismatch')
        with zipfile.ZipFile(ROOT/'paper/PLaND.docx') as docx:
            check(sha(source) in docx.read('docProps/core.xml').decode(), 'Word source mismatch')
        qa = read(OUT/'visual-qa.json')
        check(qa['pdf_sha256'] == sha(ROOT/'paper/PLaND.pdf') and qa['docx_sha256'] == sha(ROOT/'paper/PLaND.docx'), 'visual QA is stale')
        check(qa['passed'] and sorted(qa['reviewed_pages']) == list(range(1, qa['pages']+1)), 'incomplete visual QA')
        print(f'Checked {count} manuscript artifact/source hashes.', flush=True)
    print(f'PASS: {len(rows)} paired runs; {payload["case_pairs"]:,} paired cases; {evidence_files} evidence/code files.', flush=True)


if __name__ == '__main__':
    main()
