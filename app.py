"""
AtmoSync - Micro-Climate Arbitrage Analytics
Root Application Entrypoint & Streamlit Multipage Orchestrator.
"""

import sys
from pathlib import Path

# Ensure application root is in python path
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import streamlit as st
import pandas as pd
from PIL import Image

from config.settings import (
    APP_NAME, APP_SUBTITLE, TAGLINE, APP_VERSION, 
    PERSISTENT_DISCLAIMER, COLORS, ASSETS_DIR
)
from database.database import (
    init_db, is_database_populated, save_dataframe_to_db, 
    get_record_counts, get_alerts, update_alert_status
)
from modules.data_generator import generate_all_datasets
from utils.helpers import get_status_badge

# Page Configuration (Wide layout, responsive title)
st.set_page_config(
    page_title=f"{APP_NAME} – {APP_SUBTITLE}",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load and inject custom CSS styling
css_file = ASSETS_DIR / "styles.css"
if css_file.exists():
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# First run: Initialize and synthesize database if unpopulated
if not is_database_populated():
    with st.spinner("🚀 Initializing AtmoSync SQLite Database & Synthesizing 10,000 Linked Records..."):
        init_db(force_reset=True)
        initial_datasets = generate_all_datasets(total_target=10000)
        for t_name, t_df in initial_datasets.items():
            save_dataframe_to_db(t_df, t_name, if_exists="append")

# Sidebar Branding
with st.sidebar:
    logo_path = ASSETS_DIR / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        st.markdown(f"## **{APP_NAME}**")
    
    st.markdown(f"<div style='font-size:0.75rem; color:#12B8A6; font-weight:700; letter-spacing:0.5px; margin-top:-10px; margin-bottom:10px;'>{APP_SUBTITLE.upper()}</div>", unsafe_allow_html=True)
    st.caption(f"{TAGLINE} • v{APP_VERSION}")
    st.markdown("---")

    # Alert Center Expander in Sidebar
    try:
        alerts_df = get_alerts()
        new_alerts = alerts_df[alerts_df["status"] == "New"] if not alerts_df.empty else pd.DataFrame()
        alert_badge = f"🔴 {len(new_alerts)}" if not new_alerts.empty else "🟢 0"
        
        with st.expander(f"🔔 Live Notification Alerts ({alert_badge})"):
            if not alerts_df.empty:
                st.caption(f"{len(new_alerts)} New • {len(alerts_df)} Total")
                alert_status_filter = st.selectbox("Status", ["All", "New", "Acknowledged", "Resolved"], key="sb_alert_filter")
                
                filtered_alerts = alerts_df if alert_status_filter == "All" else alerts_df[alerts_df["status"] == alert_status_filter]
                
                for _, alt in filtered_alerts.head(8).iterrows():
                    st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.06); padding:8px; border-radius:6px; margin-bottom:6px; border-left:3px solid {'#DC2626' if alt['severity']=='Critical' else '#F59E0B'};">
                        <div style="font-size:0.75rem; font-weight:700; color:#F8FAFC;">{alt['alert_type']}</div>
                        <div style="font-size:0.7rem; color:#CBD5E1;">{alt['description'][:90]}...</div>
                        <div style="font-size:0.65rem; color:#94A3B8; margin-top:2px;">Status: <b>{alt['status']}</b> | {alt['timestamp']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if alt["status"] == "New":
                        c_a, c_r = st.columns(2)
                        with c_a:
                            if st.button("Acknowledge", key=f"ack_{alt['alert_id']}"):
                                update_alert_status(alt['alert_id'], "Acknowledged")
                                st.rerun()
                        with c_r:
                            if st.button("Resolve", key=f"res_{alt['alert_id']}"):
                                update_alert_status(alt['alert_id'], "Resolved")
                                st.rerun()
            else:
                st.info("No active alerts.")
    except Exception:
        pass

    st.markdown("---")

    # Persistent Academic Disclaimer in Sidebar
    st.markdown(f"""
    <div style="font-size:0.7rem; color:#94A3B8; line-height:1.35; padding:8px; background:rgba(0,0,0,0.25); border-radius:6px;">
        <strong style="color:#2DD4BF;">ACADEMIC DISCLAIMER:</strong><br>
        {PERSISTENT_DISCLAIMER}
    </div>
    """, unsafe_allow_html=True)

# Multipage Navigation Setup using Streamlit Navigation API
pages = [
    st.Page("pages/executive_dashboard.py", title="Executive Dashboard", icon="📊", default=True),
    st.Page("pages/shipment_monitoring.py", title="Shipment Monitoring", icon="🚚"),
    st.Page("pages/iot_analytics.py", title="IoT Sensor Analytics", icon="📡"),
    st.Page("pages/commodity_analytics.py", title="Commodity Analytics", icon="🌾"),
    st.Page("pages/weather_analytics.py", title="Weather Analytics", icon="⛅"),
    st.Page("pages/spoilage_risk.py", title="Spoilage Risk Analysis", icon="⚠️"),
    st.Page("pages/market_arbitrage.py", title="Market Arbitrage Intelligence", icon="💡"),
    st.Page("pages/reports.py", title="Reports & Data Management", icon="📑")
]

pg = st.navigation(pages)
pg.run()
