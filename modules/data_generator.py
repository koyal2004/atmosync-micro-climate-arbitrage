"""
AtmoSync - Synthetic Dataset Generator
Programmatically generates 5,000 to 10,000 realistic, linked synthetic agricultural supply chain records.
Uses fixed seeds for complete reproducibility, enforces referential integrity, and integrates preprocessing.
"""

import math
import random
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple, Any, Optional

import numpy as np
import pandas as pd

from config.settings import DEFAULT_RANDOM_SEED, DEFAULT_TOTAL_RECORDS, GENERATED_DATA_DIR, DB_PATH
from utils.constants import (
    BASE_COMMODITIES, INDIAN_STATES_MARKETS, 
    SHIPMENT_STATUSES, SENSITIVITY_WEIGHTS
)
from utils.helpers import haversine_distance
from modules.data_cleaning import clean_and_preprocess_all, run_comprehensive_validation
from database.database import init_db, save_dataframe_to_db, get_record_counts

logger = logging.getLogger("atmosync.data_generator")

# Priority commodities and market districts to ensure required items are always present
PRIORITY_COMMODITIES = ["Mango", "Banana", "Apple", "Tomato", "Onion", "Potato"]
PRIORITY_MARKET_DISTRICTS = ["Chennai", "Bengaluru", "Hyderabad", "Navi Mumbai", "Pune", "Ernakulam"]

def generate_all_datasets(total_target: int = 10000, seed: int = DEFAULT_RANDOM_SEED) -> Dict[str, pd.DataFrame]:
    """
    Generate all linked synthetic datasets according to required distribution.
    Enforces reproducible seeds, runs data preprocessing/cleaning, and adds synthetic labels.
    """
    np.random.seed(seed)
    random.seed(seed)

    # Determine allocation based on target size (between 5,000 and 10,000)
    target = max(5000, min(10000, total_target))
    ratio = target / 10000.0

    n_commodities = max(100, int(700 * ratio))
    n_markets = max(50, int(350 * ratio))
    n_prices = max(1200, int(3000 * ratio))
    n_shipments = max(400, int(900 * ratio))
    n_sensors = max(1800, int(3800 * ratio))
    n_arbitrage = max(150, int(350 * ratio))

    # 1. Generate Commodities Dataset (with priority commodities guaranteed)
    commodities_df = _generate_commodities(n_commodities)

    # 2. Generate Markets Dataset (with priority Indian markets guaranteed)
    markets_df = _generate_markets(n_markets)

    # 3. Generate Market Prices Dataset
    market_prices_df = _generate_market_prices(n_prices, commodities_df, markets_df)

    # 4. Generate Shipments Dataset
    shipments_df = _generate_shipments(n_shipments, commodities_df, markets_df)

    # 5. Generate IoT Sensor Dataset
    sensor_df, alerts_from_sensors = _generate_iot_sensors(n_sensors, shipments_df, commodities_df)

    # 6. Generate Arbitrage Dataset
    arbitrage_df = _generate_arbitrage(n_arbitrage, shipments_df, commodities_df, markets_df, market_prices_df)

    # 7. Generate Alerts Dataset
    alerts_df = _generate_alerts(alerts_from_sensors, shipments_df, arbitrage_df)

    raw_datasets = {
        "commodities": commodities_df,
        "markets": markets_df,
        "market_prices": market_prices_df,
        "shipments": shipments_df,
        "sensor_readings": sensor_df,
        "arbitrage_opportunities": arbitrage_df,
        "alerts": alerts_df
    }

    # Run data cleaning and preprocessing to ensure zero violations
    cleaned_datasets, audit_report = clean_and_preprocess_all(raw_datasets)

    # Save to generated data folder as CSV files
    GENERATED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in cleaned_datasets.items():
        csv_path = GENERATED_DATA_DIR / f"{name}.csv"
        df.to_csv(csv_path, index=False)

    return cleaned_datasets

def _generate_commodities(n_records: int) -> pd.DataFrame:
    records = []
    # Place priority commodities first
    all_names = list(BASE_COMMODITIES.keys())
    ordered_names = [c for c in PRIORITY_COMMODITIES if c in all_names] + [c for c in all_names if c not in PRIORITY_COMMODITIES]

    grades = ["Grade-A Premium", "Grade-B Commercial", "Organic Certified", "Export Selection", "Farm-Gate Standard"]
    pack_types = ["Crate Pack", "Corrugated Carton", "Burlap Bag", "Punnets", "Clamshell"]

    count = 0
    while count < n_records:
        b_name = ordered_names[count % len(ordered_names)]
        meta = BASE_COMMODITIES[b_name]
        var = meta["varieties"][(count // len(ordered_names)) % len(meta["varieties"])]
        grade = grades[(count // (len(ordered_names) * len(meta["varieties"]))) % len(grades)]
        pack = pack_types[count % len(pack_types)]
        
        comm_id = f"COM-{count+1:04d}"
        full_name = f"{b_name} - {var} ({grade} - {pack})"

        grade_mult = 1.25 if "Export" in grade else (1.15 if "Organic" in grade else (1.05 if "Grade-A" in grade else 0.95))
        base_p = round(meta["base_price"] * grade_mult * (1 + np.random.uniform(-0.08, 0.08)), 2)

        records.append({
            "commodity_id": comm_id,
            "commodity_name": full_name,
            "category": meta["category"],
            "base_price_per_kg": max(1.0, base_p),
            "optimal_temperature": round(meta["opt_temp"], 1),
            "minimum_temperature": round(meta["min_temp"], 1),
            "maximum_temperature": round(meta["max_temp"], 1),
            "optimal_humidity": round(meta["opt_humidity"], 1),
            "maximum_humidity": round(meta["max_humidity"], 1),
            "estimated_shelf_life_days": int(meta["shelf_life_days"]),
            "sensitivity_level": meta["sensitivity"],
            "is_synthetic": 1
        })
        count += 1

    return pd.DataFrame(records)

def _generate_markets(n_records: int) -> pd.DataFrame:
    records = []
    states = list(INDIAN_STATES_MARKETS.keys())
    types = ["Terminal Mandi", "Regional Hub", "Wholesale Hub", "Sub-Mandi", "Primary APMC", "Specialized Mandi"]

    count = 0
    # First add authentic real-world hubs, prioritizing Chennai, Bengaluru, Hyderabad, Mumbai, Pune, Kochi
    for state, hubs in INDIAN_STATES_MARKETS.items():
        for hub in hubs:
            if count >= n_records:
                break
            records.append({
                "market_id": f"MKT-{count+1:04d}",
                "market_name": hub["name"],
                "state": state,
                "district": hub["district"],
                "latitude": round(hub["lat"], 4),
                "longitude": round(hub["lon"], 4),
                "market_type": hub["type"],
                "estimated_daily_capacity": hub["cap"],
                "is_synthetic": 1
            })
            count += 1

    # Synthesize remaining regional/sub-markets distributed across states
    while count < n_records:
        state = states[count % len(states)]
        ref_hubs = INDIAN_STATES_MARKETS[state]
        parent_hub = ref_hubs[count % len(ref_hubs)]
        
        lat_offset = np.random.uniform(-0.35, 0.35)
        lon_offset = np.random.uniform(-0.35, 0.35)
        m_type = types[count % len(types)]
        district = parent_hub["district"]
        
        m_id = f"MKT-{count+1:04d}"
        m_name = f"{district} Sub-Division Yard {count+1}"

        records.append({
            "market_id": m_id,
            "market_name": m_name,
            "state": state,
            "district": district,
            "latitude": round(parent_hub["lat"] + lat_offset, 4),
            "longitude": round(parent_hub["lon"] + lon_offset, 4),
            "market_type": m_type,
            "estimated_daily_capacity": int(parent_hub["cap"] * np.random.uniform(0.4, 0.85)),
            "is_synthetic": 1
        })
        count += 1

    return pd.DataFrame(records)

def _generate_market_prices(n_records: int, comm_df: pd.DataFrame, mkt_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    base_date = datetime(2026, 8, 1)
    comm_ids = comm_df["commodity_id"].tolist()
    mkt_ids = mkt_df["market_id"].tolist()
    
    price_map = dict(zip(comm_df["commodity_id"], comm_df["base_price_per_kg"]))

    for i in range(n_records):
        p_id = f"PRC-{i+1:05d}"
        c_id = random.choice(comm_ids)
        m_id = random.choice(mkt_ids)
        day_offset = int(np.random.randint(0, 90))
        rec_date = (base_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        base_p = price_map[c_id]
        
        seasonal_factor = 1.0 + 0.15 * math.sin(2 * math.pi * day_offset / 30.0)
        market_premium = np.random.uniform(-0.18, 0.22)
        
        is_spike = np.random.rand() < 0.035
        spike_mult = np.random.uniform(1.4, 1.85) if is_spike else 1.0

        modal = round(base_p * seasonal_factor * (1.0 + market_premium) * spike_mult, 2)
        modal = max(2.0, modal)
        spread = modal * np.random.uniform(0.06, 0.18)
        
        min_p = round(max(1.0, modal - spread), 2)
        max_p = round(modal + spread, 2)
        
        # Invariant: minimum_price <= modal_price <= maximum_price
        if min_p > modal:
            min_p = round(modal * 0.9, 2)
        if max_p < modal:
            max_p = round(modal * 1.1, 2)
        if min_p >= max_p:
            max_p = round(min_p + 1.0, 2)

        arrival = round(float(np.random.exponential(scale=4500) + 500), 1)
        demand_idx = round(float(np.random.normal(100, 15)), 1)
        supply_idx = round(float(np.random.normal(100, 18)), 1)

        records.append({
            "price_id": p_id,
            "date": rec_date,
            "commodity_id": c_id,
            "market_id": m_id,
            "minimum_price": min_p,
            "maximum_price": max_p,
            "modal_price": modal,
            "arrival_quantity": arrival,
            "demand_index": max(40.0, min(160.0, demand_idx)),
            "supply_index": max(35.0, min(165.0, supply_idx)),
            "is_synthetic": 1
        })

    return pd.DataFrame(records)

def _generate_shipments(n_records: int, comm_df: pd.DataFrame, mkt_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    comm_ids = comm_df["commodity_id"].tolist()
    mkt_lookup = {row["market_id"]: (row["latitude"], row["longitude"]) for _, row in mkt_df.iterrows()}
    mkt_ids = list(mkt_lookup.keys())
    shelf_map = dict(zip(comm_df["commodity_id"], comm_df["estimated_shelf_life_days"]))

    base_date = datetime(2026, 10, 1)

    for i in range(n_records):
        s_id = f"SHP-{i+1:04d}"
        c_id = random.choice(comm_ids)
        src_id = random.choice(mkt_ids)
        dest_id = random.choice(mkt_ids)
        while dest_id == src_id:
            dest_id = random.choice(mkt_ids)

        src_lat, src_lon = mkt_lookup[src_id]
        dst_lat, dst_lon = mkt_lookup[dest_id]
        distance = haversine_distance(src_lat, src_lon, dst_lat, dst_lon)
        distance = max(45.0, distance)

        dep_offset = int(np.random.randint(0, 45))
        dep_date = base_date + timedelta(days=dep_offset)
        transit_days = max(1, int(math.ceil(distance / 420.0)))
        arr_date = dep_date + timedelta(days=transit_days)

        quantity = round(float(np.random.uniform(2000, 22000)), 0)
        
        cost_per_km = 22.5 + (quantity / 5000.0) * 1.8
        transport_cost = round(distance * cost_per_km + 1500, 2)

        rand_status = np.random.rand()
        if rand_status < 0.14:
            status = "At Risk"
        elif rand_status < 0.22:
            status = "Delayed"
        elif rand_status < 0.54:
            status = "In Transit"
        elif rand_status < 0.65:
            status = "Delivered"
        else:
            status = "Completed"

        init_qual = round(float(np.random.uniform(94.0, 99.8)), 1)
        base_shelf = shelf_map[c_id]
        
        elapsed = min(transit_days, 5)
        rem_shelf = max(0.5, round(base_shelf - elapsed * (1.8 if status in ["At Risk", "Delayed"] else 1.0), 1))

        records.append({
            "shipment_id": s_id,
            "container_id": f"CONT-{1000 + (i % 350)}",
            "commodity_id": c_id,
            "source_market_id": src_id,
            "destination_market_id": dest_id,
            "departure_date": dep_date.strftime("%Y-%m-%d"),
            "expected_arrival_date": arr_date.strftime("%Y-%m-%d"),
            "quantity_kg": quantity,
            "transport_cost": transport_cost,
            "distance_km": round(distance, 1),
            "shipment_status": status,
            "initial_quality_percentage": init_qual,
            "estimated_remaining_shelf_life": rem_shelf,
            "is_synthetic": 1
        })

    return pd.DataFrame(records)

def _generate_iot_sensors(n_records: int, ship_df: pd.DataFrame, comm_df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    records = []
    alerts = []
    
    opt_temp_map = dict(zip(comm_df["commodity_id"], comm_df["optimal_temperature"]))
    max_temp_map = dict(zip(comm_df["commodity_id"], comm_df["maximum_temperature"]))
    min_temp_map = dict(zip(comm_df["commodity_id"], comm_df["minimum_temperature"]))
    opt_hum_map = dict(zip(comm_df["commodity_id"], comm_df["optimal_humidity"]))
    max_hum_map = dict(zip(comm_df["commodity_id"], comm_df["maximum_humidity"]))

    shipments_list = ship_df.to_dict("records")
    readings_per_shipment = max(2, n_records // len(shipments_list))

    total_count = 0
    sensor_idx = 1

    for ship in shipments_list:
        if total_count >= n_records:
            break
        
        s_id = ship["shipment_id"]
        cont_id = ship["container_id"]
        c_id = ship["commodity_id"]
        status = ship["shipment_status"]
        
        opt_t = opt_temp_map[c_id]
        max_t = max_temp_map[c_id]
        opt_h = opt_hum_map[c_id]
        max_h = max_hum_map[c_id]

        dep_dt = datetime.strptime(ship["departure_date"], "%Y-%m-%d")

        has_thermal_fault = (status == "At Risk") or (np.random.rand() < 0.12)
        has_vibe_fault = np.random.rand() < 0.08

        for step in range(readings_per_shipment):
            if total_count >= n_records:
                break
            
            timestamp = dep_dt + timedelta(hours=step * 4, minutes=int(np.random.randint(0, 59)))
            diurnal = 1.2 * math.sin(step * 0.8)
            noise_t = np.random.normal(0, 0.4)
            
            if has_thermal_fault and step > (readings_per_shipment // 3):
                temp = round(max_t + np.random.uniform(2.5, 9.5), 2)
                hum = round(min(99.0, max_h + np.random.uniform(4.0, 12.0)), 1)
                sensor_stat = "Warning" if temp < max_t + 4.5 else "Critical"
                
                alerts.append({
                    "alert_id": f"ALT-{len(alerts)+1:05d}",
                    "shipment_id": s_id,
                    "container_id": cont_id,
                    "alert_type": "High Temperature" if temp > max_t else "High Humidity",
                    "severity": "Critical" if sensor_stat == "Critical" else "High",
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": f"Container {cont_id} logged {temp}°C (optimal: {opt_t}°C, threshold: {max_t}°C). Spoilage risk escalated.",
                    "status": "New",
                    "is_synthetic": 1
                })
            else:
                temp = round(opt_t + diurnal + noise_t, 2)
                hum = round(min(98.0, opt_h + np.random.normal(0, 2.0)), 1)
                sensor_stat = "Normal"

            base_vibe = np.random.gamma(shape=2.0, scale=0.35)
            if has_vibe_fault and step % 2 == 0:
                base_vibe += np.random.uniform(2.8, 5.2)
                alerts.append({
                    "alert_id": f"ALT-{len(alerts)+1:05d}",
                    "shipment_id": s_id,
                    "container_id": cont_id,
                    "alert_type": "Abnormal Vibration",
                    "severity": "Medium",
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": f"Excessive vibration ({round(base_vibe, 2)}g) registered on suspension axis.",
                    "status": "New",
                    "is_synthetic": 1
                })

            records.append({
                "sensor_id": f"SNS-{sensor_idx:06d}",
                "shipment_id": s_id,
                "container_id": cont_id,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "temperature": temp,
                "humidity": hum,
                "vibration": round(float(base_vibe), 2),
                "sensor_status": sensor_stat,
                "is_synthetic": 1
            })
            sensor_idx += 1
            total_count += 1

    return pd.DataFrame(records), alerts

def _generate_arbitrage(n_records: int, ship_df: pd.DataFrame, comm_df: pd.DataFrame, 
                        mkt_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    
    avg_prices = price_df.groupby(["commodity_id", "market_id"])["modal_price"].mean().to_dict()
    mkt_lookup = {row["market_id"]: (row["latitude"], row["longitude"]) for _, row in mkt_df.iterrows()}
    mkt_ids = list(mkt_lookup.keys())
    
    shipments = ship_df.to_dict("records")
    
    opp_count = 0
    while opp_count < n_records:
        ship = random.choice(shipments)
        s_id = ship["shipment_id"]
        c_id = ship["commodity_id"]
        src_id = ship["source_market_id"]
        curr_dst_id = ship["destination_market_id"]
        qty = ship["quantity_kg"]
        
        alt_dst_id = random.choice(mkt_ids)
        while alt_dst_id in [src_id, curr_dst_id]:
            alt_dst_id = random.choice(mkt_ids)

        src_p = avg_prices.get((c_id, src_id), 35.0)
        curr_p = avg_prices.get((c_id, curr_dst_id), src_p * 1.12)
        alt_p = avg_prices.get((c_id, alt_dst_id), curr_p * np.random.uniform(0.9, 1.45))

        curr_lat, curr_lon = mkt_lookup[curr_dst_id]
        alt_lat, alt_lon = mkt_lookup[alt_dst_id]
        
        alt_dist = haversine_distance(curr_lat, curr_lon, alt_lat, alt_lon)
        add_trans_cost = round(alt_dist * 22.0 + 800, 2)
        add_handling_cost = round(qty * 0.45, 2)

        qual_loss = 0.08 if ship["shipment_status"] == "At Risk" else 0.02
        gross_advantage = round(alt_p - curr_p, 2)

        adj_revenue = alt_p * qty * (1.0 - qual_loss)
        curr_revenue = curr_p * qty
        net_benefit = round(adj_revenue - curr_revenue - add_trans_cost - add_handling_cost, 2)

        if net_benefit > 35000:
            rec_status = "High Opportunity"
        elif net_benefit > 10000:
            rec_status = "Moderate Opportunity"
        elif net_benefit > 0:
            rec_status = "Low Opportunity"
        else:
            rec_status = "Not Recommended"

        records.append({
            "opportunity_id": f"ARB-{opp_count+1:05d}",
            "shipment_id": s_id,
            "commodity_id": c_id,
            "source_market_id": src_id,
            "destination_market_id": alt_dst_id,
            "source_market_price": round(src_p, 2),
            "destination_market_price": round(alt_p, 2),
            "quantity_kg": qty,
            "estimated_quality_loss": round(qual_loss, 3),
            "transportation_cost": add_trans_cost,
            "handling_cost": add_handling_cost,
            "gross_price_advantage": gross_advantage,
            "estimated_net_benefit": net_benefit,
            "recommendation_status": rec_status,
            "is_synthetic": 1
        })
        opp_count += 1

    return pd.DataFrame(records)

def _generate_alerts(sensor_alerts: list, ship_df: pd.DataFrame, arb_df: pd.DataFrame) -> pd.DataFrame:
    alerts = list(sensor_alerts)
    
    at_risk_ships = ship_df[ship_df["shipment_status"] == "At Risk"]
    for _, ship in at_risk_ships.head(40).iterrows():
        alerts.append({
            "alert_id": f"ALT-{len(alerts)+1:05d}",
            "shipment_id": ship["shipment_id"],
            "container_id": ship["container_id"],
            "alert_type": "High Spoilage Risk",
            "severity": "Critical",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"Shipment {ship['shipment_id']} cumulative spoilage risk exceeded threshold (>75). Rerouting suggested.",
            "status": "New",
            "is_synthetic": 1
        })

    high_arb = arb_df[arb_df["recommendation_status"] == "High Opportunity"]
    for _, arb in high_arb.head(30).iterrows():
        alerts.append({
            "alert_id": f"ALT-{len(alerts)+1:05d}",
            "shipment_id": arb["shipment_id"],
            "container_id": "FLEET-ROUTER",
            "alert_type": "Potential Arbitrage Opportunity",
            "severity": "Medium",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"Arbitrage opportunity {arb['opportunity_id']} offers estimated net gain of ₹{arb['estimated_net_benefit']:,.2f}.",
            "status": "New",
            "is_synthetic": 1
        })

    return pd.DataFrame(alerts)

# ---------------------------------------------------------------------------
# Controlled Initialization and Reset API
# ---------------------------------------------------------------------------
def generate_and_persist_datasets(
    total_target: int = DEFAULT_TOTAL_RECORDS,
    seed: int = DEFAULT_RANDOM_SEED,
    force_reset: bool = True,
    db_path: Optional[Path] = None
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """
    Generate, preprocess, validate, and persist synthetic datasets to SQLite.
    Controlled way to re-initialize or reset synthetic data.
    """
    logger.info(f"Generating synthetic datasets (target: {total_target}, seed: {seed})...")
    datasets = generate_all_datasets(total_target=total_target, seed=seed)

    # Initialize SQLite database schema
    init_db(force_reset=force_reset, db_path=db_path)

    # Persist all cleaned tables in relational order
    order = ["commodities", "markets", "market_prices", "shipments", "sensor_readings", "arbitrage_opportunities", "alerts"]
    for table_name in order:
        df = datasets.get(table_name)
        if df is not None and not df.empty:
            save_dataframe_to_db(df, table_name, if_exists="append", db_path=db_path)

    # Perform post-load audit
    audit = run_comprehensive_validation(datasets)
    counts = get_record_counts(db_path=db_path)
    logger.info(f"Successfully generated and stored {counts.get('total', 0):,} records in SQLite.")

    return datasets, audit

def reset_synthetic_data(
    total_target: int = DEFAULT_TOTAL_RECORDS,
    seed: int = DEFAULT_RANDOM_SEED,
    db_path: Optional[Path] = None
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """Controlled helper to reset and repopulate synthetic records in SQLite."""
    return generate_and_persist_datasets(total_target=total_target, seed=seed, force_reset=True, db_path=db_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AtmoSync Synthetic Dataset Generator & Preprocessor")
    parser.add_argument("--target", type=int, default=10000, help="Target total records (5,000 to 10,000)")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for reproducibility")
    parser.add_argument("--reset", action="store_true", help="Force reset and re-populate SQLite database")
    args = parser.parse_args()

    print(f"Generating synthetic records for AtmoSync (target: {args.target}, seed: {args.seed})...")
    datasets, audit = generate_and_persist_datasets(total_target=args.target, seed=args.seed, force_reset=args.reset)
    print("Audit Report:")
    print(f"  Total records generated: {audit['total_records']}")
    print(f"  Referential FK violations: {audit['foreign_key_violations']}")
    print(f"  Missing null values: {audit['null_value_counts']}")
    print(f"  Duplicate primary keys: {audit['duplicate_counts']}")
    print(f"  Range constraint violations: {audit['range_violations']}")
    print(f"  Overall Validation Status: {'PASSED' if audit['is_valid'] else 'FAILED'}")
