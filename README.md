# SoilSense — Early Warning System Prototype

Hello Merlyn,

This is a working prototype of the early warning system we discussed. It has two parts: one shows you how the trigger logic works, the other is an interactive dashboard showing how farmers would actually use it.

**Status:** Prototype only. All data is fake (synthetic), but the logic is real.

---

## Part A: Trigger Logic Test (Console)

This runs the alert detection logic on mock data to show you what alerts fire and why.

### How to run it

```bash
cd prototype_logic
python trigger_test.py
```

### What you'll see

- **Console output:** A list of 10 grid cells across Limpopo region, showing which ones alert and why
- **alert_log.json:** A detailed log of all alerts (for processing)
- **grid_state.csv:** The current state of all cells (used by the dashboard)

### Example output:

```
🔴 ALERT | L01 (Polokwane_North) | SM=0.118
       🔴 [THRESHOLD] drought_critical: SM=0.118 < 0.10
       🟠 [TREND] drought_developing: SM declining 3 days. Drought incoming.

🟡 WARNING | L02 (Polokwane_Center) | SM=0.142
       🟡 [THRESHOLD] irrigation_needed: SM=0.142 < 0.15. Irrigate soon.

🟢 OK | L03 (Polokwane_South) | SM=0.165
       (no alerts)

SUMMARY: 2 CRITICAL | 4 WARNING | 3 CAUTION
Total alerts fired: 9
```

This shows:
- **Critical (🔴):** Immediate action needed — SM below critical threshold
- **Warning (🟡):** Soon — irrigation needed or rainfall deficit
- **Caution (🟠):** Early warning — trend is declining, drought coming in 3-5 days
- **Safe (🟢):** No action needed

---

## Part B: Interactive Dashboard (Web)

This is what farmers and DALRRD officials would see. An interactive map with alerts, detailed cell information, and trend analysis.

### How to open it

**Easiest:** Double-click `prototype_dashboard/index.html` to open in your browser.

**Or via Python:**
```bash
cd prototype_dashboard
python -m http.server 8000
# Then open http://localhost:8000 in your browser
```

### What the dashboard shows

#### 1. **Summary Panel** (top)
- **Total Cells:** 10 cells monitored
- **Critical 🔴:** How many cells need immediate action
- **Warning 🟡:** How many need attention soon
- **Caution 🟠:** How many show declining trends
- **Safe 🟢:** How many are OK
- **Total Alerts:** Number of active alerts today

#### 2. **Alert Map** (left side)
- Limpopo region with your 10 grid cells displayed as colored dots
- Each color shows the current status:
  - **🔴 Red:** Critical (SM < 0.10) — drought now
  - **🟡 Yellow:** Warning (SM < 0.15) — irrigate in 1-2 days
  - **🟠 Orange:** Caution (trend declining) — drought coming in 3-5 days
  - **🟢 Green:** Safe — no action needed
- **Click any cell** to see its details

#### 3. **Filter Controls** (below the map)
- **Filter by Severity:** Click to show only Critical, Warning, or Safe cells
- **Crop Type:** Select Maize, Wheat, Sorghum, or All — alerts adjust based on crop thresholds
- **Export to CSV:** Download all active alerts for your records / reports to DALRRD

#### 4. **Cell Details** (right side)
When you click a cell on the map:
- Cell ID, location, crop type
- Current SM value vs "normal" (what it should be at this time of year)
- 7-day rainfall, NDVI status
- All active alerts and why they fired

#### 5. **Soil Moisture Trend** (chart)
- **Blue line:** Current SM trend (last 10 days)
- **Gray dashed line:** What's "normal" for this cell at this time of year
- **Green bars:** Rainfall past 10 days
- **Green bars beyond:** Forecasted rainfall (next 7 days) — helps plan irrigation
- Shows at a glance: Is SM improving? Declining? Is rain coming?

#### 6. **Compare Two Cells** (optional)
- Select two cells from the dropdowns
- Click "Compare" to see their SM trends side-by-side
- Useful to compare a dry cell vs a wet cell, or see if a problem is regional

#### 7. **Alert Log** (bottom right)
- Shows all active alerts for the selected cell
- Each alert explains: What's wrong, why it fired, when it was detected

---

## How the Trigger Logic Works (A+B)

Two types of alerts fire:

### **A) Threshold Alerts** (current conditions)
- **Drought Critical:** SM drops below 0.10 m³/m³ (for maize) → Farmers must irrigate NOW
- **Irrigation Needed:** SM below 0.15 m³/m³ → Plan irrigation for next 2-3 days
- **Rainfall Deficit:** Less than 20mm in past 7 days → Supplemental rain needed
- **Crop Stress:** NDVI dropping sharply → Signs of water stress, watch closely

### **B) Trend Alerts** (early warning)
- **Drought Developing:** SM declining 3 days in a row → Rain hasn't come, drought is coming in 3-5 days
  - Fire this alert BEFORE SM hits the critical threshold
  - Gives farmers time to prepare irrigation

**These work together:** Trend alerts warn you early. Threshold alerts tell you when to act.

---

## Thresholds (Customize Per Crop)

Currently built in:

| Crop | SM Critical | SM Irrigation | Notes |
|------|------------|---------------|-------|
| Maize | 0.10 m³/m³ | 0.15 m³/m³ | Default crop |
| Wheat | 0.12 m³/m³ | 0.18 m³/m³ | Slightly higher need |
| Sorghum | 0.08 m³/m³ | 0.13 m³/m³ | More drought-tolerant |

**These are educated guesses.** The real values should come from you — you know your crops better than anyone.

---

## Grid Cells (Mock)

10 test cells across Limpopo:
- **L01–L03:** Polokwane (in the prototype, these are simulated as "drier")
- **L04–L05:** Mopani
- **L06–L07:** Musina
- **L08–L10:** Blouberg & Capricorn (simulated as "wetter")

Coordinates are real, but data is synthetic (not actual SMAP/CYGNSS). We generate realistic scenarios to test the logic.

---

## Questions for You (Before We Build Full System)

When you're ready to move from prototype to real system, I'll need your input on:

1. **Soil Moisture Thresholds**
   - What SM values actually cause stress for your crops?
   - Should thresholds vary by season (planting vs. growing vs. harvest)?

2. **Grid Resolution**
   - How fine should the grid be? 
   - 0.1° = ~10km cells (coarser, faster, cheaper)
   - 0.05° = ~5km cells (finer, shows local patterns, slower/costlier)

3. **Geographic Scope**
   - Just Limpopo region?
   - Expand to other provinces later?
   - Include South Africa-wide coverage?

4. **User Base**
   - Farmers on the ground (need mobile app)?
   - DALRRD officials (need web dashboard)?
   - Extension officers (SMS alerts)?

5. **SMS Language**
   - English only?
   - Also Sepedi, Venda, Xitsonga (local languages)?

6. **Historical Baseline**
   - I have your 2021-2022 SMAP/CHIRPS data
   - Can we use it to define "normal" SM for each cell by date?
   - This makes the alerts more meaningful (compare current vs normal, not just absolute thresholds)

7. **Deployment Timeline**
   - When do you need a working system for actual farmers?

---

## The Full System (After Prototype)

Once you confirm thresholds and scope, we build:

```
Real Data Sources
├─ SMAP (3-day revisit)
├─ CYGNSS (daily, sparse)
├─ Sentinel-2 NDVI (5-day)
└─ CHIRPS rainfall (daily)
        ↓
   Data Pipeline (daily automated)
   ├─ Fetch data
   ├─ Validate & store
   └─ Run trigger logic
        ↓
   Alert Dispatcher
   ├─ SMS to farmers
   ├─ Push notifications (mobile app)
   └─ Web dashboard (for you & officials)
        ↓
   Farmers & DALRRD See
   ├─ Map showing alert zones
   ├─ SMS: "Cell L05: Drought risk. Irrigate in 2 days."
   ├─ Mobile app: Detailed trends & recommendations
   └─ Web: Export reports, historical analysis
```

**Backend:** Python/FastAPI + PostgreSQL (database) + APScheduler (daily runs)
**Mobile:** Flutter app (iOS/Android)
**Web:** React dashboard with Mapbox
**Notifications:** Twilio for SMS (or local provider)

---

## Next Steps

1. **Look at this prototype** — Open the dashboard, click cells, try the filters
2. **Run the trigger logic test** — See what alerts fire
3. **Give feedback** — Does the UI make sense? Are the thresholds reasonable?
4. **Answer the questions above** — This drives what we build next
5. **We build the real system** — Hook up actual data, SMS gateway, deploy to cloud

---

## Files

```
D:\soilsense\
├── README.md                          (you are here)
├── prototype_logic/
│   ├── trigger_test.py                (A: console trigger test)
│   ├── alert_log.json                 (output: alert details)
│   └── grid_state.csv                 (output: cell states)
└── prototype_dashboard/
    ├── index.html                     (B: interactive map & dashboard)
    ├── style.css                      (styling)
    └── script.js                      (all the logic + mock data)
```

---

## Notes

- All data is **synthetic** — generated to test different scenarios (dry cells, wet cells, declining trends, etc.)
- The **logic is real** — once you give us real thresholds and real data, this exact code detects real alerts
- **No external dependencies for dashboard** — it works entirely in the browser (no backend needed for the prototype)
- **Fully customizable** — crop thresholds, grid cells, alert types can all be changed as you learn what works

---

Good luck exploring. Let me know what you think.

**Created:** 2026-04-26
