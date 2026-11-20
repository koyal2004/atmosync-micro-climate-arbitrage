"""
AtmoSync Test Suite - Database Operations & Integrity
Tests database connection, schema setup, primary key uniqueness, foreign key relationships,
data persistence across initializations, and error handling.
"""

import sys
import tempfile
import sqlite3
from pathlib import Path
import pytest
import pandas as pd

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.database import (
    get_connection,
    get_db_connection,
    init_db,
    is_database_populated,
    get_record_counts,
    load_table,
    execute_query,
    save_dataframe_to_db,
    insert_alert,
    get_alerts,
    update_alert_status,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    TableNotFoundError,
    VALID_TABLE_NAMES,
)

@pytest.fixture
def temp_db_path(tmp_path):
    """Fixture providing an isolated SQLite database path for testing."""
    return tmp_path / "test_atmosync.db"

class TestDatabaseSetupAndConnection:
    """Tests connection creation and configuration pragmas."""

    def test_connection_created_with_pragmas(self, temp_db_path):
        conn = get_connection(temp_db_path)
        assert conn is not None

        # Verify foreign keys pragma is ON
        fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk_status == 1

        # Verify row factory
        row = conn.execute("SELECT 1 AS test_col;").fetchone()
        assert row["test_col"] == 1

        conn.close()

    def test_context_manager_closes_connection(self, temp_db_path):
        with get_db_connection(temp_db_path) as conn:
            assert conn is not None
        # Connection should now be closed; attempting query raises ProgrammingError
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1;")

class TestSchemaInitialization:
    """Tests table creation, indexes, and primary/foreign key definitions."""

    def test_all_required_tables_created(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}

        required_tables = [
            "commodities",
            "markets",
            "market_prices",
            "shipments",
            "sensor_readings",
            "alerts",
        ]
        for tbl in required_tables:
            assert tbl in tables, f"Missing required table: {tbl}"

    def test_primary_key_uniqueness(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO commodities (commodity_id, commodity_name, category, base_price_per_kg,
                    optimal_temperature, minimum_temperature, maximum_temperature,
                    optimal_humidity, maximum_humidity, estimated_shelf_life_days, sensitivity_level)
                VALUES ('COM-0001', 'Apple', 'Fruit', 120.0, 2.0, 0.0, 5.0, 90.0, 95.0, 60, 'Moderate')
            """)
            conn.commit()

            # Attempting to insert duplicate commodity_id must raise sqlite3.IntegrityError
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO commodities (commodity_id, commodity_name, category, base_price_per_kg,
                        optimal_temperature, minimum_temperature, maximum_temperature,
                        optimal_humidity, maximum_humidity, estimated_shelf_life_days, sensitivity_level)
                    VALUES ('COM-0001', 'Apple Duplicate', 'Fruit', 130.0, 2.0, 0.0, 5.0, 90.0, 95.0, 60, 'Moderate')
                """)
                conn.commit()

    def test_foreign_key_constraints_enforced(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.cursor()

            # 1. Price referencing non-existent commodity must fail
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO market_prices (price_id, date, commodity_id, market_id,
                        minimum_price, maximum_price, modal_price, arrival_quantity, demand_index, supply_index)
                    VALUES ('PRC-00001', '2026-10-01', 'NON_EXISTENT_COM', 'MKT-0001', 30.0, 40.0, 35.0, 1000.0, 100.0, 100.0)
                """)
                conn.commit()

            # 2. Insert valid commodity and market
            cursor.execute("""
                INSERT INTO commodities (commodity_id, commodity_name, category, base_price_per_kg,
                    optimal_temperature, minimum_temperature, maximum_temperature,
                    optimal_humidity, maximum_humidity, estimated_shelf_life_days, sensitivity_level)
                VALUES ('COM-0001', 'Tomato', 'Vegetable', 35.0, 11.0, 8.0, 15.0, 88.0, 92.0, 10, 'Critical')
            """)
            cursor.execute("""
                INSERT INTO markets (market_id, market_name, state, district, latitude, longitude,
                    market_type, estimated_daily_capacity)
                VALUES ('MKT-0001', 'Koyambedu Wholesale', 'Tamil Nadu', 'Chennai', 13.0694, 80.1948, 'Terminal Mandi', 12000)
            """)
            cursor.execute("""
                INSERT INTO markets (market_id, market_name, state, district, latitude, longitude,
                    market_type, estimated_daily_capacity)
                VALUES ('MKT-0002', 'Yeshwanthpur APMC', 'Karnataka', 'Bengaluru', 13.0238, 77.5529, 'Terminal Mandi', 15000)
            """)
            conn.commit()

            # 3. Market price with valid commodity and market should succeed
            cursor.execute("""
                INSERT INTO market_prices (price_id, date, commodity_id, market_id,
                    minimum_price, maximum_price, modal_price, arrival_quantity, demand_index, supply_index)
                VALUES ('PRC-00001', '2026-10-01', 'COM-0001', 'MKT-0001', 30.0, 40.0, 35.0, 1000.0, 100.0, 100.0)
            """)
            conn.commit()

            # 4. Shipment with valid FKs should succeed
            cursor.execute("""
                INSERT INTO shipments (shipment_id, container_id, commodity_id, source_market_id,
                    destination_market_id, departure_date, expected_arrival_date, quantity_kg,
                    transport_cost, distance_km, shipment_status, initial_quality_percentage,
                    estimated_remaining_shelf_life)
                VALUES ('SHP-0001', 'CONT-1001', 'COM-0001', 'MKT-0001', 'MKT-0002', '2026-10-01',
                    '2026-10-02', 5000.0, 12000.0, 350.0, 'In Transit', 98.0, 9.0)
            """)
            conn.commit()

            # 5. Sensor reading with invalid shipment_id must fail
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO sensor_readings (sensor_id, shipment_id, container_id, timestamp,
                        temperature, humidity, vibration, sensor_status)
                    VALUES ('SNS-000001', 'INVALID-SHIPMENT', 'CONT-1001', '2026-10-01 10:00:00', 12.0, 85.0, 0.4, 'Normal')
                """)
                conn.commit()

            # 6. Sensor reading with valid shipment_id should succeed
            cursor.execute("""
                INSERT INTO sensor_readings (sensor_id, shipment_id, container_id, timestamp,
                    temperature, humidity, vibration, sensor_status)
                VALUES ('SNS-000001', 'SHP-0001', 'CONT-1001', '2026-10-01 10:00:00', 12.0, 85.0, 0.4, 'Normal')
            """)
            conn.commit()

            # 7. Alert with valid shipment_id should succeed
            cursor.execute("""
                INSERT INTO alerts (alert_id, shipment_id, container_id, alert_type, severity,
                    timestamp, description, status)
                VALUES ('ALT-00001', 'SHP-0001', 'CONT-1001', 'Temperature Warning', 'Medium',
                    '2026-10-01 10:30:00', 'Slight temperature variance detected', 'New')
            """)
            conn.commit()

class TestDataPersistence:
    """Verifies that normal execution does not delete existing records."""

    def test_existing_records_preserved_on_normal_init(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)

        # Insert a sample market
        with get_db_connection(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO markets (market_id, market_name, state, district, latitude, longitude,
                    market_type, estimated_daily_capacity)
                VALUES ('MKT-PERSIST', 'Pune Gultekdi', 'Maharashtra', 'Pune', 18.4988, 73.8653, 'Terminal Mandi', 13000)
            """)
            conn.commit()

        # Re-run init_db without force_reset
        init_db(force_reset=False, db_path=temp_db_path)

        # Check record still exists
        df = load_table("markets", db_path=temp_db_path)
        assert len(df) == 1
        assert df.iloc[0]["market_id"] == "MKT-PERSIST"

    def test_force_reset_clears_records(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)

        with get_db_connection(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO markets (market_id, market_name, state, district, latitude, longitude,
                    market_type, estimated_daily_capacity)
                VALUES ('MKT-RESET', 'Pune Gultekdi', 'Maharashtra', 'Pune', 18.4988, 73.8653, 'Terminal Mandi', 13000)
            """)
            conn.commit()

        # Reset database
        init_db(force_reset=True, db_path=temp_db_path)

        df = load_table("markets", db_path=temp_db_path)
        assert len(df) == 0

class TestDatabaseOperationsAndErrorHandling:
    """Tests load, save, queries, and proper exception raising."""

    def test_load_table_invalid_name_raises_error(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)
        with pytest.raises(TableNotFoundError):
            load_table("users_table; DROP TABLE commodities;", db_path=temp_db_path)

    def test_execute_query_invalid_sql_raises_error(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)
        with pytest.raises(DatabaseQueryError):
            execute_query("SELECT * FROM nonexistent_table;", db_path=temp_db_path)

    def test_save_and_load_dataframe_with_synthetic_flag(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)

        data = pd.DataFrame([{
            "commodity_id": "COM-0100",
            "commodity_name": "Mango Alphonso",
            "category": "Fruit",
            "base_price_per_kg": 95.0,
            "optimal_temperature": 12.0,
            "minimum_temperature": 10.0,
            "maximum_temperature": 15.0,
            "optimal_humidity": 85.0,
            "maximum_humidity": 90.0,
            "estimated_shelf_life_days": 12,
            "sensitivity_level": "Critical"
        }])

        save_dataframe_to_db(data, "commodities", if_exists="append", db_path=temp_db_path)

        loaded = load_table("commodities", db_path=temp_db_path)
        assert len(loaded) == 1
        assert loaded.iloc[0]["commodity_id"] == "COM-0100"
        # Synthetic provenance flag must be set
        assert "is_synthetic" in loaded.columns
        assert loaded.iloc[0]["is_synthetic"] == 1

    def test_is_database_populated_detection(self, temp_db_path):
        init_db(force_reset=True, db_path=temp_db_path)
        assert is_database_populated(temp_db_path) is False

        # Add shipment prerequisites and shipment
        with get_db_connection(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO commodities (commodity_id, commodity_name, category, base_price_per_kg,
                    optimal_temperature, minimum_temperature, maximum_temperature,
                    optimal_humidity, maximum_humidity, estimated_shelf_life_days, sensitivity_level)
                VALUES ('COM-0001', 'Apple', 'Fruit', 120.0, 2.0, 0.0, 5.0, 90.0, 95.0, 60, 'Moderate')
            """)
            cursor.execute("""
                INSERT INTO markets (market_id, market_name, state, district, latitude, longitude,
                    market_type, estimated_daily_capacity)
                VALUES ('MKT-0001', 'Market 1', 'State', 'District', 12.0, 77.0, 'APMC', 1000)
            """)
            cursor.execute("""
                INSERT INTO markets (market_id, market_name, state, district, latitude, longitude,
                    market_type, estimated_daily_capacity)
                VALUES ('MKT-0002', 'Market 2', 'State', 'District', 13.0, 78.0, 'APMC', 1000)
            """)
            cursor.execute("""
                INSERT INTO shipments (shipment_id, container_id, commodity_id, source_market_id,
                    destination_market_id, departure_date, expected_arrival_date, quantity_kg,
                    transport_cost, distance_km, shipment_status, initial_quality_percentage,
                    estimated_remaining_shelf_life)
                VALUES ('SHP-0001', 'CONT-1', 'COM-0001', 'MKT-0001', 'MKT-0002', '2026-10-01',
                    '2026-10-02', 5000.0, 10000.0, 300.0, 'Completed', 95.0, 8.0)
            """)
            conn.commit()

        assert is_database_populated(temp_db_path) is True
