"""Record host/runtime facts without evaluating benchmark cases."""
import argparse
import importlib.metadata
import json
import platform
import plistlib
import subprocess
import urllib.request
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args()
assert not a.output.exists()
plan=json.loads(Path('experiments/protocol/fresh-paper-ledgar-training.json').read_text())
with Path('/Users/saikrishna/Library/LaunchAgents/homebrew.mxcl.ollama.plist').open('rb') as h:
    configured=plistlib.load(h)['EnvironmentVariables']
environment={k:configured.get(k) for k in plan['runtime']['environment']}
assert environment==plan['runtime']['environment']
versions={name:importlib.metadata.version(name) for name in ['deepagents','langchain-ollama']}
assert versions=={'deepagents':plan['runtime']['deepagents_version'],'langchain-ollama':plan['runtime']['langchain_ollama_version']}
with urllib.request.urlopen('http://127.0.0.1:11434/api/version',timeout=10) as h: server=json.load(h)
assert server['version']==plan['runtime']['ollama_version']
hardware={key:subprocess.check_output(['sysctl','-n',key],text=True).strip()
          for key in ['machdep.cpu.brand_string','hw.memsize','hw.ncpu']}
result={'status':'PASS','os':platform.mac_ver()[0],'architecture':platform.machine(),
        'python':platform.python_version(),'hardware':hardware,'package_versions':versions,
        'ollama_version':server['version'],'server_environment':environment,
        'note':'Host identity and installed versions recorded after model collection; per-run runtime fingerprints and the initial concurrency test are separately retained.'}
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
