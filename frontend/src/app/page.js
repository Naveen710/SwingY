"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { startScan, getScanStatus, getScanResults } from "@/lib/api";
import Link from "next/link";

// ═══════════════════════════════════════════════════════════════
// STAT CARD COMPONENT
// ═══════════════════════════════════════════════════════════════

function StatCard({ label, value, icon, color }) {
  return (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">{label}</p>
          <p className={`text-2xl font-bold ${color || "text-white"}`}>{value}</p>
        </div>
        <span className="text-3xl opacity-20">{icon}</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// PROGRESS COMPONENT
// ═══════════════════════════════════════════════════════════════

function ScannerProgress({ status }) {
  if (!status || !status.is_running) return null;

  return (
    <div className="glass-card p-6 mb-6 scanning-pulse animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-indigo-500 rounded-full animate-pulse" />
          <span className="text-sm font-semibold text-indigo-400">Scanning NSE Stocks...</span>
        </div>
        <span className="text-xs text-[var(--text-muted)]">
          {status.scanned_count} / {status.total_stocks} stocks
        </span>
      </div>
      <div className="progress-bar mb-3">
        <div className="progress-fill" style={{ width: `${status.progress_pct}%` }} />
      </div>
      <div className="flex justify-between text-xs text-[var(--text-muted)]">
        <span>Current: {status.current_stock}</span>
        <span>{status.passed_count} opportunities found</span>
        <span>{status.elapsed_seconds}s elapsed</span>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// FILTER BAR
// ═══════════════════════════════════════════════════════════════

function FilterBar({ filters, setFilters, sectors }) {
  return (
    <div className="glass-card p-4 mb-6">
      <div className="flex flex-wrap gap-3 items-center">
        <select
          value={filters.direction || ""}
          onChange={(e) => setFilters({ ...filters, direction: e.target.value || null })}
          className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Directions</option>
          <option value="bullish">🟢 Bullish</option>
          <option value="bearish">🔴 Bearish</option>
        </select>

        <select
          value={filters.sector || ""}
          onChange={(e) => setFilters({ ...filters, sector: e.target.value || null })}
          className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
        >
          <option value="">All Sectors</option>
          {sectors.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select
          value={filters.minRr || ""}
          onChange={(e) => setFilters({ ...filters, minRr: e.target.value || null })}
          className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
        >
          <option value="">Min R:R</option>
          <option value="1.5">≥ 1.5</option>
          <option value="2">≥ 2.0</option>
          <option value="2.5">≥ 2.5</option>
          <option value="3">≥ 3.0</option>
        </select>

        <select
          value={filters.minProb || ""}
          onChange={(e) => setFilters({ ...filters, minProb: e.target.value || null })}
          className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
        >
          <option value="">Min Probability</option>
          <option value="50">≥ 50%</option>
          <option value="60">≥ 60%</option>
          <option value="70">≥ 70%</option>
        </select>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// RESULTS TABLE
// ═══════════════════════════════════════════════════════════════

function ResultsTable({ results }) {
  if (!results || results.length === 0) {
    return (
      <div className="glass-card p-12 text-center">
        <p className="text-4xl mb-4">📊</p>
        <p className="text-lg text-[var(--text-secondary)]">No scan results yet</p>
        <p className="text-sm text-[var(--text-muted)] mt-1">Click "Run Scanner" to analyze NSE stocks</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Stock</th>
              <th>Pattern</th>
              <th>Entry</th>
              <th>Stop Loss</th>
              <th>Target</th>
              <th>R:R</th>
              <th>Probability</th>
              <th>Profit (₹1L)</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => (
              <tr key={r.symbol} className="animate-fade-in" style={{ animationDelay: `${i * 50}ms` }}>
                <td className="text-[var(--text-muted)]">{i + 1}</td>
                <td>
                  <Link
                    href={`/stock/${r.symbol.replace(".NS", "")}`}
                    className="group"
                  >
                    <div className="font-semibold text-white group-hover:text-indigo-400 transition-colors">
                      {r.symbol.replace(".NS", "")}
                    </div>
                    <div className="text-xs text-[var(--text-muted)]">{r.name}</div>
                  </Link>
                </td>
                <td>
                  <span className={r.direction === "bullish" ? "badge-bullish" : "badge-bearish"}>
                    {r.pattern?.name || "—"}
                  </span>
                </td>
                <td className="font-mono">₹{r.entry?.toLocaleString("en-IN")}</td>
                <td className="font-mono text-red-400">₹{r.stop_loss?.toLocaleString("en-IN")}</td>
                <td className="font-mono text-green-400">₹{r.target?.toLocaleString("en-IN")}</td>
                <td>
                  <span className={`font-semibold ${r.risk_reward >= 2.5 ? "text-green-400" : r.risk_reward >= 2 ? "text-yellow-400" : "text-[var(--text-secondary)]"}`}>
                    1:{r.risk_reward}
                  </span>
                </td>
                <td>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${r.probability}%`,
                          background: r.probability >= 65 ? "#10b981" : r.probability >= 50 ? "#f59e0b" : "#ef4444",
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium">{r.probability}%</span>
                  </div>
                </td>
                <td className={`font-semibold ${r.profit_on_1lakh > 0 ? "text-green-400" : "text-red-400"}`}>
                  ₹{Math.round(r.profit_on_1lakh).toLocaleString("en-IN")}
                </td>
                <td>
                  <div
                    className="confidence-meter"
                    style={{
                      background: `conic-gradient(${r.confidence_score >= 0.65 ? "#10b981" : "#f59e0b"} ${r.confidence_score * 360}deg, #1f2937 0)`,
                    }}
                  >
                    <div className="w-9 h-9 rounded-full bg-[var(--bg-card)] flex items-center justify-center text-xs font-bold">
                      {Math.round(r.confidence_score * 100)}
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// TODAY'S TOP TRADE (HERO CARD)
// ═══════════════════════════════════════════════════════════════

function TopTradeCard({ trade }) {
  if (!trade) return null;

  return (
    <div className="glass-card p-6 mb-6 relative overflow-hidden animate-fade-in">
      <div className="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-indigo-500/10 to-transparent rounded-bl-full" />
      <div className="relative">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-1 rounded">
            ⭐ Top Setup Today
          </span>
        </div>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-2xl font-bold text-white">{trade.symbol.replace(".NS", "")}</h3>
            <p className="text-sm text-[var(--text-muted)]">{trade.name}</p>
            <span className={trade.direction === "bullish" ? "badge-bullish" : "badge-bearish"}>
              {trade.pattern?.name}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-xs text-[var(--text-muted)] mb-1">Entry</p>
              <p className="text-lg font-bold">₹{trade.entry?.toLocaleString("en-IN")}</p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-muted)] mb-1">Target</p>
              <p className="text-lg font-bold text-green-400">₹{trade.target?.toLocaleString("en-IN")}</p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-muted)] mb-1">Probability</p>
              <p className="text-lg font-bold text-indigo-400">{trade.probability}%</p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-muted)] mb-1">Profit (₹1L)</p>
              <p className="text-lg font-bold text-green-400">₹{Math.round(trade.profit_on_1lakh).toLocaleString("en-IN")}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN DASHBOARD PAGE
// ═══════════════════════════════════════════════════════════════

export default function Dashboard() {
  const [scanStatus, setScanStatus] = useState(null);
  const [results, setResults] = useState([]);
  const [isScanning, setIsScanning] = useState(false);
  const [sectors, setSectors] = useState([]);
  const [filters, setFilters] = useState({});
  const [lastScanTime, setLastScanTime] = useState(null);
  const pollingRef = useRef(null);

  // Poll scanner status
  const pollStatus = useCallback(async () => {
    try {
      const status = await getScanStatus();
      setScanStatus(status);

      if (status.is_running) {
        // Fetch intermediate results while scanning
        const res = await getScanResults(filters);
        setResults(res.results || []);
      } else if (isScanning) {
        // Scan just finished
        setIsScanning(false);
        const res = await getScanResults(filters);
        setResults(res.results || []);
        setLastScanTime(new Date().toLocaleTimeString());
        clearInterval(pollingRef.current);
      }
    } catch (err) {
      console.error("Status poll error:", err);
    }
  }, [isScanning, filters]);

  // Start scan
  const handleStartScan = async () => {
    try {
      setIsScanning(true);
      setResults([]);
      await startScan({ test: false, minConfidence: 0.40 });

      // Start polling
      pollingRef.current = setInterval(pollStatus, 2000);
    } catch (err) {
      console.error("Scan start error:", err);
      setIsScanning(false);
    }
  };

  // Apply filters
  useEffect(() => {
    if (!isScanning && results.length > 0) {
      getScanResults(filters).then((res) => setResults(res.results || []));
    }
  }, [filters]);

  // Cleanup
  useEffect(() => {
    // Load initial state
    getScanStatus().then((status) => {
      setScanStatus(status);
      if (status.is_running) {
        setIsScanning(true);
        pollingRef.current = setInterval(pollStatus, 2000);
      } else {
        // Load previous results if any
        getScanResults().then((res) => {
          if (res.results?.length > 0) {
            setResults(res.results);
          }
        }).catch(() => { });
      }
    }).catch(() => { });

    return () => clearInterval(pollingRef.current);
  }, []);

  const topTrade = results.length > 0 ? results[0] : null;

  return (
    <div>
      {/* Header section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Swing Trading Scanner
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Scan all NSE stocks for high-probability swing trading setups
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastScanTime && (
            <span className="text-xs text-[var(--text-muted)]">Last scan: {lastScanTime}</span>
          )}
          <button
            onClick={handleStartScan}
            disabled={isScanning}
            className="btn-gradient flex items-center gap-2"
          >
            {isScanning ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <span>🔍</span>
                Run Scanner
              </>
            )}
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total Scanned"
          value={scanStatus?.scanned_count || 0}
          icon="📈"
          color="text-blue-400"
        />
        <StatCard
          label="Opportunities"
          value={scanStatus?.passed_count || results.length}
          icon="🎯"
          color="text-green-400"
        />
        <StatCard
          label="Scan Time"
          value={scanStatus?.elapsed_seconds ? `${scanStatus.elapsed_seconds}s` : "—"}
          icon="⚡"
          color="text-amber-400"
        />
        <StatCard
          label="Win Rate (Avg)"
          value={results.length > 0 ? `${Math.round(results.reduce((a, r) => a + r.probability, 0) / results.length)}%` : "—"}
          icon="🏆"
          color="text-purple-400"
        />
      </div>

      {/* Scanner progress */}
      <ScannerProgress status={scanStatus} />

      {/* Top trade hero */}
      <TopTradeCard trade={topTrade} />

      {/* Filters */}
      <FilterBar filters={filters} setFilters={setFilters} sectors={sectors} />

      {/* Results table */}
      <ResultsTable results={results} />
    </div>
  );
}
