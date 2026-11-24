"""
Unit tests for advanced analytics: shipment performance, weather correlation,
spoilage factor decomposition, and non-overlapping arbitrage financial calculations.
"""

import pytest
import pandas as pd
import numpy as np
from database.database import load_table
from modules.analytics import (
    compute_shipment_performance_analytics,
    compute_spoilage_factor_breakdown,
    compute_weather_shipment_relationship,
    generate_automated_insights
)
from modules.risk_engine import calculate_shipment_risk
from modules.arbitrage_engine import evaluate_arbitrage_opportunities


@pytest.fixture
def core_data():
    return {
        "shipments": load_table("shipments"),
        "commodities": load_table("commodities"),
        "markets": load_table("markets"),
        "prices": load_table("market_prices"),
        "sensors": load_table("sensor_readings")
    }


def test_shipment_performance_analytics(core_data):
    ship_df = core_data["shipments"]
    perf = compute_shipment_performance_analytics(ship_df)
    assert perf["total_shipments"] == len(ship_df)
    assert 0.0 <= perf["on_time_rate_pct"] <= 100.0
    assert 0.0 <= perf["delay_rate_pct"] <= 100.0
    assert 0.0 <= perf["at_risk_rate_pct"] <= 100.0
    assert perf["avg_cost_per_ton_km"] >= 0.0
    assert perf["total_tonnage_mt"] > 0.0


def test_spoilage_factor_decomposition(core_data):
    risk_df = calculate_shipment_risk(core_data["shipments"], core_data["commodities"], core_data["sensors"])
    breakdown = compute_spoilage_factor_breakdown(risk_df)
    total_pct = breakdown["temp_contrib_pct"] + breakdown["hum_contrib_pct"] + breakdown["vibe_contrib_pct"]
    assert 99.0 <= total_pct <= 101.0  # Sums to ~100% within rounding
    assert breakdown["primary_stressor"] in [
        "Temperature Excursion", "Relative Humidity Condensation", "Mechanical Vibration & Shock"
    ]


def test_weather_shipment_relationship(core_data):
    rel_df = compute_weather_shipment_relationship(core_data["sensors"], core_data["shipments"])
    assert not rel_df.empty
    assert "shipment_status" in rel_df.columns
    assert "avg_temperature" in rel_df.columns
    assert "avg_vibration" in rel_df.columns
    assert len(rel_df) <= 5  # Status categories


def test_arbitrage_math_integrity_and_no_double_counting(core_data):
    risk_df = calculate_shipment_risk(core_data["shipments"], core_data["commodities"], core_data["sensors"])
    arb_df = evaluate_arbitrage_opportunities(
        core_data["shipments"], core_data["commodities"], core_data["markets"], core_data["prices"], risk_df
    )
    assert not arb_df.empty

    for _, row in arb_df.head(50).iterrows():
        # Verify gross advantage calculation: (P_dst - P_curr) * Q
        expected_gross = round(row["gross_price_advantage"] * row["quantity_kg"], 2)
        assert abs(row["gross_advantage"] - expected_gross) <= 0.05

        # Verify net benefit formula: Gross - Transport - Handling - Quality Loss
        expected_net = round(
            row["gross_advantage"] - row["transportation_cost"] - row["handling_cost"] - row["estimated_quality_loss_cost"], 2
        )
        assert abs(row["estimated_net_benefit"] - expected_net) <= 0.05

        # Verify profitability flag
        assert row["is_profitable"] == (row["estimated_net_benefit"] > 0)

        # Verify no negative transportation or handling costs
        assert row["transportation_cost"] >= 0.0
        assert row["handling_cost"] >= 0.0
        assert row["estimated_quality_loss_cost"] >= 0.0


def test_automated_insights_generation(core_data):
    insights = generate_automated_insights(
        core_data["prices"], core_data["shipments"], core_data["sensors"],
        pd.DataFrame(), core_data["commodities"]
    )
    assert isinstance(insights, list)
    assert len(insights) >= 2
    for ins in insights:
        assert "type" in ins
        assert "text" in ins
        assert len(ins["text"]) > 10
