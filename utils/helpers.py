"""
AtmoSync - Helper Utilities
Formatting, Haversine geospatial calculations, and UI helper components.
"""

import logging
import math
import re
from datetime import datetime
from typing import Union, Optional

_helpers_logger = logging.getLogger("atmosync.helpers")


def sanitize_error_message(err: Union[Exception, str], user_context: str = "Operation failed") -> str:
    """
    Return a safe, user-facing error message without exposing internal filesystem paths,
    credentials, or sensitive tokens.
    """
    raw = str(err or "").strip()
    # Mask Windows drive paths (e.g., C:\Users\Admin\...) and Unix root paths
    redacted = re.sub(r"[A-Za-z]:\\[^\s'\"]+", "<local-path>", raw)
    redacted = re.sub(r"/(?:home|Users|var|etc|opt|tmp)/[^\s'\"]+", "<local-path>", redacted)
    # Mask key/token/password assignments if ever present
    redacted = re.sub(
        r"(?i)(api[_-]?key|secret|password|token|bearer)\s*[:=]\s*\S+",
        r"\1=<redacted>",
        redacted,
    )
    _helpers_logger.error("%s: %s", user_context, redacted)
    if not redacted:
        return f"{user_context}. Please verify your data or configuration and try again."
    # Keep message concise and safe
    short_detail = redacted.splitlines()[0][:180]
    return f"{user_context}: {short_detail}"

def format_currency(value: Union[int, float], symbol: str = "₹") -> str:
    """Format numbers as Indian Rupee amounts with comma separators."""
    if value is None or math.isnan(value):
        return f"{symbol}0.00"
    is_neg = value < 0
    abs_val = abs(value)
    if abs_val >= 10_000_000:
        return f"{'-' if is_neg else ''}{symbol}{abs_val/10_000_000:.2f} Cr"
    elif abs_val >= 100_000:
        return f"{'-' if is_neg else ''}{symbol}{abs_val/100_000:.2f} L"
    else:
        return f"{'-' if is_neg else ''}{symbol}{abs_val:,.2f}"

def format_quantity(kg: Union[int, float]) -> str:
    """Format kg into Metric Tonnes or Quintals."""
    if kg is None or math.isnan(kg):
        return "0 kg"
    if kg >= 1000:
        return f"{kg / 1000:.2f} MT ({kg:,.0f} kg)"
    return f"{kg:,.0f} kg"

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in kilometers."""
    R = 6371.0 # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

def get_status_badge(status: str) -> str:
    """Generate HTML pill badge for shipment or sensor status."""
    status_lower = status.lower()
    color_map = {
        "delivered": ("#DCFCE7", "#15803D"),
        "completed": ("#DCFCE7", "#15803D"),
        "in transit": ("#E0F2FE", "#0369A1"),
        "normal": ("#E0F2FE", "#0369A1"),
        "at risk": ("#FEE2E2", "#B91C1C"),
        "critical": ("#FEE2E2", "#B91C1C"),
        "high risk": ("#FFEDD5", "#C2410C"),
        "delayed": ("#FEF3C7", "#B45309"),
        "warning": ("#FEF3C7", "#B45309"),
        "anomaly": ("#FEE2E2", "#B91C1C"),
        "high opportunity": ("#DCFCE7", "#15803D"),
        "moderate opportunity": ("#CCFBF1", "#0F766E"),
        "low opportunity": ("#FEF3C7", "#B45309"),
        "not recommended": ("#F1F5F9", "#475569")
    }
    bg, fg = color_map.get(status_lower, ("#F1F5F9", "#475569"))
    return f'<span style="background-color:{bg}; color:{fg}; padding:3px 10px; border-radius:12px; font-weight:600; font-size:0.8rem; display:inline-block;">{status}</span>'

def render_kpi_card(title: str, value: str, subtext: str = "", delta: Optional[str] = None, delta_color: str = "normal", icon: str = "") -> str:
    """Generate styled HTML KPI Card."""
    delta_html = ""
    if delta:
        d_color = "#16A34A" if delta_color == "positive" else ("#DC2626" if delta_color == "negative" else "#64748B")
        delta_html = f'<div style="font-size: 0.8rem; color: {d_color}; margin-top: 4px; font-weight:600;">{delta}</div>'

    icon_html = f'<span style="font-size: 1.4rem; opacity: 0.85;">{icon}</span>' if icon else ""

    html = f"""
    <div style="
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 700; color: #64748B;">
                {title}
            </span>
            {icon_html}
        </div>
        <div style="font-size: 1.65rem; font-weight: 800; color: #10243A; margin: 8px 0 2px 0; letter-spacing: -0.5px;">
            {value}
        </div>
        <div>
            {delta_html}
            <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 2px;">{subtext}</div>
        </div>
    </div>
    """
    return html
