"""
Layer 2: ML Engine
Regression-Kriging downscaling via Random Forest
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import pickle

def load_mock_model():
    """
    Load or create mock Random Forest model for soil moisture prediction.
    In production: load from trained_rf_model.pkl
    """
    print("  [ML Engine] Creating mock Random Forest model (trained on 2021-2022 data)...")

    # In real scenario, this would load:
    # with open('data/trained_rf_model.pkl', 'rb') as f:
    #     return pickle.load(f)

    # For demo: create a mock model that maps inputs to realistic SM values
    model = {
        "type": "RandomForestRegressor",
        "features": ["smap", "chirps_7d", "ndvi", "doy", "clay", "sand", "elevation"],
        "performance": {
            "r_squared": 0.9542,
            "rmse": 0.0209,  # m³/m³
            "mae": 0.0176,
        },
        "trained_on": "2021-2022 SMAP + Sentinel-2 + CHIRPS + SoilGrids v2",
    }

    return model

def predict_soil_moisture(smap, chirps_7d, ndvi, model):
    """
    Layer 2: Predict 10-m soil moisture using Random Forest + Kriging.

    Inputs:
    - smap: 9-km SMAP values (array, n_cells)
    - chirps_7d: 7-day cumulative rainfall (array, n_cells)
    - ndvi: NDVI index (array, n_cells)
    - model: Trained RF model dict

    Returns:
    - predictions: 10-m downscaled SM estimates (array, n_cells)
    """

    n_cells = len(smap)

    # Feature normalization (mock)
    # Real: StandardScaler fitted on training data
    smap_norm = (smap - 0.25) / 0.15  # Mock normalization
    chirps_norm = (chirps_7d - 40) / 30
    ndvi_norm = (ndvi - 0.55) / 0.25

    # Simplified RF inference logic:
    # SM_predicted = f(SMAP, CHIRPS, NDVI, ...)
    # Real model has 100+ trees, here we use linear approximation for transparency

    predictions = np.zeros(n_cells)

    for i in range(n_cells):
        # Mock RF logic: weighted combination of inputs
        # Weights based on feature importance from Merlyn's thesis
        sm_pred = (
            0.60 * smap[i] +           # SMAP is strongest predictor
            0.15 * (chirps_7d[i] / 100) +  # Rainfall influence (normalized)
            0.15 * ndvi[i] +           # Vegetation influence
            0.10 * (0.3 - 0.05 * (chirps_7d[i] < 20))  # Drought stress
        )

        # Regression-Kriging: add spatial smoothing via kriging residuals
        # Mock: small random perturbation (kriging std ≈ 0.0089)
        kriging_smooth = np.random.normal(0, 0.009)

        # Final 10-m prediction (bounded to realistic range)
        predictions[i] = np.clip(sm_pred + kriging_smooth, 0.05, 0.55)

    return predictions

def calculate_feature_importance():
    """
    Return feature importance from trained model
    (Merlyn's thesis: Fig 18 feature importance)
    """
    return {
        "smap_lag1": 0.45,
        "ndvi": 0.22,
        "chirps_7d": 0.18,
        "sand_percent": 0.08,
        "elevation": 0.04,
        "doy": 0.03,
    }

def generate_10m_map(predictions, cell_ids):
    """
    Convert point predictions to continuous 10-m raster.
    In production: IDW or kriging interpolation → GeoTIFF
    """
    return {
        "resolution": "10 m",
        "cell_ids": cell_ids,
        "sm_values": predictions.tolist(),
        "format": "numpy array (real: GeoTIFF via rasterio)",
    }
