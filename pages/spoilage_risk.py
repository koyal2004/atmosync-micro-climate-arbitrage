"""
AtmoSync - Page 6: Spoilage Risk Analysis
Commodity Spoilage Risk Intelligence: Parametric degradation models, multi-factor exposure scoring, and shelf-life projections.
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
from config.settings import PERSISTENT_DISCLAIMER, COLORS, RISK_TIERS

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Synthetic Risk Model:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)
    st.title("Commodity Spoilage Risk Intelligence")
    st.caption("Thermal Deviation Integral, Cumulative Stress Modeling & Quality Degradation Forecasting")

    shipments_df = load_table("shipments")
    commodities_df = load_table("commodities")
    sensor_df = load_table("sensor_readings")

    if shipments_df.empty:
        st.warning("Shipment dataset is empty.")
        return

    # Calculate transparent risk scores
    risk_df = calculate_shipment_risk(shipments_df, commodities_df, sensor_df)
    summary = get_risk_summary(risk_df)

    # 6 KPI Cards (Section 11)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(render_kpi_card("Low-Risk Consignments", f"{summary['low']:,}", "0–24 Risk Index", icon="🟢"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Moderate-Risk", f"{summary['moderate']:,}", "25–49 Risk Index", icon="🔵"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("High-Risk", f"{summary['high']:,}", "50–74 Risk Index", delta="Elevated alert", delta_color="negative", icon="🟠"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Critical Shipments", f"{summary['critical']:,}", "75–100 Risk Index", delta=f"{summary['critical']} require diversion", delta_color="negative", icon="🔴"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Average Risk Score", f"{summary['avg_risk']:.1f} / 100", "Fleet composite index", icon="📊"), unsafe_allow_html=True)
    with k6:
        st.markdown(render_kpi_card("Est. Quality Loss", f"{summary['avg_loss']:.1f} %", "Projected inventory loss", delta_color="negative", icon="📉"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Transparent Formula Explanation Box
    with st.expander("ℹ️ Transparent Spoilage Risk Scoring Mathematical Methodology"):
        st.markdown(r"""
        The **AtmoSync Environmental Exposure Score ($E$)** is modeled as a function of thermal kinetics, moisture saturation, and transit duration:
        
        $$E_{\text{temp}} = \min\left(50, \, (\Delta T)^{1.25} \times (\tau_{\text{days}})^{0.5} \times 4.2\right)$$
        $$E_{\text{humidity}} = \min\left(25, \, (\Delta H) \times 1.5\right)$$
        $$\text{Risk Score} = \min\left(100, \, (E_{\text{temp}} + E_{\text{humidity}} + E_{\text{vibration}}) \times W_{\text{sensitivity}}\right)$$
        
        Where:
        - $\Delta T = \max(0, T_{\text{actual}} - T_{\text{max\_threshold}}) + \max(0, T_{\text{min\_threshold}} - T_{\text{actual}})$
        - $\Delta H = \max(0, H_{\text{actual}} - H_{\text{max\_threshold}})$
        - $\tau_{\text{days}}$ is the transit duration computed via corridor distance / 420 km/day.
        - $W_{\text{sensitivity}} \in \{0.65, 1.00, 1.35, 1.70\}$ based on agricultural biological respiration sensitivity.
        - Risk Categories: **0–24** (Low), **25–49** (Moderate), **50–74** (High), **75–100** (Critical).
        """)

    # Visualizations (7 Core Charts per Section 11)
    st.subheader("📊 Spoilage Risk Visual Intelligence Suite (7 Core Charts)")

    # 1. Risk distribution
    # 2. Shipment risk ranking
    c1, c2 = st.columns(2)
    with c1:
        risk_color_map = {"Low": COLORS["success"], "Moderate": COLORS["info"], "High": COLORS["warning"], "Critical": COLORS["critical"]}
        fig_donut = create_donut_chart(risk_df, "risk_category", title="1. Consignment Risk Category Distribution", color_map=risk_color_map)
        st.plotly_chart(fig_donut, use_container_width=True)

    with c2:
        top_ranked = risk_df.sort_values("risk_score", ascending=False).head(12)
        fig_rank = create_bar_chart(top_ranked, "shipment_id", "risk_score", color_col="risk_category", color_map=risk_color_map, title="2. Top 12 Highest-Risk Freight Shipments")
        st.plotly_chart(fig_rank, use_container_width=True)

    # 3. Temperature exposure analysis
    # 4. Humidity exposure analysis
    c3, c4 = st.columns(2)
    with c3:
        fig_t_exp = px.histogram(risk_df, x="temperature_score", nbins=25, title="3. Temperature Exposure Score Histogram (0–50 pts)", color_discrete_sequence=[COLORS["critical"]])
        fig_t_exp.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_t_exp, use_container_width=True)

    with c4:
        fig_h_exp = px.histogram(risk_df, x="humidity_score", nbins=25, title="4. Humidity Stress Score Histogram (0–25 pts)", color_discrete_sequence=[COLORS["secondary"]])
        fig_h_exp.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_h_exp, use_container_width=True)

    # 5. Commodity-wise risk comparison
    # 6. Risk versus transportation duration
    c5, c6 = st.columns(2)
    with c5:
        comm_risk = risk_df.groupby("commodity_name")["risk_score"].mean().reset_index().sort_values("risk_score", ascending=False).head(10)
        fig_comm_r = create_bar_chart(comm_risk, "commodity_name", "risk_score", title="5. Top 10 Commodities by Vulnerability Index")
        st.plotly_chart(fig_comm_r, use_container_width=True)

    with c6:
        # Distance proxy for duration
        fig_dur = px.scatter(risk_df.sample(n=min(500, len(risk_df)), random_state=42), 
                             x="distance_km", y="risk_score", color="risk_category",
                             color_discrete_map=risk_color_map,
                             title="6. Risk Score vs. Transportation Corridor Distance (km)")
        fig_dur.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_dur, use_container_width=True)

    # 7. Estimated remaining shelf-life analysis
    st.markdown("#### 7. Remaining Estimated Shelf-Life by Consignment Vulnerability")
    fig_shelf = px.box(risk_df, x="risk_category", y="estimated_remaining_shelf_life", 
                       color="risk_category", color_discrete_map=risk_color_map,
                       title="7. Remaining Shelf Life Distribution (Days) across Risk Tiers")
    fig_shelf.update_layout(**THEME_LAYOUT)
    st.plotly_chart(fig_shelf, use_container_width=True)

    # SHIPMENT RISK TABLE (Section 11)
    st.markdown("---")
    st.subheader(f"📋 Consignment Spoilage Risk Registry ({len(risk_df):,} entries)")
    
    # Filter
    t_f1, t_f2 = st.columns([1, 2])
    with t_f1:
        cat_filter = st.selectbox("Filter Risk Category:", ["All", "Critical", "High", "Moderate", "Low"])
    with t_f2:
        search_txt = st.text_input("Filter by Shipment ID or Commodity Name:", placeholder="e.g. SHP-0042, Tomato")

    display_table = risk_df.copy()
    if cat_filter != "All":
        display_table = display_table[display_table["risk_category"] == cat_filter]
    if search_txt:
        s_low = search_txt.lower()
        display_table = display_table[
            display_table["shipment_id"].str.lower().str.contains(s_low) |
            display_table["commodity_name"].str.lower().str.contains(s_low)
        ]

    # Required columns
    table_cols = [
        "shipment_id", "commodity_name", "container_id", "current_temperature",
        "current_humidity", "risk_score", "risk_category", "estimated_quality",
        "estimated_remaining_shelf_life"
    ]
    renamed_cols = {
        "shipment_id": "Shipment ID",
        "commodity_name": "Commodity",
        "container_id": "Container ID",
        "current_temperature": "Current Temp (°C)",
        "current_humidity": "Current Humidity (%)",
        "risk_score": "Risk Score (0–100)",
        "risk_category": "Risk Category",
        "estimated_quality": "Estimated Quality (%)",
        "estimated_remaining_shelf_life": "Remaining Shelf Life (days)"
    }
    st.dataframe(display_table[table_cols].rename(columns=renamed_cols), use_container_width=True, height=350)

if __name__ == "__main__":
    render()
else:
    render()
