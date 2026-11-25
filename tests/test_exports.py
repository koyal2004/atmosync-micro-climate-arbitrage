"""
Unit tests for data export pipelines and filtered analytical report generation:
ZIP archives, Excel workbooks (with metadata/disclaimers), PDF reports, and all 5 report types.
"""

import io
import zipfile
from datetime import date
import pytest
import pandas as pd
from openpyxl import load_workbook

from utils.export import (
    create_datasets_zip,
    create_excel_workbook,
    generate_pdf_report,
    build_filtered_report,
)
from database.database import load_table


@pytest.fixture
def sample_datasets():
    return {
        "commodities": load_table("commodities").head(20),
        "markets": load_table("markets").head(20),
        "shipments": load_table("shipments").head(20),
    }


@pytest.fixture
def full_datasets():
    return {
        "commodities": load_table("commodities"),
        "markets": load_table("markets"),
        "market_prices": load_table("market_prices"),
        "shipments": load_table("shipments"),
        "sensor_readings": load_table("sensor_readings"),
    }


def test_create_datasets_zip(sample_datasets):
    zip_bytes = create_datasets_zip(sample_datasets)
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        file_list = zf.namelist()
        assert "commodities.csv" in file_list
        assert "markets.csv" in file_list
        assert "shipments.csv" in file_list
        assert "README_METADATA.txt" in file_list


def test_create_excel_workbook_with_metadata(sample_datasets):
    excel_bytes = create_excel_workbook(sample_datasets, filter_summary="Test Scope: Fruit")
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    wb = load_workbook(io.BytesIO(excel_bytes), read_only=True)
    sheet_names = wb.sheetnames
    assert "Report_Metadata" in sheet_names
    assert "commodities" in sheet_names
    assert "markets" in sheet_names
    assert "shipments" in sheet_names

    meta_rows = list(wb["Report_Metadata"].iter_rows(values_only=True))
    meta_text = " ".join(str(cell) for row in meta_rows for cell in row if cell)
    assert "Test Scope: Fruit" in meta_text
    assert "synthetic" in meta_text.lower()


def test_generate_pdf_report():
    summary_metrics = {
        "total_shipments": 900,
        "active_shipments": 600,
        "at_risk_shipments": 45,
        "total_markets": 350,
        "avg_temp": 12.4,
        "avg_hum": 84.5,
        "total_arbitrage": 350,
        "max_benefit": 45000.0,
        "filter_scope": "Full Database Scope",
    }
    risk_summary = {
        "low": 700,
        "moderate": 150,
        "high": 40,
        "critical": 10,
        "avg_risk": 13.5,
        "avg_loss": 8.2,
    }
    quality_summary = {
        "completeness_pct": 100.0,
        "total_records": 9536,
        "foreign_key_violations": 0,
        "duplicate_counts": 0,
    }
    sample_arb = pd.DataFrame([{
        "shipment_id": "SHP-001",
        "commodity_name": "Tomato",
        "source_market_name": "Kolar",
        "alternative_market_name": "Azadpur",
        "gross_price_advantage": 12.5,
        "estimated_net_benefit": 7900.0,
    }])

    pdf_bytes = generate_pdf_report(
        summary_metrics, risk_summary, sample_arb, quality_summary
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.parametrize("rep_type,cat_filter", [
    ("Shipment Summary", "In Transit"),
    ("IoT Sensor Analytics", "Critical"),
    ("Commodity Price Analysis", "Fruit"),
    ("Spoilage Risk Summary", "Low"),
    ("Market Arbitrage Opportunities", "Profitable Only"),
])
def test_build_filtered_reports_all_types(full_datasets, rep_type, cat_filter):
    df, summary, scope = build_filtered_report(rep_type, full_datasets, category_filter=cat_filter)
    assert isinstance(df, pd.DataFrame)
    assert isinstance(summary, dict)
    assert rep_type in scope
    assert not df.empty

    if rep_type == "Shipment Summary":
        assert (df["shipment_status"] == "In Transit").all()
    elif rep_type == "IoT Sensor Analytics":
        assert (df["sensor_status"] == "Critical").all()
    elif rep_type == "Commodity Price Analysis":
        assert (df["category"] == "Fruit").all()
    elif rep_type == "Spoilage Risk Summary":
        assert (df["risk_category"] == "Low").all()
    elif rep_type == "Market Arbitrage Opportunities":
        assert (df["estimated_net_benefit"] > 0).all()


def test_build_filtered_report_empty_date_range(full_datasets):
    # Future date range with 0 matching records should return empty DataFrame cleanly
    df, summary, scope = build_filtered_report(
        "Shipment Summary",
        full_datasets,
        date_range=(date(2099, 1, 1), date(2099, 1, 5)),
        category_filter="All",
    )
    assert df.empty
    assert summary["Records"] == 0
