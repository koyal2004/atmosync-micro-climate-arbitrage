"""
Unit tests for Commit 1: Backend Reliability, Database Optimization,
Safe CSV Upload Validation, and Duplicate-Safe Import Pipelines.
"""

import sqlite3
import pytest
import pandas as pd

from database.database import (
    init_db,
    load_table,
    save_dataframe_to_db,
    safe_import_dataframe,
    check_database_health,
    insert_alert,
    update_alert_status,
    get_connection,
    invalidate_table_cache,
)
from modules.data_cleaning import validate_uploaded_csv


@pytest.fixture
def isolated_db(tmp_path):
    db_file = tmp_path / "test_reliability.db"
    init_db(force_reset=True, db_path=db_file)
    invalidate_table_cache(db_path=db_file)
    return db_file


def test_replace_preserves_schema_and_primary_keys(isolated_db):
    df_comm = pd.DataFrame([{
        "commodity_id": "COM-T1",
        "commodity_name": "Tomato",
        "category": "Vegetable",
        "base_price_per_kg": 35.0,
        "optimal_temperature": 11.0,
        "minimum_temperature": 8.0,
        "maximum_temperature": 15.0,
        "optimal_humidity": 88.0,
        "maximum_humidity": 92.0,
        "estimated_shelf_life_days": 10,
        "sensitivity_level": "Critical",
        "is_synthetic": 1,
    }])

    save_dataframe_to_db(df_comm, "commodities", if_exists="replace", db_path=isolated_db)
    loaded = load_table("commodities", db_path=isolated_db)
    assert len(loaded) == 1

    # Verify PRIMARY KEY constraint is still intact after replace
    with get_connection(isolated_db) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO commodities (commodity_id, commodity_name, category, base_price_per_kg,
                    optimal_temperature, minimum_temperature, maximum_temperature,
                    optimal_humidity, maximum_humidity, estimated_shelf_life_days, sensitivity_level)
                VALUES ('COM-T1', 'Duplicate', 'Vegetable', 40.0, 11.0, 8.0, 15.0, 88.0, 92.0, 10, 'Critical')
            """)
            conn.commit()


def test_cache_invalidation_on_writes(isolated_db):
    # Initial load populates cache with 0 rows
    df_initial = load_table("commodities", db_path=isolated_db, use_cache=True)
    assert df_initial.empty

    # Save 1 row -> cache must automatically invalidate
    df_new = pd.DataFrame([{
        "commodity_id": "COM-C1",
        "commodity_name": "Mango",
        "category": "Fruit",
        "base_price_per_kg": 80.0,
        "optimal_temperature": 12.0,
        "minimum_temperature": 10.0,
        "maximum_temperature": 14.0,
        "optimal_humidity": 85.0,
        "maximum_humidity": 90.0,
        "estimated_shelf_life_days": 14,
        "sensitivity_level": "High",
    }])
    save_dataframe_to_db(df_new, "commodities", if_exists="append", db_path=isolated_db)

    df_after = load_table("commodities", db_path=isolated_db, use_cache=True)
    assert len(df_after) == 1
    assert df_after.iloc[0]["commodity_name"] == "Mango"


def test_safe_import_duplicate_prevention_and_upsert(isolated_db):
    df_batch1 = pd.DataFrame([{
        "commodity_id": "COM-01",
        "commodity_name": "Banana",
        "category": "Fruit",
        "base_price_per_kg": 45.0,
        "optimal_temperature": 13.0,
        "minimum_temperature": 12.0,
        "maximum_temperature": 15.0,
        "optimal_humidity": 90.0,
        "maximum_humidity": 95.0,
        "estimated_shelf_life_days": 12,
        "sensitivity_level": "High",
    }])
    res1 = safe_import_dataframe(df_batch1, "commodities", mode="skip_duplicates", db_path=isolated_db)
    assert res1["status"] == "success"
    assert res1["inserted"] == 1

    # Attempt re-import with 1 duplicate and 1 new row
    df_batch2 = pd.DataFrame([
        {
            "commodity_id": "COM-01",
            "commodity_name": "Banana Updated",
            "category": "Fruit",
            "base_price_per_kg": 55.0,
            "optimal_temperature": 13.0,
            "minimum_temperature": 12.0,
            "maximum_temperature": 15.0,
            "optimal_humidity": 90.0,
            "maximum_humidity": 95.0,
            "estimated_shelf_life_days": 12,
            "sensitivity_level": "High",
        },
        {
            "commodity_id": "COM-02",
            "commodity_name": "Apple",
            "category": "Fruit",
            "base_price_per_kg": 120.0,
            "optimal_temperature": 2.0,
            "minimum_temperature": 0.0,
            "maximum_temperature": 4.0,
            "optimal_humidity": 90.0,
            "maximum_humidity": 95.0,
            "estimated_shelf_life_days": 45,
            "sensitivity_level": "Moderate",
        },
    ])
    res2 = safe_import_dataframe(df_batch2, "commodities", mode="skip_duplicates", db_path=isolated_db)
    assert res2["status"] == "success"
    assert res2["inserted"] == 1
    assert res2["skipped_duplicates"] == 1

    # Verify original COM-01 was not overwritten
    loaded = load_table("commodities", db_path=isolated_db)
    assert loaded.loc[loaded["commodity_id"] == "COM-01", "commodity_name"].iloc[0] == "Banana"

    # Now test upsert mode
    res3 = safe_import_dataframe(df_batch2, "commodities", mode="upsert", db_path=isolated_db)
    assert res3["status"] == "success"
    loaded_upsert = load_table("commodities", db_path=isolated_db)
    assert loaded_upsert.loc[loaded_upsert["commodity_id"] == "COM-01", "commodity_name"].iloc[0] == "Banana Updated"


def test_csv_upload_validation_edge_cases():
    # 1. Empty 0-byte file
    res_empty = validate_uploaded_csv(b"", "commodities")
    assert res_empty["is_valid"] is False
    assert any("empty" in e.lower() for e in res_empty["errors"])

    # 2. Header-only CSV
    header_only = b"commodity_id,commodity_name,category,base_price_per_kg\n"
    res_header = validate_uploaded_csv(header_only, "commodities")
    assert res_header["is_valid"] is False

    # 3. Missing required columns
    missing_cols_csv = b"commodity_id,commodity_name\nCOM-99,Onion\n"
    res_missing = validate_uploaded_csv(missing_cols_csv, "commodities")
    assert res_missing["is_valid"] is False
    assert len(res_missing["summary"]["missing_columns"]) > 0

    # 4. Malformed numeric values & duplicates sanitized safely
    dirty_csv = (
        "commodity_id,commodity_name,category,base_price_per_kg,optimal_temperature,"
        "minimum_temperature,maximum_temperature,optimal_humidity,maximum_humidity,"
        "estimated_shelf_life_days,sensitivity_level\n"
        "COM-10,Onion,Vegetable,not_a_number,15,10,20,70,75,30,Low\n"
        "COM-10,Onion Dup,Vegetable,25,15,10,20,70,75,30,Low\n"
        ",NoPK,Vegetable,25,15,10,20,70,75,30,Low\n"
    ).encode("utf-8")
    res_dirty = validate_uploaded_csv(dirty_csv, "commodities")
    assert res_dirty["is_valid"] is True
    assert len(res_dirty["df"]) == 1
    assert res_dirty["df"].iloc[0]["base_price_per_kg"] == 30.0  # Imputed default
    assert len(res_dirty["warnings"]) >= 2


def test_database_health_check(isolated_db):
    health = check_database_health(isolated_db)
    assert health["exists"] is True
    assert health["integrity_ok"] is True
    assert health["foreign_keys_enabled"] is True
    assert health["missing_tables"] == []
