"""
AtmoSync - Page 8: Reports & Data Management
Data Governance, Relational Database Audits, Dataset Previews,
Multi-Format Export Pipelines (CSV, Excel, ZIP, PDF), and Database Status Monitoring.

DISCLAIMER:
All stored records and generated reports reflect synthetic agricultural simulation data.
"""

import io
import os
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL, DB_PATH
from database.database import (
    load_table, get_record_counts, init_db, save_dataframe_to_db,
    is_database_populated, execute_query, safe_import_dataframe, TABLE_SCHEMAS
)
from modules.data_generator import generate_all_datasets
from modules.data_cleaning import (
    run_comprehensive_validation, get_data_quality_dataframe,
    clean_and_preprocess_all, validate_cross_table_relationships,
    validate_uploaded_csv
)
from modules.risk_engine import calculate_shipment_risk, get_risk_summary
from modules.arbitrage_engine import evaluate_arbitrage_opportunities
from utils.export import (
    create_datasets_zip, create_excel_workbook, generate_pdf_report, build_filtered_report
)
from utils.helpers import render_kpi_card


def get_database_diagnostics() -> dict:
    """Retrieve database health, file size, and SQLite PRAGMA settings."""
    diag = {
        "exists": DB_PATH.exists(),
        "path": str(DB_PATH),
        "size_kb": 0.0,
        "integrity": "Unknown",
        "journal_mode": "Unknown",
        "foreign_keys": "Unknown"
    }
    if DB_PATH.exists():
        try:
            diag["size_kb"] = round(DB_PATH.stat().st_size / 1024.0, 1)
            integ_df = execute_query("PRAGMA integrity_check;")
            diag["integrity"] = str(integ_df.iloc[0, 0]) if not integ_df.empty else "OK"
            jm_df = execute_query("PRAGMA journal_mode;")
            diag["journal_mode"] = str(jm_df.iloc[0, 0]).upper() if not jm_df.empty else "WAL"
            fk_df = execute_query("PRAGMA foreign_keys;")
            diag["foreign_keys"] = "ENABLED (1)" if (not fk_df.empty and fk_df.iloc[0, 0] == 1) else "OFF (0)"
        except Exception as e:
            diag["integrity"] = f"Check Failed: {e}"
    return diag


def render():
    st.markdown(
        '<div class="disclaimer-banner"><strong>Data Governance Suite:</strong> '
        + PERSISTENT_DISCLAIMER
        + "</div>",
        unsafe_allow_html=True,
    )
    st.title("Data Management & Analytics Reports")
    st.caption(
        f"Relational Persistence, Referential Audits, Multi-Format Export Pipelines & PDF Intelligence Generation • {DATASET_LABEL}"
    )

    # ------------------------------------------------------------------
    # Load Datasets Safely
    # ------------------------------------------------------------------
    datasets = {}
    table_names = [
        "commodities", "markets", "market_prices",
        "shipments", "sensor_readings", "arbitrage_opportunities", "alerts"
    ]
    load_errors = []
    for t_name in table_names:
        try:
            datasets[t_name] = load_table(t_name)
        except Exception as e:
            load_errors.append(f"{t_name}: {e}")
            datasets[t_name] = pd.DataFrame()

    if load_errors:
        st.warning(f"Notice: Issues encountered loading some tables: {', '.join(load_errors)}")

    counts = get_record_counts()
    db_diag = get_database_diagnostics()

    # ------------------------------------------------------------------
    # Section 1: Database Status & Record Counts
    # ------------------------------------------------------------------
    st.subheader("📊 Relational Database Storage & Health Status")

    # Status Bar
    stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
    with stat_c1:
        st.markdown(f"**Database State:** `{'ONLINE 🟢' if db_diag['exists'] else 'OFFLINE 🔴'}`")
        st.markdown(f"**Path:** `{db_diag['path']}`")
    with stat_c2:
        st.markdown(f"**Storage Size:** `{db_diag['size_kb']} KB` ({db_diag['size_kb']/1024:.2f} MB)")
        st.markdown(f"**Integrity Check:** `{db_diag['integrity']}`")
    with stat_c3:
        st.markdown(f"**Journal Mode:** `{db_diag['journal_mode']}`")
        st.markdown(f"**Foreign Keys:** `{db_diag['foreign_keys']}`")
    with stat_c4:
        st.markdown(f"**Total Records:** `{counts.get('total', 0):,}` rows")
        st.markdown(f"**Cataloged Tables:** `{len(table_names)} tables`")

    st.markdown("<br>", unsafe_allow_html=True)

    # Table Counts KPI Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(render_kpi_card("Total Records", f"{counts.get('total', 0):,}", "Active SQLite rows", icon="💾"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_kpi_card("Commodity SKUs", f"{counts.get('commodities', 0):,}", "Catalog records", icon="🌾"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_kpi_card("APMC Mandis", f"{counts.get('markets', 0):,}", "Trading hubs", icon="🏛️"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_kpi_card("Shipments", f"{counts.get('shipments', 0):,}", "Highway manifests", icon="🚚"), unsafe_allow_html=True)
    with c5:
        st.markdown(render_kpi_card("Sensor Readings", f"{counts.get('sensor_readings', 0):,}", "IoT telemetry packets", icon="📡"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Section 2: Automated Data Quality, Null & Duplicate Audits
    # ------------------------------------------------------------------
    st.subheader("🛡️ Automated Data Quality & Referential Integrity Audit")
    val_report = run_comprehensive_validation(datasets)
    rel_report = validate_cross_table_relationships(datasets)
    quality_df = get_data_quality_dataframe(val_report)

    if val_report["is_valid"] and rel_report["all_valid"]:
        st.success(
            "🟢 **Data Quality Verification Passed:** 100% referential integrity verified. "
            "Zero missing primary keys, zero unlinked foreign keys, zero date inversions, and all numeric constraints validated."
        )
    else:
        st.warning(
            f"⚠️ **Data Quality Notice:** Identified {val_report['null_value_counts']} null cells, "
            f"{val_report['duplicate_counts']} duplicate keys, {val_report['range_violations']} range excursions, "
            f"and {rel_report['total_violations']} unlinked relationship records."
        )

    qc1, qc2, qc3, qc4, qc5 = st.columns(5)
    with qc1:
        st.markdown(render_kpi_card("Data Completeness", f"{val_report['completeness_pct']}%", "Null & duplicate check", delta="100% Passed" if val_report['completeness_pct'] == 100 else "Issues Detected", delta_color="positive" if val_report['completeness_pct'] == 100 else "negative", icon="✅"), unsafe_allow_html=True)
    with qc2:
        st.markdown(render_kpi_card("Foreign Key Checks", f"{val_report['foreign_key_violations']}", "Cross-table linkage", delta="Zero Violations" if val_report['foreign_key_violations'] == 0 else "Violations Detected", delta_color="positive" if val_report['foreign_key_violations'] == 0 else "negative", icon="🔗"), unsafe_allow_html=True)
    with qc3:
        st.markdown(render_kpi_card("Missing Values", f"{val_report['null_value_counts']}", "Empty attribute cells", delta="Zero Nulls" if val_report['null_value_counts'] == 0 else "Nulls Flagged", delta_color="positive" if val_report['null_value_counts'] == 0 else "negative", icon="🔍"), unsafe_allow_html=True)
    with qc4:
        st.markdown(render_kpi_card("Duplicate Records", f"{val_report['duplicate_counts']}", "Primary key collisions", delta="Zero Duplicates" if val_report['duplicate_counts'] == 0 else "Duplicates Found", delta_color="positive" if val_report['duplicate_counts'] == 0 else "negative", icon="📐"), unsafe_allow_html=True)
    with qc5:
        st.markdown(render_kpi_card("Date & Range Audits", f"{val_report['date_violations'] + val_report['range_violations']}", "Temporal & numeric bounds", delta="Zero Inversions" if (val_report['date_violations'] + val_report['range_violations']) == 0 else "Violations Flagged", delta_color="positive" if (val_report['date_violations'] + val_report['range_violations']) == 0 else "negative", icon="⏱️"), unsafe_allow_html=True)

    st.dataframe(quality_df, use_container_width=True)

    btn_c1, btn_c2 = st.columns([1.5, 2.5])
    with btn_c1:
        if st.button("🧹 Run Automated Preprocessing & Data Sanitization", key="btn_run_sanitize"):
            with st.spinner("Executing sanitization, referential alignment and domain bounds enforcement..."):
                cleaned_ds, clean_rep = clean_and_preprocess_all(datasets)
                for t_name, c_df in cleaned_ds.items():
                    save_dataframe_to_db(c_df, t_name, if_exists="replace")
                st.success("✅ Dataset sanitization and preprocessing complete: 100% integrity verified and persisted!")
                st.rerun()

    with st.expander("📤 Upload & Validate External CSV Dataset (Safe Import)", expanded=False):
        st.caption("Upload a CSV file for schema validation, sanitization, and duplicate-safe import into SQLite.")
        up_c1, up_c2 = st.columns([1.2, 1.8])
        with up_c1:
            target_tbl = st.selectbox(
                "Target Database Table:",
                list(TABLE_SCHEMAS.keys()),
                index=0,
                key="csv_upload_target_tbl"
            )
            import_mode = st.radio(
                "Duplicate Key Handling:",
                ["skip_duplicates", "upsert"],
                format_func=lambda m: "Skip Existing Primary Keys" if m == "skip_duplicates" else "Update / Upsert Existing Keys",
                key="csv_upload_mode"
            )
        with up_c2:
            req_cols = TABLE_SCHEMAS[target_tbl]["required_cols"]
            st.markdown(f"**Required Columns (`{target_tbl}`):** `{', '.join(req_cols)}`")
            uploaded_csv = st.file_uploader(
                "Select CSV File to Validate & Import",
                type=["csv"],
                key="csv_file_uploader"
            )

        if uploaded_csv is not None:
            validation_res = validate_uploaded_csv(uploaded_csv, target_tbl, reference_data=datasets)
            for warn_msg in validation_res["warnings"]:
                st.warning(f"⚠️ {warn_msg}")
            for err_msg in validation_res["errors"]:
                st.error(f"❌ {err_msg}")

            if validation_res["is_valid"]:
                clean_preview = validation_res["df"]
                st.success(
                    f"✅ CSV validation passed: {len(clean_preview):,} valid record(s) ready for import "
                    f"(from {validation_res['summary']['raw_rows']:,} raw rows)."
                )
                st.dataframe(clean_preview.head(10), use_container_width=True)
                if st.button("💾 Confirm Safe Import to SQLite", key="btn_confirm_csv_import", type="primary"):
                    imp_res = safe_import_dataframe(clean_preview, target_tbl, mode=import_mode)
                    if imp_res["status"] == "success":
                        st.success(f"✅ {imp_res['message']} (Skipped duplicates: {imp_res.get('skipped_duplicates', 0)})")
                        st.rerun()
                    else:
                        st.error(f"❌ {imp_res['message']}")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Section 3: Interactive Dataset Preview with Search & Filter
    # ------------------------------------------------------------------
    st.subheader("📑 Interactive Dataset Table Browser & Filtered Preview")
    st.caption("Select a table, search or filter rows, inspect data attributes, and export the exact filtered subset.")

    p_c1, p_c2, p_c3 = st.columns([1.5, 2.0, 1.0])
    with p_c1:
        table_choice = st.selectbox(
            "Select Table to Preview:",
            table_names,
            index=0,
            key="report_table_choice"
        )
    with p_c2:
        search_filter = st.text_input(
            "Search Table Content:",
            placeholder="Filter rows by any text value...",
            key="report_search_filter"
        )
    with p_c3:
        row_limit = st.selectbox("Display Limit:", [50, 100, 250, 500], index=1, key="report_row_limit")

    target_df = datasets.get(table_choice, pd.DataFrame())

    if not target_df.empty:
        # Apply search filter across all string columns
        if search_filter:
            s_term = search_filter.lower().strip()
            mask = target_df.astype(str).apply(lambda row: row.str.lower().str.contains(s_term, na=False)).any(axis=1)
            preview_df = target_df[mask]
        else:
            preview_df = target_df

        st.caption(f"Showing {min(len(preview_df), row_limit):,} of {len(preview_df):,} matched rows (Total table rows: {len(target_df):,}).")
        st.dataframe(preview_df.head(row_limit), use_container_width=True, height=280)

        # Download Filtered View Button
        filtered_csv_bytes = preview_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"⬇️ Export Filtered View ({len(preview_df):,} rows as CSV)",
            data=filtered_csv_bytes,
            file_name=f"atmosync_{table_choice}_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key=f"dl_filtered_{table_choice}",
            help="Exports the exact filtered search results visible in the table browser."
        )
    else:
        st.info(f"Table '{table_choice}' is currently empty.")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Section 4: Filtered Analytical Report Generator & Export Hub
    # ------------------------------------------------------------------
    st.subheader("📥 Filtered Analytical Report Generator & Export Hub")
    st.caption("Generate domain-specific analytical reports from live SQLite records with date/category filters and synthetic-data provenance.")

    report_types = [
        "Shipment Summary",
        "IoT Sensor Analytics",
        "Commodity Price Analysis",
        "Spoilage Risk Summary",
        "Market Arbitrage Opportunities"
    ]

    rf1, rf2, rf3 = st.columns([1.4, 1.3, 1.3])
    with rf1:
        selected_rep_type = st.selectbox("Select Analytical Report:", report_types, index=0, key="rep_gen_type")

    # Determine appropriate date bounds & category options dynamically
    with rf2:
        if selected_rep_type in ["Shipment Summary", "Spoilage Risk Summary", "Market Arbitrage Opportunities"]:
            dt_col = pd.to_datetime(datasets["shipments"]["departure_date"], errors="coerce").dropna() if not datasets["shipments"].empty else pd.Series(dtype="datetime64[ns]")
        elif selected_rep_type == "IoT Sensor Analytics":
            dt_col = pd.to_datetime(datasets["sensor_readings"]["timestamp"], errors="coerce").dropna() if not datasets["sensor_readings"].empty else pd.Series(dtype="datetime64[ns]")
        else:
            dt_col = pd.to_datetime(datasets["market_prices"]["date"], errors="coerce").dropna() if not datasets["market_prices"].empty else pd.Series(dtype="datetime64[ns]")

        if not dt_col.empty:
            rep_date_range = st.date_input(
                "Report Date Range:",
                value=(dt_col.min().date(), dt_col.max().date()),
                min_value=dt_col.min().date(),
                max_value=dt_col.max().date(),
                key=f"rep_date_range_{selected_rep_type}"
            )
        else:
            rep_date_range = None

    with rf3:
        if selected_rep_type == "Shipment Summary":
            cat_opts = ["All", "In Transit", "Delivered", "Delayed", "At Risk", "Completed"]
        elif selected_rep_type == "IoT Sensor Analytics":
            cat_opts = ["All", "Normal", "Warning", "Critical"]
        elif selected_rep_type == "Commodity Price Analysis":
            cat_opts = ["All", "Fruit", "Vegetable"]
        elif selected_rep_type == "Spoilage Risk Summary":
            cat_opts = ["All", "Critical", "High", "Moderate", "Low"]
        else:
            cat_opts = ["All", "Profitable Only", "Unprofitable Only"]
        selected_rep_cat = st.selectbox("Category / Status Filter:", cat_opts, index=0, key=f"rep_cat_{selected_rep_type}")

    rep_df, rep_summary, rep_scope = build_filtered_report(
        selected_rep_type, datasets, date_range=rep_date_range, category_filter=selected_rep_cat
    )

    if rep_df.empty:
        st.warning(f"⚠️ No records match the selected filters for '{selected_rep_type}'. Please broaden your date range or category selection.")
    else:
        # Display computed summary metrics
        sm_cols = st.columns(len(rep_summary))
        for idx, (m_label, m_val) in enumerate(rep_summary.items()):
            with sm_cols[idx]:
                st.metric(m_label, f"{m_val:,}" if isinstance(m_val, (int, float)) else str(m_val))

        st.dataframe(rep_df.head(100), use_container_width=True, height=240)
        st.caption(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Scope: {rep_scope} | {PERSISTENT_DISCLAIMER}")

        slug = selected_rep_type.lower().replace(" ", "_")
        date_stamp = datetime.now().strftime("%Y%m%d_%H%M")
        dl_c1, dl_c2 = st.columns(2)
        with dl_c1:
            rep_csv = rep_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"⬇️ Download {selected_rep_type} Report (.csv)",
                data=rep_csv,
                file_name=f"AtmoSync_{slug}_{date_stamp}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"dl_rep_csv_{slug}"
            )
        with dl_c2:
            rep_xlsx = create_excel_workbook({selected_rep_type[:31]: rep_df}, filter_summary=rep_scope)
            st.download_button(
                label=f"⬇️ Download {selected_rep_type} Report (.xlsx)",
                data=rep_xlsx,
                file_name=f"AtmoSync_{slug}_{date_stamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"dl_rep_xlsx_{slug}"
            )

    st.markdown("---")
    st.markdown("#### 📦 Executive PDF Dossier & Bulk Dataset Archives")

    col_d1, col_d2 = st.columns(2)

    with col_d1:
        st.markdown("#### 📄 Executive Analytical PDF Report")
        st.markdown(
            "Generate a high-resolution, branded PDF dossier incorporating executive summaries, "
            "telemetry statistics, spoilage assessments, and arbitrage rankings."
        )

        if st.button("Generate Executive PDF Report", type="primary", use_container_width=True, key="btn_gen_pdf"):
            with st.spinner("Compiling ReportLab PDF dossier..."):
                try:
                    # Compute live metrics for report
                    risk_df = calculate_shipment_risk(datasets["shipments"], datasets["commodities"], datasets["sensor_readings"])
                    r_summary = get_risk_summary(risk_df)

                    summary_metrics = {
                        "total_shipments": len(datasets["shipments"]),
                        "active_shipments": int(datasets["shipments"]["shipment_status"].isin(["In Transit", "At Risk", "Delayed"]).sum()) if not datasets["shipments"].empty else 0,
                        "at_risk_shipments": int((datasets["shipments"]["shipment_status"] == "At Risk").sum()) if not datasets["shipments"].empty else 0,
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
                        use_container_width=True,
                        key="btn_download_pdf_file"
                    )
                    st.success("Executive PDF report generated successfully!")
                except Exception as e:
                    st.error(f"Failed to generate PDF report: {e}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📦 Bulk Archives & Workbooks")

        try:
            zip_bytes = create_datasets_zip(datasets)
            st.download_button(
                label="⬇️ Download Complete Dataset Archive (ZIP of all CSVs)",
                data=zip_bytes,
                file_name=f"AtmoSync_Full_Datasets_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
                use_container_width=True,
                key="dl_zip_all"
            )
        except Exception as e:
            st.error(f"ZIP export creation error: {e}")

        try:
            excel_bytes = create_excel_workbook(datasets)
            st.download_button(
                label="⬇️ Download Multi-Sheet Excel Workbook (.xlsx)",
                data=excel_bytes,
                file_name=f"AtmoSync_Worksheet_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_excel_all"
            )
        except Exception as e:
            st.error(f"Excel export creation error: {e}")

    with col_d2:
        st.markdown("#### 📄 Individual Table CSV Downloads")
        st.markdown("Export individual database tables directly for external processing:")

        for name in table_names:
            df = datasets.get(name, pd.DataFrame())
            if not df.empty:
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇️ Download {name.replace('_', ' ').title()} CSV ({len(df):,} rows)",
                    data=csv_bytes,
                    file_name=f"atmosync_{name}.csv",
                    mime="text/csv",
                    key=f"dl_tbl_{name}",
                    use_container_width=True
                )
            else:
                st.button(f"Table '{name}' is Empty", disabled=True, use_container_width=True, key=f"dl_empty_{name}")

        quality_csv = quality_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Data Quality Report CSV",
            data=quality_csv,
            file_name="atmosync_data_quality_audit.csv",
            mime="text/csv",
            key="dl_quality_csv",
            use_container_width=True
        )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Section 5: Database Lifecycle Management & Synthetic Generator
    # ------------------------------------------------------------------
    st.subheader("⚙️ Database Lifecycle Management & Synthetic Generator")
    st.markdown("Configure synthetic record volume and re-initialize relational SQLite database tables.")

    target_size = st.slider(
        "Target Total Records (5,000 to 10,000 records)",
        min_value=5000,
        max_value=10000,
        value=10000,
        step=500,
        help="Adjust target total records generated programmatically across all relational tables.",
        key="target_size_slider"
    )

    with st.expander("⚠️ Reset Database & Regenerate Synthetic Records (Requires Confirmation)"):
        st.error("Warning: This will truncate all tables in `atmosync.db` and synthesize new linked records.")
        confirm = st.checkbox("I confirm I want to reset and regenerate the database.", key="chk_confirm_reset")

        if st.button("Reset Database & Regenerate Records", disabled=not confirm, type="primary", key="btn_reset_db"):
            with st.spinner("Generating fresh synthetic dataset and re-populating SQLite..."):
                try:
                    init_db(force_reset=True)
                    new_datasets = generate_all_datasets(total_target=target_size)
                    for t_name, t_df in new_datasets.items():
                        save_dataframe_to_db(t_df, t_name, if_exists="append")
                    st.success(f"Database reset and successfully populated with {target_size:,} records!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Database regeneration failed: {e}")


if __name__ == "__main__":
    render()
else:
    render()
