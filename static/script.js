import os
import pandas as pd
import numpy as np
import xgboost as xgb
import shap

class PredictionService:
    def __init__(self):
        # 1. Strictly enforced XGBoost feature order
        self.features_order = [
            'amt',
            'distance_km',
            'age',
            'city_pop',
            'trans_hour',
            'trans_dayofweek',
            'lat',
            'long',
            'merch_lat',
            'merch_long',
            'card_tx_count_1h',
            'card_tx_count_24h',
            'card_avg_amt_7d',
            'card_amt_ratio_7d',
            'card_merch_pair_cnt',
            'merchant_tx_count_24h',
            'category_freq',
            'gender_freq'
        ]

        # 2. Project Paths
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(base_dir, "models", "riskgraph_xgboost.json")
        self.train_path = os.path.join(base_dir, "outputs", "train_graph.parquet")
        self.test_path = os.path.join(base_dir, "outputs", "test_graph.parquet")

        # 3. Load Parquet Data
        if not os.path.exists(self.test_path):
            raise FileNotFoundError(f"Missing required data file: {self.test_path}")

        try:
            self.test_df = pd.read_parquet(self.test_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read parquet file ({self.test_path}). Ensure pyarrow or fastparquet is installed: {e}")

        # Ensure sample_id identifier column exists
        if 'trans_num' in self.test_df.columns:
            self.test_df['sample_id'] = self.test_df['trans_num'].astype(str)
        elif 'id' in self.test_df.columns:
            self.test_df['sample_id'] = self.test_df['id'].astype(str)
        else:
            self.test_df['sample_id'] = self.test_df.index.astype(str)

        # 4. Compute Category & Gender Frequencies safely
        self.category_freq_map = {}
        self.gender_freq_map = {}

        if os.path.exists(self.train_path):
            try:
                train_df = pd.read_parquet(self.train_path)
                if 'category' in train_df.columns:
                    self.category_freq_map = train_df['category'].value_counts(normalize=True).to_dict()
                if 'gender' in train_df.columns:
                    self.gender_freq_map = train_df['gender'].value_counts(normalize=True).to_dict()
            except Exception as e:
                print(f"⚠️ Warning loading train_graph.parquet for frequencies: {e}")

        if not self.category_freq_map and 'category' in self.test_df.columns:
            self.category_freq_map = self.test_df['category'].value_counts(normalize=True).to_dict()

        if not self.gender_freq_map and 'gender' in self.test_df.columns:
            self.gender_freq_map = self.test_df['gender'].value_counts(normalize=True).to_dict()

        # Add missing frequencies to test_df if absent
        if 'category_freq' not in self.test_df.columns and 'category' in self.test_df.columns:
            self.test_df['category_freq'] = self.test_df['category'].map(self.category_freq_map).fillna(0.0)
        elif 'category_freq' not in self.test_df.columns:
            self.test_df['category_freq'] = 0.0

        if 'gender_freq' not in self.test_df.columns and 'gender' in self.test_df.columns:
            self.test_df['gender_freq'] = self.test_df['gender'].map(self.gender_freq_map).fillna(0.0)
        elif 'gender_freq' not in self.test_df.columns:
            self.test_df['gender_freq'] = 0.0

        # Fill missing features in expected model features with 0.0 safety defaults
        for col in self.features_order:
            if col not in self.test_df.columns:
                self.test_df[col] = 0.0

        # 5. Load Trained Model
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file missing: {self.model_path}")

        self.model = xgb.XGBClassifier()
        self.model.load_model(self.model_path)

        # 6. Initialize SHAP Explainer
        self.explainer = shap.TreeExplainer(self.model)

        self.feature_labels = {
            "amt": "Transaction amount",
            "distance_km": "Distance from home location",
            "trans_hour": "Time of transaction",
            "trans_dayofweek": "Day of week spending pattern",
            "card_tx_count_1h": "1-hour card transaction velocity",
            "card_tx_count_24h": "24-hour card transaction frequency",
            "card_avg_amt_7d": "7-day average spend baseline",
            "card_amt_ratio_7d": "7-day spend ratio",
            "card_merch_pair_cnt": "Previous card-merchant relationship frequency",
            "merchant_tx_count_24h": "Merchant transaction frequency (24h)",
            "category_freq": "Unusual or low-frequency category",
            "gender_freq": "Demographic spending baseline",
            "city_pop": "City population density"
        }

    def get_sample_options(self):
        samples = []
        subset = self.test_df.head(30)
        for _, row in subset.iterrows():
            sid = str(row['sample_id'])
            short_id = sid[:8] if len(sid) >= 8 else sid
            amt = float(row.get('amt', 0.0))
            
            raw_cat = str(row.get('category', 'General'))
            cat = raw_cat.replace('_', ' ').title()
            
            time_str = "00:00:00"
            if 'trans_date_trans_time' in row and pd.notna(row['trans_date_trans_time']):
                time_str = str(row['trans_date_trans_time'])
            elif 'trans_hour' in row:
                time_str = f"{int(row['trans_hour']):02d}:00:00"

            is_fraud = int(row.get('is_fraud', 0))
            label_str = "FRAUD" if is_fraud == 1 else "LEGITIMATE"
            
            display_text = f"Tx #{short_id} | ${amt:.2f} | {cat} | {time_str} | [{label_str}]"
            samples.append({'sample_id': sid, 'display_text': display_text})
        return samples

    def predict_sample(self, sample_id, block_threshold=0.85, review_threshold=0.50):
        row_matches = self.test_df[self.test_df['sample_id'] == str(sample_id)]
        
        if row_matches.empty:
            try:
                row_matches = self.test_df.iloc[[int(sample_id)]]
            except (ValueError, IndexError):
                raise KeyError(f"Sample ID '{sample_id}' not found in dataset.")

        row = row_matches.iloc[0]
        X_sample = pd.DataFrame([row[self.features_order]], columns=self.features_order)

        prob_matrix = self.model.predict_proba(X_sample)
        fraud_prob = float(prob_matrix[0][1])

        if fraud_prob >= block_threshold:
            action = "BLOCK"
        elif fraud_prob >= review_threshold:
            action = "REVIEW"
        else:
            action = "ALLOW"

        is_fraud = int(row.get('is_fraud', 0))
        actual_label = "Fraud" if is_fraud == 1 else "Legitimate"

        # SHAP calculation
        shap_values = self.explainer.shap_values(X_sample)
        if isinstance(shap_values, list):
            vals = shap_values[1][0]
        elif len(shap_values.shape) == 2:
            vals = shap_values[0]
        else:
            vals = shap_values[0]

        risk_reasons = []
        shap_tuples = sorted(
            zip(self.features_order, vals),
            key=lambda x: abs(x[1]),
            reverse=True
        )

        for feat, val in shap_tuples[:4]:
            label = self.feature_labels.get(feat, feat)
            risk_reasons.append({
                "description": label,
                "impact_score": float(val)
            })

        return {
            "fraud_probability": fraud_prob,
            "risk_percentage": fraud_prob * 100.0,
            "decision": action,
            "actual_label": actual_label,
            "transaction_details": {
                "amount": float(row.get('amt', 0.0)),
                "category": str(row.get('category', 'N/A')).replace('_', ' ').title(),
                "trans_hour": int(row.get('trans_hour', 0)),
                "distance_km": float(row.get('distance_km', 0.0))
            },
            "risk_reasons": risk_reasons,
            "graph_summary": {
                "card_history": {
                    "tx_count_1h": int(row.get('card_tx_count_1h', 0)),
                    "tx_count_24h": int(row.get('card_tx_count_24h', 0)),
                    "avg_amt_7d": float(row.get('card_avg_amt_7d', 0.0)),
                    "amt_ratio_7d": float(row.get('card_amt_ratio_7d', 0.0))
                },
                "relationship_signals": {
                    "card_merch_pair_cnt": int(row.get('card_merch_pair_cnt', 0)),
                    "merchant_tx_count_24h": int(row.get('merchant_tx_count_24h', 0))
                }
            }
        }