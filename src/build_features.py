import os
import pandas as pd
import numpy as np

def apply_leakage_free_encodings(train_df: pd.DataFrame, test_df: pd.DataFrame):
    cat_cols = ['category', 'gender']
    for col in cat_cols:
        if col in train_df.columns:
            freq_map = train_df[col].value_counts(normalize=True).to_dict()
            train_df[f'{col}_freq'] = train_df[col].map(freq_map).fillna(0.0)
            test_df[f'{col}_freq'] = test_df[col].map(freq_map).fillna(0.0)
    return train_df, test_df

def build_all_features():
    print("============================================================")
    print("STAGE 3: BUILDING BASELINE FEATURES")
    print("============================================================")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "outputs")
    
    train_path = os.path.join(output_dir, "train.parquet")
    test_path = os.path.join(output_dir, "test.parquet")
    
    if not os.path.exists(train_path) or not os.path.exists(test_path):
        raise FileNotFoundError(f"Missing preprocessed parquet files in {output_dir}. Run preprocessing.py first.")
        
    print("Loading preprocessed dataset splits...")
    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)
    
    print("Applying leakage-free frequency encodings...")
    train_df, test_df = apply_leakage_free_encodings(train_df, test_df)
    
    out_train_path = os.path.join(output_dir, "train_features.parquet")
    out_test_path = os.path.join(output_dir, "test_features.parquet")
    
    train_df.to_parquet(out_train_path, index=False)
    test_df.to_parquet(out_test_path, index=False)
    
    print(f"? Baseline features successfully built and saved to:\n - {out_train_path}\n - {out_test_path}")

if __name__ == "__main__":
    build_all_features()
