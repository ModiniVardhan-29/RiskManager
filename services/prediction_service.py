import os
import json
import pandas as pd
import numpy as np
import shap
from xgboost import XGBClassifier

FEATURES_ORDER = [
    'amt', 'distance_km', 'age', 'city_pop', 'trans_hour', 'trans_dayofweek',
    'lat', 'long', 'merch_lat', 'merch_long', 'card_tx_count_1h',
    'card_tx_count_24h', 'card_avg_amt_7d', 'card_amt_ratio_7d',
    'card_merch_pair_cnt', 'merchant_tx_count_24h', 'category_freq', 'gender_freq'
]

GRAPH_FEATURES = [
    'card_tx_count_1h', 'card_tx_count_24h', 'card_avg_amt_7d',
    'card_amt_ratio_7d', 'card_merch_pair_cnt', 'merchant_tx_count_24h'
]

FEATURE_NAME_MAP = {
    'amt': 'Transaction amount',
    'distance_km': 'Distance from home location',
    'age': 'Account holder age profile',
    'city_pop': 'City population density',
    'trans_hour': 'Time of transaction',
    'trans_dayofweek': 'Day of week spending pattern',
    'card_tx_count_1h': '1-hour card transaction velocity',
    'card_tx_count_24h': '24-hour card transaction frequency',
    'card_avg_amt_7d': '7-day average spend baseline',
    'card_amt_ratio_7d': '7-day spend ratio',
    'card_merch_pair_cnt': 'Card-merchant pairing history',
    'merchant_tx_count_24h': '24-hour merchant transaction volume',
    'category_freq': 'Unusual or low-frequency category',
    'gender_freq': 'Demographic profile frequency',
    'lat': 'Transaction latitude anomaly',
    'long': 'Transaction longitude anomaly',
    'merch_lat': 'Merchant latitude anomaly',
    'merch_long': 'Merchant longitude anomaly'
}

class PredictionService:
    def __init__(self, model_dir="models", data_dir="outputs"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_dir = os.path.join(base_dir, model_dir)
        self.data_dir = os.path.join(base_dir, data_dir)
        
        self.model = None
        self.explainer = None
        self.demo_samples_df = None
        self.demo_samples_dict = {}
        self.category_freq_map = {}
        self.gender_freq_map = {}

        self._load_frequency_encodings()
        self._load_model()
        self._load_demo_samples()

    def _load_frequency_encodings(self):
        train_path = os.path.join(self.data_dir, "train_graph.parquet")
        if os.path.exists(train_path):
            try:
                train_df = pd.read_parquet(train_path)
                if 'category' in train_df.columns:
                    self.category_freq_map = train_df['category'].value_counts(normalize=True).to_dict()
                if 'gender' in train_df.columns:
                    self.gender_freq_map = train_df['gender'].value_counts(normalize=True).to_dict()
            except Exception as e:
                print(f"Warning: Frequency maps load issue: {e}")

    def _load_model(self):
        model_path = os.path.join(self.model_dir, "riskgraph_xgboost.json")
        if not os.path.exists(model_path):
            print(f"Warning: Model file missing at {model_path}")
            self.model = None
            return

        self.model = XGBClassifier()
        self.model.load_model(model_path)
        
        try:
            self.explainer = shap.TreeExplainer(self.model)
        except Exception as e:
            print(f"Warning: Failed to initialize SHAP TreeExplainer: {e}")
            self.explainer = None

    def _load_demo_samples(self):
        test_path = os.path.join(self.data_dir, "test_graph.parquet")
        if not os.path.exists(test_path):
            raise FileNotFoundError(f"Dataset file not found at path: {test_path}")

        df = pd.read_parquet(test_path)
        
        if 'category_freq' not in df.columns and 'category' in df.columns:
            df['category_freq'] = df['category'].map(self.category_freq_map).fillna(0.0)
        elif 'category_freq' not in df.columns:
            df['category_freq'] = 0.0

        if 'gender_freq' not in df.columns and 'gender' in df.columns:
            df['gender_freq'] = df['gender'].map(self.gender_freq_map).fillna(0.0)
        elif 'gender_freq' not in df.columns:
            df['gender_freq'] = 0.0

        if 'trans_num' in df.columns:
            df['sample_id'] = df['trans_num'].astype(str)
        elif 'id' in df.columns:
            df['sample_id'] = df['id'].astype(str)
        else:
            df['sample_id'] = df.index.astype(str)

        for col in FEATURES_ORDER:
            if col not in df.columns:
                df[col] = 0.0

        if 'is_fraud' in df.columns:
            fraud_samples = df[df['is_fraud'] == 1]
            legit_samples = df[df['is_fraud'] == 0]
        else:
            fraud_samples = pd.DataFrame()
            legit_samples = df

        n_fraud = min(15, len(fraud_samples))
        n_legit = min(30 - n_fraud, len(legit_samples))

        sampled_fraud = fraud_samples.sample(n=n_fraud, random_state=42) if n_fraud > 0 else pd.DataFrame()
        sampled_legit = legit_samples.sample(n=n_legit, random_state=42) if n_legit > 0 else pd.DataFrame()
        
        if not sampled_fraud.empty or not sampled_legit.empty:
            combined_df = pd.concat([sampled_fraud, sampled_legit]).sample(frac=1.0, random_state=42).reset_index(drop=True)
        else:
            combined_df = df.head(30).reset_index(drop=True)

        self.demo_samples_df = combined_df
        for _, row in combined_df.iterrows():
            self.demo_samples_dict[str(row['sample_id'])] = row.to_dict()

    def get_sample_options(self):
        options = []
        for _, row in self.demo_samples_df.iterrows():
            category = str(row.get('category', 'N/A')).replace('_', ' ').title()
            amt = float(row.get('amt', 0.0))
            trans_time = str(row.get('trans_date_trans_time', f"Hour {row.get('trans_hour', 'N/A')}"))
            sample_id = str(row['sample_id'])
            
            label_str = ""
            if 'is_fraud' in row and pd.notna(row['is_fraud']):
                label_str = " | [FRAUD SAMPLE]" if int(row['is_fraud']) == 1 else " | [LEGITIMATE]"

            display_text = f"Tx #{sample_id[:8]} | ${amt:.2f} | {category} | {trans_time}{label_str}"
            
            options.append({
                "sample_id": sample_id,
                "display_text": display_text
            })
        return options

    def predict_sample(self, sample_id, block_threshold=0.85, review_threshold=0.50):
        if self.model is None:
            raise RuntimeError("Model is not loaded properly. Unable to perform prediction.")

        if str(sample_id) not in self.demo_samples_dict:
            raise KeyError(f"Sample ID '{sample_id}' not found in demo registry.")

        row_dict = self.demo_samples_dict[str(sample_id)]

        for f in FEATURES_ORDER:
            if f not in row_dict or pd.isna(row_dict[f]):
                row_dict[f] = 0.0

        input_data = {f: [float(row_dict[f])] for f in FEATURES_ORDER}
        input_df = pd.DataFrame(input_data)[FEATURES_ORDER]

        raw_prob = float(self.model.predict_proba(input_df)[0][1])

        if raw_prob >= block_threshold:
            decision = "BLOCK"
        elif raw_prob >= review_threshold:
            decision = "REVIEW"
        else:
            decision = "ALLOW"

        pos_contribs = []
        neg_contribs = []

        if self.explainer is not None:
            try:
                shap_matrix = self.explainer.shap_values(input_df)
                if isinstance(shap_matrix, list):
                    shap_vals = shap_matrix[1][0]
                elif len(shap_matrix.shape) == 2:
                    shap_vals = shap_matrix[0]
                else:
                    shap_vals = shap_matrix

                for idx, feat_name in enumerate(FEATURES_ORDER):
                    val = float(shap_vals[idx])
                    desc = FEATURE_NAME_MAP.get(feat_name, feat_name.replace('_', ' ').title())
                    
                    item = {
                        "feature": feat_name,
                        "description": desc,
                        "impact_score": round(val, 4),
                        "display_text": f"+{val:.3f}" if val > 0 else f"{val:.3f}"
                    }

                    if val > 0.0001:
                        pos_contribs.append(item)
                    elif val < -0.0001:
                        neg_contribs.append(item)

                pos_contribs.sort(key=lambda x: x["impact_score"], reverse=True)
                neg_contribs.sort(key=lambda x: x["impact_score"])
            except Exception as e:
                print(f"SHAP calculation failed: {e}")

        if decision in ["BLOCK", "REVIEW"]:
            shap_heading = "Top Fraud Risk Drivers"
            shap_subtitle = "Key features that contributed most toward increasing predicted fraud risk."
            primary_shap_list = pos_contribs[:5]
        else:
            shap_heading = "Top Factors Considered"
            shap_subtitle = "Key transaction characteristics evaluated by the model during scoring."
            primary_shap_list = sorted(pos_contribs + neg_contribs, key=lambda x: abs(x["impact_score"]), reverse=True)[:5]

        top_driver_names = [f["description"].lower() for f in primary_shap_list[:2]]
        driver_text = ", ".join(top_driver_names) if top_driver_names else "behavioral parameters"
        
        if decision == "BLOCK":
            risk_summary = f"Elevated fraud risk driven primarily by {driver_text}. Transaction velocity and relationship signals deviate significantly from normal cardholder patterns."
        elif decision == "REVIEW":
            risk_summary = f"Moderate risk detected due to variations in {driver_text}. Manual verification is recommended before settlement."
        else:
            risk_summary = f"Transaction risk profile remains minimal. Spending patterns align with established cardholder history and low-risk merchant interaction indicators."

        actual_label = None
        if 'is_fraud' in row_dict and not pd.isna(row_dict['is_fraud']):
            actual_label = "Fraud" if int(row_dict['is_fraud']) == 1 else "Legitimate"

        if actual_label is not None:
            if decision == "BLOCK" and actual_label == "Fraud":
                eval_text = "✓ Correctly Identified Fraud"
                eval_status = "match"
            elif decision == "ALLOW" and actual_label == "Legitimate":
                eval_text = "✓ Correctly Identified Legitimate Transaction"
                eval_status = "match"
            else:
                eval_text = "⚠ Prediction Does Not Match Dataset Label"
                eval_status = "mismatch"
        else:
            eval_text = "N/A (Unlabeled Transaction)"
            eval_status = "neutral"

        graph_summary = {
            "card_history": {
                "tx_count_1h": int(row_dict.get('card_tx_count_1h', 0)),
                "tx_count_24h": int(row_dict.get('card_tx_count_24h', 0)),
                "avg_amt_7d": round(float(row_dict.get('card_avg_amt_7d', 0.0)), 2),
                "amt_ratio_7d": round(float(row_dict.get('card_amt_ratio_7d', 0.0)), 2)
            },
            "relationship_signals": {
                "card_merch_pair_cnt": int(row_dict.get('card_merch_pair_cnt', 0)),
                "merchant_tx_count_24h": int(row_dict.get('merchant_tx_count_24h', 0))
            }
        }

        return {
            "sample_id": sample_id,
            "raw_probability": raw_prob,
            "fraud_probability": raw_prob,
            "risk_percentage": float(raw_prob * 100.0),
            "decision": decision,
            "actual_label": actual_label,
            "eval_text": eval_text,
            "eval_status": eval_status,
            "shap_heading": shap_heading,
            "shap_subtitle": shap_subtitle,
            "risk_summary": risk_summary,
            "threshold_used": block_threshold,
            "review_threshold_used": review_threshold,
            "transaction_details": {
                "amount": round(float(row_dict.get('amt', 0.0)), 2),
                "category": str(row_dict.get('category', 'N/A')).replace('_', ' ').title(),
                "trans_hour": int(row_dict.get('trans_hour', 0)),
                "distance_km": round(float(row_dict.get('distance_km', 0.0)), 2),
                "age": int(row_dict.get('age', 0)),
                "city_pop": int(row_dict.get('city_pop', 0))
            },
            "risk_reasons": primary_shap_list,
            "mitigating_factors": neg_contribs[:3],
            "graph_summary": graph_summary
        }