"""
End-to-End Streamlit App Integration Tests (Commit 3):
Verifies app.py and all 8 page modules render without exceptions or st.error,
and validates interactive filter state updates.
"""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


PAGE_FILES = [
    "app.py",
    "pages/executive_dashboard.py",
    "pages/shipment_monitoring.py",
    "pages/iot_analytics.py",
    "pages/commodity_analytics.py",
    "pages/weather_analytics.py",
    "pages/spoilage_risk.py",
    "pages/market_arbitrage.py",
    "pages/reports.py",
]


@pytest.mark.parametrize("page_path", PAGE_FILES)
def test_page_renders_without_errors(page_path):
    """Verify every page module executes cleanly in Streamlit AppTest without exceptions."""
    at = AppTest.from_file(str(PROJECT_ROOT / page_path), default_timeout=30)
    at.run()
    assert not at.exception, f"Unhandled exception in {page_path}: {[e.value for e in at.exception]}"
    assert not at.error, f"Unexpected st.error in {page_path}: {[e.value for e in at.error]}"


def test_executive_dashboard_filter_interaction():
    """Verify filtering on Executive Dashboard updates KPIs cleanly without errors."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/executive_dashboard.py"), default_timeout=30)
    at.run()
    assert not at.exception
    # Select 'At Risk' shipment status if available in selectbox
    for sb in at.sidebar.selectbox:
        if "Status" in sb.label and "At Risk" in sb.options:
            sb.set_value("At Risk").run()
            break
    assert not at.exception
    assert not at.error


def test_reports_page_report_type_switching():
    """Verify switching report types on Reports & Data Management works cleanly."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/reports.py"), default_timeout=30)
    at.run()
    assert not at.exception
    for sb in at.selectbox:
        if sb.label == "Select Analytical Report:":
            sb.set_value("Spoilage Risk Summary").run()
            break
    assert not at.exception
    assert not at.error
