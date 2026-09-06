"""Record the offline repository verifier result without model calls."""
import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args()
assert not a.output.exists()
command=[sys.executable,'reproduce/verify.py']
result=subprocess.run(command,text=True,capture_output=True)
print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
a.output.write_text(json.dumps({'status':'PASS' if result.returncode==0 else 'FAIL',
    'completed_at':datetime.now(UTC).isoformat(),'argv':command,'exit_code':result.returncode,
    'summary':result.stdout.splitlines()[-1] if result.stdout else '',
    'scope':'offline code tests, historical and fresh manifests, preserved manuscript files, fresh report audit'},indent=2)+'\n')
raise SystemExit(result.returncode)
