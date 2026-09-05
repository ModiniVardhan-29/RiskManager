// Render Decision Summary
document.getElementById('decisionSummaryText').innerText = data.decision_summary;

// Render SHAP Contributions
const shapContainer = document.getElementById('shapContainer');
shapContainer.innerHTML = '';

data.risk_reasons.forEach((item, index) => {
    const isIncrease = item.direction === 'INCREASE';
    const badgeColor = isIncrease ? 'text-amber-400 bg-amber-400/10 border-amber-400/20' : 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
    
    const row = document.createElement('div');
    row.className = 'flex justify-between items-center p-2 rounded text-xs bg-slate-900/50 border border-slate-800';
    row.innerHTML = `
        <div class="flex items-center gap-2">
            <span class="text-slate-500 font-mono">#${index + 1}</span>
            <span class="text-slate-200 font-medium">${item.description}</span>
        </div>
        <span class="px-2 py-0.5 rounded border text-[11px] font-mono ${badgeColor}">
            ${item.display_text}
        </span>
    `;
    shapContainer.appendChild(row);
});