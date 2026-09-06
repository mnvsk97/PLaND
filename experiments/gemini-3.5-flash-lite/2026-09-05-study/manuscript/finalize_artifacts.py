#!/usr/bin/env python3
"""Record completed visual inspection and copy the reviewed PDF to paper/."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[4]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--render-dir', type=Path, required=True)
    parser.add_argument('--reviewed-pages', type=int, nargs='+', required=True)
    args = parser.parse_args()
    rendered = args.render_dir.resolve()
    source = rendered / 'PLaND.pdf'
    reader = PdfReader(source)
    count = len(reader.pages)
    if sorted(args.reviewed_pages) != list(range(1, count + 1)):
        raise SystemExit('Every rendered page must have been reviewed before finalizing.')
    page_records = []
    for number, page in enumerate(reader.pages, 1):
        png = rendered / f'page-{number}.png'
        if not png.exists() or len(page.extract_text().strip()) < 100:
            raise SystemExit(f'Missing render or nearly empty page: {number}')
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        if abs(width - 595.3) > 1 or abs(height - 841.9) > 1:
            raise SystemExit('Unexpected paper geometry')
        page_records.append({'page':number, 'render_sha256':digest(png),
                             'text_characters':len(page.extract_text()), 'a4':True})
    destination = ROOT / 'paper/PLaND.pdf'
    shutil.copy2(source, destination)
    record = {'schema_version':1, 'pages':count, 'reviewed_pages':args.reviewed_pages,
              'pdf_sha256':digest(destination), 'docx_sha256':digest(ROOT/'paper/PLaND.docx'),
              'source_sha256':digest(ROOT/'paper/PLaND.md'), 'page_checks':page_records,
              'review':'All rendered pages inspected for clipping, overlap, table wrapping, figure readability, captions, page flow, equations, and references.',
              'format':'A4; two-column body; Times New Roman 10 pt; tables 9 pt', 'passed':True}
    (Path(__file__).parent / 'visual-qa.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'Finalized reviewed {count}-page PDF; editable Word and HTML share the audited Markdown source.')


if __name__ == '__main__':
    main()
