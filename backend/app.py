"""
SoilSense Backend Prototype
Layer 1: Data Input → Layer 2: Processing → Layer 3: Validation → Layer 4: Output
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from datetime import datetime
import numpy as np
import traceback
from ml_engine import predict_soil_moisture, load_mock_model
from validation import validate_predictions
from sms_dispatcher import generate_sms_alert, get_alert_log

app = FastAPI(title="SoilSense Backend", version="1.0")

# CORS - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global state for demo
SYSTEM_STATE = {
    "model": None,
    "last_update": None,
    "current_predictions": None,
    "alerts": [],
    "validation_metrics": {},
    "trust_score": "🟢",
}

@app.on_event("startup")
async def startup_event():
    """Load ML model on startup"""
    try:
        print("[Layer 2] Loading Random Forest model...")
        SYSTEM_STATE["model"] = load_mock_model()
        print("[Layer 2] ✓ Model loaded. Ready for predictions.")
    except Exception as e:
        print(f"✗ Model load error: {e}")
        SYSTEM_STATE["model"] = None

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "service": "SoilSense Backend",
        "version": "1.0",
        "status": "running",
    }

@app.get("/health")
def health_check():
    """System status"""
    return {
        "status": "operational",
        "last_update": SYSTEM_STATE["last_update"],
        "model_loaded": SYSTEM_STATE["model"] is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/pipeline/status")
def pipeline_status():
    """Full pipeline status (all 4 layers)"""
    return {
        "layer1_data": "Connected" if True else "Error",  # Mock
        "layer2_model": "Ready" if SYSTEM_STATE["model"] else "Loading",
        "layer3_validation": "OK" if SYSTEM_STATE["validation_metrics"] else "Pending",
        "layer4_output": "Ready",
        "trust_score": SYSTEM_STATE["trust_score"],
    }

@app.post("/pipeline/run")
def run_daily_pipeline():
    """
    Simulate daily pipeline execution:
    Layer 1 → Layer 2 → Layer 3 → Layer 4
    """
    try:
        print("\n" + "="*60)
        print("DAILY PIPELINE EXECUTION")
        print("="*60)

    # --- LAYER 1: DATA INPUT ---
    print("\n[LAYER 1] Data Input")
    print("  • Fetching SMAP (9-km)...")
    print("  • Fetching Sentinel-2 (NDVI)...")
    print("  • Fetching CHIRPS (rainfall)...")
    print("  • Fetching u-blox GNSS-R (validation)...")

    # Mock data (10 grid cells)
    n_cells = 10
    smap_values = np.random.uniform(0.10, 0.40, n_cells)
    chirps_7d = np.random.uniform(10, 80, n_cells)
    ndvi = np.random.uniform(0.3, 0.8, n_cells)
    ublox_truth = smap_values + np.random.normal(0, 0.01, n_cells)  # Add small noise

    print(f"  ✓ Data ingested ({n_cells} cells)")

    # --- LAYER 2: PROCESSING & MODELING ---
    print("\n[LAYER 2] Processing & Modeling")
    print("  • Loading Random Forest model...")
    print("  • Computing 10-m predictions...")

    # Predict soil moisture (mock Random Forest)
    predictions = predict_soil_moisture(
        smap=smap_values,
        chirps_7d=chirps_7d,
        ndvi=ndvi,
        model=SYSTEM_STATE["model"]
    )

    print(f"  • Regression-Kriging interpolation (10-m grid)...")
    print(f"  ✓ Predictions complete")

    # Trigger alert logic (Layer 2)
    print("\n  Alert Trigger Logic:")
    alerts = []
    for i in range(n_cells):
        sm = predictions[i]
        cell_id = f"L{str(i+1).zfill(2)}"

        # Threshold checks (A)
        if sm < 0.10:
            alerts.append({
                "cell_id": cell_id,
                "sm_value": sm,
                "alert_type": "drought_critical",
                "severity": "🔴",
                "trigger_reason": f"SM = {sm:.3f} < 0.10 (critical)",
                "timestamp": datetime.utcnow().isoformat(),
            })
            print(f"    {cell_id}: 🔴 CRITICAL (SM={sm:.3f})")
        elif sm < 0.15:
            alerts.append({
                "cell_id": cell_id,
                "sm_value": sm,
                "alert_type": "irrigation_needed",
                "severity": "🟡",
                "trigger_reason": f"SM = {sm:.3f} < 0.15 (warning)",
                "timestamp": datetime.utcnow().isoformat(),
            })
            print(f"    {cell_id}: 🟡 WARNING (SM={sm:.3f})")
        else:
            print(f"    {cell_id}: 🟢 OK (SM={sm:.3f})")

    SYSTEM_STATE["current_predictions"] = {
        "cell_ids": [f"L{str(i+1).zfill(2)}" for i in range(n_cells)],
        "sm_values": predictions.tolist(),
        "alerts_triggered": len(alerts),
    }

    # --- LAYER 3: VALIDATION & QUALITY CONTROL ---
    print("\n[LAYER 3] Validation & Quality Control")
    print("  • Comparing predictions vs. u-blox GNSS-R ground truth...")

    metrics = validate_predictions(predictions, ublox_truth)
    SYSTEM_STATE["validation_metrics"] = metrics

    print(f"  • Pearson R: {metrics['r']:.3f} (target: ≥0.80) {'✓' if metrics['r'] >= 0.80 else '✗'}")
    print(f"  • RMSE: {metrics['rmse']:.4f} m³/m³ (target: ≤0.040) {'✓' if metrics['rmse'] <= 0.040 else '✗'}")
    print(f"  • MAE: {metrics['mae']:.4f} m³/m³ (target: ≤0.030) {'✓' if metrics['mae'] <= 0.030 else '✗'}")
    print(f"  • Bias: {metrics['bias']:+.4f} m³/m³ (target: ±0.02) {'✓' if abs(metrics['bias']) <= 0.02 else '✗'}")

    # Calculate trust score
    all_pass = (
        metrics['r'] >= 0.80 and
        metrics['rmse'] <= 0.040 and
        metrics['mae'] <= 0.030 and
        abs(metrics['bias']) <= 0.02
    )
    SYSTEM_STATE["trust_score"] = "🟢 All metrics pass" if all_pass else "🟡 Some warnings"
    print(f"  ✓ Trust Score: {SYSTEM_STATE['trust_score']}")

    # --- LAYER 4: OUTPUT CHANNELS ---
    print("\n[LAYER 4] Output Channels")
    print("  • Generating SMS alerts...")

    SYSTEM_STATE["alerts"] = alerts
    sms_log = []
    for alert in alerts:
        sms_msg = generate_sms_alert(
            cell_id=alert["cell_id"],
            sm_value=alert["sm_value"],
            alert_type=alert["alert_type"],
            crop="maize"  # Default crop
        )
        sms_log.append({
            "cell_id": alert["cell_id"],
            "message": sms_msg,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending_dispatch"  # Would send via Twilio in production
        })
        print(f"    [{alert['cell_id']}] {sms_msg[:50]}...")

    print(f"  • Updating dashboard (WebSocket)...")
    print(f"  • SMS alerts ready for dispatch: {len(sms_log)}")
    print(f"  ✓ Layer 4 complete")

    SYSTEM_STATE["last_update"] = datetime.utcnow().isoformat()

        print("\n" + "="*60)
        print("PIPELINE EXECUTION COMPLETE ✓")
        print("="*60 + "\n")

        return {
            "status": "success",
            "timestamp": SYSTEM_STATE["last_update"],
            "predictions": SYSTEM_STATE["current_predictions"],
            "alerts_triggered": len(alerts),
            "validation_metrics": metrics,
            "trust_score": SYSTEM_STATE["trust_score"],
            "sms_ready": len(sms_log),
        }

    except Exception as e:
        print(f"\n✗ PIPELINE ERROR: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }

@app.get("/dashboard/maps")
def get_soil_moisture_maps():
    """Layer 4: Return 10-m soil moisture map data for frontend"""
    try:
        if not SYSTEM_STATE["current_predictions"]:
            return {
                "cell_ids": [],
                "sm_values": [],
                "color_coded": [],
            }

        return {
            "cell_ids": SYSTEM_STATE["current_predictions"]["cell_ids"],
            "sm_values": SYSTEM_STATE["current_predictions"]["sm_values"],
            "color_coded": [
                "drought" if v < 0.10 else "monitor" if v < 0.15 else "safe"
                for v in SYSTEM_STATE["current_predictions"]["sm_values"]
            ],
        }
    except Exception as e:
        print(f"Error in get_soil_moisture_maps: {e}")
        return {"error": str(e)}

@app.get("/dashboard/alerts")
def get_active_alerts():
    """Layer 4: Return current alerts for dashboard"""
    try:
        alerts = SYSTEM_STATE["alerts"] or []
        return {
            "total_alerts": len(alerts),
            "critical": sum(1 for a in alerts if a.get("alert_type") == "drought_critical"),
            "warning": sum(1 for a in alerts if a.get("alert_type") == "irrigation_needed"),
            "alerts": alerts,
        }
    except Exception as e:
        print(f"Error in get_active_alerts: {e}")
        return {"total_alerts": 0, "critical": 0, "warning": 0, "alerts": []}

@app.get("/dashboard/validation")
def get_validation_metrics():
    """Layer 3: Return validation metrics for dashboard widget"""
    try:
        metrics = SYSTEM_STATE["validation_metrics"] or {}
        return {
            "metrics": metrics,
            "trust_score": SYSTEM_STATE["trust_score"],
        }
    except Exception as e:
        print(f"Error in get_validation_metrics: {e}")
        return {
            "metrics": {},
            "trust_score": "🟡",
        }

@app.get("/sms/log")
def get_sms_alert_log():
    """Layer 4: SMS dispatcher log"""
    try:
        alerts = SYSTEM_STATE["alerts"] or []
        log = get_alert_log(alerts)
        return {
            "total_alerts": len(log),
            "alerts": log,
        }
    except Exception as e:
        print(f"Error in get_sms_alert_log: {e}")
        return {"total_alerts": 0, "alerts": []}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("🌱 SoilSense Backend")
    print("="*70)
    print("Status: Starting...")
    print("Access: http://localhost:8000")
    print("Docs:   http://localhost:8000/docs")
    print("="*70 + "\n")

    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"\n✗ Server error: {e}")
        import traceback
        traceback.print_exc()
