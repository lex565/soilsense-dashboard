"""
SoilSense Early Warning System — Prototype Logic Test
Tests trigger engine (A+B: threshold + trend) with mock data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# ============================================================================
# CONFIG: Thresholds by crop (customize with Merlyn)
# ============================================================================

CROP_THRESHOLDS = {
    'maize': {
        'sm_critical': 0.10,
        'sm_irrigation': 0.15,
        'rainfall_deficit': 20,
        'ndvi_stress': 0.05,
    },
    'wheat': {
        'sm_critical': 0.12,
        'sm_irrigation': 0.18,
        'rainfall_deficit': 25,
        'ndvi_stress': 0.04,
    },
    'sorghum': {
        'sm_critical': 0.08,
        'sm_irrigation': 0.13,
        'rainfall_deficit': 15,
        'ndvi_stress': 0.06,
    },
}

# ============================================================================
# MOCK DATA: 10 grid cells across Limpopo region
# ============================================================================

GRID_CELLS = [
    {'cell_id': 'L01', 'lat': -23.85, 'lon': 29.12, 'name': 'Polokwane_North', 'crop': 'maize'},
    {'cell_id': 'L02', 'lat': -23.90, 'lon': 29.20, 'name': 'Polokwane_Center', 'crop': 'maize'},
    {'cell_id': 'L03', 'lat': -23.95, 'lon': 29.28, 'name': 'Polokwane_South', 'crop': 'wheat'},
    {'cell_id': 'L04', 'lat': -24.10, 'lon': 29.50, 'name': 'Mopani_East', 'crop': 'maize'},
    {'cell_id': 'L05', 'lat': -24.20, 'lon': 29.60, 'name': 'Mopani_West', 'crop': 'sorghum'},
    {'cell_id': 'L06', 'lat': -24.50, 'lon': 29.80, 'name': 'Musina_North', 'crop': 'wheat'},
    {'cell_id': 'L07', 'lat': -24.55, 'lon': 29.85, 'name': 'Musina_South', 'crop': 'maize'},
    {'cell_id': 'L08', 'lat': -23.70, 'lon': 28.90, 'name': 'Blouberg_West', 'crop': 'sorghum'},
    {'cell_id': 'L09', 'lat': -23.80, 'lon': 28.80, 'name': 'Blouberg_Center', 'crop': 'maize'},
    {'cell_id': 'L10', 'lat': -24.00, 'lon': 29.00, 'name': 'Capricorn_Central', 'crop': 'wheat'},
]

def generate_mock_timeseries(cell_id, days=30):
    """Generate 30 days of mock SM/rainfall/NDVI for one cell."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    cell_num = int(cell_id[1:])

    if cell_num <= 3:
        sm_base = 0.12
        sm_trend = -0.005
    elif cell_num <= 6:
        sm_base = 0.18
        sm_trend = 0.001
    else:
        sm_base = 0.25
        sm_trend = -0.002

    sm = np.array([sm_base + sm_trend * i + np.random.normal(0, 0.01) for i in range(days)])
    sm = np.clip(sm, 0.05, 0.35)

    rainfall = np.where(np.random.random(days) > 0.7, np.random.uniform(5, 25), 0)
    if cell_num in [1, 4, 7]:
        rainfall = rainfall * 0.5

    ndvi_base = 0.6 if cell_num <= 3 else 0.7
    ndvi = np.array([ndvi_base - 0.01 * i + np.random.normal(0, 0.02) for i in range(days)])
    ndvi = np.clip(ndvi, 0.3, 0.8)

    df = pd.DataFrame({
        'date': dates,
        'sm': sm,
        'rainfall': rainfall,
        'ndvi': ndvi,
    })
    return df

# ============================================================================
# TRIGGER LOGIC (A: Threshold, B: Trend)
# ============================================================================

def check_threshold_alerts(cell_id, ts, crop):
    """A) Check if current values breach thresholds."""
    alerts = []
    thresholds = CROP_THRESHOLDS.get(crop, CROP_THRESHOLDS['maize'])
    current = ts.iloc[-1]

    if current['sm'] < thresholds['sm_critical']:
        alerts.append({
            'type': 'drought_critical',
            'reason': 'threshold',
            'message': f"CRITICAL: SM={current['sm']:.3f} < {thresholds['sm_critical']}",
            'severity': 'critical',
        })
    elif current['sm'] < thresholds['sm_irrigation']:
        alerts.append({
            'type': 'irrigation_needed',
            'reason': 'threshold',
            'message': f"WARNING: SM={current['sm']:.3f} < {thresholds['sm_irrigation']}. Irrigate soon.",
            'severity': 'warning',
        })

    rainfall_7d = ts.iloc[-7:]['rainfall'].sum()
    if rainfall_7d < thresholds['rainfall_deficit']:
        alerts.append({
            'type': 'rainfall_deficit',
            'reason': 'threshold',
            'message': f"ALERT: 7-day rainfall={rainfall_7d:.1f}mm < {thresholds['rainfall_deficit']}mm",
            'severity': 'warning',
        })

    ndvi_now = current['ndvi']
    ndvi_7d_avg = ts.iloc[-7:]['ndvi'].mean()
    ndvi_drop = ndvi_7d_avg - ndvi_now
    if ndvi_drop > thresholds['ndvi_stress']:
        alerts.append({
            'type': 'crop_stress',
            'reason': 'threshold',
            'message': f"ALERT: NDVI dropped {ndvi_drop:.3f}",
            'severity': 'warning',
        })

    return alerts

def check_trend_alerts(cell_id, ts):
    """B) Check if values are declining (early warning)."""
    alerts = []

    sm_last3 = ts.iloc[-3:]['sm'].values
    if len(sm_last3) == 3:
        is_declining = (sm_last3[0] > sm_last3[1]) and (sm_last3[1] > sm_last3[2])
        if is_declining:
            sm_decline = sm_last3[0] - sm_last3[2]
            alerts.append({
                'type': 'drought_developing',
                'reason': 'trend',
                'message': f"EARLY WARNING: SM declining 3 days ({sm_decline:.4f} drop). Drought incoming.",
                'severity': 'caution',
            })

    return alerts

def process_cell(cell_id, crop):
    """Run both threshold (A) and trend (B) checks."""
    ts = generate_mock_timeseries(cell_id)
    threshold_alerts = check_threshold_alerts(cell_id, ts, crop)
    trend_alerts = check_trend_alerts(cell_id, ts)
    return ts, threshold_alerts + trend_alerts

# ============================================================================
# MAIN: Run prototype
# ============================================================================

def main():
    print("\n" + "="*80)
    print("SOILSENSE EARLY WARNING SYSTEM — PROTOTYPE LOGIC TEST")
    print("="*80)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    all_alerts = []

    for cell in GRID_CELLS:
        cell_id = cell['cell_id']
        cell_name = cell['name']
        crop = cell['crop']

        ts, alerts = process_cell(cell_id, crop)

        current_sm = ts.iloc[-1]['sm']
        status = "🔴 ALERT" if alerts else "🟢 OK"
        print(f"{status} | {cell_id} ({cell_name:20s}) | Crop: {crop:8s} | SM={current_sm:.3f}")

        for alert in alerts:
            severity_emoji = {'critical': '🔴', 'warning': '🟡', 'caution': '🟠'}.get(alert['severity'], '⚪')
            print(f"       {severity_emoji} [{alert['reason'].upper()}] {alert['type']}: {alert['message']}")
            all_alerts.append({
                'timestamp': datetime.now().isoformat(),
                'cell_id': cell_id,
                'cell_name': cell_name,
                'crop': crop,
                **alert,
            })

    print("\n" + "="*80)
    critical_count = sum(1 for a in all_alerts if a['severity'] == 'critical')
    warning_count = sum(1 for a in all_alerts if a['severity'] == 'warning')
    caution_count = sum(1 for a in all_alerts if a['severity'] == 'caution')
    print(f"SUMMARY: {critical_count} CRITICAL | {warning_count} WARNING | {caution_count} CAUTION")
    print(f"Total alerts fired: {len(all_alerts)}")
    print("="*80 + "\n")

    with open('alert_log.json', 'w') as f:
        json.dump(all_alerts, f, indent=2)
    print(f"✓ Alert log saved to alert_log.json")

    grid_state = []
    for cell in GRID_CELLS:
        ts, alerts = process_cell(cell['cell_id'], cell['crop'])
        alert_types = [a['type'] for a in alerts]
        severity = max([a['severity'] for a in alerts], default='ok') if alerts else 'ok'

        grid_state.append({
            'cell_id': cell['cell_id'],
            'lat': cell['lat'],
            'lon': cell['lon'],
            'name': cell['name'],
            'crop': cell['crop'],
            'sm': ts.iloc[-1]['sm'],
            'rainfall_7d': ts.iloc[-7:]['rainfall'].sum(),
            'ndvi': ts.iloc[-1]['ndvi'],
            'alerts': ','.join(alert_types),
            'severity': severity,
        })

    grid_df = pd.DataFrame(grid_state)
    grid_df.to_csv('grid_state.csv', index=False)
    print(f"✓ Grid state saved to grid_state.csv")
    print(f"\nReady to show Merlyn:")
    print(f"  1. Alert log: alert_log.json")
    print(f"  2. Grid state: grid_state.csv")
    print(f"  3. Dashboard: open index.html in browser\n")

if __name__ == '__main__':
    main()
