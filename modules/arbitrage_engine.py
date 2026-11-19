"""
AtmoSync - Market Arbitrage & Dynamic Rerouting Engine
Calculates price differentials, route deviations, quality-adjusted revenues,
and produces actionable rerouting recommendations for at-risk agricultural cargo.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from utils.helpers import haversine_distance

def evaluate_arbitrage_opportunities(
    shipments_df: pd.DataFrame,
    commodities_df: pd.DataFrame,
    markets_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    risk_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Evaluates arbitrage opportunities across all active or at-risk shipments.
    Calculates exact mathematical formulas specified in system architecture:
    1. Gross Price Advantage = Alt Destination Market Price - Current Destination Market Price
    2. Gross Market Advantage = Gross Price Advantage * Quantity
    3. Quality-Adjusted Alt Revenue = Alt Market Price * Quantity * (1 - Quality Loss)
    4. Current Revenue = Current Market Price * Quantity
    5. Net Benefit = Quality-Adjusted Alt Revenue - Current Revenue - Addl Transport - Addl Handling
    """
    if shipments_df.empty or markets_df.empty or prices_df.empty:
        return pd.DataFrame()

    # Create market coordinate lookup
    mkt_lookup = {row["market_id"]: {
        "name": row["market_name"],
        "lat": row["latitude"],
        "lon": row["longitude"],
        "state": row["state"]
    } for _, row in markets_df.iterrows()}

    # Compute latest or average modal price per (commodity_id, market_id)
    price_lookup = prices_df.groupby(["commodity_id", "market_id"])["modal_price"].mean().to_dict()

    # Pre-index commodity metadata
    comm_lookup = commodities_df.set_index("commodity_id").to_dict(orient="index")

    # Risk lookup for quality loss
    risk_lookup = {}
    if risk_df is not None and not risk_df.empty:
        risk_lookup = risk_df.set_index("shipment_id")["estimated_quality_loss_pct"].to_dict()

    records = []
    market_ids = list(mkt_lookup.keys())

    opp_id_counter = 1

    # Focus primarily on In Transit, At Risk, and Delayed shipments
    active_ships = shipments_df[shipments_df["shipment_status"].isin(["In Transit", "At Risk", "Delayed"])]
    if active_ships.empty:
        active_ships = shipments_df.head(50)

    for _, ship in active_ships.iterrows():
        s_id = ship["shipment_id"]
        c_id = ship["commodity_id"]
        src_id = ship["source_market_id"]
        curr_dst_id = ship["destination_market_id"]
        qty = float(ship["quantity_kg"])
        
        c_meta = comm_lookup.get(c_id, {"commodity_name": "Commodity", "base_price_per_kg": 30.0})
        base_price = c_meta.get("base_price_per_kg", 30.0)

        # Baseline prices
        src_p = price_lookup.get((c_id, src_id), base_price * 0.95)
        curr_dst_p = price_lookup.get((c_id, curr_dst_id), base_price * 1.08)

        curr_dst_info = mkt_lookup.get(curr_dst_id, {"lat": 13.0, "lon": 80.0, "name": "Current Mandi", "state": "Tamil Nadu"})

        # Quality loss from risk engine or status
        q_loss_pct = risk_lookup.get(s_id, 8.0 if ship["shipment_status"] == "At Risk" else 2.5)
        q_loss = min(0.60, q_loss_pct / 100.0)

        # Evaluate candidate destination markets
        # Pick 5-8 nearby or high-demand alternative markets
        candidate_mkts = np.random.choice(market_ids, size=min(12, len(market_ids)), replace=False)

        best_ship_opp = None
        max_ship_benefit = -999999.0

        for alt_id in candidate_mkts:
            if alt_id in [src_id, curr_dst_id]:
                continue
            
            alt_info = mkt_lookup.get(alt_id)
            if not alt_info:
                continue

            alt_p = price_lookup.get((c_id, alt_id), base_price * np.random.uniform(1.02, 1.40))
            
            # Additional detour/rerouting distance from current destination to alternative
            reroute_dist = haversine_distance(curr_dst_info["lat"], curr_dst_info["lon"], alt_info["lat"], alt_info["lon"])
            addl_transport_cost = round(reroute_dist * 22.5 + 850.0, 2)
            addl_handling_cost = round(qty * 0.40, 2)

            # Calculation
            gross_price_adv = round(alt_p - curr_dst_p, 2)
            gross_mkt_adv = round(gross_price_adv * qty, 2)

            alt_adj_rev = alt_p * qty * (1.0 - q_loss)
            curr_rev = curr_dst_p * qty
            net_benefit = round(alt_adj_rev - curr_rev - addl_transport_cost - addl_handling_cost, 2)

            if net_benefit > 35000:
                rec = "High Opportunity"
            elif net_benefit > 10000:
                rec = "Moderate Opportunity"
            elif net_benefit > 0:
                rec = "Low Opportunity"
            else:
                rec = "Not Recommended"

            entry = {
                "opportunity_id": f"ARB-{opp_id_counter:05d}",
                "shipment_id": s_id,
                "container_id": ship["container_id"],
                "commodity_id": c_id,
                "commodity_name": c_meta.get("commodity_name", "Commodity"),
                "shipment_status": ship["shipment_status"],
                "source_market_id": src_id,
                "source_market_name": mkt_lookup.get(src_id, {}).get("name", src_id),
                "destination_market_id": curr_dst_id,
                "current_destination_name": curr_dst_info["name"],
                "alternative_market_id": alt_id,
                "alternative_market_name": alt_info["name"],
                "alternative_state": alt_info["state"],
                "source_market_price": round(src_p, 2),
                "current_market_price": round(curr_dst_p, 2),
                "destination_market_price": round(alt_p, 2),
                "quantity_kg": qty,
                "estimated_quality_loss": round(q_loss, 3),
                "transportation_cost": addl_transport_cost,
                "handling_cost": addl_handling_cost,
                "gross_price_advantage": gross_price_adv,
                "gross_market_advantage": gross_mkt_adv,
                "estimated_net_benefit": net_benefit,
                "recommendation_status": rec,
                "alt_latitude": alt_info["lat"],
                "alt_longitude": alt_info["lon"],
                "curr_latitude": curr_dst_info["lat"],
                "curr_longitude": curr_dst_info["lon"]
            }
            records.append(entry)
            opp_id_counter += 1

    return pd.DataFrame(records)

def generate_recommendation_matrix(arb_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ranks alternative markets for at-risk and active shipments and returns top recommendations.
    """
    if arb_df.empty:
        return pd.DataFrame()

    # Filter to recommended opportunities with positive net benefit
    profitable = arb_df[arb_df["estimated_net_benefit"] > 0]
    if profitable.empty:
        return pd.DataFrame()

    # For each shipment, find the highest net benefit opportunity
    ranked = profitable.sort_values(["shipment_id", "estimated_net_benefit"], ascending=[True, False])
    best_per_ship = ranked.groupby("shipment_id").first().reset_index()

    # Add descriptive recommendation reasoning
    reasons = []
    for _, row in best_per_ship.iterrows():
        p_diff = row["gross_price_advantage"]
        net_b = row["estimated_net_benefit"]
        loss_pct = row["estimated_quality_loss"] * 100
        alt_mkt = row["alternative_market_name"]
        
        if row["shipment_status"] == "At Risk":
            reason = (f"Cargo at thermal risk (est. {loss_pct:.1f}% loss). Rerouting to {alt_mkt} "
                      f"captures +₹{p_diff:.2f}/kg premium, yielding estimated net gain of ₹{net_b:,.0f}.")
        else:
            reason = (f"Market arbitrage indicates {alt_mkt} is trading ₹{p_diff:.2f}/kg higher. "
                      f"Net gain ₹{net_b:,.0f} after ₹{row['transportation_cost']:,.0f} logistics.")
        reasons.append(reason)

    best_per_ship["recommendation_reason"] = reasons
    return best_per_ship.sort_values("estimated_net_benefit", ascending=False)
