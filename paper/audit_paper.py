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
BASE = Path('experiments/gemini-3.5-flash-lite/2026-09-05-study')
SPAM = BASE / 'spamassassin/amendment-02-final'
OUT = BASE / 'manuscript'
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
    directory = BASE / 'spamassassin/initial' if dataset == 'SpamAssassin' and stage == 'development' else DATASETS[dataset]
    return directory / 'results' / f'{stage}-repeat-{repeat}-{arm}.json'


def comparison_path(dataset, stage, repeat):
    directory = BASE / 'spamassassin/initial' if dataset == 'SpamAssassin' and stage == 'development' else DATASETS[dataset]
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


def mean_token_reduction(rows):
    """Descriptive mean of the three per-run token reductions."""
    check(len(rows) == len(REPEATS) and {r['repeat'] for r in rows} == set(REPEATS),
          'incomplete token-reduction repeats')
    check(len({(r['dataset'], r['stage']) for r in rows}) == 1, 'mixed token-reduction group')
    return math.fsum(r['token_reduction'] for r in rows) / len(rows)


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
        "Business processes and agentic systems contain decisions with different computational requirements. Some require interpretation, contextual judgment, novelty handling, or exception resolution; others are stable enough to execute deterministically. When these boundaries are not known in advance, a natural-language agent provides an expressive starting point, but repeatedly routing stable work through a language model creates avoidable model calls and token consumption. We present Path to Least Non Determinism (PLaND), an evaluation-driven methodology for progressively reducing model-mediated computation within accuracy limits set before evaluation. PLaND begins with an entirely English standard operating procedure (SOP). Its evolver skill instructs a host reasoning agent to inspect development examples and execution records, then propose one revised SOP, called a candidate. A candidate may add Python or Bash code and retain model reasoning for unresolved inputs. Evaluation compares predicted and expected answers on separate examples. This study evaluates these packages, not candidate discovery across independent runs. Using Gemini 3.5 Flash Lite, we tested PLaND on three classification tasks: LEDGAR legal clauses, CFPB consumer complaints, and SpamAssassin email. "
        'For each dataset, we used 500 cases for development and 1,000 for selection. We reserved another 500 cases for the final test. At every stage a dataset reached, we ran the comparison three times and report the mean. '
        f'LEDGAR passed all three final-test runs. Mean accuracy improved from {pct(mean_accuracy(l,"baseline"),2)}% to {pct(mean_accuracy(l,"hybrid"),2)}%, while mean token use fell by {pct(mean_token_reduction(l),2)}%. '
        f'SpamAssassin also passed all three final-test runs. Mean accuracy changed slightly from {pct(mean_accuracy(s,"baseline"),2)}% to {pct(mean_accuracy(s,"hybrid"),2)}%, while mean token use fell by {pct(mean_token_reduction(s),2)}%. '
        f'CFPB did not pass selection. Its mean accuracy changed from {pct(mean_accuracy(c,"baseline"),2)}% to {pct(mean_accuracy(c,"hybrid"),2)}%, and the hybrid result stayed below the required 80% in all three runs. We therefore did not open the CFPB final test.'
    )
    blocks['selection_table'] = '| Dataset | Mean accuracy B → H (%) | Mean token reduction (%) | Decision |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {d} | {pct(mean_accuracy(select(d,"selection"),"baseline"),2)} → {pct(mean_accuracy(select(d,"selection"),"hybrid"),2)} | {pct(mean_token_reduction(select(d,"selection")),2)} | {"Accept" if all(r["passed"] for r in select(d,"selection")) else "Reject"} |' for d in DATASETS)
    blocks['final_table'] = '| Dataset | Mean accuracy B → H (%) | Calls B → H | Mean token reduction (%) |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {d} | {pct(mean_accuracy(select(d,"final-test"),"baseline"),2)} → {pct(mean_accuracy(select(d,"final-test"),"hybrid"),2)} | {select(d,"final-test")[0]["baseline"]["model_calls"]} → {select(d,"final-test")[0]["hybrid"]["model_calls"]} | {pct(mean_token_reduction(select(d,"final-test")),2)} |' for d in ('LEDGAR','SpamAssassin'))
    blocks['main_table'] = '| Dataset and split | Baseline to hybrid result |\n| --- | --- |\n' + '\n'.join(
        f'| {group[0]["dataset"]}, {group[0]["stage"]}, {group[0]["baseline"]["cases"]:,} cases | Mean accuracy: {pct(mean_accuracy(group,"baseline"),2)}% → {pct(mean_accuracy(group,"hybrid"),2)}%; mean token reduction: {pct(mean_token_reduction(group),2)}%; **{"Pass" if all(r["passed"] for r in group) else "Reject"}** |'
        for group in (l, c, s))
    blocks['ledgar_result'] = (
        f'On the {l[0]["baseline"]["cases"]:,} LEDGAR final-test clauses, mean accuracy changed from {pct(mean_accuracy(l,"baseline"),2)}% for the baseline to {pct(mean_accuracy(l,"hybrid"),2)}% for the hybrid. '
        'The quality and token requirements passed in every repeat.\n\n'
        f'The hybrid handled {l[0]["command_cases"]} clauses through the Python classification script and sent the remaining {l[0]["hybrid"]["model_calls"]} to the model. '
        f'Model calls therefore fell from {l[0]["baseline"]["model_calls"]} to {l[0]["hybrid"]["model_calls"]} per run, and the mean token reduction was {pct(mean_token_reduction(l),2)}%.'
    )
    blocks['spam_result'] = (
        f"SpamAssassin's hybrid reduced model calls from {s[0]['baseline']['model_calls']} to {s[0]['hybrid']['model_calls']} per final-test run. "
        f'Mean accuracy changed from {pct(mean_accuracy(s,"baseline"),2)}% to {pct(mean_accuracy(s,"hybrid"),2)}%, and the mean token reduction was {pct(mean_token_reduction(s),2)}%. '
        'It passed the quality and token requirements in every repeat. Its small accuracy loss stayed within the allowed tolerance; passing does not mean that accuracy improved.'
    )
    blocks['cfpb_result'] = (
        f"CFPB's hybrid reduced model calls from {c[0]['baseline']['model_calls']:,} to {c[0]['hybrid']['model_calls']} per selection run, with a mean token reduction of {pct(mean_token_reduction(c),2)}%, "
        f'but mean accuracy changed from {pct(mean_accuracy(c,"baseline"),2)}% to {pct(mean_accuracy(c,"hybrid"),2)}%. '
        'Every hybrid repeat missed the 80% minimum. The candidate was rejected and the reserved test was not evaluated. Lower token use did not compensate for failing the accuracy floor.'
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
    blocks['repeat_table'] = '| Dataset and stage | Run | Accuracy: baseline / hybrid (%) | Model tokens: baseline / hybrid |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {r["dataset"]} {"selection" if r["stage"]=="selection" else "final test"} | {REPEATS.index(r["repeat"])+1} | {pct(r["baseline"]["accuracy"])} / {pct(r["hybrid"]["accuracy"])} | {r["baseline"]["total_tokens"]:,} / {r["hybrid"]["total_tokens"]:,} |'
        for r in rows if r['stage'] != 'development')
    blocks['interval_table'] = '| Dataset and stage | Run | Accuracy difference 95% CI (points) | Token reduction 95% CI (%) |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {r["dataset"]} {"selection" if r["stage"]=="selection" else "final test"} | {REPEATS.index(r["repeat"])+1} | {pct(r["accuracy_ci"][0],2)} to {pct(r["accuracy_ci"][1],2)} | {pct(r["token_ci"][0],2)} to {pct(r["token_ci"][1],2)} |'
        for r in rows if r['stage'] != 'development')
    blocks['development_table'] = '| Dataset | B attempts | H attempts | Mean accuracy B → H (%) |\n| --- | --- | --- | --- |\n' + '\n'.join(
        f'| {d} | 1 | {1 if d=="SpamAssassin" else 2} | {pct(mean_accuracy(select(d,"development"),"baseline"),2)} → {pct(mean_accuracy(select(d,"development"),"hybrid"),2)} |' for d in DATASETS)
    blocks['conclusion'] = (
        'PLaND is a methodology for reducing model-mediated work through evaluated changes to an English SOP. Its central mechanism is selective code execution with model fallback. '
        f'On LEDGAR, the evaluated hybrid had a mean token reduction of {pct(mean_token_reduction(l),2)}%, with mean accuracy changing from {pct(mean_accuracy(l,"baseline"),2)}% to {pct(mean_accuracy(l,"hybrid"),2)}%. '
        f'SpamAssassin had a mean token reduction of {pct(mean_token_reduction(s),2)}%, with mean accuracy changing from {pct(mean_accuracy(s,"baseline"),2)}% to {pct(mean_accuracy(s,"hybrid"),2)}%. '
        'Both passed the stated requirements in all three paired runs. CFPB did not pass selection, and its reserved test was not evaluated. '
        'These results show why both quality and token use should be tested before accepting a substitution. The study evaluates the selected packages; it does not establish how reliably independent evolver runs will discover useful candidates or how PLaND performs in complete production workflows.'
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
