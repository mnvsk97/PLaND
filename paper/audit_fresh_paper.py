"""Recompute fresh manuscript evidence, including stopped and rejected stages."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_text())

def verify(md):
    scope=read(ROOT/'paper/fresh_revision_scope.json')
    for name,digest in scope['section_sha256'].items():
        match=re.search(r'^#{2,3} '+re.escape(name)+r'\n',md,re.M)
        assert match, name
        after=md[match.end():];end=re.search(r'^#{2,3} ',after,re.M)
        body=after[:end.start()] if end else after
        assert hashlib.sha256(body.encode()).hexdigest()==digest, ('unnecessary section change',name)
    for name,digest in scope['figure_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, ('figure changed',name)
    from audit_fresh_collection import audit
    report=ROOT/'paper/FRESH_COLLECTION_REPORT.md'
    audit(report)
    summary=read(report.with_suffix('.json'))
    assert set(summary['datasets'])=={'ledgar','cfpb','spamassassin'}
    spec=importlib.util.spec_from_file_location('comparison',ROOT/'experiments/text-classification/scripts/compare.py')
    compare=importlib.util.module_from_spec(spec);spec.loader.exec_module(compare)
    verified=[]
    for ds,item in summary['datasets'].items():
        directory=ROOT/item['evidence_root']/ds/'results'
        assert item['data_audit']['passed']
        assert item['data_audit']['counts']['by_split']=={'development':500,'validation':1000,'test':500}
        for filename,record in item['audit']['runs'].items():
            path=directory/filename;run=read(path);cases=run['cases']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
            assert len({c['id'] for c in cases})==len(cases)
            assert all(c['correct']==(c['expected']==c['actual']) for c in cases)
            for key in ['correct','model_calls','input_tokens','output_tokens','total_tokens']:
                assert sum(c[key] for c in cases)==run['summary'][key]
            assert run['summary']['accuracy']==sum(c['correct'] for c in cases)/len(cases)
            assert not run['summary']['errors'] and run['summary']['normal_completion_rate']==1
        for path in directory.glob('*-comparison.json'):
            if path.name.endswith('-sop-comparison.json'): continue
            parts=path.stem.split('-');split,seed=parts[:2];saved=read(path)
            suffix='-'+'-'.join(parts[2:-1]) if len(parts)>3 else ''
            npath=directory/f'{split}-{seed}-baseline.json'
            if split=='development': npath=directory/f'baseline-development-{item["baseline_attempt"]:02}.json'
            n=read(npath);h=read(directory/f'{split}-{seed}-hybrid{suffix}.json')
            assert n['invariants']==h['invariants'] and n['runtime']==h['runtime']
            nc={c['id']:c for c in n['cases']};hc={c['id']:c for c in h['cases']}
            assert nc.keys()==hc.keys()
            pairs=[(nc[k],hc[k]) for k in sorted(nc)]
            assert all(a['expected']==b['expected'] for a,b in pairs)
            for variant,run in [('natural_language',n),('hybrid',h)]:
                for key in ['cases','correct','accuracy','model_calls','input_tokens','output_tokens','total_tokens']:
                    assert saved[variant][key]==run['summary'][key]
                assert saved[variant]['macro_f1']==compare.macro_f1(run['cases'])
            for key,fn,offset in [('accuracy_difference_bootstrap_95',compare.accuracy_difference,0),
                                  ('token_reduction_bootstrap_95',compare.token_reduction,1)]:
                assert saved['paired_statistics'][key]==compare.paired_bootstrap(pairs,fn,5000,20260902+offset)
            gate=saved['gate'];stats=saved['paired_statistics']
            assert (gate['minimum_accuracy'],gate['noninferiority_margin'],gate['minimum_token_reduction'])==(.8,.02,.05)
            passed=(min(n['summary']['accuracy'],h['summary']['accuracy'])>=.8
                    and stats['accuracy_difference_bootstrap_95'][0]>=-.02
                    and compare.token_reduction(pairs)>=.05 and stats['token_reduction_bootstrap_95'][0]>0)
            assert gate['test_release_pass']==passed
        stage=item['reported_stage'];comparison=item['comparison']
        if comparison:
            for variant in ['natural_language','hybrid']:
                values=comparison[variant]
                assert f"{100*values['accuracy']:.1f}%" in md
                assert f"{values['total_tokens']:,}" in md
            assert f"{100*comparison['delta_hybrid_minus_nl']['token_reduction_fraction']:.2f}%" in md
        else:
            assert stage=='development' and not list(directory.glob('test-*-baseline.json'))
            assert f"{100*item['main_baseline']['accuracy']:.1f}%" in md
        if stage=='test': assert item['selection']['decision']=='accept'
        else: assert not list(directory.glob('test-*-baseline.json'))
        verified.append({'dataset':ds,'split':stage,'cases':item['main_baseline']['cases'],
                         'selection_decision':item['selection']['decision'] if item['selection'] else 'not reached'})
    assert '500 | 1,000 | 500' in md
    assert '16,384' in md and 'exact' in md and 'fallback' in md
    assert 'official training' in md
    return summary,verified
