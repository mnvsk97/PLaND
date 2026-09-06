from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Concrete controller invocations for the approved collection, with resumable runs."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'tmp/fresh-paper-continuation-20260905'
CONTROLLER = ROOT/'.codex/skills/pland-data-collection/scripts/run_collection.py'
RUNNER = ROOT/'experiments/text-classification/scripts/run_experiment.py'
PYTHON = ROOT/'reproduce/.venv/bin/python'

def plan_path(ds):
    state=BASE/'runs'/ds/'collection-state.json'
    if state.exists(): return Path(json.loads(state.read_text())['plan']['path'])
    return ROOT/f'experiments/protocol/fresh-paper-{ds}-amended-20260906.json'

def call(argv):
    print(json.dumps({'argv': [str(x) for x in argv]}), flush=True)
    subprocess.run([str(x) for x in argv], cwd=ROOT, check=True)

def controlled(ds, stage, name, argv, inputs=(), outputs=()):
    command = [PYTHON, CONTROLLER, 'run-command', '--run-dir', BASE/'runs'/ds,
               '--stage', stage, '--name', name]
    for path in inputs:
        command += ['--input', path]
    for path in outputs:
        command += ['--output', path]
    call(command+['--']+argv)

def decision(ds, stage, value, evidence):
    call([PYTHON, CONTROLLER, 'decision', '--run-dir', BASE/'runs'/ds,
          '--stage', stage, '--value', value, '--evidence', evidence])

def baseline(ds):
    path = BASE/'runs'/ds/'chosen-baseline.json'
    if path.exists():
        return json.loads(path.read_text())
    return {'attempt': 1, 'package': str(BASE/'packages'/ds/'baseline-01'),
            'run': str(BASE/'runs'/ds/'baseline-development-01.json')}

def candidate_info(ds):
    pointer=BASE/'runs'/ds/'chosen-candidate.json'
    if pointer.exists(): return json.loads(pointer.read_text())
    return {'attempt':1,'candidate_id':'candidate-01','package':str(BASE/'candidates'/ds/'candidate-01')}

def dev_suffix(ds):
    n=candidate_info(ds)['attempt']
    return '' if n==1 else f'-candidate-{n:02}'

def model(ds, stage, variant, seed, name=None):
    plan = json.loads(plan_path(ds).read_text())
    os.environ.update(plan['runtime']['environment'])
    os.environ['PYTHONUNBUFFERED'] = '1'
    split = {'candidate-development':'development', 'selection':'validation', 'final-test':'test'}[stage]
    info = baseline(ds)
    package = Path(info['package'])
    sop = package/f'skills/{ds}-classification/SKILL.md'
    suffix=dev_suffix(ds) if split=='development' else ''
    out = BASE/'runs'/ds/f'{split}-{seed}-{variant}{suffix}.json'
    ci=candidate_info(ds)
    argv = [PYTHON, RUNNER, '--dataset', BASE/'datasets'/ds, '--split', split,
            '--system-prompt', package/'instructions.md', '--sop', sop,
            '--execution-backend', 'deepagent', '--model', plan['model']['name'],
            '--seed', str(seed), '--workers', '2', '--num-ctx', '16384', '--num-predict', '128',
            '--keep-alive', '-1', '--candidate-id', 'baseline' if variant == 'baseline' else ci['candidate_id'],
            '--attempt', str(baseline(ds)['attempt'] if variant=='baseline' else ci['attempt']),
            '--experiment-id', plan['study_id'], '--output', out, '--resume']
    inputs = [sop, package/'instructions.md', RUNNER, RUNNER.with_name('deepagent_execution.py'),
              BASE/'datasets'/ds/'evals.csv', BASE/'datasets'/ds/'freshness-receipt.json']
    if variant == 'hybrid':
        candidate = Path(ci['package'])
        argv[argv.index('--sop')+1] = candidate/'SKILL.md'
        argv += ['--classifier', candidate/'classify.py', '--baseline-sop', sop, '--command-step-id', 'S03']
        inputs += [candidate]
    controlled(ds, stage, name or f'{split}-{seed}-{variant}{suffix}', argv, inputs, [out])
    return out

def compare(ds, stage, seed):
    split = {'candidate-development':'development','selection':'validation','final-test':'test'}[stage]
    directory = BASE/'runs'/ds
    nl = Path(baseline(ds)['run']) if split == 'development' else directory/f'{split}-{seed}-baseline.json'
    suffix=dev_suffix(ds) if split=='development' else ''
    hybrid = directory/f'{split}-{seed}-hybrid{suffix}.json'
    out = directory/f'{split}-{seed}{suffix}-comparison.json'
    script = ROOT/'experiments/text-classification/scripts/compare.py'
    controlled(ds, stage, f'{split}-{seed}{suffix}-comparison', [PYTHON, script, '--nl', nl, '--hybrid', hybrid,
               '--output', out, '--bootstrap-samples', '5000', '--bootstrap-seed', '20260902',
               '--noninferiority-margin', '0.02', '--minimum-token-reduction', '0.05', '--minimum-accuracy', '0.8'],
               [nl, hybrid, script], [out])
    generic = directory/f'{split}-{seed}{suffix}-sop-comparison.json'
    script = ROOT/'skills/pland-evolver/scripts/compare_variants.py'
    controlled(ds, stage, f'{split}-{seed}{suffix}-sop-comparison', [PYTHON, script,
               '--natural-language-run', nl, '--hybrid-run', hybrid, '--output', generic],
               [nl, hybrid, script], [generic])
    return out

def baseline_gate(ds):
    info = baseline(ds)
    directory = BASE/'runs'/ds
    out = directory/f'baseline-decision-{info["attempt"]:02}.json'
    script = ROOT/'skills/generate-initial-version/scripts/assess_baseline.py'
    controlled(ds, 'baseline-development', f'assess-baseline-{info["attempt"]:02}',
               [PYTHON, script, '--run', info['run'], '--attempt', str(info['attempt']),
                '--max-attempts', '10', '--minimum-quality', '0.8', '--output', out], [Path(info['run']), script], [out])
    result = json.loads(out.read_text())['decision']
    decision(ds, 'baseline-development', {'ready_to_freeze':'ready', 'refine_baseline':'refine',
              'baseline_nonviable':'nonviable'}[result], out)

def candidate_gate(ds, stage):
    directory = BASE/'runs'/ds
    ci=candidate_info(ds);limit=json.loads(plan_path(ds).read_text())['limits']['candidate_attempts']
    dev = directory/f'development-20260902-hybrid{dev_suffix(ds)}.json'
    script = ROOT/'skills/pland-evolver/scripts/assess_candidate.py'
    suffix=dev_suffix(ds) if stage=='candidate-development' else ''
    out = directory/f'{stage}{suffix}-assessment.json'
    argv = [PYTHON, script, '--baseline-development', baseline(ds)['run'], '--candidate-development', dev,
            '--candidate', ci['candidate_id'], '--hypothesis', 'Conservative development-derived lexical routes reduce model work with exact English fallback.',
            '--iteration', str(ci['attempt']), '--max-iterations', str(limit), '--target-quality', '0.8',
            '--minimum-baseline-quality', '0.8', '--optimization-metric', 'total_tokens',
            '--min-objective-improvement-ratio', '0', '--require-hybrid-sop',
            '--max-validation-latency-ratio', 'inf', '--output', out]
    inputs = [Path(baseline(ds)['run']), dev, script]
    if stage == 'selection':
        n, h = directory/'validation-20260902-baseline.json', directory/'validation-20260902-hybrid.json'
        argv += ['--baseline-validation', n, '--candidate-validation', h, '--non-inferiority-margin', '0.02']
        inputs += [n,h]
    controlled(ds, stage, f'{stage}{suffix}-assessment', argv, inputs, [out])
    result = json.loads(out.read_text())
    if stage == 'candidate-development':
        decision(ds, stage, 'ready' if result['decision'] == 'eligible_for_validation' else
                 ('refine' if ci['attempt']<limit else 'nonviable'), out)
    else:
        comp = json.loads((directory/'validation-20260902-comparison.json').read_text())
        # Release combines the generic SOP contract with every approved paired statistical gate.
        release = directory/'selection-release.json'
        pair = [json.loads((directory/f'validation-20260902-{v}.json').read_text()) for v in ['baseline','hybrid']]
        errors_clear = all(not r['summary'].get('errors') and r['summary'].get('normal_completion_rate') == 1 for r in pair)
        approved = result['decision']=='accept' and comp['gate']['test_release_pass'] and errors_clear
        evidence = {'decision':'accept' if approved else 'reject', 'assessment':str(out),
                    'comparison':str(directory/'validation-20260902-comparison.json'),
                    'generic_decision':result['decision'], 'statistical_gate':comp['gate'], 'execution_errors_clear': errors_clear}
        if release.exists():
            assert json.loads(release.read_text()) == evidence
        else:
            release.write_text(json.dumps(evidence, indent=2)+'\n')
        decision(ds, stage, evidence['decision'], release)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('dataset', choices=['ledgar','cfpb','spamassassin'])
    p.add_argument('action', choices=['model','compare','baseline-gate','candidate-gate','paired-repeats'])
    p.add_argument('--stage', default='candidate-development')
    p.add_argument('--variant', default='hybrid', choices=['baseline','hybrid'])
    p.add_argument('--seed', default=20260902, type=int)
    a = p.parse_args()
    if a.action == 'model': model(a.dataset,a.stage,a.variant,a.seed)
    elif a.action == 'compare': compare(a.dataset,a.stage,a.seed)
    elif a.action == 'baseline-gate': baseline_gate(a.dataset)
    elif a.action == 'candidate-gate': candidate_gate(a.dataset,a.stage)
    else:
        for index, seed in enumerate([20260903,20260904,20260905]):
            order = ['baseline','hybrid'] if index != 1 else ['hybrid','baseline']
            for variant in order: model(a.dataset,a.stage,variant,seed)
            compare(a.dataset,a.stage,seed)
