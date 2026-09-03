#!/usr/bin/env python3
"""Build a self-contained arXiv source bundle from paper/PAPER.md."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tarfile
from pathlib import Path


FIGURES = {
    "<!-- architecture-diagram -->": "architecture.jpg",
    "<!-- evolution-diagram -->": "evolution-loop.jpg",
    "<!-- evolution-path-diagram -->": "evolution-path.jpg",
}


def escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def inline(value: str) -> str:
    tokens: list[str] = []
    def hold(rendered: str) -> str:
        tokens.append(rendered)
        return f"@@TOKEN{len(tokens) - 1}@@"
    def code_span(raw: str) -> str:
        # TeX treats an unpunctuated hash as one unbreakable monospace word.
        # Add explicit break opportunities without changing the visible value.
        if len(raw) > 24 and re.fullmatch(r"[0-9A-Za-z]+", raw):
            parts = [escape(raw[index:index + 12]) for index in range(0, len(raw), 12)]
            return r"\texttt{" + r"}\allowbreak\texttt{".join(parts) + "}"
        return r"\texttt{" + escape(raw) + "}"
    value = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)",
                   lambda m: hold(r"\href{" + escape(m.group(2)) + "}{" + escape(m.group(1)) + "}"), value)
    value = re.sub(r"(?<!\S)(https?://\S+)", lambda m: hold(r"\url{" + escape(m.group(1).rstrip(".,;")) + "}"), value)
    value = re.sub(r"\*\*(.+?)\*\*", lambda m: hold(r"\textbf{" + escape(m.group(1)) + "}"), value)
    value = re.sub(r"`(.+?)`", lambda m: hold(code_span(m.group(1))), value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: hold(r"\emph{" + escape(m.group(1)) + "}"), value)
    value = escape(value)
    for index, token in enumerate(tokens):
        value = value.replace(f"@@TOKEN{index}@@", token)
    return value


def table_block(lines: list[str], caption: str | None) -> str:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    columns = len(rows[0])
    widths = "@{}" + "X" * columns + "@{}"
    body = []
    for index, row in enumerate(rows):
        body.append(" & ".join(inline(cell) for cell in row) + " \\\\")
        if index == 0:
            body.append(r"\midrule")
    title = inline(caption or "")
    return "\n".join([
        r"\begin{table*}[t]", r"\centering", r"\small",
        f"\\caption{{{title}}}" if title else "",
        f"\\begin{{tabularx}}{{\\textwidth}}{{{widths}}}", r"\toprule",
        *body, r"\bottomrule", r"\end{tabularx}", r"\end{table*}",
    ])


def convert_body(markdown: str) -> str:
    lines = markdown.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("## Introduction"))
    output: list[str] = []
    paragraph: list[str] = []
    pending_caption: str | None = None
    pending_figure: str | None = None
    in_references = False

    def flush() -> None:
        if paragraph:
            output.append(inline(" ".join(part.strip() for part in paragraph)))
            output.append("")
            paragraph.clear()

    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped in FIGURES:
            flush()
            pending_figure = FIGURES[stripped]
        elif stripped.startswith("**Figure ") and pending_figure:
            flush()
            caption = re.sub(r"^\*\*Figure\s+\d+\.\s*", "", stripped).replace("**", "", 1)
            width = "0.62" if pending_figure == "evolution-loop.jpg" else "0.64"
            output.extend([r"\begin{figure*}[t]", r"\centering",
                           f"\\includegraphics[width={width}\\textwidth]{{{pending_figure}}}",
                           f"\\caption{{{inline(caption)}}}", r"\end{figure*}", ""])
            pending_figure = None
        elif stripped.startswith("**Table "):
            flush()
            pending_caption = re.sub(r"^\*\*Table\s+\d+\.\s*", "", stripped).rstrip("*")
        elif line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|"):
            flush()
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i])
                i += 1
            output.extend([table_block(block, pending_caption), ""])
            pending_caption = None
            continue
        elif line.startswith("## "):
            flush()
            heading = line[3:]
            in_references = heading == "References"
            if in_references:
                output.append(r"\begin{thebibliography}{99}")
            else:
                output.append(f"\\section{{{inline(heading)}}}")
        elif line.startswith("### "):
            flush()
            output.append(f"\\subsection{{{inline(line[4:])}}}")
        elif in_references and re.match(r"^\[\d+\]", line):
            flush()
            match = re.match(r"^\[(\d+)\]\s*(.*)", line)
            output.append(f"\\bibitem{{ref{match.group(1)}}} {inline(match.group(2))}")
        elif line.startswith("- "):
            flush()
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"\\item {inline(lines[i][2:])}")
                i += 1
            output.extend([r"\begin{itemize}", *items, r"\end{itemize}", ""])
            continue
        elif stripped.startswith("<!--"):
            pass
        elif not stripped:
            flush()
        else:
            paragraph.append(line)
        i += 1
    flush()
    if in_references:
        output.append(r"\end{thebibliography}")
    return "\n".join(output)


def build(markdown: str, output_dir: Path, figures_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    title = re.search(r"^# (.+)$", markdown, re.M).group(1)
    author_line = re.search(r"^\*\*(Maddipatla.+?)\*\*, \*\*(Asit.+?)\*\*$", markdown, re.M)
    authors = escape(author_line.group(1)) + r" \quad " + escape(author_line.group(2))
    abstract = re.search(r"^## Abstract\s+(.+?)(?=^\*\*Keywords:)", markdown, re.S | re.M).group(1).strip()
    keywords = re.search(r"^\*\*Keywords:\*\*\s*(.+)$", markdown, re.M).group(1)
    latex = r"""\documentclass[9pt,a4paper,twocolumn]{article}
\usepackage[a4paper,top=19mm,bottom=18mm,left=19mm,right=19mm,columnsep=6mm]{geometry}
\usepackage{mathptmx}
\usepackage[T1]{fontenc}
\usepackage{xcolor,graphicx,booktabs,tabularx,hyperref,fancyhdr}
\definecolor{journalblue}{HTML}{004A93}
\definecolor{headingblue}{HTML}{0070C0}
\definecolor{rulegreen}{HTML}{557030}
\definecolor{abstractgreen}{HTML}{F1F5E8}
\hypersetup{colorlinks=true,urlcolor=journalblue,linkcolor=journalblue}
\pagestyle{fancy}\fancyhf{}
\fancyhead[R]{\scriptsize Maddipatla Naga Venkata Sai Krishna \& Asit Kumar Sahoo, Sch J Eng Tech}
\renewcommand{\headrulewidth}{0.5pt}\renewcommand{\headrule}{\hbox to\headwidth{\color{rulegreen}\leaders\hrule height \headrulewidth\hfill}}
\fancyfoot[L]{\scriptsize PLaND $\mid$ Preprint - arXiv identifier pending}
\fancyfoot[R]{\scriptsize\thepage}
\renewcommand{\footrulewidth}{0.5pt}
\setlength{\parindent}{1.2em}\setlength{\parskip}{0.15em}
\makeatletter
\renewcommand\section{\@startsection{section}{1}{0pt}{0.7ex}{0.25ex}{\color{headingblue}\normalfont\large}}
\renewcommand\subsection{\@startsection{subsection}{2}{0pt}{0.6ex}{0.2ex}{\normalfont\normalsize}}
\makeatother
\begin{document}
\twocolumn[
\begin{minipage}{\textwidth}
{\color{journalblue}\LARGE Scholars Journal of Engineering and Technology\par}
\vspace{0.5mm}
{\scriptsize Abbreviated Key Title: Sch J Eng Tech \quad Journal homepage: \url{https://saspublishers.com/journal/sjet/home}\par}
\vspace{2mm}
{\color{rulegreen}\hrule}\vspace{3mm}
""" + f"{{\\color{{journalblue}}\\LARGE {escape(title)}\\par}}\n\\vspace{{1mm}}\n" + \
        f"{{\\normalsize {authors}\\par}}\n\\vspace{{1mm}}\n" + \
        r"{\color{red}\hrule}\vspace{2mm}" + "\n" + \
        r"\begin{center}\begin{minipage}{0.98\textwidth}\colorbox{journalblue}{\parbox{0.97\textwidth}{\color{white}\textbf{Abstract}\hfill Original Research Article}}" + "\n" + \
        r"\colorbox{abstractgreen}{\parbox{0.97\textwidth}{" + inline(abstract) + "\\\\[1mm]\\textbf{Keywords:} " + inline(keywords) + "}}\n" + \
        r"\end{minipage}\end{center}\vspace{2mm}" + "\n\\end{minipage}\n]\n" + convert_body(markdown) + "\n\\end{document}\n"
    (output_dir / "main.tex").write_text(latex, encoding="utf-8")
    for image in FIGURES.values():
        shutil.copy2(figures_dir / image, output_dir / image)
    metadata = {
        "title": title,
        "authors": [author_line.group(1), author_line.group(2)],
        "primary_category": "cs.CL",
        "cross_lists": ["cs.AI", "cs.LG"],
        "arxiv_identifier": "pending",
        "external_submission_performed": False,
        "license_selection": "pending_author_selection_at_submission",
        "evidence_reference": "same Git commit as manuscript",
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# PLaND arXiv source bundle\n\nPrimary category: `cs.CL`; cross-lists: `cs.AI`, `cs.LG`.\n\n"
        "Evidence reference: the source and experiment evidence are preserved in the same Git commit as the manuscript.\n\n"
        "The arXiv identifier and license selection are pending. This bundle has not been uploaded or submitted.\n\n"
        "Compile with `pdflatex main.tex` twice. The archive contains only `main.tex`, the three figure JPEGs, this README, and `metadata.json`.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("PAPER.md"))
    parser.add_argument("--output-dir", type=Path, default=Path("output/arxiv/PLAND_ARXIV_SOURCE"))
    parser.add_argument("--archive", type=Path, default=Path("output/arxiv/PLAND_ARXIV_SOURCE.tar.gz"))
    args = parser.parse_args()
    build(args.source.read_text(encoding="utf-8"), args.output_dir, args.source.parent / "figures")
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.archive, "w:gz") as archive:
        for path in sorted(args.output_dir.iterdir()):
            archive.add(path, arcname=path.name)
    print(args.output_dir.resolve())
    print(args.archive.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
