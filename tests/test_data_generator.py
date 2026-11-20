"""
AtmoSync Test Suite - Synthetic Dataset Generator & Preprocessing
Tests dataset volume (5,000 to 10,000 records), seed reproducibility,
domain ranges (prices, quantities, IoT sensors), referential integrity,
commodity and market coverage, data cleaning, and SQLite persistence.
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.data_generator import (
    generate_all_datasets,
    generate_and_persist_datasets,
    reset_synthetic_data,
    PRIORITY_COMMODITIES,
    PRIORITY_MARKET_DISTRICTS
)
from modules.data_cleaning import (
    clean_dataset,
    clean_and_preprocess_all,
    run_comprehensive_validation
)
from database.database import (
    init_db,
    load_table,
    get_record_counts,
    is_database_populated
)

@pytest.fixture
def temp_db(tmp_path):
    """Fixture providing temporary isolated SQLite database."""
    return tmp_path / "test_generator.db"

class TestDatasetVolumeAndStructure:
    """Verifies generated records fall in the 5,000–10,000 target range across all tables."""

    def test_record_counts_10k_target(self):
        datasets = generate_all_datasets(total_target=10000, seed=42)
        total_records = sum(len(df) for df in datasets.values())
        
        # Must be in the 5,000-11,000 range (approx 10,000)
        assert 9500 <= total_records <= 10500, f"Total records {total_records} outside 9,500-10,500 target"

        # Verify all 5 core tables + auxiliary tables are populated
        assert len(datasets["commodities"]) >= 500
        assert len(datasets["markets"]) >= 250
        assert len(datasets["market_prices"]) >= 1500
        assert len(datasets["shipments"]) >= 500
        assert len(datasets["sensor_readings"]) >= 2000

    def test_record_counts_5k_target(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        total_records = sum(len(df) for df in datasets.values())
        
        # Must be around 5,000
        assert 4800 <= total_records <= 5500, f"Total records {total_records} outside 4,800-5,500 target"

class TestCommodityAndMarketCoverage:
    """Verifies that all specified agricultural commodities and Indian markets are included."""

    def test_required_commodities_included(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        comm_df = datasets["commodities"]

        # Check required commodities: mango, banana, apple, tomato, onion, potato
        names = comm_df["commodity_name"].str.lower().tolist()
        required = ["mango", "banana", "apple", "tomato", "onion", "potato"]
        for req in required:
            found = any(req in name for name in names)
            assert found, f"Required commodity '{req}' not found in commodities dataset"

    def test_required_indian_markets_included(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        mkt_df = datasets["markets"]

        # Check required Indian markets: Chennai, Bengaluru, Hyderabad, Mumbai, Pune, Kochi
        districts = mkt_df["district"].str.lower().tolist()
        names = mkt_df["market_name"].str.lower().tolist()
        combined = [f"{d} {n}" for d, n in zip(districts, names)]

        required_cities = ["chennai", "bengaluru", "hyderabad", "mumbai", "pune", "ernakulam"]
        for city in required_cities:
            found = any(city in text for text in combined)
            assert found, f"Required market/city '{city}' not found in markets dataset"

class TestRealisticSimulationsAndInvariants:
    """Tests realistic price distributions, IoT sensor values, quantities, and invariants."""

    def test_price_invariants_minimum_less_than_maximum(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        prices = datasets["market_prices"]

        # Invariant: minimum_price <= modal_price <= maximum_price
        violations = prices[
            (prices["minimum_price"] > prices["modal_price"]) |
            (prices["modal_price"] > prices["maximum_price"]) |
            (prices["minimum_price"] > prices["maximum_price"])
        ]
        assert len(violations) == 0, f"Found {len(violations)} records violating price invariants"

    def test_shipment_quantities_and_distances(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        shipments = datasets["shipments"]

        # Quantities must be positive (between 1,000 kg and 25,000 kg)
        assert (shipments["quantity_kg"] > 0).all()
        assert (shipments["distance_km"] > 0).all()
        assert (shipments["transport_cost"] > 0).all()
        assert (shipments["initial_quality_percentage"] >= 50.0).all()
        assert (shipments["initial_quality_percentage"] <= 100.0).all()

    def test_sensor_readings_realistic_domains(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        sensors = datasets["sensor_readings"]

        # Temperature between -30°C and 70°C
        assert (sensors["temperature"] >= -30.0).all()
        assert (sensors["temperature"] <= 70.0).all()

        # Humidity between 0% and 100%
        assert (sensors["humidity"] >= 0.0).all()
        assert (sensors["humidity"] <= 100.0).all()

        # Vibration non-negative
        assert (sensors["vibration"] >= 0.0).all()

    def test_reproducibility_with_fixed_seed(self):
        ds1 = generate_all_datasets(total_target=5000, seed=123)
        ds2 = generate_all_datasets(total_target=5000, seed=123)

        pd.testing.assert_frame_equal(ds1["commodities"], ds2["commodities"])
        pd.testing.assert_frame_equal(ds1["markets"], ds2["markets"])
        pd.testing.assert_frame_equal(ds1["market_prices"], ds2["market_prices"])
        pd.testing.assert_frame_equal(ds1["shipments"], ds2["shipments"])

    def test_synthetic_provenance_labels(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        for name, df in datasets.items():
            assert "is_synthetic" in df.columns, f"Table '{name}' missing 'is_synthetic' column"
            assert (df["is_synthetic"] == 1).all(), f"Table '{name}' has non-synthetic entries"

class TestReferentialIntegrityAndPreprocessing:
    """Verifies foreign-key integrity, absence of duplicate IDs, and data cleaning."""

    def test_referential_integrity_audit(self):
        datasets = generate_all_datasets(total_target=5000, seed=42)
        audit = run_comprehensive_validation(datasets)

        assert audit["is_valid"] is True
        assert audit["foreign_key_violations"] == 0
        assert audit["null_value_counts"] == 0
        assert audit["duplicate_counts"] == 0
        assert audit["range_violations"] == 0

    def test_clean_dataset_fixes_price_inversion_and_duplicates(self):
        dirty_prices = pd.DataFrame([
            {
                "price_id": "PRC-99999",
                "date": "2026-10-01",
                "commodity_id": "COM-0001",
                "market_id": "MKT-0001",
                "minimum_price": 50.0,
                "maximum_price": 20.0, # Inverted!
                "modal_price": 30.0,
                "arrival_quantity": 1000.0,
                "demand_index": 100.0,
                "supply_index": 100.0
            },
            {
                "price_id": "PRC-99999", # Duplicate PK!
                "date": "2026-10-02",
                "commodity_id": "COM-0001",
                "market_id": "MKT-0001",
                "minimum_price": 30.0,
                "maximum_price": 40.0,
                "modal_price": 35.0,
                "arrival_quantity": 1200.0,
                "demand_index": 100.0,
                "supply_index": 100.0
            }
        ])

        cleaned = clean_dataset("market_prices", dirty_prices)
        assert len(cleaned) == 1 # Duplicate dropped
        assert cleaned.iloc[0]["minimum_price"] <= cleaned.iloc[0]["maximum_price"]
        assert cleaned.iloc[0]["is_synthetic"] == 1

class TestSQLitePersistenceAndLifecycle:
    """Verifies controlled save, reset, and unpopulated detection."""

    def test_generate_and_persist_to_sqlite(self, temp_db):
        datasets, audit = generate_and_persist_datasets(
            total_target=5000, seed=42, force_reset=True, db_path=temp_db
        )
        assert audit["is_valid"] is True

        # Check database is populated
        assert is_database_populated(db_path=temp_db) is True

        # Check record counts in SQLite
        counts = get_record_counts(db_path=temp_db)
        assert counts["commodities"] >= 300
        assert counts["markets"] >= 150
        assert counts["shipments"] >= 400
        assert counts["total"] >= 4500

    def test_reset_synthetic_data(self, temp_db):
        # Generate initial data
        reset_synthetic_data(total_target=5000, seed=42, db_path=temp_db)
        counts_1 = get_record_counts(db_path=temp_db)

        # Reset with different size
        reset_synthetic_data(total_target=6000, seed=43, db_path=temp_db)
        counts_2 = get_record_counts(db_path=temp_db)

        assert counts_2["total"] > counts_1["total"]
