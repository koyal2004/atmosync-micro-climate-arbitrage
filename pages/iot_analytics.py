"""
AtmoSync - Page 3: IoT Sensor Analytics
Live Container Sensor Intelligence: Streaming telemetry simulation, environmental anomalies, and reefer condition monitoring.
"""

import time
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from database.database import load_table
from utils.helpers import render_kpi_card, get_status_badge
from utils.charts import (
    create_line_chart, create_scatter_plot, create_bar_chart, 
    create_donut_chart, create_dual_axis_chart
)
from modules.anomaly_detection import run_sensor_anomaly_detection
from config.settings import PERSISTENT_DISCLAIMER, COLORS

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Simulated IoT Streaming – Not Connected to Physical Sensors:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)
    st.title("Live Container Sensor Intelligence")
    st.caption("Container Micro-Climate Ingestion, Thermal Dynamics, Vibration Sensors & Real-Time Event Replay")

    sensor_df = load_table("sensor_readings")
    shipments_df = load_table("shipments")

    if sensor_df.empty:
        st.warning("Sensor dataset is empty. Please generate synthetic data.")
        return

    # Machine Learning Anomaly Detection
    sensor_with_ml, anomaly_summary = run_sensor_anomaly_detection(sensor_df)

    # Global Sensor KPIs (Section 8)
    avg_temp = float(sensor_df["temperature"].mean())
    max_temp = float(sensor_df["temperature"].max())
    avg_hum = float(sensor_df["humidity"].mean())
    max_hum = float(sensor_df["humidity"].max())
    abnormal_count = int(sensor_df["sensor_status"].isin(["Warning", "Critical"]).sum())
    active_sensors = sensor_df["container_id"].nunique()

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(render_kpi_card("Avg Temp", f"{avg_temp:.1f} °C", "Chamber average", icon="🌡️"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Max Temp", f"{max_temp:.1f} °C", "Peak exposure", delta=f"{max_temp - avg_temp:+.1f}°C spike", delta_color="negative", icon="🔥"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Avg Humidity", f"{avg_hum:.1f} %", "RH setpoint", icon="💧"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Max Humidity", f"{max_hum:.1f} %", "Moisture peak", icon="🌫️"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Abnormal Events", f"{abnormal_count:,}", "Warning / Critical", delta=f"{anomaly_summary['anomaly_rate']}% ML flagged", delta_color="negative", icon="⚠️"), unsafe_allow_html=True)
    with k6:
        st.markdown(render_kpi_card("Monitored Reefers", f"{active_sensors:,}", "Active containers", icon="📡"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # STREAMING SIMULATION CONTROL PANEL
    st.subheader("⚡ Live Sensor Telemetry Stream Replay Engine")
    
    # Initialize simulation states
    if "sim_active" not in st.session_state:
        st.session_state.sim_active = False
    if "sim_step" not in st.session_state:
        st.session_state.sim_step = 0
    if "sim_buffer" not in st.session_state:
        st.session_state.sim_buffer = []

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.5, 1.5, 1.2, 1.2])

    with ctrl_col1:
        container_list = sorted(sensor_df["container_id"].unique().tolist())
        selected_container = st.selectbox("Select Target Reefer Container:", container_list, index=0)
    with ctrl_col2:
        update_interval = st.selectbox("Replay Speed Interval:", [1, 2, 3, 5], index=1, format_func=lambda x: f"{x} second{'s' if x>1 else ''} per cycle")

    with ctrl_col3:
        st.write("")
        st.write("")
        if not st.session_state.sim_active:
            if st.button("▶️ Start Stream", use_container_width=True, type="primary"):
                st.session_state.sim_active = True
                st.session_state.sim_step = 0
                st.session_state.sim_buffer = []
                st.rerun()
        else:
            if st.button("⏸️ Pause Stream", use_container_width=True):
                st.session_state.sim_active = False
                st.rerun()

    with ctrl_col4:
        st.write("")
        st.write("")
        if st.button("⏹️ Reset Stream", use_container_width=True):
            st.session_state.sim_active = False
            st.session_state.sim_step = 0
            st.session_state.sim_buffer = []
            st.rerun()

    # Streaming logic & fragment
    container_history = sensor_df[sensor_df["container_id"] == selected_container].sort_values("timestamp").reset_index(drop=True)
    
    if st.session_state.sim_active:
        st.info(f"🟢 **Live Replay Active** for Reefer `{selected_container}`. Auto-ingesting event ticks every {update_interval}s.")
        step = st.session_state.sim_step
        total_steps = len(container_history)

        if step < total_steps:
            current_reading = container_history.iloc[step].to_dict()
            st.session_state.sim_buffer.append(current_reading)
            st.session_state.sim_step += 1
        else:
            st.success("Replay sequence completed for this container manifest. Resetting buffer.")
            st.session_state.sim_step = 0

    # Display live telemetry monitor box
    if st.session_state.sim_buffer:
        latest = st.session_state.sim_buffer[-1]
        sim_stream_df = pd.DataFrame(st.session_state.sim_buffer)

        # Highlight box for latest reading
        badge = get_status_badge(latest['sensor_status'])
        st.markdown(f"""
        <div style="background:#FFFFFF; border:2px solid {COLORS['secondary']}; border-radius:10px; padding:15px; margin-bottom:15px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:1.1rem; font-weight:700; color:{COLORS['primary']};">
                    Telemetry Stream Packet: <code>{latest['sensor_id']}</code>
                </span>
                {badge}
            </div>
            <div style="display:flex; gap:30px; margin-top:10px;">
                <div><strong>Timestamp:</strong> {latest['timestamp']}</div>
                <div><strong>Temperature:</strong> <span style="font-size:1.2rem; font-weight:700; color:{COLORS['critical']};">{latest['temperature']:.1f} °C</span></div>
                <div><strong>Humidity:</strong> <span style="font-size:1.2rem; font-weight:700; color:{COLORS['secondary']};">{latest['humidity']:.1f} %</span></div>
                <div><strong>Vibration:</strong> <span style="font-size:1.2rem; font-weight:700; color:{COLORS['info']};">{latest['vibration']:.2f} g</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if latest['sensor_status'] in ["Warning", "Critical"]:
            st.error(f"🚨 SENSOR EVENT WARNING: Reefer {latest['container_id']} logged abnormal condition at {latest['timestamp']}. Threshold breach recorded.")

        # If live simulation is running, execute safe delay and trigger rerun
        if st.session_state.sim_active and st.session_state.sim_step < len(container_history):
            time.sleep(update_interval)
            st.rerun()

    # 6 REQUIRED CHARTS (Section 8)
    st.markdown("---")
    st.subheader("📊 Reefer Container Environmental Telemetry Analysis")

    # Chart 1: Real-time-style temperature monitoring
    # Chart 2: Humidity trend
    r1_c1, r1_c2 = st.columns(2)
    view_data = pd.DataFrame(st.session_state.sim_buffer) if (st.session_state.sim_buffer and len(st.session_state.sim_buffer) > 2) else container_history.tail(40)
    
    with r1_c1:
        fig_temp = create_line_chart(view_data, "timestamp", "temperature", title=f"1. Real-Time Temperature Trajectory ({selected_container})", y_title="Temperature (°C)")
        st.plotly_chart(fig_temp, use_container_width=True)

    with r1_c2:
        fig_hum = create_line_chart(view_data, "timestamp", "humidity", title=f"2. Relative Humidity Saturation Trend ({selected_container})", y_title="Relative Humidity (%)")
        st.plotly_chart(fig_hum, use_container_width=True)

    # Chart 3: Vibration monitoring
    # Chart 4: Temperature vs humidity scatter plot
    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        fig_vibe = create_line_chart(view_data, "timestamp", "vibration", title=f"3. Chassis & Cargo Vibration Accelerometer ({selected_container})", y_title="Vibration (g-force RMS)")
        st.plotly_chart(fig_vibe, use_container_width=True)

    with r2_c2:
        sample_scatter = sensor_with_ml.sample(n=min(800, len(sensor_with_ml)), random_state=42)
        fig_scat = create_scatter_plot(sample_scatter, "temperature", "humidity", color_col="ml_anomaly_label", title="4. Temperature vs. Humidity (Isolation Forest Anomaly Tags)")
        st.plotly_chart(fig_scat, use_container_width=True)

    # Chart 5: Sensor readings by container
    # Chart 6: Abnormal event distribution
    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        cont_counts = sensor_df.groupby("container_id")["sensor_id"].count().reset_index().head(12)
        fig_cont_bar = create_bar_chart(cont_counts, "container_id", "sensor_id", title="5. Telemetry Ingestion Frequency Across Fleet Containers")
        st.plotly_chart(fig_cont_bar, use_container_width=True)

    with r3_c2:
        stat_colors = {"Normal": COLORS["info"], "Warning": COLORS["warning"], "Critical": COLORS["critical"]}
        fig_event_donut = create_donut_chart(sensor_df, "sensor_status", title="6. Telemetry Event Status Distribution", color_map=stat_colors)
        st.plotly_chart(fig_event_donut, use_container_width=True)

if __name__ == "__main__":
    render()
else:
    render()
