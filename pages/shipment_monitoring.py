"""
AtmoSync - Page 2: Shipment Monitoring
Shipment Intelligence & Tracking: Detailed manifest exploration, live telemetry charts, and PyDeck GIS routing.
"""

import streamlit as st
import pandas as pd
from database.database import load_table
from utils.helpers import render_kpi_card, format_currency, format_quantity, get_status_badge
from utils.charts import create_line_chart, create_pydeck_route_map
from modules.risk_engine import calculate_shipment_risk
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Demonstration Telemetry:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)
    st.title("Shipment Intelligence & Tracking")
    st.caption("Active Freight In-Transit Visibility, Thermal Exposure & Dynamic Route Tracking")

    shipments_df = load_table("shipments")
    commodities_df = load_table("commodities")
    markets_df = load_table("markets")
    sensor_df = load_table("sensor_readings")

    if shipments_df.empty:
        st.warning("No shipment records available.")
        return

    # Calculate risk scores for all shipments
    risk_df = calculate_shipment_risk(shipments_df, commodities_df, sensor_df)

    # Merge descriptive names
    mkt_names = dict(zip(markets_df["market_id"], markets_df["market_name"]))
    comm_names = dict(zip(commodities_df["commodity_id"], commodities_df["commodity_name"]))

    display_df = shipments_df.copy()
    display_df["commodity"] = display_df["commodity_id"].map(comm_names)
    display_df["source_market"] = display_df["source_market_id"].map(mkt_names)
    display_df["destination_market"] = display_df["destination_market_id"].map(mkt_names)

    # Merge risk category
    if not risk_df.empty:
        risk_map = dict(zip(risk_df["shipment_id"], risk_df["risk_category"]))
        display_df["risk_level"] = display_df["shipment_id"].map(risk_map).fillna("Low")
    else:
        display_df["risk_level"] = "Low"

    # KPIs per Section 7
    active_count = int(display_df["shipment_status"].isin(["In Transit", "At Risk", "Delayed"]).sum())
    delivered_count = int((display_df["shipment_status"] == "Delivered").sum())
    delayed_count = int((display_df["shipment_status"] == "Delayed").sum())
    at_risk_count = int((display_df["shipment_status"] == "At Risk").sum())
    avg_dist = float(display_df["distance_km"].mean())
    total_qty = float(display_df["quantity_kg"].sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(render_kpi_card("Active Shipments", f"{active_count:,}", "On highway", icon="🚚"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_kpi_card("Delivered", f"{delivered_count:,}", "Completed runs", icon="✅"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_kpi_card("Delayed", f"{delayed_count:,}", "Behind schedule", icon="⏳"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_kpi_card("At-Risk Containers", f"{at_risk_count:,}", "Action required", delta=f"{at_risk_count} consignments", delta_color="negative", icon="🚨"), unsafe_allow_html=True)
    with c5:
        st.markdown(render_kpi_card("Avg Distance", f"{avg_dist:.0f} km", "Corridor average", icon="📏"), unsafe_allow_html=True)
    with c6:
        st.markdown(render_kpi_card("Total Freight", format_quantity(total_qty), "Total hauled", icon="⚖️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Search & Filter Controls
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_query = st.text_input("🔍 Search by Shipment ID, Container ID, or Commodity", placeholder="e.g. SHP-0010, Hass, CONT-1002")
    with f_col2:
        status_filter = st.selectbox("Status Filter", ["All"] + sorted(display_df["shipment_status"].unique().tolist()))
    with f_col3:
        risk_filter = st.selectbox("Risk Level Filter", ["All", "Critical", "High", "Moderate", "Low"])

    filtered_table = display_df.copy()
    if search_query:
        query = search_query.lower()
        filtered_table = filtered_table[
            filtered_table["shipment_id"].str.lower().str.contains(query) |
            filtered_table["container_id"].str.lower().str.contains(query) |
            filtered_table["commodity"].astype(str).str.lower().str.contains(query)
        ]
    if status_filter != "All":
        filtered_table = filtered_table[filtered_table["shipment_status"] == status_filter]
    if risk_filter != "All":
        filtered_table = filtered_table[filtered_table["risk_level"] == risk_filter]

    st.subheader(f"📋 Consignment Registry ({len(filtered_table):,} records)")

    # Columns per Section 7
    table_view = filtered_table[[
        "shipment_id", "container_id", "commodity", "source_market", 
        "destination_market", "quantity_kg", "departure_date", 
        "expected_arrival_date", "shipment_status", "risk_level"
    ]].rename(columns={
        "shipment_id": "Shipment ID",
        "container_id": "Container ID",
        "commodity": "Commodity",
        "source_market": "Source Market",
        "destination_market": "Destination Market",
        "quantity_kg": "Quantity (kg)",
        "departure_date": "Departure Date",
        "expected_arrival_date": "Expected Arrival",
        "shipment_status": "Shipment Status",
        "risk_level": "Risk Level"
    })

    st.dataframe(table_view, use_container_width=True, height=280)

    # Detailed Inspection Pane
    st.markdown("---")
    st.subheader("🔎 Individual Consignment Telemetry & Route Deep-Dive")
    
    selected_shipment_id = st.selectbox(
        "Select Shipment to Inspect Detailed Telemetry & Route:",
        options=filtered_table["shipment_id"].tolist() if not filtered_table.empty else display_df["shipment_id"].head(20).tolist()
    )

    if selected_shipment_id:
        ship_row = display_df[display_df["shipment_id"] == selected_shipment_id].iloc[0]
        ship_risk = risk_df[risk_df["shipment_id"] == selected_shipment_id].iloc[0] if not risk_df.empty else None

        # Display Shipment & Commodity information
        info_c1, info_c2, info_c3 = st.columns(3)
        with info_c1:
            st.markdown(f"**Shipment ID:** `{ship_row['shipment_id']}`")
            st.markdown(f"**Container ID:** `{ship_row['container_id']}`")
            st.markdown(f"**Commodity:** {ship_row['commodity']}")
            st.markdown(f"**Quantity:** {format_quantity(ship_row['quantity_kg'])}")
        with info_c2:
            st.markdown(f"**Source Market:** {ship_row['source_market']}")
            st.markdown(f"**Destination Market:** {ship_row['destination_market']}")
            st.markdown(f"**Corridor Distance:** {ship_row['distance_km']:.1f} km")
            st.markdown(f"**Transportation Cost:** {format_currency(ship_row['transport_cost'])}")
        with info_c3:
            st.markdown(f"**Status:** {get_status_badge(ship_row['shipment_status'])}", unsafe_allow_html=True)
            st.markdown(f"**Departure:** {ship_row['departure_date']}")
            st.markdown(f"**Estimated Arrival:** {ship_row['expected_arrival_date']}")
            if ship_risk is not None:
                st.markdown(f"**Remaining Shelf Life:** `{ship_risk['estimated_remaining_shelf_life']} days`")
                st.markdown(f"**Estimated Quality:** `{ship_risk['estimated_quality']}%` (Initial: {ship_risk['initial_quality']}%)")

        st.markdown("<br>", unsafe_allow_html=True)

        # PyDeck Route Visualization
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

        # Sensor History & Trends for this shipment
        st.markdown("#### 📈 Reefer Chamber Sensor History")
        ship_sensors = sensor_df[sensor_df["shipment_id"] == selected_shipment_id].sort_values("timestamp")
        
        if not ship_sensors.empty:
            tc1, tc2 = st.columns(2)
            with tc1:
                fig_t = create_line_chart(ship_sensors, "timestamp", "temperature", title=f"Container {ship_row['container_id']} Temperature Profile (°C)", y_title="Temperature (°C)")
                st.plotly_chart(fig_t, use_container_width=True)
            with tc2:
                fig_h = create_line_chart(ship_sensors, "timestamp", "humidity", title=f"Container {ship_row['container_id']} Humidity Profile (%)", y_title="Relative Humidity (%)")
                st.plotly_chart(fig_h, use_container_width=True)

            with st.expander("📄 View Raw Sensor Reading Records"):
                st.dataframe(ship_sensors, use_container_width=True)
        else:
            st.info("No recorded sensor time-series for this specific shipment.")

if __name__ == "__main__":
    render()
else:
    render()
