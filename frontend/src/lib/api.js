const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function startScan({ test = false, minConfidence = 0.45 } = {}) {
    const res = await fetch(`${API_BASE}/api/scan?test=${test}&min_confidence=${minConfidence}`, {
        method: "POST",
    });
    return res.json();
}

export async function getScanStatus() {
    const res = await fetch(`${API_BASE}/api/status`);
    return res.json();
}

export async function getScanResults({ direction, sector, minRr, minProb, limit = 50 } = {}) {
    const params = new URLSearchParams();
    if (direction) params.set("direction", direction);
    if (sector) params.set("sector", sector);
    if (minRr) params.set("min_rr", minRr);
    if (minProb) params.set("min_prob", minProb);
    params.set("limit", limit);

    const res = await fetch(`${API_BASE}/api/results?${params}`);
    return res.json();
}

export async function getStocks() {
    const res = await fetch(`${API_BASE}/api/stocks`);
    return res.json();
}

export async function getStockDetail(symbol) {
    const res = await fetch(`${API_BASE}/api/stock/${symbol}`);
    return res.json();
}

export async function getBacktest(symbol) {
    const res = await fetch(`${API_BASE}/api/backtest/${symbol}`);
    return res.json();
}

export async function getSectors() {
    const res = await fetch(`${API_BASE}/api/sectors`);
    return res.json();
}
