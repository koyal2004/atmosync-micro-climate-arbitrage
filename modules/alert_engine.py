"""
AtmoSync - Alert Notification Engine
Processes sensor events and supply chain anomalies into actionable alerts.
Supports New, Acknowledged, and Resolved state transitions.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from database.database import get_alerts, update_alert_status, insert_alert

ALERT_TYPES = [
    "High Temperature",
    "High Humidity",
    "Abnormal Vibration",
    "High Spoilage Risk",
    "Shipment Delay",
    "Potential Arbitrage Opportunity"
]

def fetch_active_alerts(status_filter: str = "All") -> pd.DataFrame:
    """Retrieve alerts filtered by status."""
    return get_alerts(status_filter)

def acknowledge_alert(alert_id: str):
    """Mark an alert as Acknowledged."""
    update_alert_status(alert_id, "Acknowledged")

def resolve_alert(alert_id: str):
    """Mark an alert as Resolved."""
    update_alert_status(alert_id, "Resolved")

def trigger_manual_alert(shipment_id: str, container_id: str, alert_type: str, severity: str, description: str):
    """Creates a new operational alert and saves to SQLite."""
    alert_dict = {
        "alert_id": f"ALT-{int(datetime.now().timestamp()*1000)%1000000:06d}",
        "shipment_id": shipment_id,
        "container_id": container_id,
        "alert_type": alert_type,
        "severity": severity,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "status": "New"
    }
    insert_alert(alert_dict)
