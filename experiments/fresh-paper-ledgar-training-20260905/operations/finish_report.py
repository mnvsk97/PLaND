"""Package and audit LEDGAR only after collection reaches its permitted terminal stage."""
from pathlib import Path
from operate import BASE,ROOT,PYTHON,CONTROLLER,controlled,call

OPS=Path(__file__).resolve().parent
ds='ledgar';directory=BASE/'runs'/ds
export=ROOT/'experiments/fresh-paper-ledgar-training-20260905/ledgar'
report=ROOT/'paper/LEDGAR_COLLECTION_REPORT.md'
call([PYTHON,OPS/'package_dataset.py',ds])
controlled(ds,'paper-audit','generate-ledgar-report',[PYTHON,OPS/'build_report.py','--output',report],
           [OPS/'build_report.py',directory/'collection-audit.json',export/'case-evidence-manifest.json'],
           [report,report.with_suffix('.json')])
audit=ROOT/'paper/audit_fresh_collection.py'
controlled(ds,'paper-audit','audit-ledgar-report',[PYTHON,audit,'--report',report,'--output',directory/'report-audit.json'],
           [audit,report,report.with_suffix('.json')],[directory/'report-audit.json'])
call([PYTHON,CONTROLLER,'manifest','--run-dir',directory,'--export-dir',export])
controlled(ds,'paper-audit','verify-repository',[PYTHON,OPS/'verify_repository.py',
           '--output',directory/'repository-verification.json'],
           [OPS/'verify_repository.py',ROOT/'reproduce/verify.py'],[directory/'repository-verification.json'])
call([PYTHON,CONTROLLER,'complete-stage','--run-dir',directory,'--stage','paper-audit'])
call([PYTHON,CONTROLLER,'manifest','--run-dir',directory,'--export-dir',export])
print('LEDGAR evidence and report completed. CFPB and SpamAssassin were not started.')
