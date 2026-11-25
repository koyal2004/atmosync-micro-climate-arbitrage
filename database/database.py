"""
AtmoSync - Database Operations & Persistence Layer
SQLite storage for commodities, markets, prices, shipments, sensors, arbitrage, alerts, and settings.
Includes robust connection pooling/handling, schema initialization, referential integrity, and error management.
"""

import sqlite3
import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List, Generator, Tuple
import pandas as pd
from config.settings import DB_PATH

logger = logging.getLogger("atmosync.database")

# ---------------------------------------------------------------------------
# Thread-Safe In-Memory Table Cache (Invalidated on Writes)
# ---------------------------------------------------------------------------
_CACHE_LOCK = threading.RLock()
_TABLE_CACHE: Dict[Tuple[str, str, Optional[int]], Tuple[float, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = 30.0


def invalidate_table_cache(table_name: Optional[str] = None, db_path: Optional[Path] = None):
    """Invalidate cached table DataFrames on any write, update, or schema reset."""
    target_str = str(Path(db_path).resolve()) if db_path else str(DB_PATH.resolve())
    with _CACHE_LOCK:
        if table_name is None:
            keys_to_del = [k for k in _TABLE_CACHE if k[0] == target_str]
        else:
            keys_to_del = [k for k in _TABLE_CACHE if k[0] == target_str and k[1] == table_name]
        for k in keys_to_del:
            _TABLE_CACHE.pop(k, None)


# ---------------------------------------------------------------------------
# Table Schema Registry (Required Columns & Primary Keys)
# ---------------------------------------------------------------------------
TABLE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "commodities": {
        "pk": "commodity_id",
        "required_cols": [
            "commodity_id", "commodity_name", "category", "base_price_per_kg",
            "optimal_temperature", "minimum_temperature", "maximum_temperature",
            "optimal_humidity", "maximum_humidity", "estimated_shelf_life_days", "sensitivity_level"
        ],
    },
    "markets": {
        "pk": "market_id",
        "required_cols": [
            "market_id", "market_name", "state", "district", "latitude", "longitude",
            "market_type", "estimated_daily_capacity"
        ],
    },
    "market_prices": {
        "pk": "price_id",
        "required_cols": [
            "price_id", "date", "commodity_id", "market_id", "minimum_price",
            "maximum_price", "modal_price", "arrival_quantity", "demand_index", "supply_index"
        ],
    },
    "shipments": {
        "pk": "shipment_id",
        "required_cols": [
            "shipment_id", "container_id", "commodity_id", "source_market_id",
            "destination_market_id", "departure_date", "expected_arrival_date",
            "quantity_kg", "transport_cost", "distance_km", "shipment_status",
            "initial_quality_percentage", "estimated_remaining_shelf_life"
        ],
    },
    "sensor_readings": {
        "pk": "sensor_id",
        "required_cols": [
            "sensor_id", "shipment_id", "container_id", "timestamp",
            "temperature", "humidity", "vibration", "sensor_status"
        ],
    },
    "arbitrage_opportunities": {
        "pk": "opportunity_id",
        "required_cols": [
            "opportunity_id", "shipment_id", "commodity_id", "source_market_id",
            "destination_market_id", "source_market_price", "destination_market_price",
            "quantity_kg", "estimated_quality_loss", "transportation_cost", "handling_cost",
            "gross_price_advantage", "estimated_net_benefit", "recommendation_status"
        ],
    },
    "alerts": {
        "pk": "alert_id",
        "required_cols": [
            "alert_id", "shipment_id", "container_id", "alert_type",
            "severity", "timestamp", "description", "status"
        ],
    },
}

# ---------------------------------------------------------------------------
# Custom Database Exceptions
# ---------------------------------------------------------------------------
class DatabaseError(Exception):
    """Base exception for all database operations in AtmoSync."""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when connection to SQLite database fails."""
    pass

class DatabaseQueryError(DatabaseError):
    """Raised when a SQL query execution fails."""
    pass

class TableNotFoundError(DatabaseError):
    """Raised when an operation targets a non-existent database table."""
    pass

# ---------------------------------------------------------------------------
# Database Connection Helpers
# ---------------------------------------------------------------------------
def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Create and return a SQLite connection with foreign keys enabled and WAL mode.
    Ensures the parent directory exists and configures row factory for dictionary-like access.
    """
    target_path = Path(db_path) if db_path else DB_PATH
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(target_path),
            timeout=30.0,
            check_same_thread=False
        )
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database at {target_path}: {e}")
        raise DatabaseConnectionError(f"Database connection error: {e}") from e

@contextmanager
def get_db_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for safe database connections with automatic closing."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def transaction(conn: Optional[sqlite3.Connection] = None, db_path: Optional[Path] = None) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for transactional queries with automatic commit and rollback."""
    close_after = False
    if conn is None:
        conn = get_connection(db_path)
        close_after = True
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Transaction failed, changes rolled back: {e}")
        raise DatabaseQueryError(f"Database transaction error: {e}") from e
    finally:
        if close_after:
            conn.close()

# ---------------------------------------------------------------------------
# Schema Initialization
# ---------------------------------------------------------------------------
def init_db(force_reset: bool = False, db_path: Optional[Path] = None):
    """
    Initialize database tables and indexes.
    If force_reset is False (default), existing data is preserved and tables are created if not present.
    If force_reset is True, all tables are dropped and recreated cleanly.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    try:
        if force_reset:
            logger.warning("force_reset is True: dropping all existing AtmoSync tables.")
            cursor.executescript("""
                DROP TABLE IF EXISTS alerts;
                DROP TABLE IF EXISTS arbitrage_opportunities;
                DROP TABLE IF EXISTS sensor_readings;
                DROP TABLE IF EXISTS shipments;
                DROP TABLE IF EXISTS market_prices;
                DROP TABLE IF EXISTS markets;
                DROP TABLE IF EXISTS commodities;
                DROP TABLE IF EXISTS simulation_settings;
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
                sensitivity_level TEXT NOT NULL,
                is_synthetic INTEGER NOT NULL DEFAULT 1
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
                estimated_daily_capacity INTEGER NOT NULL,
                is_synthetic INTEGER NOT NULL DEFAULT 1
            );
        """)

        # 3. Market Prices Table (FK to commodities & markets)
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
                is_synthetic INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (commodity_id) REFERENCES commodities (commodity_id) ON DELETE RESTRICT,
                FOREIGN KEY (market_id) REFERENCES markets (market_id) ON DELETE RESTRICT
            );
        """)

        # 4. Shipments Table (FK to commodities, source market, destination market)
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
                is_synthetic INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (commodity_id) REFERENCES commodities (commodity_id) ON DELETE RESTRICT,
                FOREIGN KEY (source_market_id) REFERENCES markets (market_id) ON DELETE RESTRICT,
                FOREIGN KEY (destination_market_id) REFERENCES markets (market_id) ON DELETE RESTRICT
            );
        """)

        # 5. IoT Sensor Dataset Table (FK to shipments)
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
                is_synthetic INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id) ON DELETE CASCADE
            );
        """)

        # 6. Arbitrage Opportunities Table (FK to shipments, commodities, markets)
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
                is_synthetic INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id) ON DELETE CASCADE,
                FOREIGN KEY (commodity_id) REFERENCES commodities (commodity_id) ON DELETE RESTRICT,
                FOREIGN KEY (source_market_id) REFERENCES markets (market_id) ON DELETE RESTRICT,
                FOREIGN KEY (destination_market_id) REFERENCES markets (market_id) ON DELETE RESTRICT
            );
        """)

        # 7. Alerts Table (FK to shipments)
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
                is_synthetic INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (shipment_id) REFERENCES shipments (shipment_id) ON DELETE CASCADE
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipments_commodity ON shipments (commodity_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensors_shipment ON sensor_readings (shipment_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensors_container ON sensor_readings (container_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sensors_timestamp ON sensor_readings (timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_shipment ON alerts (shipment_id);")

        conn.commit()
        invalidate_table_cache(db_path=db_path)
        logger.info("AtmoSync SQLite database initialized successfully.")
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database initialization failed: {e}")
        raise DatabaseError(f"Database initialization failed: {e}") from e
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# Inspection & Record Count Utilities
# ---------------------------------------------------------------------------
def is_database_populated(db_path: Optional[Path] = None) -> bool:
    """Check if database exists and has data in the core shipments table."""
    target_path = Path(db_path) if db_path else DB_PATH
    if not target_path.exists():
        return False
    try:
        with get_db_connection(target_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM shipments")
            row = cursor.fetchone()
            return (row[0] > 0) if row else False
    except sqlite3.Error:
        return False

def get_record_counts(db_path: Optional[Path] = None) -> Dict[str, int]:
    """Retrieve record counts from all standard AtmoSync tables."""
    tables = [
        "commodities", "markets", "market_prices", 
        "shipments", "sensor_readings", "arbitrage_opportunities", "alerts"
    ]
    counts = {}
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except sqlite3.Error:
                    counts[table] = 0
    except DatabaseConnectionError:
        return {table: 0 for table in tables} | {"total": 0}

    counts["total"] = sum(counts.values())
    return counts

# ---------------------------------------------------------------------------
# Data Loading & Persistence
# ---------------------------------------------------------------------------
VALID_TABLE_NAMES = {
    "commodities", "markets", "market_prices",
    "shipments", "sensor_readings", "arbitrage_opportunities",
    "alerts", "simulation_settings"
}

def load_table(table_name: str, limit: Optional[int] = None, db_path: Optional[Path] = None, use_cache: bool = True) -> pd.DataFrame:
    """Load a SQLite table into a Pandas DataFrame with caching, validation, and error handling."""
    if table_name not in VALID_TABLE_NAMES:
        raise TableNotFoundError(f"Invalid or unauthorized table name '{table_name}'. Must be one of {VALID_TABLE_NAMES}")

    target_str = str(Path(db_path).resolve()) if db_path else str(DB_PATH.resolve())
    cache_key = (target_str, table_name, int(limit) if limit and limit > 0 else None)

    if use_cache:
        with _CACHE_LOCK:
            cached = _TABLE_CACHE.get(cache_key)
            if cached is not None:
                ts, cached_df = cached
                if (time.monotonic() - ts) < _CACHE_TTL_SECONDS:
                    return cached_df.copy()

    try:
        with get_db_connection(db_path) as conn:
            query = f"SELECT * FROM {table_name}"
            if limit and limit > 0:
                query += f" LIMIT {int(limit)}"
            df = pd.read_sql_query(query, conn)
            if use_cache:
                with _CACHE_LOCK:
                    _TABLE_CACHE[cache_key] = (time.monotonic(), df.copy())
            return df
    except Exception as e:
        logger.error(f"Error loading table '{table_name}': {e}")
        raise DatabaseQueryError(f"Failed to load table '{table_name}': {e}") from e


def execute_query(query: str, params: tuple = (), db_path: Optional[Path] = None) -> pd.DataFrame:
    """Execute arbitrary SQL query safely with parameter binding and return DataFrame."""
    try:
        with get_db_connection(db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
            return df
    except Exception as e:
        logger.error(f"Error executing query '{query}': {e}")
        raise DatabaseQueryError(f"Query execution failed: {e}") from e


def save_dataframe_to_db(df: pd.DataFrame, table_name: str, if_exists: str = "append", db_path: Optional[Path] = None):
    """
    Write DataFrame into a SQLite table safely while preserving schema constraints (PK, FK, indexes).
    Ensures 'is_synthetic' column is present to fulfill dataset provenance requirements.
    """
    if table_name not in VALID_TABLE_NAMES:
        raise TableNotFoundError(f"Invalid table name '{table_name}'.")

    if df.empty:
        logger.warning(f"Attempted to save empty DataFrame to {table_name}. Skipping.")
        return

    df_to_save = df.copy()
    if "is_synthetic" not in df_to_save.columns:
        df_to_save["is_synthetic"] = 1

    try:
        with get_db_connection(db_path) as conn:
            if if_exists == "replace":
                # Preserve existing table schema (PK, FK, indexes) by truncating rows
                cursor = conn.cursor()
                cursor.execute("PRAGMA foreign_keys = OFF;")
                cursor.execute(f"DELETE FROM {table_name};")
                df_to_save.to_sql(table_name, conn, if_exists="append", index=False)
                cursor.execute("PRAGMA foreign_keys = ON;")
            else:
                df_to_save.to_sql(table_name, conn, if_exists=if_exists, index=False)
            conn.commit()
            invalidate_table_cache(table_name=table_name, db_path=db_path)
            logger.info(f"Saved {len(df_to_save)} records to table '{table_name}' ({if_exists}).")
    except Exception as e:
        logger.error(f"Failed to save DataFrame to table '{table_name}': {e}")
        raise DatabaseQueryError(f"Failed to persist data to '{table_name}': {e}") from e


def safe_import_dataframe(
    df: pd.DataFrame,
    table_name: str,
    mode: str = "skip_duplicates",
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Safely imports a validated DataFrame into an existing SQLite table.
    Prevents duplicate primary keys and handles IntegrityErrors gracefully without crashing.
    """
    if table_name not in TABLE_SCHEMAS:
        raise TableNotFoundError(f"Table '{table_name}' is not supported for structured import.")

    if df is None or df.empty:
        return {"status": "skipped", "inserted": 0, "skipped_duplicates": 0, "message": "Empty DataFrame provided."}

    schema = TABLE_SCHEMAS[table_name]
    pk = schema["pk"]
    allowed_cols = schema["required_cols"] + ["is_synthetic"]

    df_clean = df.copy()
    if "is_synthetic" not in df_clean.columns:
        df_clean["is_synthetic"] = 1

    # Retain only valid schema columns in order
    present_cols = [c for c in allowed_cols if c in df_clean.columns]
    missing_cols = [c for c in schema["required_cols"] if c not in df_clean.columns]
    if missing_cols:
        return {
            "status": "error",
            "inserted": 0,
            "skipped_duplicates": 0,
            "message": f"Missing required columns for '{table_name}': {', '.join(missing_cols)}"
        }

    df_clean = df_clean[present_cols].drop_duplicates(subset=[pk], keep="first")

    try:
        with get_db_connection(db_path) as conn:
            existing_pks = set(
                pd.read_sql_query(f"SELECT {pk} FROM {table_name}", conn)[pk].astype(str).tolist()
            )
            incoming_pks = df_clean[pk].astype(str)
            dup_mask = incoming_pks.isin(existing_pks)
            skipped_count = int(dup_mask.sum())

            if mode == "skip_duplicates":
                to_insert = df_clean[~dup_mask]
            else:
                # Upsert: delete matching existing keys first, then append
                if skipped_count > 0:
                    dup_ids = incoming_pks[dup_mask].tolist()
                    placeholders = ",".join(["?"] * len(dup_ids))
                    conn.execute(f"DELETE FROM {table_name} WHERE {pk} IN ({placeholders})", dup_ids)
                to_insert = df_clean

            if not to_insert.empty:
                to_insert.to_sql(table_name, conn, if_exists="append", index=False)
                conn.commit()
                invalidate_table_cache(table_name=table_name, db_path=db_path)

            inserted_count = len(to_insert)
            return {
                "status": "success",
                "inserted": inserted_count,
                "skipped_duplicates": skipped_count if mode == "skip_duplicates" else 0,
                "updated": skipped_count if mode != "skip_duplicates" else 0,
                "message": f"Imported {inserted_count} record(s) into '{table_name}'."
            }
    except sqlite3.IntegrityError as e:
        logger.warning(f"Foreign key or constraint violation during import into '{table_name}': {e}")
        return {
            "status": "error",
            "inserted": 0,
            "skipped_duplicates": 0,
            "message": f"Referential integrity check failed (unmatched foreign key): {e}"
        }
    except Exception as e:
        logger.error(f"Unexpected error importing into '{table_name}': {e}")
        return {
            "status": "error",
            "inserted": 0,
            "skipped_duplicates": 0,
            "message": f"Import failed: {e}"
        }


def check_database_health(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Perform a comprehensive SQLite health, integrity, and schema check."""
    target_path = Path(db_path) if db_path else DB_PATH
    health = {
        "exists": target_path.exists(),
        "integrity_ok": False,
        "foreign_keys_enabled": False,
        "missing_tables": [],
        "counts": {}
    }
    if not target_path.exists():
        return health
    try:
        with get_db_connection(target_path) as conn:
            cursor = conn.cursor()
            integ = cursor.execute("PRAGMA integrity_check;").fetchone()[0]
            health["integrity_ok"] = (str(integ).lower() == "ok")
            fk = cursor.execute("PRAGMA foreign_keys;").fetchone()[0]
            health["foreign_keys_enabled"] = (fk == 1)

            existing_tables = {
                r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
            }
            expected = set(TABLE_SCHEMAS.keys())
            health["missing_tables"] = sorted(list(expected - existing_tables))
            health["counts"] = get_record_counts(target_path)
    except Exception as e:
        health["error"] = str(e)
    return health


# ---------------------------------------------------------------------------
# Alert CRUD Operations
# ---------------------------------------------------------------------------
def get_alerts(status_filter: Optional[str] = None, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Retrieve alerts with optional status filter."""
    try:
        with get_db_connection(db_path) as conn:
            query = "SELECT * FROM alerts"
            params: List[Any] = []
            if status_filter and status_filter != "All":
                query += " WHERE status = ?"
                params.append(status_filter)
            query += " ORDER BY timestamp DESC"
            df = pd.read_sql_query(query, conn, params=params)
            return df
    except sqlite3.Error as e:
        logger.error(f"Failed to fetch alerts: {e}")
        raise DatabaseQueryError(f"Failed to fetch alerts: {e}") from e


def update_alert_status(alert_id: str, new_status: str, db_path: Optional[Path] = None):
    """Update status of an alert (e.g., Acknowledged or Resolved)."""
    if new_status not in {"New", "Acknowledged", "Resolved"}:
        raise ValueError(f"Invalid alert status '{new_status}'.")
    try:
        with transaction(db_path=db_path) as cursor:
            cursor.execute("UPDATE alerts SET status = ? WHERE alert_id = ?", (new_status, alert_id))
        invalidate_table_cache(table_name="alerts", db_path=db_path)
    except sqlite3.Error as e:
        logger.error(f"Failed to update alert '{alert_id}' status to '{new_status}': {e}")
        raise DatabaseQueryError(f"Failed to update alert status: {e}") from e


def insert_alert(alert_dict: Dict[str, Any], db_path: Optional[Path] = None):
    """Insert a single alert record safely."""
    item = dict(alert_dict)
    if "is_synthetic" not in item:
        item["is_synthetic"] = 1

    try:
        with transaction(db_path=db_path) as cursor:
            cursor.execute("""
                INSERT INTO alerts (alert_id, shipment_id, container_id, alert_type, severity, timestamp, description, status, is_synthetic)
                VALUES (:alert_id, :shipment_id, :container_id, :alert_type, :severity, :timestamp, :description, :status, :is_synthetic)
            """, item)
        invalidate_table_cache(table_name="alerts", db_path=db_path)
    except sqlite3.Error as e:
        logger.error(f"Failed to insert alert: {e}")
        raise DatabaseQueryError(f"Failed to insert alert: {e}") from e
