"""
AtmoSync - Page 4: Commodity Analytics
Agricultural Commodity Intelligence: Price distributions, APMC mandi spreads, arrival quantities, and automated insights.
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
from config.settings import PERSISTENT_DISCLAIMER, COLORS

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Synthetic Market Intelligence:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)
    st.title("Agricultural Commodity Intelligence")
    st.caption("APMC Mandi Price Dynamics, Seasonal Arrival Cycles, Volatility Analysis & AI Price Projections")

    commodities_df = load_table("commodities")
    markets_df = load_table("markets")
    prices_df = load_table("market_prices")

    if commodities_df.empty or prices_df.empty:
        st.warning("Commodity or price datasets are empty.")
        return

    # Sidebar Filters per Section 9
    st.sidebar.markdown("### 🌾 Commodity Filters")
    categories = ["All"] + sorted(commodities_df["category"].unique().tolist())
    selected_cat = st.sidebar.selectbox("Filter Category", categories, index=0)

    filtered_comms = commodities_df if selected_cat == "All" else commodities_df[commodities_df["category"] == selected_cat]
    
    comm_options = ["All"] + filtered_comms["commodity_name"].tolist()
    selected_comm_name = st.sidebar.selectbox("Select Specific Commodity", comm_options, index=0)

    states = ["All"] + sorted(markets_df["state"].unique().tolist())
    selected_state = st.sidebar.selectbox("Select State", states, index=0)

    # Filter prices
    merged_prices = prices_df.merge(commodities_df[["commodity_id", "commodity_name", "category"]], on="commodity_id", how="left")
    merged_prices = merged_prices.merge(markets_df[["market_id", "market_name", "state"]], on="market_id", how="left")

    if selected_cat != "All":
        merged_prices = merged_prices[merged_prices["category"] == selected_cat]
    if selected_comm_name != "All":
        merged_prices = merged_prices[merged_prices["commodity_name"] == selected_comm_name]
    if selected_state != "All":
        merged_prices = merged_prices[merged_prices["state"] == selected_state]

    # Calculate KPIs (Section 9)
    total_comms = commodities_df["commodity_id"].nunique()
    avg_modal_p = float(merged_prices["modal_price"].mean()) if not merged_prices.empty else 0.0
    highest_p = float(merged_prices["maximum_price"].max()) if not merged_prices.empty else 0.0
    lowest_p = float(merged_prices["minimum_price"].min()) if not merged_prices.empty else 0.0
    total_arrivals = float(merged_prices["arrival_quantity"].sum()) if not merged_prices.empty else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(render_kpi_card("Commodity Scope", f"{total_comms}", "Tracked agro SKUs", icon="🌾"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Avg Modal Price", f"₹{avg_modal_p:.2f}/kg", "Weighted market rate", icon="💵"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Highest Observed", f"₹{highest_p:.2f}/kg", "Peak wholesale bid", icon="📈"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Lowest Observed", f"₹{lowest_p:.2f}/kg", "Floor wholesale bid", icon="📉"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Total Arrivals", format_quantity(total_arrivals), "Arrival volume", icon="⚖️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # AUTOMATED ANALYTICAL INSIGHTS (Section 9)
    st.subheader("💡 Algorithmic Market Findings & Price Extremes")
    if not merged_prices.empty:
        comm_stats = merged_prices.groupby("commodity_name")["modal_price"].agg(["mean", "std", "min", "max"]).reset_index()
        mkt_stats = merged_prices.groupby("market_name")["modal_price"].agg(["mean", "min", "max"]).reset_index()
        
        highest_c = comm_stats.sort_values("mean", ascending=False).iloc[0]
        lowest_c = comm_stats.sort_values("mean", ascending=True).iloc[0]
        most_vol = comm_stats.sort_values("std", ascending=False).iloc[0] if len(comm_stats) > 1 else highest_c
        top_mkt = mkt_stats.sort_values("mean", ascending=False).iloc[0]
        floor_mkt = mkt_stats.sort_values("mean", ascending=True).iloc[0]

        st.markdown(f"""
        - 🥇 **Price Leader:** **{highest_c['commodity_name']}** command highest average modal price at **₹{highest_c['mean']:.2f}/kg** (range: ₹{highest_c['min']:.2f} &ndash; ₹{highest_c['max']:.2f}).
        - 📉 **Lowest Wholesale Rate:** **{lowest_c['commodity_name']}** trades lowest across monitored mandis at **₹{lowest_c['mean']:.2f}/kg**.
        - ⚡ **Highest Market Dispersion:** **{most_vol['commodity_name']}** exhibits greatest volatility (σ = ₹{most_vol['std']:.2f}), creating prime conditions for spatial price arbitrage.
        - 🏛️ **Premium Mandi:** Highest realization benchmark registered at **{top_mkt['market_name']}** (avg modal: **₹{top_mkt['mean']:.2f}/kg**); floor benchmark at **{floor_mkt['market_name']}** (avg modal: **₹{floor_mkt['mean']:.2f}/kg**).
        """)
    else:
        st.info("No price records matched the filter criteria.")

    st.markdown("---")
    st.subheader("📊 Commodity Visual Intelligence Dashboard (8 Core Charts)")

    # 1. Commodity-wise average price
    # 2. Historical commodity price trends
    c1, c2 = st.columns(2)
    with c1:
        top_comm_avg = merged_prices.groupby("commodity_name")["modal_price"].mean().reset_index().sort_values("modal_price", ascending=False).head(10)
        fig_comm_avg = create_bar_chart(top_comm_avg, "commodity_name", "modal_price", title="1. Top 10 Commodities by Average Modal Price (₹/kg)")
        st.plotly_chart(fig_comm_avg, use_container_width=True)

    with c2:
        price_timeline = merged_prices.groupby("date")["modal_price"].mean().reset_index().sort_values("date")
        fig_trend = create_line_chart(price_timeline, "date", "modal_price", title="2. Historical Modal Price Timeline Across Monitored Hubs", y_title="Modal Price (₹/kg)")
        st.plotly_chart(fig_trend, use_container_width=True)

    # 3. Monthly price fluctuations
    # 4. Market-wise commodity comparison
    c3, c4 = st.columns(2)
    with c3:
        merged_prices["month"] = pd.to_datetime(merged_prices["date"]).dt.strftime("%Y-%m")
        monthly_var = merged_prices.groupby("month")["modal_price"].agg(["min", "mean", "max"]).reset_index()
        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Bar(x=monthly_var["month"], y=monthly_var["mean"], name="Mean Modal Price", marker_color=COLORS["secondary"]))
        fig_monthly.add_trace(go.Scatter(x=monthly_var["month"], y=monthly_var["max"], name="Max Peak", line={"color": COLORS["critical"], "dash": "dash"}))
        fig_monthly.add_trace(go.Scatter(x=monthly_var["month"], y=monthly_var["min"], name="Min Floor", line={"color": COLORS["info"], "dash": "dash"}))
        fig_monthly.update_layout(title="3. Monthly Price Range Fluctuations", **THEME_LAYOUT)
        st.plotly_chart(fig_monthly, use_container_width=True)

    with c4:
        top_m = merged_prices.groupby("market_name")["modal_price"].mean().reset_index().sort_values("modal_price", ascending=False).head(10)
        fig_mkt_comp = create_bar_chart(top_m, "market_name", "modal_price", title="4. Cross-Mandi Price Comparison (Top 10 Locations)")
        st.plotly_chart(fig_mkt_comp, use_container_width=True)

    # 5. Commodity arrival quantity
    # 6. Minimum, maximum, and modal price comparison
    c5, c6 = st.columns(2)
    with c5:
        arrivals_by_comm = merged_prices.groupby("commodity_name")["arrival_quantity"].sum().reset_index().sort_values("arrival_quantity", ascending=False).head(10)
        arrivals_by_comm["arrivals_MT"] = arrivals_by_comm["arrival_quantity"] / 1000.0
        fig_arr = create_bar_chart(arrivals_by_comm, "commodity_name", "arrivals_MT", title="5. Commodity Arrival Volume (Metric Tonnes)")
        st.plotly_chart(fig_arr, use_container_width=True)

    with c6:
        # Min, max, modal comparison
        sub_sample = merged_prices.head(15)
        fig_mmm = go.Figure()
        fig_mmm.add_trace(go.Bar(x=sub_sample["commodity_name"], y=sub_sample["minimum_price"], name="Min Price", marker_color="#94A3B8"))
        fig_mmm.add_trace(go.Bar(x=sub_sample["commodity_name"], y=sub_sample["modal_price"], name="Modal Price", marker_color=COLORS["secondary"]))
        fig_mmm.add_trace(go.Bar(x=sub_sample["commodity_name"], y=sub_sample["maximum_price"], name="Max Price", marker_color=COLORS["primary"]))
        fig_mmm.update_layout(barmode="group", title="6. Min, Modal & Max Price Comparison Band", **THEME_LAYOUT)
        st.plotly_chart(fig_mmm, use_container_width=True)

    # 7. Price distribution
    # 8. Seasonal price analysis & AI Projection
    c7, c8 = st.columns(2)
    with c7:
        fig_dist = px.histogram(merged_prices, x="modal_price", nbins=30, title="7. Mandi Modal Price Frequency Distribution (₹/kg)", color_discrete_sequence=[COLORS["primary"]])
        fig_dist.update_layout(**THEME_LAYOUT)
        st.plotly_chart(fig_dist, use_container_width=True)

    with c8:
        # AI Time-Series Projection for selected commodity
        target_comm_id = filtered_comms.iloc[0]["commodity_id"]
        hist_p, fc_p, fc_meta = forecast_commodity_price(prices_df, target_comm_id, horizon_days=14)
        
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(x=hist_p["date"], y=hist_p["modal_price"], name="Observed Modal", line={"color": COLORS["primary"], "width": 2}))
        fig_fc.add_trace(go.Scatter(x=fc_p["date"], y=fc_p["forecast_price"], name="14-Day Forecast", line={"color": COLORS["secondary"], "dash": "dash", "width": 2}))
        fig_fc.add_trace(go.Scatter(x=fc_p["date"], y=fc_p["upper_ci"], name="Upper 95% CI", line={"color": "#CBD5E1", "dash": "dot"}))
        fig_fc.add_trace(go.Scatter(x=fc_p["date"], y=fc_p["lower_ci"], name="Lower 95% CI", fill="tonexty", fillcolor="rgba(18, 184, 166, 0.12)", line={"color": "#CBD5E1", "dash": "dot"}))
        fig_fc.update_layout(title=f"8. AI Price Projection & Seasonal Curve ({fc_meta['trend_direction']})", **THEME_LAYOUT)
        st.plotly_chart(fig_fc, use_container_width=True)

if __name__ == "__main__":
    render()
else:
    render()
