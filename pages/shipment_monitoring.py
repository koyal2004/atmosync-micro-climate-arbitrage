"""
AtmoSync - Page 2: Shipment Monitoring
Shipment Intelligence & Tracking: Detailed manifest exploration, live telemetry charts, and PyDeck GIS routing.
Features comprehensive search, multi-factor filtering, route mapping, and shipment-specific sensor telemetry.

All data is generated dynamically from the SQLite database.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database.database import load_table
from utils.helpers import render_kpi_card, format_currency, format_quantity, get_status_badge
from utils.charts import (
    create_line_chart, create_pydeck_route_map, create_donut_chart,
    create_scatter_plot, THEME_LAYOUT
)
from modules.risk_engine import calculate_shipment_risk
from modules.analytics import compute_shipment_performance_analytics
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL


def render():
    st.markdown(
        '<div class="disclaimer-banner"><strong>Demonstration Telemetry:</strong> '
        + PERSISTENT_DISCLAIMER
        + "</div>",
        unsafe_allow_html=True,
    )
    st.title("Shipment Intelligence & Tracking")
    st.caption(
        f"Active Freight In-Transit Visibility, Thermal Exposure & Dynamic Route Tracking • {DATASET_LABEL}"
    )

    # ------------------------------------------------------------------
    # Load Tables from Database
    # ------------------------------------------------------------------
    try:
        shipments_df = load_table("shipments")
        commodities_df = load_table("commodities")
        markets_df = load_table("markets")
        sensor_df = load_table("sensor_readings")
    except Exception as e:
        st.error(f"⚠️ Failed to load database tables: {e}")
        return

    if shipments_df.empty:
        st.warning("No shipment records available. Please generate synthetic data in Reports.")
        return

    # ------------------------------------------------------------------
    # Data Enrichment & Spoilage Risk Calculation
    # ------------------------------------------------------------------
    risk_df = calculate_shipment_risk(shipments_df, commodities_df, sensor_df)

    mkt_names = dict(zip(markets_df["market_id"], markets_df["market_name"]))
    comm_names = dict(zip(commodities_df["commodity_id"], commodities_df["commodity_name"]))

    display_df = shipments_df.copy()
    display_df["commodity"] = display_df["commodity_id"].map(comm_names).fillna("Unknown")
    display_df["source_market"] = display_df["source_market_id"].map(mkt_names).fillna("Origin")
    display_df["destination_market"] = display_df["destination_market_id"].map(mkt_names).fillna("Destination")

    if not risk_df.empty:
        risk_map = dict(zip(risk_df["shipment_id"], risk_df["risk_category"]))
        shelf_map = dict(zip(risk_df["shipment_id"], risk_df["estimated_remaining_shelf_life"]))
        display_df["risk_level"] = display_df["shipment_id"].map(risk_map).fillna("Low")
        # Ensure remaining shelf life reflects environmental risk calculation if available
        if "estimated_remaining_shelf_life" not in display_df.columns:
            display_df["estimated_remaining_shelf_life"] = display_df["shipment_id"].map(shelf_map).fillna(7.0)
    else:
        display_df["risk_level"] = "Low"

    # Date parsing for date filtering
    display_df["departure_date_dt"] = pd.to_datetime(display_df["departure_date"], errors="coerce")

    # ------------------------------------------------------------------
    # Summary KPIs
    # ------------------------------------------------------------------
    active_count = int(display_df["shipment_status"].isin(["In Transit", "At Risk", "Delayed"]).sum())
    delivered_count = int((display_df["shipment_status"] == "Delivered").sum())
    delayed_count = int((display_df["shipment_status"] == "Delayed").sum())
    at_risk_count = int((display_df["shipment_status"] == "At Risk").sum())
    avg_dist = float(display_df["distance_km"].mean()) if not display_df.empty else 0.0
    total_qty = float(display_df["quantity_kg"].sum()) if not display_df.empty else 0.0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(render_kpi_card("Active Shipments", f"{active_count:,}", "On highway", icon="🚚"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_kpi_card("Delivered", f"{delivered_count:,}", "Completed runs", icon="✅"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_kpi_card("Delayed", f"{delayed_count:,}", "Behind schedule", delta=f"{delayed_count} shipments", delta_color="negative" if delayed_count > 0 else "positive", icon="⏳"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_kpi_card("At-Risk Containers", f"{at_risk_count:,}", "Thermal stress", delta=f"{at_risk_count} consignments", delta_color="negative" if at_risk_count > 0 else "positive", icon="🚨"), unsafe_allow_html=True)
    with c5:
        st.markdown(render_kpi_card("Avg Distance", f"{avg_dist:.0f} km", "Corridor average", icon="📏"), unsafe_allow_html=True)
    with c6:
        st.markdown(render_kpi_card("Total Freight", format_quantity(total_qty), "Total hauled", icon="⚖️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Alert Box for Delayed and High-Risk Shipments
    # ------------------------------------------------------------------
    critical_consignments = display_df[display_df["shipment_status"].isin(["At Risk", "Delayed"])]
    if not critical_consignments.empty:
        with st.expander(f"⚠️ Action Required: {len(critical_consignments)} Delayed or High-Risk Consignments", expanded=False):
            st.markdown(
                f"The following {len(critical_consignments)} shipments have been identified as **Delayed** or **At Risk** "
                "due to environmental excursions or transit bottlenecks. Immediate rerouting or cold-chain inspection is advised."
            )
            st.dataframe(
                critical_consignments[[
                    "shipment_id", "container_id", "commodity", "source_market",
                    "destination_market", "shipment_status", "risk_level",
                    "estimated_remaining_shelf_life", "departure_date"
                ]].rename(columns={
                    "shipment_id": "Shipment ID",
                    "container_id": "Container ID",
                    "commodity": "Commodity",
                    "source_market": "Origin",
                    "destination_market": "Destination",
                    "shipment_status": "Status",
                    "risk_level": "Risk Tier",
                    "estimated_remaining_shelf_life": "Shelf Life (Days)",
                    "departure_date": "Departure"
                }),
                use_container_width=True,
                height=180
            )

    # ------------------------------------------------------------------
    # Fleet Shipment Performance Analytics
    # ------------------------------------------------------------------
    perf_metrics = compute_shipment_performance_analytics(display_df)
    with st.expander("📊 Fleet Logistics Performance Analytics (On-Time Rates & Unit Costs)", expanded=False):
        st.markdown("Detailed breakdown of fleet logistics health, delivery efficiency, and transit cost-per-ton-km.")
        pm1, pm2, pm3, pm4 = st.columns(4)
        with pm1:
            st.metric("Delivered Completion Rate", f"{perf_metrics['on_time_rate_pct']}%", delta="Historical completed")
        with pm2:
            st.metric("Corridor Delay Ratio", f"{perf_metrics['delay_rate_pct']}%", delta="Delayed runs", delta_color="inverse")
        with pm3:
            st.metric("Thermal Risk Incidence", f"{perf_metrics['at_risk_rate_pct']}%", delta="Cold-chain breach", delta_color="inverse")
        with pm4:
            st.metric("Avg Logistics Cost", f"₹{perf_metrics['avg_cost_per_ton_km']}/ton-km", delta="Freight unit cost")

        p_r1, p_r2 = st.columns(2)
        with p_r1:
            stat_colors = {"In Transit": COLORS["info"], "Delivered": COLORS["success"], "At Risk": COLORS["critical"], "Delayed": COLORS["warning"], "Completed": COLORS["primary"]}
            fig_perf_status = create_donut_chart(display_df, "shipment_status", title="Fleet Operational Status Distribution", color_map=stat_colors)
            st.plotly_chart(fig_perf_status, use_container_width=True)
        with p_r2:
            sample_sub = display_df.sample(n=min(300, len(display_df)), random_state=42) if len(display_df) > 0 else display_df
            fig_perf_scatter = create_scatter_plot(sample_sub, "distance_km", "transport_cost", color_col="shipment_status", title="Corridor Distance (km) vs. Transport Cost (₹)")
            st.plotly_chart(fig_perf_scatter, use_container_width=True)

    # ------------------------------------------------------------------
    # Search & Multi-Factor Filters
    # ------------------------------------------------------------------
    st.markdown("### 🔍 Search & Filter Shipments")
    f_col1, f_col2, f_col3, f_col4 = st.columns([1.8, 1.2, 1.0, 1.0])

    with f_col1:
        search_query = st.text_input(
            "Search Shipments",
            placeholder="Search by Shipment ID, Container ID, or Commodity Name...",
            key="shipment_search_query"
        )

    with f_col2:
        all_commodities = ["All"] + sorted(display_df["commodity"].dropna().unique().tolist())
        selected_commodity = st.selectbox("Commodity", all_commodities, index=0, key="shipment_comm_filter")

    with f_col3:
        all_statuses = ["All"] + sorted(display_df["shipment_status"].dropna().unique().tolist())
        status_filter = st.selectbox("Status", all_statuses, index=0, key="shipment_status_filter")

    with f_col4:
        all_risks = ["All", "Critical", "High", "Moderate", "Low"]
        risk_filter = st.selectbox("Risk Level", all_risks, index=0, key="shipment_risk_filter")

    # Date range filter row
    min_dep = display_df["departure_date_dt"].min()
    max_dep = display_df["departure_date_dt"].max()
    if pd.notna(min_dep) and pd.notna(max_dep):
        date_c1, _ = st.columns([1.5, 2.5])
        with date_c1:
            shipment_date_range = st.date_input(
                "Departure Date Range",
                value=(min_dep.date(), max_dep.date()),
                min_value=min_dep.date(),
                max_value=max_dep.date(),
                key="shipment_date_filter"
            )
    else:
        shipment_date_range = None

    # Apply all filters
    filtered_table = display_df.copy()

    if search_query:
        query = search_query.lower().strip()
        filtered_table = filtered_table[
            filtered_table["shipment_id"].str.lower().str.contains(query, na=False)
            | filtered_table["container_id"].str.lower().str.contains(query, na=False)
            | filtered_table["commodity"].astype(str).str.lower().str.contains(query, na=False)
            | filtered_table["source_market"].astype(str).str.lower().str.contains(query, na=False)
            | filtered_table["destination_market"].astype(str).str.lower().str.contains(query, na=False)
        ]

    if selected_commodity != "All":
        filtered_table = filtered_table[filtered_table["commodity"] == selected_commodity]

    if status_filter != "All":
        filtered_table = filtered_table[filtered_table["shipment_status"] == status_filter]

    if risk_filter != "All":
        filtered_table = filtered_table[filtered_table["risk_level"] == risk_filter]

    if shipment_date_range and len(shipment_date_range) == 2:
        start_d, end_d = shipment_date_range
        filtered_table = filtered_table[
            (filtered_table["departure_date_dt"].dt.date >= start_d)
            & (filtered_table["departure_date_dt"].dt.date <= end_d)
        ]

    # ------------------------------------------------------------------
    # Manifest Table Display
    # ------------------------------------------------------------------
    st.subheader(f"📋 Consignment Registry ({len(filtered_table):,} records found)")

    if filtered_table.empty:
        st.warning("⚠️ No shipments match your search and filter criteria. Please broaden your selection.")
        return

    # Complete Required Columns per Specification:
    # Shipment ID, Commodity, Source market, Destination market, Shipment date,
    # Quantity, Distance, Transport cost, Shipment status, Remaining shelf life
    table_view = filtered_table[[
        "shipment_id", "container_id", "commodity", "source_market",
        "destination_market", "departure_date", "expected_arrival_date",
        "quantity_kg", "distance_km", "transport_cost",
        "shipment_status", "estimated_remaining_shelf_life", "risk_level"
    ]].copy()

    table_view["quantity_kg"] = table_view["quantity_kg"].apply(lambda q: f"{q:,.0f} kg")
    table_view["distance_km"] = table_view["distance_km"].apply(lambda d: f"{d:.1f} km")
    table_view["transport_cost"] = table_view["transport_cost"].apply(lambda c: f"₹{c:,.2f}")
    table_view["estimated_remaining_shelf_life"] = table_view["estimated_remaining_shelf_life"].apply(lambda s: f"{s:.1f} days")

    table_display = table_view.rename(columns={
        "shipment_id": "Shipment ID",
        "container_id": "Container ID",
        "commodity": "Commodity",
        "source_market": "Source Market",
        "destination_market": "Destination Market",
        "departure_date": "Shipment Date",
        "expected_arrival_date": "Expected Arrival",
        "quantity_kg": "Quantity",
        "distance_km": "Distance",
        "transport_cost": "Transport Cost",
        "shipment_status": "Shipment Status",
        "estimated_remaining_shelf_life": "Remaining Shelf Life",
        "risk_level": "Risk Level"
    })

    st.dataframe(table_display, use_container_width=True, height=300)

    # ------------------------------------------------------------------
    # Detailed Shipment Inspection Pane
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔎 Individual Consignment Telemetry & Route Deep-Dive")

    available_ids = filtered_table["shipment_id"].tolist()
    selected_shipment_id = st.selectbox(
        "Select Shipment to Inspect Detailed Telemetry & Route:",
        options=available_ids,
        index=0,
        key="inspect_selected_shipment"
    )

    if selected_shipment_id:
        ship_row = display_df[display_df["shipment_id"] == selected_shipment_id].iloc[0]
        ship_risk = risk_df[risk_df["shipment_id"] == selected_shipment_id].iloc[0] if not risk_df.empty else None

        # Display Detailed Shipment Metadata
        st.markdown(f"#### Consignment Overview: `{ship_row['shipment_id']}` ({ship_row['commodity']})")
        info_c1, info_c2, info_c3 = st.columns(3)
        with info_c1:
            st.markdown(f"**Shipment ID:** `{ship_row['shipment_id']}`")
            st.markdown(f"**Container ID:** `{ship_row['container_id']}`")
            st.markdown(f"**Commodity:** {ship_row['commodity']}")
            st.markdown(f"**Freight Quantity:** {format_quantity(ship_row['quantity_kg'])}")
        with info_c2:
            st.markdown(f"**Source Market:** {ship_row['source_market']}")
            st.markdown(f"**Destination Market:** {ship_row['destination_market']}")
            st.markdown(f"**Corridor Distance:** {ship_row['distance_km']:.1f} km")
            st.markdown(f"**Transportation Cost:** {format_currency(ship_row['transport_cost'])}")
        with info_c3:
            st.markdown(f"**Status:** {get_status_badge(ship_row['shipment_status'])}", unsafe_allow_html=True)
            st.markdown(f"**Shipment Date:** {ship_row['departure_date']}")
            st.markdown(f"**Expected Arrival:** {ship_row['expected_arrival_date']}")
            if ship_risk is not None:
                st.markdown(f"**Remaining Shelf Life:** `{ship_risk['estimated_remaining_shelf_life']} days`")
                st.markdown(f"**Estimated Quality:** `{ship_risk['estimated_quality']}%` (Initial: {ship_risk['initial_quality']}%)")
            else:
                st.markdown(f"**Remaining Shelf Life:** `{ship_row.get('estimated_remaining_shelf_life', 7.0):.1f} days`")

        st.markdown("<br>", unsafe_allow_html=True)

        # ------------------------------------------------------------------
        # Geospatial Route Visualization
        # ------------------------------------------------------------------
        st.markdown("#### 🗺️ Geospatial Highway Routing & Nodes")
        mkt_geo = markets_df.set_index("market_id").to_dict(orient="index")
        src_geo = mkt_geo.get(ship_row["source_market_id"], {"latitude": 13.0827, "longitude": 80.2707, "market_name": "Origin"})
        dst_geo = mkt_geo.get(ship_row["destination_market_id"], {"latitude": 12.9716, "longitude": 77.5946, "market_name": "Destination"})

        deck = create_pydeck_route_map(
            source_lat=src_geo["latitude"], source_lon=src_geo["longitude"],
            dest_lat=dst_geo["latitude"], dest_lon=dst_geo["longitude"],
            source_name=src_geo["market_name"], dest_name=dst_geo["market_name"]
        )
        st.pydeck_chart(deck)

        # ------------------------------------------------------------------
        # Shipment-Specific Sensor Telemetry (Temperature, Humidity, Vibration)
        # ------------------------------------------------------------------
        st.markdown("#### 📈 Reefer Chamber Sensor Telemetry (Simulated Data)")
        st.caption("⚠️ All sensor readings below represent simulated IoT telemetry packets for academic demonstration.")

        ship_sensors = sensor_df[sensor_df["shipment_id"] == selected_shipment_id].sort_values("timestamp")

        if not ship_sensors.empty:
            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                fig_t = create_line_chart(
                    ship_sensors, "timestamp", "temperature",
                    title=f"Temperature Profile (°C) – {ship_row['container_id']}",
                    y_title="Temperature (°C)"
                )
                st.plotly_chart(fig_t, use_container_width=True)

            with tc2:
                fig_h = create_line_chart(
                    ship_sensors, "timestamp", "humidity",
                    title=f"Relative Humidity (%) – {ship_row['container_id']}",
                    y_title="Relative Humidity (%)"
                )
                st.plotly_chart(fig_h, use_container_width=True)

            with tc3:
                fig_v = create_line_chart(
                    ship_sensors, "timestamp", "vibration",
                    title=f"Vibration Acceleration (g) – {ship_row['container_id']}",
                    y_title="Vibration (g-force)"
                )
                st.plotly_chart(fig_v, use_container_width=True)

            with st.expander(f"📄 View Raw Sensor Reading Records ({len(ship_sensors)} records)"):
                st.dataframe(
                    ship_sensors[[
                        "sensor_id", "container_id", "timestamp",
                        "temperature", "humidity", "vibration", "sensor_status"
                    ]],
                    use_container_width=True
                )
        else:
            st.info(f"No sensor telemetry records found for Shipment `{selected_shipment_id}`.")


if __name__ == "__main__":
    render()
else:
    render()
