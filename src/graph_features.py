# src/graph_features.py
import os
import pandas as pd
import numpy as np

def compute_leak_free_graph_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes time-aware graph and relational interaction features
    without future data leakage using updated Pandas offset strings.
    """
    print("Sorting transactions chronologically to enforce zero-leakage constraints...")
    df = df.sort_values('unix_time').copy()
    
    # 1. Create Compound Features & Datetime Index
    df['card_merch_pair'] = df['card_id'] + "_" + df['merchant_id']
    df['dt_temp'] = pd.to_datetime(df['unix_time'], unit='s')
    
    # Set Datetime index AFTER compound columns exist
    df_indexed = df.set_index('dt_temp')
    
    # 2. Card Velocity Signals
    print("Extracting card temporal velocity signals (1h, 24h, 7D)...")
    
    card_1h = df_indexed.groupby('card_id')['amt'].transform(
        lambda x: x.rolling('1h', closed='left').count()
    ).fillna(0)
    
    card_24h = df_indexed.groupby('card_id')['amt'].transform(
        lambda x: x.rolling('24h', closed='left').count()
    ).fillna(0)
    
    card_avg_7d = df_indexed.groupby('card_id')['amt'].transform(
        lambda x: x.rolling('7D', closed='left').mean()
    ).fillna(0)
    
    df['card_tx_count_1h'] = card_1h.values
    df['card_tx_count_24h'] = card_24h.values
    df['card_avg_amt_7d'] = card_avg_7d.values
    
    # Amount Ratio compared to card's 7-day average spend
    df['card_amt_ratio_7d'] = np.where(df['card_avg_amt_7d'] > 0, df['amt'] / df['card_avg_amt_7d'], 1.0)
    
    # 3. Card-Merchant Pair Interaction Count
    print("Extracting Card ↔ Merchant entity graph connection strength...")
    pair_cnt_30d = df_indexed.groupby('card_merch_pair')['amt'].transform(
        lambda x: x.rolling('30D', closed='left').count()
    ).fillna(0)
    df['card_merch_pair_cnt'] = pair_cnt_30d.values
    
    # 4. Merchant Multi-Card Spikes (Abuse-Ring Indicator)
    print("Extracting Merchant abuse-ring signals (transaction count in 24h)...")
    merch_tx_24h = df_indexed.groupby('merchant_id')['amt'].transform(
        lambda x: x.rolling('24h', closed='left').count()
    ).fillna(0)
    df['merchant_tx_count_24h'] = merch_tx_24h.values
    
    # Clean up temporary calculation columns
    df = df.drop(columns=['dt_temp', 'card_merch_pair'])
    
    print("Graph feature extraction completed successfully!")
    return df

def generate_graph_datasets(data_dir: str = "outputs"):
    print("=" * 60)
    print("STAGE 6 & 7: GRAPH FEATURE ENGINEERING (RISKGRAPH)")
    print("=" * 60)
    
    train_df = pd.read_parquet(os.path.join(data_dir, "train.parquet"))
    val_df = pd.read_parquet(os.path.join(data_dir, "val.parquet"))
    test_df = pd.read_parquet(os.path.join(data_dir, "test.parquet"))
    
    # Store original row counts for verification
    n_train_orig = len(train_df)
    n_val_orig = len(val_df)
    n_test_orig = len(test_df)
    total_orig = n_train_orig + n_val_orig + n_test_orig
    
    # [FIXED 1]: Assign explicit split identifiers before concatenation
    train_df["_split"] = "train"
    val_df["_split"] = "val"
    test_df["_split"] = "test"
    
    # Combine chronologically for smooth sequence state calculation
    full_df = pd.concat([train_df, val_df, test_df], axis=0).reset_index(drop=True)
    
    # Compute Features
    full_df_enriched = compute_leak_free_graph_features(full_df)
    
    # [FIXED 1]: Restore datasets using explicit _split identifier column (NO iloc)
    train_enriched = full_df_enriched[full_df_enriched["_split"] == "train"].drop(columns=["_split"]).copy()
    val_enriched = full_df_enriched[full_df_enriched["_split"] == "val"].drop(columns=["_split"]).copy()
    test_enriched = full_df_enriched[full_df_enriched["_split"] == "test"].drop(columns=["_split"]).copy()
    
    # [FIXED 1]: Validation Assertions for Split Integrity
    print("\nRunning Split Integrity Validation Checks...")
    assert len(train_enriched) == n_train_orig, f"Train count mismatch: {len(train_enriched)} vs {n_train_orig}"
    assert len(val_enriched) == n_val_orig, f"Val count mismatch: {len(val_enriched)} vs {n_val_orig}"
    assert len(test_enriched) == n_test_orig, f"Test count mismatch: {len(test_enriched)} vs {n_test_orig}"
    assert (len(train_enriched) + len(val_enriched) + len(test_enriched)) == total_orig, "Total row count mismatch!"
    
    # Verify chronological boundary integrity
    assert train_enriched['unix_time'].max() <= val_enriched['unix_time'].min(), "Chronological train/val boundary violated!"
    assert val_enriched['unix_time'].max() <= test_enriched['unix_time'].min(), "Chronological val/test boundary violated!"
    print("✔ All Split Integrity Assertions Passed (Zero row loss, boundary verified)!")
    
    print("\nSaving enriched datasets with Graph features...")
    train_enriched.to_parquet(os.path.join(data_dir, "train_graph.parquet"), index=False)
    val_enriched.to_parquet(os.path.join(data_dir, "val_graph.parquet"), index=False)
    test_enriched.to_parquet(os.path.join(data_dir, "test_graph.parquet"), index=False)
    
    print("Saved train_graph.parquet, val_graph.parquet, test_graph.parquet successfully!\n" + "=" * 60)

if __name__ == "__main__":
    generate_graph_datasets()