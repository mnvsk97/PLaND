#!/usr/bin/env python3
"""Audit manuscript numbers against saved evidence; never run model inference."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import statistics
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'paper'
DATASETS = ['ledgar-text-classification', 'cfpb-text-classification', 'spamassassin-email-classification']

def read(path):
    return json.loads(path.read_text())

def main():
    args = argparse.ArgumentParser()
    args.add_argument('--artifacts', action='store_true')
    opt = args.parse_args()
    md = (PAPER/'PLaND.md').read_text()
    forbidden = r'quality.first|LiteParse|SROIE|RVL|Tobacco|QS.OCR|release contract|baseline nonviable|program synthesis methods'
    assert not re.search(forbidden, md, re.I), 'Removed scope or jargon returned'
    heads = re.findall(r'^#{2,3} (.+)$', md, re.M)
    for section in re.findall(r'Section (\d+\.\d+)', md):
        assert any(h.startswith(section+' ') for h in heads), section
    body, refs = md.split('## References')
    assert [int(x) for x in re.findall(r'^\[(\d+)\]', refs, re.M)] == list(range(1,19))
    cited = set()
    citation_order = []
    for group in re.findall(r'\[([\d, -]+)\]', body):
        for part in group.split(','):
            pair = part.strip().split('-')
            for value in range(int(pair[0]),int(pair[-1])+1):
                if value not in cited:
                    citation_order.append(value)
                cited.add(value)
    assert cited == set(range(1,19)), cited
    assert citation_order == list(range(1,19)), citation_order
    assert len(re.findall(r'^\*\*Table \d\.', md, re.M)) == 4
    assert len(re.findall(r'^\*\*Figure \d\.', md, re.M)) == 3
    assert len(re.findall(r'\b[\w\'-]+\b',md.split('## Abstract')[1].split('**Keywords:')[0])) <= 300

    fresh = None
    if (PAPER/'FRESH_COLLECTION_REPORT.json').exists():
        from audit_fresh_paper import verify
        fresh, verified = verify(md)
    else:
        script = ROOT/'experiments/text-classification/scripts/compare.py'
        spec=importlib.util.spec_from_file_location('comparison',script)
        compare=importlib.util.module_from_spec(spec); spec.loader.exec_module(compare)
        verified=[]
        for dataset in DATASETS:
            folder=ROOT/'experiments'/dataset
            manifest=read(folder/'confirmatory-dataset.json')
            assert {k:manifest['design'][k] for k in ['development','validation','test']} == {'development':100,'validation':100,'test':1000}
            checks=manifest['verified_checks']
            for key in ['split_id_overlap_count','content_duplicate_count','runtime_label_leakage_count','missing_case_count','pilot_overlap_count']:
                assert checks[key] == 0
            assert all(checks['balanced_within_each_split'].values())
            splits=['test'] if dataset.startswith('ledgar') else ['validation']
            for split in splits:
                prefix=folder/'results'/f'confirmatory-{split}'
                saved=read(Path(str(prefix)+'-comparison.json'))
                n=read(Path(str(prefix)+'-nl.json'))
                h=read(Path(str(prefix)+'-hybrid.json'))
                nc={x['id']:x for x in n['cases']}; hc={x['id']:x for x in h['cases']}
                assert len(nc)==len(n['cases']) and len(hc)==len(h['cases']) and nc.keys()==hc.keys()
                pairs=[(nc[key],hc[key]) for key in sorted(nc)]
                for variant,cases in [('natural_language',n['cases']),('hybrid',h['cases'])]:
                    correct=sum(x['correct'] for x in cases)
                    tokens=sum(x['total_tokens'] for x in cases)
                    assert correct==saved[variant]['correct']
                    assert tokens==saved[variant]['total_tokens']
                    assert f'{100*correct/len(cases):.1f}%' in md
                    assert f'{tokens:,}' in md
                stat=saved['paired_statistics']
                seed=stat['bootstrap_seed']; samples=stat['bootstrap_samples']
                for label,metric,offset in [('accuracy_difference_bootstrap_95',compare.accuracy_difference,0),('token_reduction_bootstrap_95',compare.token_reduction,1)]:
                    actual=compare.paired_bootstrap(pairs,metric,samples,seed+offset)
                    assert all(abs(a-b)<1e-10 for a,b in zip(actual,stat[label])), (dataset,split,label,actual,stat[label])
                delta=100*(sum(x['correct'] for x in h['cases'])-sum(x['correct'] for x in n['cases']))/len(pairs)
                reduction=compare.token_reduction(pairs)
                assert f'{100*reduction:.2f}%' in md
                gate=saved['gate']
                assert gate['minimum_accuracy']==.8 and gate['noninferiority_margin']==.02 and gate['minimum_token_reduction']==.05
                accepted=(min(saved['natural_language']['accuracy'],saved['hybrid']['accuracy'])>=.8 and stat['accuracy_difference_bootstrap_95'][0]>=-.02 and reduction>=.05 and stat['token_reduction_bootstrap_95'][0]>0)
                assert accepted==gate['test_release_pass']
                assert accepted==dataset.startswith('ledgar')
                verified.append({'dataset':dataset,'split':split,'cases':len(pairs),'accuracy_change_points':round(delta,2),'token_reduction_percent':round(100*reduction,2),'accepted':accepted})

        repeats=read(ROOT/'experiments/variance-study/summary.json')
        assert repeats['study_design']['replications']==3
        for dataset in DATASETS:
            record=repeats['datasets'][dataset]
            for seed in record['seeds']:
                comparison=read(ROOT/'experiments'/dataset/'results'/'variance-study-20260903'/f'seed-{seed}-comparison.json')
                assert comparison['gate']['test_release_pass']==dataset.startswith('ledgar')
            for variant in ['nl','hybrid']:
                values=record['variants'][variant]
                assert len(values['accuracy']['values'])==3
                assert values['accuracy']['sample_sd']==0
                assert values['prediction_stability']['any_disagreement_cases']==0
                mean=values['total_tokens']['mean']
                formatted=f'{mean:,.2f}' if mean%1 else f'{mean:,.0f}'
                assert formatted in md, formatted
                measured=[]
                labels=[]
                for seed in record['seeds']:
                    run=read(ROOT/'experiments'/dataset/'results'/'variance-study-20260903'/f'seed-{seed}-{variant}.json')
                    measured.append(sum(c['total_tokens'] for c in run['cases']))
                    labels.append({c['id']:c['actual'] for c in run['cases']})
                    assert sum(c['correct'] for c in run['cases'])/len(run['cases'])==values['accuracy']['values'][0]
                assert labels[0]==labels[1]==labels[2]
                assert abs(statistics.mean(measured)-mean)<1e-8
                assert abs(statistics.stdev(measured)-values['total_tokens']['sample_sd'])<1e-8

    assert not re.search(r'^\| LEDGAR (validation|final test|test)', md, re.M)
    assert '37,147' not in md and '21,104' not in md
    source_hash=hashlib.sha256(md.encode()).hexdigest()
    pages=None
    if opt.artifacts:
        html=(PAPER/'PLaND.html').read_text()
        assert source_hash in html
        html_without_embedded_figures = re.sub(r'src="data:[^"]+"', 'src=""', html)
        assert not re.search(forbidden, html_without_embedded_figures, re.I)
        with zipfile.ZipFile(PAPER/'PLaND.docx') as z:
            xml=z.read('word/document.xml').decode()
            assert not re.search(forbidden,xml,re.I)
            assert source_hash in z.read('docProps/core.xml').decode()
            assert xml.count('<m:oMath>')==3
            assert xml.count('<w:tbl>')==4
            assert xml.count('<w:tblHeader')==4
            styles=z.read('word/styles.xml').decode()
            assert '<w:pBdr>' not in styles
        from pypdf import PdfReader
        pdf=PdfReader(PAPER/'PLaND.pdf')
        pages=len(pdf.pages)
        page_text=[]
        for number,p in enumerate(pdf.pages,1):
            lines=p.extract_text().splitlines()
            if lines and lines[0].strip()==str(number):
                lines=lines[1:]
            page_text.append('\n'.join(lines))
        content='\n'.join(page_text)
        assert not re.search(forbidden,content,re.I)
        phrases=['Appendix A','Appendix B']
        if fresh:
            for item in fresh['datasets'].values():
                for values in [item['main_baseline'],item['main_hybrid']]:
                    if values:
                        phrases += [f"{values['total_tokens']:,}",f"{100*values['accuracy']:.1f}%"]
                if item['comparison']:
                    phrases.append(f"{100*item['comparison']['delta_hybrid_minus_nl']['token_reduction_fraction']:.2f}%")
        else:
            phrases += ['376,088','225,573','40.02%','93.5%','92.7%','31.30%','53.14%','43.08%']
        for phrase in phrases:
            assert phrase in content, phrase
        assert '\ufffd' not in content
        def normalized(value):
            return ''.join(c for c in unicodedata.normalize('NFKC',value).lower() if c.isalnum())
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        normalized_pdf=normalized(content)
        for para in ET.fromstring(xml).iter('{'+ns['w']+'}p'):
            paragraph=''.join(t.text or '' for t in para.iter('{'+ns['w']+'}t'))
            if len(paragraph)>10:
                assert normalized(paragraph) in normalized_pdf, 'Text lost in PDF: '+paragraph[:120]
    repeated_pairs=sum(len(i['repeats']) for i in fresh['datasets'].values()) if fresh else 9
    main_pairs=sum(i['selection'] is not None for i in fresh['datasets'].values()) if fresh else 3
    print(json.dumps({'status':'PASS','source_sha256':source_hash,'main_comparisons':verified,
        'repeated_pairs':repeated_pairs,'total_pairs':main_pairs+repeated_pairs,
        'total_runs':2*(main_pairs+repeated_pairs),'references':18,'tables':4,'figures':3,'pdf_pages':pages},indent=2))

if __name__=='__main__':
    main()
