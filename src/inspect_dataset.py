# src/inspect_dataset.py
import os
import pandas as pd
import numpy as np

def run_dataset_audit(data_path: str):
    """
    Performs a thorough audit of the input transaction CSV dataset.
    Prints schema, sample rows, missing values, timestamp range, and target imbalance.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset path not found at: {data_path}")

    print("=" * 60)
    print("STAGE 1: RISKGRAPH AI - DATASET AUDIT")
    print("=" * 60)
    print(f"Loading data from: {data_path}\n")

    df = pd.read_csv(data_path)

    # 1. Basic Dimensions
    print("--- 1. SHAPE & MEMORY USAGE ---")
    print(f"Total Rows: {df.shape[0]:,}")
    print(f"Total Columns: {df.shape[1]}")
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
    print(f"Memory Usage: {memory_mb:.2f} MB\n")

    # 2. Columns & Data Types
    print("--- 2. COLUMN DATA TYPES & MISSING VALUES ---")
    dtypes_df = pd.DataFrame({
        "Column": df.columns,
        "DataType": df.dtypes.values,
        "Missing_Count": df.isnull().sum().values,
        "Missing_Pct": (df.isnull().sum() / len(df) * 100).values,
        "Unique_Values": [df[col].nunique() for col in df.columns]
    })
    print(dtypes_df.to_string(index=False))
    print("\n")

    # 3. Head Sample (First 3 Rows)
    print("--- 3. FIRST 3 ROWS SAMPLE ---")
    print(df.head(3).T)
    print("\n")

    # 4. Duplicate Check
    duplicates = df.duplicated().sum()
    print("--- 4. DUPLICATES ---")
    print(f"Duplicate Rows Count: {duplicates}\n")

    # 5. Timestamp & Sorting Check
    # Common timestamp columns in Kartik2112 dataset: 'trans_date_trans_time' or 'unix_time'
    time_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()]
    print("--- 5. DETECTED TIMESTAMP COLUMNS ---")
    print(f"Candidate Timestamp Columns: {time_cols}")
    for col in time_cols:
        try:
            min_val = df[col].min()
            max_val = df[col].max()
            print(f"  - {col}: Min = {min_val} | Max = {max_val}")
        except Exception as e:
            print(f"  - {col}: Could not aggregate ({e})")
    print("\n")

    # 6. Target Fraud Class Distribution
    target_candidates = [col for col in df.columns if 'fraud' in col.lower() or 'label' in col.lower() or col == 'target']
    print("--- 6. TARGET FRAUD DISTRIBUTION ---")
    print(f"Candidate Target Columns: {target_candidates}")
    for target in target_candidates:
        val_counts = df[target].value_counts()
        val_pcts = df[target].value_counts(normalize=True) * 100
        print(f"\nTarget Column: '{target}'")
        for val in val_counts.index:
            print(f"  Class {val}: {val_counts[val]:,} transactions ({val_pcts[val]:.3f}%)")

        # Imbalance ratio
        if len(val_counts) == 2:
            imbalance_ratio = val_counts.min() / val_counts.max()
            print(f"  Positive Class Imbalance Ratio: 1:{int(1/imbalance_ratio)}")
    print("\n")

    # 7. Numerical Summary
    print("--- 7. NUMERICAL FEATURE SUMMARY ---")
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    print(df[num_cols].describe().T[['mean', 'std', 'min', '50%', 'max']])
    print("\n" + "=" * 60)

    return df

if __name__ == "__main__":
    # Update this path to where your local file sits
    DATASET_PATH = "C:/Users/pmodi/Downloads/archive (2)/fraudTrain.csv"
    run_dataset_audit(DATASET_PATH)