"""
AtmoSync - Multi-Format Data & Report Export Engine
Generates CSVs, Excel workbooks, ZIP archives, and professional PDF reports using ReportLab.
"""

import io
import zipfile
import pandas as pd
from datetime import datetime
from typing import Dict, Any

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from config.settings import PERSISTENT_DISCLAIMER, APP_NAME, TAGLINE, ORGANIZATION

def create_datasets_zip(datasets: Dict[str, pd.DataFrame]) -> bytes:
    """Create in-memory zip archive containing CSVs of all active tables."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for name, df in datasets.items():
            csv_data = df.to_csv(index=False).encode("utf-8")
            zip_file.writestr(f"{name}.csv", csv_data)
        
        # Include Readme note
        readme_txt = f"""AtmoSync Synthetic Agricultural Data Export
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Research Lab: {ORGANIZATION}

DISCLAIMER:
{PERSISTENT_DISCLAIMER}
"""
        zip_file.writestr("README_METADATA.txt", readme_txt.encode("utf-8"))
    
    buf.seek(0)
    return buf.getvalue()

def create_excel_workbook(datasets: Dict[str, pd.DataFrame]) -> bytes:
    """Create multi-sheet Excel workbook using OpenPyXL."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in datasets.items():
            # Truncate sheet name to 31 chars (Excel limit)
            sheet_title = name[:31]
            df.head(2500).to_excel(writer, sheet_name=sheet_title, index=False)
    buf.seek(0)
    return buf.getvalue()

def generate_pdf_report(
    summary_metrics: Dict[str, Any],
    risk_summary: Dict[str, Any],
    arbitrage_df: pd.DataFrame,
    quality_summary: Dict[str, Any]
) -> bytes:
    """
    Builds an executive PDF analytical dossier using ReportLab.
    Includes Executive Summary, Quality Audit, Risk Profile, and Arbitrage Highlights.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#10243A")
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#12B8A6")
    )
    h2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#10243A"),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#64748B")
    )

    story = []

    # Title & Metadata Banner
    story.append(Paragraph(f"{APP_NAME} &mdash; Executive Intelligence Report", title_style))
    story.append(Paragraph(f"{TAGLINE.upper()} | {ORGANIZATION}", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#12B8A6"), spaceBefore=4, spaceAfter=10))

    # Executive Overview
    story.append(Paragraph("1. Executive Operations Summary", h2_style))
    exec_summary_text = (
        f"This intelligence dossier aggregates synthetic telemetry and spot market signals across Indian APMC mandis. "
        f"A total of <b>{summary_metrics.get('total_shipments', 0):,}</b> consignments and <b>{summary_metrics.get('total_markets', 0)}</b> "
        f"trading hubs are tracked. Currently, <b>{summary_metrics.get('at_risk_shipments', 0)}</b> containers exhibit elevated thermal exposure, "
        f"representing high-priority rerouting opportunities."
    )
    story.append(Paragraph(exec_summary_text, body_style))
    story.append(Spacer(1, 8))

    # KPI Table
    kpi_data = [
        ["Metric Indicator", "Observed Value", "Strategic Status"],
        ["Active Fleet Shipments", f"{summary_metrics.get('active_shipments', 0):,}", "Monitored"],
        ["At-Risk Consignments", f"{summary_metrics.get('at_risk_shipments', 0):,}", "Action Required"],
        ["Average Reefer Temperature", f"{summary_metrics.get('avg_temp', 0):.1f} °C", "Nominal Band"],
        ["Average Relative Humidity", f"{summary_metrics.get('avg_hum', 0):.1f} %", "Controlled"],
        ["Arbitrage Opportunities Identified", f"{summary_metrics.get('total_arbitrage', 0):,}", "Available"],
        ["Peak Estimated Net Advantage", f"₹{summary_metrics.get('max_benefit', 0):,.2f}", "Profitable Target"]
    ]
    t_kpi = Table(kpi_data, colWidths=[200, 150, 160])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10243A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 12))

    # Spoilage Risk Distribution
    story.append(Paragraph("2. Micro-Climate Spoilage Assessment", h2_style))
    risk_text = (
        f"Consignments are categorized using multi-factor environmental exposure scoring (0–100 scale). "
        f"Critical Risk: <b>{risk_summary.get('critical', 0)}</b> | High Risk: <b>{risk_summary.get('high', 0)}</b> | "
        f"Moderate Risk: <b>{risk_summary.get('moderate', 0)}</b> | Low Risk: <b>{risk_summary.get('low', 0)}</b>. "
        f"Fleet average quality degradation is projected at <b>{risk_summary.get('avg_loss', 0):.1f}%</b>."
    )
    story.append(Paragraph(risk_text, body_style))
    story.append(Spacer(1, 10))

    # Top Arbitrage Targets Table
    story.append(Paragraph("3. Top Recommended Arbitrage Divergence Targets", h2_style))
    if not arbitrage_df.empty:
        top_arb = arbitrage_df.sort_values("estimated_net_benefit", ascending=False).head(5)
        arb_rows = [["Shipment", "Commodity", "Current Dest", "Recommended Alt", "Price Diff", "Est. Net Gain"]]
        for _, row in top_arb.iterrows():
            arb_rows.append([
                str(row.get("shipment_id", "")),
                str(row.get("commodity_name", ""))[:14],
                str(row.get("current_destination_name", row.get("source_market_name", "")))[:14],
                str(row.get("alternative_market_name", ""))[:14],
                f"+₹{row.get('gross_price_advantage', 0):.2f}",
                f"₹{row.get('estimated_net_benefit', 0):,.0f}"
            ])
        t_arb = Table(arb_rows, colWidths=[65, 95, 95, 100, 65, 90])
        t_arb.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12B8A6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")])
        ]))
        story.append(t_arb)
    story.append(Spacer(1, 14))

    # Data Quality Audit Section
    story.append(Paragraph("4. Data Quality & Referential Integrity Audit", h2_style))
    story.append(Paragraph(
        f"Data Completeness Score: <b>{quality_summary.get('completeness_pct', 100.0)}%</b> | "
        f"Total Records Audited: <b>{quality_summary.get('total_records', 0):,}</b> | "
        f"Foreign Key Violations: <b>{quality_summary.get('foreign_key_violations', 0)}</b> | "
        f"Duplicate Keys: <b>{quality_summary.get('duplicate_counts', 0)}</b>.",
        body_style
    ))
    story.append(Spacer(1, 18))

    # Academic Disclaimer Footer
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceBefore=6, spaceAfter=6))
    story.append(Paragraph(f"<b>SCIENTIFIC & LEGAL DISCLAIMER:</b> {PERSISTENT_DISCLAIMER}", disclaimer_style))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
