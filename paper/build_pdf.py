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
    FrameBreak,
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


NAVY = colors.HexColor("#004A93")
RED = colors.HexColor("#D21F26")
PALE = colors.HexColor("#F1F5E8")
GREEN = colors.HexColor("#557030")
BLUE = colors.HexColor("#0070C0")
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
        "FROZEN BEFORE MEASUREMENT",
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

    process(269, "1. RUN BASELINE", "English SOP; check viability")
    down(269, 244)
    process(201, "2. MEASURE", "Save traces, quality, tokens, time")
    down(201, 176)
    process(133, "3. CHANGE ONE STEP", "English -> reference or command")
    down(133, 108)
    process(65, "4. TEST AND EVALUATE", "Development mines; validation promotes")
    down(65, 59)

    drawing.add(Polygon([116, 59, 171, 38, 116, 17, 61, 38],
                        fillColor=colors.HexColor("#FFF1E8"), strokeColor=RED,
                        strokeWidth=1.2))
    drawing.add(String(88, 35, "PASS GATES?", fontName="Helvetica-Bold",
                       fontSize=7.5, fillColor=RED))

    drawing.add(Line(171, 38, 221, 38, strokeColor=colors.HexColor("#2E7D32"),
                     strokeWidth=1.3))
    drawing.add(Polygon([218, 42, 226, 38, 218, 34],
                        fillColor=colors.HexColor("#2E7D32"),
                        strokeColor=colors.HexColor("#2E7D32")))
    drawing.add(String(181, 47, "YES", fontName="Helvetica-Bold", fontSize=7,
                       fillColor=colors.HexColor("#2E7D32")))

    drawing.add(Line(61, 38, 12, 38, strokeColor=RED, strokeWidth=1.3))
    drawing.add(Line(12, 38, 12, 154, strokeColor=RED, strokeWidth=1.3))
    drawing.add(Line(12, 154, 27, 154, strokeColor=RED, strokeWidth=1.3))
    drawing.add(Polygon([23, 158, 31, 154, 23, 150], fillColor=RED,
                        strokeColor=RED))
    drawing.add(String(15, 47, "NO", fontName="Helvetica-Bold", fontSize=7,
                       fillColor=RED))
    drawing.add(String(17, 142, "NEXT", fontName="Helvetica-Bold", fontSize=6.7,
                       fillColor=RED))
    return drawing


def evolution_path_diagram() -> Drawing:
    """Show actual LEDGAR NL/hybrid excerpts and the graph-based target."""
    width, height = 232, 250
    drawing = Drawing(width, height)

    def box(y, h, fill, stroke, title):
        drawing.add(Rect(8, y, width - 16, h, rx=8, ry=8, fillColor=fill,
                         strokeColor=stroke, strokeWidth=1.2))
        drawing.add(String(20, y + h - 18, title, fontName="Helvetica-Bold",
                           fontSize=8.2, fillColor=stroke))

    def line(x, y, value, size=7.0, font="Helvetica", color=TEXT):
        drawing.add(String(x, y, value, fontName=font, fontSize=size,
                           fillColor=color))

    def down(top, bottom):
        x = width / 2
        drawing.add(Line(x, top, x, bottom + 6, strokeColor=NAVY, strokeWidth=1.3))
        drawing.add(Polygon([x - 4, bottom + 9, x + 4, bottom + 9, x, bottom + 3],
                            fillColor=NAVY, strokeColor=NAVY))

    muted = colors.HexColor("#59636B")
    box(161, 84, colors.HexColor("#E8F1F7"), NAVY,
        "1. NATURAL-LANGUAGE SOP")
    line(20, 214, "Actual LEDGAR excerpt", 6.2, "Helvetica-Oblique", muted)
    line(20, 202, "1. Read the complete contract clause.", 6.4)
    line(20, 190, "2. Identify the clause's main legal function...", 6.4)
    line(20, 178, "3. Compare that function with every allowed label.", 6.4)
    line(20, 166, "4. Select the single best label...", 6.4)

    down(161, 149)
    box(58, 91, colors.HexColor("#FFF1E8"), RED,
        "2. HYBRID SOP")
    line(20, 118, "Actual LEDGAR excerpt", 6.2, "Helvetica-Oblique", muted)
    line(20, 106, "1. Read the complete contract clause.", 6.4)
    line(20, 94, "2. Run `python classify.py` on the clause and labels;", 6.4,
         "Helvetica-Bold", colors.HexColor("#2E7D32"))
    line(27, 82, "accept only a high-confidence result.", 6.4,
         "Helvetica-Bold", colors.HexColor("#2E7D32"))
    line(20, 70, "3. If the command abstains, use the NL steps.", 6.4)

    down(58, 46)
    green = colors.HexColor("#2E7D32")
    box(3, 43, colors.HexColor("#EDF6ED"), green,
        "3. GRAPH-BASED SOP - MATURE TARGET")
    line(20, 11, "Stable nodes in code; a few semantic nodes use the model.",
         6.2, "Helvetica-Oblique", muted)
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
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Times-Roman", fontSize=17, leading=20, textColor=NAVY, alignment=0, spaceAfter=3, borderColor=RED, borderWidth=0, borderPadding=0),
        "authors": ParagraphStyle("Authors", parent=base["Normal"], fontName="Times-Roman", fontSize=9.2, leading=11, alignment=0, textColor=TEXT, spaceAfter=7, borderColor=RED, borderWidth=0, borderPadding=0),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName="Times-Roman", fontSize=11.5, leading=13.5, textColor=BLUE, spaceBefore=7, spaceAfter=3, keepWithNext=True),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName="Times-Roman", fontSize=9.8, leading=11.5, textColor=TEXT, spaceBefore=6, spaceAfter=2, keepWithNext=True),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.6, leading=10.4, alignment=TA_JUSTIFY, firstLineIndent=5*mm, textColor=TEXT, spaceAfter=3),
        "abstract": ParagraphStyle("Abstract", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.7, leading=10.5, alignment=TA_JUSTIFY, backColor=PALE, borderColor=GREEN, borderWidth=0.5, borderPadding=5, spaceAfter=4),
        "keywords": ParagraphStyle("Keywords", parent=base["BodyText"], fontName="Times-Roman", fontSize=8.5, leading=10, alignment=TA_JUSTIFY, backColor=PALE, borderColor=GREEN, borderWidth=0.5, borderPadding=5, spaceAfter=2),
        "quote": ParagraphStyle("Quote", parent=base["BodyText"], fontName="Times-Italic", fontSize=9.3, leading=12.2, leftIndent=8*mm, rightIndent=5*mm, borderColor=RED, borderWidth=0.8, borderPadding=5, spaceAfter=6),
        "code": ParagraphStyle("Code", parent=base["Code"], fontName="Courier", fontSize=7.7, leading=10, backColor=PALE, borderPadding=5, spaceAfter=6),
        "list": ParagraphStyle("List", parent=base["BodyText"], fontName="Times-Roman", fontSize=9.2, leading=11.8, leftIndent=3*mm),
        "table": ParagraphStyle("Table", parent=base["BodyText"], fontName="Helvetica", fontSize=7.4, leading=9),
        "table_caption": ParagraphStyle("TableCaption", parent=base["BodyText"], fontName="Times-Bold", fontSize=9.3, leading=12.2, textColor=TEXT, spaceAfter=2, keepWithNext=True),
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
    pending_table_caption = None
    pending_table_heading = None

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
            table_group = []
            if pending_table_heading is not None:
                table_group.append(pending_table_heading)
                pending_table_heading = None
            if pending_table_caption is not None:
                table_group.extend([pending_table_caption, Spacer(1, 2)])
                pending_table_caption = None
            table_group.append(markdown_table(block, st))
            story.extend([KeepTogether(table_group), Spacer(1, 6)])
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
        elif line.startswith("**Keywords:**"):
            flush_paragraph(); flush_list()
            story.append(Paragraph(inline(line), st["keywords"]))
            story.append(FrameBreak())
            abstract_mode = False
        elif line.startswith("## "):
            flush_paragraph(); flush_list(); abstract_mode = line[3:].strip() == "Abstract"
            heading = Paragraph(inline(line[3:]), st["h1"])
            if line[3:].strip() == "Results":
                pending_table_heading = heading
            else:
                story.append(heading)
        elif line.startswith("### "):
            flush_paragraph(); flush_list(); abstract_mode = False
            story.append(Paragraph(inline(line[4:]), st["h2"]))
        elif line.startswith("**Table "):
            flush_paragraph(); flush_list()
            pending_table_caption = Paragraph(inline(line), st["table_caption"])
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
    if doc.page == 1:
        canvas.setFillColor(NAVY)
        canvas.setFont("Times-Roman", 16)
        canvas.drawString(19*mm, height-14*mm, "Scholars Journal of Engineering and Technology")
        canvas.setFont("Times-Roman", 7.2)
        canvas.setFillColor(TEXT)
        canvas.drawString(19*mm, height-18*mm, "Abbreviated Key Title: Sch J Eng Tech")
        canvas.drawString(19*mm, height-21.5*mm, "Journal homepage: https://saspublishers.com/journal/sjet/home")
    else:
        canvas.setFont("Times-Roman", 6.8)
        canvas.setFillColor(TEXT)
        canvas.drawRightString(width-19*mm, height-12.5*mm,
                               "Maddipatla Naga Venkata Sai Krishna & Asit Kumar Sahoo, Sch J Eng Tech")
    canvas.setStrokeColor(GREEN); canvas.setLineWidth(0.7)
    canvas.line(19*mm, height-24*mm if doc.page == 1 else height-14*mm,
                width-19*mm, height-24*mm if doc.page == 1 else height-14*mm)
    canvas.setStrokeColor(GREEN); canvas.setLineWidth(0.5)
    canvas.rect(19*mm, 8.5*mm, width-38*mm, 5*mm, stroke=1, fill=0)
    canvas.setFillColor(TEXT); canvas.setFont("Times-Roman", 6.6)
    canvas.drawString(21*mm, 10.2*mm, "PLaND | Submission manuscript")
    canvas.setFillColor(colors.HexColor("#DCE8C6"))
    canvas.rect(width-33*mm, 8.5*mm, 14*mm, 5*mm, stroke=1, fill=1)
    canvas.setFillColor(TEXT)
    canvas.drawCentredString(width-26*mm, 10.2*mm, f"{doc.page}")
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
    doc = BaseDocTemplate(str(destination), pagesize=A4, leftMargin=19*mm, rightMargin=19*mm, topMargin=27*mm, bottomMargin=16*mm, title="PLaND - Path to Least Non Determinism")
    gutter = 6 * mm
    column_width = (doc.width - gutter) / 2
    # Keep the complete front matter (including keywords) in the full-width
    # frame. This mirrors the published SJET first page and ensures the body
    # begins in the lower-left column rather than skipping to the right.
    first_top_height = 100 * mm
    first_lower_height = doc.height - first_top_height - 4*mm
    first_frame = Frame(doc.leftMargin, doc.bottomMargin + first_lower_height + 4*mm,
                        doc.width, first_top_height, id="front-matter")
    first_left = Frame(doc.leftMargin, doc.bottomMargin, column_width,
                       first_lower_height, id="first-left-column")
    first_right = Frame(doc.leftMargin + column_width + gutter, doc.bottomMargin,
                        column_width, first_lower_height, id="first-right-column")
    left_frame = Frame(doc.leftMargin, doc.bottomMargin, column_width, doc.height, id="left-column")
    right_frame = Frame(doc.leftMargin + column_width + gutter, doc.bottomMargin, column_width, doc.height, id="right-column")
    doc.addPageTemplates([
        PageTemplate(id="front", frames=[first_frame, first_left, first_right], onPage=decorate, autoNextPageTemplate="columns"),
        PageTemplate(id="columns", frames=[left_frame, right_frame], onPage=decorate),
    ])
    doc.build(parse(source.read_text(encoding="utf-8")))
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
