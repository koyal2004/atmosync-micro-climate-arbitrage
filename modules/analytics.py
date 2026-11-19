"""
AtmoSync - General Analytics & Automated Insights Engine
Produces dynamic data insights, statistical aggregates,
and cross-market comparisons without hardcoding.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

def generate_automated_insights(
    prices_df: pd.DataFrame,
    shipments_df: pd.DataFrame,
    sensor_df: pd.DataFrame,
    arb_df: pd.DataFrame,
    comm_df: pd.DataFrame
) -> List[Dict[str, str]]:
    """
    Computes key data-driven natural language findings directly from the live datasets.
    """
    insights = []

    # 1. Price extremes & volatility
    if not prices_df.empty and not comm_df.empty:
        comm_names = dict(zip(comm_df["commodity_id"], comm_df["commodity_name"]))
        avg_prices = prices_df.groupby("commodity_id")["modal_price"].agg(["mean", "std", "min", "max"])
        
        if not avg_prices.empty:
            highest_id = avg_prices["mean"].idxmax()
            lowest_id = avg_prices["mean"].idxmin()
            highest_name = comm_names.get(highest_id, highest_id)
            lowest_name = comm_names.get(lowest_id, lowest_id)
            
            insights.append({
                "type": "Price Leadership",
                "icon": "📈",
                "text": f"Highest average modal price is recorded by {highest_name} at ₹{avg_prices.loc[highest_id, 'mean']:.2f}/kg, while {lowest_name} trades lowest at ₹{avg_prices.loc[lowest_id, 'mean']:.2f}/kg."
            })

            # Volatility
            vol_id = (avg_prices["std"] / avg_prices["mean"]).idxmax()
            vol_name = comm_names.get(vol_id, vol_id)
            insights.append({
                "type": "Market Volatility",
                "icon": "⚡",
                "text": f"Greatest price dispersion occurs in {vol_name} with coefficient of variation {((avg_prices.loc[vol_id, 'std']/avg_prices.loc[vol_id, 'mean'])*100):.1f}%, indicating localized arbitrage potential."
            })

    # 2. Environmental & Spoilage Stress
    if not sensor_df.empty:
        high_temp_count = int((sensor_df["sensor_status"] == "Critical").sum())
        mean_temp = float(sensor_df["temperature"].mean())
        max_temp = float(sensor_df["temperature"].max())
        insights.append({
            "type": "Micro-Climate Observation",
            "icon": "🌡️",
            "text": f"Fleet containers average {mean_temp:.1f}°C with a recorded peak of {max_temp:.1f}°C. {high_temp_count} sensor readings violated critical reefer thermal boundaries."
        })

    # 3. Arbitrage Highlights
    if not arb_df.empty:
        high_opps = arb_df[arb_df["recommendation_status"] == "High Opportunity"]
        if not high_opps.empty:
            best_opp = high_opps.sort_values("estimated_net_benefit", ascending=False).iloc[0]
            insights.append({
                "type": "Arbitrage Alpha",
                "icon": "💡",
                "text": f"Maximum rerouting net benefit identified for shipment {best_opp['shipment_id']} ({best_opp['commodity_name']}) diverted to {best_opp['alternative_market_name']} with estimated gain of ₹{best_opp['estimated_net_benefit']:,.2f}."
            })

    # 4. Fleet In Transit Status
    if not shipments_df.empty:
        at_risk = int((shipments_df["shipment_status"] == "At Risk").sum())
        in_transit = int((shipments_df["shipment_status"] == "In Transit").sum())
        insights.append({
            "type": "Transit Integrity",
            "icon": "🚚",
            "text": f"Currently {in_transit} shipments in active transit; {at_risk} containers are classified At Risk and prioritized for dynamic route intervention."
        })

    return insights
