"""
AtmoSync - Configuration & Application Settings
Intelligent Climate Monitoring & Agricultural Market Arbitrage
"""

import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(env_path: Path) -> None:
    """Safely load key=value pairs from a local .env file without overwriting OS env vars."""
    if not env_path.is_file():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, val)
    except OSError:
        pass


_load_env_file(BASE_DIR / ".env")


def _resolve_project_path(env_var: str, default_rel: Path) -> Path:
    """Resolve an optional path from environment variables safely."""
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return default_rel
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else (BASE_DIR / candidate).resolve()


def _get_int_env(env_var: str, default_val: int, min_val: int, max_val: int) -> int:
    """Read and clamp an integer environment variable safely."""
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return default_val
    try:
        parsed = int(raw)
        return max(min_val, min(max_val, parsed))
    except ValueError:
        return default_val


# Configurable Paths & Environment Settings
DATA_DIR = _resolve_project_path("ATMOSYNC_DATA_DIR", BASE_DIR / "data")
GENERATED_DATA_DIR = DATA_DIR / "generated"
EXPORTS_DIR = DATA_DIR / "exports"
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = _resolve_project_path("ATMOSYNC_DB_PATH", DATABASE_DIR / "atmosync.db")
ASSETS_DIR = BASE_DIR / "assets"

APP_ENV = os.environ.get("ATMOSYNC_APP_ENV", "academic-local").strip() or "academic-local"
_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_raw_level = os.environ.get("ATMOSYNC_LOG_LEVEL", "INFO").strip().upper()
LOG_LEVEL = _raw_level if _raw_level in _ALLOWED_LOG_LEVELS else "INFO"

# Ensure directories exist
GENERATED_DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Application Branding
APP_NAME = "AtmoSync"
APP_SUBTITLE = "Micro-Climate Arbitrage Analytics"
TAGLINE = "Intelligent Climate Monitoring & Agricultural Market Arbitrage"
APP_VERSION = "2.4.0 (Enterprise Academic Edition)"
ORGANIZATION = "Infotact Advanced Data Analytics & Engineering"

# Data Generation Configuration
MIN_TOTAL_RECORDS = 5000
MAX_TOTAL_RECORDS = 10000
DEFAULT_RANDOM_SEED = _get_int_env("ATMOSYNC_RANDOM_SEED", 42, 0, 999999)
DEFAULT_TOTAL_RECORDS = _get_int_env("ATMOSYNC_DEFAULT_RECORDS", 10000, MIN_TOTAL_RECORDS, MAX_TOTAL_RECORDS)

# Distribution of records for Default ~10,000 total:
RECORD_DISTRIBUTION_10K = {
    "commodities": 1000,
    "markets": 500,
    "market_prices": 3000,
    "shipments": 1000,
    "sensor_readings": 4000,
    "arbitrage_opportunities": 500
}

# Distribution of records for Minimum ~5,000 total:
RECORD_DISTRIBUTION_5K = {
    "commodities": 500,
    "markets": 250,
    "market_prices": 1600,
    "shipments": 600,
    "sensor_readings": 2000,
    "arbitrage_opportunities": 250
}

# Color Palette (Bloomberg / Enterprise SaaS Theme)
COLORS = {
    "primary": "#10243A",       # Deep Navy
    "secondary": "#12B8A6",     # Teal
    "background": "#F4F7FA",    # Light Grey
    "card": "#FFFFFF",          # Pure White
    "text": "#0F172A",          # Dark Slate
    "text_muted": "#64748B",    # Muted Slate
    "border": "#E2E8F0",        # Border Light
    "success": "#16A34A",       # Forest Green
    "warning": "#F59E0B",       # Amber
    "critical": "#DC2626",      # Crimson Red
    "info": "#2563EB",          # Royal Blue
    "accent": "#0D9488",        # Dark Teal
}

# Persistent Synthetic Data Disclaimer
PERSISTENT_DISCLAIMER = (
    "AtmoSync is an academic demonstration platform using synthetic agricultural market, "
    "shipment, and IoT sensor data. All prices, shipment records, sensor observations, "
    "risk scores, and arbitrage opportunities are simulated and must not be interpreted "
    "as actual market conditions or trading recommendations."
)
DATASET_LABEL = "SYNTHETIC DEMONSTRATION DATA (INFOTACT RESEARCH LAB)"
