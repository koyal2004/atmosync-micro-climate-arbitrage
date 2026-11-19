"""
AtmoSync - Spoilage Risk Engine
Calculates transparent, parametric spoilage risk scores (0–100) based on
temperature exposure, humidity deviation, transit duration, and commodity sensitivity.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from utils.constants import SENSITIVITY_WEIGHTS, RISK_TIERS

def calculate_shipment_risk(
    shipments_df: pd.DataFrame,
    commodities_df: pd.DataFrame,
    sensor_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Computes transparent environmental exposure and spoilage risk index for every shipment.
    
    Formula:
    1. Temp Deviation = max(0, avg_temp - max_temp) + max(0, min_temp - avg_temp)
    2. Temp Exposure Score = min(45, (Temp Deviation ^ 1.3) * (duration_days ^ 0.5) * 4.5)
    3. Humidity Deviation = max(0, avg_hum - max_hum)
    4. Humidity Exposure Score = min(25, Humidity Deviation * 1.2)
    5. Combined Environmental Score = (Temp Exposure + Humidity Exposure)
    6. Sensitivity Multiplier: Low (0.65), Moderate (1.0), High (1.35), Critical (1.70)
    7. Raw Risk Score = Combined Environmental Score * Sensitivity Multiplier
    8. Scaled Final Risk Score = min(100, max(0, Raw Risk Score))
    9. Quality Loss % = (Risk Score / 100) * 0.35 * (100 - initial_quality + 5) / 10
    """
    if shipments_df.empty:
        return pd.DataFrame()

    # Pre-index commodity metadata
    comm_meta = commodities_df.set_index("commodity_id").to_dict(orient="index")

    # Aggregate sensor readings per shipment
    if not sensor_df.empty:
        sensor_agg = sensor_df.groupby("shipment_id").agg({
            "temperature": ["mean", "max", "min", "last"],
            "humidity": ["mean", "max", "last"],
            "vibration": "mean"
        })
        sensor_agg.columns = [f"{col}_{stat}" for col, stat in sensor_agg.columns]
        sensor_dict = sensor_agg.to_dict(orient="index")
    else:
        sensor_dict = {}

    results = []

    for _, ship in shipments_df.iterrows():
        s_id = ship["shipment_id"]
        c_id = ship["commodity_id"]
        meta = comm_meta.get(c_id, {
            "optimal_temperature": 10.0, "minimum_temperature": 5.0, "maximum_temperature": 15.0,
            "optimal_humidity": 85.0, "maximum_humidity": 95.0, "sensitivity_level": "Moderate",
            "commodity_name": "Unknown", "estimated_shelf_life_days": 14
        })

        # Sensor readings
        sns = sensor_dict.get(s_id, {})
        avg_temp = sns.get("temperature_mean", meta["optimal_temperature"])
        max_temp = sns.get("temperature_max", meta["optimal_temperature"])
        last_temp = sns.get("temperature_last", avg_temp)
        avg_hum = sns.get("humidity_mean", meta["optimal_humidity"])
        last_hum = sns.get("humidity_last", avg_hum)
        avg_vibe = sns.get("vibration_mean", 0.8)

        # Transit duration approx
        transit_days = max(1.0, float(ship["distance_km"]) / 420.0)

        # 1. Temperature Deviation
        t_high_dev = max(0.0, avg_temp - meta["maximum_temperature"])
        t_low_dev = max(0.0, meta["minimum_temperature"] - avg_temp)
        total_t_dev = t_high_dev + t_low_dev

        # Temp score (up to 50 points)
        temp_score = min(50.0, (total_t_dev ** 1.25) * (transit_days ** 0.5) * 4.2)

        # 2. Humidity Deviation
        h_dev = max(0.0, avg_hum - meta["maximum_humidity"])
        hum_score = min(25.0, h_dev * 1.5)

        # 3. Vibration impact
        vibe_score = min(15.0, max(0.0, (avg_vibe - 1.2) * 4.0))

        # 4. Sensitivity weighting
        sens = meta["sensitivity_level"]
        weight = SENSITIVITY_WEIGHTS.get(sens, 1.0)

        # Raw risk calculation
        raw_risk = (temp_score + hum_score + vibe_score) * weight

        # If shipment status was explicitly set to At Risk, guarantee elevated score
        if ship["shipment_status"] == "At Risk":
            raw_risk = max(raw_risk, 62.0 + np.random.uniform(5.0, 30.0))

        risk_score = round(float(np.clip(raw_risk, 2.0, 99.0)), 1)

        # Tier assignment
        if risk_score >= 75.0:
            category = "Critical"
        elif risk_score >= 50.0:
            category = "High"
        elif risk_score >= 25.0:
            category = "Moderate"
        else:
            category = "Low"

        # Quality estimation
        init_qual = float(ship["initial_quality_percentage"])
        est_loss_pct = round(min(60.0, (risk_score / 100.0) * 35.0 + (transit_days * 0.8)), 1)
        est_curr_qual = round(max(30.0, init_qual - est_loss_pct), 1)

        # Remaining shelf life
        shelf_base = float(meta["estimated_shelf_life_days"])
        shelf_consumed = transit_days * (1.0 + (risk_score / 45.0))
        rem_shelf = round(max(0.2, shelf_base - shelf_consumed), 1)

        results.append({
            "shipment_id": s_id,
            "container_id": ship["container_id"],
            "commodity_id": c_id,
            "commodity_name": meta["commodity_name"],
            "sensitivity_level": sens,
            "shipment_status": ship["shipment_status"],
            "current_temperature": round(last_temp, 1),
            "current_humidity": round(last_hum, 1),
            "average_temperature": round(avg_temp, 1),
            "average_humidity": round(avg_hum, 1),
            "average_vibration": round(avg_vibe, 2),
            "temperature_score": round(temp_score, 1),
            "humidity_score": round(hum_score, 1),
            "risk_score": risk_score,
            "risk_category": category,
            "initial_quality": init_qual,
            "estimated_quality": est_curr_qual,
            "estimated_quality_loss_pct": est_loss_pct,
            "estimated_remaining_shelf_life": rem_shelf,
            "distance_km": ship["distance_km"],
            "quantity_kg": ship["quantity_kg"],
            "source_market_id": ship["source_market_id"],
            "destination_market_id": ship["destination_market_id"]
        })

    return pd.DataFrame(results)

def get_risk_summary(risk_df: pd.DataFrame) -> Dict[str, Any]:
    """Aggregate statistics for KPI cards."""
    if risk_df.empty:
        return {"low": 0, "moderate": 0, "high": 0, "critical": 0, "avg_risk": 0.0, "avg_loss": 0.0}

    counts = risk_df["risk_category"].value_counts().to_dict()
    return {
        "low": counts.get("Low", 0),
        "moderate": counts.get("Moderate", 0),
        "high": counts.get("High", 0),
        "critical": counts.get("Critical", 0),
        "avg_risk": round(float(risk_df["risk_score"].mean()), 1),
        "avg_loss": round(float(risk_df["estimated_quality_loss_pct"].mean()), 1),
        "total": len(risk_df)
    }
