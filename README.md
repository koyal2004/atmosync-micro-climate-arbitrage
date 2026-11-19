# AtmoSync – Micro-Climate Arbitrage Analytics
### Intelligent Climate Monitoring & Agricultural Market Arbitrage
**Advanced Data Analytics & Engineering Academic Project | Infotact Research Lab**

*Branch:* `prudhvirajb` | *Repository:* `koyal2004/atmosync-micro-climate-arbitrage`

---

## 📖 1. Project Abstract

Agricultural perishables in India encounter post-harvest losses exceeding 15–25% primarily due to uncontrolled thermal and humidity excursions during long-haul interstate transportation. Traditional cold-chain operations rely on static destination routing, oblivious to localized in-transit biological deterioration or real-time spatial price arbitrage across alternate APMC mandis. 

**AtmoSync** is an enterprise-grade decision-support platform designed to bridge IoT micro-climate telematics with agricultural market economics. By continuously monitoring reefer container micro-climates, computing multi-factor parametric spoilage risk scores ($0–100$), and tracking wholesale spot prices across major agricultural trading hubs in 10 Indian states, AtmoSync prescribes dynamic, margin-maximizing rerouting decisions for consignments at risk of thermal degradation.

---

## 🎯 2. Problem Statement & Objectives

### Problem Statement
Standard agricultural transport systems adhere strictly to pre-planned origin-to-destination corridors. When a refrigerated container experiences equipment malfunction or severe temperature spikes, the produce depreciates rapidly. Conventional supply chains lack the intelligence to dynamically evaluate whether diverting the cargo to an alternative, higher-paying regional terminal mandi could offset logistics detour costs and recover net revenue.

### Core Objectives
1. **Real-Time Highway Ingestion:** Ingest simulated container telemetry (temperature, relative humidity, vibration).
2. **Biological Exposure Scoring:** Model thermal and humidity stress using commodity-specific respiration guidelines across 15 core fruits and vegetables.
3. **Mandi Price Intelligence:** Track wholesale prices across 500 agricultural trading locations in India.
4. **Spatial Arbitrage Modeling:** Calculate net rerouting advantages considering freight, handling, and quality adjustments.
5. **Operational Decision Support:** Present actionable alerts and 3D GIS route divergence maps.

---

## 💡 3. Proposed Solution Architecture

AtmoSync integrates relational persistence, streaming telemetry replay, unsupervised machine learning, and dynamic financial modeling into an intuitive Streamlit web application:

```
AtmoSync Architecture
├── 1. Data Layer: SQLite (atmosync.db) with 10,000+ linked records & FK constraints
├── 2. Ingestion & Streaming: Virtual reefer simulation engine with manual speed controls
├── 3. Analytics & ML:
│   ├── Isolation Forest: Unsupervised anomaly detection on temperature, humidity, vibration
│   ├── Parametric Risk Engine: Exposure integrals & remaining shelf-life estimation
│   ├── Holt's Exponential Smoothing: 14-day price forecasting with 95% confidence intervals
│   └── Arbitrage Optimizer: Quality-adjusted gross margin waterfall & rerouting recommendations
├── 4. Visualization & GIS: Plotly Express, Plotly Graph Objects & PyDeck 3D Corridors
└── 5. Reporting Hub: Multi-format exports (ReportLab PDF, Multi-sheet Excel, Full ZIP)
```

---

## 🛠️ 4. Technology Stack

- **Core Language:** Python 3.11 / 3.12 / 3.14
- **Web Framework:** Streamlit (Modern Multipage `st.navigation` architecture)
- **Data Engineering:** Pandas, NumPy
- **Visual Analytics:** Plotly Express, Plotly Graph Objects
- **3D Geospatial Engine:** PyDeck (ArcLayer & ScatterplotLayer)
- **Machine Learning & Forecasting:** Scikit-Learn (Isolation Forest), Statistical Holt's Trend Models
- **Database & Persistence:** SQLite (`database/atmosync.db`)
- **Document Generation:** ReportLab (Executive PDF generation), OpenPyXL (Excel), Zipfile

---

## 📑 5. Module Descriptions (Eight Core Pages)

| # | Module | Description |
|---|---|---|
| **1** | **Executive Dashboard** | 8 KPI cards, 8 high-level Plotly charts, global date/state/commodity filters, and APMC geospatial overview. |
| **2** | **Shipment Monitoring** | Live freight registry, searchable manifest table, 3D PyDeck corridor routes, and individual container sensor histories. |
| **3** | **IoT Sensor Analytics** | Interactive reefer streaming simulator (Start/Pause/Reset controls), packet inspector, and Isolation Forest ML anomaly tags. |
| **4** | **Commodity Analytics** | APMC mandi modal price distributions, arrival volume charts, cross-mandi spreads, and AI price projections with 95% CI. |
| **5** | **Weather Analytics** | Internal reefer micro-climate telemetry, environmental safety thresholds, and vibration accelerometer analysis. |
| **6** | **Spoilage Risk Analysis** | Parametric 0–100 biological exposure modeling, quality loss forecasting, and shelf-life depletion analysis. |
| **7** | **Market Arbitrage Intelligence** | Spatial price arbitrage algorithms, margin waterfall decomposition, and automated rerouting recommendation engine. |
| **8** | **Reports & Data Management** | Data quality and referential integrity audit, CSV/Excel/ZIP downloads, ReportLab executive PDF dossier, and DB reset slider. |

---

## 📊 6. Synthetic Dataset Explanation

The application programmatically synthesizes between **5,000 and 10,000 linked records** (default: 10,686 records) using a fixed seed (`seed=42`) for reproducibility:

1. **`commodities` (1,000 records):** 15 core fruits and vegetables (Avocado, Mango, Banana, Apple, Orange, Grapes, Papaya, Tomato, Onion, Potato, Brinjal, Cabbage, Green Chilli, Carrot, Cauliflower) with baseline storage thresholds and sensitivity tiers.
2. **`markets` (500 records):** Trading hubs across 10 Indian states (Tamil Nadu, Karnataka, Andhra Pradesh, Telangana, Maharashtra, Kerala, Gujarat, Delhi, Uttar Pradesh, West Bengal) with realistic coordinates for major mandis (Koyambedu, Vashi APMC, Yeshwanthpur, Azadpur Mandi, etc.).
3. **`market_prices` (3,000 records):** Wholesale daily rates (₹/kg) ensuring strict mathematical consistency ($P_{\min} \le P_{\text{modal}} \le P_{\max}$).
4. **`shipments` (1,000 records):** Consignment records linking origin and destination mandis, transit distance (km), freight costs, and shipment statuses (*In Transit, Delivered, Delayed, At Risk, Completed*).
5. **`sensor_readings` (4,000 records):** Reefer telemetry logging timestamps, temperature (°C), relative humidity (%), and vibration (g-force RMS) with simulated refrigeration anomalies.
6. **`arbitrage_opportunities` (500 records):** Calculated financial opportunities derived from destination price spreads, quality loss, and detour costs.
7. **`alerts` (686 records):** Operational alerts tracking *New, Acknowledged, and Resolved* states.

---

## 🚀 7. Installation & Execution Instructions

### Step 1: Clone and Checkout Branch
```powershell
git clone -b prudhvirajb https://github.com/koyal2004/atmosync-micro-climate-arbitrage.git
cd atmosync-micro-climate-arbitrage
git checkout prudhvirajb
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Streamlit Application
```powershell
streamlit run app.py
```

### Step 4: Open in Browser
Navigate to `http://localhost:8501`.

*(Note: The database automatically initializes and populates on initial run if not already present. To reset or reconfigure record counts between 5,000 and 10,000, navigate to Page 8: Reports & Data Management).*

---

## 🧪 8. Testing & Validation Summary

An automated end-to-end verification script confirms:
- **Module Import Verification:** All modules import without circular dependencies or missing requirements.
- **Referential Integrity Audit:** 100% data completeness, 0 foreign key violations, 0 null cells, and 0 range constraint violations.
- **Risk & Arbitrage Engines:** Verified mathematical logic across active and at-risk shipments.
- **Export Pipelines:** Verified ZIP, Excel, and ReportLab PDF document generation.

---

## ⚖️ 9. Limitations & Academic Disclaimer

> **ACADEMIC DEMONSTRATION DISCLAIMER:**
> **AtmoSync** is an academic research platform developed for Advanced Data Analytics & Engineering at Infotact. All agricultural market prices, consignment records, reefer sensor readings, spoilage vulnerability scores, and arbitrage recommendations are programmatically synthesized demonstration records. They must not be construed as actual government agricultural observations or commercial trading advice.
