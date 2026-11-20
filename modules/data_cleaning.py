"""
AtmoSync - Data Cleaning & Validation Suite
Audits referential integrity, schema constraints, range violations,
null values, duplicate keys, and preprocesses/cleans synthetic datasets.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger("atmosync.data_cleaning")

def clean_dataset(
    table_name: str,
    df: pd.DataFrame,
    reference_data: Optional[Dict[str, pd.DataFrame]] = None
) -> pd.DataFrame:
    """
    Preprocess and clean a single dataset table.
    Enforces non-null primary keys, removes duplicate IDs, corrects range anomalies,
    and applies synthetic provenance labels.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    cleaned = df.copy()

    # 1. Deduplicate by primary key
    pk_map = {
        "commodities": "commodity_id",
        "markets": "market_id",
        "market_prices": "price_id",
        "shipments": "shipment_id",
        "sensor_readings": "sensor_id",
        "arbitrage_opportunities": "opportunity_id",
        "alerts": "alert_id"
    }
    pk = pk_map.get(table_name)
    if pk and pk in cleaned.columns:
        # Drop rows where primary key is null
        cleaned = cleaned.dropna(subset=[pk])
        # Drop duplicate primary keys, keeping first
        cleaned = cleaned.drop_duplicates(subset=[pk], keep="first")

    # 2. Table-specific domain rules and validations
    if table_name == "commodities":
        # Ensure positive prices and valid temperature/humidity bounds
        cleaned["base_price_per_kg"] = cleaned["base_price_per_kg"].apply(lambda x: max(1.0, float(x)))
        cleaned["optimal_temperature"] = cleaned["optimal_temperature"].astype(float)
        cleaned["minimum_temperature"] = cleaned["minimum_temperature"].astype(float)
        cleaned["maximum_temperature"] = cleaned["maximum_temperature"].astype(float)
        # Ensure min <= opt <= max
        cleaned["minimum_temperature"] = np.minimum(cleaned["minimum_temperature"], cleaned["optimal_temperature"])
        cleaned["maximum_temperature"] = np.maximum(cleaned["maximum_temperature"], cleaned["optimal_temperature"])
        cleaned["optimal_humidity"] = cleaned["optimal_humidity"].clip(10.0, 99.0)
        cleaned["maximum_humidity"] = np.maximum(cleaned["maximum_humidity"], cleaned["optimal_humidity"]).clip(10.0, 100.0)
        cleaned["estimated_shelf_life_days"] = cleaned["estimated_shelf_life_days"].apply(lambda x: max(1, int(x)))

    elif table_name == "markets":
        # Validate coordinates
        cleaned["latitude"] = cleaned["latitude"].clip(-90.0, 90.0)
        cleaned["longitude"] = cleaned["longitude"].clip(-180.0, 180.0)
        cleaned["estimated_daily_capacity"] = cleaned["estimated_daily_capacity"].apply(lambda x: max(100, int(x)))

    elif table_name == "market_prices":
        # Strict invariant: minimum_price <= modal_price <= maximum_price
        cleaned["modal_price"] = cleaned["modal_price"].apply(lambda x: max(1.0, float(x)))
        cleaned["minimum_price"] = cleaned["minimum_price"].apply(lambda x: max(0.5, float(x)))
        cleaned["maximum_price"] = cleaned["maximum_price"].apply(lambda x: max(1.0, float(x)))

        # Fix any min_price > modal_price or max_price < modal_price
        cleaned["minimum_price"] = np.minimum(cleaned["minimum_price"], cleaned["modal_price"])
        cleaned["maximum_price"] = np.maximum(cleaned["maximum_price"], cleaned["modal_price"])

        # Ensure minimum is strictly less than or equal to maximum
        mask_equal = cleaned["minimum_price"] >= cleaned["maximum_price"]
        cleaned.loc[mask_equal, "maximum_price"] = cleaned.loc[mask_equal, "minimum_price"] + 1.0

        cleaned["arrival_quantity"] = cleaned["arrival_quantity"].apply(lambda x: max(0.0, float(x)))
        cleaned["demand_index"] = cleaned["demand_index"].clip(20.0, 200.0)
        cleaned["supply_index"] = cleaned["supply_index"].clip(20.0, 200.0)

        # Referential filtering if reference data is provided
        if reference_data:
            comm_ids = set(reference_data.get("commodities", pd.DataFrame()).get("commodity_id", []))
            mkt_ids = set(reference_data.get("markets", pd.DataFrame()).get("market_id", []))
            if comm_ids:
                cleaned = cleaned[cleaned["commodity_id"].isin(comm_ids)]
            if mkt_ids:
                cleaned = cleaned[cleaned["market_id"].isin(mkt_ids)]

    elif table_name == "shipments":
        cleaned["quantity_kg"] = cleaned["quantity_kg"].apply(lambda x: max(100.0, float(x)))
        cleaned["distance_km"] = cleaned["distance_km"].apply(lambda x: max(10.0, float(x)))
        cleaned["transport_cost"] = cleaned["transport_cost"].apply(lambda x: max(500.0, float(x)))
        cleaned["initial_quality_percentage"] = cleaned["initial_quality_percentage"].clip(50.0, 100.0)
        cleaned["estimated_remaining_shelf_life"] = cleaned["estimated_remaining_shelf_life"].apply(lambda x: max(0.1, float(x)))

        # Referential filtering
        if reference_data:
            comm_ids = set(reference_data.get("commodities", pd.DataFrame()).get("commodity_id", []))
            mkt_ids = set(reference_data.get("markets", pd.DataFrame()).get("market_id", []))
            if comm_ids:
                cleaned = cleaned[cleaned["commodity_id"].isin(comm_ids)]
            if mkt_ids:
                cleaned = cleaned[cleaned["source_market_id"].isin(mkt_ids) & cleaned["destination_market_id"].isin(mkt_ids)]

    elif table_name == "sensor_readings":
        cleaned["temperature"] = cleaned["temperature"].clip(-30.0, 70.0)
        cleaned["humidity"] = cleaned["humidity"].clip(0.0, 100.0)
        cleaned["vibration"] = cleaned["vibration"].apply(lambda x: max(0.0, float(x)))

        if reference_data:
            ship_ids = set(reference_data.get("shipments", pd.DataFrame()).get("shipment_id", []))
            if ship_ids:
                cleaned = cleaned[cleaned["shipment_id"].isin(ship_ids)]

    elif table_name == "arbitrage_opportunities":
        if reference_data:
            ship_ids = set(reference_data.get("shipments", pd.DataFrame()).get("shipment_id", []))
            if ship_ids:
                cleaned = cleaned[cleaned["shipment_id"].isin(ship_ids)]

    elif table_name == "alerts":
        if reference_data:
            ship_ids = set(reference_data.get("shipments", pd.DataFrame()).get("shipment_id", []))
            if ship_ids:
                cleaned = cleaned[cleaned["shipment_id"].isin(ship_ids)]

    # 3. Provenance flag
    cleaned["is_synthetic"] = 1

    return cleaned.reset_index(drop=True)

def clean_and_preprocess_all(datasets: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """
    Clean and preprocess all generated datasets in dependency order to ensure
    100% referential integrity and valid domain boundaries.
    Returns cleaned datasets and validation audit report.
    """
    cleaned_datasets = {}

    # 1. Clean independent tables
    cleaned_datasets["commodities"] = clean_dataset("commodities", datasets.get("commodities", pd.DataFrame()))
    cleaned_datasets["markets"] = clean_dataset("markets", datasets.get("markets", pd.DataFrame()))

    # 2. Clean dependent tables
    cleaned_datasets["market_prices"] = clean_dataset(
        "market_prices", datasets.get("market_prices", pd.DataFrame()), reference_data=cleaned_datasets
    )
    cleaned_datasets["shipments"] = clean_dataset(
        "shipments", datasets.get("shipments", pd.DataFrame()), reference_data=cleaned_datasets
    )
    cleaned_datasets["sensor_readings"] = clean_dataset(
        "sensor_readings", datasets.get("sensor_readings", pd.DataFrame()), reference_data=cleaned_datasets
    )
    cleaned_datasets["arbitrage_opportunities"] = clean_dataset(
        "arbitrage_opportunities", datasets.get("arbitrage_opportunities", pd.DataFrame()), reference_data=cleaned_datasets
    )
    cleaned_datasets["alerts"] = clean_dataset(
        "alerts", datasets.get("alerts", pd.DataFrame()), reference_data=cleaned_datasets
    )

    # 3. Run audit on cleaned data
    audit_report = run_comprehensive_validation(cleaned_datasets)

    return cleaned_datasets, audit_report

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
            results["foreign_key_violations"] += int(invalid_comm + invalid_mkt)
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
        total_ship_fk = int(inv_ship_comm + inv_ship_src + inv_ship_dst)
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
