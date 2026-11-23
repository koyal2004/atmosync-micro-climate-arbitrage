"""
AtmoSync - Page 7: Market Arbitrage Intelligence
Smart Market Arbitrage & Dynamic Rerouting Engine: Rerouting at-risk freight, spatial price arbitrage,
margin breakdown waterfalls, and transparent net-benefit calculations.

ACADEMIC DISCLAIMER:
All market comparisons and arbitrage opportunities are simulated from synthetic datasets.
They do not represent real financial trading positions or actual trading recommendations.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from database.database import load_table
from utils.helpers import render_kpi_card, format_currency, format_quantity, get_status_badge
from utils.charts import (
    create_bar_chart, create_donut_chart, create_waterfall_chart,
    create_pydeck_route_map, THEME_LAYOUT
)
from modules.risk_engine import calculate_shipment_risk
from modules.arbitrage_engine import evaluate_arbitrage_opportunities, generate_recommendation_matrix
from config.settings import PERSISTENT_DISCLAIMER, COLORS, DATASET_LABEL


def render():
    st.markdown(
        '<div class="disclaimer-banner"><strong>Spatial Arbitrage Simulation:</strong> '
        + PERSISTENT_DISCLAIMER
        + "</div>",
        unsafe_allow_html=True,
    )
    st.title("Smart Market Arbitrage & Dynamic Rerouting")
    st.caption(
        f"Agricultural Price Disparities, Dynamic Rerouting Optimization & Transparent Margin Analysis • {DATASET_LABEL}"
    )

    try:
        shipments_df = load_table("shipments")
        commodities_df = load_table("commodities")
        markets_df = load_table("markets")
        prices_df = load_table("market_prices")
        sensor_df = load_table("sensor_readings")
    except Exception as e:
        st.error(f"⚠️ Failed to load database tables: {e}")
        return

    if shipments_df.empty or markets_df.empty or prices_df.empty:
        st.warning("Core datasets unavailable for arbitrage modeling. Please ensure database is populated.")
        return

    # Compute risk and evaluate full arbitrage matrix
    risk_df = calculate_shipment_risk(shipments_df, commodities_df, sensor_df)
    arb_df = evaluate_arbitrage_opportunities(shipments_df, commodities_df, markets_df, prices_df, risk_df)

    if arb_df.empty:
        st.info("No active freight shipments currently eligible for dynamic arbitrage analysis.")
        return

    # ------------------------------------------------------------------
    # Interactive Multi-Factor Filters (Sidebar)
    # ------------------------------------------------------------------
    st.sidebar.markdown("### 💡 Arbitrage Parameters & Filters")

    # 1. Commodity Selection
    all_commodities = ["All Commodities"] + sorted(arb_df["commodity_name"].dropna().unique().tolist())
    selected_comm = st.sidebar.selectbox("Commodity Selection", all_commodities, index=0, key="arb_comm_select")

    # 2. Source Market Selection
    all_sources = ["All Sources"] + sorted(arb_df["source_market_name"].dropna().unique().tolist())
    selected_source = st.sidebar.selectbox("Source Market Selection", all_sources, index=0, key="arb_src_select")

    # 3. Destination Market Comparison Filter
    all_dests = ["All Destinations"] + sorted(arb_df["alternative_market_name"].dropna().unique().tolist())
    selected_dest = st.sidebar.selectbox("Destination Market Comparison", all_dests, index=0, key="arb_dst_select")

    # 4. Profitability Filter
    profit_options = ["All Opportunities", "Only Profitable (Net Benefit > 0)", "Unprofitable Only (Net Benefit ≤ 0)"]
    selected_profit = st.sidebar.selectbox("Profitability Filter", profit_options, index=0, key="arb_profit_select")

    # Apply Filters
    filtered_arb = arb_df.copy()
    if selected_comm != "All Commodities":
        filtered_arb = filtered_arb[filtered_arb["commodity_name"] == selected_comm]
    if selected_source != "All Sources":
        filtered_arb = filtered_arb[filtered_arb["source_market_name"] == selected_source]
    if selected_dest != "All Destinations":
        filtered_arb = filtered_arb[filtered_arb["alternative_market_name"] == selected_dest]
    if selected_profit == "Only Profitable (Net Benefit > 0)":
        filtered_arb = filtered_arb[filtered_arb["is_profitable"] == True]
    elif selected_profit == "Unprofitable Only (Net Benefit ≤ 0)":
        filtered_arb = filtered_arb[filtered_arb["is_profitable"] == False]

    if filtered_arb.empty:
        st.warning("⚠️ No arbitrage opportunities match your selected filter criteria. Please broaden your selection.")
        return

    # ------------------------------------------------------------------
    # Transparent Calculation Assumptions & Methodology Expander
    # ------------------------------------------------------------------
    with st.expander("ℹ️ Transparent Arbitrage Calculation Methodology & Assumptions", expanded=False):
        st.markdown(r"""
        > **Important Academic Notice:** All values represent a simulated micro-climate decision-support model.
        > They do not constitute actual trading advice, commodity forward commitments, or guaranteed yields.

        ### Mathematical Formulation:
        1. **Gross Price Advantage ($\Delta P$):**
           $$\Delta P = P_{\text{alternative\_destination}} - P_{\text{current\_scheduled}}$$
        2. **Potential Gross Advantage ($G$):**
           $$G = \Delta P \times Q_{\text{kg}}$$
        3. **Quality Loss Cost ($C_{\text{quality}}$):**
           $$C_{\text{quality}} = P_{\text{alternative\_destination}} \times Q_{\text{kg}} \times L_{\text{quality\_loss\_pct}}$$
        4. **Additional Logistics Cost ($C_{\text{transport}}$):**
           $$C_{\text{transport}} = D_{\text{detour\_km}} \times ₹22.50/\text{km} + ₹850 \text{ (fixed dispatcher fee)}$$
        5. **Terminal Handling Cost ($C_{\text{handling}}$):**
           $$C_{\text{handling}} = Q_{\text{kg}} \times ₹0.40/\text{kg}$$
        6. **Estimated Net Benefit ($B_{\text{net}}$):**
           $$B_{\text{net}} = G - C_{\text{transport}} - C_{\text{handling}} - C_{\text{quality}}$$
           *Costs are strictly non-overlapping and deducted once.*
        7. **Profitability Condition:**
           Only opportunities where $B_{\text{net}} > 0$ are classified as **Profitable Opportunities**.
        """)

    # ------------------------------------------------------------------
    # Dynamic KPI Cards
    # ------------------------------------------------------------------
    st.markdown("#### 📌 Spatial Arbitrage & Financial Overview")
    st.caption("Metrics computed dynamically across the currently active shipment set.")

    total_opps = len(filtered_arb)
    profitable_opps = int((filtered_arb["is_profitable"] == True).sum())
    unprofitable_opps = total_opps - profitable_opps
    best_net_benefit = float(filtered_arb["estimated_net_benefit"].max()) if not filtered_arb.empty else 0.0
    highest_spread = float(filtered_arb["gross_price_advantage"].max()) if not filtered_arb.empty else 0.0
    potential_alt_mkts = filtered_arb[filtered_arb["is_profitable"] == True]["alternative_market_id"].nunique()

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(render_kpi_card("Total Scenarios", f"{total_opps:,}", f"{profitable_opps} profitable / {unprofitable_opps} loss", icon="📊"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Profitable Leads", f"{profitable_opps:,}", "Positive net yield", delta=f"{(profitable_opps / max(1, total_opps)) * 100:.1f}% yield rate", delta_color="positive" if profitable_opps > 0 else "normal", icon="💎"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Peak Price Spread", f"+₹{highest_spread:.2f}/kg", "Highest spatial premium", icon="📈"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("Top Net Benefit", format_currency(best_net_benefit), "Single shipment peak upside", delta="Actionable upside" if best_net_benefit > 0 else "Negative margin", delta_color="positive" if best_net_benefit > 0 else "negative", icon="🚀"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Viable Alt Mandis", f"{potential_alt_mkts}", "Profitable destination hubs", icon="🏛️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # Profitable vs Unprofitable Alert Notification
    # ------------------------------------------------------------------
    if profitable_opps == 0:
        st.warning("⚠️ No positive-net-benefit opportunity was identified for the current selection. All evaluated destination rerouting scenarios result in a negative net margin after transportation, handling, and quality degradation costs.")
    else:
        st.success(f"🟢 Identified {profitable_opps} potentially profitable arbitrage opportunities with net benefits up to {format_currency(best_net_benefit)}.")

    # ------------------------------------------------------------------
    # Automated Top Rerouting Recommendations Table
    # ------------------------------------------------------------------
    st.subheader("🎯 Top Profitable Rerouting Prescriptions")
    st.caption("Displays the single highest-yield alternative market per at-risk or active shipment (positive net benefit only).")

    recommendations = generate_recommendation_matrix(filtered_arb)

    if not recommendations.empty:
        rec_display = recommendations[[
            "shipment_id", "commodity_name", "source_market_name",
            "current_destination_name", "alternative_market_name",
            "quantity_kg", "source_market_price", "destination_market_price",
            "gross_advantage", "transportation_cost", "handling_cost",
            "estimated_quality_loss_cost", "estimated_net_benefit", "recommendation_reason"
        ]].copy()

        rec_display["quantity_kg"] = rec_display["quantity_kg"].apply(lambda q: f"{q:,.0f} kg")
        rec_display["source_market_price"] = "₹" + rec_display["source_market_price"].round(2).astype(str) + "/kg"
        rec_display["destination_market_price"] = "₹" + rec_display["destination_market_price"].round(2).astype(str) + "/kg"
        rec_display["gross_advantage"] = rec_display["gross_advantage"].apply(lambda x: format_currency(x))
        rec_display["transportation_cost"] = rec_display["transportation_cost"].apply(lambda x: format_currency(x))
        rec_display["handling_cost"] = rec_display["handling_cost"].apply(lambda x: format_currency(x))
        rec_display["estimated_quality_loss_cost"] = rec_display["estimated_quality_loss_cost"].apply(lambda x: format_currency(x))
        rec_display["estimated_net_benefit"] = rec_display["estimated_net_benefit"].apply(lambda x: format_currency(x))

        st.dataframe(
            rec_display.rename(columns={
                "shipment_id": "Shipment ID",
                "commodity_name": "Commodity",
                "source_market_name": "Source Market",
                "current_destination_name": "Scheduled Mandi",
                "alternative_market_name": "Alternative Mandi",
                "quantity_kg": "Quantity",
                "source_market_price": "Source Price",
                "destination_market_price": "Dest Price",
                "gross_advantage": "Gross Advantage",
                "transportation_cost": "Transport Cost",
                "handling_cost": "Handling Cost",
                "estimated_quality_loss_cost": "Quality Loss Cost",
                "estimated_net_benefit": "Estimated Net Benefit",
                "recommendation_reason": "Decision Rationale"
            }),
            use_container_width=True,
            height=260
        )
    else:
        st.info("No positive-net-benefit opportunity was identified among the filtered consignments.")

    # ------------------------------------------------------------------
    # Visual Analytics Suite (Plotly Charts)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📊 Arbitrage Visual Analytics Suite")

    if filtered_arb.empty:
        st.info("No records to visualize under current filter criteria.")
        return

    # Row 1: Source vs Destination Price Comparison & Gross Price Spread
    c1, c2 = st.columns(2)
    with c1:
        top_diff = filtered_arb.sort_values("gross_price_advantage", ascending=False).head(10)
        fig_src_dst = go.Figure()
        fig_src_dst.add_trace(go.Bar(
            x=top_diff["shipment_id"], y=top_diff["current_market_price"],
            name="Current Scheduled (₹/kg)", marker_color=COLORS["primary"]
        ))
        fig_src_dst.add_trace(go.Bar(
            x=top_diff["shipment_id"], y=top_diff["destination_market_price"],
            name="Alternative Mandi (₹/kg)", marker_color=COLORS["secondary"]
        ))
        fig_src_dst.update_layout(
            barmode="group",
            title="1. Current Destination vs. Alternative Mandi Price (₹/kg)",
            yaxis_title="Price (₹/kg)",
            **THEME_LAYOUT
        )
        st.plotly_chart(fig_src_dst, use_container_width=True)

    with c2:
        comm_spread = (
            filtered_arb.groupby("commodity_name")["gross_price_advantage"]
            .mean()
            .reset_index()
            .sort_values("gross_price_advantage", ascending=False)
            .head(10)
        )
        fig_diff = create_bar_chart(
            comm_spread, "commodity_name", "gross_price_advantage",
            title="2. Commodity Average Gross Price Spread (₹/kg)"
        )
        st.plotly_chart(fig_diff, use_container_width=True)

    # Row 2: Top Destination Mandis & Top Profit Opportunities
    c3, c4 = st.columns(2)
    with c3:
        top_mkts = (
            filtered_arb[filtered_arb["is_profitable"] == True]
            .groupby("alternative_market_name")["estimated_net_benefit"]
            .sum()
            .reset_index()
            .sort_values("estimated_net_benefit", ascending=False)
            .head(10)
        )
        if not top_mkts.empty:
            fig_top_m = create_bar_chart(
                top_mkts, "alternative_market_name", "estimated_net_benefit",
                title="3. Top Destination Mandis by Cumulative Net Gain (₹)"
            )
            st.plotly_chart(fig_top_m, use_container_width=True)
        else:
            st.info("No profitable destination markets to display in chart.")

    with c4:
        top_ships_ben = filtered_arb.sort_values("estimated_net_benefit", ascending=False).head(10)
        fig_ben_rank = create_bar_chart(
            top_ships_ben, "shipment_id", "estimated_net_benefit",
            color_col="profitability_label",
            color_map={"Profitable Opportunity": COLORS["success"], "Unprofitable": COLORS["critical"]},
            title="4. Top 10 Arbitrage Scenarios Ranked by Net Benefit (₹)"
        )
        st.plotly_chart(fig_ben_rank, use_container_width=True)

    # Row 3: Margin Waterfall Chart & Opportunity Classification
    c5, c6 = st.columns(2)
    with c5:
        best_single = filtered_arb.sort_values("estimated_net_benefit", ascending=False).iloc[0] if not filtered_arb.empty else None
        if best_single is not None:
            gross_adv_amt = best_single["gross_advantage"]
            qual_deduct = - best_single["estimated_quality_loss_cost"]
            logistics_deduct = - best_single["transportation_cost"]
            handling_deduct = - best_single["handling_cost"]
            net_amt = best_single["estimated_net_benefit"]

            waterfall_data = {
                "Potential Gross Advantage": gross_adv_amt,
                "Quality Stress Cost": qual_deduct,
                "Rerouting Logistics": logistics_deduct,
                "Terminal Handling": handling_deduct,
                "Estimated Net Benefit": net_amt
            }
            fig_wf = create_waterfall_chart(waterfall_data, title=f"5. Profit Margin Waterfall ({best_single['shipment_id']})")
            st.plotly_chart(fig_wf, use_container_width=True)
        else:
            st.info("No waterfall data available.")

    with c6:
        tier_colors = {
            "Profitable Opportunity": COLORS["success"],
            "Unprofitable": "#94A3B8"
        }
        fig_opp_donut = create_donut_chart(
            filtered_arb, "profitability_label",
            title="6. Profitable vs. Unprofitable Scenarios",
            color_map=tier_colors
        )
        st.plotly_chart(fig_opp_donut, use_container_width=True)

    # Row 4: Route Divergence Map
    st.markdown("#### 7. Dynamic Geospatial Corridor & Rerouting Divergence Map")
    if best_single is not None and "curr_latitude" in best_single:
        mkt_geo = markets_df.set_index("market_id").to_dict(orient="index")
        src_geo = mkt_geo.get(best_single["source_market_id"], {"latitude": 13.0827, "longitude": 80.2707, "market_name": "Origin"})

        reroute_deck = create_pydeck_route_map(
            source_lat=src_geo["latitude"], source_lon=src_geo["longitude"],
            dest_lat=best_single["curr_latitude"], dest_lon=best_single["curr_longitude"],
            source_name=src_geo["market_name"], dest_name=best_single["current_destination_name"],
            alt_lat=best_single["alt_latitude"], alt_lon=best_single["alt_longitude"],
            alt_name=best_single["alternative_market_name"]
        )
        st.pydeck_chart(reroute_deck)
        st.caption(
            f"Visualizing Corridor Divergence: Origin ({src_geo['market_name']}) ➔ Scheduled Destination ({best_single['current_destination_name']}) ➔ Alternative Mandi ({best_single['alternative_market_name']})."
        )

    # ------------------------------------------------------------------
    # Complete Underlying Manifest Table
    # ------------------------------------------------------------------
    with st.expander(f"📄 View All Evaluated Arbitrage Records ({len(filtered_arb):,} rows)"):
        st.dataframe(
            filtered_arb[[
                "opportunity_id", "shipment_id", "commodity_name",
                "source_market_name", "current_destination_name", "alternative_market_name",
                "quantity_kg", "source_market_price", "destination_market_price",
                "gross_advantage", "transportation_cost", "handling_cost",
                "estimated_quality_loss_cost", "estimated_net_benefit",
                "profitability_label", "recommendation_status"
            ]].rename(columns={
                "opportunity_id": "Opportunity ID",
                "shipment_id": "Shipment ID",
                "commodity_name": "Commodity",
                "source_market_name": "Source Market",
                "current_destination_name": "Scheduled Mandi",
                "alternative_market_name": "Alternative Mandi",
                "quantity_kg": "Quantity (kg)",
                "source_market_price": "Source Price (₹)",
                "destination_market_price": "Dest Price (₹)",
                "gross_advantage": "Gross Adv (₹)",
                "transportation_cost": "Transport (₹)",
                "handling_cost": "Handling (₹)",
                "estimated_quality_loss_cost": "Quality Loss (₹)",
                "estimated_net_benefit": "Net Benefit (₹)",
                "profitability_label": "Profitability",
                "recommendation_status": "Tier"
            }),
            use_container_width=True
        )


if __name__ == "__main__":
    render()
else:
    render()
