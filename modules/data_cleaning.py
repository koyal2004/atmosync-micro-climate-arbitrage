"""
AtmoSync - Data Cleaning & Validation Suite
Audits referential integrity, schema constraints, range violations,
null values, duplicate keys, and generates an enterprise audit report.
"""

import pandas as pd
from typing import Dict, Any, List

def run_comprehensive_validation(datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Validates all tables across foreign keys, null checks, duplicates,
    numeric validity, and domain ranges.
    Returns a structured audit report dictionary.
    """
    comm_df = datasets.get("commodities", pd.DataFrame())
    mkt_df = datasets.get("markets", pd.DataFrame())
    price_df = datasets.get("market_prices", pd.DataFrame())
    ship_df = datasets.get("shipments", pd.DataFrame())
    sensor_df = datasets.get("sensor_readings", pd.DataFrame())
    arb_df = datasets.get("arbitrage_opportunities", pd.DataFrame())
    alerts_df = datasets.get("alerts", pd.DataFrame())

    results = {
        "is_valid": True,
        "table_summaries": {},
        "foreign_key_violations": 0,
        "null_value_counts": 0,
        "duplicate_counts": 0,
        "range_violations": 0,
        "details": []
    }

    # Helper: Check duplicates and nulls
    for name, df in datasets.items():
        if df.empty:
            continue
        null_count = int(df.isnull().sum().sum())
        # Check primary key duplication
        pk_col = df.columns[0]
        dup_count = int(df.duplicated(subset=[pk_col]).sum())
        
        results["null_value_counts"] += null_count
        results["duplicate_counts"] += dup_count
        
        results["table_summaries"][name] = {
            "record_count": len(df),
            "columns": list(df.columns),
            "null_cells": null_count,
            "duplicate_pks": dup_count
        }

    # Foreign Key Audits
    valid_comm_ids = set(comm_df["commodity_id"]) if not comm_df.empty else set()
    valid_mkt_ids = set(mkt_df["market_id"]) if not mkt_df.empty else set()
    valid_ship_ids = set(ship_df["shipment_id"]) if not ship_df.empty else set()

    # Price -> Comm & Market
    if not price_df.empty:
        invalid_comm = (~price_df["commodity_id"].isin(valid_comm_ids)).sum()
        invalid_mkt = (~price_df["market_id"].isin(valid_mkt_ids)).sum()
        if invalid_comm > 0 or invalid_mkt > 0:
            results["foreign_key_violations"] += (invalid_comm + invalid_mkt)
            results["details"].append(f"Market prices have {invalid_comm} invalid comm IDs and {invalid_mkt} invalid mkt IDs.")

        # Price consistency: min <= modal <= max
        price_inv = (price_df["minimum_price"] > price_df["modal_price"]) | (price_df["modal_price"] > price_df["maximum_price"])
        inv_count = int(price_inv.sum())
        if inv_count > 0:
            results["range_violations"] += inv_count
            results["details"].append(f"{inv_count} price records violate min <= modal <= max constraint.")

    # Shipment -> Comm & Markets
    if not ship_df.empty:
        inv_ship_comm = (~ship_df["commodity_id"].isin(valid_comm_ids)).sum()
        inv_ship_src = (~ship_df["source_market_id"].isin(valid_mkt_ids)).sum()
        inv_ship_dst = (~ship_df["destination_market_id"].isin(valid_mkt_ids)).sum()
        total_ship_fk = inv_ship_comm + inv_ship_src + inv_ship_dst
        if total_ship_fk > 0:
            results["foreign_key_violations"] += total_ship_fk
            results["details"].append(f"Shipments have {total_ship_fk} foreign key violations.")

        # Quantities must be > 0
        inv_qty = (ship_df["quantity_kg"] <= 0).sum()
        if inv_qty > 0:
            results["range_violations"] += int(inv_qty)
            results["details"].append(f"{inv_qty} shipments have non-positive quantities.")

    # Sensors -> Shipments
    if not sensor_df.empty:
        inv_sns_ship = (~sensor_df["shipment_id"].isin(valid_ship_ids)).sum()
        if inv_sns_ship > 0:
            results["foreign_key_violations"] += int(inv_sns_ship)
            results["details"].append(f"Sensors have {inv_sns_ship} unlinked shipment IDs.")
            
        # Temperature & Humidity range check
        extreme_temp = ((sensor_df["temperature"] < -30) | (sensor_df["temperature"] > 70)).sum()
        extreme_hum = ((sensor_df["humidity"] < 0) | (sensor_df["humidity"] > 100)).sum()
        if extreme_temp > 0 or extreme_hum > 0:
            results["range_violations"] += int(extreme_temp + extreme_hum)
            results["details"].append(f"Sensors have extreme readings: {extreme_temp} temp / {extreme_hum} humidity.")

    # Arbitrage -> Shipments & Markets
    if not arb_df.empty:
        inv_arb_ship = (~arb_df["shipment_id"].isin(valid_ship_ids)).sum()
        if inv_arb_ship > 0:
            results["foreign_key_violations"] += int(inv_arb_ship)
            results["details"].append(f"Arbitrage has {inv_arb_ship} unlinked shipment IDs.")

    total_issues = (results["foreign_key_violations"] + 
                    results["null_value_counts"] + 
                    results["duplicate_counts"] + 
                    results["range_violations"])
    results["is_valid"] = (total_issues == 0)
    results["total_records"] = sum(s["record_count"] for s in results["table_summaries"].values())
    results["completeness_pct"] = 100.0 if total_issues == 0 else round(100.0 - (total_issues / max(1, results["total_records"])) * 100, 2)

    return results

def get_data_quality_dataframe(report: Dict[str, Any]) -> pd.DataFrame:
    """Format validation summary as a displayable DataFrame."""
    rows = []
    for table_name, summary in report.get("table_summaries", {}).items():
        rows.append({
            "Dataset Table": table_name.replace("_", " ").title(),
            "Total Records": f"{summary['record_count']:,}",
            "Attributes (Cols)": len(summary["columns"]),
            "Missing Values": summary["null_cells"],
            "Duplicate PKs": summary["duplicate_pks"],
            "Integrity Status": "PASS" if (summary["null_cells"] == 0 and summary["duplicate_pks"] == 0) else "FAIL"
        })
    return pd.DataFrame(rows)
