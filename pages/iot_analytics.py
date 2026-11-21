"""
AtmoSync - Page 3: IoT Sensor Analytics
Live Container Sensor Intelligence: Streaming telemetry simulation, environmental anomalies,
reefer condition monitoring, and shipment-wise sensor analysis.

All sensor telemetry displayed represents simulated demonstration data, not live hardware.
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
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL


def render():
    st.markdown(
        '<div class="disclaimer-banner"><strong>Simulated IoT Streaming – Not Connected to Physical Sensors:</strong> '
        + PERSISTENT_DISCLAIMER
        + "</div>",
        unsafe_allow_html=True,
    )
    st.title("Live Container Sensor Intelligence")
    st.caption(
        f"Container Micro-Climate Ingestion, Thermal Dynamics, Vibration Sensors & Telemetry Analysis • {DATASET_LABEL}"
    )

    # ------------------------------------------------------------------
    # Load Tables from Database
    # ------------------------------------------------------------------
    try:
        sensor_df = load_table("sensor_readings")
        shipments_df = load_table("shipments")
        commodities_df = load_table("commodities")
    except Exception as e:
        st.error(f"⚠️ Failed to load database tables: {e}")
        return

    if sensor_df.empty:
        st.warning("Sensor dataset is empty. Please generate synthetic data in Reports & Data Management.")
        return

    # Merge commodity information into shipments for richer context
    comm_names = dict(zip(commodities_df["commodity_id"], commodities_df["commodity_name"]))
    ship_comm_map = dict(zip(shipments_df["shipment_id"], shipments_df["commodity_id"].map(comm_names)))
    sensor_df["commodity"] = sensor_df["shipment_id"].map(ship_comm_map).fillna("Agricultural Freight")
    sensor_df["timestamp_dt"] = pd.to_datetime(sensor_df["timestamp"], errors="coerce")

    # ------------------------------------------------------------------
    # Machine Learning Anomaly Detection (Isolation Forest)
    # ------------------------------------------------------------------
    sensor_with_ml, anomaly_summary = run_sensor_anomaly_detection(sensor_df)

    # ------------------------------------------------------------------
    # Global Filters: Shipment, Status, and Date Range
    # ------------------------------------------------------------------
    st.markdown("### 🎛️ Telemetry Filters & Shipment Association")
    f1, f2, f3 = st.columns([1.5, 1.2, 1.3])

    with f1:
        all_shipments = ["All Shipments"] + sorted(sensor_df["shipment_id"].dropna().unique().tolist())
        selected_shipment = st.selectbox("Filter by Shipment ID", all_shipments, index=0, key="iot_shipment_filter")

    with f2:
        status_options = ["All Statuses", "Normal", "Warning", "Critical"]
        selected_sensor_status = st.selectbox("Sensor Status Filter", status_options, index=0, key="iot_status_filter")

    with f3:
        min_ts = sensor_df["timestamp_dt"].min()
        max_ts = sensor_df["timestamp_dt"].max()
        if pd.notna(min_ts) and pd.notna(max_ts):
            sensor_date_range = st.date_input(
                "Telemetry Date Range",
                value=(min_ts.date(), max_ts.date()),
                min_value=min_ts.date(),
                max_value=max_ts.date(),
                key="iot_date_range"
            )
        else:
            sensor_date_range = None

    # Apply filters
    filtered_sensors = sensor_with_ml.copy()
    if selected_shipment != "All Shipments":
        filtered_sensors = filtered_sensors[filtered_sensors["shipment_id"] == selected_shipment]

    if selected_sensor_status != "All Statuses":
        filtered_sensors = filtered_sensors[filtered_sensors["sensor_status"] == selected_sensor_status]

    if sensor_date_range and len(sensor_date_range) == 2:
        start_d, end_d = sensor_date_range
        filtered_sensors = filtered_sensors[
            (filtered_sensors["timestamp_dt"].dt.date >= start_d)
            & (filtered_sensors["timestamp_dt"].dt.date <= end_d)
        ]

    # ------------------------------------------------------------------
    # Sensor KPIs (Computed dynamically from filtered records)
    # ------------------------------------------------------------------
    if not filtered_sensors.empty:
        avg_temp = float(filtered_sensors["temperature"].mean())
        max_temp = float(filtered_sensors["temperature"].max())
        avg_hum = float(filtered_sensors["humidity"].mean())
        max_hum = float(filtered_sensors["humidity"].max())
        avg_vibe = float(filtered_sensors["vibration"].mean())
        abnormal_count = int(filtered_sensors["sensor_status"].isin(["Warning", "Critical"]).sum())
        ml_anomalies_count = int((filtered_sensors["ml_anomaly_label"] == "Anomaly").sum())
        active_containers = filtered_sensors["container_id"].nunique()
    else:
        avg_temp, max_temp, avg_hum, max_hum, avg_vibe = 0.0, 0.0, 0.0, 0.0, 0.0
        abnormal_count, ml_anomalies_count, active_containers = 0, 0, 0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(render_kpi_card("Avg Temp", f"{avg_temp:.1f} °C", "Chamber average", icon="🌡️"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Max Temp", f"{max_temp:.1f} °C", "Peak thermal exposure", delta=f"{max_temp - avg_temp:+.1f}°C spike" if max_temp > avg_temp else "Stable", delta_color="negative" if max_temp > 25.0 else "positive", icon="🔥"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Avg Humidity", f"{avg_hum:.1f} %", "RH setpoint", icon="💧"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Avg Vibration", f"{avg_vibe:.2f} g", "RMS g-force axis", icon="📳"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Abnormal Readings", f"{abnormal_count:,}", f"{ml_anomalies_count} ML Anomalies", delta=f"{(abnormal_count / max(1, len(filtered_sensors))) * 100:.1f}% breach rate", delta_color="negative" if abnormal_count > 0 else "positive", icon="⚠️"), unsafe_allow_html=True)
    with k6:
        st.markdown(render_kpi_card("Active Reefers", f"{active_containers:,}", "Monitored containers", icon="📡"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Abnormal Readings Alert Callout
    # ------------------------------------------------------------------
    if abnormal_count > 0:
        abnormal_df = filtered_sensors[filtered_sensors["sensor_status"].isin(["Warning", "Critical"])].sort_values("timestamp", ascending=False)
        with st.expander(f"🚨 Abnormal Reading Identification: {abnormal_count} Excursions Flagged", expanded=False):
            st.markdown(
                "The table below isolates sensor packets that exceeded safe temperature or humidity envelopes "
                "or exhibited abnormal vibration spikes. All data is labeled as simulated."
            )
            st.dataframe(
                abnormal_df[[
                    "sensor_id", "shipment_id", "container_id", "commodity",
                    "timestamp", "temperature", "humidity", "vibration",
                    "sensor_status", "ml_anomaly_label"
                ]].rename(columns={
                    "sensor_id": "Sensor ID",
                    "shipment_id": "Shipment ID",
                    "container_id": "Container ID",
                    "commodity": "Cargo Commodity",
                    "timestamp": "Timestamp",
                    "temperature": "Temp (°C)",
                    "humidity": "Humidity (%)",
                    "vibration": "Vibration (g)",
                    "sensor_status": "Threshold Status",
                    "ml_anomaly_label": "ML Flag"
                }),
                use_container_width=True,
                height=200
            )

    # ------------------------------------------------------------------
    # STREAMING SIMULATION CONTROL PANEL (Controlled Simulation)
    # ------------------------------------------------------------------
    st.subheader("⚡ Live Sensor Telemetry Stream Replay Engine")
    st.caption("ℹ️ Controlled simulation player: Replays stored synthetic sensor packets sequentially to demonstrate real-time ingestion.")

    if "sim_active" not in st.session_state:
        st.session_state.sim_active = False
    if "sim_step" not in st.session_state:
        st.session_state.sim_step = 0
    if "sim_buffer" not in st.session_state:
        st.session_state.sim_buffer = []

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.5, 1.5, 1.2, 1.2])

    with ctrl_col1:
        container_list = sorted(sensor_df["container_id"].dropna().unique().tolist())
        selected_container = st.selectbox("Target Reefer Container:", container_list, index=0, key="sim_container_choice")
    with ctrl_col2:
        update_interval = st.selectbox("Replay Tick Interval:", [1, 2, 3, 5], index=1, format_func=lambda x: f"{x} second{'s' if x > 1 else ''} per cycle", key="sim_speed_choice")

    with ctrl_col3:
        st.write("")
        st.write("")
        if not st.session_state.sim_active:
            if st.button("▶️ Start Stream", use_container_width=True, type="primary", key="btn_start_sim"):
                st.session_state.sim_active = True
                st.session_state.sim_step = 0
                st.session_state.sim_buffer = []
                st.rerun()
        else:
            if st.button("⏸️ Pause Stream", use_container_width=True, key="btn_pause_sim"):
                st.session_state.sim_active = False
                st.rerun()

    with ctrl_col4:
        st.write("")
        st.write("")
        if st.button("⏹️ Reset Stream", use_container_width=True, key="btn_reset_sim"):
            st.session_state.sim_active = False
            st.session_state.sim_step = 0
            st.session_state.sim_buffer = []
            st.rerun()

    container_history = sensor_df[sensor_df["container_id"] == selected_container].sort_values("timestamp").reset_index(drop=True)

    if st.session_state.sim_active:
        st.info(f"🟢 **Live Telemetry Replay Ingestion Active** for Container `{selected_container}`. Ticking every {update_interval}s.")
        step = st.session_state.sim_step
        total_steps = len(container_history)

        if step < total_steps:
            current_reading = container_history.iloc[step].to_dict()
            st.session_state.sim_buffer.append(current_reading)
            st.session_state.sim_step += 1
        else:
            st.success("Replay sequence finished for selected container manifest. Looping back.")
            st.session_state.sim_step = 0

    if st.session_state.sim_buffer:
        latest = st.session_state.sim_buffer[-1]
        badge = get_status_badge(latest["sensor_status"])
        st.markdown(f"""
        <div style="background:#FFFFFF; border:2px solid {COLORS['secondary']}; border-radius:10px; padding:15px; margin-bottom:15px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:1.05rem; font-weight:700; color:{COLORS['primary']};">
                    Telemetry Stream Ingested Packet: <code>{latest['sensor_id']}</code> (Shipment: <code>{latest['shipment_id']}</code>)
                </span>
                {badge}
            </div>
            <div style="display:flex; gap:35px; margin-top:10px; flex-wrap:wrap;">
                <div><strong>Timestamp:</strong> {latest['timestamp']}</div>
                <div><strong>Temperature:</strong> <span style="font-size:1.15rem; font-weight:700; color:{COLORS['critical']};">{latest['temperature']:.1f} °C</span></div>
                <div><strong>Humidity:</strong> <span style="font-size:1.15rem; font-weight:700; color:{COLORS['secondary']};">{latest['humidity']:.1f} %</span></div>
                <div><strong>Vibration:</strong> <span style="font-size:1.15rem; font-weight:700; color:{COLORS['info']};">{latest['vibration']:.2f} g</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if latest["sensor_status"] in ["Warning", "Critical"]:
            st.error(f"🚨 EXCURSION DETECTED: Reefer {latest['container_id']} logged status '{latest['sensor_status']}' at {latest['timestamp']}.")

        if st.session_state.sim_active and st.session_state.sim_step < len(container_history):
            time.sleep(update_interval)
            st.rerun()

    # ------------------------------------------------------------------
    # Required Visualizations:
    # 1. Temperature Trend Chart
    # 2. Humidity Trend Chart
    # 3. Vibration Trend Chart
    # 4. Temperature vs. Humidity Scatter (ML Anomaly Tags)
    # 5. Sensor Readings by Container
    # 6. Status Breakdown Donut
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 Telemetry Trend Visualizations & Multivariate Analysis")

    view_data = (
        pd.DataFrame(st.session_state.sim_buffer)
        if (st.session_state.sim_buffer and len(st.session_state.sim_buffer) > 2)
        else (filtered_sensors.tail(50) if not filtered_sensors.empty else container_history.tail(40))
    )

    # Row 1: Temperature & Humidity Trend Charts
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        fig_temp = create_line_chart(
            view_data, "timestamp", "temperature",
            title=f"1. Temperature Trend Profile (°C)",
            y_title="Temperature (°C)"
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with r1_c2:
        fig_hum = create_line_chart(
            view_data, "timestamp", "humidity",
            title=f"2. Relative Humidity Saturation Trend (%)",
            y_title="Relative Humidity (%)"
        )
        st.plotly_chart(fig_hum, use_container_width=True)

    # Row 2: Vibration Trend Chart & Multivariate Scatter Plot
    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        fig_vibe = create_line_chart(
            view_data, "timestamp", "vibration",
            title=f"3. Vibration Trend Accelerometer (g-force)",
            y_title="Vibration (g)"
        )
        st.plotly_chart(fig_vibe, use_container_width=True)

    with r2_c2:
        scatter_sample = filtered_sensors.sample(n=min(600, len(filtered_sensors)), random_state=42) if not filtered_sensors.empty else pd.DataFrame()
        if not scatter_sample.empty:
            fig_scat = create_scatter_plot(
                scatter_sample, "temperature", "humidity",
                color_col="ml_anomaly_label",
                title="4. Temperature vs. Humidity (Isolation Forest Anomaly Labels)"
            )
            st.plotly_chart(fig_scat, use_container_width=True)
        else:
            st.info("No data for multivariate scatter plot.")

    # Row 3: Shipment-wise Sensor Analysis & Status Breakdown
    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        # Shipment-wise sensor readings count
        ship_counts = (
            filtered_sensors.groupby("shipment_id")["sensor_id"]
            .count()
            .reset_index()
            .sort_values("sensor_id", ascending=False)
            .head(10)
        )
        fig_ship_bar = create_bar_chart(
            ship_counts, "shipment_id", "sensor_id",
            title="5. Top Shipments by Sensor Telemetry Volume"
        )
        st.plotly_chart(fig_ship_bar, use_container_width=True)

    with r3_c2:
        stat_colors = {
            "Normal": COLORS["info"],
            "Warning": COLORS["warning"],
            "Critical": COLORS["critical"]
        }
        fig_status_donut = create_donut_chart(
            filtered_sensors if not filtered_sensors.empty else sensor_df,
            "sensor_status",
            title="6. Sensor Status Distribution (Threshold Compliance)",
            color_map=stat_colors
        )
        st.plotly_chart(fig_status_donut, use_container_width=True)

    # ------------------------------------------------------------------
    # Shipment-Wise Detailed Sensor Telemetry Manifest
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📑 Raw IoT Telemetry Log & Manifest Inspection")
    st.caption("All records below are synthetic telemetry packets associated with simulated shipments.")

    display_cols = [
        "sensor_id", "shipment_id", "container_id", "commodity",
        "timestamp", "temperature", "humidity", "vibration",
        "sensor_status", "ml_anomaly_label"
    ]
    st.dataframe(
        filtered_sensors[display_cols].rename(columns={
            "sensor_id": "Sensor ID",
            "shipment_id": "Shipment ID",
            "container_id": "Container ID",
            "commodity": "Commodity",
            "timestamp": "Timestamp",
            "temperature": "Temp (°C)",
            "humidity": "Humidity (%)",
            "vibration": "Vibration (g)",
            "sensor_status": "Status",
            "ml_anomaly_label": "Anomaly Flag"
        }),
        use_container_width=True,
        height=260
    )


if __name__ == "__main__":
    render()
else:
    render()
