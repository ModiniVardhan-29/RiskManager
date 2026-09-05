# src/calibration_analysis.py
import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from xgboost import XGBClassifier
from sklearn.calibration import calibration_curve

def get_percentile_stats(arr):
    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99))
    }

def run_calibration_analysis(data_dir: str = "outputs", model_dir: str = "models", output_dir: str = "outputs/calibration"):
    print("=" * 60)
    print("STAGE 10: CALIBRATION CURVES & DISTRIBUTION ANALYSIS")
    print("=" * 60)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load Models & Test Data
    print("Loading models and calibrators...")
    base_model = XGBClassifier()
    base_model.load_model(os.path.join(model_dir, "baseline_xgboost.json"))
    base_calibrator = joblib.load(os.path.join(model_dir, "baseline_calibrator.pkl"))
    
    rg_model = XGBClassifier()
    rg_model.load_model(os.path.join(model_dir, "riskgraph_xgboost.json"))
    rg_calibrator = joblib.load(os.path.join(model_dir, "riskgraph_calibrator.pkl"))
    
    # Load Data
    train_df = pd.read_parquet(os.path.join(data_dir, "train_graph.parquet"))
    test_base = pd.read_parquet(os.path.join(data_dir, "test.parquet"))
    test_rg = pd.read_parquet(os.path.join(data_dir, "test_graph.parquet"))
    
    # Frequency Encodings
    cat_cols = ['category', 'gender']
    for col in cat_cols:
        freq_map = train_df[col].value_counts(normalize=True).to_dict()
        test_base[f'{col}_freq'] = test_base[col].map(freq_map).fillna(0)
        test_rg[f'{col}_freq'] = test_rg[col].map(freq_map).fillna(0)
        
    with open(os.path.join(model_dir, "baseline_metrics.json")) as f:
        base_features = json.load(f)["features"]
    with open(os.path.join(model_dir, "riskgraph_metrics.json")) as f:
        rg_features = json.load(f)["features"]
        
    y_test = test_rg['is_fraud'].values
    
    # Compute Probabilities
    print("Generating raw and calibrated probability predictions...")
    base_raw = base_model.predict_proba(test_base[base_features])[:, 1]
    base_calib = base_calibrator.transform(base_raw)
    
    rg_raw = rg_model.predict_proba(test_rg[rg_features])[:, 1]
    rg_calib = rg_calibrator.transform(rg_raw)
    
    # 1. Generate Reliability Diagram
    print("Plotting Reliability Diagram...")
    plt.figure(figsize=(9, 7))
    plt.plot([0, 1], [0, 1], "k--", label="Perfectly Calibrated")
    
    for name, raw, calib in [("Baseline", base_raw, base_calib), ("RiskGraph", rg_raw, rg_calib)]:
        prob_true_raw, prob_pred_raw = calibration_curve(y_test, raw, n_bins=10)
        prob_true_calib, prob_pred_calib = calibration_curve(y_test, calib, n_bins=10)
        
        plt.plot(prob_pred_raw, prob_true_raw, "s-", label=f"{name} (Raw Risk Score)")
        plt.plot(prob_pred_calib, prob_true_calib, "o-", label=f"{name} (Calibrated)")
        
    plt.xlabel("Mean Predicted Probability", fontsize=11)
    plt.ylabel("Fraction of Positives", fontsize=11)
    plt.title("Reliability Diagram: Raw Risk Score vs. Calibrated Probability", fontsize=12, pad=15)
    plt.legend(loc="upper left")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    
    chart_path = os.path.join(output_dir, "reliability_diagram.png")
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"Saved Calibration Chart to {chart_path}")
    
    # 2. Probability Distribution Analysis
    print("Saving probability distribution metrics...")
    legit_mask = (y_test == 0)
    fraud_mask = (y_test == 1)
    
    dist_analysis = {
        "riskgraph_raw": {
            "legitimate": get_percentile_stats(rg_raw[legit_mask]),
            "fraud": get_percentile_stats(rg_raw[fraud_mask])
        },
        "riskgraph_calibrated": {
            "legitimate": get_percentile_stats(rg_calib[legit_mask]),
            "fraud": get_percentile_stats(rg_calib[fraud_mask])
        }
    }
    
    dist_path = os.path.join(output_dir, "probability_distribution_analysis.json")
    with open(dist_path, "w") as f:
        json.dump(dist_analysis, f, indent=4)
    print(f"Saved Distribution Summary to {dist_path}\n" + "=" * 60)

if __name__ == "__main__":
    run_calibration_analysis()