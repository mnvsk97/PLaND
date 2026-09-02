#!/usr/bin/env python3
"""Render the PLaND Markdown manuscript as a clean technical-paper PDF."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


NAVY = colors.HexColor("#18324B")
RED = colors.HexColor("#A52A2A")
PALE = colors.HexColor("#EEF2F4")
TEXT = colors.HexColor("#222222")


def inline(value: str) -> str:
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", value)
    value = re.sub(r"\[(.+?)\]\((.+?)\)", r"<link href='\2' color='#18324B'>\1</link>", value)
    return value


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=NAVY, alignment=TA_CENTER, spaceAfter=8),
        "authors": ParagraphStyle("Authors", parent=base["Normal"], fontName="Helvetica", fontSize=9.5, leading=12, alignment=TA_CENTER, textColor=TEXT, spaceAfter=12),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=12.5, leading=15, textColor=NAVY, spaceBefore=10, spaceAfter=5, keepWithNext=True),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=RED, spaceBefore=8, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Times-Roman", fontSize=9.3, leading=12.2, alignment=TA_JUSTIFY, textColor=TEXT, spaceAfter=5),
        "abstract": ParagraphStyle("Abstract", parent=base["BodyText"], fontName="Times-Italic", fontSize=9.1, leading=12, alignment=TA_JUSTIFY, leftIndent=8*mm, rightIndent=8*mm, spaceAfter=7),
        "quote": ParagraphStyle("Quote", parent=base["BodyText"], fontName="Times-Italic", fontSize=9.3, leading=12.2, leftIndent=8*mm, rightIndent=5*mm, borderColor=RED, borderWidth=0.8, borderPadding=5, spaceAfter=6),
        "code": ParagraphStyle("Code", parent=base["Code"], fontName="Courier", fontSize=7.7, leading=10, backColor=PALE, borderPadding=5, spaceAfter=6),
        "list": ParagraphStyle("List", parent=base["BodyText"], fontName="Times-Roman", fontSize=9.2, leading=11.8, leftIndent=3*mm),
        "table": ParagraphStyle("Table", parent=base["BodyText"], fontName="Helvetica", fontSize=7.4, leading=9),
    }


def markdown_table(lines: list[str], st) -> Table:
    rows = []
    header_style = ParagraphStyle("TableHeader", parent=st["table"], textColor=colors.white, fontName="Helvetica-Bold")
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        cell_style = header_style if not rows else st["table"]
        rows.append([Paragraph(inline(cell), cell_style) for cell in cells])
    # Main paper pages use two columns. Keep tables within one column so they
    # remain close to the paragraph that introduces them.
    width = 82 * mm
    table = Table(rows, colWidths=[width / len(rows[0])] * len(rows[0]), repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB4BA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def parse(markdown: str):
    st = styles()
    lines = markdown.splitlines()
    story = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_ordered = False
    in_code = False
    code: list[str] = []
    abstract_mode = False
    seen_title = False

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            style = st["abstract"] if abstract_mode else st["body"]
            story.append(Paragraph(inline(" ".join(x.strip() for x in paragraph)), style))
            paragraph = []

    def flush_list():
        nonlocal list_items
        if list_items:
            items = [ListItem(Paragraph(inline(x), st["list"]), leftIndent=9) for x in list_items]
            story.append(ListFlowable(items, bulletType="1" if list_ordered else "bullet", leftIndent=15, bulletFontSize=7, spaceAfter=5))
            list_items = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush_paragraph(); flush_list()
            if in_code:
                story.append(Paragraph("<br/>".join(inline(x or " ") for x in code), st["code"]))
                code = []
            in_code = not in_code
            i += 1; continue
        if in_code:
            code.append(line); i += 1; continue
        if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].startswith("|"):
            flush_paragraph(); flush_list(); block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i]); i += 1
            story.extend([Spacer(1, 2), KeepTogether([markdown_table(block, st)]), Spacer(1, 6)])
            continue
        if line.startswith("# "):
            flush_paragraph(); flush_list()
            story.append(Paragraph(inline(line[2:]), st["title"])); seen_title = True
        elif seen_title and (line.startswith("**Sai Krishna") or line.startswith("*Affiliations")):
            flush_paragraph(); flush_list(); story.append(Paragraph(inline(line.replace("**", "").strip("*")), st["authors"]))
        elif line.startswith("## "):
            flush_paragraph(); flush_list(); abstract_mode = line[3:].strip() == "Abstract"
            story.append(Paragraph(inline(line[3:]), st["h1"]))
        elif line.startswith("### "):
            flush_paragraph(); flush_list(); abstract_mode = False
            story.append(Paragraph(inline(line[4:]), st["h2"]))
        elif line.startswith("> "):
            flush_paragraph(); flush_list(); block = []
            while i < len(lines) and lines[i].startswith("> "):
                block.append(lines[i][2:]); i += 1
            story.append(Paragraph(inline(" ".join(block)), st["quote"]))
            continue
        elif re.match(r"^\d{1,2}\. ", line) or line.startswith("- "):
            flush_paragraph()
            ordered = bool(re.match(r"^\d{1,2}\. ", line))
            if list_items and ordered != list_ordered: flush_list()
            list_ordered = ordered
            list_items.append(re.sub(r"^(?:\d{1,2}\.|-)\s+", "", line))
        elif not line.strip():
            flush_paragraph(); flush_list()
        elif list_items:
            list_items[-1] += " " + line.strip()
        else:
            paragraph.append(line)
        i += 1
    flush_paragraph(); flush_list()
    return story


def decorate(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(RED); canvas.setLineWidth(0.8)
    canvas.line(19*mm, height-15*mm, width-19*mm, height-15*mm)
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.HexColor("#66717A"))
    canvas.drawString(19*mm, 11*mm, "PLaND — Technical Paper Draft")
    canvas.drawRightString(width-19*mm, 11*mm, f"{doc.page}")
    canvas.restoreState()


def main() -> int:
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(destination), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=20*mm, bottomMargin=18*mm, title="Path to Least Non-Determinism")
    first_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="front-matter")
    gutter = 6 * mm
    column_width = (doc.width - gutter) / 2
    left_frame = Frame(doc.leftMargin, doc.bottomMargin, column_width, doc.height, id="left-column")
    right_frame = Frame(doc.leftMargin + column_width + gutter, doc.bottomMargin, column_width, doc.height, id="right-column")
    doc.addPageTemplates([
        PageTemplate(id="front", frames=[first_frame], onPage=decorate, autoNextPageTemplate="columns"),
        PageTemplate(id="columns", frames=[left_frame, right_frame], onPage=decorate),
    ])
    doc.build(parse(source.read_text(encoding="utf-8")))
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
