"""
AtmoSync - Micro-Climate Arbitrage Analytics
Root Application Entrypoint & Streamlit Multipage Orchestrator.

Enterprise-grade agricultural supply-chain monitoring dashboard
with eight navigable analytical modules.
"""

import sys
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Configure logging early
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("atmosync.app")

# Ensure application root is in python path
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import streamlit as st
import pandas as pd

# ---------------------------------------------------------------------------
# Safe imports with error handling
# ---------------------------------------------------------------------------
try:
    from config.settings import (
        APP_NAME, APP_SUBTITLE, TAGLINE, APP_VERSION,
        PERSISTENT_DISCLAIMER, COLORS, ASSETS_DIR
    )
except ImportError as e:
    st.error(f"⚠️ Configuration module failed to load: {e}")
    st.stop()

try:
    from database.database import (
        init_db, is_database_populated, save_dataframe_to_db,
        get_record_counts, get_alerts, update_alert_status
    )
except ImportError as e:
    st.error(f"⚠️ Database module failed to load: {e}")
    st.stop()

try:
    from modules.data_generator import generate_all_datasets
except ImportError as e:
    st.error(f"⚠️ Data generator module failed to load: {e}")
    st.stop()

try:
    from utils.helpers import get_status_badge
except ImportError as e:
    st.error(f"⚠️ Utility helpers module failed to load: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Page Configuration (must be first Streamlit command)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"{APP_NAME} – {APP_SUBTITLE}",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Inject Custom CSS – Enterprise Navy / Teal / Light Theme
# ---------------------------------------------------------------------------
css_file = ASSETS_DIR / "styles.css"
if css_file.exists():
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Additional inline styling for consistent enterprise look
st.markdown("""
<style>
    /* Global app background */
    .stApp {
        background-color: #F4F7FA;
    }

    /* Sidebar deep-navy branding */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A1929 0%, #10243A 100%) !important;
    }

    /* Navigation active state highlight */
    section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] a[aria-current="page"] {
        background: linear-gradient(90deg, #12B8A6, #0D9488) !important;
        color: #FFFFFF !important;
        font-weight: 700;
        border-radius: 8px;
    }

    /* Main content area cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    /* Expander styling in sidebar */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        color: #CBD5E1 !important;
        font-weight: 600;
    }

    /* Tab styling for modules */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        font-weight: 600;
    }

    /* Footer watermark */
    .footer-watermark {
        text-align: center;
        font-size: 0.7rem;
        color: #94A3B8;
        padding: 20px 0 10px 0;
        border-top: 1px solid #E2E8F0;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Database Initialization – auto-populate on first run
# ---------------------------------------------------------------------------
def initialize_database():
    """Initialize and populate the database if empty."""
    try:
        if not is_database_populated():
            with st.spinner("🚀 Initializing AtmoSync SQLite Database & Synthesizing 10,000 Linked Records..."):
                init_db(force_reset=True)
                initial_datasets = generate_all_datasets(total_target=10000)
                for t_name, t_df in initial_datasets.items():
                    save_dataframe_to_db(t_df, t_name, if_exists="append")
                logger.info("Database initialized and populated successfully.")
    except Exception as e:
        st.error(f"⚠️ Database initialization failed: {e}")
        logger.error(f"Database initialization error: {e}", exc_info=True)
        st.info("The application will continue but some features may be unavailable.")

initialize_database()

# ---------------------------------------------------------------------------
# Database connectivity check
# ---------------------------------------------------------------------------
def check_database_connection():
    """Verify database connectivity and return status."""
    try:
        counts = get_record_counts()
        total = counts.get("total", 0)
        return True, total
    except Exception as e:
        logger.error(f"Database connectivity check failed: {e}")
        return False, 0

db_connected, db_record_count = check_database_connection()

# ---------------------------------------------------------------------------
# Sidebar – Branding & Navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    # Logo or text branding
    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        try:
            st.image(str(logo_path), use_container_width=True)
        except Exception:
            st.markdown(f"## **{APP_NAME}**")
    else:
        st.markdown(f"## **{APP_NAME}**")

    st.markdown(
        f"<div style='font-size:0.75rem; color:#12B8A6; font-weight:700; "
        f"letter-spacing:0.5px; margin-top:-10px; margin-bottom:10px;'>"
        f"{APP_SUBTITLE.upper()}</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"{TAGLINE} • v{APP_VERSION}")

    # Database status indicator
    if db_connected:
        st.markdown(
            f"<div style='font-size:0.72rem; color:#16A34A; font-weight:600; "
            f"margin-bottom:8px;'>🟢 Database Online • {db_record_count:,} records</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-size:0.72rem; color:#DC2626; font-weight:600; "
            "margin-bottom:8px;'>🔴 Database Offline</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Alert Center Expander in Sidebar
    try:
        alerts_df = get_alerts()
        new_alerts = alerts_df[alerts_df["status"] == "New"] if not alerts_df.empty else pd.DataFrame()
        alert_badge = f"🔴 {len(new_alerts)}" if not new_alerts.empty else "🟢 0"

        with st.expander(f"🔔 Live Notification Alerts ({alert_badge})"):
            if not alerts_df.empty:
                st.caption(f"{len(new_alerts)} New • {len(alerts_df)} Total")
                alert_status_filter = st.selectbox(
                    "Status", ["All", "New", "Acknowledged", "Resolved"],
                    key="sb_alert_filter",
                )

                filtered_alerts = (
                    alerts_df
                    if alert_status_filter == "All"
                    else alerts_df[alerts_df["status"] == alert_status_filter]
                )

                for _, alt in filtered_alerts.head(8).iterrows():
                    sev_color = "#DC2626" if alt["severity"] == "Critical" else "#F59E0B"
                    desc_text = str(alt["description"])[:90]
                    st.markdown(
                        f"""
                    <div style="background:rgba(255,255,255,0.06); padding:8px;
                                border-radius:6px; margin-bottom:6px;
                                border-left:3px solid {sev_color};">
                        <div style="font-size:0.75rem; font-weight:700; color:#F8FAFC;">
                            {alt['alert_type']}
                        </div>
                        <div style="font-size:0.7rem; color:#CBD5E1;">
                            {desc_text}...
                        </div>
                        <div style="font-size:0.65rem; color:#94A3B8; margin-top:2px;">
                            Status: <b>{alt['status']}</b> | {alt['timestamp']}
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    if alt["status"] == "New":
                        c_a, c_r = st.columns(2)
                        with c_a:
                            if st.button("Acknowledge", key=f"ack_{alt['alert_id']}"):
                                update_alert_status(alt["alert_id"], "Acknowledged")
                                st.rerun()
                        with c_r:
                            if st.button("Resolve", key=f"res_{alt['alert_id']}"):
                                update_alert_status(alt["alert_id"], "Resolved")
                                st.rerun()
            else:
                st.info("No active alerts.")
    except Exception as e:
        logger.warning(f"Alert center rendering skipped: {e}")

    st.markdown("---")

    # Persistent Academic Disclaimer in Sidebar
    st.markdown(
        f"""
    <div style="font-size:0.7rem; color:#94A3B8; line-height:1.35; padding:8px;
                background:rgba(0,0,0,0.25); border-radius:6px;">
        <strong style="color:#2DD4BF;">ACADEMIC DISCLAIMER:</strong><br>
        {PERSISTENT_DISCLAIMER}
    </div>
    """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Multipage Navigation – All Eight Modules
# ---------------------------------------------------------------------------

# Define pages with safe import handling
PAGE_DEFINITIONS = [
    {"path": "pages/executive_dashboard.py", "title": "Executive Dashboard", "icon": "📊", "default": True},
    {"path": "pages/shipment_monitoring.py", "title": "Shipment Monitoring", "icon": "🚚", "default": False},
    {"path": "pages/iot_analytics.py", "title": "IoT Sensor Analytics", "icon": "📡", "default": False},
    {"path": "pages/commodity_analytics.py", "title": "Commodity Analytics", "icon": "🌾", "default": False},
    {"path": "pages/weather_analytics.py", "title": "Weather Analytics", "icon": "⛅", "default": False},
    {"path": "pages/spoilage_risk.py", "title": "Spoilage Risk Analysis", "icon": "⚠️", "default": False},
    {"path": "pages/market_arbitrage.py", "title": "Market Arbitrage Analysis", "icon": "💡", "default": False},
    {"path": "pages/reports.py", "title": "Reports and Data Management", "icon": "📑", "default": False},
]

pages = []
missing_pages = []

for page_def in PAGE_DEFINITIONS:
    page_file = APP_ROOT / page_def["path"]
    if page_file.exists():
        try:
            page = st.Page(
                page_def["path"],
                title=page_def["title"],
                icon=page_def["icon"],
                default=page_def["default"],
            )
            pages.append(page)
        except Exception as e:
            logger.error(f"Failed to register page '{page_def['title']}': {e}")
            missing_pages.append(page_def["title"])
    else:
        logger.warning(f"Page file not found: {page_def['path']}")
        missing_pages.append(page_def["title"])

# Report any missing pages (non-blocking)
if missing_pages:
    logger.warning(f"Missing page modules: {missing_pages}")

# Run navigation
if pages:
    pg = st.navigation(pages)
    pg.run()
else:
    st.error("⚠️ No page modules found. Please verify the `pages/` directory contains the required modules.")
    st.info("Expected modules: " + ", ".join(p["title"] for p in PAGE_DEFINITIONS))
