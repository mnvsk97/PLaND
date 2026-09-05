#!/usr/bin/env node
// Render the single manuscript source to editable Word and self-contained HTML.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const sharp = require('sharp');

async function main() {
  const { marked } = await import(require.resolve('marked'));
  const paper = __dirname;
  const root = path.dirname(paper);
  const python = process.env.PLAND_PYTHON || 'python3';
  function run(script) {
    const result = spawnSync(python, [path.join(paper, script)], { cwd: root, stdio: 'inherit' });
    if (result.status !== 0) throw new Error(`${script} failed`);
  }
  // Original SVG artwork is read-only input; never regenerate the diagrams.
  const tmp = path.join(root, 'tmp/paper-build/figures');
  fs.mkdirSync(tmp, {recursive:true});
  const names = ['evolution-path', 'architecture', 'evolution-loop'];
  for (const name of names) {
    await sharp(path.join(paper, 'figures', `${name}.svg`), {density:300})
      .png().toFile(path.join(tmp, `${name}.png`));
  }
  run('build_manuscript.py');
  const source = fs.readFileSync(path.join(paper, 'PLaND.md'), 'utf8');
  const hash = crypto.createHash('sha256').update(source).digest('hex');
  let text = source;
  const markers = ['evolution-path-diagram', 'architecture-diagram', 'evolution-diagram'];
  for (let i=0; i<names.length; i++) {
    const svg = fs.readFileSync(path.join(paper, 'figures', `${names[i]}.svg`));
    text = text.replace(`<!-- ${markers[i]} -->`, `<figure><img alt="${names[i].replaceAll('-', ' ')}" src="data:image/svg+xml;base64,${svg.toString('base64')}"></figure>`);
  }
  let body = marked.parse(text).replace(/<pre><code class="language-equation">([\s\S]*?)<\/code><\/pre>/g, (_, math) => `<div class="equation">${math.trim().replaceAll('Qmin', 'Q<sub>min</sub>').replaceAll('\n','<br>')}</div>`);
  body = body.replace('<h2>1 Introduction</h2>', '<main class="columns"><h2>1 Introduction</h2>') + '</main>';
  fs.writeFileSync(path.join(paper, 'PLaND.html'), `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="source-sha256" content="${hash}"><title>PLaND Path to Least Non Determinism</title>
<style>body{max-width:850px;margin:48px auto;padding:0 28px;font:17px/1.5 Georgia,serif;color:#161616}h1,h2,h3{line-height:1.2}h1{color:#004a93}h2{color:#0070c0}h3{color:#000}h1{font-size:29px}h2{font-size:23px;margin-top:32px}h3{font-size:19px;margin-top:24px}a{color:#245579}table{border-collapse:collapse;width:100%;font-size:14px;margin:16px 0 22px}td,th{border:1px solid #d9d9d9;padding:9px 10px;text-align:center}td:first-child,th:first-child{text-align:left}th{background:#e8eef3}thead{display:table-header-group}tr{break-inside:avoid}figure{margin:20px 0}img{width:100%;height:auto;max-width:320px;display:block;margin:auto}code{font-size:.86em;overflow-wrap:anywhere}.equation{text-align:center;font-family:'Cambria Math',serif;line-height:1.7;margin:15px 0}.columns{column-count:2;column-gap:24px}.columns table{column-span:all}p{text-align:justify}h2,h3{break-after:avoid}figure{break-inside:avoid}@media(max-width:700px){.columns{column-count:1}}@media print{@page{size:A4;margin:19mm}body{font:10pt/1.1 'Times New Roman',serif;margin:0;max-width:none;padding:0}h2,h3{break-after:avoid}figure{break-inside:avoid}table{font-size:9pt}}</style></head><body>${body}</body></html>\n`);
  console.log('Built PLaND.docx and PLaND.html from source ' + hash);
}
main().catch(error => { console.error(error); process.exit(1); });
