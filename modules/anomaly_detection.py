"""
AtmoSync - Anomaly Detection Engine
Unsupervised machine learning model using Isolation Forest
to flag environmental deviations (temperature, humidity, vibration).
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Tuple, Dict, Any

def run_sensor_anomaly_detection(sensor_df: pd.DataFrame, contamination: float = 0.05) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Fits an Isolation Forest on temperature, humidity, and vibration features.
    Flags readings as 'Normal' or 'Anomaly' (academic demonstration).
    """
    if sensor_df.empty or len(sensor_df) < 20:
        df_copy = sensor_df.copy()
        df_copy["ml_anomaly_label"] = "Normal"
        df_copy["anomaly_score"] = 0.0
        return df_copy, {"total_anomalies": 0, "anomaly_rate": 0.0, "status": "Insufficient data"}

    features = ["temperature", "humidity", "vibration"]
    # Handle any nulls safely
    X = sensor_df[features].fillna(sensor_df[features].mean()).values

    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    
    preds = model.fit_predict(X)
    scores = model.decision_function(X) # Lower scores indicate higher anomaly tendency

    df_result = sensor_df.copy()
    df_result["ml_anomaly_label"] = np.where(preds == -1, "Anomaly", "Normal")
    df_result["anomaly_score"] = np.round(-scores, 3) # Higher = more anomalous

    anomaly_count = int((preds == -1).sum())
    total_count = len(df_result)
    rate = round((anomaly_count / total_count) * 100, 2)

    summary = {
        "total_anomalies": anomaly_count,
        "total_records": total_count,
        "anomaly_rate": rate,
        "mean_temp_anomaly": round(float(df_result[df_result["ml_anomaly_label"] == "Anomaly"]["temperature"].mean()), 2) if anomaly_count > 0 else 0.0,
        "mean_temp_normal": round(float(df_result[df_result["ml_anomaly_label"] == "Normal"]["temperature"].mean()), 2) if (total_count - anomaly_count) > 0 else 0.0,
        "mean_vibe_anomaly": round(float(df_result[df_result["ml_anomaly_label"] == "Anomaly"]["vibration"].mean()), 2) if anomaly_count > 0 else 0.0,
        "mean_vibe_normal": round(float(df_result[df_result["ml_anomaly_label"] == "Normal"]["vibration"].mean()), 2) if (total_count - anomaly_count) > 0 else 0.0,
        "status": "Trained and Evaluated Successfully"
    }

    return df_result, summary
