"""
Layer 3: Validation & Quality Control
Independent u-blox GNSS-R comparison
"""

import numpy as np
from scipy import stats

def validate_predictions(predictions, ublox_truth):
    """
    Layer 3: Validate model predictions against independent u-blox GNSS-R measurements.

    Inputs:
    - predictions: RF-Kriging 10-m SM estimates
    - ublox_truth: Independent u-blox ground truth measurements

    Returns:
    - metrics: Dict with R, RMSE, MAE, Bias (Table 19 in Maryline's thesis)
    """

    # Calculate metrics
    pearson_r = np.corrcoef(predictions, ublox_truth)[0, 1]
    rmse = np.sqrt(np.mean((predictions - ublox_truth) ** 2))
    mae = np.mean(np.abs(predictions - ublox_truth))
    bias = np.mean(predictions - ublox_truth)

    # Linear regression fit (for 1:1 validation plot)
    slope, intercept, r_value, p_value, std_err = stats.linregress(ublox_truth, predictions)

    # Operational thresholds (from Maryline's thesis, Table 19)
    thresholds = {
        "pearson_r_min": 0.80,
        "rmse_max": 0.040,
        "mae_max": 0.030,
        "bias_range": (-0.02, 0.02),
    }

    # Check against thresholds
    passes = {
        "pearson_r": pearson_r >= thresholds["pearson_r_min"],
        "rmse": rmse <= thresholds["rmse_max"],
        "mae": mae <= thresholds["mae_max"],
        "bias": thresholds["bias_range"][0] <= bias <= thresholds["bias_range"][1],
    }

    return {
        "r": pearson_r,
        "rmse": rmse,
        "mae": mae,
        "bias": bias,
        "regression_slope": slope,
        "regression_intercept": intercept,
        "p_value": p_value,
        "n_samples": len(predictions),
        "thresholds": thresholds,
        "passes": passes,
        "all_pass": all(passes.values()),
    }

def calculate_trust_score(metrics):
    """
    Generate "Trust Score" widget value (Layer 3).
    Returns emoji + confidence level.
    """

    if metrics["all_pass"]:
        return "🟢 All metrics pass | High confidence"
    elif sum(metrics["passes"].values()) >= 3:
        return "🟡 Most metrics pass | Medium confidence"
    else:
        return "🔴 Validation failed | Low confidence - Review model"

def threshold_monitor(metrics):
    """
    Monitor real-time metric divergence.
    Flag if validation degrades (e.g., R drops below 0.80).
    """

    warnings = []

    if metrics["r"] < 0.80:
        warnings.append(f"⚠️ Pearson R degraded to {metrics['r']:.3f} (target ≥0.80)")
    if metrics["rmse"] > 0.040:
        warnings.append(f"⚠️ RMSE increased to {metrics['rmse']:.4f} m³/m³ (target ≤0.040)")
    if abs(metrics["bias"]) > 0.02:
        warnings.append(f"⚠️ Bias high: {metrics['bias']:+.4f} m³/m³ (target ±0.02)")

    return {
        "status": "OK" if not warnings else "WARNING",
        "warnings": warnings,
    }

def generate_trust_widget():
    """
    HTML widget for Layer 3 validation display on dashboard.
    Shows Table 19 metrics in farmer-friendly format.
    """

    widget_html = """
    <div class="trust-widget">
        <h3>System Reliability (Table 19)</h3>
        <table>
            <tr>
                <td>Accuracy (Pearson R)</td>
                <td id="metric-r">0.93 ✓</td>
                <td>Target: ≥0.80</td>
            </tr>
            <tr>
                <td>Error (RMSE)</td>
                <td id="metric-rmse">0.0181 ✓</td>
                <td>Target: ≤0.040 m³/m³</td>
            </tr>
            <tr>
                <td>Mean Error (MAE)</td>
                <td id="metric-mae">0.0131 ✓</td>
                <td>Target: ≤0.030 m³/m³</td>
            </tr>
            <tr>
                <td>Systematic Bias</td>
                <td id="metric-bias">+0.0021 ✓</td>
                <td>Target: ±0.02 m³/m³</td>
            </tr>
        </table>
        <div class="trust-score">
            <strong id="trust-emoji">🟢</strong>
            <strong id="trust-text">All metrics pass - High confidence</strong>
        </div>
        <p>Last updated: <span id="last-update">2026-04-27 00:31 UTC</span></p>
    </div>
    """

    return widget_html
