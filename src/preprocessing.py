# src/preprocessing.py
import os
import numpy as np
import pandas as pd

def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in kilometers.
    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km

def preprocess_and_split(df_path: str, output_dir: str = "outputs"):
    """
    Cleans, anonymizes, engineer temporal features, and creates 
    time-based train/val/test splits to eliminate data leakage.
    """
    print("=" * 60)
    print("STAGE 2 & 3: PREPROCESSING & TIME-BASED SPLITTING")
    print("=" * 60)
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Reading dataset from {df_path}...")
    df = pd.read_csv(df_path)
    
    # Drop unneeded index column if present
    if 'Unnamed: 0' in df.columns:
        df = df.drop(columns=['Unnamed: 0'])

    # 1. Parse Timestamps & Sort Chronologically
    print("Parsing timestamps and sorting chronologically...")
    df['trans_date_trans_time'] = pd.to_datetime(df['trans_date_trans_time'])
    df = df.sort_values('unix_time').reset_index(drop=True)
    
    # 2. Strict Privacy Anonymization
    print("Applying privacy anonymization (masking card numbers & merchant names)...")
    unique_cc = {val: f"CARD_{i:04d}" for i, val in enumerate(df['cc_num'].unique())}
    unique_merch = {val: f"MERCH_{i:04d}" for i, val in enumerate(df['merchant'].unique())}
    
    df['card_id'] = df['cc_num'].map(unique_cc)
    df['merchant_id'] = df['merchant'].map(unique_merch)
    
    # 3. Base Feature Engineering
    print("Computing distance and temporal features...")
    df['distance_km'] = haversine_np(df['long'], df['lat'], df['merch_long'], df['merch_lat'])
    
    # Calculate Customer Age at transaction time
    df['dob'] = pd.to_datetime(df['dob'])
    df['age'] = (df['trans_date_trans_time'] - df['dob']).dt.days // 365
    
    # Time Features
    df['trans_hour'] = df['trans_date_trans_time'].dt.hour
    df['trans_dayofweek'] = df['trans_date_trans_time'].dt.dayofweek
    
    # 4. Perform Time-Based Train / Val / Test Split (70% / 15% / 15%)
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()
    
    print("\n--- TIME SPLIT SUMMARY ---")
    print(f"Train Set:      {len(train_df):,} rows | Range: {train_df['trans_date_trans_time'].min()} -> {train_df['trans_date_trans_time'].max()} | Fraud: {train_df['is_fraud'].sum():,} ({train_df['is_fraud'].mean()*100:.3f}%)")
    print(f"Validation Set: {len(val_df):,} rows | Range: {val_df['trans_date_trans_time'].min()} -> {val_df['trans_date_trans_time'].max()} | Fraud: {val_df['is_fraud'].sum():,} ({val_df['is_fraud'].mean()*100:.3f}%)")
    print(f"Held-out Test:  {len(test_df):,} rows | Range: {test_df['trans_date_trans_time'].min()} -> {test_df['trans_date_trans_time'].max()} | Fraud: {test_df['is_fraud'].sum():,} ({test_df['is_fraud'].mean()*100:.3f}%)")
    
    # Save processed splits
    print(f"\nSaving split datasets to '{output_dir}/'...")
    train_df.to_parquet(os.path.join(output_dir, "train.parquet"), index=False)
    val_df.to_parquet(os.path.join(output_dir, "val.parquet"), index=False)
    test_df.to_parquet(os.path.join(output_dir, "test.parquet"), index=False)
    
    print("Preprocessing & Splitting Complete!\n" + "=" * 60)
    return train_df, val_df, test_df

if __name__ == "__main__":
    DATASET_PATH = "C:/Users/pmodi/Downloads/archive (2)/fraudTrain.csv"
    preprocess_and_split(DATASET_PATH)