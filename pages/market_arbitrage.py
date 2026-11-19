"""
AtmoSync - Page 7: Market Arbitrage Intelligence
Smart Market Arbitrage & Dynamic Rerouting Engine: Rerouting at-risk freight, spatial price arbitrage, and profit waterfall analytics.
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
from config.settings import PERSISTENT_DISCLAIMER, COLORS, OPPORTUNITY_TIERS

def render():
    st.markdown('<div class="disclaimer-banner"><strong>Spatial Arbitrage Simulation:</strong> ' + PERSISTENT_DISCLAIMER + '</div>', unsafe_allow_html=True)
    st.title("Smart Market Arbitrage & Dynamic Rerouting")
    st.caption("Agricultural Price Disparities, Dynamic Rerouting Optimization & Cold-Chain Margin Preservation")

    shipments_df = load_table("shipments")
    commodities_df = load_table("commodities")
    markets_df = load_table("markets")
    prices_df = load_table("market_prices")
    sensor_df = load_table("sensor_readings")

    if shipments_df.empty or markets_df.empty or prices_df.empty:
        st.warning("Core datasets unavailable for arbitrage modeling.")
        return

    # Compute risk and evaluate full arbitrage matrix
    risk_df = calculate_shipment_risk(shipments_df, commodities_df, sensor_df)
    arb_df = evaluate_arbitrage_opportunities(shipments_df, commodities_df, markets_df, prices_df, risk_df)

    if arb_df.empty:
        st.info("No active freight shipments currently eligible for dynamic arbitrage analysis.")
        return

    # Filter controls in sidebar
    st.sidebar.markdown("### 💡 Arbitrage Parameters")
    opp_filter = st.sidebar.selectbox("Opportunity Classification", ["All", "High Opportunity", "Moderate Opportunity", "Low Opportunity", "Not Recommended"])
    
    # Calculate KPIs (Section 12)
    total_opps = len(arb_df[arb_df["recommendation_status"].isin(["High Opportunity", "Moderate Opportunity", "Low Opportunity"])])
    highest_price_adv = float(arb_df["gross_price_advantage"].max())
    best_net_benefit = float(arb_df["estimated_net_benefit"].max())
    at_risk_shipments_count = int((shipments_df["shipment_status"] == "At Risk").sum())
    potential_alt_mkts = arb_df[arb_df["estimated_net_benefit"] > 0]["alternative_market_id"].nunique()

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(render_kpi_card("Total Opportunities", f"{total_opps:,}", "Positive net yield", icon="💎"), unsafe_allow_html=True)
    with k2:
        st.markdown(render_kpi_card("Highest Price Spread", f"+₹{highest_price_adv:.2f}/kg", "Peak mandi premium", icon="📈"), unsafe_allow_html=True)
    with k3:
        st.markdown(render_kpi_card("Best Net Benefit", format_currency(best_net_benefit), "Single shipment upside", delta=f"{format_currency(best_net_benefit)} alpha", delta_color="positive", icon="🚀"), unsafe_allow_html=True)
    with k4:
        st.markdown(render_kpi_card("At-Risk Shipments", f"{at_risk_shipments_count:,}", "Candidates for diversion", delta="Priority intervention", delta_color="negative", icon="🚨"), unsafe_allow_html=True)
    with k5:
        st.markdown(render_kpi_card("Alternative Mandis", f"{potential_alt_mkts}", "Viable destination hubs", icon="🏛️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Dynamic Recommendation Engine for At-Risk and Active Shipments
    st.subheader("🎯 Automated Rerouting Recommendation Engine")
    st.markdown("Prescribe dynamic route diversions to alternative terminal mandis before cargo reaches critical spoilage thresholds.")

    recommendations = generate_recommendation_matrix(arb_df)

    if not recommendations.empty:
        rec_display = recommendations[[
            "shipment_id", "commodity_name", "current_destination_name", "alternative_market_name",
            "current_market_price", "destination_market_price", "estimated_quality_loss",
            "transportation_cost", "estimated_net_benefit", "recommendation_reason"
        ]].copy()
        
        rec_display["estimated_quality_loss"] = (rec_display["estimated_quality_loss"] * 100).round(1).astype(str) + " %"
        rec_display["current_market_price"] = "₹" + rec_display["current_market_price"].round(2).astype(str) + "/kg"
        rec_display["destination_market_price"] = "₹" + rec_display["destination_market_price"].round(2).astype(str) + "/kg"
        rec_display["transportation_cost"] = rec_display["transportation_cost"].apply(lambda x: format_currency(x))
        rec_display["estimated_net_benefit"] = rec_display["estimated_net_benefit"].apply(lambda x: format_currency(x))

        rec_display = rec_display.rename(columns={
            "shipment_id": "Shipment ID",
            "commodity_name": "Commodity",
            "current_destination_name": "Current Destination",
            "alternative_market_name": "Recommended Alternative",
            "current_market_price": "Current Price",
            "destination_market_price": "Alt Market Price",
            "estimated_quality_loss": "Est Quality Loss",
            "transportation_cost": "Additional Transport",
            "estimated_net_benefit": "Est Net Benefit",
            "recommendation_reason": "Decision Rationale"
        })
        st.dataframe(rec_display, use_container_width=True, height=280)
    else:
        st.warning("No Profitable Alternative Market Identified for current active shipments.")

    st.markdown("---")
    st.subheader("📊 Arbitrage Visual Analytics Suite (7 Core Charts)")

    filtered_arb = arb_df.copy()
    if opp_filter != "All":
        filtered_arb = filtered_arb[filtered_arb["recommendation_status"] == opp_filter]

    # 1. Source versus destination market comparison
    # 2. Commodity price differences
    c1, c2 = st.columns(2)
    with c1:
        top_diff = filtered_arb.sort_values("gross_price_advantage", ascending=False).head(10)
        fig_src_dst = go.Figure()
        fig_src_dst.add_trace(go.Bar(x=top_diff["shipment_id"], y=top_diff["current_market_price"], name="Current Dest Price (₹/kg)", marker_color=COLORS["primary"]))
        fig_src_dst.add_trace(go.Bar(x=top_diff["shipment_id"], y=top_diff["destination_market_price"], name="Alt Mandi Price (₹/kg)", marker_color=COLORS["secondary"]))
        fig_src_dst.update_layout(barmode="group", title="1. Current Destination vs. Alternative Mandi Price (₹/kg)", **THEME_LAYOUT)
        st.plotly_chart(fig_src_dst, use_container_width=True)

    with c2:
        comm_spread = filtered_arb.groupby("commodity_name")["gross_price_advantage"].mean().reset_index().sort_values("gross_price_advantage", ascending=False).head(10)
        fig_diff = create_bar_chart(comm_spread, "commodity_name", "gross_price_advantage", title="2. Commodity Gross Spatial Price Spread (+₹/kg)")
        st.plotly_chart(fig_diff, use_container_width=True)

    # 3. Top 10 market opportunities
    # 4. Potential financial benefit ranking
    c3, c4 = st.columns(2)
    with c3:
        top_mkts = filtered_arb.groupby("alternative_market_name")["estimated_net_benefit"].sum().reset_index().sort_values("estimated_net_benefit", ascending=False).head(10)
        fig_top_m = create_bar_chart(top_mkts, "alternative_market_name", "estimated_net_benefit", title="3. Top 10 Destination Mandis by Cumulative Net Gain (₹)")
        st.plotly_chart(fig_top_m, use_container_width=True)

    with c4:
        top_ships_ben = filtered_arb.sort_values("estimated_net_benefit", ascending=False).head(10)
        fig_ben_rank = create_bar_chart(top_ships_ben, "shipment_id", "estimated_net_benefit", color_col="recommendation_status", title="4. Top 10 Consignment Arbitrage Profit Realizations (₹)")
        st.plotly_chart(fig_ben_rank, use_container_width=True)

    # 5. Arbitrage Waterfall Chart
    # 6. Market opportunity distribution
    c5, c6 = st.columns(2)
    with c5:
        # Construct representative waterfall for best opportunity
        best_single = filtered_arb.sort_values("estimated_net_benefit", ascending=False).iloc[0] if not filtered_arb.empty else None
        if best_single is not None:
            gross_mkt_rev = best_single["destination_market_price"] * best_single["quantity_kg"]
            qual_deduct = - (gross_mkt_rev * best_single["estimated_quality_loss"])
            logistics_deduct = - best_single["transportation_cost"]
            handling_deduct = - best_single["handling_cost"]
            curr_rev_base = - (best_single["current_market_price"] * best_single["quantity_kg"])

            waterfall_data = {
                "Alt Gross Rev": gross_mkt_rev,
                "Quality Stress Loss": qual_deduct,
                "Rerouting Freight": logistics_deduct,
                "Terminal Handling": handling_deduct,
                "Baseline Current Rev": curr_rev_base,
                "Net Arbitrage Margin": best_single["estimated_net_benefit"]
            }
            fig_wf = create_waterfall_chart(waterfall_data, title=f"5. Margin Waterfall ({best_single['shipment_id']})")
            st.plotly_chart(fig_wf, use_container_width=True)
        else:
            st.info("No waterfall available.")

    with c6:
        tier_colors = {"High Opportunity": COLORS["success"], "Moderate Opportunity": COLORS["secondary"], "Low Opportunity": COLORS["warning"], "Not Recommended": "#94A3B8"}
        fig_opp_donut = create_donut_chart(arb_df, "recommendation_status", title="6. Arbitrage Opportunity Tier Classification", color_map=tier_colors)
        st.plotly_chart(fig_opp_donut, use_container_width=True)

    # 7. Source and alternative market map
    st.markdown("#### 7. Dynamic Geospatial Corridor & Rerouting Divergence Map")
    if best_single is not None and "curr_latitude" in best_single:
        # Render route with PyDeck
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
        st.caption(f"Visualizing Corridor Divergence: Origin ({src_geo['market_name']}) ➔ Scheduled Destination ({best_single['current_destination_name']}) ➔ Recommended Arbitrage Target ({best_single['alternative_market_name']}).")

if __name__ == "__main__":
    render()
else:
    render()
