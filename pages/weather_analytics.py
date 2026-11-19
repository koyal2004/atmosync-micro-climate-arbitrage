"""
AtmoSync - Page 5: Weather Analytics
Micro-Climate & Environmental Intelligence: Reefer micro-climate telemetry, environmental anomaly scoring, and threshold audits.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from database.database import load_table
from utils.helpers import render_kpi_card, get_status_badge
from utils.charts import (
    create_line_chart, create_scatter_plot, create_bar_chart, 
    create_donut_chart, THEME_LAYOUT
)
from modules.anomaly_detection import run_sensor_anomaly_detection
from config.settings import PERSISTENT_DISCLAIMER, COLORS

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Reefer Micro-Climate Analytics:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)
    st.title("Micro-Climate & Environmental Intelligence")
    st.caption("Internal Shipping Container Atmosphere, Thermal Boundaries, Moisture Saturation & Kinetic Shock")

    sensor_df = load_table("sensor_readings")
    commodities_df = load_table("commodities")
    alerts_df = load_table("alerts")

    if sensor_df.empty:
        st.warning("Sensor dataset is empty.")
        return

    # Run ML Anomaly Detection on telemetry
    sensor_ml, ml_summary = run_sensor_anomaly_detection(sensor_df)

    # Calculate KPIs (Section 10)
    avg_temp = float(sensor_df["temperature"].mean())
    avg_hum = float(sensor_df["humidity"].mean())
    max_temp = float(sensor_df["temperature"].max())
    env_alerts = int((sensor_df["sensor_status"] != "Normal").sum())
    avg_vibe = float(sensor_df["vibration"].mean())

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(render_kpi_card("Avg Temperature", f"{avg_temp:.1f} °C", "Chamber baseline", icon="🌡️"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Avg Humidity", f"{avg_hum:.1f} %", "Chamber saturation", icon="💧"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Max Temperature", f"{max_temp:.1f} °C", "Extreme excursion", delta=f"{max_temp - avg_temp:+.1f}°C deviation", delta_color="negative", icon="🔥"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Environmental Alerts", f"{env_alerts:,}", "Thermal & humidity breaches", delta=f"{env_alerts} occurrences", delta_color="negative", icon="🚨"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Avg Vibration", f"{avg_vibe:.2f} g", "Chassis kinetic baseline", icon="〰️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Configurable Environmental Thresholds Expander
    with st.expander("⚙️ Configure Parametric Environmental Thresholds (Analytical Assumptions)"):
        st.markdown("Adjust hypothetical thermal safety margins applied across reefer consignments for scenario testing.")
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            warn_temp_thresh = st.slider("Thermal Warning Boundary (°C)", min_value=12.0, max_value=24.0, value=15.0, step=0.5)
        with tc2:
            crit_temp_thresh = st.slider("Thermal Critical Boundary (°C)", min_value=18.0, max_value=32.0, value=22.0, step=0.5)
        with tc3:
            crit_hum_thresh = st.slider("Moisture Critical Boundary (% RH)", min_value=85.0, max_value=99.0, value=95.0, step=1.0)

    st.subheader("📊 Micro-Climate Analytical Suite (8 Core Charts)")

    # 1. Temperature trend
    # 2. Humidity trend
    r1_c1, r1_c2 = st.columns(2)
    sample_series = sensor_df.sort_values("timestamp").head(150)
    with r1_c1:
        fig_t = create_line_chart(sample_series, "timestamp", "temperature", title="1. Reefer Internal Temperature Trajectory (°C)", y_title="Temperature (°C)")
        st.plotly_chart(fig_t, use_container_width=True)

    with r1_c2:
        fig_h = create_line_chart(sample_series, "timestamp", "humidity", title="2. Internal Relative Humidity Saturation (%)", y_title="Humidity (%)")
        st.plotly_chart(fig_h, use_container_width=True)

    # 3. Temperature versus humidity
    # 4. Vibration analysis
    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        fig_scat = create_scatter_plot(sensor_ml.sample(n=min(1000, len(sensor_ml)), random_state=42), 
                                       "temperature", "humidity", color_col="sensor_status", 
                                       title="3. Temperature vs. Humidity Exposure Profile")
        st.plotly_chart(fig_scat, use_container_width=True)

    with r2_c2:
        fig_vibe_hist = px.histogram(sensor_df, x="vibration", nbins=30, title="4. Vibration Accelerometer Distribution (g RMS)", color_discrete_sequence=[COLORS["primary"]])
        fig_vibe_hist.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_vibe_hist, use_container_width=True)

    # 5. Environmental condition distribution
    # 6. Container-wise environmental comparison
    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        stat_colors = {"Normal": COLORS["info"], "Warning": COLORS["warning"], "Critical": COLORS["critical"]}
        fig_stat = create_donut_chart(sensor_df, "sensor_status", title="5. Environmental Condition Classification", color_map=stat_colors)
        st.plotly_chart(fig_stat, use_container_width=True)

    with r3_c2:
        cont_compare = sensor_df.groupby("container_id").agg({"temperature": "mean", "humidity": "mean"}).reset_index().head(12)
        fig_cont = go.Figure()
        fig_cont.add_trace(go.Bar(x=cont_compare["container_id"], y=cont_compare["temperature"], name="Avg Temp (°C)", marker_color=COLORS["critical"]))
        fig_cont.add_trace(go.Bar(x=cont_compare["container_id"], y=cont_compare["humidity"], name="Avg Humidity (%)", marker_color=COLORS["secondary"]))
        fig_cont.update_layout(barmode="group", title="6. Container-Wise Micro-Climate Comparison", **THEME_LAYOUT)
        st.plotly_chart(fig_cont, use_container_width=True)

    # 7. Daily temperature variation
    # 8. Environmental anomaly analysis (Isolation Forest)
    r4_c1, r4_c2 = st.columns(2)
    with r4_c1:
        sensor_daily = sensor_df.copy()
        sensor_daily["date"] = pd.to_datetime(sensor_daily["timestamp"]).dt.strftime("%Y-%m-%d")
        daily_spread = sensor_daily.groupby("date")["temperature"].agg(["min", "mean", "max"]).reset_index().tail(25)
        
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Scatter(x=daily_spread["date"], y=daily_spread["max"], name="Max Recorded", line={"color": COLORS["critical"]}))
        fig_daily.add_trace(go.Scatter(x=daily_spread["date"], y=daily_spread["min"], name="Min Recorded", line={"color": COLORS["info"]}, fill="tonexty", fillcolor="rgba(16, 36, 58, 0.1)"))
        fig_daily.add_trace(go.Scatter(x=daily_spread["date"], y=daily_spread["mean"], name="Mean Temperature", line={"color": COLORS["primary"], "width": 2}))
        fig_daily.update_layout(title="7. Daily Reefer Ambient Range & Spread", **THEME_LAYOUT)
        st.plotly_chart(fig_daily, use_container_width=True)

    with r4_c2:
        ml_counts = sensor_ml["ml_anomaly_label"].value_counts().reset_index()
        ml_counts.columns = ["label", "count"]
        fig_ml_bar = create_bar_chart(ml_counts, "label", "count", color_col="label", 
                                      color_map={"Normal": COLORS["info"], "Anomaly": COLORS["critical"]},
                                      title="8. Isolation Forest ML Sensor Anomaly Detection Distribution")
        st.plotly_chart(fig_ml_bar, use_container_width=True)

if __name__ == "__main__":
    render()
else:
    render()
