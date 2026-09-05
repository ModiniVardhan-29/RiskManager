import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "riskgraph_cases.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(reset_session=True):
    """Initializes SQLite database and wipes old demo cases on fresh app restarts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            trans_num TEXT,
            amount REAL,
            category TEXT,
            trans_time TEXT,
            distance_km REAL,
            calibrated_prob REAL,
            raw_risk_score REAL,
            risk_level TEXT,
            recommended_action TEXT,
            case_status TEXT,
            human_decision TEXT,
            analyst_notes TEXT,
            reviewed_by TEXT,
            reviewed_at TEXT,
            dataset_ground_truth INTEGER,
            shap_drivers TEXT,
            rel_features TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()

    if reset_session:
        cursor.execute("DELETE FROM cases")
        conn.commit()

    conn.close()

def create_case_if_not_exists(case_data: dict) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()

    tx_num = str(case_data.get('trans_num', 'TXN_UNKNOWN'))
    cursor.execute("SELECT case_id FROM cases WHERE trans_num = ?", (tx_num,))
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return existing['case_id']

    cursor.execute("SELECT COUNT(*) as cnt FROM cases")
    count = cursor.fetchone()['cnt'] + 1
    case_id = f"CASE-{count:06d}"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        INSERT INTO cases (
            case_id, trans_num, amount, category, trans_time, distance_km,
            calibrated_prob, raw_risk_score, risk_level, recommended_action,
            case_status, human_decision, analyst_notes, reviewed_by, reviewed_at,
            dataset_ground_truth, shap_drivers, rel_features, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        case_id,
        tx_num,
        float(case_data.get('amount', 0.0)),
        str(case_data.get('category', 'General')),
        str(case_data.get('trans_time', '12:00')),
        float(case_data.get('distance_km', 0.0)),
        float(case_data.get('calibrated_prob', 0.0)),
        float(case_data.get('raw_risk_score', 0.0)),
        str(case_data.get('risk_level', 'MEDIUM RISK')),
        str(case_data.get('recommended_action', 'REVIEW')),
        str(case_data.get('case_status', 'OPEN')),
        str(case_data.get('analyst_decision', 'PENDING')),
        str(case_data.get('analyst_notes', '')),
        case_data.get('reviewed_by'),
        case_data.get('reviewed_at'),
        int(case_data.get('dataset_ground_truth', 0)),
        json.dumps(case_data.get('shap_drivers', [])),
        json.dumps(case_data.get('rel_features', {})),
        now_str
    ))

    conn.commit()
    conn.close()
    return case_id

def get_all_cases(status_filter='ALL', risk_filter='ALL'):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM cases WHERE 1=1"
    params = []

    if status_filter != 'ALL':
        query += " AND case_status = ?"
        params.append(status_filter)

    if risk_filter != 'ALL':
        query += " AND risk_level = ?"
        params.append(risk_filter)

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cases = []
    for r in rows:
        cases.append({
            'case_id': r['case_id'],
            'trans_num': r['trans_num'],
            'amount': r['amount'],
            'category': r['category'],
            'trans_time': r['trans_time'],
            'distance_km': r['distance_km'],
            'calibrated_prob': r['calibrated_prob'],
            'raw_risk_score': r['raw_risk_score'],
            'risk_level': r['risk_level'],
            'recommended_action': r['recommended_action'],
            'case_status': r['case_status'],
            'human_decision': r['human_decision'],
            'analyst_notes': r['analyst_notes'],
            'reviewed_by': r['reviewed_by'],
            'reviewed_at': r['reviewed_at'],
            'dataset_ground_truth': r['dataset_ground_truth'],
            'shap_drivers': json.loads(r['shap_drivers']) if r['shap_drivers'] else [],
            'rel_features': json.loads(r['rel_features']) if r['rel_features'] else {},
            'created_at': r['created_at']
        })

    conn.close()
    return cases

def get_case_by_id(case_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
    r = cursor.fetchone()
    conn.close()

    if not r:
        return None

    return {
        'case_id': r['case_id'],
        'trans_num': r['trans_num'],
        'amount': r['amount'],
        'category': r['category'],
        'trans_time': r['trans_time'],
        'distance_km': r['distance_km'],
        'calibrated_prob': r['calibrated_prob'],
        'raw_risk_score': r['raw_risk_score'],
        'risk_level': r['risk_level'],
        'recommended_action': r['recommended_action'],
        'case_status': r['case_status'],
        'human_decision': r['human_decision'],
        'analyst_notes': r['analyst_notes'],
        'reviewed_by': r['reviewed_by'],
        'reviewed_at': r['reviewed_at'],
        'dataset_ground_truth': r['dataset_ground_truth'],
        'shap_drivers': json.loads(r['shap_drivers']) if r['shap_drivers'] else [],
        'rel_features': json.loads(r['rel_features']) if r['rel_features'] else {},
        'created_at': r['created_at']
    }

def update_analyst_action(case_id, action, notes='', reviewer='Analyst'):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    if not case:
        conn.close()
        return False, "Case not found"

    new_status = case['case_status']
    new_decision = case['human_decision']

    if action == 'START_REVIEW':
        new_status = 'UNDER_REVIEW'
    elif action == 'CONFIRM_FRAUD':
        new_status = 'RESOLVED'
        new_decision = 'CONFIRMED_FRAUD'
    elif action == 'MARK_LEGITIMATE':
        new_status = 'RESOLVED'
        new_decision = 'DISMISSED_LEGITIMATE'
    elif action == 'ESCALATE':
        new_status = 'ESCALATED'
    elif action == 'RESUME_REVIEW':
        new_status = 'UNDER_REVIEW'

    cursor.execute('''
        UPDATE cases
        SET case_status = ?, human_decision = ?, analyst_notes = ?, reviewed_by = ?, reviewed_at = ?
        WHERE case_id = ?
    ''', (new_status, new_decision, notes, reviewer, now_str, case_id))

    conn.commit()
    conn.close()
    return True, new_status

def reset_all_cases():
    """Explicit endpoint helper to reset session cases on request."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases")
    conn.commit()
    conn.close()

def get_hitl_analytics():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM cases")
    total_cases = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as cnt FROM cases WHERE case_status IN ('OPEN', 'UNDER_REVIEW', 'ESCALATED')")
    open_cases = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM cases WHERE case_status = 'RESOLVED'")
    resolved_cases = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM cases WHERE human_decision = 'CONFIRMED_FRAUD'")
    confirmed_fraud = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM cases WHERE human_decision = 'DISMISSED_LEGITIMATE'")
    dismissed_legit = cursor.fetchone()['cnt']

    cursor.execute("SELECT * FROM cases WHERE human_decision IN ('CONFIRMED_FRAUD', 'DISMISSED_LEGITIMATE')")
    reviewed_rows = cursor.fetchall()
    total_reviewed = len(reviewed_rows)

    agreements = 0
    for r in reviewed_rows:
        rec = r['recommended_action']
        dec = r['human_decision']
        if (rec == 'BLOCK' and dec == 'CONFIRMED_FRAUD') or (rec == 'REVIEW' and dec == 'CONFIRMED_FRAUD') or (rec == 'ALLOW' and dec == 'DISMISSED_LEGITIMATE'):
            agreements += 1

    agreement_rate = round((agreements / total_reviewed) * 100, 1) if total_reviewed > 0 else None

    conn.close()

    return {
        'total_cases': total_cases,
        'open_cases': open_cases,
        'resolved_cases': resolved_cases,
        'confirmed_fraud': confirmed_fraud,
        'dismissed_legit': dismissed_legit,
        'total_reviewed': total_reviewed,
        'agreements': agreements,
        'agreement_rate': agreement_rate
    }