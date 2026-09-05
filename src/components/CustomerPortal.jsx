import React, { useState } from 'react';
import { transactionsData } from '../data/transactionsData';
import TransactionLocationMap from './TransactionLocationMap';
import TransactionRelationshipGraph from './TransactionRelationshipGraph';

export default function CustomerPortal({ authAccount, onLogout }) {
  // Filter transactions exclusively belonging to logged-in customer account
  const customerTransactions = transactionsData.filter((tx) =>
    authAccount?.transactionIds?.includes(tx.transactionId || tx.id)
  );

  const [selectedTxId, setSelectedTxId] = useState(
    customerTransactions[0]?.transactionId || customerTransactions[0]?.id || ''
  );

  const activeTransaction =
    customerTransactions.find(
      (tx) => (tx.transactionId || tx.id) === selectedTxId
    ) || customerTransactions[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* CUSTOMER INFORMATION HEADER */}
      <header className="flex justify-between items-center border-b border-slate-800 pb-4 max-w-7xl mx-auto">
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Customer Portal
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Logged in as: <span className="text-indigo-300 font-mono">{authAccount?.email}</span> (ID: {authAccount?.customerId})
          </p>
        </div>
        <button
          onClick={onLogout}
          className="px-3 py-1.5 bg-slate-900 border border-slate-700 hover:bg-slate-800 text-xs font-semibold rounded-lg text-slate-300 transition-colors"
        >
          Sign Out
        </button>
      </header>

      <main className="max-w-7xl mx-auto space-y-6">
        {/* TRANSACTION SELECTION */}
        {customerTransactions.length > 1 && (
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-2">
            <label className="text-xs font-semibold text-slate-400">Select Your Transaction:</label>
            <select
              value={selectedTxId}
              onChange={(e) => setSelectedTxId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              {customerTransactions.map((tx) => (
                <option key={tx.transactionId || tx.id} value={tx.transactionId || tx.id}>
                  {tx.transactionId || tx.id} - ${tx.amount} ({tx.merchant})
                </option>
              ))}
            </select>
          </div>
        )}

        {activeTransaction ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* ASSOCIATED TRANSACTION DETAILS */}
              <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="text-base font-semibold text-slate-200 border-b border-slate-800 pb-2">
                  Transaction Details
                </h3>
                
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Transaction ID:</span>
                    <span className="font-mono text-indigo-400">{activeTransaction.transactionId || activeTransaction.id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Amount:</span>
                    <span className="font-bold text-slate-100">${activeTransaction.amount}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Merchant:</span>
                    <span className="text-slate-200">{activeTransaction.merchant}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Timestamp:</span>
                    <span className="text-slate-400">{activeTransaction.timestamp}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Status:</span>
                    <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px] uppercase font-bold">
                      {activeTransaction.status || 'COMPLETED'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Fraud Risk Level:</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      activeTransaction.riskScore > 0.8 || activeTransaction.fraudStatus === 'FRAUD'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}>
                      {activeTransaction.riskScore > 0.8 || activeTransaction.fraudStatus === 'FRAUD' ? 'FRAUD RISK DETECTED' : 'LOW RISK'}
                    </span>
                  </div>
                </div>

                {/* TRANSACTION LOCATION MAP */}
                <div className="pt-4 border-t border-slate-800">
                  <h4 className="text-xs font-semibold text-slate-400 mb-2">Transaction Location</h4>
                  <div className="h-48 rounded-lg overflow-hidden border border-slate-800">
                    <TransactionLocationMap
                      latitude={activeTransaction.latitude}
                      longitude={activeTransaction.longitude}
                      merchant={activeTransaction.merchant}
                    />
                  </div>
                </div>
              </div>

              {/* FRAUD TIMELINE */}
              <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="text-base font-semibold text-slate-200 border-b border-slate-800 pb-2">
                  Activity & Verification Timeline
                </h3>
                
                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                  {(activeTransaction.timeline || [
                    { title: 'Transaction Initiated', time: activeTransaction.timestamp, desc: 'Payment request received.' },
                    { title: 'Historical Baseline Checked', time: activeTransaction.timestamp, desc: 'Verified past behavior patterns.' },
                    activeTransaction.riskScore > 0.8 || activeTransaction.fraudStatus === 'FRAUD'
                      ? { title: 'FRAUD RISK DETECTED', time: activeTransaction.timestamp, desc: 'Anomaly flagged by relationship graph models.', isAlert: true }
                      : { title: 'Transaction Approved', time: activeTransaction.timestamp, desc: 'Passed risk threshold checks.' }
                  ]).map((step, idx) => (
                    <div key={idx} className="relative">
                      <div className={`absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 ${
                        step.isAlert || step.title.includes('FRAUD')
                          ? 'bg-red-500 border-red-900 animate-pulse'
                          : 'bg-indigo-500 border-slate-950'
                      }`} />
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold ${
                            step.isAlert || step.title.includes('FRAUD') ? 'text-red-400' : 'text-slate-200'
                          }`}>
                            {step.title}
                          </span>
                          <span className="text-[10px] text-slate-500">{step.time}</span>
                        </div>
                        <p className="text-xs text-slate-400">{step.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* TRANSACTION RELATIONSHIP & FRAUD CONNECTION GRAPH */}
            <TransactionRelationshipGraph
              transaction={activeTransaction}
              customerEmail={authAccount?.email}
            />
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 bg-slate-900 rounded-xl border border-slate-800">
            No transactions found for this customer account.
          </div>
        )}
      </main>
    </div>
  );
}