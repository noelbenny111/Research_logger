"""
PDF export utility for Research Logger.
Uses reportlab to produce clean, readable PDFs.
"""
import os
import re
from datetime import date
from typing import List, Dict, Any, Optional


_LAST_EXPORT_ERROR = ""


def _set_last_export_error(message: str):
    global _LAST_EXPORT_ERROR
    _LAST_EXPORT_ERROR = message or ""


def get_last_export_error() -> str:
    return _LAST_EXPORT_ERROR


def _clean_for_pdf(text: str) -> str:
    """Strip markdown for plain-text PDF rendering."""
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"^[-*+]\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"-{3,}", "─" * 40, text)
    return text.strip()


def export_entry_to_pdf(entry: Dict[str, Any], output_path: str) -> bool:
    """Export a single daily entry to PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        HRFlowable, Table, TableStyle)
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "Title", parent=styles["Heading1"],
            fontSize=18, spaceAfter=6,
            textColor=colors.HexColor("#1a1a2e"),
        )
        date_style = ParagraphStyle(
            "DateStyle", parent=styles["Normal"],
            fontSize=10, textColor=colors.grey, spaceAfter=12,
        )
        heading_style = ParagraphStyle(
            "H2", parent=styles["Heading2"],
            fontSize=13, spaceAfter=4, spaceBefore=12,
            textColor=colors.HexColor("#16213e"),
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["Normal"],
            fontSize=10, leading=15, spaceAfter=6,
        )

        story = []
        entry_date = entry.get("entry_date", "")
        content = entry.get("content", "")
        tags = entry.get("tags", [])
        attachments = entry.get("attachments", [])

        story.append(Paragraph("Research Log", title_style))
        story.append(Paragraph(entry_date, date_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Spacer(1, 0.4 * cm))

        # Parse markdown sections
        sections = re.split(r"^(#{1,3}\s+.+)$", content, flags=re.MULTILINE)
        for chunk in sections:
            chunk = chunk.strip()
            if not chunk:
                continue
            if re.match(r"^#{1,3}\s+", chunk):
                heading_text = re.sub(r"^#{1,3}\s+", "", chunk)
                story.append(Paragraph(heading_text, heading_style))
            else:
                lines = _clean_for_pdf(chunk).split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        story.append(Spacer(1, 0.15 * cm))
                        continue
                    safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(safe, body_style))

        # Tags
        if tags:
            story.append(Spacer(1, 0.5 * cm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
            tag_style = ParagraphStyle("Tags", parent=styles["Normal"],
                                       fontSize=9, textColor=colors.grey)
            story.append(Paragraph(f"Tags: {', '.join(tags)}", tag_style))

        # Attachments list
        if attachments:
            story.append(Spacer(1, 0.3 * cm))
            att_style = ParagraphStyle("Att", parent=styles["Normal"],
                                       fontSize=9, textColor=colors.grey)
            story.append(Paragraph("Attachments:", att_style))
            for att in attachments:
                story.append(Paragraph(f"  • {att['filename']}", att_style))

        doc.build(story)
        _set_last_export_error("")
        return True
    except ImportError as e:
        msg = f"Missing dependency while generating PDF: {e}"
        _set_last_export_error(msg)
        print(f"PDF export error: {msg}")
        return False
    except Exception as e:
        _set_last_export_error(str(e))
        print(f"PDF export error: {e}")
        return False


def export_summary_to_pdf(title: str, content: str, output_path: str) -> bool:
    """Export a summary string to PDF."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.enums import TA_LEFT

        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                leftMargin=2.5*cm, rightMargin=2.5*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("T", parent=styles["Heading1"], fontSize=16,
                                     textColor=colors.HexColor("#1a1a2e"), spaceAfter=8)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12,
                                  textColor=colors.HexColor("#16213e"), spaceBefore=10, spaceAfter=4)
        h3_style = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=11,
                                  textColor=colors.HexColor("#0f3460"), spaceBefore=8, spaceAfter=4)
        body_style = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, leading=14)

        story = [Paragraph(title, title_style),
                 HRFlowable(width="100%", thickness=1, color=colors.lightgrey),
                 Spacer(1, 0.3*cm)]

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1*cm))
                continue
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if re.match(r"^##\s+", line):
                story.append(Paragraph(re.sub(r"^##\s+", "", safe), h2_style))
            elif re.match(r"^###\s+", line):
                story.append(Paragraph(re.sub(r"^###\s+", "", safe), h3_style))
            elif line.startswith("**") and line.endswith("**"):
                story.append(Paragraph(f"<b>{safe[2:-2]}</b>", body_style))
            else:
                story.append(Paragraph(safe, body_style))

        doc.build(story)
        _set_last_export_error("")
        return True
    except ImportError as e:
        msg = f"Missing dependency while generating PDF: {e}"
        _set_last_export_error(msg)
        print(f"PDF export error: {msg}")
        return False
    except Exception as e:
        _set_last_export_error(str(e))
        print(f"PDF export error: {e}")
        return False
