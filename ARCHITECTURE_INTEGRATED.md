# SoilSense: Integrated Architecture
**Merlyn GNSS-R Soil Moisture + Operational Early Warning System**

---

## System Overview

4-layer operational architecture combining Maryline's soil moisture downscaling framework with Merlyn's early warning delivery system.

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: FARMER INTERFACE                                   │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│ │ Web Dashboard│  │ Mobile App   │  │ SMS Alerts   │       │
│ │ (React+Map) │  │ (Flutter)    │  │ (SMS Gateway)│       │
│ └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP API + WebSocket
┌──────────────────────┴──────────────────────────────────────┐
│ Layer 3: VALIDATION & QUALITY CONTROL                       │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ • Automated metric calculation (R, RMSE, MAE, Bias)     ││
│ │ • Threshold monitoring (R≥0.80, RMSE≤0.040)            ││
│ │ • Live "Trust Score" widget (green checkmarks)          ││
│ │ • u-blox GNSS-R comparison (validation truth)           ││
│ └──────────────────────────────────────────────────────────┘│
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│ Layer 2: PROCESSING & MODELING                              │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Regression-Kriging Downscaling Engine                   ││
│ │ • Input: SMAP (9-km), Sentinel-2 (NDVI), CHIRPS        ││
│ │ • Random Forest fusion: DOY, rainfall, NDVI, soil props ││
│ │ • Output: 10-m resolution soil moisture maps            ││
│ │ • Trigger Logic: Threshold (A) + Trend (B) detection   ││
│ │   - A: SM < 0.10 (critical), < 0.15 (warning)         ││
│ │   - B: 3+ consecutive days declining SM                 ││
│ └──────────────────────────────────────────────────────────┘│
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│ Layer 1: DATA INPUT                                         │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ SMAP L3 AM  │ │ Sentinel-2  │ │ CHIRPS      │           │
│ │ (9-km, 3d)  │ │ (NDVI, ~5d) │ │ (daily rain)│           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ u-blox GNSS-R (ground truth validation, daily)         ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Layers

### Layer 1: Data Input
**Purpose:** Ingest multi-source satellite + ground observations for model fusion.

| Source | Resolution | Frequency | Use |
|--------|-----------|-----------|-----|
| SMAP L3 AM | 9 km | 3-day | Primary SM target |
| Sentinel-2 | 10m | ~5-day | NDVI, NDWI, LAI |
| CHIRPS | 0.05° (~5km) | Daily | Rainfall driver |
| u-blox GNSS-R | Station point | Daily | Independent validation |

**Data Pipeline:**
- Scheduled daily fetch at 00:30 UTC (APScheduler)
- Cache raw data in PostgreSQL `raw_data` table
- Pre-process: gap-fill, coregister grids to 100m baseline

---

### Layer 2: Processing & Modeling
**Purpose:** Downscale coarse SMAP to 10-m resolution using ML + physics.

**Regression-Kriging Engine:**
1. **Feature Fusion** (Random Forest inputs):
   - SMAP (lag-1 temporal continuity)
   - NDVI (vegetation stress)
   - CHIRPS (recent rainfall driver)
   - Day-of-year (seasonal cycle)
   - Soil props: clay%, sand%, SOC (SoilGrids v2)
   - Terrain: elevation, slope, aspect

2. **Random Forest Model:**
   - Trained on 2021-2022 SMAP vs. Sentinel-2/soil/terrain
   - Performance: R² = 0.9542, RMSE = 0.0209 m³/m³
   - Generates predictions at 10-m grid cells within UNIVEN farm boundary

3. **Kriging Residual Interpolation:**
   - Spatial interpolation of RF prediction errors
   - Smooth field to 10-m resolution
   - Output: 10-m continuous soil moisture map

**Trigger Logic (Alert Detection):**

| Alert Type | Condition | Severity |
|-----------|-----------|----------|
| drought_critical | SM < 0.10 m³/m³ | 🔴 Critical |
| irrigation_needed | SM < 0.15 m³/m³ | 🟡 Warning |
| drought_developing | 3+ consecutive days declining SM | 🟠 Caution |
| rainfall_deficit | 7-day cumulative < 20mm | 🟡 Warning |
| crop_stress | NDVI drop > 0.05 from 7-day avg | 🟠 Caution |

**Output:**
- 10-m SM maps (continuous raster, stored in PostGIS)
- Alert grid (binary: triggered/not triggered per cell)
- Validation metrics (live calculation vs. u-blox)

---

### Layer 3: Validation & Quality Control
**Purpose:** Ensure model reliability before farmer delivery.

**Automated Checks (Table 19 equivalents):**
- **Pearson R:** Target ≥ 0.80; current = 0.93 ✓
- **RMSE:** Target ≤ 0.040 m³/m³; current = 0.0181 ✓
- **MAE:** Target ≤ 0.030 m³/m³; current = 0.0131 ✓
- **Bias:** Acceptable ±0.02; current = +0.0021 ✓

**Live "Trust Score" Widget:**
- Displays validation metrics on dashboard
- Green checkmark = all metrics passing
- Red warning = metric failed threshold
- Updates daily after model run

**Independent Validation:**
- Compare daily 10-m predictions vs. u-blox GNSS-R measurements
- Track divergence over time
- Flag if validation fails (e.g., R drops below 0.80)

---

### Layer 4: Dashboard & Output Channels

#### 4A: Web Dashboard (React + Mapbox)
**Components:**
1. **Interactive 10-m Soil Moisture Map**
   - Color-coded by irrigation need (red=dry, yellow=moderate, green=wet)
   - Click cell → view time series + forecast + irrigation action

2. **Plot-Level Status Cards**
   - Current SM value
   - 48-hour forecast
   - Specific irrigation action (e.g., "Irrigate in 2 days")
   - Alert reason + severity

3. **Validation Metrics Widget**
   - Live Table 19 metrics (R, RMSE, MAE, Bias)
   - Green checkmarks when passing
   - Last update timestamp

4. **Rainfall & Vegetation Trends**
   - CHIRPS 7-day cumulative (current + forecast)
   - NDVI 7-day moving average
   - Comparison to historical baseline

5. **Alert Log**
   - Timestamp, cell ID, alert type, trigger reason
   - Export to CSV for DALRRD reports

#### 4B: SMS Gateway
**Message Template (160 char limit, bilingual):**

```
English (Maize):
"⚠️ Plot L01: Drought risk. SM=0.12 m³/m³. Irrigate in 2 days. Rainfall forecast: 5mm."

Tshivenda:
"vha songo shelesa VWC = 0.12 (Zwitadza). Tshifhinga tsha u sheledza zwino. Tshinela nga 25 mm."
```

**Delivery:**
- Triggered when alert condition met (Layer 2 logic)
- Sent to registered farmers' feature phones
- SMS gateway: Twilio (international) or Afrimotech (local SA)
- Log stored in PostgreSQL for audit trail

#### 4C: Mobile App (Flutter)
**Core Features:**
- Offline map tile cache (essential for rural areas)
- Notification panel (alerts)
- Time series view per plot
- Simple irrigation action button
- Sync when online

---

## Technical Stack

### Backend
- **Framework:** FastAPI (Python 3.9+)
- **Database:** PostgreSQL + PostGIS + TimescaleDB
- **Scheduler:** APScheduler (daily 00:30 UTC)
- **ML Stack:** scikit-learn (Random Forest), scipy (Kriging)
- **Geospatial:** rasterio, geopandas, pyproj
- **SMS:** Twilio SDK or local HTTP gateway
- **API:** REST + WebSocket (live metric updates)

### Frontend
- **Web:** React + Mapbox GL + Redux (state)
- **Mobile:** Flutter (Dart)
- **Charts:** Chart.js (trends), Folium (static maps)
- **Styling:** Tailwind CSS

### Deployment
- **Backend:** Docker container (FastAPI + PostgreSQL)
- **Frontend Web:** Vercel or Netlify
- **Frontend Mobile:** App Store / Play Store
- **Cloud:** AWS/GCP/Azure (RDS, S3 for rasters, Lambda for scheduling)
- **SMS:** Twilio account (international) or Afrimotech (local)

---

## Data Flow (Daily Cycle)

```
00:30 UTC: APScheduler triggers daily_pipeline()
│
├─ Layer 1: Fetch SMAP, Sentinel-2, CHIRPS → PostgreSQL
│
├─ Layer 2: 
│   ├─ Load cached Random Forest model
│   ├─ Compute 10-m predictions
│   ├─ Kriging interpolation
│   ├─ Trigger logic (threshold + trend checks)
│   └─ Store maps + alerts in PostGIS
│
├─ Layer 3:
│   ├─ Compare predictions vs. u-blox
│   ├─ Calculate R, RMSE, MAE, Bias
│   ├─ Check against thresholds
│   └─ Update "Trust Score" in dashboard
│
└─ Layer 4:
    ├─ Generate SMS messages (bilingual)
    ├─ Dispatch via Twilio/Afrimotech
    ├─ Log alerts in PostgreSQL
    └─ Push updates to web/mobile dashboards (WebSocket)

Web/Mobile User sees:
- Updated 10-m maps
- New alerts (if triggered)
- Validation metrics + trust score
- SMS received on phone
```

---

## File Structure
```
D:\soilsense\
├── ARCHITECTURE_INTEGRATED.md (this file)
├── backend/
│   ├── app.py (FastAPI main)
│   ├── data_pipeline.py (Layer 1: fetch)
│   ├── ml_engine.py (Layer 2: RF + Kriging)
│   ├── validation.py (Layer 3: u-blox comparison)
│   ├── sms_dispatcher.py (Layer 4: SMS logic)
│   ├── models.py (SQLAlchemy ORM)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── web/
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js (React + Mapbox)
│   └── mobile/
│       └── lib/main.dart (Flutter)
├── data/
│   ├── trained_rf_model.pkl
│   ├── soil_grid_rasters/
│   └── test_data/ (mock for prototyping)
└── README.md
```

---

## Key Design Decisions

1. **10-m resolution, not SMS only:** Spatial granularity crucial for precision irrigation
2. **Independent validation (u-blox):** Operational trust, not just SMAP accuracy
3. **Bilingual SMS:** Tshivenda + English for Limpopo smallholders
4. **Offline-first mobile:** Rural areas have unreliable connectivity
5. **Daily 00:30 UTC sync:** Off-peak compute, avoids farmer disruption
6. **Trust Score widget:** Transparency = farmer adoption

---

## Next Steps (With Merlyn)

Before full deployment:
1. Confirm SM thresholds for her crops (currently: critical=0.10, warning=0.15)
2. Validate bilingual SMS messaging with target farmers
3. Test u-blox deployment at UNIVEN campus
4. Pilot SMS delivery (Twilio test account)
5. Gather farmer feedback on dashboard UX
