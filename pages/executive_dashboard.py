"""
AtmoSync - Page 1: Executive Dashboard
Executive overview of agricultural supply chain operations, fleet status, and market signals.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database.database import load_table
from utils.helpers import render_kpi_card, format_currency, format_quantity
from utils.charts import (
    create_donut_chart, create_line_chart, create_bar_chart,
    create_dual_axis_chart, create_state_market_map
)
from modules.risk_engine import calculate_shipment_risk, get_risk_summary
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Academic Research Mode:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)

    st.title("AtmoSync – Executive Overview")
    st.caption(f"Agricultural Supply Chain Telemetry & Market Arbitrage Intelligence • {DATASET_LABEL}")

    # Load data from database (cached in session state)
    shipments_df = load_table("shipments")
    commodities_df = load_table("commodities")
    markets_df = load_table("markets")
    sensor_df = load_table("sensor_readings")
    prices_df = load_table("market_prices")
    arb_df = load_table("arbitrage_opportunities")

    if shipments_df.empty:
        st.warning("Database contains no records. Please generate synthetic data in Reports & Data Management.")
        return

    # Sidebar / Top Global Filters
    st.sidebar.markdown("### 🎛️ Executive Filters")
    
    # State filter
    all_states = ["All"] + sorted(markets_df["state"].unique().tolist())
    selected_state = st.sidebar.selectbox("Filter by State", all_states, index=0)

    # Commodity Category filter
    all_cats = ["All"] + sorted(commodities_df["category"].unique().tolist())
    selected_cat = st.sidebar.selectbox("Commodity Category", all_cats, index=0)

    # Status filter
    all_statuses = ["All"] + sorted(shipments_df["shipment_status"].unique().tolist())
    selected_status = st.sidebar.selectbox("Shipment Status", all_statuses, index=0)

    # Filter shipments based on selections
    filtered_ships = shipments_df.copy()
    if selected_status != "All":
        filtered_ships = filtered_ships[filtered_ships["shipment_status"] == selected_status]

    if selected_state != "All":
        valid_mkts = markets_df[markets_df["state"] == selected_state]["market_id"].tolist()
        filtered_ships = filtered_ships[
            filtered_ships["source_market_id"].isin(valid_mkts) | 
            filtered_ships["destination_market_id"].isin(valid_mkts)
        ]

    if selected_cat != "All":
        valid_comms = commodities_df[commodities_df["category"] == selected_cat]["commodity_id"].tolist()
        filtered_ships = filtered_ships[filtered_ships["commodity_id"].isin(valid_comms)]

    # Compute Executive KPIs
    total_ships = len(filtered_ships)
    in_transit_ships = int((filtered_ships["shipment_status"] == "In Transit").sum())
    at_risk_ships = int((filtered_ships["shipment_status"] == "At Risk").sum())
    total_comms = commodities_df["commodity_id"].nunique()
    total_mkts = markets_df["market_id"].nunique()

    # Environmental sensor KPIs
    if not sensor_df.empty:
        # Link to filtered shipments
        filtered_sensors = sensor_df[sensor_df["shipment_id"].isin(filtered_ships["shipment_id"])]
        if filtered_sensors.empty:
            filtered_sensors = sensor_df
        avg_temp = float(filtered_sensors["temperature"].mean())
        avg_hum = float(filtered_sensors["humidity"].mean())
    else:
        avg_temp, avg_hum = 0.0, 0.0

    # Arbitrage Opportunities count
    total_opps = len(arb_df[arb_df["recommendation_status"].isin(["High Opportunity", "Moderate Opportunity"])])

    # Render KPI Cards (8 KPI Metrics per Section 6)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(render_kpi_card("Total Shipments", f"{total_ships:,}", "Active & Historical", icon="📦"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_kpi_card("In Transit", f"{in_transit_ships:,}", "Active on highway", delta=f"{(in_transit_ships/max(1, total_ships))*100:.1f}% fleet", delta_color="positive", icon="🚚"), unsafe_allow_html=True)
    with c3:
        st.markdown(render_kpi_card("At-Risk Shipments", f"{at_risk_ships:,}", "Thermal stress flagged", delta=f"{at_risk_ships} critical consignments", delta_color="negative" if at_risk_ships > 0 else "positive", icon="⚠️"), unsafe_allow_html=True)
    with c4:
        st.markdown(render_kpi_card("Potential Arbitrage", f"{total_opps:,}", "Profitable rerouting leads", delta="Actionable", delta_color="positive", icon="💡"), unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(render_kpi_card("Tracked Commodities", f"{total_comms:,}", "15 core agro items", icon="🌾"), unsafe_allow_html=True)
    with c6:
        st.markdown(render_kpi_card("Trading APMC Markets", f"{total_mkts:,}", "Across 10 Indian states", icon="🏛️"), unsafe_allow_html=True)
    with c7:
        st.markdown(render_kpi_card("Avg Container Temp", f"{avg_temp:.1f} °C", "Nominal setpoint", icon="🌡️"), unsafe_allow_html=True)
    with c8:
        st.markdown(render_kpi_card("Avg Relative Humidity", f"{avg_hum:.1f} %", "Reefer chamber average", icon="💧"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 8 Required Charts (Section 6)
    # Row 1: Shipment status donut & Daily shipment activity line
    st.subheader("📊 Consignment Distribution & Highway Activity")
    r1_col1, r1_col2 = st.columns([1, 1])

    with r1_col1:
        status_colors = {
            "In Transit": COLORS["info"], "Delivered": COLORS["success"],
            "Completed": COLORS["primary"], "At Risk": COLORS["critical"], "Delayed": COLORS["warning"]
        }
        fig_donut = create_donut_chart(filtered_ships, "shipment_status", title="1. Consignment Status Breakdown", color_map=status_colors)
        st.plotly_chart(fig_donut, use_container_width=True)

    with r1_col2:
        activity_df = filtered_ships.groupby("departure_date")["shipment_id"].count().reset_index()
        activity_df = activity_df.rename(columns={"shipment_id": "shipments_departed"}).sort_values("departure_date")
        fig_line = create_line_chart(activity_df, "departure_date", "shipments_departed", title="2. Daily Shipment Dispatch Activity", y_title="Dispatched Volume")
        st.plotly_chart(fig_line, use_container_width=True)

    # Row 2: Commodity distribution bar & Temp/Humidity trend
    st.subheader("🌾 Commodity Volume & Reefer Environmental Telemetry")
    r2_col1, r2_col2 = st.columns([1, 1])

    with r2_col1:
        # Merge commodity name
        merged_ships = filtered_ships.merge(commodities_df[["commodity_id", "category"]], on="commodity_id", how="left")
        comm_dist = merged_ships.groupby("category")["quantity_kg"].sum().reset_index()
        comm_dist["quantity_MT"] = comm_dist["quantity_kg"] / 1000.0
        fig_comm_bar = create_bar_chart(comm_dist, "category", "quantity_MT", title="3. Commodity Category Shipment Volume (MT)", orientation="v")
        st.plotly_chart(fig_comm_bar, use_container_width=True)

    with r2_col2:
        sensor_daily = sensor_df.copy()
        sensor_daily["date"] = pd.to_datetime(sensor_daily["timestamp"]).dt.strftime("%Y-%m-%d")
        daily_telemetry = sensor_daily.groupby("date").agg({"temperature": "mean", "humidity": "mean"}).reset_index().sort_values("date").tail(30)
        fig_dual = create_dual_axis_chart(daily_telemetry, "date", "temperature", "humidity", "Avg Temp (°C)", "Avg Humidity (%)", "4. Reefer Temperature & Humidity Multi-Week Trend")
        st.plotly_chart(fig_dual, use_container_width=True)

    # Row 3: Market-wise avg price & Spoilage risk distribution
    st.subheader("📈 Mandi Market Pricing & Spoilage Exposure Profiles")
    r3_col1, r3_col2 = st.columns([1, 1])

    with r3_col1:
        top_mkt_prices = prices_df.groupby("market_id")["modal_price"].mean().reset_index()
        top_mkt_prices = top_mkt_prices.merge(markets_df[["market_id", "market_name", "state"]], on="market_id", how="left")
        top_10_mkt = top_mkt_prices.sort_values("modal_price", ascending=False).head(10)
        fig_mkt_p = create_bar_chart(top_10_mkt, "market_name", "modal_price", color_col="state", title="5. Top Mandis by Average Commodity Modal Price (₹/kg)")
        st.plotly_chart(fig_mkt_p, use_container_width=True)

    with r3_col2:
        risk_df = calculate_shipment_risk(filtered_ships, commodities_df, sensor_df)
        risk_color_map = {"Low": COLORS["success"], "Moderate": COLORS["info"], "High": COLORS["warning"], "Critical": COLORS["critical"]}
        fig_risk_donut = create_donut_chart(risk_df, "risk_category", title="6. Spoilage Exposure Risk Category Distribution", color_map=risk_color_map)
        st.plotly_chart(fig_risk_donut, use_container_width=True)

    # Row 4: Potential Arbitrage benefit bar & State-wise market map
    st.subheader("💡 Financial Arbitrage & Geographical Footprint")
    r4_col1, r4_col2 = st.columns([1, 1])

    with r4_col1:
        top_arb_ships = arb_df.sort_values("estimated_net_benefit", ascending=False).head(10)
        fig_arb_bar = create_bar_chart(top_arb_ships, "shipment_id", "estimated_net_benefit", color_col="recommendation_status", title="7. Top 10 Shipments with Highest Arbitrage Net Gain (₹)")
        st.plotly_chart(fig_arb_bar, use_container_width=True)

    with r4_col2:
        fig_map = create_state_market_map(markets_df)
        st.plotly_chart(fig_map, use_container_width=True)

if __name__ == "__main__":
    render()
else:
    render()
