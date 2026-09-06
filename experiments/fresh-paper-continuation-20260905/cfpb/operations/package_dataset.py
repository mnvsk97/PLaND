"""Audit and export a terminal dataset without changing its scientific evidence."""
import sys
from pathlib import Path
from operate import BASE, ROOT, PYTHON, CONTROLLER, controlled, call

OPS = Path(__file__).resolve().parent
ds = sys.argv[1]
assert ds in {'cfpb', 'spamassassin'}
directory = BASE/'runs'/ds
controlled(ds, 'package-evidence', 'audit-complete-collection',
           [PYTHON, OPS/'audit_collection.py', '--dataset', ds, '--output', directory/'collection-audit.json'],
           [OPS/'audit_collection.py'], [directory/'collection-audit.json'])
controlled(ds, 'package-evidence', 'export-safe-evidence',
           [PYTHON, OPS/'export_evidence.py', '--dataset', ds, '--receipt', directory/'export-receipt.json'],
           [OPS/'export_evidence.py', directory/'collection-audit.json'], [directory/'export-receipt.json'])
call([PYTHON, CONTROLLER, 'complete-stage', '--run-dir', directory, '--stage', 'package-evidence'])
call([PYTHON, CONTROLLER, 'manifest', '--run-dir', directory,
      '--export-dir', ROOT/'experiments/fresh-paper-continuation-20260905'/ds])
