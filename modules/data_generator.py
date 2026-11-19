"""
AtmoSync - Synthetic Dataset Generator
Programmatically generates 5,000 to 10,000 realistic, linked synthetic agricultural supply chain records.
Uses fixed seeds for complete reproducibility and validates referential integrity.
"""

import math
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Tuple

from config.settings import DEFAULT_RANDOM_SEED, DEFAULT_TOTAL_RECORDS, GENERATED_DATA_DIR
from utils.constants import (
    BASE_COMMODITIES, INDIAN_STATES_MARKETS, 
    SHIPMENT_STATUSES, SENSITIVITY_WEIGHTS
)
from utils.helpers import haversine_distance

def generate_all_datasets(total_target: int = 10000, seed: int = DEFAULT_RANDOM_SEED) -> Dict[str, pd.DataFrame]:
    """
    Generate all linked synthetic datasets according to the required distribution.
    All data is programmatically synthesized for academic research at Infotact.
    """
    np.random.seed(seed)
    random.seed(seed)

    # Determine allocation based on target size
    ratio = max(0.5, min(1.0, total_target / 10000.0))
    n_commodities = int(1000 * ratio)
    n_markets = int(500 * ratio)
    n_prices = int(3000 * ratio)
    n_shipments = int(1000 * ratio)
    n_sensors = int(4000 * ratio)
    n_arbitrage = int(500 * ratio)

    # 1. Generate Commodities Dataset
    commodities_df = _generate_commodities(n_commodities)

    # 2. Generate Markets Dataset
    markets_df = _generate_markets(n_markets)

    # 3. Generate Market Prices Dataset
    market_prices_df = _generate_market_prices(n_prices, commodities_df, markets_df)

    # 4. Generate Shipments Dataset
    shipments_df = _generate_shipments(n_shipments, commodities_df, markets_df)

    # 5. Generate IoT Sensor Dataset
    sensor_df, alerts_from_sensors = _generate_iot_sensors(n_sensors, shipments_df, commodities_df)

    # 6. Generate Arbitrage Dataset
    arbitrage_df = _generate_arbitrage(n_arbitrage, shipments_df, commodities_df, markets_df, market_prices_df)

    # 7. Generate Initial Alerts (Combining sensor alerts and operational alerts)
    alerts_df = _generate_alerts(alerts_from_sensors, shipments_df, arbitrage_df)

    # Save to generated data folder as CSV
    commodities_df.to_csv(GENERATED_DATA_DIR / "commodities.csv", index=False)
    markets_df.to_csv(GENERATED_DATA_DIR / "markets.csv", index=False)
    market_prices_df.to_csv(GENERATED_DATA_DIR / "market_prices.csv", index=False)
    shipments_df.to_csv(GENERATED_DATA_DIR / "shipments.csv", index=False)
    sensor_df.to_csv(GENERATED_DATA_DIR / "sensor_readings.csv", index=False)
    arbitrage_df.to_csv(GENERATED_DATA_DIR / "arbitrage_opportunities.csv", index=False)
    alerts_df.to_csv(GENERATED_DATA_DIR / "alerts.csv", index=False)

    return {
        "commodities": commodities_df,
        "markets": markets_df,
        "market_prices": market_prices_df,
        "shipments": shipments_df,
        "sensor_readings": sensor_df,
        "arbitrage_opportunities": arbitrage_df,
        "alerts": alerts_df
    }

def _generate_commodities(n_records: int) -> pd.DataFrame:
    records = []
    base_names = list(BASE_COMMODITIES.keys())
    grades = ["Grade-A Premium", "Grade-B Commercial", "Organic Certified", "Export Selection", "Farm-Gate Standard"]
    pack_types = ["Crate Pack", "Corrugated Carton", "Burlap Bag", "Punnets", "Clamshell"]

    count = 0
    while count < n_records:
        b_name = base_names[count % len(base_names)]
        meta = BASE_COMMODITIES[b_name]
        var = meta["varieties"][(count // len(base_names)) % len(meta["varieties"])]
        grade = grades[(count // (len(base_names) * len(meta["varieties"]))) % len(grades)]
        pack = pack_types[count % len(pack_types)]
        
        comm_id = f"COM-{count+1:04d}"
        full_name = f"{var} ({grade} - {pack})"

        # Slight price adjustment based on grade
        grade_mult = 1.25 if "Export" in grade else (1.15 if "Organic" in grade else (1.05 if "Grade-A" in grade else 0.95))
        base_p = round(meta["base_price"] * grade_mult * (1 + np.random.uniform(-0.08, 0.08)), 2)

        records.append({
            "commodity_id": comm_id,
            "commodity_name": full_name,
            "category": meta["category"],
            "base_price_per_kg": base_p,
            "optimal_temperature": round(meta["opt_temp"], 1),
            "minimum_temperature": round(meta["min_temp"], 1),
            "maximum_temperature": round(meta["max_temp"], 1),
            "optimal_humidity": round(meta["opt_humidity"], 1),
            "maximum_humidity": round(meta["max_humidity"], 1),
            "estimated_shelf_life_days": int(meta["shelf_life_days"]),
            "sensitivity_level": meta["sensitivity"]
        })
        count += 1

    return pd.DataFrame(records)

def _generate_markets(n_records: int) -> pd.DataFrame:
    records = []
    states = list(INDIAN_STATES_MARKETS.keys())
    types = ["Terminal Mandi", "Regional Hub", "Wholesale Hub", "Sub-Mandi", "Primary APMC", "Specialized Mandi"]

    count = 0
    # First add all authentic real-world hubs
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
                "estimated_daily_capacity": hub["cap"]
            })
            count += 1

    # Synthesize remaining regional/sub-markets distributed across the 10 states
    while count < n_records:
        state = states[count % len(states)]
        ref_hubs = INDIAN_STATES_MARKETS[state]
        parent_hub = ref_hubs[count % len(ref_hubs)]
        
        # Jitter coordinates slightly within agricultural perimeter (~10 to 45 km)
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
            "estimated_daily_capacity": int(parent_hub["cap"] * np.random.uniform(0.4, 0.85))
        })
        count += 1

    return pd.DataFrame(records)

def _generate_market_prices(n_records: int, comm_df: pd.DataFrame, mkt_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    base_date = datetime(2026, 8, 1) # Recent 90-day seasonal window
    comm_ids = comm_df["commodity_id"].tolist()
    mkt_ids = mkt_df["market_id"].tolist()
    
    # Pre-index base prices
    price_map = dict(zip(comm_df["commodity_id"], comm_df["base_price_per_kg"]))

    for i in range(n_records):
        p_id = f"PRC-{i+1:05d}"
        c_id = random.choice(comm_ids)
        m_id = random.choice(mkt_ids)
        day_offset = int(np.random.randint(0, 90))
        rec_date = (base_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

        base_p = price_map[c_id]
        
        # Seasonality wave + market variation
        seasonal_factor = 1.0 + 0.15 * math.sin(2 * math.pi * day_offset / 30.0)
        market_premium = np.random.uniform(-0.18, 0.22)
        
        # Injects ~3% price spikes (anomalies) for detection and arbitrage opportunity
        is_spike = np.random.rand() < 0.035
        spike_mult = np.random.uniform(1.4, 1.85) if is_spike else 1.0

        modal = round(base_p * seasonal_factor * (1.0 + market_premium) * spike_mult, 2)
        spread = modal * np.random.uniform(0.06, 0.18)
        
        min_p = round(max(2.0, modal - spread), 2)
        max_p = round(modal + spread, 2)
        
        # Ensure strict invariant: min <= modal <= max
        if min_p > modal:
            min_p = round(modal * 0.9, 2)
        if max_p < modal:
            max_p = round(modal * 1.1, 2)

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
            "supply_index": max(35.0, min(165.0, supply_idx))
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
        # Ensure minimum realistic transit distance
        distance = max(45.0, distance)

        # Dates
        dep_offset = int(np.random.randint(0, 45))
        dep_date = base_date + timedelta(days=dep_offset)
        # Transit duration approx 450 km per day
        transit_days = max(1, int(math.ceil(distance / 420.0)))
        arr_date = dep_date + timedelta(days=transit_days)

        # Quantity between 1.5 MT and 22 MT (typical reefer / refrigerated truck capacities)
        quantity = round(float(np.random.uniform(2000, 22000)), 0)
        
        # Transport cost: ₹18 - ₹28 per km based on truck size + base toll
        cost_per_km = 22.5 + (quantity / 5000.0) * 1.8
        transport_cost = round(distance * cost_per_km + 1500, 2)

        # Status distribution: ~45% Completed, 30% In Transit, 12% At Risk, 8% Delayed, 5% Delivered
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
        
        # Degradation estimation
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
            "distance_km": distance,
            "shipment_status": status,
            "initial_quality_percentage": init_qual,
            "estimated_remaining_shelf_life": rem_shelf
        })

    return pd.DataFrame(records)

def _generate_iot_sensors(n_records: int, ship_df: pd.DataFrame, comm_df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    records = []
    alerts = []
    
    # Pre-index commodity thresholds
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
        min_t = min_temp_map[c_id]
        opt_h = opt_hum_map[c_id]
        max_h = max_hum_map[c_id]

        dep_dt = datetime.strptime(ship["departure_date"], "%Y-%m-%d")

        # Determine if this shipment container suffers thermal stress
        has_thermal_fault = (status == "At Risk") or (np.random.rand() < 0.12)
        has_vibe_fault = np.random.rand() < 0.08

        # Generate time series points for this container
        for step in range(readings_per_shipment):
            if total_count >= n_records:
                break
            
            timestamp = dep_dt + timedelta(hours=step * 4, minutes=int(np.random.randint(0, 59)))
            
            # Base temperature with random diurnal oscillation
            diurnal = 1.2 * math.sin(step * 0.8)
            noise_t = np.random.normal(0, 0.4)
            
            if has_thermal_fault and step > (readings_per_shipment // 3):
                # Simulated refrigeration malfunction / temperature spike
                temp = round(max_t + np.random.uniform(2.5, 9.5), 2)
                hum = round(min(99.0, max_h + np.random.uniform(4.0, 12.0)), 1)
                sensor_stat = "Warning" if temp < max_t + 4.5 else "Critical"
                
                # Register alert
                alerts.append({
                    "alert_id": f"ALT-{len(alerts)+1:05d}",
                    "shipment_id": s_id,
                    "container_id": cont_id,
                    "alert_type": "High Temperature" if temp > max_t else "High Humidity",
                    "severity": "Critical" if sensor_stat == "Critical" else "High",
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": f"Container {cont_id} logged {temp}°C (optimal: {opt_t}°C, threshold: {max_t}°C). Spoilage risk escalated.",
                    "status": "New"
                })
            else:
                temp = round(opt_t + diurnal + noise_t, 2)
                hum = round(min(98.0, opt_h + np.random.normal(0, 2.0)), 1)
                sensor_stat = "Normal"

            # Vibration (g-force RMS)
            base_vibe = np.random.gamma(shape=2.0, scale=0.35)
            if has_vibe_fault and step % 2 == 0:
                base_vibe += np.random.uniform(2.8, 5.2) # Pot hole / mechanical impact
                alerts.append({
                    "alert_id": f"ALT-{len(alerts)+1:05d}",
                    "shipment_id": s_id,
                    "container_id": cont_id,
                    "alert_type": "Abnormal Vibration",
                    "severity": "Medium",
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "description": f"Excessive vibration ({round(base_vibe, 2)}g) registered on suspension axis.",
                    "status": "New"
                })

            records.append({
                "sensor_id": f"SNS-{sensor_idx:06d}",
                "shipment_id": s_id,
                "container_id": cont_id,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "temperature": temp,
                "humidity": hum,
                "vibration": round(float(base_vibe), 2),
                "sensor_status": sensor_stat
            })
            sensor_idx += 1
            total_count += 1

    return pd.DataFrame(records), alerts

def _generate_arbitrage(n_records: int, ship_df: pd.DataFrame, comm_df: pd.DataFrame, 
                        mkt_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    
    # Build quick lookup for average modal prices per (commodity, market)
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
        
        # Select an alternative market
        alt_dst_id = random.choice(mkt_ids)
        while alt_dst_id in [src_id, curr_dst_id]:
            alt_dst_id = random.choice(mkt_ids)

        src_p = avg_prices.get((c_id, src_id), 35.0)
        curr_p = avg_prices.get((c_id, curr_dst_id), src_p * 1.12)
        alt_p = avg_prices.get((c_id, alt_dst_id), curr_p * np.random.uniform(0.9, 1.45))

        # Coordinates
        curr_lat, curr_lon = mkt_lookup[curr_dst_id]
        alt_lat, alt_lon = mkt_lookup[alt_dst_id]
        
        # Additional rerouting distance from current destination or midway
        alt_dist = haversine_distance(curr_lat, curr_lon, alt_lat, alt_lon)
        add_trans_cost = round(alt_dist * 22.0 + 800, 2)
        add_handling_cost = round(qty * 0.45, 2) # ₹0.45 per kg handling/unloading at alt terminal

        # Spoilage impact on price
        qual_loss = 0.08 if ship["shipment_status"] == "At Risk" else 0.02
        
        gross_advantage = round(alt_p - curr_p, 2)
        gross_market_adv = gross_advantage * qty

        # Formulas per requirement:
        # Quality-Adjusted Destination Revenue: alt_p * qty * (1 - qual_loss)
        # Current Destination Revenue: curr_p * qty
        # Net Benefit: (Quality-Adjusted Destination Revenue) - (Current Destination Revenue) - add_trans_cost - add_handling_cost
        adj_revenue = alt_p * qty * (1.0 - qual_loss)
        curr_revenue = curr_p * qty
        net_benefit = round(adj_revenue - curr_revenue - add_trans_cost - add_handling_cost, 2)

        # Classification based on net benefit
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
            "destination_market_id": alt_dst_id, # Recommended alternative market
            "source_market_price": round(src_p, 2),
            "destination_market_price": round(alt_p, 2),
            "quantity_kg": qty,
            "estimated_quality_loss": round(qual_loss, 3),
            "transportation_cost": add_trans_cost,
            "handling_cost": add_handling_cost,
            "gross_price_advantage": gross_advantage,
            "estimated_net_benefit": net_benefit,
            "recommendation_status": rec_status
        })
        opp_count += 1

    return pd.DataFrame(records)

def _generate_alerts(sensor_alerts: list, ship_df: pd.DataFrame, arb_df: pd.DataFrame) -> pd.DataFrame:
    alerts = list(sensor_alerts)
    
    # Add alerts for High Spoilage Risk
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
            "status": "New"
        })

    # Add alerts for High Arbitrage Opportunity
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
            "status": "New"
        })

    return pd.DataFrame(alerts)
