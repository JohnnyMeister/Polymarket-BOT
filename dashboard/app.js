document.addEventListener("DOMContentLoaded", () => {
    const grid = document.getElementById("strategy-grid");
    const globalProfitEl = document.getElementById("global-profit");
    const globalTradesEl = document.getElementById("global-trades");
    const globalEvEl = document.getElementById("global-ev");

    async function fetchStats() {
        try {
            const response = await fetch('/api/v1/stats');
            const data = await response.json();
            renderDashboard(data);
        } catch (err) {
            console.error("Dashboard fetch error:", err);
            grid.innerHTML = `<div class="loader" style="color: var(--danger)">Connection to Engine Lost</div>`;
        }
    }

    function formatMoney(num) {
        let formatted = `$${Math.abs(num).toFixed(2)}`;
        return num < 0 ? `-${formatted}` : formatted;
    }

    function renderDashboard(data) {
        grid.innerHTML = ""; // Clear loader
        
        // Tracking global aggregates
        let aggProfit = 0;
        let aggTrades = 0;
        let aggEvSum = 0;
        let stratCount = 0;

        // Iterate over keys
        for (const [strategyId, stats] of Object.entries(data)) {
            if (!stats.total_trades) continue; // Skip empty strats

            aggProfit += stats.total_profit;
            aggTrades += stats.total_trades;
            aggEvSum += stats.average_ev;
            stratCount++;

            const card = document.createElement("div");
            card.className = "strategy-card";
            
            const roiClass = stats.roi_percent >= 0 ? "success" : "danger";
            const profitClass = stats.total_profit >= 0 ? "success" : "danger";

            card.innerHTML = `
                <div class="strategy-header">
                    <h3>${strategyId.replace(/_/g, " ")}</h3>
                    <div class="roi-badge ${roiClass}">${stats.roi_percent}% ROI</div>
                </div>
                <div class="metric-list">
                    <div class="metric-row">
                        <span class="name">Profit</span>
                        <span class="val ${profitClass}">${formatMoney(stats.total_profit)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="name">Win Rate</span>
                        <span class="val">${stats.win_rate_percent}%</span>
                    </div>
                    <div class="metric-row">
                        <span class="name">Total Trades</span>
                        <span class="val">${stats.total_trades}</span>
                    </div>
                    <div class="metric-row">
                        <span class="name">Max Drawdown</span>
                        <span class="val danger">${formatMoney(stats.max_drawdown)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="name">Avg Expected Value</span>
                        <span class="val">${stats.average_ev.toFixed(4)}</span>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        }

        // Handle empty initial state gracefully
        if (stratCount === 0) {
            grid.innerHTML = `<div class="loader">Awaiting Initial Trades...</div>`;
            return;
        }

        // Update globals
        globalProfitEl.innerText = formatMoney(aggProfit);
        globalProfitEl.className = `value ${aggProfit >= 0 ? 'success' : 'danger'}`;
        globalTradesEl.innerText = aggTrades;
        globalEvEl.innerText = (aggEvSum / stratCount).toFixed(4); // Average of averages
    }

    // Polling every 2.5 seconds
    fetchStats();
    setInterval(fetchStats, 2500);
});
