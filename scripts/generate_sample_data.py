"""
OpenData Sentinel - Sample Dataset Generator
Creates realistic, authenticated Indian Government demonstration datasets
reflecting data.gov.in formats, schemas, and realistic distributions.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_agri_mandi_prices():
    """
    Ministry of Agriculture & Farmers Welfare, Directorate of Marketing & Inspection (DMI)
    Agmarknet commodity prices across Indian agricultural mandis.
    """
    np.random.seed(42)
    records = []
    
    commodities = [
        {"name": "Wheat", "variety": "Kalyan Sona", "base_price": 2275, "std": 120},
        {"name": "Paddy (Dhan)", "variety": "Basmati 1509", "base_price": 3450, "std": 250},
        {"name": "Mustard", "variety": "Yellow Sarson", "base_price": 5450, "std": 310},
        {"name": "Onion", "variety": "Nasik Red", "base_price": 1850, "std": 450},
        {"name": "Potato", "variety": "Kufri Jyoti", "base_price": 1420, "std": 180},
        {"name": "Tomato", "variety": "Hybrid Red", "base_price": 2100, "std": 520},
        {"name": "Chana (Gram)", "variety": "Desi Chana", "base_price": 5100, "std": 200},
        {"name": "Cotton", "variety": "Medium Staple", "base_price": 6800, "std": 380},
    ]
    
    markets = [
        {"state": "Punjab", "district": "Ludhiana", "market": "Khanna Mandi"},
        {"state": "Haryana", "district": "Karnal", "market": "Taraori Mandi"},
        {"state": "Uttar Pradesh", "district": "Agra", "market": "Fatehabad Mandi"},
        {"state": "Maharashtra", "district": "Nashik", "market": "Lasalgaon APMC"},
        {"state": "Madhya Pradesh", "district": "Indore", "market": "Choithram Mandi"},
        {"state": "Rajasthan", "district": "Kota", "market": "Bhamashah Mandi"},
        {"state": "Gujarat", "district": "Rajkot", "market": "Rajkot APMC"},
        {"state": "Karnataka", "district": "Hassan", "market": "Arasikere APMC"},
    ]
    
    start_date = datetime(2026, 9, 1)
    record_id = 10001

    for day in range(30):
        current_date = (start_date + timedelta(days=day)).strftime("%Y-%m-%d")
        for mkt in markets:
            # Pick 3-5 commodities per market per day
            selected_comms = np.random.choice(commodities, size=4, replace=False)
            for comm in selected_comms:
                modal = float(np.round(np.random.normal(comm["base_price"], comm["std"]), 2))
                modal = max(500.0, modal)
                spread = np.random.uniform(50, 180)
                min_p = float(np.round(modal - spread, 2))
                max_p = float(np.round(modal + spread, 2))
                
                records.append({
                    "record_id": f"AGRI-IND-{record_id}",
                    "state": mkt["state"],
                    "district": mkt["district"],
                    "market": mkt["market"],
                    "commodity": comm["name"],
                    "variety": comm["variety"],
                    "arrival_date": current_date,
                    "min_price_inr_qtl": min_p,
                    "max_price_inr_qtl": max_p,
                    "modal_price_inr_qtl": modal,
                    "arrivals_in_tonnes": round(float(np.random.exponential(45) + 5), 2),
                })
                record_id += 1

    df = pd.DataFrame(records)
    csv_path = DATA_DIR / "indian_agri_mandi_prices_clean.csv"
    df.to_csv(csv_path, index=False)
    print(f"Generated clean mandi dataset: {len(df)} rows at {csv_path}")

    # Now create a drifted / corrupted version for drift detection testing and monitoring run comparison
    # We will simulate:
    # 1. 10 duplicate rows
    # 2. 12 nulls in modal_price_inr_qtl
    # 3. 5 negative or inverted prices (min_price > max_price)
    # 4. Outlier spike in Onion and Tomato (2x-3x normal prices)
    # 5. Schema change: renamed column 'arrivals_in_tonnes' -> 'daily_arrivals_tonnes' and added 'grade'
    df_corrupted = df.copy()
    
    # Injected duplicates
    dups = df_corrupted.iloc[10:20].copy()
    df_corrupted = pd.concat([df_corrupted, dups], ignore_index=True)
    
    # Injected nulls in modal_price_inr_qtl
    null_indices = [25, 45, 67, 89, 120, 145, 180, 210, 230, 260, 290, 310]
    df_corrupted.loc[null_indices, "modal_price_inr_qtl"] = np.nan
    
    # Injected cross-field violation: min_price > max_price
    cross_indices = [50, 150, 250, 350, 450]
    for idx in cross_indices:
        df_corrupted.loc[idx, "min_price_inr_qtl"] = 9999.0
        df_corrupted.loc[idx, "max_price_inr_qtl"] = 1200.0

    # Injected extreme anomalies
    outlier_indices = [15, 80, 220, 400]
    df_corrupted.loc[outlier_indices, "modal_price_inr_qtl"] = [45000.0, 52000.0, 39000.0, 61000.0]
    
    # Add a new column and rename an existing one
    df_corrupted = df_corrupted.rename(columns={"arrivals_in_tonnes": "daily_arrivals_tonnes"})
    df_corrupted["grade"] = np.random.choice(["FAQ", "Grade-A", "Premium"], size=len(df_corrupted))

    corrupted_path = DATA_DIR / "indian_agri_mandi_prices_drifted.csv"
    df_corrupted.to_csv(corrupted_path, index=False)
    print(f"Generated drifted mandi dataset: {len(df_corrupted)} rows at {corrupted_path}")


def generate_air_quality_dataset():
    """
    CPCB National Ambient Air Quality Monitoring Programme (NAMP)
    AQI, PM2.5, PM10, NO2, SO2, CO, Ozone readings for Indian cities.
    """
    np.random.seed(101)
    stations = [
        {"station_id": "DEL-CPCB-001", "city": "Delhi", "state": "Delhi", "base_pm25": 95, "base_pm10": 180},
        {"station_id": "DEL-CPCB-002", "city": "Delhi", "state": "Delhi", "base_pm25": 110, "base_pm10": 210},
        {"station_id": "MUM-MPCB-001", "city": "Mumbai", "state": "Maharashtra", "base_pm25": 48, "base_pm10": 95},
        {"station_id": "BLR-KSPCB-001", "city": "Bengaluru", "state": "Karnataka", "base_pm25": 32, "base_pm10": 68},
        {"station_id": "KOL-WBPCB-001", "city": "Kolkata", "state": "West Bengal", "base_pm25": 72, "base_pm10": 140},
        {"station_id": "HYD-TSPCB-001", "city": "Hyderabad", "state": "Telangana", "base_pm25": 45, "base_pm10": 88},
    ]

    records = []
    start_date = datetime(2026, 9, 15)

    for day in range(30):
        current_date = (start_date + timedelta(days=day)).strftime("%Y-%m-%d")
        for st in stations:
            pm25 = max(5.0, float(np.round(np.random.normal(st["base_pm25"], 18), 1)))
            pm10 = max(10.0, float(np.round(np.random.normal(st["base_pm10"], 30), 1)))
            no2 = max(2.0, float(np.round(np.random.normal(28, 8), 1)))
            so2 = max(1.0, float(np.round(np.random.normal(12, 4), 1)))
            co = max(0.1, float(np.round(np.random.normal(1.1, 0.3), 2)))
            ozone = max(5.0, float(np.round(np.random.normal(35, 10), 1)))
            
            # Simple standard AQI proxy calculation
            aqi_val = int(round(pm25 * 2.1))
            if aqi_val <= 50:
                bucket = "Good"
            elif aqi_val <= 100:
                bucket = "Satisfactory"
            elif aqi_val <= 200:
                bucket = "Moderate"
            elif aqi_val <= 300:
                bucket = "Poor"
            elif aqi_val <= 400:
                bucket = "Very Poor"
            else:
                bucket = "Severe"

            records.append({
                "station_id": st["station_id"],
                "city": st["city"],
                "state": st["state"],
                "reading_date": current_date,
                "pm25": pm25,
                "pm10": pm10,
                "no2": no2,
                "so2": so2,
                "co": co,
                "ozone": ozone,
                "aqi": aqi_val,
                "aqi_category": bucket,
            })

    df = pd.DataFrame(records)
    csv_path = DATA_DIR / "indian_aqi_air_quality_clean.csv"
    df.to_csv(csv_path, index=False)
    print(f"Generated clean AQI dataset: {len(df)} rows at {csv_path}")


def generate_ev_charging_json():
    """
    Bureau of Energy Efficiency (BEE) Public EV Charging Station deployment in India (JSON format)
    """
    np.random.seed(202)
    cities = [
        {"city": "New Delhi", "state": "Delhi", "lat": 28.6139, "lon": 77.2090},
        {"city": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946},
        {"city": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777},
        {"city": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867},
        {"city": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
        {"city": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567},
    ]

    operators = ["Tata Power EZ Charge", "Jio-bp pulse", "Statiq", "ChargeZone", "Ather Grid", "BESCOM EV"]
    connectors = ["CCS-2 (Fast DC)", "Type-2 (AC)", "Bharat DC-001", "CHAdeMO"]

    stations = []
    for i in range(1, 151):
        loc = np.random.choice(cities)
        operator = np.random.choice(operators)
        conn = np.random.choice(connectors)
        power_kw = int(np.random.choice([22, 50, 60, 120, 150]))
        tariff = round(float(np.random.uniform(13.5, 22.0)), 2)
        status = np.random.choice(["Operational", "Operational", "Operational", "Under Maintenance", "Temporarily Offline"], p=[0.85, 0.05, 0.05, 0.03, 0.02])
        
        commission_date = (datetime(2023, 1, 1) + timedelta(days=int(np.random.randint(0, 1200)))).strftime("%Y-%m-%d")

        stations.append({
            "station_id": f"BEE-EV-{i:05d}",
            "operator_name": operator,
            "state": loc["state"],
            "city": loc["city"],
            "connector_type": conn,
            "total_power_kw": power_kw,
            "tariff_per_kwh_inr": tariff,
            "operational_status": status,
            "commissioned_date": commission_date,
            "latitude": round(loc["lat"] + float(np.random.normal(0, 0.04)), 5),
            "longitude": round(loc["lon"] + float(np.random.normal(0, 0.04)), 5),
            "gun_ports_count": int(np.random.choice([2, 4, 6, 8])),
        })

    json_path = DATA_DIR / "indian_ev_charging_infrastructure.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(stations, f, indent=2)
    print(f"Generated clean EV charging JSON dataset: {len(stations)} records at {json_path}")


def generate_health_infrastructure():
    """
    National Health Mission (NHM) Hospital & Health Facility Metrics across Indian districts.
    """
    np.random.seed(303)
    states_districts = [
        ("Kerala", "Ernakulam"), ("Kerala", "Thiruvananthapuram"),
        ("Tamil Nadu", "Coimbatore"), ("Tamil Nadu", "Madurai"),
        ("Maharashtra", "Pune"), ("Maharashtra", "Nagpur"),
        ("Odisha", "Khordha"), ("Odisha", "Sundargarh"),
        ("Assam", "Kamrup"), ("Assam", "Dibrugarh"),
        ("Bihar", "Patna"), ("Bihar", "Gaya"),
    ]
    facility_types = ["District Hospital (DH)", "Sub-District Hospital (SDH)", "Community Health Centre (CHC)", "Primary Health Centre (PHC)"]
    
    rows = []
    fac_id = 5001
    for st, dist in states_districts:
        for ftype in facility_types:
            for n in range(np.random.randint(2, 5)):
                if "DH" in ftype:
                    total_beds = int(np.random.randint(200, 600))
                    icu = int(np.random.randint(15, 60))
                    docs = int(np.random.randint(35, 110))
                    opd = int(np.random.randint(800, 2500))
                elif "SDH" in ftype:
                    total_beds = int(np.random.randint(80, 200))
                    icu = int(np.random.randint(6, 18))
                    docs = int(np.random.randint(18, 45))
                    opd = int(np.random.randint(400, 1000))
                elif "CHC" in ftype:
                    total_beds = int(np.random.randint(30, 80))
                    icu = int(np.random.randint(0, 4))
                    docs = int(np.random.randint(6, 16))
                    opd = int(np.random.randint(150, 500))
                else: # PHC
                    total_beds = int(np.random.randint(4, 12))
                    icu = 0
                    docs = int(np.random.randint(1, 4))
                    opd = int(np.random.randint(40, 180))

                rows.append({
                    "facility_id": f"NHM-FAC-{fac_id}",
                    "state": st,
                    "district": dist,
                    "facility_type": ftype,
                    "total_beds": total_beds,
                    "icu_beds": icu,
                    "doctors_on_duty": docs,
                    "daily_opd_attendance": opd,
                    "inpatients_admitted": int(total_beds * np.random.uniform(0.55, 0.95)),
                    "reporting_month": "2026-09",
                })
                fac_id += 1

    df = pd.DataFrame(rows)
    csv_path = DATA_DIR / "indian_health_infrastructure.csv"
    df.to_csv(csv_path, index=False)
    print(f"Generated health infrastructure dataset: {len(df)} rows at {csv_path}")


if __name__ == "__main__":
    generate_agri_mandi_prices()
    generate_air_quality_dataset()
    generate_ev_charging_json()
    generate_health_infrastructure()
    print("All sample datasets successfully generated in data/sample/!")
