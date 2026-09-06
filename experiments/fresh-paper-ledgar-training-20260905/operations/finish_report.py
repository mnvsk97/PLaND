"""Package and audit LEDGAR only after collection reaches its permitted terminal stage."""
from pathlib import Path
import shutil
import json
from operate import BASE,ROOT,PYTHON,CONTROLLER,controlled,call

OPS=Path(__file__).resolve().parent
ds='ledgar';directory=BASE/'runs'/ds
export=ROOT/'experiments/fresh-paper-ledgar-training-20260905/ledgar'
report=ROOT/'paper/LEDGAR_COLLECTION_REPORT.md'
call([PYTHON,OPS/'package_dataset.py',ds])
disposition=ROOT/'experiments/protocol/ledgar-transport-disposition.json'
if not disposition.exists() or json.loads(disposition.read_text()).get('decision')!='accept_with_disclosure':
    raise SystemExit('Evidence packaged. Author disposition of the recorded transport deviation is required before report finalization.')
shutil.copy2(disposition,export/'protocol'/disposition.name)
controlled(ds,'paper-audit','generate-ledgar-report',[PYTHON,OPS/'build_report.py','--output',report],
           [OPS/'build_report.py',directory/'collection-audit.json',export/'case-evidence-manifest.json',disposition],
           [report,report.with_suffix('.json')])
audit=ROOT/'paper/audit_fresh_collection.py'
controlled(ds,'paper-audit','audit-ledgar-report',[PYTHON,audit,'--report',report,'--output',directory/'report-audit.json'],
           [audit,report,report.with_suffix('.json')],[directory/'report-audit.json'])
call([PYTHON,CONTROLLER,'manifest','--run-dir',directory,'--export-dir',export])
controlled(ds,'paper-audit','verify-repository',[PYTHON,OPS/'verify_repository.py',
           '--output',directory/'repository-verification.json'],
           [OPS/'verify_repository.py',ROOT/'reproduce/verify.py'],[directory/'repository-verification.json'])
call([PYTHON,CONTROLLER,'complete-stage','--run-dir',directory,'--stage','paper-audit'])
for name in ['report-audit.json','repository-verification.json']:
    shutil.copy2(directory/name,export/'results'/name)
(export/'report').mkdir(exist_ok=True)
for path in [report,report.with_suffix('.json')]: shutil.copy2(path,export/'report'/path.name)
call([PYTHON,CONTROLLER,'manifest','--run-dir',directory,'--export-dir',export])
print('LEDGAR evidence and report completed. CFPB and SpamAssassin were not started.')
