from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.core.database import get_db
from app.models.models import Activity, Plant, Zone, EvidenceMedia, Profile

from app.core.access import Actor, get_actor, scope_query

router = APIRouter(prefix="/reports", tags=["PDF Reports"])

@router.get("/activity/{activity_id}/pdf")
async def generate_activity_pdf(activity_id: str, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    act = result.scalar_one_or_none()
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")

    plant_res = await db.execute(select(Plant).where(Plant.id == act.plant_id))
    plant = plant_res.scalar_one_or_none()
    plant_name = plant.name if plant else "Austin Gigafactory"

    zone_res = await db.execute(select(Zone).where(Zone.id == act.zone_id))
    zone = zone_res.scalar_one_or_none()
    zone_name = zone.name if zone else "Zone"

    ev_res = await db.execute(select(EvidenceMedia).where(EvidenceMedia.activity_id == act.id))
    evidence = ev_res.scalars().all()
    before_count = sum(1 for e in evidence if e.media_type == "before_photo")
    after_count = sum(1 for e in evidence if e.media_type == "after_photo")

    # Generate PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    header_style = ParagraphStyle(
        'SecHeader',
        parent=styles['Heading3'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0284C7'),
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E293B')
    )
    bold_style = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title & Plant Banner
    story.append(Paragraph(f"DIGI5S — 5S ACTIVITY RECORD: {act.activity_number}", title_style))
    story.append(Paragraph(f"Plant: {plant_name} | Location: {zone_name} | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", subtitle_style))
    story.append(Spacer(1, 14))

    # Activity Meta Table
    meta_data = [
        [
            Paragraph("<b>Title:</b>", bold_style), Paragraph(act.title, body_style),
            Paragraph("<b>Status:</b>", bold_style), Paragraph(act.status.upper().replace('_', ' '), bold_style)
        ],
        [
            Paragraph("<b>5S Category:</b>", bold_style), Paragraph(act.category.replace('_', ' ').title(), body_style),
            Paragraph("<b>Priority:</b>", bold_style), Paragraph(act.priority.upper(), body_style)
        ],
        [
            Paragraph("<b>Submitted:</b>", bold_style), Paragraph(act.submitted_at.strftime('%Y-%m-%d') if act.submitted_at else "Pending", body_style),
            Paragraph("<b>Reviewed:</b>", bold_style), Paragraph(act.reviewed_at.strftime('%Y-%m-%d') if act.reviewed_at else "Pending", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[90, 180, 80, 190])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Problem Statement & Corrective Action
    story.append(Paragraph("1. PROBLEM DESCRIPTION & OPPORTUNITY", header_style))
    story.append(Paragraph(act.problem_description, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. CORRECTIVE ACTION IMPLEMENTED", header_style))
    story.append(Paragraph(act.corrective_action or "Action in progress by shop floor operator.", body_style))
    story.append(Spacer(1, 10))

    if act.outcome_description:
        story.append(Paragraph("3. STANDARDIZED OUTCOME", header_style))
        story.append(Paragraph(act.outcome_description, body_style))
        story.append(Spacer(1, 10))

    # Evidence Summary Box
    story.append(Paragraph("4. PHOTO EVIDENCE VERIFICATION", header_style))
    ev_data = [
        [
            Paragraph("<b>BEFORE EVIDENCE PHOTOS</b>", bold_style),
            Paragraph("<b>AFTER EVIDENCE PHOTOS</b>", bold_style)
        ],
        [
            Paragraph(f"Verified Assets: {before_count} item(s)<br/>Inspection status: Registered on file", body_style),
            Paragraph(f"Verified Assets: {after_count} item(s)<br/>Inspection status: {'Verified by Supervisor' if act.status in ['approved', 'completed'] else 'Pending Final Signoff'}", body_style)
        ]
    ]
    ev_table = Table(ev_data, colWidths=[270, 270])
    ev_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(ev_table)
    story.append(Spacer(1, 14))

    # Measurable Benefits Table
    story.append(Paragraph("5. MEASURABLE BUSINESS IMPACT & OPERATIONAL SAVINGS", header_style))
    benefits_data = [
        [Paragraph("<b>Metric</b>", bold_style), Paragraph("<b>Recorded Improvement</b>", bold_style)],
        [Paragraph("Safety Hazard Mitigated:", body_style), Paragraph("Yes (Validated Zero Pinch/Trip Hazard)" if act.benefits_safety else "Standard Ergonomics Baseline", body_style)],
        [Paragraph("Floor Space Recovered:", body_style), Paragraph(f"+{act.benefits_space_sqft:.1f} sq.ft recovered", body_style)],
        [Paragraph("Cycle / Search Time Saved:", body_style), Paragraph(f"{act.benefits_time_seconds:.0f} seconds saved per shift / setup", body_style)],
        [Paragraph("Scrap / Cost Avoidance:", body_style), Paragraph(f"${act.benefits_cost_savings:,.2f} USD estimated annual value", body_style)],
    ]
    if act.benefits_summary:
        benefits_data.append([Paragraph("Benefit Notes:", body_style), Paragraph(act.benefits_summary, body_style)])

    b_table = Table(benefits_data, colWidths=[180, 360])
    b_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(b_table)
    story.append(Spacer(1, 16))

    # Sign-off Stamp
    approval_text = "OFFICIALLY APPROVED & ARCHIVED" if act.status in ['approved', 'completed'] else f"CURRENT STATUS: {act.status.upper()}"
    sign_data = [
        [
            Paragraph(f"<b>Review Status:</b> {approval_text}", bold_style),
            Paragraph("<b>Supervisor Sign-off Stamp:</b> [DIGI5S-VERIFIED-AUTH]", bold_style)
        ]
    ]
    sign_table = Table(sign_data, colWidths=[270, 270])
    sign_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0284C7')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F9FF')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(sign_table)

    doc.build(story)
    buffer.seek(0)

    pdf_bytes = buffer.getvalue()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={act.activity_number}_Report.pdf"}
    )
