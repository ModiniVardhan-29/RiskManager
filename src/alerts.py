import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RiskGraphAlerts")

# Environment settings
ALERTS_ENABLED = os.getenv("ALERTS_ENABLED", "true").lower() == "true"
HIGH_RISK_THRESHOLD = float(os.getenv("HIGH_RISK_THRESHOLD", "0.80"))

# Email Config
EMAIL_ALERTS_ENABLED = os.getenv("EMAIL_ALERTS_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "alerts@riskgraph.ai")

# WhatsApp Config
WHATSAPP_ALERTS_ENABLED = os.getenv("WHATSAPP_ALERTS_ENABLED", "false").lower() == "true"
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")
ALERT_WHATSAPP_TO = os.getenv("ALERT_WHATSAPP_TO", "")

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5000")


def send_fraud_email_alert(case_data: dict, force: bool = False) -> dict:
    """
    Sends an email alert for a high-risk fraud case.
    Falls back gracefully to SIMULATION MODE if SMTP is disabled or unconfigured.
    """
    case_id = case_data.get("case_id", case_data.get("id", "UNKNOWN"))
    prob = case_data.get("calibrated_prob", case_data.get("risk_score", 0.0))
    if isinstance(prob, (int, float)) and prob <= 1.0:
        prob_pct = f"{prob * 100:.1f}%"
    else:
        prob_pct = f"{prob}%"

    drivers = case_data.get("shap_drivers", case_data.get("top_drivers", []))
    drivers_str = "\n".join([f"  {idx + 1}. {d}" for idx, d in enumerate(drivers[:3])]) if drivers else "  1. Anomaly in transaction pattern"

    subject = f"🚨 FRAUD ALERT — RISKGRAPH AI: Case {case_id}"
    body = f"""🚨 FRAUD ALERT — RISKGRAPH AI

Case ID: {case_id}

Risk Level: HIGH RISK
Calibrated Fraud Probability: {prob_pct}

Recommended Action: BLOCK

Transaction Details:
Amount: ${case_data.get('amount', 'N/A')}
Category: {case_data.get('category', 'N/A')}
Time: {case_data.get('time', 'N/A')}
Distance: {case_data.get('distance', 'N/A')} km

Top Risk Drivers:
{drivers_str}

Current Status:
{case_data.get('status', 'OPEN')}

Action Required:
Please review this case in the RiskGraph AI Fraud Case Management Queue.
Dashboard: {DASHBOARD_URL}/cases/{case_id}
"""

    if EMAIL_ALERTS_ENABLED and SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg["From"] = ALERT_EMAIL_FROM
            msg["To"] = ALERT_EMAIL_TO
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()

            logger.info(f"[Alert] Real Email sent successfully for case {case_id}.")
            return {"status": "SENT", "mode": "LIVE", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        except Exception as e:
            logger.error(f"[Alert] Failed to send real email: {str(e)}")
            return {"status": "FAILED", "mode": "LIVE", "error": str(e), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    else:
        logger.info(f"\n[ALERT SIMULATION — EMAIL]\nRecipient: {ALERT_EMAIL_TO or 'analyst@riskgraph.ai'}\nSubject: {subject}\n{body}\n")
        return {"status": "SIMULATED", "mode": "DEMO", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def send_fraud_whatsapp_alert(case_data: dict, force: bool = False) -> dict:
    """
    Sends a WhatsApp alert via Twilio for a high-risk fraud case.
    Falls back gracefully to SIMULATION MODE if Twilio is disabled or unconfigured.
    """
    case_id = case_data.get("case_id", case_data.get("id", "UNKNOWN"))
    prob = case_data.get("calibrated_prob", case_data.get("risk_score", 0.0))
    if isinstance(prob, (int, float)) and prob <= 1.0:
        prob_pct = f"{prob * 100:.1f}%"
    else:
        prob_pct = f"{prob}%"

    message_body = (
        f"🚨 *FRAUD ALERT — RISKGRAPH AI*\n\n"
        f"*Case ID:* {case_id}\n"
        f"*Risk Level:* HIGH RISK\n"
        f"*Probability:* {prob_pct}\n"
        f"*Action:* BLOCK\n\n"
        f"*Amount:* ${case_data.get('amount', 'N/A')}\n"
        f"*Category:* {case_data.get('category', 'N/A')}\n\n"
        f"⚠️ Immediate analyst review required.\n"
        f"View case: {DASHBOARD_URL}/cases/{case_id}"
    )

    if WHATSAPP_ALERTS_ENABLED and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_WHATSAPP_FROM,
                to=ALERT_WHATSAPP_TO
            )
            logger.info(f"[Alert] Real WhatsApp sent via Twilio (SID: {message.sid}).")
            return {"status": "SENT", "mode": "LIVE", "sid": message.sid, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        except Exception as e:
            logger.error(f"[Alert] Failed to send WhatsApp via Twilio: {str(e)}")
            return {"status": "FAILED", "mode": "LIVE", "error": str(e), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    else:
        logger.info(
            f"\n[ALERT SIMULATION — WHATSAPP]\n"
            f"To: {ALERT_WHATSAPP_TO or 'whatsapp:+12345678900'}\n"
            f"Message:\n{message_body}\n"
        )
        return {"status": "SIMULATED", "mode": "DEMO", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def send_fraud_alerts(case_data: dict, force_resend: bool = False) -> dict:
    """
    Main entry point for dispatching fraud alerts.
    Includes duplicate prevention logic to prevent duplicate alerts on reloads or re-openings.
    """
    if not ALERTS_ENABLED and not force_resend:
        return {"email": {"status": "DISABLED"}, "whatsapp": {"status": "DISABLED"}}

    # Check risk threshold
    prob = case_data.get("calibrated_prob", case_data.get("risk_score", 0.0))
    if isinstance(prob, str):
        try:
            prob = float(prob.replace("%", "")) / 100.0
        except ValueError:
            prob = 0.0

    if prob < HIGH_RISK_THRESHOLD and not force_resend:
        logger.info(f"[Alert] Probability {prob:.2f} is below threshold {HIGH_RISK_THRESHOLD}. Skipping alert.")
        return {"email": {"status": "SKIPPED_LOW_RISK"}, "whatsapp": {"status": "SKIPPED_LOW_RISK"}}

    # Duplicate prevention check
    if case_data.get("alerts_sent", False) and not force_resend:
        logger.info(f"[Alert] Alerts already sent for case {case_data.get('case_id')}. Skipping duplicate.")
        return {"email": {"status": "SKIPPED_DUPLICATE"}, "whatsapp": {"status": "SKIPPED_DUPLICATE"}}

    logger.info(f"[RiskGraph] Triggering fraud alerts for Case {case_data.get('case_id')}...")

    email_res = send_fraud_email_alert(case_data, force=force_resend)
    whatsapp_res = send_fraud_whatsapp_alert(case_data, force=force_resend)

    return {
        "email": email_res,
        "whatsapp": whatsapp_res,
        "alerts_sent": True,
        "last_alert_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }