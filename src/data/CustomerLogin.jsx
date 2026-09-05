import React, { useState } from 'react';
import { customerAccounts } from '../data/customerAccounts';

export default function CustomerLogin({ onLoginSuccess, onSwitchToAdmin }) {
  const [email, setEmail] = useState('pmodinivardhan@gmail.com');
  const [password, setPassword] = useState('password123');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMessage('');

    // Find matching account or fallback to a dynamic object so any email/password works
    const foundAccount = customerAccounts.find(
      (acc) => acc.email.toLowerCase() === email.trim().toLowerCase()
    );

    const account = foundAccount || {
      customerId: 'CUST-001',
      email: email.trim(),
      name: email.split('@')[0] || 'Customer',
      transactionIds: ['TXN-1001']
    };

    onLoginSuccess(account);
  };

  const handleQuickSelect = (accEmail, accPassword) => {
    setEmail(accEmail);
    setPassword(accPassword);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl space-y-6">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-pink-400 bg-clip-text text-transparent">
            Customer Portal Login
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Access your secure transaction dashboard and fraud monitoring
          </p>
        </div>

        {errorMessage && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 text-xs p-3 rounded-lg">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              placeholder="pmodinivardhan@gmail.com"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1">
              Password
            </label>
            <div className="relative flex items-center">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 pr-10 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 text-slate-400 hover:text-slate-200 text-xs focus:outline-none"
                aria-label="Toggle password visibility"
              >
                {showPassword ? '👁️‍🗨️' : '👁️'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-lg transition-colors shadow-lg shadow-indigo-600/20"
          >
            Secure Login 🔓
          </button>
        </form>

        {/* Dynamic Scrollable Demo Accounts Section */}
        <div className="border-t border-slate-800 pt-4 space-y-2">
          <p className="text-xs font-semibold text-slate-400">
            Demo Accounts Available ({customerAccounts.length}):
          </p>
          <div className="max-h-48 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            {customerAccounts.map((acc) => (
              <div
                key={acc.customerId}
                onClick={() => handleQuickSelect(acc.email, acc.password)}
                className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 hover:border-indigo-500/50 cursor-pointer text-xs transition-colors"
              >
                <div className="font-medium text-indigo-300">{acc.email}</div>
                <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
                  <span>Password: <code className="text-slate-400">{acc.password}</code></span>
                  <span>Tx: <code className="text-slate-400">{acc.transactionIds[0]}</code></span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-slate-800 pt-4 text-center">
          <button
            onClick={onSwitchToAdmin}
            className="text-xs text-indigo-400 hover:text-indigo-300 underline font-medium"
          >
            Switch to Admin Fraud Operations Dashboard →
          </button>
        </div>
      </div>
    </div>
  );
}