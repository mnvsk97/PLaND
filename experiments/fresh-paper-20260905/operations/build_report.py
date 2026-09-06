from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Generate the approved paper report from audited collection artifacts only."""
import argparse
import hashlib
import itertools
import json
import statistics
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();ROOT=Path.cwd();BASE=ROOT/'tmp/fresh-paper-ledgar-training-20260905'
names={'ledgar':'LEDGAR','cfpb':'CFPB','spamassassin':'SpamAssassin'}
def read(path): return json.loads(path.read_text())
def percent(x,d=2): return f'{100*x:.{d}f}%'
def interval(xs,pp=False): return '['+', '.join(f'{100*x:+.2f}' if pp else f'{100*x:.2f}%' for x in xs)+']'
summary={'study_id':'fresh-paper-20260905-complete','datasets':{}}
for ds,name in names.items():
    evidence_root='experiments/fresh-paper-ledgar-training-20260905' if ds=='ledgar' else 'experiments/fresh-paper-continuation-20260905'
    BASE=ROOT/('tmp/fresh-paper-ledgar-training-20260905' if ds=='ledgar' else 'tmp/fresh-paper-continuation-20260905')
    directory=BASE/'runs'/ds;state=read(directory/'collection-state.json')
    audit=read(directory/'collection-audit.json');assert audit['status']=='PASS'
    selected=read(directory/'chosen-baseline.json') if (directory/'chosen-baseline.json').exists() else {'run':str(directory/'baseline-development-01.json'),'attempt':1}
    baseline=read(Path(selected['run']))
    baseline_history=[]
    for path in sorted(directory.glob('baseline-development-[0-9][0-9].json')):
        run=read(path)
        baseline_history.append({'file':path.name,'attempt':run['attempt'],
            'accuracy':run['summary']['accuracy'],'correct':run['summary']['correct'],
            'cases':run['summary']['cases'],'total_tokens':run['summary']['total_tokens'],
            'sop_sha256':run['sop_sha256']})
    selection=read(directory/'selection-release.json') if (directory/'selection-release.json').exists() else None
    stage='test' if selection and selection['decision']=='accept' else 'validation' if selection else 'development'
    comp_path=directory/f'{stage}-20260902-comparison.json'
    comparison=read(comp_path) if comp_path.exists() else None
    main_n_path=directory/f'{stage}-20260902-baseline.json' if stage!='development' else Path(selected['run'])
    main_h_path=directory/f'{stage}-20260902-hybrid.json'
    n=read(main_n_path);h=read(main_h_path) if main_h_path.exists() else None
    construction=BASE/'candidates'/ds/'candidate-01/construction.json'
    repeats=[]
    repeat_runs={'baseline':[],'hybrid':[]}
    for index,seed in enumerate([20260903,20260904,20260905]):
        path=directory/f'{stage}-{seed}-comparison.json'
        if not path.exists(): continue
        r=read(path);repeats.append({'seed':seed,'pair_order':'baseline → hybrid' if index!=1 else 'hybrid → baseline',
                                  'comparison':r})
        for variant in repeat_runs: repeat_runs[variant].append(read(directory/f'{stage}-{seed}-{variant}.json'))
    variability={}
    for variant,runs in repeat_runs.items():
        if not runs: continue
        maps=[{c['id']:c['actual'] for c in r['cases']} for r in runs]
        metrics={}
        for metric in ['accuracy','total_tokens']:
            values=[r['summary'][metric] for r in runs]
            metrics[metric]={'values':values,'mean':statistics.mean(values),'sample_sd':statistics.stdev(values),
                             'min':min(values),'max':max(values)}
        metrics['any_disagreement_cases']=sum(len({m[k] for m in maps})>1 for k in maps[0])
        metrics['pairwise_disagreements']=[sum(x[k]!=y[k] for k in x) for x,y in itertools.combinations(maps,2)]
        variability[variant]=metrics
    summary['datasets'][ds]={'name':name,'evidence_root':evidence_root,'host_runtime':read(directory/'runtime-audit.json'),'reported_stage':stage,'selection':selection,'comparison':comparison,
        'runtime_disclosure':read(ROOT/'experiments/protocol/continuation-runtime-disclosure.json') if ds!='ledgar' else None,
        'selection_comparison':read(directory/'validation-20260902-comparison.json') if selection else None,
        'baseline_development':baseline['summary'],'baseline_attempt':selected['attempt'],
        'baseline_history':baseline_history,
        'baseline_sop_sha256':baseline['sop_sha256'],'candidate_sop_sha256':h['sop_sha256'] if h else None,
        'candidate_skill_content_sha256':h['skill_content_sha256'] if h else None,
        'main_baseline':n['summary'],'main_hybrid':h['summary'] if h else None,
        'plan_sha256':state['plan']['sha256'],'git_head':state['git_head'],
        'model_digest':n['model_digest'],'runtime':n['runtime'],'repeats':repeats,'variability':variability,
        'construction':read(construction) if construction.exists() else None,'audit':audit,
        'data_audit':read(directory/'dataset-audit.json'),
        'per_case_latency_p95':{v:sorted(r['cases'],key=lambda c:c['latency_seconds'])[int(.95*(len(r['cases'])-1))]['latency_seconds']
                                for v,r in [('baseline',n),('hybrid',h)] if r},
        'escape_counts':{reason:sum(c['step_trace']['escape_reason']==reason for c in h['cases'])
                         for reason in sorted({c['step_trace']['escape_reason'] for c in h['cases'] if c['step_trace']['escape_reason']})} if h else {},
    }
lines=['# PLaND fresh evaluation report','',
       '## Technical summary','',
       'This collection evaluates fixed English and hybrid SOP execution on fresh, balanced LEDGAR, CFPB, and SpamAssassin study splits. LEDGAR uses untouched official training rows; the other tasks use their frozen source snapshots. '
       'Each dataset has exactly 500 development, 1,000 selection, and 500 reserved final-test cases. '
       'The main results below identify the stage actually reached; a reserved test is evaluated only after selection accepts.','']
for ds,item in summary['datasets'].items():
    c=item['comparison'];stage={'test':'final test','validation':'selection','development':'development'}[item['reported_stage']]
    if c:
        decision='passed' if c['gate']['test_release_pass'] else 'did not pass'
        lines.append(f"{item['name']} {decision} the stated statistical criteria on {stage}: accuracy was {percent(c['natural_language']['accuracy'],1)} → {percent(c['hybrid']['accuracy'],1)}, with {percent(c['delta_hybrid_minus_nl']['token_reduction_fraction'])} fewer model tokens.")
    else: lines.append(f"{item['name']} stopped at development; no selection or final-test estimate is available.")
lines+=['','These measurements test the resulting fixed packages. The construction record does not independently establish autonomous rule-discovery reliability.','',
 '## Study contract and completed scope','',
 '| Item | Frozen value |','| --- | --- |',
 '| Study | Approved fresh paper collection, all three datasets |',
 '| Model | qwen3:14b; '+next(iter(summary['datasets'].values()))['model_digest']+' |',
 '| Runtime | Native Ollama 0.33.0; DeepAgent 0.7.12; langchain-ollama 1.1.0; temperature 0; thinking disabled; complete responses at harness boundary, internally streamed Ollama HTTP transport (documented deviation); context 16,384; output cap 128; two case workers and two server slots; Flash Attention; q8_0 KV cache; one loaded model; keep alive −1 |',
 '| Main / dataset seed | 20260902 |',
 '| Bootstrap | 5,000 paired resamples; accuracy RNG seed 20260902; token RNG seed 20260903; two-sided 95% percentile intervals |',
 '| Readiness | At least 80% development accuracy, complete valid outputs, no errors, at most ten English attempts |',
 '| Candidate limit | One hybrid candidate per dataset |',
 '| Selection | Both accuracies ≥80%; accuracy-difference CI lower bound ≥−2 pp; token reduction ≥5%; token-reduction CI lower bound >0; matching frozen invariants and no execution errors |',
 '| Repeats | Three additional paired executions on the reached selection/final split, seeds 20260903–20260905; pair order alternates |','',
 'Token use is reported model input plus output tokens. Accuracy is exact label agreement. All comparisons use the same case identifiers and expected labels within a pair. '
 'Runtime latency is elapsed case time within a two-worker run; throughput wall time is a separate measurement.','',
 '## Main results','',
 '| Dataset | Stage | Cases | Baseline → hybrid accuracy | Difference (pp), 95% CI | Model calls | Model tokens | Token reduction, 95% CI | Criteria |',
 '| --- | --- | ---: | --- | --- | ---: | ---: | --- | --- |']
for item in summary['datasets'].values():
    c=item['comparison']
    if not c:
        lines.append(f"| {item['name']} | development only | 500 | {percent(item['main_baseline']['accuracy'])} → not created | not measured | {item['main_baseline']['model_calls']} → not measured | {item['main_baseline']['total_tokens']:,} → not measured | not measured | baseline stopped |")
        continue
    n,h,s=c['natural_language'],c['hybrid'],c['paired_statistics'];d=c['delta_hybrid_minus_nl']
    lines.append(f"| {item['name']} | {item['reported_stage'].replace('test','final test').replace('validation','selection')} | {n['cases']:,} | {percent(n['accuracy'],1)} → {percent(h['accuracy'],1)} | {100*d['accuracy']:+.2f}; {interval(s['accuracy_difference_bootstrap_95'],True)} | {n['model_calls']:,} → {h['model_calls']:,} | {n['total_tokens']:,} → {h['total_tokens']:,} | {percent(d['token_reduction_fraction'])}; {interval(s['token_reduction_bootstrap_95'])} | {'Pass' if c['gate']['test_release_pass'] else 'Reject'} |")
lines+=['','Final-test criteria are descriptive checks on the frozen package, not another selection or refinement opportunity.','',
 '## Acceptance-gate audit','',
 '| Dataset | Selection decision | Baseline ≥80% | Hybrid ≥80% | Accuracy lower bound ≥−2 pp | Tokens reduced ≥5% | Token lower bound >0 | Reserved final test |',
 '| --- | --- | --- | --- | --- | --- | --- | --- |']
for item in summary['datasets'].values():
    s=item['selection']
    c=item['selection_comparison']
    checks=[c['natural_language']['accuracy']>=.8,c['hybrid']['accuracy']>=.8,
            c['paired_statistics']['accuracy_difference_bootstrap_95'][0]>=-.02,
            c['delta_hybrid_minus_nl']['token_reduction_fraction']>=.05,
            c['paired_statistics']['token_reduction_bootstrap_95'][0]>0] if c else [None]*5
    cells=' | '.join('not reached' if x is None else 'Pass' if x else 'Fail' for x in checks)
    lines.append(f"| {item['name']} | {s['decision'] if s else 'not reached'} | {cells} | {'evaluated' if item['reported_stage']=='test' else 'unopened'} |")
lines+=['','## Baseline readiness and candidate provenance','',
 '| Dataset | English attempts | Development accuracy | Candidate rules | Baseline SOP SHA-256 | Candidate SOP SHA-256 |',
 '| --- | ---: | ---: | ---: | --- | --- |']
for item in summary['datasets'].values():
    lines.append(f"| {item['name']} | {item['baseline_attempt']}/10 | {percent(item['baseline_development']['accuracy'])} | {len(item['construction']['rules']) if item['construction'] else 0} | `{item['baseline_sop_sha256']}` | `{item['candidate_sop_sha256'] or 'not created'}` |")
lines += ['', '| Dataset | English attempt | Development correct / cases | Accuracy | Model tokens |',
          '| --- | ---: | --- | ---: | ---: |']
for item in summary['datasets'].values():
    for attempt in item['baseline_history']:
        lines.append(f"| {item['name']} | {attempt['attempt']} | {attempt['correct']} / {attempt['cases']} | {percent(attempt['accuracy'],1)} | {attempt['total_tokens']:,} |")
lines+=['','The host used the two PLaND skills to generate the English scaffold and construct one candidate after baseline readiness. '
 'Each candidate uses frequent 4–6-word phrases observed in at least eight development cases, with one label and correct baseline decisions on those cases. '
 'At most three complementary phrases per label are retained. Matching multiple labels, absent matches, invalid inputs, and failed output checks abstain. '
 'The command replaces S03 and retains the exact frozen English S03 as fallback. No prediction cache, paid service, or classifier network access is used.','',
 '| Dataset | Command-resolved cases | Command precision | Model fallback cases | Escape reasons |',
 '| --- | ---: | ---: | ---: | --- |']
for item in summary['datasets'].values():
    c=item['comparison']
    if c:
        m=c['mechanism_decomposition']
        precision=m['command_routed_hybrid_precision']
        lines.append(f"| {item['name']} | {m['command_routed_cases']} | {percent(precision) if precision is not None else 'not applicable'} | {m['model_fallback_cases']} | {item['escape_counts']} |")
lines+=['','## Repeatability of the frozen comparison','',
 '| Dataset | Stage | Seed | Pair order | Baseline → hybrid accuracy | Baseline → hybrid tokens | Criteria |',
 '| --- | --- | ---: | --- | --- | ---: | --- |']
for item in summary['datasets'].values():
    for r in item['repeats']:
        c=r['comparison'];n,h=c['natural_language'],c['hybrid']
        lines.append(f"| {item['name']} | {item['reported_stage']} | {r['seed']} | {r['pair_order']} | {percent(n['accuracy'],1)} → {percent(h['accuracy'],1)} | {n['total_tokens']:,} → {h['total_tokens']:,} | {'Pass' if c['gate']['test_release_pass'] else 'Reject'} |")
lines+=['','These executions reuse the same frozen cases; they are not independent test samples. No repeat changed the selected package.','',
 '| Dataset / variant | Mean accuracy ± sample SD | Mean tokens ± sample SD | Token range | Cases with any label disagreement | Pairwise disagreements |',
 '| --- | --- | --- | --- | ---: | --- |']
for item in summary['datasets'].values():
    for variant,v in item['variability'].items():
        q,t=v['accuracy'],v['total_tokens']
        lines.append(f"| {item['name']} / {variant} | {percent(q['mean'])} ± {100*q['sample_sd']:.3f} pp | {t['mean']:,.2f} ± {t['sample_sd']:,.2f} | {t['min']:,}–{t['max']:,} | {v['any_disagreement_cases']} | {v['pairwise_disagreements']} |")
lines+=['','## Data integrity and comparability','',
 '| Dataset | Split counts | Duplicate / overlapping cases | Plan SHA-256 | Data audit |',
 '| --- | --- | --- | --- | --- |']
for ds,item in summary['datasets'].items():
    d=item['data_audit'];checks=d['checks']
    lines.append(f"| {item['name']} | 500 / 1,000 / 500 | IDs: {checks['split_id_overlap_count']}; content: {checks['content_duplicate_count']}; prior overlap: {checks['pilot_overlap_count']} | `{item['plan_sha256']}` | [Passed](../{item['evidence_root']}/{ds}/results/dataset-audit.json) |")
lines+=['','Source hashes, full data-selection fingerprints, baseline/candidate package fingerprints, seeds, original commands, traces, failure logs, '
 'and release timestamps are retained in each dataset evidence directory. Raw benchmark inputs remain local under upstream terms.','',
 '## Runtime measurements','',
 '| Dataset | Mean case time baseline → hybrid (s) | p95 case time (s) | Throughput wall time (s) | Max runner RSS baseline → hybrid (bytes) |',
 '| --- | --- | --- | --- | --- |']
for item in summary['datasets'].values():
    n,h=item['main_baseline'],item['main_hybrid']
    if h:
        lines.append(f"| {item['name']} | {n['latency_seconds']['mean']:.4f} → {h['latency_seconds']['mean']:.4f} | {item['per_case_latency_p95']['baseline']:.4f} → {item['per_case_latency_p95']['hybrid']:.4f} | {n['wall_seconds']:.2f} → {h['wall_seconds']:.2f} | {n['max_rss_bytes']:,} → {h['max_rss_bytes']:,} |")
lines+=['','Local API charges were zero; this is not a measurement of hardware cost, electricity, total operational cost, or dollar savings. Runner RSS excludes the separately resident Ollama model.','',
 '## Paper-ready findings','',
 '### Methods paragraph','',
 'We evaluated fixed English and hybrid SOPs on balanced LEDGAR clauses, CFPB complaints, and SpamAssassin email. '
 'Each dataset contained 500 development, 1,000 selection, and 500 reserved test examples. Previously opened identifiers and normalized-content duplicates were excluded, '
 'and new disjoint study splits were constructed within the official LEDGAR training partition; these are not official benchmark validation/test scores. An English baseline had to reach 80% development accuracy with complete, error-free execution before one hybrid candidate could be constructed. '
 'The hybrid used development-derived phrase rules and the exact frozen English fallback. Model-mediated execution used DeepAgent with local qwen3:14b, temperature zero, thinking disabled, and two concurrent workers. '
 'Selection required both workflows to reach 80% accuracy, a paired 95% accuracy-difference interval lower bound of at least −2 percentage points, at least 5% fewer model tokens, '
 'and a strictly positive lower bound for token reduction. We used 5,000 paired bootstrap resamples. Only selection acceptance released the reserved test.','',
 '### Results paragraph','']
for item in summary['datasets'].values():
    c=item['comparison']
    if c:
        n,h=c['natural_language'],c['hybrid']
        stage={'test':'reserved test','validation':'selection set','development':'development set'}[item['reported_stage']]
        lines.append(f"On {item['name']}'s {n['cases']:,}-case {stage}, accuracy changed from {percent(n['accuracy'],1)} to {percent(h['accuracy'],1)}; model calls changed from {n['model_calls']:,} to {h['model_calls']:,}, and tokens from {n['total_tokens']:,} to {h['total_tokens']:,} ({percent(c['delta_hybrid_minus_nl']['token_reduction_fraction'])} reduction). The fixed package {'met' if c['gate']['test_release_pass'] else 'did not meet'} the stated statistical criteria at this stage.")
    else: lines.append(f"{item['name']} did not reach selection; its development result is retained as a stopped outcome.")
lines+=['','### Repeatability paragraph','',
 'For each dataset that reached selection, three additional paired executions used the same frozen packages and the same reached evaluation split, with inference seeds 20260903, 20260904, and 20260905. '
 'The repeat table reports each result separately, and the variability table gives sample standard deviations and prediction disagreements. '
 'These are repeated executions, not new evaluation samples or further candidate attempts.','',
 '### Limitations paragraph','',
 'The evidence is limited to one local model, balanced subsets, and the specific fixed SOP packages. The data do not represent natural production label frequencies. '
 'Freshness means no prior local experimental exposure; it does not establish absence from Qwen pretraining. '
 'The LEDGAR study splits were sampled from official training rows, so its results are not official benchmark validation/test scores. '
 'Development phrase purity does not guarantee correctness on unseen documents; the paired evaluation is the relevant safeguard. '
 'Bootstrap intervals describe sampled-case uncertainty within these prepared tasks and do not cover model changes or distribution shift. '
 'The construction trail does not independently test autonomous rule discovery. Full business workflows, production readiness, energy use, and monetary savings were not evaluated. '
 'Any dataset rejected before final test has no reserved-test estimate.','',
 '## Verification and disposition','',
 'Dataset integrity, run arithmetic, model-token accounting, frozen pair fingerprints, statistical recomputation, and release order passed the saved collection audits. '
 'The separate repository/report audit receipt records final manifest verification. This report supplies replacement manuscript text and exact results; the existing PLaND.pdf is not changed by this report builder.','',
 '## Remaining questions','',
 'The statistical outcomes are fixed. Any future candidate revision requires a new development process and unused evaluation evidence.','']
a.output.parent.mkdir(parents=True,exist_ok=True)
disposition=read(ROOT/'experiments/protocol/ledgar-transport-disposition.json')
assert disposition['decision']=='accept_with_disclosure'
summary['transport_disposition']=disposition
summary['case_evidence_manifests']=[]
lines+=['## Disclosed transport deviation','',
 'The harness received complete responses, while Ollama used HTTP `stream: true` internally. '
 'Both arms used the same frozen path and aggregated responses before scoring. Raw `stream: false` fields describe the outward interface, not HTTP transport. '
 'This is the previously accepted metadata correction, not a change to measured execution.','',
 '## Detailed paper statistics and provenance','']
for ds,item in summary['datasets'].items():
    item['raw_run_runtime']=item['runtime']
    item['runtime']={k:v for k,v in item['raw_run_runtime'].items() if k!='stream'}
    item['runtime'].update(harness_streaming=False,ollama_http_streaming=True,responses_aggregated_before_scoring=True)
    manifest=ROOT/item['evidence_root']/ds/'case-evidence-manifest.json'
    entry={'path':str(manifest.relative_to(ROOT)),'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}
    summary['case_evidence_manifests'].append(entry)
    host=item['host_runtime'];assert host['status']=='PASS'
    lines += [f"### {item['name']} provenance",'',
      f"Frozen run commit: `{item['git_head']}`. Case-evidence manifest: `{entry['path']}`; SHA-256 `{entry['sha256']}`.",'',
      f"Host: {host['hardware']['machdep.cpu.brand_string']}, {int(host['hardware']['hw.memsize'])/2**30:g} GiB, macOS {host['os']}, Python {host['python']}.",'',
      '| Data fingerprint | SHA-256 |','| --- | --- |']
    for key,value in item['data_audit']['hashes'].items(): lines.append(f'| {key} | `{value}` |')
    for source in item['data_audit']['sources']: lines.append(f"| Source {source['path']} | `{source['sha256']}` |")
    c=item['comparison']
    if c:
        n,h,stat=c['natural_language'],c['hybrid'],c['paired_statistics']
        lines += ['', '| Main statistic | Baseline | Hybrid |','| --- | ---: | ---: |',
          f"| Correct / cases | {n['correct']} / {n['cases']} | {h['correct']} / {h['cases']} |",
          f"| Macro F1 | {n['macro_f1']:.6f} | {h['macro_f1']:.6f} |",
          f"| Accuracy Wilson 95% CI | {interval(stat['natural_language_accuracy_wilson_95'])} | {interval(stat['hybrid_accuracy_wilson_95'])} |",
          f"| Input tokens | {n['input_tokens']:,} | {h['input_tokens']:,} |",
          f"| Output tokens | {n['output_tokens']:,} | {h['output_tokens']:,} |",'',
          f"Exact McNemar p-value: {stat['mcnemar_exact_p']:.8g}.",'',
          '| Label | Baseline recall | Hybrid recall |','| --- | ---: | ---: |']
        for label,value in sorted(c['per_label_recall']['natural_language'].items()):
            lines.append(f"| {label} | {percent(value)} | {percent(c['per_label_recall']['hybrid'][label])} |")
    lines.append('')
lines += ['The invalid initial LEDGAR sample remains quarantined and is excluded from this report. The accepted LEDGAR restart has its own plan and evidence directory. Previous historical results are not pooled with these fresh results.','']
completed=sum(len(item['audit']['runs']) for item in summary['datasets'].values())
failed=sum(item['audit']['failed_commands_preserved'] for item in summary['datasets'].values())
unopened=sum(item['reported_stage']!='test' for item in summary['datasets'].values())
summary['scope_counts']={'completed_model_runs':completed,'failed_commands_preserved':failed,'unopened_final_tests':unopened}
lines += [f'Completed model-run commands: {completed}. Failed commands preserved in the valid collection ledgers: {failed}. Reserved final-test splits unopened: {unopened}.','']
if a.output.exists(): raise ValueError('Report exists; preserve its previous revision')
a.output.write_text('\n'.join(lines))
summary['report_sha256']=hashlib.sha256(a.output.read_bytes()).hexdigest()
a.output.with_suffix('.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'report':str(a.output),'datasets':list(summary['datasets'])}))
