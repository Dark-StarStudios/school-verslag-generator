from __future__ import annotations

import io
import json
import os
import re
import zipfile
import base64
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from flask import Flask, Response, jsonify, render_template, request, send_file
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Flowable,
    Image as ReportLabImage,
    KeepInFrame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

DECLARATION = (
    "Hierbij verklaar ik dat:\n"
    "Het door mij gemaakte werk zelf geschreven is en dat ik geen teksten heb "
    "overgenomen uit andere stageverslagen, scripties, overige geschriften en "
    "literatuur zonder de bron te hebben vermeld.\n"
    "De inhoud van dit verslag komt, voor wat betreft de feiten en de verrichte "
    "werkzaamheden, geheel overeen met de werkelijkheid.\n"
    "De beschreven door mij uitgevoerde werkzaamheden zijn daadwerkelijk door "
    "mij verricht."
)

ALLOWED_DOCUMENT_FONTS = {"Arial", "Georgia", "Times New Roman", "Verdana"}
PDF_FONT_FAMILIES = {
    "Arial": ("Helvetica", "Helvetica-Bold"),
    "Georgia": ("Times-Roman", "Times-Bold"),
    "Times New Roman": ("Times-Roman", "Times-Bold"),
    "Verdana": ("Helvetica", "Helvetica-Bold"),
}


def clean(value, fallback=""):
    return str(value if value is not None else fallback).strip()


def safe_filename(value):
    value = re.sub(r'[\\/:*?"<>|]+', "-", clean(value, "verslag"))
    value = re.sub(r"\s+", "-", value).strip("-.")
    return value[:80] or "verslag"


def to_iso_date(value):
    value = clean(value)
    match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", value)
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else value


def display_date(value):
    value = clean(value)
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else value


def document_design(report):
    raw = report.get("design", {}) if isinstance(report.get("design", {}), dict) else {}
    heading_color = clean(raw.get("heading_color"), "#5B9BD5").upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", heading_color):
        heading_color = "#5B9BD5"
    heading_font = clean(raw.get("heading_font"), "Arial")
    body_font = clean(raw.get("body_font"), "Arial")
    cover_background_color = clean(raw.get("cover_background_color"), "#FFFFFF").upper()
    cover_gradient_end_color = clean(raw.get("cover_gradient_end_color"), "#3858E8").upper()
    cover_text_color = clean(raw.get("cover_text_color"), "#FFFFFF").upper()
    declaration_color = clean(raw.get("declaration_color"), "#FF5F57").upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", cover_background_color):
        cover_background_color = "#FFFFFF"
    if not re.fullmatch(r"#[0-9A-F]{6}", cover_text_color):
        cover_text_color = "#FFFFFF"
    if not re.fullmatch(r"#[0-9A-F]{6}", cover_gradient_end_color):
        cover_gradient_end_color = "#3858E8"
    if not re.fullmatch(r"#[0-9A-F]{6}", declaration_color):
        declaration_color = "#FF5F57"
    cover_background_type = clean(raw.get("cover_background_type"), "solid")
    if cover_background_type not in {"solid", "gradient"}:
        cover_background_type = "solid"
    cover_gradient_direction = clean(raw.get("cover_gradient_direction"), "diagonal")
    if cover_gradient_direction not in {"vertical", "horizontal", "diagonal"}:
        cover_gradient_direction = "diagonal"
    return {
        "heading_color": heading_color,
        "heading_font": heading_font if heading_font in ALLOWED_DOCUMENT_FONTS else "Arial",
        "body_font": body_font if body_font in ALLOWED_DOCUMENT_FONTS else "Arial",
        "cover_background_color": cover_background_color,
        "cover_background_type": cover_background_type,
        "cover_gradient_end_color": cover_gradient_end_color,
        "cover_gradient_direction": cover_gradient_direction,
        "cover_text_color": cover_text_color,
        "declaration_color": declaration_color,
        "cover_logo": raw.get("cover_logo") if isinstance(raw.get("cover_logo"), dict) else None,
    }


def rgb_color(hex_color):
    value = hex_color.lstrip("#")
    return RGBColor(*(int(value[index:index + 2], 16) for index in (0, 2, 4)))


def mix_hex(start, end, amount):
    start_rgb = tuple(int(start.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4))
    end_rgb = tuple(int(end.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4))
    mixed = tuple(round(a + (b - a) * amount) for a, b in zip(start_rgb, end_rgb))
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


class GradientPanel(Flowable):
    """Fixed-size cover panel with native PDF gradient and overlaid content."""

    def __init__(self, content, width, height, start_color, end_color, direction):
        super().__init__()
        self.width = width
        self.height = height
        self.start_color = colors.HexColor(start_color)
        self.end_color = colors.HexColor(end_color)
        self.direction = direction
        self.content = KeepInFrame(width - 32 * mm, height - 26 * mm, content, mode="shrink")

    def wrap(self, available_width, available_height):
        self.content.wrapOn(self.canv, self.width - 32 * mm, self.height - 26 * mm)
        return self.width, self.height

    def draw(self):
        if self.direction == "horizontal":
            points = (0, 0, self.width, 0)
        elif self.direction == "vertical":
            points = (0, self.height, 0, 0)
        else:
            points = (0, self.height, self.width, 0)
        self.canv.linearGradient(*points, (self.start_color, self.end_color), (0, 1), extend=True)
        self.content.drawOn(self.canv, 16 * mm, 13 * mm)


def normalize_report(raw):
    """Accept the native schema and the public matrijzen concept shape."""
    if not isinstance(raw, dict):
        raise ValueError("Het JSON-bestand moet een object bevatten.")
    if raw.get("schema") == "school-verslag/1.0":
        # Older concepts may not contain fields added in a later form version.
        return merge_report(empty_report(), raw)

    # matrijzen.ictmbo.nl concept compatibility
    if "werkprocessen" in raw and any(k in raw for k in ("opleiding_id", "kd_id", "ov")):
        report = empty_report()
        report["student"].update({
            "name": clean(raw.get("naam")),
            "student_number": clean(raw.get("ov")),
            "class_name": clean(raw.get("klas")),
            "company": clean(raw.get("bedrijf")),
            "practice_supervisor": clean(raw.get("praktijk")),
            "bpv_supervisor": clean(raw.get("bpv")),
        })
        report["project"].update({
            "title": clean(raw.get("examen"), "Examenverslag"),
            "exam_name": clean(raw.get("examen")),
            "exam_number": clean(raw.get("ep")),
            "start_date": to_iso_date(raw.get("start")),
            "end_date": to_iso_date(raw.get("eind")),
            "description": clean(raw.get("omschrijving")),
            "products": [clean(x) for x in raw.get("products", []) if clean(x)],
        })
        selected = []
        for wp in raw.get("werkprocessen", []):
            code = clean(wp.get("code"))
            base = next((x for x in report["work_processes"] if x["code"] == code), None)
            selected.append({
                **(base or {}),
                "selected": True,
                "code": code,
                "title": clean(wp.get("naam")),
                "competencies": split_competencies(wp.get("competenties")),
                "indicators": wp.get("pi") or [],
                "accountability": clean(wp.get("desc")),
                "evidence": [],
                "evidence_images": [],
            })
        known = {x["code"] for x in selected}
        report["work_processes"] = selected + [
            {**x, "selected": False}
            for x in report["work_processes"]
            if x["code"] not in known
        ]
        return report
    raise ValueError("Onbekend JSON-schema.")


def merge_report(defaults, saved):
    """Recursively add missing defaults without overwriting saved values."""
    if not isinstance(defaults, dict) or not isinstance(saved, dict):
        return deepcopy(saved)
    merged = deepcopy(defaults)
    for key, saved_value in saved.items():
        default_value = merged.get(key)
        merged[key] = (
            merge_report(default_value, saved_value)
            if isinstance(default_value, dict) and isinstance(saved_value, dict)
            else deepcopy(saved_value)
        )
    return merged


def split_competencies(value):
    if isinstance(value, list):
        return [clean(x) for x in value if clean(x)]
    return [x.strip() for x in clean(value).split(",") if x.strip()]


def empty_report():
    with open(BASE_DIR / "data" / "default_report.json", encoding="utf-8") as handle:
        return json.load(handle)


def text_list(items):
    return [clean(x) for x in (items or []) if clean(x)]


def selected_work_processes(report):
    return [wp for wp in report.get("work_processes", []) if wp.get("selected")]


def selected_keuzedelen(report):
    return [
        item for item in report.get("keuzedelen", [])
        if any(process.get("selected") for process in item.get("work_processes", []))
    ]


def evidence_images(items):
    """Decode safe image data URLs stored in a local concept."""
    decoded = []
    for index, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        data_url = clean(item.get("data"))
        match = re.fullmatch(r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\s]+)", data_url)
        if not match:
            continue
        try:
            blob = base64.b64decode(match.group(2), validate=True)
        except (ValueError, TypeError):
            continue
        if not blob or len(blob) > 3 * 1024 * 1024:
            continue
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[match.group(1)]
        source_name = clean(item.get("name") or f"bewijs-{index + 1}")
        decoded.append({
            "name": safe_filename(Path(source_name).stem) + "." + extension,
            "mime": match.group(1),
            "bytes": blob,
        })
    return decoded


def report_sections(report):
    student = report.get("student", {})
    project = report.get("project", {})
    scope = report.get("scope", {})
    evaluation = report.get("evaluation", {})
    activities = text_list(report.get("activities"))
    resources = report.get("resources", {})
    planning = report.get("planning", [])

    sections = []
    sections.append(("Inleiding", [project.get("introduction") or project.get("description", "")]))
    project_blocks = []
    for label, key, formatter in (
        ("Examennaam", "exam_name", clean),
        ("Examennummer", "exam_number", clean),
        ("Startdatum examen", "start_date", display_date),
        ("Einddatum examen", "end_date", display_date),
    ):
        value = formatter(project.get(key))
        if value:
            project_blocks.append((label, value))
    products = text_list(project.get("products"))
    if products:
        project_blocks.append(("Op te leveren producten", products))
    if project_blocks:
        sections.append(("Projectgegevens", project_blocks))
    exam_blocks = []
    if activities:
        exam_blocks.append(("Wat moest ik doen om het resultaat te behalen", activities))
    for label, key in (
        ("Materialen en software", "materials"),
        ("Mensen", "people"),
        ("Middelen", "means"),
        ("Kennis", "knowledge"),
    ):
        values = text_list(resources.get(key))
        if values:
            exam_blocks.append((label, values))
    sections.append(("Examenactiviteiten", exam_blocks))
    sections.append(("Grenzen en randvoorwaarden", [
        ("Wat hoort wel bij het examen", text_list(scope.get("included"))),
        ("Wat hoort niet bij het examen", text_list(scope.get("excluded"))),
        ("Wat moet de opdrachtgever ter beschikking stellen", text_list(scope.get("provided"))),
    ]))
    plan_blocks = []
    for phase in planning:
        title = clean(phase.get("phase"))
        period = clean(phase.get("period"))
        plan_blocks.append((f"{title}{' - ' + period if period else ''}", text_list(phase.get("tasks"))))
    sections.append(("Planning", plan_blocks))
    accountability = []
    for wp in selected_work_processes(report):
        evidence = text_list(wp.get("evidence"))
        body = clean(wp.get("accountability"))
        accountability.append((f"Werkproces {wp.get('code', '')} {wp.get('title', '')}", {
            "body": body,
            "competencies": wp.get("competencies", []),
            "indicators": wp.get("indicators", []),
            "evidence": evidence,
            "evidence_images": evidence_images(wp.get("evidence_images")),
        }))
    sections.append(("Verantwoording", accountability))
    choices = []
    for choice in selected_keuzedelen(report):
        processes = []
        for wp in choice.get("work_processes", []):
            if not wp.get("selected"):
                continue
            processes.append((f"{wp.get('code', '')} - {wp.get('title', '')}", {
                "body": clean(wp.get("accountability")),
                "evidence": text_list(wp.get("evidence")),
                "evidence_images": evidence_images(wp.get("evidence_images")),
            }))
        choices.append((f"{choice.get('code', '')} - {choice.get('title', '')}", {
            "certificate": clean(choice.get("certificate")),
            "work_processes": processes,
        }))
    if choices:
        sections.append(("Keuzedelen", choices))
    sections.append(("Evaluatie", [
        ("Vakinhoudelijke evaluatie", clean(evaluation.get("professional"))),
        ("Persoonlijke evaluatie", clean(evaluation.get("personal"))),
        ("Volgend project", clean(evaluation.get("next_project"))),
    ]))
    sections.append(("Verklaring", [DECLARATION]))
    return sections


@app.get("/")
def index():
    return render_template("index.html", default_report=empty_report())


@app.get("/api/template")
def template():
    return jsonify(empty_report())


@app.post("/api/normalize")
def normalize():
    try:
        return jsonify(normalize_report(request.get_json(force=True)))
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/export/<kind>")
def export(kind):
    try:
        report = normalize_report(request.get_json(force=True))
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    if kind not in {"pdf", "docx", "odt"}:
        return jsonify({"error": "Onbekend exportformaat."}), 404
    title = report.get("project", {}).get("title") or "examenverslag"
    student = report.get("student", {}).get("name") or "student"
    filename = f"{safe_filename(title)}-{safe_filename(student)}.{kind}"
    builders = {"pdf": build_pdf, "docx": build_docx, "odt": build_odt}
    mime = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "odt": "application/vnd.oasis.opendocument.text",
    }[kind]
    output = builders[kind](report)
    return send_file(output, mimetype=mime, as_attachment=True, download_name=filename)


class ReportDocTemplate(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self.draw_page))

    def draw_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D7DBE2"))
        canvas.line(24 * mm, 17 * mm, 186 * mm, 17 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#687184"))
        canvas.drawString(24 * mm, 10 * mm, "Examenverslag")
        canvas.drawRightString(186 * mm, 10 * mm, f"Pagina {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            level = getattr(flowable, "toc_level", None)
            if level is not None:
                self.notify("TOCEntry", (level, flowable.getPlainText(), self.page))


def pdf_styles(report):
    design = document_design(report)
    body_regular, _ = PDF_FONT_FAMILIES[design["body_font"]]
    _, heading_bold = PDF_FONT_FAMILIES[design["heading_font"]]
    heading_color = colors.HexColor(design["heading_color"])
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName=heading_bold, fontSize=28, leading=32, textColor=heading_color, alignment=TA_LEFT, spaceAfter=14))
    styles.add(ParagraphStyle(name="CoverMeta", parent=styles["BodyText"], fontName=body_regular, fontSize=11, leading=17, textColor=colors.HexColor("#475467")))
    styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName=heading_bold, fontSize=18, leading=22, textColor=heading_color, spaceBefore=12, spaceAfter=9, keepWithNext=True))
    styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName=heading_bold, fontSize=12.5, leading=16, textColor=heading_color, spaceBefore=10, spaceAfter=5, keepWithNext=True))
    styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName=body_regular, fontSize=10.2, leading=15, textColor=colors.HexColor("#20242C"), spaceAfter=7))
    styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName=body_regular, fontSize=8.5, leading=12, textColor=colors.HexColor("#586174"), spaceAfter=5))
    styles.add(ParagraphStyle(name="Bulletx", parent=styles["BodyText"], fontName=body_regular, fontSize=10.2, leading=14, leftIndent=14, firstLineIndent=-7, bulletIndent=4, spaceAfter=3))
    return styles


def p(text, style):
    safe = escape(clean(text)).replace("\n", "<br/>")
    return Paragraph(safe or " ", style)


def add_pdf_heading(story, text, style, level):
    item = p(text, style)
    item.toc_level = level
    story.append(item)


def add_pdf_list(story, items, styles):
    for item in text_list(items):
        story.append(Paragraph("- " + escape(item), styles["Bulletx"]))


def build_pdf(report):
    stream = io.BytesIO()
    styles = pdf_styles(report)
    design = document_design(report)
    body_regular, _ = PDF_FONT_FAMILIES[design["body_font"]]
    _, heading_bold = PDF_FONT_FAMILIES[design["heading_font"]]
    doc = ReportDocTemplate(stream, pagesize=A4, rightMargin=24 * mm, leftMargin=24 * mm, topMargin=22 * mm, bottomMargin=23 * mm, title=clean(report.get("project", {}).get("title"), "Examenverslag"))
    student = report.get("student", {})
    project = report.get("project", {})
    meta = [
        ["Naam", student.get("name", "")], ["OV-nummer", student.get("student_number", "")],
        ["Klas", student.get("class_name", "")], ["Versie", project.get("version", "1.0")],
        ["Datum", display_date(project.get("report_date", ""))], ["Examennaam", project.get("exam_name", "")],
        ["Examennummer", project.get("exam_number", "")],
        ["Startdatum examen", display_date(project.get("start_date", ""))],
        ["Einddatum examen", display_date(project.get("end_date", ""))],
        ["Stagebedrijf", student.get("company", "")], ["Praktijkopleider", student.get("practice_supervisor", "")],
        ["BPV-begeleider", student.get("bpv_supervisor", "")],
    ]
    logo = evidence_images([design.get("cover_logo")])
    custom_cover = bool(logo or design["cover_background_color"] != "#FFFFFF" or design["cover_background_type"] == "gradient")
    if custom_cover:
        story = [Spacer(1, 10 * mm)]
        if logo:
            picture = ReportLabImage(io.BytesIO(logo[0]["bytes"]))
            picture._restrictSize(95 * mm, 34 * mm)
            story += [picture, Spacer(1, 10 * mm)]
        cover_title = ParagraphStyle(name="CoverTitleCustom", parent=styles["CoverTitle"], textColor=colors.HexColor(design["cover_text_color"]), fontSize=30, leading=34)
        cover_version = ParagraphStyle(name="CoverVersionCustom", parent=styles["CoverMeta"], textColor=colors.HexColor(design["cover_text_color"]), fontSize=18, leading=23)
        cover_meta = ParagraphStyle(name="CoverMetaCustom", parent=styles["CoverMeta"], textColor=colors.HexColor(design["cover_text_color"]), fontSize=13, leading=19)
        panel_content = [
            p(project.get("title", "Examenverslag"), cover_title),
            p("Versie " + clean(project.get("version"), "1.0"), cover_version),
            Spacer(1, 13 * mm),
            p(student.get("name", ""), cover_meta),
            p(display_date(project.get("report_date", "")), cover_meta),
            Spacer(1, 28 * mm),
            p("Stagebedrijf: " + clean(student.get("company"), "-"), cover_meta),
            p("Stagebegeleider: " + clean(student.get("practice_supervisor"), "-"), cover_meta),
            p("BPV: " + clean(student.get("bpv_supervisor"), "-"), cover_meta),
        ]
        if design["cover_background_type"] == "gradient":
            panel = GradientPanel(
                panel_content,
                162 * mm,
                150 * mm,
                design["cover_background_color"],
                design["cover_gradient_end_color"],
                design["cover_gradient_direction"],
            )
        else:
            panel = Table([[panel_content]], colWidths=[162 * mm], rowHeights=[150 * mm])
            panel.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(design["cover_background_color"])),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 16 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 14 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12 * mm),
            ]))
        story += [panel, PageBreak()]
    else:
        story = [Spacer(1, 32 * mm), p(project.get("title", "Examenverslag"), styles["CoverTitle"])]
        subtitle = project.get("subtitle") or project.get("exam_name") or "Examenverslag"
        story += [p(subtitle, styles["H2x"]), Spacer(1, 10 * mm)]
        table = Table([[p(a, styles["Smallx"]), p(b, styles["Bodyx"])] for a, b in meta if clean(b)], colWidths=[42 * mm, 105 * mm])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E6ED")), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story += [table, PageBreak()]

    story.append(p("Inhoudsopgave", styles["H1x"]))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(name="TOC1", fontName=heading_bold, fontSize=10.5, leading=16, leftIndent=0, firstLineIndent=0, textColor=colors.HexColor(design["heading_color"])),
        ParagraphStyle(name="TOC2", fontName=body_regular, fontSize=9.5, leading=14, leftIndent=10 * mm, firstLineIndent=0, textColor=colors.HexColor("#475467")),
    ]
    story += [toc, PageBreak()]
    for title, content in report_sections(report):
        add_pdf_heading(story, title, styles["H1x"], 0)
        if title == "Verantwoording":
            for sub, data in content:
                add_pdf_heading(story, sub, styles["H2x"], 1)
                if data.get("competencies"):
                    story.append(p("Competenties: " + ", ".join(data["competencies"]), styles["Smallx"]))
                story.append(p(data.get("body"), styles["Bodyx"]))
                if data.get("evidence"):
                    story.append(p("Bewijs", styles["H2x"]))
                    add_pdf_list(story, data["evidence"], styles)
                for image in data.get("evidence_images", []):
                    story.append(p(image["name"], styles["Smallx"]))
                    picture = ReportLabImage(io.BytesIO(image["bytes"]))
                    picture._restrictSize(155 * mm, 95 * mm)
                    story += [picture, Spacer(1, 3 * mm)]
        elif title == "Keuzedelen":
            for choice_title, choice in content:
                add_pdf_heading(story, choice_title, styles["H2x"], 1)
                if choice.get("certificate"):
                    story.append(p("Code: " + choice["certificate"], styles["Smallx"]))
                for process_title, data in choice.get("work_processes", []):
                    add_pdf_heading(story, process_title, styles["H2x"], 1)
                    story.append(p(data.get("body"), styles["Bodyx"]))
                    if data.get("evidence"):
                        story.append(p("Bewijs", styles["H2x"]))
                        add_pdf_list(story, data["evidence"], styles)
                    for image in data.get("evidence_images", []):
                        story.append(p(image["name"], styles["Smallx"]))
                        picture = ReportLabImage(io.BytesIO(image["bytes"]))
                        picture._restrictSize(155 * mm, 95 * mm)
                        story += [picture, Spacer(1, 3 * mm)]
        elif title in {"Projectgegevens", "Examenactiviteiten", "Grenzen en randvoorwaarden", "Planning", "Evaluatie"}:
            for sub, body in content:
                if not clean(sub):
                    continue
                add_pdf_heading(story, sub, styles["H2x"], 1)
                if isinstance(body, list):
                    add_pdf_list(story, body, styles)
                else:
                    story.append(p(body, styles["Bodyx"]))
        elif title == "Verklaring":
            declaration_background = mix_hex(design["declaration_color"], "#FFFFFF", 0.92)
            declaration_table = Table([[p(content[0], styles["Bodyx"])]], colWidths=[158 * mm])
            declaration_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(declaration_background)),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E6ED")),
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(design["declaration_color"])),
                ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 6 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6 * mm),
            ]))
            story.append(declaration_table)
        else:
            for body in content:
                story.append(p(body, styles["Bodyx"]))
        story.append(Spacer(1, 4 * mm))
    doc.multiBuild(story)
    stream.seek(0)
    return stream


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_border(cell, **edges):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge, options in edges.items():
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        for key, value in options.items():
            element.set(qn(f"w:{key}"), str(value))


def add_docx_toc(doc):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    doc.settings._element.append(update)


def add_docx_field(run, instruction):
    begin = OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = instruction
    separate = OxmlElement("w:fldChar"); separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])


def configure_docx(doc, report):
    design = document_design(report)
    section = doc.sections[0]
    section.top_margin = Cm(2.2); section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5); section.right_margin = Cm(2.5)
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = design["body_font"]; normal.font.size = Pt(10.5); normal.font.color.rgb = RGBColor(32, 36, 44)
    normal.paragraph_format.space_after = Pt(7); normal.paragraph_format.line_spacing = 1.15
    for name, size, before, after in (("Title", 28, 0, 14), ("Heading 1", 18, 14, 8), ("Heading 2", 13, 10, 5)):
        style = styles[name]
        style.font.name = design["heading_font"]; style.font.size = Pt(size); style.font.bold = True; style.font.color.rgb = rgb_color(design["heading_color"])
        style.paragraph_format.space_before = Pt(before); style.paragraph_format.space_after = Pt(after); style.paragraph_format.keep_with_next = True
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("Pagina ")
    add_docx_field(footer.add_run(), "PAGE")


def add_docx_bullets(doc, items):
    for item in text_list(items):
        doc.add_paragraph(item, style="List Bullet")


def build_docx(report):
    doc = Document()
    configure_docx(doc, report)
    student = report.get("student", {}); project = report.get("project", {})
    design = document_design(report)
    rows = [
        ("Naam", student.get("name")), ("OV-nummer", student.get("student_number")),
        ("Klas", student.get("class_name")), ("Versie", project.get("version", "1.0")),
        ("Datum", display_date(project.get("report_date"))), ("Examennaam", project.get("exam_name")),
        ("Examennummer", project.get("exam_number")),
        ("Startdatum examen", display_date(project.get("start_date"))),
        ("Einddatum examen", display_date(project.get("end_date"))),
        ("Stagebedrijf", student.get("company")), ("Praktijkopleider", student.get("practice_supervisor")),
        ("BPV-begeleider", student.get("bpv_supervisor")),
    ]
    logo = evidence_images([design.get("cover_logo")])
    custom_cover = bool(logo or design["cover_background_color"] != "#FFFFFF" or design["cover_background_type"] == "gradient")
    if custom_cover:
        doc.add_paragraph()
        if logo:
            doc.add_picture(io.BytesIO(logo[0]["bytes"]), width=Cm(10.5))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()
        content = (
            (project.get("title", "Examenverslag"), 32, True, 0),
            ("Versie " + clean(project.get("version"), "1.0"), 20, False, 4),
            (student.get("name", ""), 17, False, 22),
            (display_date(project.get("report_date", "")), 17, False, 0),
            ("Stagebedrijf: " + clean(student.get("company"), "-"), 14, False, 80),
            ("Stagebegeleider: " + clean(student.get("practice_supervisor"), "-"), 14, False, 0),
            ("BPV: " + clean(student.get("bpv_supervisor"), "-"), 14, False, 0),
        )
        if design["cover_background_type"] == "gradient":
            table = doc.add_table(rows=len(content), cols=1)
            table.autofit = False
            row_heights = (34, 21, 24, 15, 45, 13, 13)
            for index, ((text, size, bold, _), row) in enumerate(zip(content, table.rows)):
                row.height = Cm(row_heights[index] / 10)
                row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
                cell = row.cells[0]
                cell.width = Cm(16)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                gradient_amount = index / max(1, len(content) - 1)
                set_cell_shading(cell, mix_hex(design["cover_background_color"], design["cover_gradient_end_color"], gradient_amount).lstrip("#"))
                set_cell_border(cell, top={"val": "nil"}, bottom={"val": "nil"}, left={"val": "nil"}, right={"val": "nil"})
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_after = Pt(0)
                run = paragraph.add_run(clean(text))
                run.bold = bold
                run.font.name = design["heading_font"] if index < 2 else design["body_font"]
                run.font.size = Pt(size)
                run.font.color.rgb = rgb_color(design["cover_text_color"])
        else:
            table = doc.add_table(rows=1, cols=1)
            table.autofit = False
            cell = table.cell(0, 0)
            cell.width = Cm(16)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            set_cell_shading(cell, design["cover_background_color"].lstrip("#"))
            for index, (text, size, bold, before) in enumerate(content):
                paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
                paragraph.paragraph_format.space_before = Pt(before)
                paragraph.paragraph_format.space_after = Pt(2)
                run = paragraph.add_run(clean(text))
                run.bold = bold
                run.font.name = design["heading_font"] if index < 2 else design["body_font"]
                run.font.size = Pt(size)
                run.font.color.rgb = rgb_color(design["cover_text_color"])
    else:
        doc.add_paragraph(project.get("title", "Examenverslag"), style="Title")
        doc.add_paragraph(project.get("subtitle") or project.get("exam_name") or "Examenverslag", style="Subtitle")
        doc.add_paragraph()
        table = doc.add_table(rows=0, cols=2)
        table.autofit = False
        for i, (label, value) in enumerate((x for x in rows if clean(x[1]))):
            cells = table.add_row().cells
            cells[0].width = Cm(4.2); cells[1].width = Cm(11.8)
            cells[0].text = label; cells[1].text = clean(value)
            cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cells[1].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if i % 2:
                set_cell_shading(cells[0], "F5F7FA"); set_cell_shading(cells[1], "F5F7FA")
    doc.add_page_break()
    doc.add_heading("Inhoudsopgave", level=1)
    add_docx_toc(doc)
    doc.add_page_break()
    for title, content in report_sections(report):
        doc.add_heading(title, level=1)
        if title == "Verantwoording":
            for sub, data in content:
                doc.add_heading(sub, level=2)
                if data.get("competencies"):
                    para = doc.add_paragraph()
                    para.add_run("Competenties: ").bold = True
                    para.add_run(", ".join(data["competencies"]))
                doc.add_paragraph(data.get("body") or "")
                if data.get("evidence"):
                    para = doc.add_paragraph(); para.add_run("Bewijs").bold = True
                    add_docx_bullets(doc, data["evidence"])
                for image in data.get("evidence_images", []):
                    doc.add_paragraph(image["name"], style="Caption")
                    doc.add_picture(io.BytesIO(image["bytes"]), width=Cm(15.5))
        elif title == "Keuzedelen":
            for choice_title, choice in content:
                doc.add_heading(choice_title, level=2)
                if choice.get("certificate"):
                    para = doc.add_paragraph(); para.add_run("Code: ").bold = True; para.add_run(choice["certificate"])
                for process_title, data in choice.get("work_processes", []):
                    doc.add_heading(process_title, level=2)
                    doc.add_paragraph(data.get("body") or "")
                    if data.get("evidence"):
                        para = doc.add_paragraph(); para.add_run("Bewijs").bold = True
                        add_docx_bullets(doc, data["evidence"])
                    for image in data.get("evidence_images", []):
                        doc.add_paragraph(image["name"], style="Caption")
                        doc.add_picture(io.BytesIO(image["bytes"]), width=Cm(15.5))
        elif title in {"Projectgegevens", "Examenactiviteiten", "Grenzen en randvoorwaarden", "Planning", "Evaluatie"}:
            for sub, body in content:
                if not clean(sub):
                    continue
                doc.add_heading(sub, level=2)
                if isinstance(body, list):
                    add_docx_bullets(doc, body)
                else:
                    doc.add_paragraph(clean(body))
        elif title == "Verklaring":
            declaration_table = doc.add_table(rows=1, cols=1)
            cell = declaration_table.cell(0, 0)
            set_cell_shading(cell, mix_hex(design["declaration_color"], "#FFFFFF", 0.92).lstrip("#"))
            set_cell_border(
                cell,
                left={"val": "single", "sz": "28", "color": design["declaration_color"].lstrip("#")},
                top={"val": "single", "sz": "4", "color": "E2E6ED"},
                right={"val": "single", "sz": "4", "color": "E2E6ED"},
                bottom={"val": "single", "sz": "4", "color": "E2E6ED"},
            )
            cell.paragraphs[0].add_run(clean(content[0]))
        else:
            for body in content:
                doc.add_paragraph(clean(body))
    output = io.BytesIO(); doc.save(output); output.seek(0); return output


def odt_paragraph(text, style="Text_20_body"):
    lines = escape(clean(text)).replace("\n", "<text:line-break/>")
    return f'<text:p text:style-name="{style}">{lines}</text:p>'


def odt_list(items):
    values = text_list(items)
    if not values:
        return ""
    return '<text:list text:style-name="L1">' + "".join(
        f'<text:list-item>{odt_paragraph(item)}</text:list-item>' for item in values
    ) + "</text:list>"


def build_odt(report):
    student = report.get("student", {}); project = report.get("project", {})
    design = document_design(report)
    embedded_images = []
    body = []
    cover_fields = (
        ("Naam", student.get("name")), ("OV-nummer", student.get("student_number")),
        ("Klas", student.get("class_name")), ("Versie", project.get("version", "1.0")),
        ("Datum", display_date(project.get("report_date"))), ("Examennaam", project.get("exam_name")),
        ("Examennummer", project.get("exam_number")),
        ("Startdatum examen", display_date(project.get("start_date"))),
        ("Einddatum examen", display_date(project.get("end_date"))),
        ("Stagebedrijf", student.get("company")), ("Praktijkopleider", student.get("practice_supervisor")),
        ("BPV-begeleider", student.get("bpv_supervisor")),
    )
    logo = evidence_images([design.get("cover_logo")])
    custom_cover = bool(logo or design["cover_background_color"] != "#FFFFFF" or design["cover_background_type"] == "gradient")
    if custom_cover:
        if logo:
            archive_name = f"Pictures/cover-{logo[0]['name']}"
            embedded_images.append((archive_name, logo[0]["mime"], logo[0]["bytes"]))
            body.append(f'<text:p><draw:frame draw:name="Voorbladlogo" text:anchor-type="paragraph" svg:width="10.5cm" svg:height="3.4cm"><draw:image xlink:href="{escape(archive_name)}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame></text:p>')
        panel = [
            odt_paragraph(project.get("title", "Examenverslag"), "CoverTitleWhite"),
            odt_paragraph("Versie " + clean(project.get("version"), "1.0"), "CoverVersionWhite"),
            odt_paragraph(student.get("name", ""), "CoverTextWhite"),
            odt_paragraph(display_date(project.get("report_date", "")), "CoverTextWhite"),
            odt_paragraph("Stagebedrijf: " + clean(student.get("company"), "-"), "CoverTextWhite"),
            odt_paragraph("Stagebegeleider: " + clean(student.get("practice_supervisor"), "-"), "CoverTextWhite"),
            odt_paragraph("BPV: " + clean(student.get("bpv_supervisor"), "-"), "CoverTextWhite"),
        ]
        body.append('<table:table table:name="Voorblad"><table:table-column table:number-columns-repeated="1"/><table:table-row><table:table-cell table:style-name="CoverCell" office:value-type="string">' + "".join(panel) + '</table:table-cell></table:table-row></table:table>')
    else:
        body.extend([odt_paragraph(project.get("title", "Examenverslag"), "Title"), odt_paragraph(project.get("subtitle") or project.get("exam_name") or "Examenverslag", "Subtitle")])
        for label, value in cover_fields:
            if clean(value):
                body.append(odt_paragraph(f"{label}: {clean(value)}"))
    body.append('<text:p text:style-name="PageBreak"/>')
    body.append(odt_paragraph("Inhoudsopgave", "Heading_20_1"))
    body.append('<text:table-of-content text:name="Inhoudsopgave1" text:protected="false"><text:table-of-content-source text:outline-level="2"/><text:index-body><text:p>Werk de inhoudsopgave bij in LibreOffice.</text:p></text:index-body></text:table-of-content>')
    body.append('<text:p text:style-name="PageBreak"/>')
    for title, content in report_sections(report):
        body.append(odt_paragraph(title, "Heading_20_1"))
        if title == "Verantwoording":
            for sub, data in content:
                body.append(odt_paragraph(sub, "Heading_20_2"))
                if data.get("competencies"):
                    body.append(odt_paragraph("Competenties: " + ", ".join(data["competencies"])))
                body.append(odt_paragraph(data.get("body")))
                if data.get("evidence"):
                    body.append(odt_paragraph("Bewijs", "Heading_20_2")); body.append(odt_list(data["evidence"]))
                for image in data.get("evidence_images", []):
                    archive_name = f"Pictures/{len(embedded_images) + 1}-{image['name']}"
                    embedded_images.append((archive_name, image["mime"], image["bytes"]))
                    body.append(odt_paragraph(image["name"]))
                    body.append(f'<draw:frame draw:name="Afbeelding{len(embedded_images)}" text:anchor-type="paragraph" svg:width="15.5cm" svg:height="9.5cm"><draw:image xlink:href="{escape(archive_name)}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>')
        elif title == "Keuzedelen":
            for choice_title, choice in content:
                body.append(odt_paragraph(choice_title, "Heading_20_2"))
                if choice.get("certificate"):
                    body.append(odt_paragraph("Code: " + choice["certificate"]))
                for process_title, data in choice.get("work_processes", []):
                    body.append(odt_paragraph(process_title, "Heading_20_2"))
                    body.append(odt_paragraph(data.get("body")))
                    if data.get("evidence"):
                        body.append(odt_paragraph("Bewijs", "Heading_20_2")); body.append(odt_list(data["evidence"]))
                    for image in data.get("evidence_images", []):
                        archive_name = f"Pictures/{len(embedded_images) + 1}-{image['name']}"
                        embedded_images.append((archive_name, image["mime"], image["bytes"]))
                        body.append(odt_paragraph(image["name"]))
                        body.append(f'<draw:frame draw:name="Afbeelding{len(embedded_images)}" text:anchor-type="paragraph" svg:width="15.5cm" svg:height="9.5cm"><draw:image xlink:href="{escape(archive_name)}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>')
        elif title in {"Projectgegevens", "Examenactiviteiten", "Grenzen en randvoorwaarden", "Planning", "Evaluatie"}:
            for sub, value in content:
                if clean(sub): body.append(odt_paragraph(sub, "Heading_20_2"))
                body.append(odt_list(value) if isinstance(value, list) else odt_paragraph(value))
        elif title == "Verklaring":
            body.append('<table:table table:name="Verklaring"><table:table-column table:number-columns-repeated="1"/><table:table-row><table:table-cell table:style-name="DeclarationCell" office:value-type="string">' + odt_paragraph(content[0]) + '</table:table-cell></table:table-row></table:table>')
        else:
            body.extend(odt_paragraph(x) for x in content)
    odt_gradient_angle = {"vertical": "0", "horizontal": "900", "diagonal": "1350"}[design["cover_gradient_direction"]]
    cover_fill = ('draw:fill="gradient" draw:fill-gradient-name="CoverGradient"' if design["cover_background_type"] == "gradient" else f'fo:background-color="{design["cover_background_color"]}"')
    declaration_background = mix_hex(design["declaration_color"], "#FFFFFF", 0.92)
    content_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" office:version="1.3"><office:automatic-styles><draw:gradient draw:name="CoverGradient" draw:style="linear" draw:start-color="{design['cover_background_color']}" draw:end-color="{design['cover_gradient_end_color']}" draw:angle="{odt_gradient_angle}"/><style:style style:name="PageBreak" style:family="paragraph"><style:paragraph-properties fo:break-before="page"/></style:style><style:style style:name="CoverCell" style:family="table-cell"><style:table-cell-properties {cover_fill} fo:padding="1.2cm"/></style:style><style:style style:name="DeclarationCell" style:family="table-cell"><style:table-cell-properties fo:background-color="{declaration_background}" fo:border="0.5pt solid #E2E6ED" fo:border-left="3pt solid {design['declaration_color']}" fo:padding="0.55cm"/></style:style><text:list-style style:name="L1"><text:list-level-style-bullet text:level="1" text:bullet-char="•"><style:list-level-properties text:space-before="0.65cm" text:min-label-width="0.45cm"/></text:list-level-style-bullet></text:list-style></office:automatic-styles><office:body><office:text>{''.join(body)}</office:text></office:body></office:document-content>'''
    styles_xml = f'''<?xml version="1.0" encoding="UTF-8"?><office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.3"><office:styles><style:default-style style:family="paragraph"><style:text-properties style:font-name="{escape(design['body_font'])}" fo:font-family="{escape(design['body_font'])}" fo:font-size="10.5pt"/><style:paragraph-properties fo:line-height="115%" fo:margin-bottom="0.18cm"/></style:default-style><style:style style:name="Title" style:family="paragraph"><style:text-properties style:font-name="{escape(design['heading_font'])}" fo:font-family="{escape(design['heading_font'])}" fo:color="{design['heading_color']}" fo:font-size="28pt" fo:font-weight="bold"/><style:paragraph-properties fo:margin-top="3cm" fo:margin-bottom="0.45cm"/></style:style><style:style style:name="Subtitle" style:family="paragraph"><style:text-properties fo:font-size="15pt"/><style:paragraph-properties fo:margin-bottom="1cm"/></style:style><style:style style:name="CoverTitleWhite" style:family="paragraph"><style:text-properties style:font-name="{escape(design['heading_font'])}" fo:font-family="{escape(design['heading_font'])}" fo:color="{design['cover_text_color']}" fo:font-size="30pt" fo:font-weight="bold"/><style:paragraph-properties fo:margin-bottom="0.25cm"/></style:style><style:style style:name="CoverVersionWhite" style:family="paragraph"><style:text-properties fo:color="{design['cover_text_color']}" fo:font-size="18pt"/><style:paragraph-properties fo:margin-bottom="1.2cm"/></style:style><style:style style:name="CoverTextWhite" style:family="paragraph"><style:text-properties fo:color="{design['cover_text_color']}" fo:font-size="13pt"/><style:paragraph-properties fo:margin-bottom="0.15cm"/></style:style><style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph" style:default-outline-level="1"><style:text-properties style:font-name="{escape(design['heading_font'])}" fo:font-family="{escape(design['heading_font'])}" fo:color="{design['heading_color']}" fo:font-size="18pt" fo:font-weight="bold"/><style:paragraph-properties fo:margin-top="0.5cm" fo:margin-bottom="0.25cm"/></style:style><style:style style:name="Heading_20_2" style:display-name="Heading 2" style:family="paragraph" style:default-outline-level="2"><style:text-properties style:font-name="{escape(design['heading_font'])}" fo:font-family="{escape(design['heading_font'])}" fo:color="{design['heading_color']}" fo:font-size="13pt" fo:font-weight="bold"/><style:paragraph-properties fo:margin-top="0.35cm" fo:margin-bottom="0.15cm"/></style:style></office:styles></office:document-styles>'''
    image_manifest = "".join(f'<manifest:file-entry manifest:full-path="{escape(path)}" manifest:media-type="{mime}"/>' for path, mime, _ in embedded_images)
    manifest = f'''<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>{image_manifest}</manifest:manifest>'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text", compress_type=zipfile.ZIP_STORED)
        zf.writestr("content.xml", content_xml)
        zf.writestr("styles.xml", styles_xml)
        zf.writestr("META-INF/manifest.xml", manifest)
        for path, _, blob in embedded_images:
            zf.writestr(path, blob)
    output.seek(0); return output


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "Het bestand is groter dan 6 MB."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
