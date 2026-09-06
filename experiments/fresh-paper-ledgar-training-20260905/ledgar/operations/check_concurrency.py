"""Synthetic machine diagnostic; not an experimental dataset measurement."""
import concurrent.futures
import json
import threading
import time
import urllib.request
from pathlib import Path
import argparse
p=argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); args=p.parse_args()
assert not args.output.exists()

URL = 'http://127.0.0.1:11434/api/generate'
barrier = threading.Barrier(2)

def request(payload):
    return urllib.request.urlopen(urllib.request.Request(
        URL, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}), timeout=180)

with request({'model': 'qwen3:14b', 'keep_alive': -1, 'stream': False,
              'options': {'num_ctx': 16384}}) as response:
    json.load(response)

def run(index):
    barrier.wait()
    start = time.monotonic()
    times = []
    final = {}
    with request({'model': 'qwen3:14b', 'prompt': f'Count from {index+1} to 100, separating each number with a comma.',
                  'think': False, 'stream': True, 'keep_alive': -1,
                  'options': {'num_ctx': 16384, 'num_predict': 128, 'temperature': 0, 'seed': 20260902}}) as response:
        for line in response:
            value = json.loads(line)
            if value.get('response'):
                times.append(time.monotonic())
            if value.get('done'):
                final = value
    return {'request': index, 'start': start, 'first_token': times[0], 'last_token': times[-1],
            'elapsed_seconds': time.monotonic()-start,
            'eval_count': final.get('eval_count'), 'eval_duration': final.get('eval_duration'),
            'done_reason': final.get('done_reason')}

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    runs = list(pool.map(run, range(2)))
overlap = min(r['last_token'] for r in runs)-max(r['first_token'] for r in runs)
result = {'purpose': 'synthetic Ollama configuration diagnostic, excluded from paper evidence',
          'runs': runs, 'generation_overlap_seconds': overlap, 'concurrent_generation_verified': overlap > 0}
args.output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
assert overlap > 0, 'Requests did not demonstrate concurrent generation'
