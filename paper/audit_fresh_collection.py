#!/usr/bin/env python3
"""Audit the fresh paper report against the exported case-level evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def audit(report):
    text=report.read_text()
    summary=json.loads(report.with_suffix('.json').read_text())
    assert summary['report_sha256']==hashlib.sha256(report.read_bytes()).hexdigest()
    verified=[]
    for ds,item in summary['datasets'].items():
        directory=ROOT/summary.get('evidence_root','experiments/fresh-paper-20260905')/ds/'results'
        receipt=json.loads((directory/'collection-audit.json').read_text())
        assert receipt['status']=='PASS' and receipt==item['audit']
        stage=item['reported_stage']
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
        assert item['data_audit']['counts']['by_split']=={'development':500,'validation':1000,'test':500}
        for repeat in item['repeats']:
            saved=json.loads((directory/f'{stage}-{repeat["seed"]}-comparison.json').read_text())
            assert saved==repeat['comparison']
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
