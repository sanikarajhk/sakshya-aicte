"""
Sakshya Synthetic Document Generator (ReportLab & Pillow)
Generates realistic institutional PDFs and certificate images for testing.
All documents are clearly stamped as SYNTHETIC & TEST-ONLY.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage


def create_notary_stamp_image(
    output_path: Path,
    notary_name: str,
    reg_number: str,
    date_str: str,
    color_rgb: tuple = (180, 20, 20)
) -> Path:
    """Generate a realistic round notary stamp image using Pillow."""
    size = (300, 300)
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Outer double circle
    draw.ellipse([10, 10, 290, 290], outline=color_rgb, width=4)
    draw.ellipse([20, 20, 280, 280], outline=color_rgb, width=2)

    # Notary text
    draw.text((70, 45), "NOTARY PUBLIC", fill=color_rgb)
    draw.text((60, 95), "GOVT OF NCT DELHI", fill=color_rgb)
    draw.text((45, 140), f"ADV. {notary_name.upper()}", fill=color_rgb)
    draw.text((70, 185), f"REG: {reg_number}", fill=color_rgb)
    draw.text((85, 225), f"DATE: {date_str}", fill=color_rgb)

    # Add slight texture/grunge
    img = img.rotate(4, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255, 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def create_mock_qr_image(output_path: Path, payload_text: str) -> Path:
    """
    Generate a 2D matrix mock QR code representation.
    Produces high-contrast matrix blocks with corner position detection patterns.
    """
    size = (200, 200)
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Outer border
    draw.rectangle([0, 0, 199, 199], outline=(0, 0, 0), width=3)

    # Corner finder patterns (Top-left, Top-right, Bottom-left)
    for corner in [(15, 15), (135, 15), (15, 135)]:
        x, y = corner
        draw.rectangle([x, y, x + 50, y + 50], fill=(0, 0, 0))
        draw.rectangle([x + 10, y + 10, x + 40, y + 40], fill=(255, 255, 255))
        draw.rectangle([x + 20, y + 20, x + 30, y + 30], fill=(0, 0, 0))

    # Deterministic pseudo-random pattern derived from text
    h = hash(payload_text)
    for i in range(12):
        for j in range(12):
            if (i < 4 and j < 4) or (i > 7 and j < 4) or (i < 4 and j > 7):
                continue
            bit = (h >> ((i * 12 + j) % 60)) & 1
            if bit:
                bx = 20 + i * 13
                by = 20 + j * 13
                draw.rectangle([bx, by, bx + 10, by + 10], fill=(0, 0, 0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def degrade_pdf_to_scanned_image(pdf_path: Path, output_image_path: Path, noise_level: float = 0.5):
    """Create a simulated noisy scan image from PDF for OCR testing."""
    # Create synthetic degraded page
    img = Image.new("RGB", (850, 1100), (248, 248, 244))
    draw = ImageDraw.Draw(img)
    draw.text((60, 60), "[SYNTHETIC DEGRADED SCAN - OCR BENCHMARK]", fill=(80, 80, 80))
    draw.text((60, 120), "OFFICIAL RECORD DEED & PERMIT", fill=(50, 50, 50))
    draw.text((60, 160), "Extract text via OCR engine under noise degradation.", fill=(60, 60, 60))

    # Add Gaussian blur and slight noise
    img = img.filter(ImageFilter.GaussianBlur(radius=noise_level))
    img.save(output_image_path, "PNG")


def generate_land_title_pdf(
    output_path: Path,
    institution_name: str,
    survey_number: str,
    land_area_acres: float,
    owner_trust_name: str,
    registration_number: str,
    issue_date: str,
    notary_stamp_path: Optional[Path] = None,
    qr_code_path: Optional[Path] = None,
    watermark_text: str = "SYNTHETIC TEST DOCUMENT"
) -> Path:
    """Generate Land Title / Registered Sale & Lease Deed PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        alignment=1,
        textColor=colors.navy
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.dimgrey
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.black
    )
    bold_style = ParagraphStyle(
        "DocBold",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        fontName="Helvetica-Bold",
        textColor=colors.black
    )
    warning_style = ParagraphStyle(
        "DocWarn",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.red
    )

    story = []

    # Watermark / Notice
    story.append(Paragraph(f"*** {watermark_text} - AICTE SIH26261 TESTING ONLY ***", warning_style))
    story.append(Spacer(1, 10))

    # Header
    story.append(Paragraph("GOVERNMENT OF STATE REGISTRATION DEPARTMENT", subtitle_style))
    story.append(Paragraph("DEED OF PERPETUAL LEASE AND CONVEYANCE", title_style))
    story.append(Spacer(1, 10))

    # Metadata Table
    meta_data = [
        [Paragraph("<b>Deed Registration No:</b>", body_style), Paragraph(registration_number, bold_style)],
        [Paragraph("<b>Execution Date:</b>", body_style), Paragraph(issue_date, bold_style)],
        [Paragraph("<b>Sub-Registrar Office:</b>", body_style), Paragraph("District Central Sub-Registry Office", body_style)],
    ]
    meta_table = Table(meta_data, colWidths=[180, 320])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Legal Covenant Text
    p1 = f"""
    THIS INDENTURE is made and entered into on this <b>{issue_date}</b> between the Land Authority 
    hereinafter called the LESSOR, and the sponsoring body <b>{owner_trust_name}</b>, for the establishment 
    and perpetual institutional operation of <b>{institution_name}</b>, hereinafter called the LESSEE.
    """
    story.append(Paragraph(p1, body_style))
    story.append(Spacer(1, 10))

    p2 = f"""
    <b>SCHEDULE OF PROPERTY:</b><br/>
    All that piece and parcel of contiguous institutional land bearing <b>Survey Number: {survey_number}</b>, 
    measuring a total area of <b>{land_area_acres:.2f} Acres</b> (equivalent to {land_area_acres * 4046.86:.1f} square meters), 
    situated in Institutional Knowledge Park Zone. The Lessee covenants that this land shall be earmarked 
    solely and exclusively for educational purposes approved by statutory bodies including AICTE.
    """
    story.append(Paragraph(p2, body_style))
    story.append(Spacer(1, 15))

    # Stamp and QR Code row
    elements_row = []
    if notary_stamp_path and os.path.exists(notary_stamp_path):
        elements_row.append(RLImage(str(notary_stamp_path), width=120, height=120))
    else:
        elements_row.append(Paragraph("<b>[NOTARY SEAL ATTESTED]</b>", body_style))

    if qr_code_path and os.path.exists(qr_code_path):
        elements_row.append(RLImage(str(qr_code_path), width=90, height=90))
    else:
        elements_row.append(Paragraph("<b>[VERIFICATION QR ATTACHED]</b>", body_style))

    sig_data = [
        [Paragraph("<b>Attested by Notary Public:</b>", body_style), Paragraph("<b>Digital Verification QR:</b>", body_style)],
        [elements_row[0], elements_row[1]],
        [Paragraph("Registered Advocate & Commissioner of Oaths", subtitle_style), Paragraph("Scan to query State Revenue Record", subtitle_style)]
    ]
    sig_table = Table(sig_data, colWidths=[250, 250])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)

    doc.build(story)
    return output_path


def generate_building_plan_pdf(
    output_path: Path,
    institution_name: str,
    survey_number: str,
    built_up_area_sqm: float,
    approval_number: str,
    approval_date: str,
    expiry_date: Optional[str],
    architect_license: str,
    qr_code_path: Optional[Path] = None,
    watermark_text: str = "SYNTHETIC TEST DOCUMENT"
) -> Path:
    """Generate Municipal / Town Planning Building Plan Approval PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BPlanTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        alignment=1,
        textColor=colors.darkgreen
    )
    subtitle_style = ParagraphStyle(
        "BPlanSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.dimgrey
    )
    body_style = ParagraphStyle(
        "BPlanBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.black
    )
    bold_style = ParagraphStyle(
        "BPlanBold",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        fontName="Helvetica-Bold",
        textColor=colors.black
    )
    warning_style = ParagraphStyle(
        "BPlanWarn",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.red
    )

    story = []
    story.append(Paragraph(f"*** {watermark_text} - AICTE SIH26261 TESTING ONLY ***", warning_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("MUNICIPAL URBAN DEVELOPMENT AUTHORITY", subtitle_style))
    story.append(Paragraph("INSTITUTIONAL BUILDING PLAN SANCTION & OCCUPANCY ORDER", title_style))
    story.append(Spacer(1, 10))

    validity_display = expiry_date if expiry_date else "PERMANENT OCCUPANCY (Subject to safety norms)"
    table_data = [
        [Paragraph("<b>Sanction Order No:</b>", body_style), Paragraph(approval_number, bold_style)],
        [Paragraph("<b>Sanction Date:</b>", body_style), Paragraph(approval_date, bold_style)],
        [Paragraph("<b>Validity / Expiry Date:</b>", body_style), Paragraph(validity_display, bold_style)],
        [Paragraph("<b>Institution Name:</b>", body_style), Paragraph(institution_name, bold_style)],
        [Paragraph("<b>Survey / Plot Reference:</b>", body_style), Paragraph(survey_number, bold_style)],
        [Paragraph("<b>Total Approved Built-Up Area:</b>", body_style), Paragraph(f"{built_up_area_sqm:,.2f} sq. meters", bold_style)],
        [Paragraph("<b>Empaneled Architect License:</b>", body_style), Paragraph(architect_license, bold_style)],
    ]
    info_table = Table(table_data, colWidths=[190, 310])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    p = f"""
    The Town Planning Directorate has reviewed the architectural layout drawings submitted by 
    <b>{institution_name}</b> on plot bearing <b>{survey_number}</b>. 
    The layout strictly complies with the AICTE space norms, FAR requirements, and Barrier-Free 
    accessibility provisions for differently-abled persons. Sanction is hereby accorded.
    """
    story.append(Paragraph(p, body_style))
    story.append(Spacer(1, 15))

    if qr_code_path and os.path.exists(qr_code_path):
        qr_table = Table([
            [RLImage(str(qr_code_path), width=85, height=85),
             Paragraph("<b>MUNICIPAL VERIFICATION QR</b><br/>Official clearance digital validation token.<br/>Town Planning Department Authority.", subtitle_style)]
        ], colWidths=[100, 400])
        qr_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        story.append(qr_table)

    doc.build(story)
    return output_path


def generate_fire_noc_pdf(
    output_path: Path,
    institution_name: str,
    noc_number: str,
    issue_date: str,
    expiry_date: str,
    qr_code_path: Optional[Path] = None,
    watermark_text: str = "SYNTHETIC TEST DOCUMENT"
) -> Path:
    """Generate State Fire & Rescue Services Department NOC PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FireTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        alignment=1,
        textColor=colors.darkred
    )
    subtitle_style = ParagraphStyle(
        "FireSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.dimgrey
    )
    body_style = ParagraphStyle(
        "FireBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=colors.black
    )
    bold_style = ParagraphStyle(
        "FireBold",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        fontName="Helvetica-Bold",
        textColor=colors.black
    )
    warning_style = ParagraphStyle(
        "FireWarn",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.red
    )

    story = []
    story.append(Paragraph(f"*** {watermark_text} - AICTE SIH26261 TESTING ONLY ***", warning_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("STATE DISASTER MANAGEMENT & FIRE RESCUE SERVICES", subtitle_style))
    story.append(Paragraph("FIRE SAFETY CERTIFICATE / NO OBJECTION CERTIFICATE (NOC)", title_style))
    story.append(Spacer(1, 10))

    table_data = [
        [Paragraph("<b>Fire NOC Certificate No:</b>", body_style), Paragraph(noc_number, bold_style)],
        [Paragraph("<b>Date of Issuance:</b>", body_style), Paragraph(issue_date, bold_style)],
        [Paragraph("<b>Valid Until (Expiry Date):</b>", body_style), Paragraph(expiry_date, bold_style)],
        [Paragraph("<b>Certified Institution:</b>", body_style), Paragraph(institution_name, bold_style)],
        [Paragraph("<b>Inspecting Station:</b>", body_style), Paragraph("Divisional Fire Headquarters", body_style)],
    ]
    info_table = Table(table_data, colWidths=[190, 310])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    p = f"""
    Certified that the educational premises of <b>{institution_name}</b> was inspected on <b>{issue_date}</b> 
    by the authorized Fire Prevention Officers. All required fire hydrants, smoke alarms, emergency exits, 
    and pressurized stairwells were tested in conformity with National Building Code (NBC) Part IV. 
    This certificate remains valid until <b>{expiry_date}</b>.
    """
    story.append(Paragraph(p, body_style))
    story.append(Spacer(1, 15))

    if qr_code_path and os.path.exists(qr_code_path):
        qr_table = Table([
            [RLImage(str(qr_code_path), width=85, height=85),
             Paragraph("<b>FIRE DEPARTMENT VERIFICATION PORTAL</b><br/>Direct registry validation QR token.<br/>Fire Services Command Directorate.", subtitle_style)]
        ], colWidths=[100, 400])
        qr_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        story.append(qr_table)

    doc.build(story)
    return output_path


def generate_mandatory_disclosure_pdf(
    output_path: Path,
    institution_name: str,
    institution_type: str,
    society_trust_name: str,
    land_area_acres: float,
    survey_number: str,
    fire_noc_number: str,
    applied_intake: int,
    principal_name: str,
    watermark_text: str = "SYNTHETIC TEST DOCUMENT"
) -> Path:
    """Generate AICTE Mandatory Disclosure Document PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MDiscTitle",
        parent=styles["Heading1"],
        fontSize=15,
        leading=18,
        alignment=1,
        textColor=colors.HexColor("#1A365D")
    )
    subtitle_style = ParagraphStyle(
        "MDiscSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.dimgrey
    )
    body_style = ParagraphStyle(
        "MDiscBody",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.black
    )
    bold_style = ParagraphStyle(
        "MDiscBold",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        fontName="Helvetica-Bold",
        textColor=colors.black
    )
    warning_style = ParagraphStyle(
        "MDiscWarn",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.red
    )

    story = []
    story.append(Paragraph(f"*** {watermark_text} - AICTE SIH26261 TESTING ONLY ***", warning_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("ALL INDIA COUNCIL FOR TECHNICAL EDUCATION (AICTE)", subtitle_style))
    story.append(Paragraph("MANDATORY DISCLOSURE OF INSTITUTIONAL PARTICULARS", title_style))
    story.append(Spacer(1, 10))

    table_data = [
        [Paragraph("<b>Name of the Institution:</b>", body_style), Paragraph(institution_name, bold_style)],
        [Paragraph("<b>Category / Type:</b>", body_style), Paragraph(institution_type, bold_style)],
        [Paragraph("<b>Sponsoring Society / Trust:</b>", body_style), Paragraph(society_trust_name, bold_style)],
        [Paragraph("<b>Head of Institution (Principal):</b>", body_style), Paragraph(principal_name, bold_style)],
        [Paragraph("<b>Total Campus Land Area (Acres):</b>", body_style), Paragraph(f"{land_area_acres:.2f} Acres", bold_style)],
        [Paragraph("<b>Survey / Khasra Number:</b>", body_style), Paragraph(survey_number, bold_style)],
        [Paragraph("<b>Fire Safety NOC Reference:</b>", body_style), Paragraph(fire_noc_number, bold_style)],
        [Paragraph("<b>Approved Student Intake:</b>", body_style), Paragraph(str(applied_intake), bold_style)],
    ]
    info_table = Table(table_data, colWidths=[200, 300])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    p = f"""
    We hereby solemnly affirm that the particulars stated above are true to our institutional records 
    and certified by competent local authorities. Any discrepancy observed during scrutiny or virtual/physical 
    inspection shall render our application liable for penal regulatory action under AICTE regulations.
    """
    story.append(Paragraph(p, body_style))

    doc.build(story)
    return output_path
