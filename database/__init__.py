"""
AtmoSync Database Package.
Provides SQLite database connection management, schema definitions, and persistence helpers.
"""

from .database import (
    get_connection,
    get_db_connection,
    transaction,
    init_db,
    is_database_populated,
    get_record_counts,
    load_table,
    execute_query,
    save_dataframe_to_db,
    get_alerts,
    update_alert_status,
    insert_alert,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseQueryError,
    TableNotFoundError,
    VALID_TABLE_NAMES,
)

__all__ = [
    "get_connection",
    "get_db_connection",
    "transaction",
    "init_db",
    "is_database_populated",
    "get_record_counts",
    "load_table",
    "execute_query",
    "save_dataframe_to_db",
    "get_alerts",
    "update_alert_status",
    "insert_alert",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "TableNotFoundError",
    "VALID_TABLE_NAMES",
]
