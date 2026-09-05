import { triggerFraudAlertEmail } from './services/emailService';
// src/services/emailService.js

export async function triggerFraudAlertEmail(transactionData) {
  try {
    const response = await fetch('http://localhost:5000/api/send-fraud-alert', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        transactionId: transactionData.id,
        merchant: transactionData.merchant,
        amount: transactionData.amount,
        dateTime: transactionData.timestamp || new Date().toISOString(),
        location: transactionData.location,
        status: transactionData.status,
        riskScore: transactionData.riskScore,
        reason: transactionData.reason || transactionData.shapSummary,
      }),
    });

    const result = await response.json();
    if (result.success) {
      console.log('✓ Fraud alert email sent successfully');
    }
  } catch (error) {
    console.error('Unable to send fraud alert email:', error);
  }
}