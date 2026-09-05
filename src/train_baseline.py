# src/train_baseline.py
import os
import json
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    precision_score, recall_score, f1_score, 
    average_precision_score, roc_auc_score, confusion_matrix,
    brier_score_loss
)

def find_optimal_threshold(calibrator, raw_probs, y_val, cost_fp=10.0, cost_fn=120.0):
    """
    Sweeps decision thresholds on CALIBRATED validation probabilities to find 
    the threshold that minimizes business financial loss.
    """
    calibrated_probs = calibrator.transform(raw_probs)
    thresholds = np.arange(0.10, 0.95, 0.01)
    best_threshold = 0.50
    min_loss = float('inf')
    
    for t in thresholds:
        preds = (calibrated_probs >= t).astype(int)
        fp = np.sum((preds == 1) & (y_val == 0))
        fn = np.sum((preds == 0) & (y_val == 1))
        
        total_loss = (fp * cost_fp) + (fn * cost_fn)
        
        if total_loss < min_loss:
            min_loss = total_loss
            best_threshold = t
            
    return float(best_threshold)

def train_baseline_model(data_dir: str = "outputs", model_dir: str = "models", cost_fp: float = 10.0, cost_fn: float = 120.0):
    print("=" * 60)
    print("STAGE 4 & 5: TRAINING BASELINE XGBOOST (TRANSACTION-ONLY + CALIBRATION)")
    print("=" * 60)
    
    os.makedirs(model_dir, exist_ok=True)
    
    # 1. Load Parquet Data
    print("Loading raw split datasets...")
    train_df = pd.read_parquet(os.path.join(data_dir, "train.parquet"))
    val_df = pd.read_parquet(os.path.join(data_dir, "val.parquet"))
    test_df = pd.read_parquet(os.path.join(data_dir, "test.parquet"))
    
    # 2. Baseline Features Only
    features = [
        'amt', 'distance_km', 'age', 'city_pop', 
        'trans_hour', 'trans_dayofweek', 'lat', 'long', 
        'merch_lat', 'merch_long'
    ]
    
    # Categorical Frequency Encoding strictly from train split
    cat_cols = ['category', 'gender']
    for col in cat_cols:
        freq_map = train_df[col].value_counts(normalize=True).to_dict()
        train_df[f'{col}_freq'] = train_df[col].map(freq_map).fillna(0)
        val_df[f'{col}_freq'] = val_df[col].map(freq_map).fillna(0)
        test_df[f'{col}_freq'] = test_df[col].map(freq_map).fillna(0)
        features.append(f'{col}_freq')
        
    X_train, y_train = train_df[features], train_df['is_fraud']
    X_val, y_val = val_df[features], val_df['is_fraud']
    X_test, y_test = test_df[features], test_df['is_fraud']
    
    # 3. Calculate Scale Pos Weight
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / pos_count
    
    # 4. Train Baseline XGBoost
    print("\nTraining Baseline XGBoost model...")
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        tree_method="hist",
        n_jobs=-1
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50
    )
    
    # Save Model
    model_path = os.path.join(model_dir, "baseline_xgboost.json")
    model.save_model(model_path)
    print(f"\nSaved Baseline model to {model_path}")
    
    # 5. Fit Calibrator ONLY on Validation Set Predictions
    print("\nFitting Isotonic Calibrator strictly on Validation Set predictions...")
    val_raw_probs = model.predict_proba(X_val)[:, 1]
    
    calibrator = IsotonicRegression(out_of_bounds='clip')
    calibrator.fit(val_raw_probs, y_val)
    
    calibrator_path = os.path.join(model_dir, "baseline_calibrator.pkl")
    joblib.dump(calibrator, calibrator_path)
    print(f"Saved Baseline Calibrator to {calibrator_path}")
    
    # 6. Optimize Threshold on Calibrated Validation Probabilities
    optimal_thresh = find_optimal_threshold(calibrator, val_raw_probs, y_val, cost_fp, cost_fn)
    print(f"Optimal Baseline Threshold (Calibrated Val Set): {optimal_thresh:.2f}")
    
    # 7. Evaluate Baseline Split Function
    def evaluate_split(name, X, y, threshold):
        raw_probs = model.predict_proba(X)[:, 1]
        calibrated_probs = calibrator.transform(raw_probs)
        preds = (calibrated_probs >= threshold).astype(int)
        
        prec = precision_score(y, preds, zero_division=0)
        rec = recall_score(y, preds, zero_division=0)
        f1 = f1_score(y, preds, zero_division=0)
        pr_auc = average_precision_score(y, raw_probs)
        roc_auc = roc_auc_score(y, raw_probs)
        
        brier_raw = brier_score_loss(y, raw_probs)
        brier_calibrated = brier_score_loss(y, calibrated_probs)
        
        cm = confusion_matrix(y, preds)
        fp_cost_val = cm[0][1] * cost_fp
        fn_cost_val = cm[1][0] * cost_fn
        total_loss_val = fp_cost_val + fn_cost_val
        
        print(f"\n--- BASELINE EVALUATION: {name.upper()} (Threshold={threshold:.2f}) ---")
        print(f"Precision:            {prec:.4f}")
        print(f"Recall:               {rec:.4f}")
        print(f"F1 Score:             {f1:.4f}")
        print(f"PR-AUC:               {pr_auc:.4f}")
        print(f"ROC-AUC:              {roc_auc:.4f}")
        print(f"Brier Score (Raw):    {brier_raw:.4f}")
        print(f"Brier Score (Calib):  {brier_calibrated:.4f}")
        print(f"Confusion Matrix:\n  TN: {cm[0][0]:<8} FP: {cm[0][1]}")
        print(f"  FN: {cm[1][0]:<8} TP: {cm[1][1]}")
        print(f"Estimated Loss:       ${total_loss_val:,.2f}")
        
        return {
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "pr_auc": float(pr_auc),
            "roc_auc": float(roc_auc),
            "brier_score_raw": float(brier_raw),
            "brier_score_calibrated": float(brier_calibrated),
            "false_positives": int(cm[0][1]),
            "false_negatives": int(cm[1][0]),
            "threshold_used": threshold,
            "financial_loss": total_loss_val
        }
        
    val_metrics = evaluate_split("Validation Set", X_val, y_val, threshold=optimal_thresh)
    test_metrics = evaluate_split("Held-out Test Set", X_test, y_test, threshold=optimal_thresh)
    
    metrics_summary = {
        "validation": val_metrics,
        "test": test_metrics,
        "features": features
    }
    with open(os.path.join(model_dir, "baseline_metrics.json"), "w") as f:
        json.dump(metrics_summary, f, indent=4)

if __name__ == "__main__":
    train_baseline_model()