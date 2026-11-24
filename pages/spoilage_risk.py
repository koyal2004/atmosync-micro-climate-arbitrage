"""
AtmoSync - Page 6: Spoilage Risk Analysis
Commodity Spoilage Risk Intelligence: Transparent rule-based degradation models,
multi-factor environmental exposure scoring, and shelf-life projections.

DISCLAIMER:
All risk scores and categories are project-defined heuristic rules for academic demonstration.
They are NOT scientifically validated spoilage prediction standards.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from database.database import load_table
from utils.helpers import render_kpi_card, get_status_badge
from utils.charts import (
    create_donut_chart, create_bar_chart, create_scatter_plot,
    create_line_chart, THEME_LAYOUT
)
from modules.risk_engine import calculate_shipment_risk, get_risk_summary
from modules.analytics import compute_spoilage_factor_breakdown
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL


def render():
    st.markdown(
        '<div class="disclaimer-banner"><strong>Academic Risk Scoring Engine:</strong> '
        + PERSISTENT_DISCLAIMER
        + "</div>",
        unsafe_allow_html=True,
    )
    st.title("Commodity Spoilage Risk Intelligence")
    st.caption(
        f"Rule-Based Environmental Stress Modeling, Multi-Factor Exposure Index & Shelf-Life Estimation • {DATASET_LABEL}"
    )

    try:
        shipments_df = load_table("shipments")
        commodities_df = load_table("commodities")
        sensor_df = load_table("sensor_readings")
    except Exception as e:
        st.error(f"⚠️ Failed to load database tables: {e}")
        return

    if shipments_df.empty:
        st.warning("Shipment dataset is empty. Please populate or initialize synthetic data.")
        return

    # Calculate transparent, rule-based risk scores
    risk_df = calculate_shipment_risk(shipments_df, commodities_df, sensor_df)
    if risk_df.empty:
        st.warning("Unable to compute risk scores. Please check database records.")
        return

    # ------------------------------------------------------------------
    # Interactive Sidebar Filters
    # ------------------------------------------------------------------
    st.sidebar.markdown("### 🛡️ Spoilage Risk Filters")

    # Risk Category Filter
    risk_categories = ["All", "Critical", "High", "Moderate", "Low"]
    selected_risk_cat = st.sidebar.selectbox("Risk Category Tier", risk_categories, index=0, key="spoil_risk_cat")

    # Commodity Filter
    all_commodities = ["All"] + sorted(risk_df["commodity_name"].dropna().unique().tolist())
    selected_comm = st.sidebar.selectbox("Commodity", all_commodities, index=0, key="spoil_comm")

    # Shipment Status Filter
    statuses = ["All"] + sorted(risk_df["shipment_status"].dropna().unique().tolist())
    selected_status = st.sidebar.selectbox("Shipment Status", statuses, index=0, key="spoil_status")

    # Date Range Filter
    if "departure_date" in risk_df.columns:
        risk_df["dep_date_dt"] = pd.to_datetime(risk_df["departure_date"], errors="coerce")
        min_date = risk_df["dep_date_dt"].min()
        max_date = risk_df["dep_date_dt"].max()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.sidebar.date_input(
                "Departure Date Range",
                value=(min_date.date(), max_date.date()),
                min_value=min_date.date(),
                max_value=max_date.date(),
                key="spoil_date_range"
            )
        else:
            date_range = None
    else:
        date_range = None

    # Apply Filters
    filtered_risk = risk_df.copy()
    if selected_risk_cat != "All":
        filtered_risk = filtered_risk[filtered_risk["risk_category"] == selected_risk_cat]
    if selected_comm != "All":
        filtered_risk = filtered_risk[filtered_risk["commodity_name"] == selected_comm]
    if selected_status != "All":
        filtered_risk = filtered_risk[filtered_risk["shipment_status"] == selected_status]
    if date_range and len(date_range) == 2 and "dep_date_dt" in filtered_risk.columns:
        start_d, end_d = date_range
        filtered_risk = filtered_risk[
            (filtered_risk["dep_date_dt"].dt.date >= start_d)
            & (filtered_risk["dep_date_dt"].dt.date <= end_d)
        ]

    # Handle Empty Data Condition gracefully
    if filtered_risk.empty:
        st.warning("⚠️ No consignments match the selected filter criteria. Please broaden your selection.")
        return

    # Compute Summary KPIs dynamically on filtered data
    summary = get_risk_summary(filtered_risk)

    # ------------------------------------------------------------------
    # KPI Cards (Project-Defined Tiers)
    # ------------------------------------------------------------------
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(render_kpi_card("Low-Risk (0–24)", f"{summary['low']:,}", "Nominal cold chain", icon="🟢"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Moderate (25–49)", f"{summary['moderate']:,}", "Minor excursions", icon="🔵"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("High-Risk (50–74)", f"{summary['high']:,}", "Action recommended", delta="Elevated alert", delta_color="negative", icon="🟠"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Critical (75–100)", f"{summary['critical']:,}", "Immediate reroute", delta=f"{summary['critical']} critical", delta_color="negative", icon="🔴"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Scope Avg Risk", f"{summary['avg_risk']:.1f} / 100", "Composite risk index", icon="📊"), unsafe_allow_html=True)
    with k6:
        st.markdown(render_kpi_card("Est. Quality Loss", f"{summary['avg_loss']:.1f} %", "Average degradation", delta_color="negative", icon="📉"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Transparent Rule-Based Mathematical Methodology & Disclaimer
    # ------------------------------------------------------------------
    with st.expander("ℹ️ Transparent Rule-Based Spoilage Risk Engine Formulation (Click to Expand)", expanded=False):
        st.markdown(r"""
        > **Academic Notice:** This calculation represents a **rule-based, heuristic scoring model** developed for demonstration
        > and decision-support simulation. It is **not a scientifically validated biochemical spoilage prediction standard**.

        The composite **Spoilage Risk Index ($R \in [0, 100]$)** incorporates four independent environmental and operational vectors:

        1. **Temperature Exposure Score ($E_{\text{temp}} \in [0, 50]$):**
           Calculates cumulative excursion degrees outside the commodity's optimal storage envelope $[T_{\min}, T_{\max}]$,
           amplified by transit duration $\tau$:
           $$\Delta T = \max(0, T_{\text{avg}} - T_{\max}) + \max(0, T_{\min} - T_{\text{avg}})$$
           $$E_{\text{temp}} = \min\left(50, \, (\Delta T)^{1.25} \times \tau_{\text{days}}^{0.5} \times 4.2\right)$$

        2. **Humidity Exposure Score ($E_{\text{hum}} \in [0, 25]$):**
           Penalizes excessive relative humidity above threshold $H_{\max}$ causing fungal/moisture condensation:
           $$E_{\text{hum}} = \min\left(25, \, \max(0, H_{\text{avg}} - H_{\max}) \times 1.5\right)$$

        3. **Vibration Exposure Score ($E_{\text{vibe}} \in [0, 15]$):**
           Penalizes continuous mechanical shock and chassis acceleration above $1.2\text{ g}$:
           $$E_{\text{vibe}} = \min\left(15, \, \max(0, \text{Vibe}_{\text{avg}} - 1.2) \times 4.0\right)$$

        4. **Commodity Sensitivity Weight ($W_{\text{sens}}$):**
           Biologically grounded respiration category multipliers:
           *Low* ($0.65$), *Moderate* ($1.00$), *High* ($1.35$), *Critical* ($1.70$).

        5. **Final Composite Score & Project Tiers:**
           $$\text{Risk Score} = \text{clamp}\Big((E_{\text{temp}} + E_{\text{hum}} + E_{\text{vibe}}) \times W_{\text{sens}}, \, 0, \, 100\Big)$$

        | Score Range | Risk Category | Operational Guidance |
        | :--- | :--- | :--- |
        | **0 – 24** | **Low** | Nominal transit; standard cold-chain protocol. |
        | **25 – 49** | **Moderate** | Minor stress; maintain continuous telemetry monitoring. |
        | **50 – 74** | **High** | Significant degradation risk; expedite corridor, adjust setpoint. |
        | **75 – 100** | **Critical** | Severe excursion; immediate dynamic reroute to nearest mandi. |
        """)

    # ------------------------------------------------------------------
    # Spoilage Visualizations Suite (Plotly Charts)
    # ------------------------------------------------------------------
    st.subheader("📊 Spoilage Risk Intelligence Dashboard")

    risk_color_map = {
        "Low": COLORS["success"],
        "Moderate": COLORS["info"],
        "High": COLORS["warning"],
        "Critical": COLORS["critical"]
    }

    # Row 1: Donut Distribution & Top Risk Consignments
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        fig_donut = create_donut_chart(
            filtered_risk, "risk_category",
            title="1. Spoilage Risk Category Distribution (Project-Defined)",
            color_map=risk_color_map
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with r1_c2:
        top_ranked = filtered_risk.sort_values("risk_score", ascending=False).head(12)
        fig_rank = create_bar_chart(
            top_ranked, "shipment_id", "risk_score",
            color_col="risk_category", color_map=risk_color_map,
            title="2. Top 12 Consignments Ranked by Risk Score"
        )
        st.plotly_chart(fig_rank, use_container_width=True)

    # Row 2: Exposure Histograms (Temperature, Humidity, Vibration)
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        fig_t_exp = px.histogram(
            filtered_risk, x="temperature_score", nbins=20,
            title="3. Temperature Exposure Score (0–50 pts)",
            color_discrete_sequence=[COLORS["critical"]]
        )
        fig_t_exp.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_t_exp, use_container_width=True)

    with r2_c2:
        fig_h_exp = px.histogram(
            filtered_risk, x="humidity_score", nbins=20,
            title="4. Humidity Stress Score (0–25 pts)",
            color_discrete_sequence=[COLORS["secondary"]]
        )
        fig_h_exp.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_h_exp, use_container_width=True)

    with r2_c3:
        fig_v_exp = px.histogram(
            filtered_risk, x="vibration_score", nbins=15,
            title="5. Vibration Impact Score (0–15 pts)",
            color_discrete_sequence=[COLORS["info"]]
        )
        fig_v_exp.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_v_exp, use_container_width=True)

    # Row 3: Commodity Vulnerability & Remaining Shelf Life Box Plot
    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        comm_risk = (
            filtered_risk.groupby("commodity_name")["risk_score"]
            .mean()
            .reset_index()
            .sort_values("risk_score", ascending=False)
            .head(10)
        )
        fig_comm_r = create_bar_chart(
            comm_risk, "commodity_name", "risk_score",
            title="6. Top Commodities by Average Risk Score"
        )
        st.plotly_chart(fig_comm_r, use_container_width=True)

    with r3_c2:
        fig_shelf = px.box(
            filtered_risk, x="risk_category", y="estimated_remaining_shelf_life",
            color="risk_category", color_discrete_map=risk_color_map,
            category_orders={"risk_category": ["Low", "Moderate", "High", "Critical"]},
            title="7. Remaining Shelf Life (Days) across Risk Tiers"
        )
        fig_shelf.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_shelf, use_container_width=True)

    # ------------------------------------------------------------------
    # Contributing Stressor Decomposition & Primary Driver Analysis
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔬 Environmental Contributing Stressors Decomposition")
    st.caption("Decomposing composite risk scores into temperature, humidity, and kinetic vibration stress vectors.")

    factor_data = compute_spoilage_factor_breakdown(filtered_risk)
    sb_c1, sb_c2, sb_c3, sb_c4 = st.columns(4)
    with sb_c1:
        st.metric("Thermal Stress Vector", f"{factor_data['temp_contrib_pct']}%", f"Mean: {factor_data['mean_temp_score']} pts")
    with sb_c2:
        st.metric("Moisture Stress Vector", f"{factor_data['hum_contrib_pct']}%", f"Mean: {factor_data['mean_hum_score']} pts")
    with sb_c3:
        st.metric("Kinetic Shock Vector", f"{factor_data['vibe_contrib_pct']}%", f"Mean: {factor_data['mean_vibe_score']} pts")
    with sb_c4:
        st.metric("Primary Degradation Driver", factor_data["primary_stressor"])

    top_comm_stress = filtered_risk.groupby("commodity_name")[["temperature_score", "humidity_score", "vibration_score"]].mean().reset_index().head(8)
    fig_stress_comp = go.Figure()
    fig_stress_comp.add_trace(go.Bar(
        x=top_comm_stress["commodity_name"], y=top_comm_stress["temperature_score"],
        name="Temperature Exposure (0-50 pts)", marker_color=COLORS["critical"]
    ))
    fig_stress_comp.add_trace(go.Bar(
        x=top_comm_stress["commodity_name"], y=top_comm_stress["humidity_score"],
        name="Humidity Condensation (0-25 pts)", marker_color=COLORS["secondary"]
    ))
    fig_stress_comp.add_trace(go.Bar(
        x=top_comm_stress["commodity_name"], y=top_comm_stress["vibration_score"],
        name="Vibration Impact (0-15 pts)", marker_color=COLORS["info"]
    ))
    fig_stress_comp.update_layout(
        barmode="stack",
        title="8. Biological Degradation Stressor Composition Across Varieties",
        yaxis_title="Cumulative Score Points",
        **THEME_LAYOUT
    )
    st.plotly_chart(fig_stress_comp, use_container_width=True)

    # ------------------------------------------------------------------
    # Spoilage Risk Registry Table (Full Specification Display)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader(f"📋 Consignment Spoilage Risk Registry ({len(filtered_risk):,} entries)")
    st.caption("Detailed breakdown per consignment with individual environmental exposure scores and recommended actions.")

    # Search Filter within the filtered view
    search_txt = st.text_input("Quick Search within filtered consignments (by Shipment ID or Commodity Name):", placeholder="e.g. SHP-0042, Tomato, Mango...", key="risk_search_txt")

    display_table = filtered_risk.copy()
    if search_txt:
        s_low = search_txt.lower().strip()
        display_table = display_table[
            display_table["shipment_id"].str.lower().str.contains(s_low, na=False)
            | display_table["commodity_name"].str.lower().str.contains(s_low, na=False)
        ]

    if display_table.empty:
        st.info("No shipments match the search query.")
        return

    # Required Display Columns:
    # Shipment ID, Commodity, Temperature exposure, Humidity exposure, Vibration exposure,
    # Remaining shelf life, Calculated risk score, Risk category, Recommended action
    table_cols = [
        "shipment_id", "commodity_name", "temperature_exposure",
        "humidity_exposure", "vibration_exposure",
        "estimated_remaining_shelf_life", "risk_score",
        "risk_category", "recommended_action"
    ]

    renamed_cols = {
        "shipment_id": "Shipment ID",
        "commodity_name": "Commodity",
        "temperature_exposure": "Temperature Exposure",
        "humidity_exposure": "Humidity Exposure",
        "vibration_exposure": "Vibration Exposure",
        "estimated_remaining_shelf_life": "Remaining Shelf Life (Days)",
        "risk_score": "Risk Score (0–100)",
        "risk_category": "Risk Category",
        "recommended_action": "Recommended Action"
    }

    st.dataframe(
        display_table[table_cols].rename(columns=renamed_cols),
        use_container_width=True,
        height=380
    )


if __name__ == "__main__":
    render()
else:
    render()
