const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function startScan({ test = false, minConfidence = 0.40 } = {}) {
    const res = await fetch(`${API_BASE}/api/scan?test=${test}&min_confidence=${minConfidence}`, {
        method: "POST",
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Scan request failed" }));
        throw new Error(err.error || "Scan failed");
    }
    return res.json();
}

export async function getScanStatus() {
    const res = await fetch(`${API_BASE}/api/status`);
    if (!res.ok) return { is_running: false, scanned_count: 0, total_stocks: 0, passed_count: 0, elapsed_seconds: 0, progress_pct: 0, current_stock: "" };
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
    if (!res.ok) return { results: [], count: 0, total: 0 };
    return res.json();
}

export async function getStocks() {
    const res = await fetch(`${API_BASE}/api/stocks`);
    if (!res.ok) return { stocks: [], sectors: [], count: 0 };
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
    if (!res.ok) return { sectors: [] };
    return res.json();
}
