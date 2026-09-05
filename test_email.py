import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

server_host = os.getenv("MAIL_SERVER", "smtp.gmail.com")
server_port = int(os.getenv("MAIL_PORT", 587))
username = os.getenv("MAIL_USERNAME")
password = os.getenv("MAIL_PASSWORD")
recipient = os.getenv("ALERT_RECIPIENT_EMAIL", username)

print(f"Loaded Username: {username}")
print(f"Loaded Recipient: {recipient}")

if not username or not password:
    print("❌ ERROR: MAIL_USERNAME or MAIL_PASSWORD is missing from your .env file!")
    exit()

# Build test message
msg = MIMEText("This is a test email sent from your Python environment.")
msg["Subject"] = "RiskGraph Python SMTP Test"
msg["From"] = username
msg["To"] = recipient

try:
    print("Attempting connection to SMTP server...")
    with smtplib.SMTP(server_host, server_port) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(username, [recipient], msg.as_string())
    print("✅ SUCCESS: Email sent successfully!")
except Exception as e:
    print(f"❌ FAILED to send email: {e}")