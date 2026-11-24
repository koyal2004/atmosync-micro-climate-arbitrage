"""
Unit tests for data quality, preprocessing, validation, and relational integrity.
"""

import pytest
import numpy as np
import pandas as pd
from database.database import load_table
from modules.data_cleaning import (
    clean_dataset, clean_and_preprocess_all, validate_and_sanitize_dataframe,
    validate_cross_table_relationships, run_comprehensive_validation
)


def test_missing_and_duplicate_handling():
    """Verify primary key deduplication and null imputation."""
    df_dirty = pd.DataFrame({
        "commodity_id": ["C001", "C001", "C002", None],
        "commodity_name": ["Tomato", "Tomato", None, "Carrot"],
        "category": ["Vegetable", "Vegetable", "InvalidCategory", "Vegetable"],
        "base_price_per_kg": [30.0, 30.0, None, -5.0],
        "optimal_temperature": [10.0, 10.0, None, 50.0],
        "minimum_temperature": [5.0, 5.0, 15.0, 5.0],
        "maximum_temperature": [15.0, 15.0, 10.0, 20.0],
        "sensitivity_level": ["Moderate", "Moderate", "AlienLevel", "Critical"]
    })

    cleaned = clean_dataset("commodities", df_dirty)
    # Deduplication and null PK drop: 4 rows -> 2 rows (C001, C002)
    assert len(cleaned) == 2
    assert "C001" in cleaned["commodity_id"].values
    assert "C002" in cleaned["commodity_id"].values
    # Null commodity_name imputed
    assert cleaned.loc[cleaned["commodity_id"] == "C002", "commodity_name"].iloc[0] == "Agricultural Produce"
    # Categorical validation
    assert cleaned.loc[cleaned["commodity_id"] == "C002", "category"].iloc[0] == "Vegetable"
    assert cleaned.loc[cleaned["commodity_id"] == "C002", "sensitivity_level"].iloc[0] == "Moderate"
    # Min <= max temperature invariant
    c2 = cleaned[cleaned["commodity_id"] == "C002"].iloc[0]
    assert c2["minimum_temperature"] <= c2["maximum_temperature"]


def test_date_validation_and_temporal_inversion():
    """Verify temporal date ordering: departure_date <= expected_arrival_date."""
    df_ship = pd.DataFrame({
        "shipment_id": ["SHP-A", "SHP-B", "SHP-C"],
        "departure_date": ["2026-11-20", "2026-11-25", "invalid-date"],
        "expected_arrival_date": ["2026-11-22", "2026-11-20", "2026-11-26"],  # SHP-B has inverted dates
        "quantity_kg": [1000.0, -500.0, 2000.0],
        "distance_km": [200.0, -20.0, 300.0],
        "transport_cost": [2500.0, 0.0, 3500.0],
        "shipment_status": ["In Transit", "BrokenStatus", "Delayed"]
    })

    cleaned = clean_dataset("shipments", df_ship)
    assert len(cleaned) == 3

    # Date inversion fixed
    b_row = cleaned[cleaned["shipment_id"] == "SHP-B"].iloc[0]
    dep_b = pd.to_datetime(b_row["departure_date"])
    arr_b = pd.to_datetime(b_row["expected_arrival_date"])
    assert dep_b < arr_b

    # Invalid date string coerced safely
    c_row = cleaned[cleaned["shipment_id"] == "SHP-C"].iloc[0]
    assert pd.to_datetime(c_row["departure_date"]) is not None

    # Negative quantities, distance and costs corrected
    assert b_row["quantity_kg"] >= 100.0
    assert b_row["distance_km"] >= 10.0
    assert b_row["transport_cost"] >= 500.0

    # Categorical status sanitized
    assert b_row["shipment_status"] == "In Transit"


def test_market_price_invariants():
    """Verify minimum_price <= modal_price <= maximum_price invariant."""
    df_prices = pd.DataFrame({
        "price_id": ["P001", "P002"],
        "modal_price": [40.0, 50.0],
        "minimum_price": [45.0, 55.0],  # Min > modal (violation)
        "maximum_price": [35.0, 45.0],  # Max < modal (violation)
        "date": ["2026-11-20", "bad-date"],
        "arrival_quantity": [-100.0, 500.0]
    })

    cleaned = clean_dataset("market_prices", df_prices)
    for _, row in cleaned.iterrows():
        assert row["minimum_price"] <= row["modal_price"] <= row["maximum_price"]
        assert row["minimum_price"] < row["maximum_price"]
        assert row["arrival_quantity"] >= 0.0
        assert pd.to_datetime(row["date"]) is not None


def test_sensor_telemetry_bounds():
    """Verify sensor telemetry clipping and formatting."""
    df_sensors = pd.DataFrame({
        "sensor_id": ["S01", "S02"],
        "shipment_id": ["SHP-001", "SHP-002"],
        "temperature": [-100.0, 150.0],
        "humidity": [-20.0, 130.0],
        "vibration": [-5.0, 25.0],
        "sensor_status": ["Normal", "InvalidStatus"],
        "timestamp": ["2026-11-20 10:00:00", "corrupt_timestamp"]
    })

    cleaned = clean_dataset("sensor_readings", df_sensors)
    s1 = cleaned[cleaned["sensor_id"] == "S01"].iloc[0]
    s2 = cleaned[cleaned["sensor_id"] == "S02"].iloc[0]

    assert -30.0 <= s1["temperature"] <= 70.0
    assert -30.0 <= s2["temperature"] <= 70.0
    assert 0.0 <= s1["humidity"] <= 100.0
    assert 0.0 <= s2["humidity"] <= 100.0
    assert 0.0 <= s1["vibration"] <= 10.0
    assert 0.0 <= s2["vibration"] <= 10.0
    assert s2["sensor_status"] == "Normal"
    assert pd.to_datetime(s2["timestamp"]) is not None


def test_cross_table_relationships_on_database():
    """Verify relational integrity across current database tables."""
    tables = [
        "commodities", "markets", "market_prices",
        "shipments", "sensor_readings", "arbitrage_opportunities", "alerts"
    ]
    datasets = {t: load_table(t) for t in tables}
    rel_report = validate_cross_table_relationships(datasets)
    assert rel_report["all_valid"] is True
    assert rel_report["total_violations"] == 0

    val_report = run_comprehensive_validation(datasets)
    assert val_report["is_valid"] is True
    assert val_report["completeness_pct"] == 100.0
