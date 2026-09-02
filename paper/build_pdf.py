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
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.graphics import renderSVG
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
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


def architecture_diagram() -> Drawing:
    """Build Figure 1 as a compact vector diagram for a journal column."""
    width, height = 232, 300
    drawing = Drawing(width, height)

    def box(y, h, fill, stroke, title, lines, title_color=colors.white,
            body_color=TEXT):
        drawing.add(Rect(4, y, width - 8, h, rx=8, ry=8,
                         fillColor=fill, strokeColor=stroke, strokeWidth=1.2))
        drawing.add(String(16, y + h - 18, title, fontName="Helvetica-Bold",
                           fontSize=9, fillColor=title_color))
        for index, line in enumerate(lines):
            drawing.add(String(16, y + h - 35 - index * 13, line,
                               fontName="Helvetica", fontSize=7.7,
                               fillColor=body_color))

    def arrow(top, bottom):
        x = width / 2
        drawing.add(Line(x, top, x, bottom + 6, strokeColor=NAVY, strokeWidth=1.4))
        drawing.add(Polygon([x - 4, bottom + 9, x + 4, bottom + 9, x, bottom + 3],
                            fillColor=NAVY, strokeColor=NAVY))

    box(250, 42, NAVY, NAVY, "INPUTS", ["Requirements  |  data sources  |  evals"],
        body_color=colors.white)
    arrow(250, 222)
    box(180, 42, colors.HexColor("#E8F1F7"), NAVY, "GENERATE ONCE",
        ["Initial agent + natural-language SOP"], title_color=NAVY)
    arrow(180, 152)
    box(87, 65, colors.HexColor("#F2F4F5"), colors.HexColor("#66717A"),
        "FROZEN AFTER BASELINE",
        ["Model + system prompt + harness", "Data + scorer + seed + permissions"],
        title_color=colors.HexColor("#39464F"))
    arrow(87, 59)
    box(4, 55, colors.HexColor("#FFF1E8"), RED, "EVOLVABLE SOP PACKAGE",
        ["SKILL.md + direct references", "Tools + scripts + dependencies"],
        title_color=RED)
    return drawing


def evolution_diagram() -> Drawing:
    """Build Figure 2 as a compact vector evaluation loop."""
    width, height = 232, 320
    drawing = Drawing(width, height)

    def process(y, title, subtitle, fill=colors.HexColor("#E8F1F7"), stroke=NAVY):
        drawing.add(Rect(27, y, 178, 43, rx=7, ry=7, fillColor=fill,
                         strokeColor=stroke, strokeWidth=1.1))
        drawing.add(String(40, y + 26, title, fontName="Helvetica-Bold",
                           fontSize=8.4, fillColor=stroke))
        drawing.add(String(40, y + 12, subtitle, fontName="Helvetica",
                           fontSize=7.2, fillColor=TEXT))

    def down(top, bottom):
        x = width / 2
        drawing.add(Line(x, top, x, bottom + 6, strokeColor=NAVY, strokeWidth=1.3))
        drawing.add(Polygon([x - 4, bottom + 9, x + 4, bottom + 9, x, bottom + 3],
                            fillColor=NAVY, strokeColor=NAVY))

    process(269, "1. RUN BASELINE", "Natural-language SOP")
    down(269, 244)
    process(201, "2. MEASURE", "Save traces, quality, tokens, time")
    down(201, 176)
    process(133, "3. CHANGE ONE STEP", "English -> reference or command")
    down(133, 108)
    process(65, "4. TEST AND EVALUATE", "Same frozen model, prompt, and data")
    down(65, 43)

    drawing.add(Polygon([116, 43, 171, 22, 116, 1, 61, 22],
                        fillColor=colors.HexColor("#FFF1E8"), strokeColor=RED,
                        strokeWidth=1.2))
    drawing.add(String(88, 19, "PASS GATES?", fontName="Helvetica-Bold",
                       fontSize=7.5, fillColor=RED))

    drawing.add(Line(171, 22, 221, 22, strokeColor=colors.HexColor("#2E7D32"),
                     strokeWidth=1.3))
    drawing.add(Polygon([218, 26, 226, 22, 218, 18],
                        fillColor=colors.HexColor("#2E7D32"),
                        strokeColor=colors.HexColor("#2E7D32")))
    drawing.add(String(181, 31, "YES", fontName="Helvetica-Bold", fontSize=7,
                       fillColor=colors.HexColor("#2E7D32")))
    drawing.add(String(180, 5, "ACCEPT", fontName="Helvetica-Bold", fontSize=8,
                       fillColor=colors.HexColor("#2E7D32")))

    drawing.add(Line(61, 22, 12, 22, strokeColor=RED, strokeWidth=1.3))
    drawing.add(Line(12, 22, 12, 154, strokeColor=RED, strokeWidth=1.3))
    drawing.add(Line(12, 154, 27, 154, strokeColor=RED, strokeWidth=1.3))
    drawing.add(Polygon([23, 158, 31, 154, 23, 150], fillColor=RED,
                        strokeColor=RED))
    drawing.add(String(15, 31, "NO", fontName="Helvetica-Bold", fontSize=7,
                       fillColor=RED))
    drawing.add(String(17, 8, "REJECT", fontName="Helvetica-Bold", fontSize=7.5,
                       fillColor=RED))
    drawing.add(String(17, 142, "NEXT", fontName="Helvetica-Bold", fontSize=6.7,
                       fillColor=RED))
    return drawing


def evolution_path_diagram() -> Drawing:
    """Build the typical PLaND progression from open-ended to graph-based."""
    width, height = 232, 250
    drawing = Drawing(width, height)

    def stage(y, h, fill, stroke, title, subtitle, note):
        drawing.add(Rect(8, y, width - 16, h, rx=8, ry=8, fillColor=fill,
                         strokeColor=stroke, strokeWidth=1.2))
        drawing.add(String(20, y + h - 18, title, fontName="Helvetica-Bold",
                           fontSize=8.6, fillColor=stroke))
        drawing.add(String(20, y + h - 34, subtitle, fontName="Helvetica",
                           fontSize=7.5, fillColor=TEXT))
        drawing.add(String(20, y + 10, note, fontName="Helvetica-Oblique",
                           fontSize=6.8, fillColor=colors.HexColor("#59636B")))

    def down(top, bottom):
        x = width / 2
        drawing.add(Line(x, top, x, bottom + 6, strokeColor=NAVY, strokeWidth=1.3))
        drawing.add(Polygon([x - 4, bottom + 9, x + 4, bottom + 9, x, bottom + 3],
                            fillColor=NAVY, strokeColor=NAVY))

    stage(181, 61, colors.HexColor("#E8F1F7"), NAVY,
          "1. OPEN-ENDED AGENT", "DeepAgents: broad reasoning and tool use",
          "Useful when the path is not yet known")
    down(181, 157)
    stage(88, 69, colors.HexColor("#FFF1E8"), RED,
          "2. HYBRID WORKFLOW", "Code for stable work + model judgment",
          "The normal PLaND target")
    down(88, 64)
    stage(3, 61, colors.HexColor("#EDF6ED"), colors.HexColor("#2E7D32"),
          "3. MOSTLY DETERMINISTIC GRAPH", "LangGraph steps + intelligence where needed",
          "Most structured endpoint when evidence supports it")
    return drawing


def inline(value: str) -> str:
    value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", value)
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
                story.append(KeepTogether([
                    Paragraph("<br/>".join(inline(x or " ") for x in code), st["code"])
                ]))
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
        if line.strip() == "<!-- architecture-diagram -->":
            flush_paragraph(); flush_list()
            story.append(KeepTogether([architecture_diagram(), Spacer(1, 4)]))
        elif line.strip() == "<!-- evolution-diagram -->":
            flush_paragraph(); flush_list()
            story.append(KeepTogether([evolution_diagram(), Spacer(1, 4)]))
        elif line.strip() == "<!-- evolution-path-diagram -->":
            flush_paragraph(); flush_list()
            story.append(KeepTogether([evolution_path_diagram(), Spacer(1, 4)]))
        elif line.strip() == "<!-- pagebreak -->":
            flush_paragraph(); flush_list(); story.append(PageBreak())
        elif line.startswith("# "):
            flush_paragraph(); flush_list()
            story.append(Paragraph(inline(line[2:]), st["title"])); seen_title = True
        elif seen_title and (line.startswith("**Maddipatla Naga Venkata Sai Krishna") or line.startswith("*Author affiliations") or line.startswith("*Affiliations")):
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
    canvas.drawString(19*mm, 11*mm, "PLaND — Revised Manuscript")
    canvas.drawRightString(width-19*mm, 11*mm, f"{doc.page}")
    canvas.restoreState()


def main() -> int:
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure_path = source.parent / "figures" / "architecture.svg"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    renderSVG.drawToFile(architecture_diagram(), str(figure_path))
    renderSVG.drawToFile(evolution_diagram(), str(source.parent / "figures" / "evolution-loop.svg"))
    renderSVG.drawToFile(evolution_path_diagram(), str(source.parent / "figures" / "evolution-path.svg"))
    doc = BaseDocTemplate(str(destination), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=20*mm, bottomMargin=18*mm, title="PLaND - Path to Least Non Determinism")
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
