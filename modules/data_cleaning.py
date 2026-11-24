"""
AtmoSync - Data Cleaning, Quality Assurance & Preprocessing Suite
Audits referential integrity, schema constraints, range violations,
null values, duplicate keys, categorical validation, temporal/date logic,
and provides robust sanitization and preprocessing across all agricultural datasets.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger("atmosync.data_cleaning")

# Categorical domain standards
COMMODITY_CATEGORIES = {"Fruit", "Vegetable"}
SENSITIVITY_LEVELS = {"Low", "Moderate", "High", "Critical"}
MARKET_TYPES = {"Terminal Mandi", "Regional APMC", "Primary Mandi", "Wholesale Hub"}
SHIPMENT_STATUSES = {"In Transit", "Delivered", "Delayed", "At Risk", "Completed"}
SENSOR_STATUSES = {"Normal", "Warning", "Critical"}
ALERT_SEVERITIES = {"Warning", "Critical"}
ALERT_STATUSES = {"New", "Acknowledged", "Resolved"}


def clean_dataset(
    table_name: str,
    df: pd.DataFrame,
    reference_data: Optional[Dict[str, pd.DataFrame]] = None
) -> pd.DataFrame:
    """
    Preprocess, validate, and clean a single dataset table.
    Enforces non-null primary keys, removes duplicate IDs, corrects range anomalies,
    sanitizes categorical values, verifies temporal date ordering, and applies synthetic provenance labels.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    cleaned = df.copy()

    # 1. Deduplicate by primary key & drop null keys
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
        cleaned = cleaned.dropna(subset=[pk])
        cleaned = cleaned.drop_duplicates(subset=[pk], keep="first")

    # 2. Table-specific domain rules, numeric constraints, and date validations
    if table_name == "commodities":
        # Missing value imputation
        if "commodity_name" in cleaned.columns:
            cleaned["commodity_name"] = cleaned["commodity_name"].fillna("Agricultural Produce")
        if "category" in cleaned.columns:
            cleaned["category"] = cleaned["category"].apply(
                lambda c: c if c in COMMODITY_CATEGORIES else "Vegetable"
            )
        if "sensitivity_level" in cleaned.columns:
            cleaned["sensitivity_level"] = cleaned["sensitivity_level"].apply(
                lambda s: s if s in SENSITIVITY_LEVELS else "Moderate"
            )

        if "base_price_per_kg" in cleaned.columns:
            cleaned["base_price_per_kg"] = cleaned["base_price_per_kg"].fillna(30.0).apply(lambda x: max(1.0, float(x)))
        if "optimal_temperature" in cleaned.columns:
            cleaned["optimal_temperature"] = cleaned["optimal_temperature"].fillna(10.0).astype(float).clip(-10.0, 45.0)
        if "minimum_temperature" in cleaned.columns:
            cleaned["minimum_temperature"] = cleaned["minimum_temperature"].fillna(5.0).astype(float).clip(-15.0, 40.0)
        if "maximum_temperature" in cleaned.columns:
            cleaned["maximum_temperature"] = cleaned["maximum_temperature"].fillna(15.0).astype(float).clip(-5.0, 50.0)

        # Enforce min <= optimal <= max
        if all(c in cleaned.columns for c in ["minimum_temperature", "optimal_temperature", "maximum_temperature"]):
            cleaned["minimum_temperature"] = np.minimum(cleaned["minimum_temperature"], cleaned["optimal_temperature"])
            cleaned["maximum_temperature"] = np.maximum(cleaned["maximum_temperature"], cleaned["optimal_temperature"])

        if "optimal_humidity" in cleaned.columns:
            cleaned["optimal_humidity"] = cleaned["optimal_humidity"].fillna(85.0).clip(10.0, 99.0)
        if "maximum_humidity" in cleaned.columns:
            cleaned["maximum_humidity"] = cleaned["maximum_humidity"].fillna(95.0).clip(10.0, 100.0)
        if "optimal_humidity" in cleaned.columns and "maximum_humidity" in cleaned.columns:
            cleaned["maximum_humidity"] = np.maximum(cleaned["maximum_humidity"], cleaned["optimal_humidity"]).clip(10.0, 100.0)

        if "estimated_shelf_life_days" in cleaned.columns:
            cleaned["estimated_shelf_life_days"] = cleaned["estimated_shelf_life_days"].fillna(14).apply(lambda x: max(1, int(x)))

    elif table_name == "markets":
        if "market_name" in cleaned.columns:
            cleaned["market_name"] = cleaned["market_name"].fillna("APMC Market")
        if "state" in cleaned.columns:
            cleaned["state"] = cleaned["state"].fillna("Maharashtra")
        if "district" in cleaned.columns:
            cleaned["district"] = cleaned["district"].fillna("Central District")
        if "market_type" in cleaned.columns:
            cleaned["market_type"] = cleaned["market_type"].apply(
                lambda m: m if m in MARKET_TYPES else "Regional APMC"
            )
        if "latitude" in cleaned.columns:
            cleaned["latitude"] = cleaned["latitude"].fillna(19.0760).clip(-90.0, 90.0)
        if "longitude" in cleaned.columns:
            cleaned["longitude"] = cleaned["longitude"].fillna(72.8777).clip(-180.0, 180.0)
        if "estimated_daily_capacity" in cleaned.columns:
            cleaned["estimated_daily_capacity"] = cleaned["estimated_daily_capacity"].fillna(5000).apply(lambda x: max(100, int(x)))

    elif table_name == "market_prices":
        if "modal_price" in cleaned.columns:
            cleaned["modal_price"] = cleaned["modal_price"].fillna(40.0).apply(lambda x: max(1.0, float(x)))
        if "minimum_price" in cleaned.columns:
            cleaned["minimum_price"] = cleaned["minimum_price"].fillna(35.0).apply(lambda x: max(0.5, float(x)))
        if "maximum_price" in cleaned.columns:
            cleaned["maximum_price"] = cleaned["maximum_price"].fillna(45.0).apply(lambda x: max(1.0, float(x)))

        # Strict invariant: minimum_price <= modal_price <= maximum_price
        if all(c in cleaned.columns for c in ["minimum_price", "modal_price", "maximum_price"]):
            cleaned["minimum_price"] = np.minimum(cleaned["minimum_price"], cleaned["modal_price"])
            cleaned["maximum_price"] = np.maximum(cleaned["maximum_price"], cleaned["modal_price"])
            mask_equal = cleaned["minimum_price"] >= cleaned["maximum_price"]
            cleaned.loc[mask_equal, "maximum_price"] = cleaned.loc[mask_equal, "minimum_price"] + 1.0

        if "arrival_quantity" in cleaned.columns:
            cleaned["arrival_quantity"] = cleaned["arrival_quantity"].fillna(1000.0).apply(lambda x: max(0.0, float(x)))
        if "demand_index" in cleaned.columns:
            cleaned["demand_index"] = cleaned["demand_index"].fillna(100.0).clip(10.0, 300.0)
        if "supply_index" in cleaned.columns:
            cleaned["supply_index"] = cleaned["supply_index"].fillna(100.0).clip(10.0, 300.0)

        # Date validation: ensure parseable ISO dates
        if "date" in cleaned.columns:
            cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("2026-10-01")

        if reference_data:
            comm_ids = set(reference_data.get("commodities", pd.DataFrame()).get("commodity_id", []))
            mkt_ids = set(reference_data.get("markets", pd.DataFrame()).get("market_id", []))
            if comm_ids and "commodity_id" in cleaned.columns:
                cleaned = cleaned[cleaned["commodity_id"].isin(comm_ids)]
            if mkt_ids and "market_id" in cleaned.columns:
                cleaned = cleaned[cleaned["market_id"].isin(mkt_ids)]

    elif table_name == "shipments":
        if "shipment_status" in cleaned.columns:
            cleaned["shipment_status"] = cleaned["shipment_status"].apply(
                lambda s: s if s in SHIPMENT_STATUSES else "In Transit"
            )
        if "quantity_kg" in cleaned.columns:
            cleaned["quantity_kg"] = cleaned["quantity_kg"].fillna(1500.0).apply(lambda x: max(100.0, float(x)))
        if "distance_km" in cleaned.columns:
            cleaned["distance_km"] = cleaned["distance_km"].fillna(250.0).apply(lambda x: max(10.0, float(x)))
        if "transport_cost" in cleaned.columns:
            cleaned["transport_cost"] = cleaned["transport_cost"].fillna(3000.0).apply(lambda x: max(500.0, float(x)))
        if "initial_quality_percentage" in cleaned.columns:
            cleaned["initial_quality_percentage"] = cleaned["initial_quality_percentage"].fillna(95.0).clip(50.0, 100.0)
        if "estimated_remaining_shelf_life" in cleaned.columns:
            cleaned["estimated_remaining_shelf_life"] = cleaned["estimated_remaining_shelf_life"].fillna(10.0).apply(lambda x: max(0.1, float(x)))

        # Date parsing and temporal consistency: departure_date <= expected_arrival_date
        if "departure_date" in cleaned.columns and "expected_arrival_date" in cleaned.columns:
            dep_dt = pd.to_datetime(cleaned["departure_date"], errors="coerce")
            arr_dt = pd.to_datetime(cleaned["expected_arrival_date"], errors="coerce")

            cleaned["departure_date"] = dep_dt.dt.strftime("%Y-%m-%d").fillna("2026-10-01")
            arr_fixed = np.maximum(dep_dt + pd.Timedelta(days=1), arr_dt)
            cleaned["expected_arrival_date"] = arr_fixed.dt.strftime("%Y-%m-%d").fillna("2026-10-05")

        if reference_data:
            comm_ids = set(reference_data.get("commodities", pd.DataFrame()).get("commodity_id", []))
            mkt_ids = set(reference_data.get("markets", pd.DataFrame()).get("market_id", []))
            if comm_ids and "commodity_id" in cleaned.columns:
                cleaned = cleaned[cleaned["commodity_id"].isin(comm_ids)]
            if mkt_ids and "source_market_id" in cleaned.columns and "destination_market_id" in cleaned.columns:
                cleaned = cleaned[
                    cleaned["source_market_id"].isin(mkt_ids) &
                    cleaned["destination_market_id"].isin(mkt_ids)
                ]

    elif table_name == "sensor_readings":
        if "sensor_status" in cleaned.columns:
            cleaned["sensor_status"] = cleaned["sensor_status"].apply(
                lambda s: s if s in SENSOR_STATUSES else "Normal"
            )
        if "temperature" in cleaned.columns:
            cleaned["temperature"] = cleaned["temperature"].fillna(12.0).clip(-30.0, 70.0)
        if "humidity" in cleaned.columns:
            cleaned["humidity"] = cleaned["humidity"].fillna(85.0).clip(0.0, 100.0)
        if "vibration" in cleaned.columns:
            cleaned["vibration"] = cleaned["vibration"].fillna(0.8).clip(0.0, 10.0)

        # Timestamp format verification
        if "timestamp" in cleaned.columns:
            ts_dt = pd.to_datetime(cleaned["timestamp"], errors="coerce")
            cleaned["timestamp"] = ts_dt.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("2026-10-01 00:00:00")

        if reference_data:
            ship_ids = set(reference_data.get("shipments", pd.DataFrame()).get("shipment_id", []))
            if ship_ids and "shipment_id" in cleaned.columns:
                cleaned = cleaned[cleaned["shipment_id"].isin(ship_ids)]

    elif table_name == "arbitrage_opportunities":
        if "quantity_kg" in cleaned.columns:
            cleaned["quantity_kg"] = cleaned["quantity_kg"].fillna(1500.0).apply(lambda x: max(1.0, float(x)))
        if "transportation_cost" in cleaned.columns:
            cleaned["transportation_cost"] = cleaned["transportation_cost"].fillna(2000.0).apply(lambda x: max(0.0, float(x)))
        if "handling_cost" in cleaned.columns:
            cleaned["handling_cost"] = cleaned["handling_cost"].fillna(600.0).apply(lambda x: max(0.0, float(x)))
        if "estimated_quality_loss" in cleaned.columns:
            cleaned["estimated_quality_loss"] = cleaned["estimated_quality_loss"].fillna(0.05).clip(0.0, 1.0)

        # Recompute financial invariants
        if all(c in cleaned.columns for c in ["destination_market_price", "source_market_price", "quantity_kg"]):
            cleaned["gross_price_advantage"] = (
                (cleaned["destination_market_price"] - cleaned["source_market_price"]) * cleaned["quantity_kg"]
            ).round(2)

        if all(c in cleaned.columns for c in [
            "gross_price_advantage", "transportation_cost", "handling_cost",
            "destination_market_price", "quantity_kg", "estimated_quality_loss"
        ]):
            q_loss_val = (cleaned["destination_market_price"] * cleaned["quantity_kg"] * cleaned["estimated_quality_loss"])
            cleaned["estimated_net_benefit"] = (
                cleaned["gross_price_advantage"] - cleaned["transportation_cost"] - cleaned["handling_cost"] - q_loss_val
            ).round(2)

        if "recommendation_status" in cleaned.columns:
            if "estimated_net_benefit" in cleaned.columns:
                cleaned["recommendation_status"] = np.where(
                    cleaned["estimated_net_benefit"] > 0, "Recommended", "Not Recommended"
                )

        if reference_data:
            ship_ids = set(reference_data.get("shipments", pd.DataFrame()).get("shipment_id", []))
            if ship_ids and "shipment_id" in cleaned.columns:
                cleaned = cleaned[cleaned["shipment_id"].isin(ship_ids)]

    elif table_name == "alerts":
        if "severity" in cleaned.columns:
            cleaned["severity"] = cleaned["severity"].apply(
                lambda s: s if s in ALERT_SEVERITIES else "Warning"
            )
        if "status" in cleaned.columns:
            cleaned["status"] = cleaned["status"].apply(
                lambda s: s if s in ALERT_STATUSES else "New"
            )
        if "description" in cleaned.columns:
            cleaned["description"] = cleaned["description"].fillna("System notification alert")

        # Timestamp verification
        if "timestamp" in cleaned.columns:
            ts_dt = pd.to_datetime(cleaned["timestamp"], errors="coerce")
            cleaned["timestamp"] = ts_dt.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("2026-10-01 00:00:00")

        if reference_data:
            ship_ids = set(reference_data.get("shipments", pd.DataFrame()).get("shipment_id", []))
            if ship_ids and "shipment_id" in cleaned.columns:
                cleaned = cleaned[cleaned["shipment_id"].isin(ship_ids)]

    # Provenance metadata
    cleaned["is_synthetic"] = 1

    return cleaned.reset_index(drop=True)


def clean_and_preprocess_all(datasets: Dict[str, pd.DataFrame]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """
    Clean and preprocess all generated datasets in dependency order to ensure
    100% referential integrity, schema constraints, and valid domain boundaries.
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

    # 3. Run comprehensive audit on cleaned data
    audit_report = run_comprehensive_validation(cleaned_datasets)

    return cleaned_datasets, audit_report


def validate_and_sanitize_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Convenience helper to validate and sanitize an individual DataFrame."""
    return clean_dataset(table_name, df)


def validate_cross_table_relationships(datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Explicitly checks relationships across shipments, sensors, markets, and commodity records.
    Returns status and violation counts for each relationship.
    """
    comm_df = datasets.get("commodities", pd.DataFrame())
    mkt_df = datasets.get("markets", pd.DataFrame())
    ship_df = datasets.get("shipments", pd.DataFrame())
    sensor_df = datasets.get("sensor_readings", pd.DataFrame())
    price_df = datasets.get("market_prices", pd.DataFrame())
    arb_df = datasets.get("arbitrage_opportunities", pd.DataFrame())
    alerts_df = datasets.get("alerts", pd.DataFrame())

    valid_comms = set(comm_df["commodity_id"]) if not comm_df.empty else set()
    valid_mkts = set(mkt_df["market_id"]) if not mkt_df.empty else set()
    valid_ships = set(ship_df["shipment_id"]) if not ship_df.empty else set()

    report = {
        "shipment_commodity": 0,
        "shipment_source_market": 0,
        "shipment_destination_market": 0,
        "sensor_shipment": 0,
        "sensor_container_alignment": 0,
        "price_commodity": 0,
        "price_market": 0,
        "arbitrage_shipment": 0,
        "alert_shipment": 0,
        "all_valid": True,
        "total_violations": 0
    }

    if not ship_df.empty:
        if valid_comms:
            report["shipment_commodity"] = int((~ship_df["commodity_id"].isin(valid_comms)).sum())
        if valid_mkts:
            report["shipment_source_market"] = int((~ship_df["source_market_id"].isin(valid_mkts)).sum())
            report["shipment_destination_market"] = int((~ship_df["destination_market_id"].isin(valid_mkts)).sum())

    if not sensor_df.empty and valid_ships:
        report["sensor_shipment"] = int((~sensor_df["shipment_id"].isin(valid_ships)).sum())
        # Check container alignment if both have container_id
        if not ship_df.empty and "container_id" in sensor_df.columns and "container_id" in ship_df.columns:
            ship_cont_map = dict(zip(ship_df["shipment_id"], ship_df["container_id"]))
            expected_cont = sensor_df["shipment_id"].map(ship_cont_map)
            mismatch = (sensor_df["container_id"] != expected_cont) & expected_cont.notna()
            report["sensor_container_alignment"] = int(mismatch.sum())

    if not price_df.empty:
        if valid_comms:
            report["price_commodity"] = int((~price_df["commodity_id"].isin(valid_comms)).sum())
        if valid_mkts:
            report["price_market"] = int((~price_df["market_id"].isin(valid_mkts)).sum())

    if not arb_df.empty and valid_ships:
        report["arbitrage_shipment"] = int((~arb_df["shipment_id"].isin(valid_ships)).sum())

    if not alerts_df.empty and valid_ships:
        report["alert_shipment"] = int((~alerts_df["shipment_id"].isin(valid_ships)).sum())

    report["total_violations"] = sum(v for k, v in report.items() if k not in ["all_valid", "total_violations"])
    report["all_valid"] = (report["total_violations"] == 0)
    return report


def run_comprehensive_validation(datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Validates all tables across foreign keys, null checks, duplicates,
    numeric validity, temporal ordering, and domain ranges.
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
        "date_violations": 0,
        "categorical_violations": 0,
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

    # Categorical Checks
    if not comm_df.empty and "sensitivity_level" in comm_df.columns:
        inv_sens = (~comm_df["sensitivity_level"].isin(SENSITIVITY_LEVELS)).sum()
        if inv_sens > 0:
            results["categorical_violations"] += int(inv_sens)
            results["details"].append(f"Commodities have {inv_sens} invalid sensitivity levels.")

    if not ship_df.empty and "shipment_status" in ship_df.columns:
        inv_stat = (~ship_df["shipment_status"].isin(SHIPMENT_STATUSES)).sum()
        if inv_stat > 0:
            results["categorical_violations"] += int(inv_stat)
            results["details"].append(f"Shipments have {inv_stat} invalid shipment statuses.")

    if not sensor_df.empty and "sensor_status" in sensor_df.columns:
        inv_sns_stat = (~sensor_df["sensor_status"].isin(SENSOR_STATUSES)).sum()
        if inv_sns_stat > 0:
            results["categorical_violations"] += int(inv_sns_stat)
            results["details"].append(f"Sensors have {inv_sns_stat} invalid sensor statuses.")

    # Cross-table relationship audit
    rel_report = validate_cross_table_relationships(datasets)
    results["foreign_key_violations"] += rel_report["total_violations"]

    # Price consistency: min <= modal <= max
    if not price_df.empty and all(c in price_df.columns for c in ["minimum_price", "modal_price", "maximum_price"]):
        price_inv = (price_df["minimum_price"] > price_df["modal_price"]) | (price_df["modal_price"] > price_df["maximum_price"])
        inv_count = int(price_inv.sum())
        if inv_count > 0:
            results["range_violations"] += inv_count
            results["details"].append(f"{inv_count} price records violate min <= modal <= max constraint.")

        # Date validation
        invalid_dates = pd.to_datetime(price_df["date"], errors="coerce").isnull().sum()
        if invalid_dates > 0:
            results["date_violations"] += int(invalid_dates)
            results["details"].append(f"Market prices have {invalid_dates} unparseable date records.")

    # Shipment range & dates
    if not ship_df.empty:
        if "quantity_kg" in ship_df.columns:
            inv_qty = (ship_df["quantity_kg"] <= 0).sum()
            if inv_qty > 0:
                results["range_violations"] += int(inv_qty)
                results["details"].append(f"{inv_qty} shipments have non-positive quantities.")

        # Temporal ordering check: departure_date <= expected_arrival_date
        if "departure_date" in ship_df.columns and "expected_arrival_date" in ship_df.columns:
            dep = pd.to_datetime(ship_df["departure_date"], errors="coerce")
            arr = pd.to_datetime(ship_df["expected_arrival_date"], errors="coerce")
            date_inversions = int((dep > arr).sum())
            invalid_dep_arr = int(dep.isnull().sum() + arr.isnull().sum())
            if date_inversions > 0 or invalid_dep_arr > 0:
                results["date_violations"] += int(date_inversions + invalid_dep_arr)
                results["details"].append(f"Shipments have {date_inversions} date inversion(s) and {invalid_dep_arr} invalid date string(s).")

    # Sensor temperature & humidity ranges
    if not sensor_df.empty:
        if "temperature" in sensor_df.columns and "humidity" in sensor_df.columns:
            extreme_temp = ((sensor_df["temperature"] < -30) | (sensor_df["temperature"] > 70)).sum()
            extreme_hum = ((sensor_df["humidity"] < 0) | (sensor_df["humidity"] > 100)).sum()
            if extreme_temp > 0 or extreme_hum > 0:
                results["range_violations"] += int(extreme_temp + extreme_hum)
                results["details"].append(f"Sensors have extreme readings: {extreme_temp} temp / {extreme_hum} humidity.")

        if "timestamp" in sensor_df.columns:
            invalid_ts = pd.to_datetime(sensor_df["timestamp"], errors="coerce").isnull().sum()
            if invalid_ts > 0:
                results["date_violations"] += int(invalid_ts)
                results["details"].append(f"Sensors have {invalid_ts} unparseable timestamps.")

    total_issues = (
        results["foreign_key_violations"] +
        results["null_value_counts"] +
        results["duplicate_counts"] +
        results["range_violations"] +
        results["date_violations"] +
        results["categorical_violations"]
    )
    results["is_valid"] = (total_issues == 0)
    results["total_records"] = sum(s["record_count"] for s in results["table_summaries"].values())
    results["completeness_pct"] = (
        100.0 if total_issues == 0
        else round(max(0.0, 100.0 - (total_issues / max(1, results["total_records"])) * 100), 2)
    )

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
