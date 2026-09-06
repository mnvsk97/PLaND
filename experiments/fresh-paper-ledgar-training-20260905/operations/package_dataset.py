from pathlib import Path
OPS = Path(__file__).resolve().parent
import sys
from operate import BASE,ROOT,PYTHON,CONTROLLER,controlled,call

ds=sys.argv[1];directory=BASE/'runs'/ds
controlled(ds,'package-evidence','record-host-runtime',[PYTHON,OPS/'verify_runtime.py',
           '--output',directory/'runtime-audit.json'],
           [OPS/'verify_runtime.py'],[directory/'runtime-audit.json'])
controlled(ds,'package-evidence','audit-complete-collection',[PYTHON,OPS/'audit_collection.py',
           '--dataset',ds,'--output',directory/'collection-audit.json'],
           [OPS/'audit_collection.py'],[directory/'collection-audit.json'])
controlled(ds,'package-evidence','export-safe-evidence',[PYTHON,OPS/'export_evidence.py',
           '--dataset',ds,'--receipt',directory/'export-receipt.json'],
           [OPS/'export_evidence.py',directory/'collection-audit.json'],[directory/'export-receipt.json'])
call([PYTHON,CONTROLLER,'complete-stage','--run-dir',directory,'--stage','package-evidence'])
call([PYTHON,CONTROLLER,'manifest','--run-dir',directory])
