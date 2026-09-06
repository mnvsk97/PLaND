from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Construct one conservative phrase-route candidate from development only."""
import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--dataset', type=Path, required=True)
p.add_argument('--baseline', type=Path, required=True)
p.add_argument('--baseline-run', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--candidate-id', default='candidate-01')
a = p.parse_args()
if a.output.exists(): raise ValueError('Candidate already exists; never generate a replacement')
run = json.loads(a.baseline_run.read_text())
assert run['split'] == 'development' and run['summary']['accuracy'] >= .8 and not run['summary']['errors']
scored = {c['id']:c for c in run['cases']}
with (a.dataset/'evals.csv').open() as h:
    rows = [r for r in csv.DictReader(h) if r['split'] == 'development']
assert len(rows) == 500 and set(scored) == {r['id'] for r in rows}
occurrences = defaultdict(set)
targets = {}
for row in rows:
    content = json.loads((a.dataset/row['input']).read_text())
    text = content.get('text') or content.get('narrative') or content.get('raw_email')
    words = re.findall(r"\b\w+\b", text.casefold())
    targets[row['id']] = json.loads(row['output'])['label']
    for width in [4,5,6]:
        for i in range(len(words)-width+1):
            phrase = ' '.join(words[i:i+width])
            if len(phrase) >= 20:
                occurrences[phrase].add(row['id'])
eligible = []
for phrase, ids in occurrences.items():
    labels = {targets[i] for i in ids}
    if len(ids) >= 8 and len(labels) == 1 and all(scored[i]['correct'] for i in ids):
        eligible.append((phrase, next(iter(labels)), ids))
rules = []
for label in sorted(set(targets.values())):
    covered = set()
    candidates = [r for r in eligible if r[1] == label]
    for _ in range(3):
        candidates.sort(key=lambda r: (-len(r[2]-covered), -len(r[0].split()), -len(r[0]), r[0]))
        if not candidates or len(candidates[0][2]-covered) < 4: break
        phrase, _, ids = candidates.pop(0)
        rules.append({'id':f'phrase-{len(rules)+1:02}', 'phrase':phrase, 'label':label,
                      'development_support':len(ids), 'development_correct':len(ids)})
        covered.update(ids)
a.output.mkdir(parents=True)
code = '''"""Exact normalized phrase routes with conflict abstention; no model or network calls."""
import re

RULES = REPLACE_RULES

def classify(text, labels):
    if not isinstance(text, str) or not text.strip() or len(text) > 200_000:
        return None
    normalized = ' ' + ' '.join(re.findall(r"\\b\\w+\\b", text.casefold())) + ' '
    matches = [rule for rule in RULES if ' '+rule['phrase']+' ' in normalized]
    targets = {rule['label'] for rule in matches}
    if len(targets) != 1 or next(iter(targets)) not in labels:
        return None
    label = next(iter(targets))
    return {'label':label, 'matched_rule':','.join(rule['id'] for rule in matches)}
'''.replace('REPLACE_RULES', repr(rules))
(a.output/'classify.py').write_text(code)
baseline = a.baseline.read_text()
lines = baseline.splitlines()
line = next(line for line in lines if line.startswith('3. [S03]'))
original = line.split('[S03] ',1)[1].split(' <!-- pland:english -->',1)[0]
replacement = ('3. [S03] Execute `python classify.py` through its `classify(text, labels)` function on the supplied evidence. '
               'Use a valid single-label result only when a declared phrase matches without a conflicting label; '
               'otherwise execute the exact English fallback. <!-- pland:command fallback=S03 -->\n'
               f'   Fallback [S03]: {original} <!-- pland:fallback -->')
(a.output/'SKILL.md').write_text(baseline.replace(line,replacement))
(a.output/'construction.json').write_text(json.dumps({
 'candidate_id':a.candidate_id, 'methodology_skill':'pland-evolver',
 'orchestrator_model':'gpt-6-astra','reasoning':'high',
 'hypothesis':'Frequent label-specific phrases that reproduced correct development decisions can bypass some Qwen calls; all ambiguous inputs retain exact English fallback.',
 'baseline_run_sha256':hashlib.sha256(a.baseline_run.read_bytes()).hexdigest(),
 'development_cases':500, 'selection_or_test_used':False, 'rules':rules,
 'construction_rule':'Enumerate normalized 4-6 word phrases; minimum 8 development matches, all same gold label and baseline-correct; at most 3 complementary phrases per label with at least 4 new matches.',
 'caching':'No prediction cache. Immutable rule constants loaded once; no mutable per-case state.',
 'parallelism':'No internal parallelism: phrase matching is small and sequential; existing two independent case workers are retained.',
 'permissions':'Pure string processing, no I/O/network/subprocess in classify; 200000-character bound; invalid/empty/conflicting outputs abstain.',
 'frozen_fallback_step':'S03',
}, indent=2)+'\n')
print(json.dumps({'rules':rules,'candidate':str(a.output)}, indent=2))
