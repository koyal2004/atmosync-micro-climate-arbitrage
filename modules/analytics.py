"""
AtmoSync - Advanced Analytics, Performance Metrics & Statistical Insights Engine
Computes dynamic operational insights, shipment performance analytics,
spoilage factor decompositions, and cross-market price spread matrices.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


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
                "text": f"Highest average modal price is commanded by {highest_name} at ₹{avg_prices.loc[highest_id, 'mean']:.2f}/kg, while {lowest_name} trades lowest at ₹{avg_prices.loc[lowest_id, 'mean']:.2f}/kg."
            })

            # Volatility
            valid_std = avg_prices[avg_prices["mean"] > 0]
            if not valid_std.empty:
                vol_id = (valid_std["std"] / valid_std["mean"]).idxmax()
                vol_name = comm_names.get(vol_id, vol_id)
                cv_pct = (valid_std.loc[vol_id, "std"] / valid_std.loc[vol_id, "mean"]) * 100.0
                insights.append({
                    "type": "Market Volatility",
                    "icon": "⚡",
                    "text": f"Greatest price dispersion occurs in {vol_name} with coefficient of variation {cv_pct:.1f}%, highlighting prime spatial price arbitrage conditions."
                })

    # 2. Environmental & Spoilage Stress
    if not sensor_df.empty:
        high_temp_count = int((sensor_df["sensor_status"] == "Critical").sum())
        mean_temp = float(sensor_df["temperature"].mean())
        max_temp = float(sensor_df["temperature"].max())
        insights.append({
            "type": "Micro-Climate Observation",
            "icon": "🌡️",
            "text": f"Fleet reefer chambers maintain a baseline average of {mean_temp:.1f}°C with a recorded peak of {max_temp:.1f}°C. {high_temp_count:,} telemetry packets violated critical temperature boundaries."
        })

    # 3. Arbitrage Highlights
    if not arb_df.empty:
        profitable_opps = arb_df[arb_df["is_profitable"] == True] if "is_profitable" in arb_df.columns else arb_df[arb_df["estimated_net_benefit"] > 0]
        if not profitable_opps.empty:
            best_opp = profitable_opps.sort_values("estimated_net_benefit", ascending=False).iloc[0]
            comm_name = best_opp.get("commodity_name", "Perishable Freight")
            alt_mkt = best_opp.get("alternative_market_name", "Alternative Mandi")
            gain_val = float(best_opp.get("estimated_net_benefit", 0.0))
            insights.append({
                "type": "Arbitrage Alpha",
                "icon": "💡",
                "text": f"Optimal rerouting prescription identified for shipment {best_opp.get('shipment_id', 'N/A')} ({comm_name}) diverted to {alt_mkt} with net recovery advantage of ₹{gain_val:,.2f}."
            })

    # 4. Fleet In Transit Status
    if not shipments_df.empty:
        at_risk = int((shipments_df["shipment_status"] == "At Risk").sum())
        in_transit = int((shipments_df["shipment_status"] == "In Transit").sum())
        insights.append({
            "type": "Transit Integrity",
            "icon": "🚚",
            "text": f"Currently {in_transit} shipments in active transit; {at_risk} containers are classified At Risk and prioritized for dynamic cold-chain intervention."
        })

    return insights


def compute_shipment_performance_analytics(shipments_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes fleet-wide shipment performance metrics:
    on-time delivery rate, delay rate, average cost per ton-km, and corridor volume.
    """
    if shipments_df.empty:
        return {
            "total_shipments": 0,
            "on_time_rate_pct": 0.0,
            "delay_rate_pct": 0.0,
            "at_risk_rate_pct": 0.0,
            "avg_cost_per_ton_km": 0.0,
            "avg_transit_distance_km": 0.0,
            "total_tonnage_mt": 0.0,
        }

    total = len(shipments_df)
    delivered = int((shipments_df["shipment_status"] == "Delivered").sum())
    delayed = int((shipments_df["shipment_status"] == "Delayed").sum())
    at_risk = int((shipments_df["shipment_status"] == "At Risk").sum())

    total_ton_km = (
        (shipments_df["quantity_kg"] / 1000.0) * shipments_df["distance_km"]
    ).sum()
    total_cost = shipments_df["transport_cost"].sum()
    avg_cost_per_ton_km = round(total_cost / max(1.0, total_ton_km), 2)

    return {
        "total_shipments": total,
        "on_time_rate_pct": round((delivered / max(1, total)) * 100.0, 1),
        "delay_rate_pct": round((delayed / max(1, total)) * 100.0, 1),
        "at_risk_rate_pct": round((at_risk / max(1, total)) * 100.0, 1),
        "avg_cost_per_ton_km": avg_cost_per_ton_km,
        "avg_transit_distance_km": round(float(shipments_df["distance_km"].mean()), 1),
        "total_tonnage_mt": round(float(shipments_df["quantity_kg"].sum()) / 1000.0, 1),
    }


def compute_spoilage_factor_breakdown(risk_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates the relative proportional contribution of temperature, humidity,
    and vibration stressors to total calculated risk across consignments.
    """
    if risk_df.empty or "temperature_score" not in risk_df.columns:
        return {
            "temp_contrib_pct": 0.0,
            "hum_contrib_pct": 0.0,
            "vibe_contrib_pct": 0.0,
            "primary_stressor": "None",
            "mean_temp_score": 0.0,
            "mean_hum_score": 0.0,
            "mean_vibe_score": 0.0
        }

    mean_temp = float(risk_df["temperature_score"].mean())
    mean_hum = float(risk_df["humidity_score"].mean())
    mean_vibe = float(risk_df["vibration_score"].mean())
    total_stress = max(0.01, mean_temp + mean_hum + mean_vibe)

    temp_pct = round((mean_temp / total_stress) * 100.0, 1)
    hum_pct = round((mean_hum / total_stress) * 100.0, 1)
    vibe_pct = round((mean_vibe / total_stress) * 100.0, 1)

    if mean_temp >= mean_hum and mean_temp >= mean_vibe:
        primary = "Temperature Excursion"
    elif mean_hum >= mean_vibe:
        primary = "Relative Humidity Condensation"
    else:
        primary = "Mechanical Vibration & Shock"

    return {
        "temp_contrib_pct": temp_pct,
        "hum_contrib_pct": hum_pct,
        "vibe_contrib_pct": vibe_pct,
        "primary_stressor": primary,
        "mean_temp_score": round(mean_temp, 1),
        "mean_hum_score": round(mean_hum, 1),
        "mean_vibe_score": round(mean_vibe, 1)
    }


def compute_weather_shipment_relationship(
    sensor_df: pd.DataFrame,
    shipments_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Aggregates micro-climate environmental telemetry by shipment operational status
    to evaluate the direct correlation between container atmosphere and transit health.
    """
    if sensor_df.empty or shipments_df.empty:
        return pd.DataFrame()

    merged = sensor_df.merge(
        shipments_df[["shipment_id", "shipment_status", "distance_km"]],
        on="shipment_id",
        how="inner"
    )

    if merged.empty:
        return pd.DataFrame()

    agg_df = merged.groupby("shipment_status").agg({
        "temperature": ["mean", "max"],
        "humidity": ["mean", "max"],
        "vibration": ["mean", "max"],
        "sensor_id": "count"
    }).reset_index()

    agg_df.columns = [
        "shipment_status", "avg_temperature", "max_temperature",
        "avg_humidity", "max_humidity", "avg_vibration", "max_vibration", "reading_count"
    ]

    for col in ["avg_temperature", "max_temperature", "avg_humidity", "max_humidity", "avg_vibration", "max_vibration"]:
        agg_df[col] = agg_df[col].round(2)

    return agg_df
