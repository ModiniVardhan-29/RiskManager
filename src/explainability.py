# src/explainability.py
import os
import json
import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
from xgboost import XGBClassifier

def run_shap_explainability(data_dir: str = "outputs", model_dir: str = "models", reports_dir: str = "reports"):
    print("=" * 60)
    print("STAGE 10: EXPLAINABLE AI WITH SHAP (RISKGRAPH)")
    print("=" * 60)
    
    os.makedirs(reports_dir, exist_ok=True)
    
    # 1. Load Model & Test Data
    print("Loading RiskGraph model & test dataset...")
    model_path = os.path.join(model_dir, "riskgraph_xgboost.json")
    model = XGBClassifier()
    model.load_model(model_path)
    
    test_df = pd.read_parquet(os.path.join(data_dir, "test_graph.parquet"))
    
    # Load feature order metadata
    with open(os.path.join(model_dir, "riskgraph_metrics.json"), "r") as f:
        features = json.load(f)["features"]
        
    # Re-encode category frequencies strictly from training reference
    cat_cols = ['category', 'gender']
    train_df = pd.read_parquet(os.path.join(data_dir, "train_graph.parquet"))
    for col in cat_cols:
        freq_map = train_df[col].value_counts(normalize=True).to_dict()
        test_df[f'{col}_freq'] = test_df[col].map(freq_map).fillna(0)
        
    X_test = test_df[features]
    
    # 2. Sample data for SHAP analysis
    print("Sampling test data for fast SHAP computation...")
    sample_size = min(5000, len(X_test))
    X_sample = X_test.sample(n=sample_size, random_state=42)
    
    # 3. Tree SHAP Calculation
    print("Computing Tree SHAP values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_sample)
    
    # 4. Save Feature Importance Chart
    print("\nGenerating SHAP feature importance plot...")
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_sample, plot_type="bar", show=False)
    plt.title("RiskGraph Feature Importance (Mean |SHAP Value|)", fontsize=12, pad=15)
    plt.tight_layout()
    bar_plot_path = os.path.join(reports_dir, "shap_feature_importance.png")
    plt.savefig(bar_plot_path, dpi=300)
    plt.close()
    print(f"Saved feature importance chart to: {bar_plot_path}")
    
    # 5. Save Beeswarm Plot
    plt.figure(figsize=(11, 7))
    shap.summary_plot(shap_values, X_sample, show=False)
    plt.title("SHAP Beeswarm Plot (Impact on Fraud Risk Score)", fontsize=12, pad=15)
    plt.tight_layout()
    beeswarm_plot_path = os.path.join(reports_dir, "shap_beeswarm.png")
    plt.savefig(beeswarm_plot_path, dpi=300)
    plt.close()
    print(f"Saved beeswarm chart to: {beeswarm_plot_path}")

if __name__ == "__main__":
    run_shap_explainability()