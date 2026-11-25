# AtmoSync – Micro-Climate Arbitrage Analytics
### Intelligent In-Transit Cold-Chain Monitoring & Agricultural Spatial Price Arbitrage
**Academic Research Platform | Branch: `prudhvirajb` | Repository: `koyal2004/atmosync-micro-climate-arbitrage`**

---

## 📌 1. Project Overview & Problem Statement

Perishable agricultural commodities in India suffer post-harvest supply-chain losses estimated at 15–25%, predominantly caused by thermal runaway, moisture condensation, and mechanical vibration during long-haul interstate highway transport. Conventional logistics platforms operate under rigid, static consignment routes: once freight departs origin mandis, drivers and dispatchers lack real-time visibility into micro-climate-driven spoilage risk or spatial price differentials across regional APMC terminal mandis.

**AtmoSync** bridges the gap between IoT reefer telematics, post-harvest biology, and agricultural economics. By ingesting streaming sensor telemetry (temperature, relative humidity, chassis shock), calculating transparent multi-factor biological degradation risk scores ($0–100$), and continuously benchmarking wholesale spot prices across Indian trading hubs, AtmoSync prescribes dynamic, margin-optimizing rerouting interventions for consignments experiencing cold-chain failure.

---

## 🎯 2. Core Objectives

1. **Highway Telematics Ingestion:** Continuous simulated container micro-climate monitoring (ambient temperature, relative humidity, mechanical vibration).
2. **Biological Degradation Modeling:** Multi-factor parametric exposure scoring ($0–100$) across 15 agricultural commodities based on physiological respiration characteristics.
3. **Wholesale Mandi Price Tracking:** Monitor APMC wholesale spot rates and arrivals across 500 trading locations in 10 Indian states.
4. **Spatial Price Arbitrage:** Compute net margin recovery from alternative terminal mandis after accounting for detour freight, terminal handling, and quality degradation without double-counting.
5. **Operational Decision Support:** Provide actionable rerouting prescriptions, alert centers, and 3D GIS route divergence maps.

---

## 🚀 3. Core Architecture & Key Capabilities

```
AtmoSync Analytics Architecture
├── 1. Data Governance Layer (SQLite: database/atmosync.db)
│   ├── 7 Relational Tables (9,500+ Linked Records) with Foreign Keys & Domain Integrity Checks
│   ├── Cross-Table Relationship Validation & Anomaly Detection (modules/data_cleaning.py)
│   └── Automated Data Cleaning, Imputation & Temporal Date Ordering (departure <= arrival)
├── 2. Telemetry & Simulation Layer
│   ├── Virtual Reefer Telematics Replay (Streaming simulation with pause/resume/speed controls)
│   └── Machine Learning Anomaly Detection (Unsupervised Isolation Forest on temperature/humidity/vibration)
├── 3. Analytical Engine Layer
│   ├── Transparent Rule-Based Spoilage Risk Model (0–100 score across 4 biological risk tiers)
│   ├── Contributing Stressor Factor Decomposition (Thermal, moisture, and kinetic shock vectors)
│   ├── Statistical Holt's Exponential Smoothing Price Forecasting (14-day projection with 95% CI)
│   └── Spatial Price Arbitrage Engine (Quality-adjusted net margin waterfalls & detour logistics costs)
├── 4. Visualization & Geospatial GIS Layer
│   ├── 30+ Interactive Plotly Visualizations (Dual-axis trajectories, donuts, histograms, waterfalls)
│   └── 3D PyDeck GIS Corridor Mapping (ArcLayer routes with elevation arcs and scatter hubs)
└── 5. Reporting & Export Pipelines
    ├── ReportLab Executive PDF Intelligence Dossier Generation
    ├── OpenPyXL Multi-Sheet Excel Workbook Export (.xlsx)
    └── Lossless ZIP Archive of All CSV Datasets & Relational Schema
```

---

## 📑 4. The Eight Navigable Application Modules

The application is structured into eight modules using Streamlit's multipage navigation (`st.navigation`):

| # | Application Module | Primary Features & Analytics |
|:---|:---|:---|
| **1** | **Executive Dashboard** | 6 dynamic KPI metric cards (Total Shipments, Active Fleet, Commodities, Avg Price, High-Risk Consignments, Telemetry Readings), multi-factor sidebar filters (Date Range, State, Commodity, Market, Status), and high-level Plotly/PyDeck fleet visualizations. |
| **2** | **Shipment Monitoring** | Live freight tracking registry, searchable consignment table with individual container histories, alert notifications for delayed/at-risk cargo, fleet logistics performance analytics (completion rates, delay ratios, unit costs), and 3D PyDeck GIS spatial routing maps. |
| **3** | **IoT Sensor Analytics** | Interactive reefer streaming telemetry simulator (Start/Pause/Reset controls), packet inspector, thermal/moisture histograms, and Unsupervised Isolation Forest machine learning anomaly classification. |
| **4** | **Commodity Analytics** | APMC mandi modal price distributions (₹/kg), minimum/maximum/modal rate spreads, arrival volume metrics (kg/MT), supply vs. demand balance ratios, and Holt's linear trend forecasting with 95% confidence intervals. |
| **5** | **Weather Analytics** | Internal shipping container micro-climate telemetry, environmental safety boundary controls, temperature vs. humidity psychrometric profiles, kinetic vibration distributions, and correlation with consignment shipment status. |
| **6** | **Spoilage Risk Analysis** | Transparent heuristic biological stress model ($0–100$), multi-factor exposure breakdowns (temperature excursion, moisture stress, vibration shock), contributing stressor decomposition, shelf-life depletion boxplots, and operational action prescriptions. |
| **7** | **Market Arbitrage Analysis** | Spatial price arbitrage algorithms, margin waterfall decomposition, detour transport & terminal handling cost deductions (strictly non-overlapping), and automated top rerouting recommendation matrix for at-risk consignments. |
| **8** | **Reports and Data Management** | SQLite database diagnostic health checks, data quality and referential integrity audit matrices, multi-format bulk exports (ReportLab PDF, Excel .xlsx, ZIP archive, CSVs), and configurable database reset slider. |

---

## 🧮 5. Mathematical Formulations & Analytical Engines

### A. Spoilage Risk Scoring Formulation ($R \in [0, 100]$)
The spoilage risk engine applies a multi-factor parametric heuristic across 15 commodity biological profiles:
1. **Temperature Exposure Score ($E_{\text{temp}} \in [0, 50]$):**
   $$\Delta T = \max(0, T_{\text{avg}} - T_{\max}) + \max(0, T_{\min} - T_{\text{avg}})$$
   $$E_{\text{temp}} = \min\left(50, \, (\Delta T)^{1.25} \times \tau_{\text{days}}^{0.5} \times 4.2\right)$$
2. **Humidity Stress Score ($E_{\text{hum}} \in [0, 25]$):**
   $$E_{\text{hum}} = \min\left(25, \, \max(0, H_{\text{avg}} - H_{\max}) \times 1.5\right)$$
3. **Kinetic Vibration Shock Score ($E_{\text{vibe}} \in [0, 15]$):**
   $$E_{\text{vibe}} = \min\left(15, \, \max(0, \text{Vibe}_{\text{avg}} - 1.2) \times 4.0\right)$$
4. **Sensitivity Weight ($W_{\text{sens}}$):** *Low* (0.65), *Moderate* (1.00), *High* (1.35), *Critical* (1.70).
5. **Composite Score & Project Tiers:**
   $$\text{Risk Score} = \text{clamp}\Big((E_{\text{temp}} + E_{\text{hum}} + E_{\text{vibe}}) \times W_{\text{sens}}, \, 0, \, 100\Big)$$
   - **0 – 24 (Low):** Nominal transit; standard cold-chain protocol.
   - **25 – 49 (Moderate):** Minor excursions; continuous telemetry tracking.
   - **50 – 74 (High):** Elevated risk; adjust setpoint and expedite corridor.
   - **75 – 100 (Critical):** Severe excursion; immediate dynamic reroute advised.

### B. Spatial Arbitrage Financial Model (Zero Double-Counting)
1. **Gross Revenue Advantage ($G$):**
   $$G = (P_{\text{alt}} - P_{\text{curr}}) \times Q_{\text{kg}}$$
2. **Quality Degradation Loss Deduction ($C_{\text{quality}}$):**
   $$C_{\text{quality}} = P_{\text{alt}} \times Q_{\text{kg}} \times L_{\text{loss\_pct}}$$
3. **Detour Freight Logistics Cost ($C_{\text{transport}}$):**
   $$C_{\text{transport}} = D_{\text{detour\_km}} \times ₹22.50/\text{km} + ₹850\text{ (fixed dispatcher fee)}$$
4. **Terminal Handling Cost ($C_{\text{handling}}$):**
   $$C_{\text{handling}} = Q_{\text{kg}} \times ₹0.40/\text{kg}$$
5. **Estimated Net Arbitrage Benefit ($B_{\text{net}}$):**
   $$B_{\text{net}} = G - C_{\text{transport}} - C_{\text{handling}} - C_{\text{quality}}$$
   *(Only opportunities yielding $B_{\text{net}} > 0$ are classified as profitable rerouting actions).*

---

## 🛠️ 6. Technology Stack

- **Application Language:** Python 3.11 / 3.12 / 3.14
- **Web UI & Navigation:** Streamlit (Enterprise Dark-Navy & Teal theme, `st.navigation` multipage router)
- **Data Engineering:** Pandas, NumPy
- **Interactive Visualizations:** Plotly Express, Plotly Graph Objects
- **Geospatial Mapping:** PyDeck 3D Corridors (ArcLayer & ScatterplotLayer)
- **Machine Learning & Forecasting:** Scikit-Learn (Isolation Forest anomaly detection), Holt's Exponential Smoothing
- **Database & Persistence:** SQLite (`database/atmosync.db`) with relational integrity
- **Export Frameworks:** ReportLab (Executive PDF generation), OpenPyXL (Excel), Zipfile, CSV

---

## 📂 7. Repository Folder Structure

```
atmosync/
├── .gitignore                          # Git ignore rules for virtual environments, caches, and DB locks
├── README.md                           # Comprehensive architectural and operational documentation
├── requirements.txt                    # Pinned Python package dependencies
├── app.py                              # Main application entry point & Streamlit multipage orchestrator
├── assets/
│   ├── logo.png                        # Application brand badge
│   └── styles.css                      # Custom enterprise CSS styling rules (Navy/Teal theme)
├── config/
│   ├── __init__.py                     # Package init
│   └── settings.py                     # Global constants, colors, DB paths, and academic disclaimers
├── data/
│   ├── exports/                        # Directory for generated PDF/Excel/ZIP artifacts (.gitkeep)
│   └── generated/                      # CSV snapshots of synthetic datasets
├── database/
│   ├── __init__.py                     # Package init
│   ├── atmosync.db                     # SQLite relational database (9,500+ linked records)
│   └── database.py                     # SQLite engine, schema initialization, table loading & PRAGMA audits
├── modules/
│   ├── __init__.py                     # Package init
│   ├── alert_engine.py                 # Telemetry threshold evaluation & alert dispatcher
│   ├── analytics.py                    # Advanced operational metrics, performance rates & stress breakdowns
│   ├── anomaly_detection.py            # Scikit-learn Isolation Forest sensor anomaly detection
│   ├── arbitrage_engine.py             # Spatial price spread optimizer & margin waterfall engine
│   ├── data_cleaning.py                # Referential integrity, cross-table checks, date validation & imputation
│   ├── data_generator.py               # Deterministic synthetic data synthesizer (5,000–10,000 records)
│   ├── forecasting.py                  # Holt's linear trend price forecasting with confidence bounds
│   └── risk_engine.py                  # Multi-factor biological spoilage risk engine (0–100 score)
├── pages/
│   ├── __init__.py                     # Package init
│   ├── executive_dashboard.py          # Module 1: High-level executive KPI overview
│   ├── shipment_monitoring.py          # Module 2: Consignment registry, performance metrics & 3D PyDeck maps
│   ├── iot_analytics.py                # Module 3: Virtual streaming telemetry simulator
│   ├── commodity_analytics.py          # Module 4: Mandi price dynamics & forecasting
│   ├── weather_analytics.py            # Module 5: Reefer micro-climate & environmental intelligence
│   ├── spoilage_risk.py                # Module 6: Rule-based biological degradation scoring & stress decomposition
│   ├── market_arbitrage.py             # Module 7: Spatial price arbitrage & dynamic rerouting
│   └── reports.py                      # Module 8: Data governance, export suite & DB lifecycle
├── tests/
│   ├── __init__.py                     # Package init
│   ├── test_database.py                # SQLite connectivity, schema, and CRUD tests (11 tests)
│   ├── test_backend_reliability.py     # Caching, duplicate-safe import & CSV upload validation (5 tests)
│   ├── test_data_generator.py          # Synthetic dataset volume, linkage, and range tests (13 tests)
│   ├── test_data_validation.py         # Data quality, temporal ordering, and cross-table tests (5 tests)
│   ├── test_advanced_analytics.py      # Performance metrics, spoilage breakdown, and arbitrage tests (5 tests)
│   ├── test_exports.py                 # Filtered reports, PDF, Excel, and ZIP export tests (9 tests)
│   └── test_app_integration.py         # End-to-end Streamlit AppTest across all 8 modules (11 tests)
└── utils/
    ├── __init__.py                     # Package init
    ├── charts.py                       # Plotly & PyDeck chart generation utilities
    ├── constants.py                    # Domain metadata (commodities, APMC coordinates, sensitivity tiers)
    ├── export.py                       # ReportLab PDF, OpenPyXL Excel, and ZIP archive builders
    └── helpers.py                      # Currency, quantity, metric card, and status badge formatters
```

---

## 💻 8. Installation & Execution Guide (Windows Local Setup)

### Step 1: Open PowerShell and Navigate to the Repository
```powershell
Set-Location "c:\Users\Admin\OneDrive\intern\atmosync"
```

### Step 2: Ensure Target Branch is Checked Out and Up to Date
```powershell
git checkout prudhvirajb
git pull origin prudhvirajb
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Execute the Streamlit Application
```powershell
streamlit run app.py
```

### Step 5: Access the Web Dashboard
Open your web browser and navigate to:
```
http://localhost:8501
```

*Note: On first run, the SQLite database (`database/atmosync.db`) automatically initializes and populates with linked records. To re-synthesize or customize dataset volume, navigate to **Module 8: Reports and Data Management**.*

---

## 🧪 9. Test Suite & Validation Results

The repository features an automated verification suite executed via `pytest`:

```powershell
pytest
```

**Verification Results (59 Passing Automated Tests):**
- **Database Architecture Tests (`tests/test_database.py`):** 11 tests verifying schema creation, foreign key constraints, table queries, and transaction rollbacks.
- **Backend Reliability & CSV Import Tests (`tests/test_backend_reliability.py`):** 5 tests verifying table caching/invalidation, schema-preserving replace, duplicate-safe upserts, and malformed CSV validation.
- **Data Generator Tests (`tests/test_data_generator.py`):** 13 tests validating deterministic generation, non-null primary keys, commodity price constraints ($P_{\min} \le P_{\text{modal}} \le P_{\max}$), and container-telemetry links.
- **Data Validation Tests (`tests/test_data_validation.py`):** 5 tests verifying null imputation, duplicate key removal, temporal date consistency (`departure <= arrival`), numeric bounds, and cross-table relationships.
- **Advanced Analytics Tests (`tests/test_advanced_analytics.py`):** 5 tests verifying logistics performance rates, spoilage stress factor breakdowns, weather-shipment correlation, and non-overlapping arbitrage net benefit calculations.
- **Report Generation & Export Pipelines (`tests/test_exports.py`):** 9 tests verifying all 5 filtered report types, empty filter states, ZIP archive creation, OpenPyXL workbooks with metadata, and ReportLab PDF compilation.
- **Streamlit App Integration (`tests/test_app_integration.py`):** 11 end-to-end `AppTest` checks verifying `app.py`, all 8 page modules, and interactive filter updates render with zero runtime exceptions.
- **Static Syntax & AST Parsing:** Automated AST traversal confirming 100% syntax compliance across all Python modules with zero import warnings.

---

## ⚖️ 10. Academic & Synthetic Data Governance Disclaimers

> **IMPORTANT ACADEMIC DEMONSTRATION NOTICE:**  
> **AtmoSync** is an academic research demonstration platform developed for advanced data analytics and data engineering studies. All agricultural prices, APMC market arrivals, reefer sensor readings, biological degradation indices, and spatial arbitrage margins are programmatically synthesized demonstration records generated using pseudo-random seeds.  
>  
> - Spoilage risk scores are calculated using project-defined heuristic rules and do not constitute scientifically validated biological prediction models.  
> - Financial arbitrage calculations represent operational simulations and must not be interpreted as financial or trading recommendations.
