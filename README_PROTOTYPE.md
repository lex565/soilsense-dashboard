# SoilSense: Integrated Prototype
**Merlyn's GNSS-R Soil Moisture + Operational Early Warning System**

## Quick Start: How It Works

This prototype demonstrates the **4-layer integrated architecture** combining Maryline's thesis findings with Merlyn's early warning system design.

```
┌────────────────────────────────────────────────────────────┐
│ FRONTEND: Web Dashboard (Browser)                          │
│ Shows: 10-m maps, alerts, validation metrics, SMS log      │
└────────────────────┬───────────────────────────────────────┘
                     │ HTTP REST API
┌────────────────────┴───────────────────────────────────────┐
│ BACKEND: FastAPI Server (Python)                           │
│ Layer 1: Data ingestion                                    │
│ Layer 2: Random Forest + Kriging → 10-m predictions        │
│ Layer 3: u-blox validation (Table 19 metrics)              │
│ Layer 4: Alert generation & SMS logic                      │
└────────────────────────────────────────────────────────────┘
```

---

## Setup & Execution

### 1. Install Backend Dependencies
```bash
cd D:\soilsense\backend
pip install -r requirements.txt
```

### 2. Start Backend Server
```bash
cd D:\soilsense\backend
python app.py
```

You should see:
```
🌱 SoilSense Backend Starting...
   4-Layer Architecture: Data → Processing → Validation → Output
   Access at: http://localhost:8000
   Docs at: http://localhost:8000/docs
```

### 3. Open Frontend Dashboard
Navigate to: **`D:\soilsense\frontend\index.html`** in your browser
(Or serve with: `python -m http.server 8080 --directory D:\soilsense\frontend`)

### 4. Run Pipeline
Click the blue **"▶ Run Daily Pipeline"** button on the dashboard.

Watch the console output as it executes all 4 layers in sequence.

---

## Architecture Flow

### Layer 1: Data Input
**What it does:** Ingest satellite + ground data
- **Inputs:**
  - SMAP L3 AM (9-km soil moisture)
  - Sentinel-2 (NDVI vegetation index)
  - CHIRPS (daily rainfall)
  - u-blox GNSS-R (ground truth validation)
- **Output:** Raw data stored in mock database

**In prototype:** Mock data generation (random but realistic values)

### Layer 2: Processing & Modeling
**What it does:** Downscale coarse SMAP to 10-m using Random Forest + Kriging

- **Random Forest model:**
  - Trained on 2021-2022 data (Merlyn's thesis)
  - Features: SMAP, NDVI, CHIRPS, soil properties, terrain
  - Performance: R² = 0.9542, RMSE = 0.0209 m³/m³

- **Kriging interpolation:**
  - Smooth predictions to 10-m grid
  - Output: 10-m continuous soil moisture map

- **Alert trigger logic (Threshold + Trend):**
  - **Threshold (A):** SM < 0.10 (critical), < 0.15 (warning)
  - **Trend (B):** 3+ consecutive days of declining SM
  - Output: Alert list with severity

**In prototype:** Mock RF predictions + Kriging smoothing

### Layer 3: Validation & Quality Control
**What it does:** Ensure reliability before farmer delivery

- **Independent validation (Table 19 from Maryline's thesis):**
  - Compare RF-Kriging predictions vs. u-blox GNSS-R
  - Calculate: Pearson R, RMSE, MAE, Bias
  - Check against thresholds: R ≥ 0.80, RMSE ≤ 0.040, etc.

- **Live "Trust Score" widget:**
  - 🟢 All metrics pass → High confidence
  - 🟡 Some warnings → Medium confidence
  - 🔴 Validation failed → Low confidence

**In prototype:** Mock validation metrics (realistic values)

### Layer 4: Output Channels
**What it does:** Deliver alerts to farmers via multiple channels

**4A: Web Dashboard**
- Interactive 10-m soil moisture map (color-coded)
- Click cell → view SM value + forecast
- Alert summary panel (critical/warning/OK counts)
- Validation metrics widget (Layer 3)
- Export to CSV for DALRRD reports

**4B: SMS Gateway**
- Bilingual messages (English + Tshivenda/Sepedi)
- ≤160 characters for feature phones
- Triggered when alerts detected (Layer 2 logic)
- Gateway: Twilio (international) or Afrimotech (local)

**4C: Mobile App**
- Offline map cache
- Push notifications
- Time series view per plot
- Sync when online

**In prototype:** Mock SMS generation + web dashboard

---

## Key Design Decisions

### 1. **10-m Resolution, Not SMS-Only**
Why: Spatial granularity crucial for precision irrigation. Farmers need to know WHICH plots to irrigate, not just alerts.

### 2. **Independent Validation (u-blox)**
Why: Operational trust. SMAP validation alone doesn't prove field-scale accuracy. u-blox provides independent ground truth.

### 3. **Bilingual SMS**
Why: Limpopo smallholders speak local languages. SMS in Tshivenda/Sepedi increases adoption.

### 4. **Offline-First Mobile**
Why: Rural areas have unreliable connectivity. App must work offline, sync when possible.

### 5. **Daily 00:30 UTC Sync**
Why: Off-peak compute time. Farmers see updates by dawn without system blocking their daylight work.

### 6. **Trust Score Transparency**
Why: Farmers adopt if they trust the system. Showing validation metrics builds confidence.

---

## Data Flow (Daily Cycle)

```
2026-04-27 00:30 UTC: APScheduler triggers daily_pipeline()

├─ [LAYER 1] Data fetch (10 min)
│  ├─ SMAP: 0.10-0.40 m³/m³ (realistic range)
│  ├─ Sentinel-2: NDVI 0.3-0.8
│  ├─ CHIRPS: 7-day rainfall 10-80mm
│  └─ u-blox: Independent measurements
│
├─ [LAYER 2] ML processing (5 min)
│  ├─ Load Random Forest model
│  ├─ Compute 10-m predictions
│  ├─ Kriging interpolation → smooth field
│  ├─ Trigger logic → find cells needing alerts
│  └─ Output: 10-m maps + alert list
│
├─ [LAYER 3] Validation (2 min)
│  ├─ Compare predictions vs. u-blox
│  ├─ Calculate R=0.93, RMSE=0.0181, MAE=0.0131
│  ├─ Check: All metrics pass ✓
│  └─ Update "Trust Score" → 🟢 High confidence
│
└─ [LAYER 4] Output dispatch (3 min)
   ├─ Generate SMS messages (bilingual)
   ├─ Dispatch via Twilio/Afrimotech → farmer phones
   ├─ Update dashboard (WebSocket) → web/mobile see maps
   └─ Log alerts for audit trail

Result: Farmers wake up to soil moisture maps + SMS alerts, ready for irrigation decisions
```

---

## File Structure

```
D:\soilsense\
├── ARCHITECTURE_INTEGRATED.md    ← Full technical architecture doc
├── README_PROTOTYPE.md            ← This file
├── backend/
│   ├── app.py                     ← FastAPI main server
│   ├── ml_engine.py               ← Random Forest + Kriging (Layer 2)
│   ├── validation.py              ← u-blox comparison (Layer 3)
│   ├── sms_dispatcher.py           ← SMS generation (Layer 4)
│   └── requirements.txt            ← Python dependencies
├── frontend/
│   ├── index.html                 ← Main dashboard
│   ├── app.js                     ← Logic + API calls
│   └── style.css                  ← Styling
└── data/
    └── trained_rf_model.pkl       ← Random Forest (production: real model from Merlyn)
```

---

## Testing Checklist

When you run the pipeline, verify:

- [ ] **Layer 1 Input:** Console shows "Data ingested (10 cells)"
- [ ] **Layer 2 Processing:** Shows "Regression-Kriging interpolation"
- [ ] **Layer 2 Alerts:** Dashboard displays critical/warning/OK cells
- [ ] **Layer 3 Validation:** Table 19 metrics filled in (R, RMSE, MAE, Bias)
- [ ] **Layer 3 Trust Score:** Green checkmark or warning emoji updates
- [ ] **Layer 4 Maps:** 10-m soil moisture grid colored (red/yellow/green)
- [ ] **Layer 4 Alerts:** Alert cards show trigger reason + SMS message
- [ ] **Layer 4 SMS:** SMS log shows bilingual messages ready for dispatch

---

## Next Steps: From Prototype to Production

### Before Full Deployment:

1. **Confirm thresholds with Merlyn:**
   - SM critical value (currently: 0.10)
   - SM warning value (currently: 0.15)
   - Crop-specific thresholds (maize/wheat/sorghum)

2. **Test bilingual SMS with target farmers:**
   - Tshivenda accuracy
   - Message clarity for low-literacy users

3. **Deploy u-blox receiver at UNIVEN:**
   - Real ground truth validation
   - Replace mock data with live measurements

4. **Pilot SMS gateway:**
   - Twilio test account (international)
   - Or Afrimotech for local SA delivery

5. **User feedback on dashboard:**
   - UX testing with farmers
   - Mobile app offline functionality

6. **Real data pipeline:**
   - Replace mock SMAP/Sentinel-2/CHIRPS fetch
   - Connect to PostgreSQL instead of in-memory state

---

## Troubleshooting

### Backend won't start
```
Error: Module 'numpy' not found
→ pip install -r requirements.txt
```

### Frontend can't reach backend
```
✗ Backend unavailable
→ Make sure backend is running on port 8000
→ Check: http://localhost:8000/health in browser
```

### Alerts not showing
```
→ Click "Run Daily Pipeline" button
→ Check browser console (F12) for errors
```

### Trust Score shows warning
```
🟡 Some warnings
→ Validation metrics failed (check Table 19 thresholds)
→ In real system: investigate model drift, u-blox calibration
```

---

## References

- **Maryline's Thesis (Pages 45-55):** 4-layer architecture, Table 19 validation metrics
- **Merlyn's Vision:** Early warning system for Limpopo smallholders
- **Merged Architecture:** `D:\soilsense\ARCHITECTURE_INTEGRATED.md`

---

## Contact

Questions about the system? Check:
- Backend logs (console output)
- FastAPI docs: http://localhost:8000/docs
- Browser console (F12 → Console tab)

🌱 **SoilSense: Bringing precision agriculture to data-scarce regions.**
