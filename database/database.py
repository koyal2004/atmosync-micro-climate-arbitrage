"""
AtmoSync - Database Operations & Persistence Layer
SQLite storage for commodities, markets, prices, shipments, sensors, arbitrage, alerts, and settings.
"""

import sqlite3
import pandas as pd
from typing import Dict, Any, Optional, List
from pathlib import Path
from config.settings import DB_PATH

def get_connection() -> sqlite3.Connection:
    """Create and return a SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(force_reset: bool = False):
    """Initialize database tables and indexes if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    if force_reset:
        cursor.executescript("""
            DROP TABLE IF EXISTS alerts;
            DROP TABLE IF EXISTS simulation_settings;
            DROP TABLE IF EXISTS arbitrage_opportunities;
            DROP TABLE IF EXISTS sensor_readings;
            DROP TABLE IF EXISTS shipments;
            DROP TABLE IF EXISTS market_prices;
            DROP TABLE IF EXISTS markets;
            DROP TABLE IF EXISTS commodities;
        """)
        conn.commit()

    # 1. Commodities Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commodities (
            commodity_id TEXT PRIMARY KEY,
            commodity_name TEXT NOT NULL,
            category TEXT NOT NULL,
            base_price_per_kg REAL NOT NULL,
            optimal_temperature REAL NOT NULL,
            minimum_temperature REAL NOT NULL,
            maximum_temperature REAL NOT NULL,
            optimal_humidity REAL NOT NULL,
            maximum_humidity REAL NOT NULL,
            estimated_shelf_life_days INTEGER NOT NULL,
            sensitivity_level TEXT NOT NULL
        );
    """)

    # 2. Markets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS markets (
            market_id TEXT PRIMARY KEY,
            market_name TEXT NOT NULL,
            state TEXT NOT NULL,
            district TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            market_type TEXT NOT NULL,
            estimated_daily_capacity INTEGER NOT NULL
        );
    """)

    # 3. Market Prices Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_prices (
            price_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            commodity_id TEXT NOT NULL,
            market_id TEXT NOT NULL,
            minimum_price REAL NOT NULL,
            maximum_price REAL NOT NULL,
            modal_price REAL NOT NULL,
            arrival_quantity REAL NOT NULL,
            demand_index REAL NOT NULL,
            supply_index REAL NOT NULL,
            FOREIGN KEY (commodity_id) REFERENCES commodities (commodity_id),
            FOREIGN KEY (market_id) REFERENCES markets (market_id)
        );
    """)

    # 4. Shipments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id TEXT PRIMARY KEY,
            container_id TEXT NOT NULL,
            commodity_id TEXT NOT NULL,
            source_market_id TEXT NOT NULL,
            destination_market_id TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            expected_arrival_date TEXT NOT NULL,
            quantity_kg REAL NOT NULL,
            transport_cost REAL NOT NULL,
            distance_km REAL NOT NULL,
            shipment_status TEXT NOT NULL,
            initial_quality_percentage REAL NOT NULL,
            estimated_remaining_shelf_life REAL NOT NULL,
            FOREIGN KEY (commodity_id) REFERENCES commodities (commodity_id),
            FOREIGN KEY (source_market_id) REFERENCES markets (market_id),
            FOREIGN KEY (destination_market_id) REFERENCES markets (market_id)
        );
    """)

    # 5. IoT Sensor Dataset Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            sensor_id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            container_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            vibration REAL NOT NULL,
            sensor_status TEXT NOT NULL,
            FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id)
        );
    """)

    # 6. Arbitrage Dataset Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
            opportunity_id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            commodity_id TEXT NOT NULL,
            source_market_id TEXT NOT NULL,
            destination_market_id TEXT NOT NULL,
            source_market_price REAL NOT NULL,
            destination_market_price REAL NOT NULL,
            quantity_kg REAL NOT NULL,
            estimated_quality_loss REAL NOT NULL,
            transportation_cost REAL NOT NULL,
            handling_cost REAL NOT NULL,
            gross_price_advantage REAL NOT NULL,
            estimated_net_benefit REAL NOT NULL,
            recommendation_status TEXT NOT NULL,
            FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id),
            FOREIGN KEY (commodity_id) REFERENCES commodities (commodity_id),
            FOREIGN KEY (source_market_id) REFERENCES markets (market_id),
            FOREIGN KEY (destination_market_id) REFERENCES markets (market_id)
        );
    """)

    # 7. Alerts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            container_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id)
        );
    """)

    # 8. Simulation Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # Performance Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_comm_mkt ON market_prices (commodity_id, market_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON market_prices (date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments (shipment_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensors_shipment ON sensor_readings (shipment_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensors_container ON sensor_readings (container_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensors_timestamp ON sensor_readings (timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);")

    conn.commit()
    conn.close()

def is_database_populated() -> bool:
    """Check if database has data already generated."""
    if not DB_PATH.exists():
        return False
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM shipments")
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        conn.close()
        return False

def get_record_counts() -> Dict[str, int]:
    """Retrieve record counts from all tables."""
    conn = get_connection()
    cursor = conn.cursor()
    tables = [
        "commodities", "markets", "market_prices", 
        "shipments", "sensor_readings", "arbitrage_opportunities", "alerts"
    ]
    counts = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except Exception:
            counts[table] = 0
    conn.close()
    counts["total"] = sum(counts.values())
    return counts

def load_table(table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Load a SQLite table into a Pandas DataFrame."""
    conn = get_connection()
    query = f"SELECT * FROM {table_name}"
    if limit:
        query += f" LIMIT {limit}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def execute_query(query: str, params: tuple = ()) -> pd.DataFrame:
    """Execute arbitrary SQL query and return DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def save_dataframe_to_db(df: pd.DataFrame, table_name: str, if_exists: str = "append"):
    """Write DataFrame into SQLite table."""
    conn = get_connection()
    df.to_sql(table_name, conn, if_exists=if_exists, index=False)
    conn.close()

# Alert CRUD Operations
def get_alerts(status_filter: Optional[str] = None) -> pd.DataFrame:
    """Retrieve alerts with optional status filter."""
    conn = get_connection()
    query = "SELECT * FROM alerts"
    params = []
    if status_filter and status_filter != "All":
        query += " WHERE status = ?"
        params.append(status_filter)
    query += " ORDER BY timestamp DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_alert_status(alert_id: str, new_status: str):
    """Update status of an alert (Acknowledged or Resolved)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET status = ? WHERE alert_id = ?", (new_status, alert_id))
    conn.commit()
    conn.close()

def insert_alert(alert_dict: Dict[str, Any]):
    """Insert a single alert."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerts (alert_id, shipment_id, container_id, alert_type, severity, timestamp, description, status)
        VALUES (:alert_id, :shipment_id, :container_id, :alert_type, :severity, :timestamp, :description, :status)
    """, alert_dict)
    conn.commit()
    conn.close()
