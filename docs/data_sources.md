# Official Government Data Sources & Demonstration Fixtures

OpenData Sentinel bundles and supports verified public datasets published by Indian Government institutions via the Open Government Data (OGD) Platform India ([data.gov.in](https://www.data.gov.in/)).

---

## 1. Agricultural Mandi Commodity Arrivals & Prices
- **Publisher**: Ministry of Agriculture & Farmers Welfare, Directorate of Marketing & Inspection (DMI) via data.gov.in
- **Programme**: Agricultural Marketing Information Network (Agmarknet)
- **Data Cadence**: Daily
- **Format**: CSV
- **Schema**:
  - `record_id` (String / Unique Identifier): e.g. `AGRI-IND-10001`
  - `state` (String): Indian State (Punjab, Haryana, Uttar Pradesh, Maharashtra, Karnataka, Rajasthan)
  - `district` (String): Administrative District
  - `market` (String): APMC Mandi Facility name (e.g. Khanna Mandi, Lasalgaon APMC)
  - `commodity` (String): Crop name (Wheat, Mustard, Paddy, Onion, Potato, Tomato, Chana)
  - `variety` (String): Agricultural variety (e.g. Kalyan Sona, Nasik Red)
  - `arrival_date` (ISO Date): Date of market arrival
  - `min_price_inr_qtl` (Float): Minimum price in INR per quintal
  - `max_price_inr_qtl` (Float): Maximum price in INR per quintal
  - `modal_price_inr_qtl` (Float): Modal (most frequent) transaction price in INR per quintal
  - `arrivals_in_tonnes` (Float): Quantity arrived in metric tonnes
- **Integrity Rules**:
  - `min_price_inr_qtl <= max_price_inr_qtl`
  - `min_price_inr_qtl >= 0`, `max_price_inr_qtl >= 0`
  - `record_id` must be unique

---

## 2. National Ambient Air Quality Index (AQI)
- **Publisher**: Central Pollution Control Board (CPCB), Ministry of Environment, Forest and Climate Change (MoEFCC) via data.gov.in
- **Programme**: National Ambient Air Quality Monitoring Programme (NAMP)
- **Data Cadence**: Daily
- **Format**: CSV
- **Schema**:
  - `station_id` (String): Monitoring Station Code (e.g. `DEL-CPCB-001`)
  - `city` (String): Urban agglomeration (Delhi, Mumbai, Bengaluru, Kolkata, Hyderabad)
  - `state` (String): Indian State
  - `reading_date` (ISO Date): Timestamp of 24-hour reading
  - `pm25` (Float): Particulate Matter $2.5\,\mu\text{g/m}^3$
  - `pm10` (Float): Particulate Matter $10\,\mu\text{g/m}^3$
  - `no2` (Float): Nitrogen Dioxide concentration
  - `so2` (Float): Sulphur Dioxide concentration
  - `co` (Float): Carbon Monoxide concentration
  - `ozone` (Float): Surface Ozone concentration
  - `aqi` (Integer): Air Quality Index score (0–500)
  - `aqi_category` (Categorical): "Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"

---

## 3. Public EV Charging Station Infrastructure
- **Publisher**: Bureau of Energy Efficiency (BEE), Ministry of Power via data.gov.in
- **Programme**: National EV Public Charging Station Deployment Database
- **Data Cadence**: Monthly
- **Format**: JSON Array
- **Schema**:
  - `station_id` (String): BEE Unique Station ID (`BEE-EV-00001`)
  - `operator_name` (String): CPO (Tata Power EZ Charge, Statiq, Jio-bp, Ather Grid)
  - `state` (String): State name
  - `city` (String): Metropolitan city
  - `connector_type` (String): `CCS-2 (Fast DC)`, `Type-2 (AC)`, `Bharat DC-001`
  - `total_power_kw` (Integer): Total rated power in kW
  - `tariff_per_kwh_inr` (Float): Retail tariff in INR / kWh
  - `operational_status` (Categorical): "Operational", "Under Maintenance", "Temporarily Offline"
  - `commissioned_date` (ISO Date): Commissioning timestamp
  - `latitude`, `longitude` (Float): Geographic coordinates

---

## 4. National Health Mission Hospital Infrastructure & Facility Metrics
- **Publisher**: Ministry of Health and Family Welfare (MoHFW), National Health Mission
- **Programme**: Health Management Information System (HMIS)
- **Data Cadence**: Monthly
- **Format**: CSV
- **Schema**:
  - `facility_id` (String): Unique Health Facility ID (`NHM-FAC-5001`)
  - `state`, `district` (String): Location
  - `facility_type` (Categorical): "District Hospital (DH)", "Sub-District Hospital (SDH)", "Community Health Centre (CHC)", "Primary Health Centre (PHC)"
  - `total_beds` (Integer): Total sanctioned bed capacity
  - `icu_beds` (Integer): Intensive Care Unit beds
  - `doctors_on_duty` (Integer): Full-time doctors on staff
  - `daily_opd_attendance` (Integer): Outpatient department daily footfall
  - `inpatients_admitted` (Integer): Inpatient admissions
- **Integrity Rules**:
  - `icu_beds <= total_beds`
  - `inpatients_admitted <= total_beds * 1.5` (Overcrowding tolerance)
