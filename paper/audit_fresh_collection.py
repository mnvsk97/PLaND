#!/usr/bin/env python3
"""Audit the fresh paper report against the exported case-level evidence."""
import argparse
import hashlib
import json
import itertools
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def audit(report):
    text=report.read_text()
    summary=json.loads(report.with_suffix('.json').read_text())
    assert summary['report_sha256']==hashlib.sha256(report.read_bytes()).hexdigest()
    verified=[]
    manifests=list(summary.get('case_evidence_manifests',[]))
    if 'case_evidence_manifest' in summary:
        manifests.append(summary['case_evidence_manifest'])
    for item in manifests:
        path=ROOT/item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        for entry in json.loads(path.read_text())['files']:
            artifact=path.parent/entry['path']
            assert artifact.stat().st_size==entry['bytes']
            assert hashlib.sha256(artifact.read_bytes()).hexdigest()==entry['sha256']
    for ds,item in summary['datasets'].items():
        directory=ROOT/item.get('evidence_root',summary.get('evidence_root','experiments/fresh-paper-20260905'))/ds/'results'
        receipt=json.loads((directory/'collection-audit.json').read_text())
        assert receipt['status']=='PASS' and receipt==item['audit']
        host=item.get('host_runtime',summary.get('host_runtime'))
        if host:
            assert host==json.loads((directory/'runtime-audit.json').read_text())
            if item.get('runtime_disclosure'):
                disclosure=json.loads((directory.parent/'protocol/continuation-runtime-disclosure.json').read_text())
                assert disclosure==item['runtime_disclosure']
                assert disclosure['scientific_settings_changed'] is False
                assert disclosure['harness_streaming'] is False and disclosure['ollama_http_streaming'] is True
                assert disclosure['responses_aggregated_before_scoring'] is True
            else:
                disposition=json.loads((directory.parent/'protocol/ledgar-transport-disposition.json').read_text())
                assert disposition==summary['transport_disposition'] and disposition['decision']=='accept_with_disclosure'
            assert 'Disclosed transport deviation' in text and 'HTTP `stream: true`' in text
        stage=item['reported_stage']
        for attempt in item.get('baseline_history',[]):
            run=json.loads((directory/attempt['file']).read_text())
            assert attempt['attempt']==run['attempt'] and attempt['sop_sha256']==run['sop_sha256']
            for key in ['accuracy','correct','cases','total_tokens']:
                assert attempt[key]==run['summary'][key]
            assert f"{attempt['total_tokens']:,}" in text
            assert f"{100*attempt['accuracy']:.1f}%" in text
        comp=directory/f'{stage}-20260902-comparison.json'
        if comp.exists():
            comparison=json.loads(comp.read_text())
            assert comparison==item['comparison']
            for variant,stem in [('natural_language','baseline'),('hybrid','hybrid')]:
                run_path=directory/f'{stage}-20260902-{stem}.json'
                if stage=='development' and stem=='baseline':
                    run_path=directory/f'baseline-development-{item["baseline_attempt"]:02}.json'
                run=json.loads(run_path.read_text())
                assert sum(c['correct'] for c in run['cases'])==comparison[variant]['correct']
                assert sum(c['total_tokens'] for c in run['cases'])==comparison[variant]['total_tokens']
                assert f"{comparison[variant]['total_tokens']:,}" in text
                assert f"{100*comparison[variant]['accuracy']:.1f}%" in text
            assert f"{100*comparison['delta_hybrid_minus_nl']['token_reduction_fraction']:.2f}%" in text
            for low_high in ['accuracy_difference_bootstrap_95','token_reduction_bootstrap_95']:
                assert len(comparison['paired_statistics'][low_high])==2
        if stage=='test': assert item['selection']['decision']=='accept'
        if not comp.exists():
            assert item['comparison'] is None and stage=='development'
            run=json.loads((directory/f'baseline-development-{item["baseline_attempt"]:02}.json').read_text())
            assert item['main_baseline']==run['summary']
            assert sum(c['correct'] for c in run['cases'])==run['summary']['correct']
            assert sum(c['total_tokens'] for c in run['cases'])==run['summary']['total_tokens']
            assert f"{run['summary']['total_tokens']:,}" in text
        assert item['data_audit']['counts']['by_split']=={'development':500,'validation':1000,'test':500}
        for repeat in item['repeats']:
            saved=json.loads((directory/f'{stage}-{repeat["seed"]}-comparison.json').read_text())
            assert saved==repeat['comparison']
        for variant, expected in item.get('variability',{}).items():
            runs=[json.loads((directory/f'{stage}-{r["seed"]}-{variant}.json').read_text()) for r in item['repeats']]
            for metric in ['accuracy','total_tokens']:
                values=[r['summary'][metric] for r in runs]
                assert expected[metric]==dict(values=values,mean=statistics.mean(values),
                    sample_sd=statistics.stdev(values),min=min(values),max=max(values))
            maps=[{c['id']:c['actual'] for c in r['cases']} for r in runs]
            assert expected['any_disagreement_cases']==sum(len({m[k] for m in maps})>1 for k in maps[0])
            assert expected['pairwise_disagreements']==[sum(x[k]!=y[k] for k in x) for x,y in itertools.combinations(maps,2)]
        verified.append({'dataset':ds,'stage':stage,'repeated_pairs':len(item['repeats'])})
    for heading in ['Technical summary','Study contract','Main results','Acceptance-gate audit',
                    'Baseline readiness','Repeatability','Data integrity','Paper-ready findings',
                    'Methods paragraph','Results paragraph','Repeatability paragraph','Limitations paragraph',
                    'Verification and disposition']:
        assert heading in text, heading
    assert 'not independently establish autonomous rule-discovery reliability' in text
    return {'status':'PASS','report':str(report),'report_sha256':summary['report_sha256'],'datasets':verified}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--report',type=Path,default=ROOT/'paper/FRESH_COLLECTION_REPORT.md')
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    result=audit(a.report)
    if a.output:
        if a.output.exists(): raise ValueError('Audit receipt already exists')
        a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
