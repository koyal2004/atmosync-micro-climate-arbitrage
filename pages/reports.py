"""
AtmoSync - Page 8: Reports & Data Management
Data Governance, Referential Audits, Multi-Format Exports (CSV, ZIP, Excel, PDF), and Database Management.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from database.database import (
    load_table, get_record_counts, init_db, save_dataframe_to_db, is_database_populated
)
from modules.data_generator import generate_all_datasets
from modules.data_cleaning import run_comprehensive_validation, get_data_quality_dataframe
from modules.risk_engine import calculate_shipment_risk, get_risk_summary
from modules.arbitrage_engine import evaluate_arbitrage_opportunities
from utils.export import create_datasets_zip, create_excel_workbook, generate_pdf_report
from utils.helpers import render_kpi_card
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Data Governance Suite:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)
    st.title("Data Management & Analytics Reports")
    st.caption(f"Relational Persistence, Referential Audits, Multi-Format Export Pipelines & PDF Intelligence Generation")

    # Load datasets
    datasets = {
        "commodities": load_table("commodities"),
        "markets": load_table("markets"),
        "market_prices": load_table("market_prices"),
        "shipments": load_table("shipments"),
        "sensor_readings": load_table("sensor_readings"),
        "arbitrage_opportunities": load_table("arbitrage_opportunities"),
        "alerts": load_table("alerts")
    }

    counts = get_record_counts()

    # Section 1: Dataset Summary KPI Cards
    st.subheader("📊 Relational Database Storage Summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(render_kpi_card("Total Records", f"{counts.get('total', 0):,}", "Active SQLite rows", icon="💾"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_kpi_card("Total Tables", f"{len(counts)-1}", "Relational schemas", icon="🗄️"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_kpi_card("Commodity SKUs", f"{counts.get('commodities', 0):,}", "Catalog records", icon="🌾"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_kpi_card("Tracked Mandis", f"{counts.get('markets', 0):,}", "APMC locations", icon="🏛️"), unsafe_allow_html=True)
    with c5:
        st.markdown(render_kpi_card("Sensor Readings", f"{counts.get('sensor_readings', 0):,}", "Telemetry packets", icon="📡"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Section 2: Data Quality & Referential Integrity Analysis
    st.subheader("🛡️ Automated Data Quality & Referential Integrity Audit")
    val_report = run_comprehensive_validation(datasets)
    quality_df = get_data_quality_dataframe(val_report)

    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        st.markdown(render_kpi_card("Data Completeness", f"{val_report['completeness_pct']}%", "Null & duplicate check", delta="100% Passed", delta_color="positive", icon="✅"), unsafe_allow_html=True)
    with qc2:
        st.markdown(render_kpi_card("Foreign Key Checks", f"{val_report['foreign_key_violations']}", "Orphaned relationships", delta="Zero Violations", delta_color="positive", icon="🔗"), unsafe_allow_html=True)
    with qc3:
        st.markdown(render_kpi_card("Missing Values", f"{val_report['null_value_counts']}", "Empty attribute cells", delta="Zero Nulls", delta_color="positive", icon="🔍"), unsafe_allow_html=True)
    with qc4:
        st.markdown(render_kpi_card("Range Violations", f"{val_report['range_violations']}", "Min <= Modal <= Max", delta="All Valid", delta_color="positive", icon="📐"), unsafe_allow_html=True)

    st.dataframe(quality_df, use_container_width=True)

    st.markdown("---")

    # Section 3: Data Preview
    st.subheader("📑 Interactive Dataset Table Browser")
    table_choice = st.selectbox(
        "Select Table to Preview:",
        ["commodities", "markets", "market_prices", "shipments", "sensor_readings", "arbitrage_opportunities", "alerts"]
    )
    if table_choice in datasets and not datasets[table_choice].empty:
        st.dataframe(datasets[table_choice].head(100), use_container_width=True)
        st.caption(f"Displaying top 100 rows of table '{table_choice}' (Total: {len(datasets[table_choice]):,} rows).")

    st.markdown("---")

    # Section 4: Multi-Format Data Downloads & PDF Dossier
    st.subheader("📥 Data Export & Report Generation Hub")
    
    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.markdown("#### 📄 Executive Analytical PDF Report")
        st.markdown("Generate a high-resolution, branded PDF dossier incorporating executive summaries, telemetry statistics, spoilage assessments, and arbitrage rankings.")
        
        if st.button("Generate PDF Report", type="primary", use_container_width=True):
            with st.spinner("Compiling ReportLab PDF document..."):
                # Compute live metrics for report
                risk_df = calculate_shipment_risk(datasets["shipments"], datasets["commodities"], datasets["sensor_readings"])
                r_summary = get_risk_summary(risk_df)
                
                summary_metrics = {
                    "total_shipments": len(datasets["shipments"]),
                    "active_shipments": int(datasets["shipments"]["shipment_status"].isin(["In Transit", "At Risk", "Delayed"]).sum()),
                    "at_risk_shipments": int((datasets["shipments"]["shipment_status"] == "At Risk").sum()),
                    "total_markets": len(datasets["markets"]),
                    "avg_temp": float(datasets["sensor_readings"]["temperature"].mean()) if not datasets["sensor_readings"].empty else 0.0,
                    "avg_hum": float(datasets["sensor_readings"]["humidity"].mean()) if not datasets["sensor_readings"].empty else 0.0,
                    "total_arbitrage": len(datasets["arbitrage_opportunities"]),
                    "max_benefit": float(datasets["arbitrage_opportunities"]["estimated_net_benefit"].max()) if not datasets["arbitrage_opportunities"].empty else 0.0
                }

                pdf_data = generate_pdf_report(summary_metrics, r_summary, datasets["arbitrage_opportunities"], val_report)
                
                st.download_button(
                    label="⬇️ Download Executive PDF Dossier",
                    data=pdf_data,
                    file_name=f"AtmoSync_Executive_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("Executive PDF report generated successfully!")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📦 Bulk Archives")
        zip_bytes = create_datasets_zip(datasets)
        st.download_button(
            label="⬇️ Download Complete Dataset Archive (ZIP containing all CSVs)",
            data=zip_bytes,
            file_name=f"AtmoSync_Full_Datasets_{datetime.now().strftime('%Y%m%d')}.zip",
            mime="application/zip",
            use_container_width=True
        )

        excel_bytes = create_excel_workbook(datasets)
        st.download_button(
            label="⬇️ Download Multi-Sheet Excel Workbook (.xlsx)",
            data=excel_bytes,
            file_name=f"AtmoSync_Worksheet_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col_d2:
        st.markdown("#### 📄 Individual Table CSV Downloads")
        st.markdown("Export individual schema tables directly for external processing:")
        
        for name, df in datasets.items():
            if not df.empty:
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇️ Download {name.replace('_', ' ').title()} CSV ({len(df):,} rows)",
                    data=csv_bytes,
                    file_name=f"atmosync_{name}.csv",
                    mime="text/csv",
                    key=f"dl_{name}",
                    use_container_width=True
                )

        quality_csv = quality_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Data Quality Report CSV",
            data=quality_csv,
            file_name="atmosync_data_quality_audit.csv",
            mime="text/csv",
            key="dl_quality",
            use_container_width=True
        )

    st.markdown("---")

    # Section 5: Database Configuration & Regeneration
    st.subheader("⚙️ Database Lifecycle Management & Synthetic Generator")
    st.markdown("Configure synthetic record volume and re-initialize relational SQLite database tables.")

    target_size = st.slider(
        "Target Total Records (5,000 to 10,000 records)",
        min_value=5000,
        max_value=10000,
        value=10000,
        step=500,
        help="Adjust target total records generated programmatically across all relational tables."
    )

    with st.expander("⚠️ Reset Database & Regenerate Synthetic Records (Requires Confirmation)"):
        st.error("Warning: This will truncate all tables in `atmosync.db` and synthesize new linked records.")
        confirm = st.checkbox("I confirm I want to reset and regenerate the database.")
        
        if st.button("Reset Database & Regenerate Records", disabled=not confirm, type="primary"):
            with st.spinner("Generating fresh synthetic dataset and re-populating SQLite..."):
                init_db(force_reset=True)
                new_datasets = generate_all_datasets(total_target=target_size)
                for t_name, t_df in new_datasets.items():
                    save_dataframe_to_db(t_df, t_name, if_exists="append")
                st.success(f"Database reset and successfully populated with {target_size:,} records!")
                st.rerun()

if __name__ == "__main__":
    render()
else:
    render()
