from pathlib import Path
OPS = Path(__file__).resolve().parent
import ast
import importlib.util
import json
import sys
from pathlib import Path

path, output = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('candidate', path)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
labels = sorted({r['label'] for r in module.RULES})
checks = {}
checks['empty_abstains'] = module.classify('', labels) is None
checks['invalid_type_abstains'] = module.classify(None, labels) is None
checks['oversized_abstains'] = module.classify('x'*200001, labels) is None
checks['unmatched_abstains'] = module.classify('unrelated synthetic input without a routing phrase', labels) is None
checks['unapproved_label_abstains'] = all(module.classify(r['phrase'], []) is None for r in module.RULES)
checks['each_phrase_routes_its_label'] = all(module.classify(r['phrase'], labels)['label']==r['label'] for r in module.RULES)
checks['traceable_rule_ids'] = all(r['id'] in module.classify(r['phrase'], labels)['matched_rule'].split(',') for r in module.RULES)
checks['conflicting_labels_abstain'] = all(module.classify(a['phrase']+' '+b['phrase'], labels) is None
    for a in module.RULES for b in module.RULES if a['label']!=b['label'])
checks['case_and_spacing_normalization'] = all(module.classify(r['phrase'].upper().replace(' ', '\n '), labels)['label']==r['label'] for r in module.RULES)
imports = [n.names[0].name for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.Import)]
checks['stdlib_only'] = imports == ['re']
payload = {'passed':all(checks.values()), 'checks':checks, 'rules':len(module.RULES)}
if output.exists(): raise ValueError('Output exists')
output.write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps(payload))
assert payload['passed']
