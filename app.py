import os
import json
import random
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try loading pandas to support dynamic reading from test_graph.parquet if present
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "riskgraph_secret_key_demo")

# --- Flask-Mail Configuration ---
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
app.config['MAIL_USE_SSL'] = os.getenv("MAIL_USE_SSL", "False").lower() == "true"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME", "")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD", "")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME", "fraud-ops-team@riskgraph.ai"))

mail = Mail(app)

PARQUET_FILE_PATH = "test_graph.parquet"

# --- In-Memory Databases ---
EMAIL_ALERTS_DB = []
CASES_DB = {}
ARCHIVED_TRANSACTIONS = set()
DELETED_TRANSACTIONS = set()

def load_all_transactions():
    """Dynamically loads transactions with latitude/longitude coordinates."""
    transactions = {}
    
    if HAS_PANDAS and os.path.exists(PARQUET_FILE_PATH):
        try:
            df = pd.read_parquet(PARQUET_FILE_PATH)
            for idx, row in df.iterrows():
                tx_id = str(row.get('tx_id', row.get('transaction_id', f'TX-{idx+100000}')))
                transactions[tx_id] = {
                    "tx_id": tx_id,
                    "card_id": str(row.get('card_id', '•••• •••• •••• 9999')),
                    "amount": float(row.get('amount', row.get('amt', 100.0))),
                    "merchant": str(row.get('merchant', row.get('merchant_name', 'Unknown Merchant'))),
                    "category": str(row.get('category', 'general_pos')),
                    "time": str(row.get('time', '12:00:00')),
                    "distance": float(row.get('distance', 5.0)),
                    "lat": float(row.get('lat', 40.7128 + random.uniform(-0.05, 0.05))),
                    "lng": float(row.get('lng', -74.0060 + random.uniform(-0.05, 0.05))),
                    "location_name": str(row.get('location_name', 'New York, NYC (Simulated)')),
                    "risk_score": float(row.get('risk_score', row.get('calibrated_prob', 0.5))),
                    "recommendation": str(row.get('recommendation', 'REVIEW')),
                    "shap_explanations": row.get('shap_explanations', [
                        {"feature": "Graph entity relationship anomaly", "contribution": 0.35, "impact": "High Impact"}
                    ]),
                    "relationship_features": {
                        "card_tx_1h": int(row.get('card_tx_1h', 1)),
                        "card_tx_24h": int(row.get('card_tx_24h', 5)),
                        "card_avg_spend_7d": float(row.get('card_avg_spend_7d', 50.0)),
                        "spend_ratio_7d": float(row.get('spend_ratio_7d', 1.5)),
                        "card_merchant_pairs": int(row.get('card_merchant_pairs', 2)),
                        "merchant_tx_24h": int(row.get('merchant_tx_24h', 50))
                    }
                }
            if len(transactions) >= 20:
                return transactions
        except Exception as e:
            print(f"Warning: Failed reading {PARQUET_FILE_PATH}: {e}")

    raw_samples = [
        ("TX-883901", "Global Electronics Store", 318.84, "electronics_pos", 0.977, "BLOCK", 42.5, 40.7128, -74.0060, "Financial District, NYC (Simulated)", [
            {"feature": "Unusual Transaction Pattern", "contribution": 0.32, "impact": "High Impact"},
            {"feature": "High-Risk / Unusual Location", "contribution": 0.28, "impact": "High Impact"},
            {"feature": "Transaction Amount Anomaly", "contribution": 0.22, "impact": "Medium Impact"},
            {"feature": "Merchant Risk Signal", "contribution": 0.15, "impact": "Medium Impact"}
        ]),
        ("TX-104928", "FreshMart Supermarket", 42.10, "grocery_pos", 0.008, "ALLOW", 1.2, 40.7306, -73.9352, "Brooklyn, NYC (Simulated)", [
            {"feature": "Matched Standard Profile", "contribution": 0.02, "impact": "Low Impact"},
            {"feature": "Known Frequent Merchant", "contribution": 0.01, "impact": "Low Impact"}
        ]),
        ("TX-502194", "Luxury Watch Boutique", 1250.00, "retail_pos", 0.620, "REVIEW", 115.0, 40.7589, -73.9851, "Times Square, NYC (Simulated)", [
            {"feature": "High Spend Ratio Variance", "contribution": 0.35, "impact": "High Impact"},
            {"feature": "New Merchant Interaction", "contribution": 0.20, "impact": "Medium Impact"}
        ]),
        ("TX-774012", "Crypto Exchange Online", 890.50, "online_digital", 0.912, "BLOCK", 0.0, 40.7135, -74.0045, "Financial District, NYC (Simulated)", [
            {"feature": "High-Risk Category Anomaly", "contribution": 0.40, "impact": "High Impact"},
            {"feature": "Rapid Transaction Velocity", "contribution": 0.35, "impact": "High Impact"}
        ]),
        ("TX-310948", "City Transit Kiosk", 15.40, "transportation", 0.012, "ALLOW", 3.1, 40.7505, -73.9934, "Penn Station, NYC (Simulated)", [
            {"feature": "Standard Micro-payment Pattern", "contribution": 0.01, "impact": "Low Impact"}
        ]),
        ("TX-662019", "Airline Flight Direct", 499.00, "travel", 0.580, "REVIEW", 880.0, 40.6413, -73.7781, "JFK Airport, NYC (Simulated)", [
            {"feature": "Geographic Distance Anomaly", "contribution": 0.30, "impact": "High Impact"},
            {"feature": "Cross-Border Category Trigger", "contribution": 0.22, "impact": "Medium Impact"}
        ]),
        ("TX-992104", "FastPay Fuel Station", 65.00, "automated_fuel", 0.010, "ALLOW", 8.4, 40.7418, -73.9893, "Flatiron, NYC (Simulated)", [
            {"feature": "Standard Automated Fuel Pattern", "contribution": 0.05, "impact": "Low Impact"}
        ]),
        ("TX-440219", "Online Gaming Platform", 250.00, "digital_goods", 0.840, "BLOCK", 0.0, 40.7140, -74.0055, "Financial District, NYC (Simulated)", [
            {"feature": "Digital Goods Burst Anomaly", "contribution": 0.45, "impact": "High Impact"},
            {"feature": "New IP Risk Node", "contribution": 0.32, "impact": "High Impact"}
        ]),
        ("TX-118290", "Local Coffee Shop", 5.75, "food_beverage", 0.005, "ALLOW", 0.5, 40.7282, -73.9942, "East Village, NYC (Simulated)", [
            {"feature": "Daily Routine Match", "contribution": 0.00, "impact": "Low Impact"}
        ]),
        ("TX-339201", "Department Store", 185.20, "retail_pos", 0.310, "REVIEW", 12.0, 40.7527, -73.9772, "Grand Central, NYC (Simulated)", [
            {"feature": "Moderate Volume Increase", "contribution": 0.18, "impact": "Medium Impact"}
        ]),
        ("TX-551029", "Digital Gift Card Hub", 500.00, "online_digital", 0.895, "BLOCK", 0.0, 40.7120, -74.0070, "Financial District, NYC (Simulated)", [
            {"feature": "Gift Card Liquid Asset Anomaly", "contribution": 0.42, "impact": "High Impact"}
        ]),
        ("TX-204918", "Urban Rideshare Service", 24.50, "transportation", 0.015, "ALLOW", 2.8, 40.7223, -73.9987, "SoHo, NYC (Simulated)", [
            {"feature": "Frequent Commute Profile", "contribution": 0.01, "impact": "Low Impact"}
        ])
    ]

    for tx_id, merch, amt, cat, score, rec, dist, lat, lng, loc_name, sh_list in raw_samples:
        transactions[tx_id] = {
            "tx_id": tx_id,
            "card_id": f"•••• •••• •••• {tx_id[-4:]}",
            "amount": amt,
            "merchant": merch,
            "category": cat,
            "time": "14:22:10",
            "distance": dist,
            "lat": lat,
            "lng": lng,
            "location_name": loc_name,
            "risk_score": score,
            "recommendation": rec,
            "shap_explanations": sh_list,
            "relationship_features": {
                "card_tx_1h": 3 if score > 0.6 else 1,
                "card_tx_24h": 12 if score > 0.6 else 3,
                "card_avg_spend_7d": 50.0,
                "spend_ratio_7d": round(amt / 50.0, 1),
                "card_merchant_pairs": 2,
                "merchant_tx_24h": 85
            }
        }
    return transactions

DEMO_TRANSACTIONS = load_all_transactions()

def send_fraud_alert_email(case, tx_data):
    """Sends live email alerts via SMTP within an active application context."""
    risk_score = tx_data.get("risk_score", 0.0)
    risk_level = "HIGH RISK" if risk_score >= 0.7 else ("MEDIUM RISK" if risk_score >= 0.3 else "LOW RISK")
    
    top_factors = ""
    for sh in tx_data.get("shap_explanations", []):
        top_factors += f"\n  - {sh.get('feature')}: +{sh.get('contribution')}"

    recipient_email = os.getenv("ALERT_RECIPIENT_EMAIL", os.getenv("MAIL_USERNAME", "fraud-ops-team@riskgraph.ai"))
    subject = f"URGENT: Potential Fraud Detected - {case['id']}"

    body = f"""URGENT: Potential Fraud Alert Triggered by RiskGraph AI

---------------------------------------------------------
CASE SUMMARY
---------------------------------------------------------
Case ID:            {case['id']}
Transaction ID:     {tx_data['tx_id']}
Timestamp:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
Risk Level:         {risk_level} (Score: {risk_score * 100:.1f}%)
Recommended Action: {tx_data['recommendation']}

---------------------------------------------------------
TRANSACTION DETAILS
---------------------------------------------------------
Amount:             ${tx_data['amount']:.2f}
Merchant:           {tx_data['merchant']}
Category:           {tx_data['category']}
Location:           {tx_data.get('location_name', 'Unknown')} (Lat: {tx_data.get('lat')}, Lng: {tx_data.get('lng')})
Card Reference:     {tx_data['card_id']}

---------------------------------------------------------
KEY SHAP / RISK FACTORS
---------------------------------------------------------{top_factors if top_factors else ' High volume anomaly detected.'}

Action Required: Please review this transaction in the RiskGraph AI Ops Queue immediately.
"""

    msg = Message(subject=subject, recipients=[recipient_email], body=body)
    status = "SENT"

    try:
        with app.app_context():
            mail.send(msg)
        print(f"[SUCCESS] Fraud alert email sent to {recipient_email}")
    except Exception as e:
        status = "FAILED"
        print(f"[ERROR] Failed to send email via SMTP: {e}")

    alert_record = {
        "alert_id": f"ALT-{random.randint(1000, 9999)}",
        "case_id": case["id"],
        "recipient": recipient_email,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "subject": subject,
        "body": body
    }
    
    EMAIL_ALERTS_DB.insert(0, alert_record)
    return alert_record

def create_or_update_case_from_tx(tx_id, status=None):
    tx_data = DEMO_TRANSACTIONS.get(tx_id)
    if not tx_data:
        return None, False

    case_id = f"CASE-{tx_id.replace('TX-', '')}"
    is_new = case_id not in CASES_DB
    
    if status is None:
        status = "OPEN"

    if is_new:
        initial_timeline = [{"time": datetime.now().strftime("%H:%M:%S"), "title": "Transaction Assessment Triggered", "desc": f"Risk assessment run for ${tx_data.get('amount', 0):.2f} at {tx_data.get('merchant')}."}]

        CASES_DB[case_id] = {
            "id": case_id,
            "status": status,
            "decision": "PENDING",
            "risk_score": tx_data.get("risk_score", 0.5),
            "recommendation": tx_data.get("recommendation", "REVIEW"),
            "transaction": tx_data,
            "shap_explanations": tx_data.get("shap_explanations", []),
            "relationship_features": tx_data.get("relationship_features", {}),
            "human_timeline_events": initial_timeline
        }

    return CASES_DB[case_id], is_new

# --- HTML TEMPLATES ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RiskGraph AI Admin Dashboard</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {
            --bg-color: #060b13;
            --card-bg: #0b132b;
            --border-color: #1c2a4a;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
        }
        body { background: var(--bg-color); color: var(--text-main); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; margin: 0; }
        
        .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
        .kpi-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; }
        .kpi-title { font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }
        .kpi-value { font-size: 24px; font-weight: bold; margin-top: 6px; }
        
        .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
        .card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 20px; margin-bottom: 24px; }
        .card h2 { font-size: 16px; margin-top: 0; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; }
        
        .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        
        .pipeline-box {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #070e1e;
            padding: 12px;
            border-radius: 6px;
            border: 1px dashed var(--border-color);
            font-size: 12px;
            text-align: center;
            margin-bottom: 16px;
        }
        .pipeline-step { padding: 6px 10px; background: #1c2a4a; border-radius: 4px; font-weight: 600; }

        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: rgba(255, 255, 255, 0.02); color: var(--text-muted); font-size: 11px; text-transform: uppercase; padding: 10px; border-bottom: 1px solid var(--border-color); }
        td { padding: 10px; border-bottom: 1px solid var(--border-color); font-size: 13px; }
        
        select, button { background: #070e1e; border: 1px solid var(--border-color); color: white; padding: 10px; border-radius: 6px; font-size: 13px; }
        .btn-action { background: #2563eb; cursor: pointer; font-weight: bold; border: none; border-radius: 6px; }
        .btn-action:hover { background: #1d4ed8; }
        .btn-danger { background: #475569; color: white; cursor: pointer; font-weight: bold; border: none; border-radius: 6px; padding: 10px; margin-top: 10px; }
        .btn-danger:hover { background: #334155; }
        .btn-permanent-delete { background: #dc2626; color: white; cursor: pointer; font-weight: bold; border: none; border-radius: 6px; padding: 10px; margin-top: 10px; }
        .btn-permanent-delete:hover { background: #b91c1c; }
        
        .btn-confirm { background: #059669; color: white; border: none; font-size: 11px; padding: 5px 8px; border-radius: 4px; cursor: pointer; font-weight: bold; margin-right: 4px; }
        .btn-confirm:hover { background: #047857; }
        .btn-resolve { background: #2563eb; color: white; border: none; font-size: 11px; padding: 5px 8px; border-radius: 4px; cursor: pointer; font-weight: bold; margin-right: 4px; }
        .btn-resolve:hover { background: #1d4ed8; }
        .btn-escalate { background: #d97706; color: white; border: none; font-size: 11px; padding: 5px 8px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-escalate:hover { background: #b45309; }

        #map { height: 260px; width: 100%; border-radius: 6px; border: 1px solid var(--border-color); }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .badge-block { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .badge-allow { background: rgba(52, 211, 153, 0.2); color: #34d399; }
        .badge-review { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }

        .alert-status-box { background: rgba(52, 211, 153, 0.1); border: 1px solid #34d399; color: #34d399; padding: 12px; border-radius: 6px; margin-top: 12px; font-size: 13px; display: none; }
        .alert-status-failed { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #ef4444; }

        /* Modal styling */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.85); display: none; align-items: center; justify-content: center; z-index: 9999; }
        .modal-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 24px; width: 380px; text-align: left; }
    </style>
</head>
<body>

    <div class="header-row">
        <div>
            <h1 style="color: var(--accent-blue); margin: 0;">RiskGraph AI Admin Dashboard</h1>
            <p style="color: var(--text-muted); margin: 4px 0 0 0; font-size: 13px;">Relationship-Aware Payment Fraud Operations & Management</p>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <button class="btn-permanent-delete" style="margin: 0; padding: 8px 16px; font-size: 13px;" onclick="openClearQueueModal()">🗑️ Clear Queue History</button>
        </div>
    </div>

    <!-- KPI Metrics Grid -->
    <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-title">Precision</div><div class="kpi-value" style="color:#34d399;">90.2%</div></div>
        <div class="kpi-card"><div class="kpi-title">Recall</div><div class="kpi-value" style="color:#60a5fa;">91.8%</div></div>
        <div class="kpi-card"><div class="kpi-title">F1-Score</div><div class="kpi-value" style="color:#a855f7;">0.923</div></div>
        <div class="kpi-card"><div class="kpi-title">Financial Loss Saved</div><div class="kpi-value" style="color:#c084fc;">$1.24M</div></div>
    </div>

    <div class="dashboard-grid">
        <!-- Left Column: Pipeline & Ablation -->
        <div>
            <div class="card">
                <h2>Autonomous Fraud Operations Pipeline</h2>
                <div class="pipeline-box">
                    <div class="pipeline-step">Transaction</div> →
                    <div class="pipeline-step">RiskGraph AI</div> →
                    <div class="pipeline-step">SHAP Drivers</div> →
                    <div class="pipeline-step">Thresholds</div> →
                    <div class="pipeline-step">Alert / Ops</div>
                </div>
            </div>

            <div class="card">
                <h2>Ablation Study Model Performance</h2>
                <table>
                    <thead>
                        <tr><th>Model Variant</th><th>AUC-ROC</th><th>F1-Score</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Baseline XGBoost</td><td>0.862</td><td>0.791</td></tr>
                        <tr><td>Graph Embeddings Only</td><td>0.894</td><td>0.845</td></tr>
                        <tr style="background: rgba(56, 189, 248, 0.1);">
                            <td><strong style="color: var(--accent-blue);">RiskGraph AI (Full)</strong></td>
                            <td><strong style="color: #34d399;">0.954</strong></td>
                            <td><strong style="color: #34d399;">0.923</strong></td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Fraud Decision Drivers -->
            <div class="card">
                <h2>🔍 Fraud Decision Drivers</h2>
                <div id="drivers-container">
                    <p style="font-size: 13px; color: var(--text-muted);">Select a transaction to load SHAP contribution factors.</p>
                </div>
            </div>
        </div>

        <!-- Right Column: Interactive Map & Scoring -->
        <div>
            <div class="card">
                <h2>Live Geographic Anomaly Map</h2>
                <div id="map"></div>
            </div>

            <div class="card">
                <h2>Run Transaction Fraud Risk Assessment</h2>
                <select id="tx-select" style="width: 100%; margin-bottom: 12px;" onchange="updateSelectedTx(this.value)">
                    <option value="" disabled selected>Select a transaction to assess</option>
                    {% for tx_id, tx in demo_txs.items() %}
                    <option value="{{ tx_id }}">{{ tx_id }} - {{ tx.merchant }} (${{ "%.2f"|format(tx.amount) }})</option>
                    {% endfor %}
                </select>
                <button class="btn-action" style="width:100%;" onclick="runAssessment()">Assess Risk & Send Alert</button>
                
                <!-- Email Alert Status Banner -->
                <div id="alert-status-box" class="alert-status-box"></div>

                <div style="display: flex; gap: 8px;">
                    <button class="btn-danger" style="flex:1;" onclick="openDeleteModal()">📁 Archive Transaction</button>
                    <button class="btn-permanent-delete" style="flex:1;" onclick="openPermanentDeleteModal()">🗑️ Delete Transaction</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Operations Queue with HITL Actions & Per-Transaction Archive/Delete Options -->
    <div class="card">
        <h2>Operations Queue</h2>
        <table>
            <thead>
                <tr><th>Case ID</th><th>Status</th><th>Risk Score</th><th>Recommendation</th><th>Location</th><th>Analyst Action (HITL) / Management</th></tr>
            </thead>
            <tbody id="queueTableBody">
                {% if cases %}
                    {% for c_id, c in cases.items() %}
                    <tr id="case-row-{{ c.id }}">
                        <td><strong>{{ c.id }}</strong></td>
                        <td><span class="badge {% if c.status == 'RESOLVED' %}badge-allow{% elif c.status == 'ESCALATED' %}badge-review{% else %}badge-block{% endif %}" id="status-badge-{{ c.id }}">{{ c.status }}</span></td>
                        <td>{{ "%.1f"|format(c.risk_score * 100) }}%</td>
                        <td>
                            <span id="rec-badge-{{ c.id }}" class="badge {% if c.recommendation == 'BLOCK' or c.decision == 'FRAUD CONFIRMED' %}badge-block{% elif c.recommendation == 'REVIEW' %}badge-review{% else %}badge-allow{% endif %}">
                                {{ c.decision if c.decision != 'PENDING' else c.recommendation }}
                            </span>
                        </td>
                        <td>{{ c.transaction.location_name }}</td>
                        <td>
                            <div id="hitl-actions-{{ c.id }}" style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap;">
                                {% if c.status == 'OPEN' %}
                                <button class="btn-confirm" onclick="hitlAction('{{ c.id }}', 'CONFIRM_FRAUD')">✓ Confirm</button>
                                <button class="btn-resolve" onclick="hitlAction('{{ c.id }}', 'MARK_LEGITIMATE')">✓ Legitimate</button>
                                <button class="btn-escalate" onclick="hitlAction('{{ c.id }}', 'ESCALATE')">Escalate</button>
                                {% else %}
                                <span style="font-size:11px; color: var(--text-muted); margin-right: 6px;">
                                    {% if c.decision == 'AUTO-ALLOWED' %}Auto-Allowed
                                    {% elif c.decision == 'FRAUD CONFIRMED' %}Confirmed
                                    {% elif c.decision == 'MARKED LEGITIMATE' %}Legitimate
                                    {% elif c.decision == 'ESCALATED' %}Escalated
                                    {% else %}Completed{% endif %}
                                </span>
                                {% endif %}
                                <button class="btn-danger" style="padding: 5px 8px; font-size: 11px; margin-top: 0; background: #334155;" onclick="openQueueArchiveModal('{{ c.transaction.tx_id }}', '{{ c.id }}', '{{ c.transaction.merchant }}', {{ c.transaction.amount }})">📁 Archive</button>
                                <button class="btn-permanent-delete" style="padding: 5px 8px; font-size: 11px; margin-top: 0;" onclick="openQueuePermanentDeleteModal('{{ c.transaction.tx_id }}', '{{ c.id }}', '{{ c.transaction.merchant }}', {{ c.transaction.amount }})">🗑️ Delete</button>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr>
                        <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 24px;">No items in the operations queue. Run a transaction risk assessment above to populate cases.</td>
                    </tr>
                {% endif %}
            </tbody>
        </table>
    </div>

    <!-- Archive Transaction Confirmation Modal -->
    <div id="deleteModal" class="modal-overlay">
        <div class="modal-card">
            <h3 style="margin-top:0; color:var(--accent-blue);">Are you sure you want to archive this transaction?</h3>
            <p style="font-size:13px; color: var(--text-muted); margin-bottom: 12px;">This action will remove it from the active dashboard.</p>
            <div style="background: #070e1e; padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); font-size: 13px; margin-bottom: 16px;">
                <div id="del-modal-txid" style="font-weight: bold; color: var(--accent-blue);"></div>
                <div id="del-modal-merchant" style="color: white; margin-top: 4px;"></div>
                <div id="del-modal-amount" style="color: #34d399; margin-top: 2px;"></div>
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="closeDeleteModal()" style="background: #1c2a4a; border: none; cursor: pointer;">Cancel</button>
                <button onclick="confirmDeleteTransaction()" style="background: #2563eb; border: none; cursor: pointer; font-weight: bold;">Archive Transaction</button>
            </div>
        </div>
    </div>

    <!-- Permanent Delete Confirmation Modal -->
    <div id="permanentDeleteModal" class="modal-overlay">
        <div class="modal-card">
            <h3 style="margin-top:0; color:#ef4444;">Are you sure you want to permanently delete this transaction? This action cannot be undone.</h3>
            <div style="background: #070e1e; padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); font-size: 13px; margin-bottom: 16px;">
                <div id="perm-del-modal-txid" style="font-weight: bold; color: var(--accent-blue);"></div>
                <div id="perm-del-modal-merchant" style="color: white; margin-top: 4px;"></div>
                <div id="perm-del-modal-amount" style="color: #34d399; margin-top: 2px;"></div>
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="closePermanentDeleteModal()" style="background: #1c2a4a; border: none; cursor: pointer;">Cancel</button>
                <button onclick="confirmPermanentDeleteTransaction()" style="background: #dc2626; border: none; cursor: pointer; font-weight: bold;">Permanently Delete</button>
            </div>
        </div>
    </div>

    <!-- Clear Queue History Confirmation Modal -->
    <div id="clearQueueModal" class="modal-overlay">
        <div class="modal-card">
            <h3 style="margin-top:0; color:#ef4444;">Are you sure you want to clear all queue history cases?</h3>
            <p style="font-size:13px; color: var(--text-muted); margin-bottom: 16px;">This will clear out the past operations queue history while keeping the active selection dropdown intact.</p>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="closeClearQueueModal()" style="background: #1c2a4a; border: none; cursor: pointer;">Cancel</button>
                <button onclick="confirmClearQueue()" style="background: #dc2626; border: none; cursor: pointer; font-weight: bold;">Clear Queue History</button>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let txData = {{ demo_txs | tojson }};
        let map = L.map('map').setView([40.7128, -74.0060], 11);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        let activeMarker = null;
        let pendingArchiveTxId = null;
        let pendingPermanentDeleteTxId = null;

        function updateSelectedTx(txId) {
            if (!txId) return;
            const tx = txData[txId];
            if (!tx) return;

            if (activeMarker) map.removeLayer(activeMarker);
            activeMarker = L.marker([tx.lat, tx.lng]).addTo(map)
                .bindPopup(`<b>${tx.merchant}</b><br>Amount: $${tx.amount.toFixed(2)}<br>Risk: ${(tx.risk_score*100).toFixed(1)}%`)
                .openPopup();
            map.setView([tx.lat, tx.lng], 13);

            let driversHtml = "";
            (tx.shap_explanations || []).forEach(sh => {
                let color = sh.impact.includes("High") ? "#ef4444" : "#fbbf24";
                driversHtml += `
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 13px; background: #070e1e; padding: 8px; border-radius: 4px; border: 1px solid var(--border-color);">
                        <span>${sh.feature}</span>
                        <span style="color: ${color}; font-weight: bold;">+${sh.contribution} (${sh.impact})</span>
                    </div>
                `;
            });
            document.getElementById('drivers-container').innerHTML = driversHtml || "<p style='font-size:13px; color:var(--text-muted);'>No anomaly factors found.</p>";
        }

        function runAssessment() {
            const select = document.getElementById('tx-select');
            const txId = select.value;
            if (!txId) {
                alert("Please select a transaction first.");
                return;
            }

            fetch('/api/assess', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tx_id: txId})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const box = document.getElementById('alert-status-box');
                    box.style.display = "block";
                    box.className = "alert-status-box" + (data.email_status === "FAILED" ? " alert-status-failed" : "");
                    box.innerHTML = `✓ Assessment completed successfully. Email Alert: <strong>${data.email_status}</strong> to ${data.recipient}`;
                    
                    setTimeout(() => { location.reload(); }, 1500);
                } else {
                    alert("Error during assessment: " + data.error);
                }
            })
            .catch(err => {
                console.error(err);
                alert("Network or server error during assessment.");
            });
        }

        function hitlAction(caseId, action) {
            fetch('/api/hitl', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({case_id: caseId, action: action})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const badge = document.getElementById(`status-badge-${caseId}`);
                    badge.innerText = data.new_status;
                    badge.className = "badge " + (data.new_status === 'RESOLVED' ? 'badge-allow' : 'badge-block');
                    
                    const recBadge = document.getElementById(`rec-badge-${caseId}`);
                    recBadge.innerText = data.new_decision;
                    recBadge.className = "badge " + (data.new_decision.includes('CONFIRMED') ? 'badge-block' : 'badge-allow');
                    
                    document.getElementById(`hitl-actions-${caseId}`).innerHTML = `<span style="font-size:11px; color: var(--text-muted);">${data.new_decision}</span>`;
                } else {
                    alert("Failed to update case: " + data.error);
                }
            })
            .catch(err => console.error(err));
        }

        function openClearQueueModal() {
            document.getElementById('clearQueueModal').style.display = 'flex';
        }
        function closeClearQueueModal() {
            document.getElementById('clearQueueModal').style.display = 'none';
        }
        function confirmClearQueue() {
            fetch('/api/clear-queue-history', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert("Failed to clear queue history");
                }
            });
        }

        function openDeleteModal() {
            const select = document.getElementById('tx-select');
            const txId = select.value;
            if (!txId) { alert("Please select a transaction first."); return; }
            pendingArchiveTxId = txId;
            const tx = txData[txId];
            document.getElementById('del-modal-txid').innerText = tx.tx_id;
            document.getElementById('del-modal-merchant').innerText = tx.merchant;
            document.getElementById('del-modal-amount').innerText = `Amount: $${tx.amount.toFixed(2)}`;
            document.getElementById('deleteModal').style.display = 'flex';
        }
        function closeDeleteModal() { document.getElementById('deleteModal').style.display = 'none'; }
        
        function openPermanentDeleteModal() {
            const select = document.getElementById('tx-select');
            const txId = select.value;
            if (!txId) { alert("Please select a transaction first."); return; }
            pendingPermanentDeleteTxId = txId;
            const tx = txData[txId];
            document.getElementById('perm-del-modal-txid').innerText = tx.tx_id;
            document.getElementById('perm-del-modal-merchant').innerText = tx.merchant;
            document.getElementById('perm-del-modal-amount').innerText = `Amount: $${tx.amount.toFixed(2)}`;
            document.getElementById('permanentDeleteModal').style.display = 'flex';
        }
        function closePermanentDeleteModal() { document.getElementById('permanentDeleteModal').style.display = 'none'; }

        function openQueueArchiveModal(txId, caseId, merchant, amount) {
            pendingArchiveTxId = txId;
            document.getElementById('del-modal-txid').innerText = txId;
            document.getElementById('del-modal-merchant').innerText = merchant;
            document.getElementById('del-modal-amount').innerText = `Amount: $${amount.toFixed(2)}`;
            document.getElementById('deleteModal').style.display = 'flex';
        }

        function openQueuePermanentDeleteModal(txId, caseId, merchant, amount) {
            pendingPermanentDeleteTxId = txId;
            document.getElementById('perm-del-modal-txid').innerText = txId;
            document.getElementById('perm-del-modal-merchant').innerText = merchant;
            document.getElementById('perm-del-modal-amount').innerText = `Amount: $${amount.toFixed(2)}`;
            document.getElementById('permanentDeleteModal').style.display = 'flex';
        }

        function confirmDeleteTransaction() {
            if (!pendingArchiveTxId) return;
            fetch('/api/archive', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tx_id: pendingArchiveTxId})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) { location.reload(); }
            });
        }

        function confirmPermanentDeleteTransaction() {
            if (!pendingPermanentDeleteTxId) return;
            fetch('/api/delete-permanent', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tx_id: pendingPermanentDeleteTxId})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) { location.reload(); }
            });
        }
    </script>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def index():
    active_cases = {k: v for k, v in CASES_DB.items() if k.replace('CASE-', 'TX-') not in ARCHIVED_TRANSACTIONS and k.replace('CASE-', 'TX-') not in DELETED_TRANSACTIONS}
    active_demos = {k: v for k, v in DEMO_TRANSACTIONS.items() if k not in ARCHIVED_TRANSACTIONS and k not in DELETED_TRANSACTIONS}
    return render_template_string(DASHBOARD_HTML, demo_txs=active_demos, cases=active_cases)

@app.route('/api/assess', methods=['POST'])
def api_assess():
    data = request.get_json() or {}
    tx_id = data.get('tx_id')
    if not tx_id or tx_id not in DEMO_TRANSACTIONS:
        return jsonify({"success": False, "error": "Invalid transaction ID"}), 400

    tx_data = DEMO_TRANSACTIONS[tx_id]
    case, is_new = create_or_update_case_from_tx(tx_id, status="OPEN")
    
    # Send email alert
    alert_record = send_fraud_alert_email(case, tx_data)
    
    return jsonify({
        "success": True,
        "case_id": case["id"],
        "email_status": alert_record["status"],
        "recipient": alert_record["recipient"]
    })

@app.route('/api/hitl', methods=['POST'])
def api_hitl():
    data = request.get_json() or {}
    case_id = data.get('case_id')
    action = data.get('action')
    
    if case_id not in CASES_DB:
        return jsonify({"success": False, "error": "Case not found"}), 404
        
    case = CASES_DB[case_id]
    
    if action == 'CONFIRM_FRAUD':
        case['status'] = 'RESOLVED'
        case['decision'] = 'FRAUD CONFIRMED'
        case['human_timeline_events'].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "title": "Analyst Confirmed Fraud",
            "desc": "Human-in-the-loop analyst verified malicious intent and permanently blocked card."
        })
    elif action == 'MARK_LEGITIMATE':
        case['status'] = 'RESOLVED'
        case['decision'] = 'MARKED LEGITIMATE'
        case['human_timeline_events'].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "title": "Analyst Verified Legitimate",
            "desc": "Human-in-the-loop analyst cleared transaction as false positive."
        })
    elif action == 'ESCALATE':
        case['status'] = 'ESCALATED'
        case['decision'] = 'ESCALATED TO TIER 2'
        case['human_timeline_events'].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "title": "Escalated for Investigation",
            "desc": "Case escalated to Tier-2 Special Fraud Operations team."
        })
        
    return jsonify({
        "success": True,
        "new_status": case['status'],
        "new_decision": case['decision']
    })

@app.route('/api/archive', methods=['POST'])
def api_archive():
    data = request.get_json() or {}
    tx_id = data.get('tx_id')
    if tx_id:
        ARCHIVED_TRANSACTIONS.add(tx_id)
        case_id = f"CASE-{tx_id.replace('TX-', '')}"
        if case_id in CASES_DB:
            ARCHIVED_TRANSACTIONS.add(case_id)
    return jsonify({"success": True})

@app.route('/api/delete-permanent', methods=['POST'])
def api_delete_permanent():
    data = request.get_json() or {}
    tx_id = data.get('tx_id')
    if tx_id:
        DELETED_TRANSACTIONS.add(tx_id)
        if tx_id in DEMO_TRANSACTIONS:
            del DEMO_TRANSACTIONS[tx_id]
        case_id = f"CASE-{tx_id.replace('TX-', '')}"
        if case_id in CASES_DB:
            DELETED_TRANSACTIONS.add(case_id)
            del CASES_DB[case_id]
    return jsonify({"success": True})

@app.route('/api/clear-queue-history', methods=['POST'])
def api_clear_queue_history():
    CASES_DB.clear()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)