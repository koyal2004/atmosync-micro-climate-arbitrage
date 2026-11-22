"""
AtmoSync - Market Arbitrage & Dynamic Rerouting Engine
Calculates spatial price differentials, transport and handling costs,
quality degradation impact, and net financial arbitrage benefit.

ACADEMIC DISCLAIMER:
All arbitrage opportunities are modeled from synthetic agricultural datasets
for demonstration and decision-support simulation. They do not represent
actual market trading positions or commercial recommendations.
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
    Evaluates market arbitrage opportunities across agricultural shipments.

    Transparent Formula Specification:
    1. Gross Price Advantage (₹/kg) = Destination Price - Source/Current Price
    2. Gross Advantage (₹) = Gross Price Advantage * Quantity (kg)
    3. Estimated Quality Loss Cost (₹) = Destination Price * Quantity * Estimated Quality Loss %
    4. Rerouting Logistics Cost (₹) = Detour Distance (km) * ₹22.50/km + Fixed Dispatch ₹850
    5. Terminal Handling Cost (₹) = Quantity (kg) * ₹0.40/kg
    6. Estimated Net Benefit (₹) = Gross Advantage - Transportation Cost - Handling Cost - Quality Loss Cost
       (Costs are non-overlapping and deducted strictly once)
    7. Profitable Opportunity: Estimated Net Benefit > 0
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

    # Compute average modal price per (commodity_id, market_id)
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
        active_ships = shipments_df.head(60)

    for _, ship in active_ships.iterrows():
        s_id = ship["shipment_id"]
        c_id = ship["commodity_id"]
        src_id = ship["source_market_id"]
        curr_dst_id = ship["destination_market_id"]
        qty = float(ship["quantity_kg"])

        c_meta = comm_lookup.get(c_id, {"commodity_name": "Commodity", "base_price_per_kg": 30.0})
        base_price = c_meta.get("base_price_per_kg", 30.0)

        # Baseline prices
        src_p = round(float(price_lookup.get((c_id, src_id), base_price * 0.95)), 2)
        curr_dst_p = round(float(price_lookup.get((c_id, curr_dst_id), base_price * 1.08)), 2)

        curr_dst_info = mkt_lookup.get(curr_dst_id, {"lat": 13.0, "lon": 80.0, "name": "Current Mandi", "state": "Tamil Nadu"})
        src_info = mkt_lookup.get(src_id, {"lat": 13.0, "lon": 80.0, "name": "Origin Mandi", "state": "Tamil Nadu"})

        # Quality loss from risk engine or status
        q_loss_pct = risk_lookup.get(s_id, 8.0 if ship["shipment_status"] == "At Risk" else 2.5)
        q_loss = round(min(0.60, float(q_loss_pct) / 100.0), 3)

        # Evaluate candidate destination markets
        candidate_mkts = np.random.choice(market_ids, size=min(12, len(market_ids)), replace=False)

        for alt_id in candidate_mkts:
            if alt_id in [src_id, curr_dst_id]:
                continue

            alt_info = mkt_lookup.get(alt_id)
            if not alt_info:
                continue

            alt_p = round(float(price_lookup.get((c_id, alt_id), base_price * np.random.uniform(0.95, 1.40))), 2)

            # Additional detour/rerouting distance from current destination to alternative
            reroute_dist = haversine_distance(curr_dst_info["lat"], curr_dst_info["lon"], alt_info["lat"], alt_info["lon"])
            addl_transport_cost = round(reroute_dist * 22.5 + 850.0, 2)
            addl_handling_cost = round(qty * 0.40, 2)

            # Transparent Calculation Formulas:
            # 1. Gross Price Advantage (₹/kg) relative to scheduled current destination
            gross_price_adv = round(alt_p - curr_dst_p, 2)
            # 2. Gross Advantage (₹)
            gross_advantage = round(gross_price_adv * qty, 2)

            # 3. Quality Loss Cost (₹)
            quality_loss_cost = round(alt_p * qty * q_loss, 2)

            # 4. Estimated Net Benefit (₹)
            # Net Benefit = Gross Advantage - Transport Cost - Handling Cost - Quality Loss Cost
            net_benefit = round(gross_advantage - addl_transport_cost - addl_handling_cost - quality_loss_cost, 2)

            # Profitability and Tier Assignment
            is_profitable = bool(net_benefit > 0)
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
                "source_market_name": src_info["name"],
                "source_state": src_info["state"],
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
                "estimated_quality_loss_cost": quality_loss_cost,
                "transportation_cost": addl_transport_cost,
                "handling_cost": addl_handling_cost,
                "gross_price_advantage": gross_price_adv,
                "gross_advantage": gross_advantage,
                "gross_market_advantage": gross_advantage,
                "estimated_net_benefit": net_benefit,
                "is_profitable": is_profitable,
                "profitability_label": "Profitable Opportunity" if is_profitable else "Unprofitable",
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
    Only includes positive net-benefit opportunities.
    """
    if arb_df.empty:
        return pd.DataFrame()

    # Filter strictly to positive net benefit opportunities
    profitable = arb_df[arb_df["estimated_net_benefit"] > 0]
    if profitable.empty:
        return pd.DataFrame()

    # For each shipment, find the highest net benefit opportunity
    ranked = profitable.sort_values(["shipment_id", "estimated_net_benefit"], ascending=[True, False])
    best_per_ship = ranked.groupby("shipment_id").first().reset_index()

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
