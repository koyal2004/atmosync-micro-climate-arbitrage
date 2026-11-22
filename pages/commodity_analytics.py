"""
AtmoSync - Page 4: Commodity Analytics
Agricultural Commodity Intelligence: Commodity-wise price analysis, market-wise price comparisons,
arrival quantities, supply/demand indices, monthly/date-wise trends, and AI price projections.

All values are computed dynamically from SQLite database records — no hardcoded metrics.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from database.database import load_table
from utils.helpers import render_kpi_card, format_currency, format_quantity
from utils.charts import create_bar_chart, create_line_chart, THEME_LAYOUT
from modules.forecasting import forecast_commodity_price
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL


def render():
    st.markdown(
        '<div class="disclaimer-banner"><strong>Synthetic Market Intelligence:</strong> '
        + PERSISTENT_DISCLAIMER
        + "</div>",
        unsafe_allow_html=True,
    )
    st.title("Agricultural Commodity Intelligence")
    st.caption(
        f"APMC Mandi Price Dynamics, Seasonal Arrival Cycles, Supply-Demand Spreads & Projections • {DATASET_LABEL}"
    )

    try:
        commodities_df = load_table("commodities")
        markets_df = load_table("markets")
        prices_df = load_table("market_prices")
    except Exception as e:
        st.error(f"⚠️ Failed to load database tables: {e}")
        return

    if commodities_df.empty or prices_df.empty:
        st.warning("Commodity or price datasets are empty. Please generate synthetic data in Reports & Data Management.")
        return

    # ------------------------------------------------------------------
    # Data Merging & Preprocessing
    # ------------------------------------------------------------------
    merged_prices = prices_df.merge(
        commodities_df[["commodity_id", "commodity_name", "category"]],
        on="commodity_id",
        how="left"
    )
    merged_prices = merged_prices.merge(
        markets_df[["market_id", "market_name", "state"]],
        on="market_id",
        how="left"
    )
    merged_prices["date_dt"] = pd.to_datetime(merged_prices["date"], errors="coerce")
    merged_prices["month"] = merged_prices["date_dt"].dt.strftime("%Y-%m")

    # ------------------------------------------------------------------
    # Interactive Sidebar Filters
    # ------------------------------------------------------------------
    st.sidebar.markdown("### 🌾 Commodity & Market Filters")

    # Category Filter
    categories = ["All"] + sorted(commodities_df["category"].dropna().unique().tolist())
    selected_cat = st.sidebar.selectbox("Filter Category", categories, index=0, key="comm_cat_filter")

    filtered_comms_meta = (
        commodities_df
        if selected_cat == "All"
        else commodities_df[commodities_df["category"] == selected_cat]
    )

    # Commodity Selection Filter
    comm_options = ["All"] + sorted(filtered_comms_meta["commodity_name"].dropna().unique().tolist())
    selected_comm_name = st.sidebar.selectbox("Select Specific Commodity", comm_options, index=0, key="comm_name_filter")

    # State Filter
    states = ["All"] + sorted(markets_df["state"].dropna().unique().tolist())
    selected_state = st.sidebar.selectbox("Select State", states, index=0, key="comm_state_filter")

    # Market Filter
    available_markets = markets_df if selected_state == "All" else markets_df[markets_df["state"] == selected_state]
    mkt_options = ["All"] + sorted(available_markets["market_name"].dropna().unique().tolist())
    selected_market = st.sidebar.selectbox("Select APMC Mandi", mkt_options, index=0, key="comm_mkt_filter")

    # Date Range Filter
    min_date = merged_prices["date_dt"].min()
    max_date = merged_prices["date_dt"].max()
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.sidebar.date_input(
            "Observation Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
            key="comm_date_range"
        )
    else:
        date_range = None

    # Apply Filters to dataset
    filtered_prices = merged_prices.copy()
    if selected_cat != "All":
        filtered_prices = filtered_prices[filtered_prices["category"] == selected_cat]
    if selected_comm_name != "All":
        filtered_prices = filtered_prices[filtered_prices["commodity_name"] == selected_comm_name]
    if selected_state != "All":
        filtered_prices = filtered_prices[filtered_prices["state"] == selected_state]
    if selected_market != "All":
        filtered_prices = filtered_prices[filtered_prices["market_name"] == selected_market]
    if date_range and len(date_range) == 2:
        start_d, end_d = date_range
        filtered_prices = filtered_prices[
            (filtered_prices["date_dt"].dt.date >= start_d)
            & (filtered_prices["date_dt"].dt.date <= end_d)
        ]

    # ------------------------------------------------------------------
    # Dynamic KPI Cards
    # ------------------------------------------------------------------
    st.markdown("#### 📌 Agricultural Commodity Statistics")
    st.caption("All figures below are computed dynamically from filtered SQLite market records.")

    total_comms = filtered_prices["commodity_id"].nunique()
    avg_modal_p = float(filtered_prices["modal_price"].mean()) if not filtered_prices.empty else 0.0
    highest_p = float(filtered_prices["maximum_price"].max()) if not filtered_prices.empty else 0.0
    lowest_p = float(filtered_prices["minimum_price"].min()) if not filtered_prices.empty else 0.0
    total_arrivals = float(filtered_prices["arrival_quantity"].sum()) if not filtered_prices.empty else 0.0
    avg_supply = float(filtered_prices["supply_index"].mean()) if not filtered_prices.empty else 0.0
    avg_demand = float(filtered_prices["demand_index"].mean()) if not filtered_prices.empty else 0.0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.markdown(render_kpi_card("Commodity Scope", f"{total_comms:,}", "Unique varieties", icon="🌾"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Avg Modal Price", f"₹{avg_modal_p:.2f}/kg", "Weighted mandi rate", icon="💵"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Peak Observed", f"₹{highest_p:.2f}/kg", "Maximum wholesale bid", icon="📈"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Floor Observed", f"₹{lowest_p:.2f}/kg", "Minimum wholesale bid", icon="📉"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Total Arrivals", format_quantity(total_arrivals), "Arrival volume", icon="⚖️"), unsafe_allow_html=True)
    with k6:
        ratio = (avg_demand / max(1.0, avg_supply))
        st.markdown(render_kpi_card("Demand/Supply", f"{ratio:.2f}", f"D: {avg_demand:.0f} | S: {avg_supply:.0f}", delta="Surplus Demand" if ratio > 1.0 else "Balanced Supply", delta_color="positive" if ratio > 1.0 else "normal", icon="⚖️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Handle Empty Data Condition
    # ------------------------------------------------------------------
    if filtered_prices.empty:
        st.warning("No market price records match your selected filter combination. Please expand your filter selections.")
        return

    # ------------------------------------------------------------------
    # Automated Algorithmic Market Findings
    # ------------------------------------------------------------------
    st.subheader("💡 Algorithmic Market Findings & Price Extremes")
    comm_stats = filtered_prices.groupby("commodity_name")["modal_price"].agg(["mean", "std", "min", "max"]).reset_index()
    mkt_stats = filtered_prices.groupby("market_name")["modal_price"].agg(["mean", "min", "max"]).reset_index()

    if not comm_stats.empty and not mkt_stats.empty:
        highest_c = comm_stats.sort_values("mean", ascending=False).iloc[0]
        lowest_c = comm_stats.sort_values("mean", ascending=True).iloc[0]
        most_vol = comm_stats.sort_values("std", ascending=False).iloc[0] if len(comm_stats) > 1 else highest_c
        top_mkt = mkt_stats.sort_values("mean", ascending=False).iloc[0]
        floor_mkt = mkt_stats.sort_values("mean", ascending=True).iloc[0]
        vol_std = float(most_vol["std"]) if pd.notna(most_vol["std"]) else 0.0

        st.markdown(f"""
        - 🥇 **Price Leader:** **{highest_c['commodity_name']}** commands the highest average modal price at **₹{highest_c['mean']:.2f}/kg** (range: ₹{highest_c['min']:.2f} &ndash; ₹{highest_c['max']:.2f}).
        - 📉 **Lowest Wholesale Rate:** **{lowest_c['commodity_name']}** trades lowest across monitored mandis at **₹{lowest_c['mean']:.2f}/kg**.
        - ⚡ **Highest Market Dispersion:** **{most_vol['commodity_name']}** exhibits greatest volatility (σ = ₹{vol_std:.2f}), creating prime conditions for spatial price arbitrage.
        - 🏛️ **Premium Mandi:** Highest realization benchmark registered at **{top_mkt['market_name']}** (avg modal: **₹{top_mkt['mean']:.2f}/kg**); floor benchmark at **{floor_mkt['market_name']}** (avg modal: **₹{floor_mkt['mean']:.2f}/kg**).
        """)

    st.markdown("---")
    st.subheader("📊 Interactive Commodity & Mandi Visualizations")

    # ------------------------------------------------------------------
    # Row 1: Commodity-wise Price & Date-wise Price Trends
    # ------------------------------------------------------------------
    c1, c2 = st.columns(2)
    with c1:
        top_comm_avg = (
            filtered_prices.groupby("commodity_name")["modal_price"]
            .mean()
            .reset_index()
            .sort_values("modal_price", ascending=False)
            .head(10)
        )
        fig_comm_avg = create_bar_chart(
            top_comm_avg, "commodity_name", "modal_price",
            title="1. Commodity-Wise Average Modal Price (₹/kg)"
        )
        st.plotly_chart(fig_comm_avg, use_container_width=True)

    with c2:
        price_timeline = (
            filtered_prices.groupby("date")
            .agg({"modal_price": "mean", "minimum_price": "min", "maximum_price": "max"})
            .reset_index()
            .sort_values("date")
        )
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=price_timeline["date"], y=price_timeline["modal_price"],
            name="Modal Price", line={"color": COLORS["secondary"], "width": 2.5}
        ))
        fig_trend.add_trace(go.Scatter(
            x=price_timeline["date"], y=price_timeline["maximum_price"],
            name="Max Peak", line={"color": COLORS["critical"], "dash": "dash", "width": 1.5}
        ))
        fig_trend.add_trace(go.Scatter(
            x=price_timeline["date"], y=price_timeline["minimum_price"],
            name="Min Floor", line={"color": COLORS["info"], "dash": "dash", "width": 1.5}
        ))
        fig_trend.update_layout(
            title="2. Date-Wise Price Trends & Range Envelope",
            yaxis_title="Price (₹/kg)",
            **THEME_LAYOUT
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # ------------------------------------------------------------------
    # Row 2: Monthly Price Trends & Market-wise Price Comparison
    # ------------------------------------------------------------------
    c3, c4 = st.columns(2)
    with c3:
        monthly_var = (
            filtered_prices.groupby("month")["modal_price"]
            .agg(["min", "mean", "max"])
            .reset_index()
            .sort_values("month")
        )
        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Bar(
            x=monthly_var["month"], y=monthly_var["mean"],
            name="Mean Modal Price", marker_color=COLORS["secondary"]
        ))
        fig_monthly.add_trace(go.Scatter(
            x=monthly_var["month"], y=monthly_var["max"],
            name="Max Peak", line={"color": COLORS["critical"], "dash": "dash"}
        ))
        fig_monthly.add_trace(go.Scatter(
            x=monthly_var["month"], y=monthly_var["min"],
            name="Min Floor", line={"color": COLORS["info"], "dash": "dash"}
        ))
        fig_monthly.update_layout(
            title="3. Monthly Price Fluctuations & Spread",
            yaxis_title="Price (₹/kg)",
            **THEME_LAYOUT
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    with c4:
        top_m = (
            filtered_prices.groupby("market_name")["modal_price"]
            .mean()
            .reset_index()
            .sort_values("modal_price", ascending=False)
            .head(10)
        )
        fig_mkt_comp = create_bar_chart(
            top_m, "market_name", "modal_price",
            title="4. Market-Wise Modal Price Comparison (Top 10 Mandis)"
        )
        st.plotly_chart(fig_mkt_comp, use_container_width=True)

    # ------------------------------------------------------------------
    # Row 3: Minimum, Maximum, and Modal Price Analysis & Arrival Quantity
    # ------------------------------------------------------------------
    c5, c6 = st.columns(2)
    with c5:
        # Min, max, modal comparison across top commodities
        sub_sample_comm = (
            filtered_prices.groupby("commodity_name")[["minimum_price", "modal_price", "maximum_price"]]
            .mean()
            .reset_index()
            .head(8)
        )
        fig_mmm = go.Figure()
        fig_mmm.add_trace(go.Bar(
            x=sub_sample_comm["commodity_name"], y=sub_sample_comm["minimum_price"],
            name="Minimum Price", marker_color="#94A3B8"
        ))
        fig_mmm.add_trace(go.Bar(
            x=sub_sample_comm["commodity_name"], y=sub_sample_comm["modal_price"],
            name="Modal Price", marker_color=COLORS["secondary"]
        ))
        fig_mmm.add_trace(go.Bar(
            x=sub_sample_comm["commodity_name"], y=sub_sample_comm["maximum_price"],
            name="Maximum Price", marker_color=COLORS["primary"]
        ))
        fig_mmm.update_layout(
            barmode="group",
            title="5. Minimum, Modal & Maximum Price Analysis (₹/kg)",
            yaxis_title="Price (₹/kg)",
            **THEME_LAYOUT
        )
        st.plotly_chart(fig_mmm, use_container_width=True)

    with c6:
        arrivals_by_comm = (
            filtered_prices.groupby("commodity_name")["arrival_quantity"]
            .sum()
            .reset_index()
            .sort_values("arrival_quantity", ascending=False)
            .head(10)
        )
        arrivals_by_comm["arrivals_MT"] = arrivals_by_comm["arrival_quantity"] / 1000.0
        fig_arr = create_bar_chart(
            arrivals_by_comm, "commodity_name", "arrivals_MT",
            title="6. Commodity Arrival Quantity Analysis (Metric Tonnes)"
        )
        st.plotly_chart(fig_arr, use_container_width=True)

    # ------------------------------------------------------------------
    # Row 4: Supply vs Demand Comparison & Price Distribution
    # ------------------------------------------------------------------
    c7, c8 = st.columns(2)
    with c7:
        # Supply and Demand Comparison
        sd_data = (
            filtered_prices.groupby("commodity_name")[["supply_index", "demand_index"]]
            .mean()
            .reset_index()
            .head(10)
        )
        fig_sd = go.Figure()
        fig_sd.add_trace(go.Bar(
            x=sd_data["commodity_name"], y=sd_data["supply_index"],
            name="Supply Index", marker_color=COLORS["info"]
        ))
        fig_sd.add_trace(go.Bar(
            x=sd_data["commodity_name"], y=sd_data["demand_index"],
            name="Demand Index", marker_color=COLORS["warning"]
        ))
        fig_sd.update_layout(
            barmode="group",
            title="7. Supply vs. Demand Index Comparison (Equilibrium = 100)",
            yaxis_title="Index Level",
            **THEME_LAYOUT
        )
        st.plotly_chart(fig_sd, use_container_width=True)

    with c8:
        fig_dist = px.histogram(
            filtered_prices, x="modal_price", nbins=30,
            title="8. Mandi Modal Price Frequency Distribution (₹/kg)",
            color_discrete_sequence=[COLORS["primary"]]
        )
        fig_dist.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_dist, use_container_width=True)

    # ------------------------------------------------------------------
    # Row 5: AI Price Forecast Projections
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔮 14-Day Price Projection & Predictive Modeling")
    target_comm_id = filtered_prices.iloc[0]["commodity_id"]
    target_comm_name = filtered_prices.iloc[0]["commodity_name"]
    hist_p, fc_p, fc_meta = forecast_commodity_price(prices_df, target_comm_id, horizon_days=14)

    fig_fc = go.Figure()
    fig_fc.add_trace(go.Scatter(
        x=hist_p["date"], y=hist_p["modal_price"],
        name="Observed Modal", line={"color": COLORS["primary"], "width": 2}
    ))
    fig_fc.add_trace(go.Scatter(
        x=fc_p["date"], y=fc_p["forecast_price"],
        name="14-Day Forecast", line={"color": COLORS["secondary"], "dash": "dash", "width": 2}
    ))
    fig_fc.add_trace(go.Scatter(
        x=fc_p["date"], y=fc_p["upper_ci"],
        name="Upper 95% CI", line={"color": "#CBD5E1", "dash": "dot"}
    ))
    fig_fc.add_trace(go.Scatter(
        x=fc_p["date"], y=fc_p["lower_ci"],
        name="Lower 95% CI", fill="tonexty", fillcolor="rgba(18, 184, 166, 0.12)",
        line={"color": "#CBD5E1", "dash": "dot"}
    ))
    fig_fc.update_layout(
        title=f"9. 14-Day Projection for {target_comm_name} ({fc_meta['trend_direction']})",
        yaxis_title="Modal Price (₹/kg)",
        **THEME_LAYOUT
    )
    st.plotly_chart(fig_fc, use_container_width=True)

    # ------------------------------------------------------------------
    # Data Table Manifest
    # ------------------------------------------------------------------
    with st.expander(f"📄 View Underlying Market Price Records ({len(filtered_prices):,} rows)"):
        st.dataframe(
            filtered_prices[[
                "price_id", "date", "commodity_name", "market_name",
                "state", "minimum_price", "modal_price", "maximum_price",
                "arrival_quantity", "demand_index", "supply_index"
            ]].rename(columns={
                "price_id": "Price ID",
                "date": "Date",
                "commodity_name": "Commodity",
                "market_name": "APMC Mandi",
                "state": "State",
                "minimum_price": "Min Price (₹)",
                "modal_price": "Modal Price (₹)",
                "maximum_price": "Max Price (₹)",
                "arrival_quantity": "Arrivals (kg)",
                "demand_index": "Demand Index",
                "supply_index": "Supply Index"
            }),
            use_container_width=True
        )


if __name__ == "__main__":
    render()
else:
    render()
