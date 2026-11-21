"""
AtmoSync - Page 1: Executive Dashboard
Executive overview of agricultural supply chain operations, fleet status, and market signals.
Dynamic KPIs, interactive filters, and Plotly visualizations driven by SQLite data.

All values are computed dynamically from database records — nothing is hardcoded.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database.database import load_table, execute_query
from utils.helpers import render_kpi_card, format_currency, format_quantity
from utils.charts import (
    create_donut_chart, create_line_chart, create_bar_chart,
    create_dual_axis_chart, create_state_market_map
)
from modules.risk_engine import calculate_shipment_risk, get_risk_summary
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL


def render():
    # Academic disclaimer banner
    st.markdown(
        '<div class="disclaimer-banner"><strong>Academic Research Mode:</strong> '
        + PERSISTENT_DISCLAIMER
        + "</div>",
        unsafe_allow_html=True,
    )

    st.title("AtmoSync – Executive Overview")
    st.caption(
        f"Agricultural Supply Chain Telemetry & Market Arbitrage Intelligence • {DATASET_LABEL}"
    )

    # ------------------------------------------------------------------
    # Load all tables from database
    # ------------------------------------------------------------------
    try:
        shipments_df = load_table("shipments")
        commodities_df = load_table("commodities")
        markets_df = load_table("markets")
        sensor_df = load_table("sensor_readings")
        prices_df = load_table("market_prices")
        arb_df = load_table("arbitrage_opportunities")
    except Exception as e:
        st.error(f"⚠️ Failed to load data from database: {e}")
        return

    if shipments_df.empty:
        st.warning(
            "Database contains no records. Please generate synthetic data in Reports & Data Management."
        )
        return

    # ------------------------------------------------------------------
    # Interactive Filters – Sidebar
    # ------------------------------------------------------------------
    st.sidebar.markdown("### 🎛️ Executive Filters")

    # Date range filter
    if "departure_date" in shipments_df.columns:
        shipments_df["departure_date_dt"] = pd.to_datetime(
            shipments_df["departure_date"], errors="coerce"
        )
        min_date = shipments_df["departure_date_dt"].min()
        max_date = shipments_df["departure_date_dt"].max()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date.date(), max_date.date()),
                min_value=min_date.date(),
                max_value=max_date.date(),
                key="exec_date_range",
            )
        else:
            date_range = None
    else:
        date_range = None

    # State filter
    all_states = ["All"] + sorted(markets_df["state"].unique().tolist())
    selected_state = st.sidebar.selectbox("Filter by State", all_states, index=0, key="exec_state")

    # Commodity filter
    comm_names_map = dict(zip(commodities_df["commodity_id"], commodities_df["commodity_name"]))
    all_cats = ["All"] + sorted(commodities_df["category"].unique().tolist())
    selected_cat = st.sidebar.selectbox("Commodity Category", all_cats, index=0, key="exec_cat")

    # Market filter
    all_markets_list = ["All"] + sorted(markets_df["market_name"].unique().tolist())
    selected_market = st.sidebar.selectbox("Market", all_markets_list, index=0, key="exec_market")

    # Shipment status filter
    all_statuses = ["All"] + sorted(shipments_df["shipment_status"].unique().tolist())
    selected_status = st.sidebar.selectbox("Shipment Status", all_statuses, index=0, key="exec_status")

    # ------------------------------------------------------------------
    # Apply Filters
    # ------------------------------------------------------------------
    filtered_ships = shipments_df.copy()

    # Date filter
    if date_range and len(date_range) == 2:
        start_dt, end_dt = date_range
        if "departure_date_dt" in filtered_ships.columns:
            filtered_ships = filtered_ships[
                (filtered_ships["departure_date_dt"].dt.date >= start_dt)
                & (filtered_ships["departure_date_dt"].dt.date <= end_dt)
            ]

    # Status filter
    if selected_status != "All":
        filtered_ships = filtered_ships[filtered_ships["shipment_status"] == selected_status]

    # State filter
    if selected_state != "All":
        valid_mkts = markets_df[markets_df["state"] == selected_state]["market_id"].tolist()
        filtered_ships = filtered_ships[
            filtered_ships["source_market_id"].isin(valid_mkts)
            | filtered_ships["destination_market_id"].isin(valid_mkts)
        ]

    # Commodity category filter
    if selected_cat != "All":
        valid_comms = commodities_df[commodities_df["category"] == selected_cat][
            "commodity_id"
        ].tolist()
        filtered_ships = filtered_ships[filtered_ships["commodity_id"].isin(valid_comms)]

    # Market filter
    if selected_market != "All":
        valid_mkt_ids = markets_df[markets_df["market_name"] == selected_market][
            "market_id"
        ].tolist()
        filtered_ships = filtered_ships[
            filtered_ships["source_market_id"].isin(valid_mkt_ids)
            | filtered_ships["destination_market_id"].isin(valid_mkt_ids)
        ]

    # ------------------------------------------------------------------
    # Compute KPIs dynamically from filtered data
    # ------------------------------------------------------------------
    total_ships = len(filtered_ships)
    active_ships = int(
        filtered_ships["shipment_status"].isin(["In Transit", "Delayed", "At Risk"]).sum()
    )
    total_comms = commodities_df["commodity_id"].nunique()

    # Average commodity price from prices table
    avg_commodity_price = float(prices_df["modal_price"].mean()) if not prices_df.empty else 0.0

    # High-risk shipments (At Risk status)
    high_risk_ships = int((filtered_ships["shipment_status"] == "At Risk").sum())

    # Total sensor readings
    total_sensor_readings = len(sensor_df)

    # Filtered sensor readings
    if not sensor_df.empty:
        filtered_sensors = sensor_df[sensor_df["shipment_id"].isin(filtered_ships["shipment_id"])]
        if filtered_sensors.empty:
            filtered_sensors = sensor_df
        avg_temp = float(filtered_sensors["temperature"].mean())
        avg_hum = float(filtered_sensors["humidity"].mean())
    else:
        avg_temp, avg_hum = 0.0, 0.0
        filtered_sensors = pd.DataFrame()

    # Arbitrage count
    total_opps = (
        len(
            arb_df[
                arb_df["recommendation_status"].isin(["High Opportunity", "Moderate Opportunity"])
            ]
        )
        if not arb_df.empty
        else 0
    )

    # ------------------------------------------------------------------
    # KPI Cards – 6 Required + 2 Supplementary
    # ------------------------------------------------------------------
    st.markdown("#### 📌 Key Performance Indicators")
    st.caption("⚠️ All metrics below are computed dynamically from synthetic demonstration data.")

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            render_kpi_card(
                "Total Shipments",
                f"{total_ships:,}",
                "Active & Historical (filtered)",
                icon="📦",
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            render_kpi_card(
                "Active Shipments",
                f"{active_ships:,}",
                "In Transit, Delayed, At Risk",
                delta=f"{(active_ships / max(1, total_ships)) * 100:.1f}% of fleet",
                delta_color="positive",
                icon="🚚",
            ),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            render_kpi_card(
                "Total Commodities",
                f"{total_comms:,}",
                "Unique commodity variants tracked",
                icon="🌾",
            ),
            unsafe_allow_html=True,
        )

    k4, k5, k6 = st.columns(3)
    with k4:
        st.markdown(
            render_kpi_card(
                "Avg Commodity Price",
                f"₹{avg_commodity_price:.2f}/kg",
                "Average modal price across all markets",
                icon="💰",
            ),
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            render_kpi_card(
                "High-Risk Shipments",
                f"{high_risk_ships:,}",
                "Flagged for thermal stress or delays",
                delta=f"{high_risk_ships} critical consignments",
                delta_color="negative" if high_risk_ships > 0 else "positive",
                icon="⚠️",
            ),
            unsafe_allow_html=True,
        )
    with k6:
        st.markdown(
            render_kpi_card(
                "Total Sensor Readings",
                f"{total_sensor_readings:,}",
                "IoT telemetry records (simulated)",
                icon="📡",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Handle empty filtered results
    # ------------------------------------------------------------------
    if filtered_ships.empty:
        st.warning(
            "No shipments match the current filter combination. "
            "Adjust the filters above to see data."
        )
        return

    # ------------------------------------------------------------------
    # Row 1: Shipment Status Distribution & Commodity Price Comparison
    # ------------------------------------------------------------------
    st.subheader("📊 Shipment Status & Commodity Pricing")
    r1_col1, r1_col2 = st.columns([1, 1])

    with r1_col1:
        status_colors = {
            "In Transit": COLORS["info"],
            "Delivered": COLORS["success"],
            "Completed": COLORS["primary"],
            "At Risk": COLORS["critical"],
            "Delayed": COLORS["warning"],
        }
        fig_donut = create_donut_chart(
            filtered_ships,
            "shipment_status",
            title="1. Shipment Status Distribution",
            color_map=status_colors,
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with r1_col2:
        # Commodity Price Comparison – avg modal price by commodity category
        comm_price_merge = prices_df.merge(
            commodities_df[["commodity_id", "category"]], on="commodity_id", how="left"
        )
        if not comm_price_merge.empty:
            cat_prices = (
                comm_price_merge.groupby("category")["modal_price"]
                .mean()
                .reset_index()
                .sort_values("modal_price", ascending=False)
            )
            fig_price_comp = create_bar_chart(
                cat_prices,
                "category",
                "modal_price",
                title="2. Commodity Price Comparison (Avg Modal ₹/kg)",
                orientation="v",
            )
            st.plotly_chart(fig_price_comp, use_container_width=True)
        else:
            st.info("No price data available.")

    # ------------------------------------------------------------------
    # Row 2: Temperature & Humidity Trends + Spoilage Risk Distribution
    # ------------------------------------------------------------------
    st.subheader("🌡️ Environmental Telemetry & Spoilage Risk")
    r2_col1, r2_col2 = st.columns([1, 1])

    with r2_col1:
        if not sensor_df.empty:
            sensor_daily = sensor_df.copy()
            sensor_daily["date"] = pd.to_datetime(sensor_daily["timestamp"]).dt.strftime(
                "%Y-%m-%d"
            )
            daily_telemetry = (
                sensor_daily.groupby("date")
                .agg({"temperature": "mean", "humidity": "mean"})
                .reset_index()
                .sort_values("date")
                .tail(30)
            )
            fig_dual = create_dual_axis_chart(
                daily_telemetry,
                "date",
                "temperature",
                "humidity",
                "Avg Temp (°C)",
                "Avg Humidity (%)",
                "3. Temperature & Humidity Trends (Last 30 Days)",
            )
            st.plotly_chart(fig_dual, use_container_width=True)
        else:
            st.info("No sensor data available for telemetry trends.")

    with r2_col2:
        risk_df = calculate_shipment_risk(filtered_ships, commodities_df, sensor_df)
        if not risk_df.empty:
            risk_color_map = {
                "Low": COLORS["success"],
                "Moderate": COLORS["info"],
                "High": COLORS["warning"],
                "Critical": COLORS["critical"],
            }
            fig_risk_donut = create_donut_chart(
                risk_df,
                "risk_category",
                title="4. Spoilage Risk Distribution",
                color_map=risk_color_map,
            )
            st.plotly_chart(fig_risk_donut, use_container_width=True)
        else:
            st.info("No risk data to display for current filters.")

    # ------------------------------------------------------------------
    # Row 3: Market-wise Analytics & State-wise Shipment Visualization
    # ------------------------------------------------------------------
    st.subheader("🏛️ Market Analytics & Geographical Footprint")
    r3_col1, r3_col2 = st.columns([1, 1])

    with r3_col1:
        # Market-wise average price analytics
        if not prices_df.empty:
            top_mkt_prices = prices_df.groupby("market_id")["modal_price"].mean().reset_index()
            top_mkt_prices = top_mkt_prices.merge(
                markets_df[["market_id", "market_name", "state"]], on="market_id", how="left"
            )
            top_10_mkt = top_mkt_prices.sort_values("modal_price", ascending=False).head(10)
            fig_mkt_p = create_bar_chart(
                top_10_mkt,
                "market_name",
                "modal_price",
                color_col="state",
                title="5. Market-wise Average Price Analytics (₹/kg)",
            )
            st.plotly_chart(fig_mkt_p, use_container_width=True)
        else:
            st.info("No market price data available.")

    with r3_col2:
        # State-wise shipment visualization using coordinates
        if not markets_df.empty and "latitude" in markets_df.columns:
            fig_map = create_state_market_map(markets_df)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("No geographic market data available for map visualization.")

    # ------------------------------------------------------------------
    # Row 4: Commodity Volume Distribution & Arbitrage Opportunities
    # ------------------------------------------------------------------
    st.subheader("💡 Commodity Insights & Arbitrage Intelligence")
    r4_col1, r4_col2 = st.columns([1, 1])

    with r4_col1:
        # Commodity category shipment volume
        merged_ships = filtered_ships.merge(
            commodities_df[["commodity_id", "category"]], on="commodity_id", how="left"
        )
        if not merged_ships.empty:
            comm_dist = merged_ships.groupby("category")["quantity_kg"].sum().reset_index()
            comm_dist["quantity_MT"] = comm_dist["quantity_kg"] / 1000.0
            fig_comm_bar = create_bar_chart(
                comm_dist,
                "category",
                "quantity_MT",
                title="7. Commodity Category Volume (Metric Tonnes)",
                orientation="v",
            )
            st.plotly_chart(fig_comm_bar, use_container_width=True)
        else:
            st.info("No commodity volume data for current filters.")

    with r4_col2:
        # Arbitrage net benefit analysis
        if not arb_df.empty:
            top_arb_ships = arb_df.sort_values("estimated_net_benefit", ascending=False).head(10)
            fig_arb_bar = create_bar_chart(
                top_arb_ships,
                "shipment_id",
                "estimated_net_benefit",
                color_col="recommendation_status",
                title="8. Top Arbitrage Opportunities by Net Gain (₹)",
            )
            st.plotly_chart(fig_arb_bar, use_container_width=True)
        else:
            st.info("No arbitrage data available.")

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown(
        '<div class="footer-watermark">'
        "AtmoSync Executive Dashboard • Synthetic Demonstration Data • "
        "All values computed dynamically from database records"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render()
else:
    render()
