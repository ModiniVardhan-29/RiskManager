import { transactionsData } from './transactionsData'; // Import your existing dataset

/**
 * Maps every existing transaction to a unique customer account credential.
 * Preserves pre-existing customerId/email if present; otherwise dynamically generates them.
 */
export const customerAccounts = transactionsData.map((tx, index) => {
  const indexPad = String(index + 1).padStart(3, '0');
  
  return {
    customerId: tx.customerId || `CUST-${indexPad}`,
    email: tx.customerEmail || `customer${index + 1}@example.com`,
    password: tx.customerPassword || `customer${index + 1}pass`,
    name: tx.customerName || `Customer ${index + 1}`,
    transactionIds: [tx.transactionId || tx.id], // Maps directly to transaction ID
  };
});

/**
 * Authentication lookup function
 */
export const authenticateCustomer = (email, password) => {
  const account = customerAccounts.find(
    (acc) => acc.email.toLowerCase() === email.trim().toLowerCase() && acc.password === password
  );
  
  if (!account) {
    return { success: false, error: 'Invalid email or password.' };
  }
  
  return { success: true, account };
};