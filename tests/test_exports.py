"""
Unit tests for data export pipelines: ZIP archives, Excel workbooks, and PDF reports.
"""

import pytest
import io
import zipfile
import pandas as pd
from openpyxl import load_workbook
from utils.export import create_datasets_zip, create_excel_workbook, generate_pdf_report
from database.database import load_table


@pytest.fixture
def sample_datasets():
    return {
        "commodities": load_table("commodities").head(10),
        "markets": load_table("markets").head(10),
        "shipments": load_table("shipments").head(10),
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


def test_create_excel_workbook(sample_datasets):
    excel_bytes = create_excel_workbook(sample_datasets)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    wb = load_workbook(io.BytesIO(excel_bytes), read_only=True)
    sheet_names = wb.sheetnames
    assert "commodities" in sheet_names
    assert "markets" in sheet_names
    assert "shipments" in sheet_names


def test_generate_pdf_report():
    summary_metrics = {
        "total_shipments": 900,
        "active_shipments": 600,
        "total_commodities": 15,
        "total_markets": 20,
        "total_readings": 4500,
        "high_risk": 45,
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
        "null_cells": 0,
        "duplicate_pks": 0,
        "foreign_key_violations": 0,
    }
    sample_arb = pd.DataFrame([{
        "shipment_id": "SHP-001",
        "commodity_name": "Tomato",
        "source_market_name": "Kolar",
        "alternative_market_name": "Azadpur",
        "gross_advantage": 15000.0,
        "transportation_cost": 4200.0,
        "handling_cost": 800.0,
        "estimated_quality_loss_cost": 2100.0,
        "estimated_net_benefit": 7900.0,
    }])

    pdf_bytes = generate_pdf_report(
        summary_metrics, risk_summary, sample_arb, quality_summary
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
