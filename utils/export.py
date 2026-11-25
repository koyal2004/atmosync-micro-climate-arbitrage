"""
AtmoSync - Multi-Format Data & Report Export Engine
Generates CSVs, Excel workbooks, ZIP archives, and professional PDF reports using ReportLab.
"""

import io
import zipfile
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

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

def create_excel_workbook(
    datasets: Dict[str, pd.DataFrame],
    filter_summary: str = "All Records (Unfiltered)"
) -> bytes:
    """Create multi-sheet Excel workbook using OpenPyXL with embedded metadata and disclaimer."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        meta_df = pd.DataFrame([
            {"Field": "Application", "Value": f"{APP_NAME} - {TAGLINE}"},
            {"Field": "Organization", "Value": ORGANIZATION},
            {"Field": "Report Generated At", "Value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"Field": "Filter Scope", "Value": filter_summary},
            {"Field": "Data Provenance Disclaimer", "Value": PERSISTENT_DISCLAIMER},
        ])
        meta_df.to_excel(writer, sheet_name="Report_Metadata", index=False)

        for name, df in datasets.items():
            # Truncate sheet name to 31 chars (Excel limit)
            sheet_title = name[:31]
            if df is not None and not df.empty:
                df.head(5000).to_excel(writer, sheet_name=sheet_title, index=False)
            else:
                pd.DataFrame([{"Notice": "No records matched the selected filter criteria."}]).to_excel(
                    writer, sheet_name=sheet_title, index=False
                )
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
    gen_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filter_desc = summary_metrics.get("filter_scope", "Full Database Scope")
    story.append(Paragraph(f"{APP_NAME} &mdash; Executive Intelligence Report", title_style))
    story.append(Paragraph(f"{TAGLINE.upper()} | {ORGANIZATION}", subtitle_style))
    story.append(Paragraph(f"<b>Generated:</b> {gen_ts} &nbsp;|&nbsp; <b>Scope:</b> {filter_desc}", body_style))
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
        ["Peak Estimated Net Advantage", f"Rs. {summary_metrics.get('max_benefit', 0):,.2f}", "Profitable Target"]
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
                f"+Rs. {row.get('gross_price_advantage', 0):.2f}",
                f"Rs. {row.get('estimated_net_benefit', 0):,.0f}"
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


def build_filtered_report(
    report_type: str,
    datasets: Dict[str, pd.DataFrame],
    date_range: Optional[Tuple[Any, Any]] = None,
    category_filter: str = "All"
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    """
    Dynamically builds one of five structured analytical reports from live application datasets,
    applying date range and category/status filters consistently.
    Returns (report_df, summary_dict, filter_scope_label).
    """
    commodities_df = datasets.get("commodities", pd.DataFrame())
    markets_df = datasets.get("markets", pd.DataFrame())
    shipments_df = datasets.get("shipments", pd.DataFrame())
    sensor_df = datasets.get("sensor_readings", pd.DataFrame())
    prices_df = datasets.get("market_prices", pd.DataFrame())

    comm_names = dict(zip(commodities_df["commodity_id"], commodities_df["commodity_name"])) if not commodities_df.empty else {}
    comm_cats = dict(zip(commodities_df["commodity_id"], commodities_df["category"])) if not commodities_df.empty else {}
    mkt_names = dict(zip(markets_df["market_id"], markets_df["market_name"])) if not markets_df.empty else {}
    mkt_states = dict(zip(markets_df["market_id"], markets_df["state"])) if not markets_df.empty else {}

    date_desc = "All Dates"
    if date_range and len(date_range) == 2:
        date_desc = f"{date_range[0]} to {date_range[1]}"
    filter_label = f"{report_type} | {date_desc} | Filter: {category_filter}"

    def _apply_date_filter(df: pd.DataFrame, col: str) -> pd.DataFrame:
        if df.empty or col not in df.columns or not date_range or len(date_range) != 2:
            return df
        dt_series = pd.to_datetime(df[col], errors="coerce").dt.date
        start_d, end_d = date_range
        return df[(dt_series >= start_d) & (dt_series <= end_d)]

    if report_type == "Shipment Summary":
        df = shipments_df.copy()
        df = _apply_date_filter(df, "departure_date")
        if not df.empty:
            df["commodity_name"] = df["commodity_id"].map(comm_names).fillna("Unknown")
            df["source_market"] = df["source_market_id"].map(mkt_names).fillna("Origin")
            df["destination_market"] = df["destination_market_id"].map(mkt_names).fillna("Destination")
            if category_filter != "All":
                df = df[df["shipment_status"] == category_filter]
            cols = [
                "shipment_id", "container_id", "commodity_name", "source_market",
                "destination_market", "departure_date", "expected_arrival_date",
                "quantity_kg", "distance_km", "transport_cost", "shipment_status",
                "estimated_remaining_shelf_life"
            ]
            df = df[[c for c in cols if c in df.columns]]
        summary = {
            "Records": len(df),
            "Total Freight (kg)": round(float(df["quantity_kg"].sum()), 1) if not df.empty else 0.0,
            "Avg Distance (km)": round(float(df["distance_km"].mean()), 1) if not df.empty else 0.0,
            "Total Transport Cost (Rs.)": round(float(df["transport_cost"].sum()), 2) if not df.empty else 0.0,
        }
        return df, summary, filter_label

    elif report_type == "IoT Sensor Analytics":
        df = sensor_df.copy()
        df = _apply_date_filter(df, "timestamp")
        if not df.empty:
            if not shipments_df.empty:
                ship_comm = dict(zip(shipments_df["shipment_id"], shipments_df["commodity_id"].map(comm_names)))
                df["commodity_name"] = df["shipment_id"].map(ship_comm).fillna("Perishable")
            if category_filter != "All":
                df = df[df["sensor_status"] == category_filter]
            cols = [
                "sensor_id", "shipment_id", "container_id", "commodity_name",
                "timestamp", "temperature", "humidity", "vibration", "sensor_status"
            ]
            df = df[[c for c in cols if c in df.columns]]
        summary = {
            "Telemetry Packets": len(df),
            "Avg Temp (C)": round(float(df["temperature"].mean()), 1) if not df.empty else 0.0,
            "Avg Humidity (%)": round(float(df["humidity"].mean()), 1) if not df.empty else 0.0,
            "Critical Readings": int((df["sensor_status"] == "Critical").sum()) if not df.empty else 0,
        }
        return df, summary, filter_label

    elif report_type == "Commodity Price Analysis":
        df = prices_df.copy()
        df = _apply_date_filter(df, "date")
        if not df.empty:
            df["commodity_name"] = df["commodity_id"].map(comm_names).fillna("Unknown")
            df["category"] = df["commodity_id"].map(comm_cats).fillna("Vegetable")
            df["market_name"] = df["market_id"].map(mkt_names).fillna("Mandi")
            df["state"] = df["market_id"].map(mkt_states).fillna("India")
            if category_filter != "All":
                df = df[df["category"] == category_filter]
            cols = [
                "price_id", "date", "commodity_name", "category", "market_name",
                "state", "minimum_price", "modal_price", "maximum_price",
                "arrival_quantity", "demand_index", "supply_index"
            ]
            df = df[[c for c in cols if c in df.columns]]
        summary = {
            "Price Observations": len(df),
            "Avg Modal Price (Rs./kg)": round(float(df["modal_price"].mean()), 2) if not df.empty else 0.0,
            "Total Arrivals (kg)": round(float(df["arrival_quantity"].sum()), 1) if not df.empty else 0.0,
            "Unique Mandis": int(df["market_name"].nunique()) if not df.empty and "market_name" in df.columns else 0,
        }
        return df, summary, filter_label

    elif report_type == "Spoilage Risk Summary":
        from modules.risk_engine import calculate_shipment_risk
        ship_filtered = _apply_date_filter(shipments_df.copy(), "departure_date")
        df = calculate_shipment_risk(ship_filtered, commodities_df, sensor_df)
        if not df.empty:
            if category_filter != "All":
                df = df[df["risk_category"] == category_filter]
            cols = [
                "shipment_id", "container_id", "commodity_name", "shipment_status",
                "departure_date", "temperature_exposure", "humidity_exposure",
                "vibration_exposure", "estimated_remaining_shelf_life",
                "risk_score", "risk_category", "recommended_action"
            ]
            df = df[[c for c in cols if c in df.columns]]
        summary = {
            "Consignments Scored": len(df),
            "Avg Risk Score (0-100)": round(float(df["risk_score"].mean()), 1) if not df.empty else 0.0,
            "High/Critical Count": int(df["risk_category"].isin(["High", "Critical"]).sum()) if not df.empty else 0,
            "Avg Shelf Life (Days)": round(float(df["estimated_remaining_shelf_life"].mean()), 1) if not df.empty else 0.0,
        }
        return df, summary, filter_label

    elif report_type == "Market Arbitrage Opportunities":
        from modules.risk_engine import calculate_shipment_risk
        from modules.arbitrage_engine import evaluate_arbitrage_opportunities
        ship_filtered = _apply_date_filter(shipments_df.copy(), "departure_date")
        risk_df = calculate_shipment_risk(ship_filtered, commodities_df, sensor_df)
        df = evaluate_arbitrage_opportunities(ship_filtered, commodities_df, markets_df, prices_df, risk_df)
        if not df.empty:
            if category_filter == "Profitable Only":
                df = df[df["is_profitable"] == True]
            elif category_filter == "Unprofitable Only":
                df = df[df["is_profitable"] == False]
            cols = [
                "opportunity_id", "shipment_id", "commodity_name",
                "source_market_name", "current_destination_name", "alternative_market_name",
                "quantity_kg", "source_market_price", "destination_market_price",
                "gross_advantage", "transportation_cost", "handling_cost",
                "estimated_quality_loss_cost", "estimated_net_benefit", "recommendation_status"
            ]
            df = df[[c for c in cols if c in df.columns]]
        summary = {
            "Scenarios Evaluated": len(df),
            "Profitable Leads": int((df["estimated_net_benefit"] > 0).sum()) if not df.empty else 0,
            "Peak Net Benefit (Rs.)": round(float(df["estimated_net_benefit"].max()), 2) if not df.empty else 0.0,
            "Total Potential Gain (Rs.)": round(float(df[df["estimated_net_benefit"] > 0]["estimated_net_benefit"].sum()), 2) if not df.empty else 0.0,
        }
        return df, summary, filter_label

    return pd.DataFrame(), {}, filter_label
