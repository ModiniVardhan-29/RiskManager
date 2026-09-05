# RiskGraph AI

## Relationship-Aware Payment Fraud Detection & Management System

RiskGraph AI is an AI-powered payment fraud detection and management system that combines machine learning, relationship-aware graph features, SHAP explainability, risk visualization, analyst workflows, and automated email alerts.

## Objective

To detect payment fraud, identify suspicious relationships and transaction patterns, explain fraud decisions, and help analysts take faster and more informed actions.

## Problem

Traditional fraud detection systems often focus on individual transactions and may miss hidden relationships between accounts, merchants, and transactions. They may also provide limited explanation for why a transaction was flagged.

RiskGraph AI addresses these challenges by combining fraud prediction with graph-based relationship analysis and explainable AI.

## Key Features

- Payment fraud detection using XGBoost
- Relationship-aware graph feature engineering
- Graph embeddings for capturing transaction relationships
- SHAP-based fraud decision explanations
- Transaction-level risk scoring
- Geographic anomaly visualization
- Fraud operations queue
- Human-in-the-loop analyst actions
- Confirm Fraud / Mark Legitimate / Escalate / Archive
- Automated fraud email alerts
- Model comparison and ablation study
- Held-out test evaluation
- False-positive cost analysis

## System Workflow

Transaction Data
↓
Data Preprocessing
↓
Feature Engineering
↓
Graph-Based Relationship Features
↓
XGBoost Fraud Detection Model
↓
Risk Score
↓
SHAP Decision Drivers
↓
Fraud Operations Dashboard
↓
Analyst Action
↓
Fraud Alert / Case Resolution

## Model Comparison

| Model | AUC-ROC | F1-Score |
|---|---:|---:|
| Baseline XGBoost | 0.862 | 0.791 |
| Graph Embeddings Only | 0.894 | 0.845 |
| RiskGraph AI (Full) | 0.954 | 0.923 |

The system evaluates fraud detection using precision, recall, F1-score, ROC-AUC, PR-AUC, confusion matrix, false-positive rate, and estimated false-positive cost.

## Explainable AI

RiskGraph AI uses SHAP to identify the main factors contributing to a fraud decision.

Example decision drivers include:

- Unusual Transaction Pattern
- High-Risk / Unusual Location
- Transaction Amount Anomaly
- Merchant Risk Signal

This allows analysts to understand why a transaction was considered risky.

## Admin Dashboard

The dashboard provides:

- Fraud detection performance metrics
- Geographic anomaly visualization
- Transaction risk assessment
- Fraud decision drivers
- Operations queue
- Analyst actions
- Automated alert functionality

## Automated Alerts

When a suspicious transaction is confirmed through the fraud-response workflow, the system can send an email alert containing:

- Transaction details
- Risk score
- Fraud decision
- Key decision drivers

This connects model predictions directly to an operational response.

## Technology Stack

- Python
- XGBoost
- Scikit-learn
- Pandas
- NumPy
- SHAP
- NetworkX / Graph-based feature engineering
- Flask
- HTML / CSS / JavaScript
- Node.js
- Express
- Nodemailer
- SMTP
- Parquet / CSV

## Project Structure

RiskGraph-AI/
│
├── app_2.py
├── alerts.py
├── build_features.py
├── calibration_analysis.py
├── explainability.py
├── graph_features.py
├── inspect_dataset.py
├── preprocessing.py
├── train_baseline.py
├── train_riskgraph.py
├── server.js
│
├── components/
├── data/
├── .env
└── README.md

## Installation

Install the required Python dependencies:

```bash
pip install -r requirements.txt
