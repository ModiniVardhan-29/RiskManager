import React, { useState } from 'react';

export default function TransactionRelationshipGraph({ transaction, customerEmail }) {
  const [hoveredNode, setHoveredNode] = useState(null);

  // Fallback diagnostic if no transaction object is passed
  if (!transaction) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 text-slate-400 text-xs">
        ⚠️ Unable to load relationship graph: No active transaction selected.
      </div>
    );
  }

  // Safely extract risk parameters with fallbacks
  const riskScore = typeof transaction.riskScore === 'number' ? transaction.riskScore : parseFloat(transaction.riskScore) || 0;
  const isHighRisk = riskScore > 0.8 || transaction.fraudStatus === 'FRAUD' || transaction.status === 'FRAUD';
  const isMediumRisk = riskScore > 0.4 && !isHighRisk;

  // Extract transaction details safely
  const txId = transaction.transactionId || transaction.id || 'TX-UNKNOWN';
  const merchant = transaction.merchant || 'Unknown Merchant';
  const amount = transaction.amount ? `$${transaction.amount}` : 'N/A';
  const location = transaction.locationName || transaction.merchantLocation || 
    (transaction.latitude && transaction.longitude ? `${transaction.latitude}, ${transaction.longitude}` : 'Location Unavailable');

  // Build dynamic risk signals
  const riskSignals = [];
  if (isHighRisk || riskScore > 0.8) {
    riskSignals.push({
      id: 'sig-1',
      label: 'High Risk Score',
      level: 'high',
      desc: `Calculated Risk Score: ${(riskScore * 100).toFixed(1)}%`
    });
  }
  if (transaction.amount && parseFloat(transaction.amount) > 500) {
    riskSignals.push({
      id: 'sig-2',
      label: 'Unusual Amount',
      level: isHighRisk ? 'high' : 'medium',
      desc: `Transaction amount ${amount} exceeds typical baseline`
    });
  }
  if (transaction.isVelocityFlagged || isHighRisk) {
    riskSignals.push({
      id: 'sig-3',
      label: 'Velocity Signal',
      level: 'high',
      desc: 'Multiple operations recorded in rapid succession'
    });
  }
  if (riskSignals.length === 0) {
    riskSignals.push({
      id: 'sig-0',
      label: 'Normal Activity Baseline',
      level: 'low',
      desc: 'Behavior matches standard cardholder profile'
    });
  }

  // Node Layout Canvas Coordinates (SVG viewBox 0 0 700 380)
  const nodes = [
    { id: 'customer', label: 'Customer', value: customerEmail || 'Cardholder', type: 'entity', x: 100, y: 190, color: '#818cf8', stroke: '#6366f1' },
    { id: 'card', label: 'Card / Account', value: '•••• 4242', type: 'entity', x: 250, y: 190, color: '#818cf8', stroke: '#6366f1' },
    { id: 'tx', label: 'Transaction', value: txId, subValue: amount, type: 'core', x: 400, y: 190, color: isHighRisk ? '#f87171' : isMediumRisk ? '#fbbf24' : '#34d399', stroke: isHighRisk ? '#ef4444' : isMediumRisk ? '#f59e0b' : '#10b981' },
    { id: 'merchant', label: 'Merchant', value: merchant, type: 'entity', x: 400, y: 70, color: '#818cf8', stroke: '#6366f1' },
    { id: 'location', label: 'Location', value: location, type: 'entity', x: 400, y: 310, color: '#818cf8', stroke: '#6366f1' },
  ];

  // Attach dynamic risk signals to the layout
  riskSignals.forEach((sig, idx) => {
    const yPos = riskSignals.length === 1 ? 190 : 110 + idx * (160 / Math.max(1, riskSignals.length - 1));
    nodes.push({
      id: sig.id,
      label: sig.label,
      value: sig.desc,
      type: 'signal',
      x: 580,
      y: yPos,
      color: sig.level === 'high' ? '#f87171' : sig.level === 'medium' ? '#fbbf24' : '#34d399',
      stroke: sig.level === 'high' ? '#ef4444' : sig.level === 'medium' ? '#f59e0b' : '#10b981',
    });
  });

  // Graph Connections (Edges)
  const edges = [
    { from: 'customer', to: 'card', label: 'owns', color: '#475569' },
    { from: 'card', to: 'tx', label: 'initiates', color: '#475569' },
    { from: 'tx', to: 'merchant', label: 'occurred at', color: '#475569' },
    { from: 'tx', to: 'location', label: 'located in', color: '#475569' },
    ...riskSignals.map((sig) => ({
      from: 'tx',
      to: sig.id,
      label: 'triggers',
      color: sig.level === 'high' ? '#ef4444' : sig.level === 'medium' ? '#f59e0b' : '#10b981',
    })),
  ];

  const getNode = (id) => nodes.find((n) => n.id === id);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3 w-full block">
      <div className="flex justify-between items-start flex-wrap gap-2">
        <div>
          <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
            <span>🔗</span> Transaction Relationship & Fraud Connection Graph
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Visual relationship analysis for selected transaction (<span className="text-indigo-300 font-mono">{txId}</span>) and associated risk signals.
          </p>
        </div>
        <span className="text-[10px] text-slate-500 bg-slate-950 border border-slate-800 px-2 py-1 rounded">
          Simulated Relationship Data for Demo
        </span>
      </div>

      {/* Interactive SVG Canvas Container */}
      <div className="relative bg-slate-950 border border-slate-800/80 rounded-lg p-2 overflow-hidden w-full min-h-[350px]">
        <svg
          viewBox="0 0 700 380"
          className="w-full h-auto min-h-[350px] max-h-[400px] block"
          style={{ minHeight: '350px' }}
        >
          {/* Legend */}
          <g transform="translate(15, 15)">
            <circle cx="5" cy="5" r="4" fill="#ef4444" />
            <text x="14" y="8" fill="#94a3b8" fontSize="10">High Risk / Fraud</text>

            <circle cx="110" cy="5" r="4" fill="#f59e0b" />
            <text x="119" y="8" fill="#94a3b8" fontSize="10">Suspicious Signal</text>

            <circle cx="215" cy="5" r="4" fill="#6366f1" />
            <text x="224" y="8" fill="#94a3b8" fontSize="10">Normal Entity</text>

            <circle cx="305" cy="5" r="4" fill="#10b981" />
            <text x="314" y="8" fill="#94a3b8" fontSize="10">Legitimate / Approved</text>
          </g>

          {/* Render Edges */}
          {edges.map((edge, idx) => {
            const source = getNode(edge.from);
            const target = getNode(edge.to);
            if (!source || !target) return null;

            return (
              <g key={idx}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={edge.color}
                  strokeWidth="1.5"
                  strokeDasharray={edge.color === '#ef4444' ? '4,4' : 'none'}
                />
                <text
                  x={(source.x + target.x) / 2}
                  y={(source.y + target.y) / 2 - 4}
                  fill="#64748b"
                  fontSize="8"
                  textAnchor="middle"
                >
                  {edge.label}
                </text>
              </g>
            );
          })}

          {/* Render Nodes */}
          {nodes.map((node) => {
            const isHovered = hoveredNode?.id === node.id;
            const isCore = node.type === 'core';

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer"
              >
                <circle
                  r={isCore ? 24 : 18}
                  fill="#020617"
                  stroke={node.stroke}
                  strokeWidth={isHovered ? '3' : '2'}
                />
                <circle
                  r={isCore ? 8 : 5}
                  fill={node.color}
                />
                <text
                  y={isCore ? 36 : 28}
                  fill="#e2e8f0"
                  fontSize="10"
                  fontWeight="600"
                  textAnchor="middle"
                >
                  {node.label}
                </text>
                <text
                  y={isCore ? 47 : 38}
                  fill="#94a3b8"
                  fontSize="8"
                  textAnchor="middle"
                >
                  {String(node.value).length > 18 ? `${String(node.value).substring(0, 16)}...` : node.value}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredNode && (
          <div className="absolute bottom-3 left-3 bg-slate-900 border border-slate-700 text-xs p-2.5 rounded-lg shadow-xl max-w-xs space-y-0.5 pointer-events-none z-10">
            <div className="font-bold text-slate-200">{hoveredNode.label}</div>
            <div className="text-indigo-300 font-mono text-[11px]">{hoveredNode.value}</div>
            {hoveredNode.subValue && <div className="text-slate-400 text-[10px]">{hoveredNode.subValue}</div>}
          </div>
        )}
      </div>
    </div>
  );
}