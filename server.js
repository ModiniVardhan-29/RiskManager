const express = require('express');
const nodemailer = require('nodemailer');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: Number(process.env.SMTP_PORT) || 587,
  secure: Number(process.env.SMTP_PORT) === 465,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

transporter.verify((error) => {
  if (error) {
    console.warn('⚠️ SMTP Warning:', error.message);
  } else {
    console.log('✓ SMTP Server is ready to send messages');
  }
});

app.post('/api/send-fraud-alert', async (req, res) => {
  try {
    const { transactionId, merchant, amount, dateTime, location, status, riskScore, reason } = req.body;
    const recipient = process.env.NOTIFICATION_RECIPIENT_EMAIL;

    if (!recipient) {
      return res.status(500).json({ success: false, error: 'Recipient missing in .env' });
    }

    const mailOptions = {
      from: `"RiskGraph AI Security" <${process.env.SMTP_USER}>`,
      to: recipient,
      subject: '🚨 RiskGraph AI Fraud Alert – Suspicious Transaction Detected',
      html: `
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <h2 style="color: #d9534f;">🚨 Fraud Alert</h2>
          <p>Our fraud protection system detected unusual activity associated with this transaction.</p>
          <hr />
          <ul>
            <li><strong>Transaction ID:</strong> ${transactionId || 'N/A'}</li>
            <li><strong>Merchant:</strong> ${merchant || 'N/A'}</li>
            <li><strong>Amount:</strong> ${amount || 'N/A'}</li>
            <li><strong>Date & Time:</strong> ${dateTime || new Date().toLocaleString()}</li>
            <li><strong>Location:</strong> ${location || 'N/A'}</li>
            <li><strong>Status:</strong> ${status || 'Flagged'}</li>
            <li><strong>Risk Score:</strong> ${riskScore ?? 'N/A'}</li>
            <li><strong>Reason:</strong> ${reason || 'High risk pattern identified'}</li>
          </ul>
        </div>
      `,
    };

    await transporter.sendMail(mailOptions);
    console.log(`✓ Fraud alert email sent to ${recipient}`);
    return res.status(200).json({ success: true, message: 'Alert sent successfully.' });
  } catch (error) {
    console.error('Email sending failed:', error.message);
    return res.status(500).json({ success: false, error: error.message });
  }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`RiskGraph AI Alert Server running on port ${PORT}`);
});