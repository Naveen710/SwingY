"use client";

import { useState, useEffect, useRef } from "react";
import { getStockDetail, getBacktest } from "@/lib/api";
import { useParams } from "next/navigation";
import Link from "next/link";

// ═══════════════════════════════════════════════════════════════
// SIMPLE CANDLESTICK CHART (SVG-based, no external deps)
// ═══════════════════════════════════════════════════════════════

function CandlestickChart({ chartData, emaData, patternLevels }) {
    const containerRef = useRef(null);

    if (!chartData || Object.keys(chartData).length === 0) {
        return (
            <div className="glass-card p-8 text-center">
                <p className="text-[var(--text-muted)]">No chart data available</p>
            </div>
        );
    }

    const entries = Object.entries(chartData).sort(([a], [b]) => a.localeCompare(b));
    const dates = entries.map(([d]) => d);
    const ohlcv = entries.map(([, v]) => v);

    // Calculate dimensions
    const width = 900;
    const height = 400;
    const margin = { top: 20, right: 60, bottom: 40, left: 10 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    const allHighs = ohlcv.map((d) => d.High);
    const allLows = ohlcv.map((d) => d.Low);
    const maxPrice = Math.max(...allHighs);
    const minPrice = Math.min(...allLows);
    const priceRange = maxPrice - minPrice;
    const padding = priceRange * 0.05;

    const scaleX = (i) => margin.left + (i / (entries.length - 1)) * chartWidth;
    const scaleY = (price) =>
        margin.top + ((maxPrice + padding - price) / (priceRange + 2 * padding)) * chartHeight;

    const candleWidth = Math.max(2, Math.min(8, chartWidth / entries.length - 1));

    return (
        <div ref={containerRef} className="glass-card p-4 overflow-x-auto">
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto" style={{ minWidth: 600 }}>
                {/* Grid lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
                    const price = minPrice - padding + (priceRange + 2 * padding) * (1 - frac);
                    const y = scaleY(price);
                    return (
                        <g key={frac}>
                            <line
                                x1={margin.left} y1={y} x2={width - margin.right} y2={y}
                                stroke="#1f2937" strokeWidth={1}
                            />
                            <text x={width - margin.right + 5} y={y + 4} fill="#6b7280" fontSize={10}>
                                ₹{Math.round(price)}
                            </text>
                        </g>
                    );
                })}

                {/* EMA lines */}
                {emaData && Object.entries(emaData).map(([emaName, emaVals]) => {
                    const emaColor = emaName === "EMA20" ? "#3b82f6" : emaName === "EMA50" ? "#f59e0b" : "#ef4444";
                    const points = dates
                        .map((d, i) => (emaVals[d] ? `${scaleX(i)},${scaleY(emaVals[d])}` : null))
                        .filter(Boolean)
                        .join(" ");
                    return (
                        <polyline
                            key={emaName}
                            points={points}
                            fill="none"
                            stroke={emaColor}
                            strokeWidth={1.5}
                            opacity={0.7}
                        />
                    );
                })}

                {/* Candlesticks */}
                {ohlcv.map((candle, i) => {
                    const x = scaleX(i);
                    const isGreen = candle.Close >= candle.Open;
                    const color = isGreen ? "#10b981" : "#ef4444";
                    const bodyTop = scaleY(Math.max(candle.Open, candle.Close));
                    const bodyBottom = scaleY(Math.min(candle.Open, candle.Close));
                    const bodyHeight = Math.max(1, bodyBottom - bodyTop);

                    return (
                        <g key={i}>
                            {/* Wick */}
                            <line
                                x1={x} y1={scaleY(candle.High)} x2={x} y2={scaleY(candle.Low)}
                                stroke={color} strokeWidth={1}
                            />
                            {/* Body */}
                            <rect
                                x={x - candleWidth / 2} y={bodyTop}
                                width={candleWidth} height={bodyHeight}
                                fill={isGreen ? color : color} stroke={color}
                                rx={1}
                            />
                        </g>
                    );
                })}

                {/* Pattern levels */}
                {patternLevels && Object.entries(patternLevels).map(([levelName, price]) => {
                    if (typeof price !== "number") return null;
                    const y = scaleY(price);
                    if (y < margin.top || y > height - margin.bottom) return null;
                    const color = levelName.includes("support") || levelName.includes("bottom") || levelName.includes("ema")
                        ? "#10b981"
                        : levelName.includes("breakout") || levelName.includes("resistance") || levelName.includes("pivot")
                            ? "#8b5cf6"
                            : "#f59e0b";
                    return (
                        <g key={levelName}>
                            <line
                                x1={margin.left} y1={y} x2={width - margin.right} y2={y}
                                stroke={color} strokeWidth={1} strokeDasharray="6,3" opacity={0.6}
                            />
                            <text x={margin.left + 5} y={y - 5} fill={color} fontSize={10} fontWeight="600">
                                {levelName}: ₹{Math.round(price)}
                            </text>
                        </g>
                    );
                })}

                {/* X-axis date labels */}
                {dates.filter((_, i) => i % Math.ceil(dates.length / 8) === 0).map((d, i) => {
                    const idx = dates.indexOf(d);
                    return (
                        <text
                            key={d}
                            x={scaleX(idx)}
                            y={height - 5}
                            fill="#6b7280"
                            fontSize={9}
                            textAnchor="middle"
                        >
                            {d.slice(5)}
                        </text>
                    );
                })}

                {/* Legend */}
                {emaData && (
                    <g>
                        {[
                            { name: "EMA20", color: "#3b82f6" },
                            { name: "EMA50", color: "#f59e0b" },
                            { name: "EMA200", color: "#ef4444" },
                        ].map((ema, i) => (
                            <g key={ema.name} transform={`translate(${margin.left + i * 80}, ${height - 22})`}>
                                <line x1={0} y1={0} x2={15} y2={0} stroke={ema.color} strokeWidth={2} />
                                <text x={18} y={4} fill="#9ca3af" fontSize={9}>{ema.name}</text>
                            </g>
                        ))}
                    </g>
                )}
            </svg>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════
// STOCK DETAIL PAGE
// ═══════════════════════════════════════════════════════════════

export default function StockDetail() {
    const params = useParams();
    const symbol = params.symbol;

    const [stock, setStock] = useState(null);
    const [backtest, setBacktest] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function load() {
            setLoading(true);
            try {
                const data = await getStockDetail(symbol);
                if (data.error) {
                    setError(data.error);
                } else {
                    setStock(data);
                    // Also fetch backtest
                    try {
                        const bt = await getBacktest(symbol);
                        setBacktest(bt);
                    } catch (e) {
                        console.log("Backtest not available", e);
                    }
                }
            } catch (e) {
                setError("Failed to load stock data");
            }
            setLoading(false);
        }
        if (symbol) load();
    }, [symbol]);

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="skeleton h-8 w-48" />
                <div className="skeleton h-[400px]" />
                <div className="grid grid-cols-2 gap-4">
                    <div className="skeleton h-32" />
                    <div className="skeleton h-32" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="glass-card p-12 text-center">
                <p className="text-4xl mb-4">❌</p>
                <p className="text-lg text-red-400">{error}</p>
                <Link href="/" className="text-sm text-indigo-400 hover:underline mt-4 inline-block">
                    ← Back to Dashboard
                </Link>
            </div>
        );
    }

    const signal = stock?.signal;
    const patterns = stock?.patterns || [];
    const indicators = stock?.indicators || {};
    const patternLevels = patterns.length > 0 ? patterns[0].key_levels : {};

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <Link href="/" className="text-sm text-indigo-400 hover:underline mb-2 inline-block">
                        ← Back to Dashboard
                    </Link>
                    <h1 className="text-3xl font-bold text-white">{symbol}</h1>
                    <p className="text-lg text-[var(--text-secondary)]">₹{stock?.current_price?.toLocaleString("en-IN")}</p>
                </div>
                {patterns.length > 0 && (
                    <span className={patterns[0].direction === "bullish" ? "badge-bullish text-lg px-4 py-2" : "badge-bearish text-lg px-4 py-2"}>
                        {patterns[0].name}
                    </span>
                )}
            </div>

            {/* Chart */}
            <CandlestickChart
                chartData={stock?.chart_data}
                emaData={stock?.ema_data}
                patternLevels={patternLevels}
            />

            {/* Trade Signal Card */}
            {signal && (
                <div className="glass-card p-6 animate-fade-in">
                    <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                        <span>🎯</span> Trade Setup
                    </h2>
                    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
                        <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-xl">
                            <p className="text-xs text-[var(--text-muted)] mb-1">Entry</p>
                            <p className="text-xl font-bold">₹{signal.entry?.toLocaleString("en-IN")}</p>
                        </div>
                        <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-xl">
                            <p className="text-xs text-[var(--text-muted)] mb-1">Stop Loss</p>
                            <p className="text-xl font-bold text-red-400">₹{signal.stop_loss?.toLocaleString("en-IN")}</p>
                        </div>
                        <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-xl">
                            <p className="text-xs text-[var(--text-muted)] mb-1">Target</p>
                            <p className="text-xl font-bold text-green-400">₹{signal.target?.toLocaleString("en-IN")}</p>
                        </div>
                        <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-xl">
                            <p className="text-xs text-[var(--text-muted)] mb-1">R:R</p>
                            <p className="text-xl font-bold text-amber-400">1:{signal.risk_reward}</p>
                        </div>
                        <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-xl">
                            <p className="text-xs text-[var(--text-muted)] mb-1">Probability</p>
                            <p className="text-xl font-bold text-indigo-400">{signal.probability}%</p>
                        </div>
                        <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-xl">
                            <p className="text-xs text-[var(--text-muted)] mb-1">Profit (₹1L)</p>
                            <p className="text-xl font-bold text-green-400">₹{Math.round(signal.profit_on_1lakh).toLocaleString("en-IN")}</p>
                        </div>
                        <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-xl">
                            <p className="text-xs text-[var(--text-muted)] mb-1">Est. Days</p>
                            <p className="text-xl font-bold text-amber-400">~{signal.estimated_days || "—"}d</p>
                        </div>
                    </div>

                    {/* Confluence Factors */}
                    {signal.confluence_factors?.length > 0 && (
                        <div className="mt-4 flex flex-wrap gap-2">
                            {signal.confluence_factors.map((f, i) => (
                                <span key={i} className="text-xs bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-1 rounded-md">
                                    {f}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Technical Indicators */}
            <div className="glass-card p-6">
                <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                    <span>📊</span> Technical Indicators
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                    {Object.entries(indicators).map(([key, val]) => {
                        if (val === null) return null;
                        let color = "text-white";
                        if (key === "RSI") {
                            color = val > 70 ? "text-red-400" : val < 30 ? "text-green-400" : "text-amber-400";
                        }
                        if (key === "Vol_Ratio") {
                            color = val > 1.5 ? "text-green-400" : "text-[var(--text-secondary)]";
                        }
                        return (
                            <div key={key} className="p-3 bg-[var(--bg-secondary)] rounded-xl">
                                <p className="text-xs text-[var(--text-muted)] mb-1">{key.replace(/_/g, " ")}</p>
                                <p className={`text-lg font-semibold ${color}`}>{typeof val === "number" ? val.toFixed(2) : val}</p>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Patterns Detected */}
            {patterns.length > 0 && (
                <div className="glass-card p-6">
                    <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                        <span>🔍</span> Detected Patterns
                    </h2>
                    <div className="space-y-3">
                        {patterns.map((p, i) => (
                            <div key={i} className="flex items-start justify-between p-4 bg-[var(--bg-secondary)] rounded-xl">
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={p.direction === "bullish" ? "badge-bullish" : "badge-bearish"}>
                                            {p.direction}
                                        </span>
                                        <span className="font-semibold">{p.name}</span>
                                    </div>
                                    <p className="text-sm text-[var(--text-muted)]">{p.description}</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-xs text-[var(--text-muted)]">Confidence</p>
                                    <p className="text-xl font-bold text-indigo-400">{Math.round(p.confidence * 100)}%</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Backtest Results */}
            {backtest?.strategies && (
                <div className="glass-card p-6">
                    <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                        <span>📈</span> Backtest Results
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {Object.entries(backtest.strategies).map(([stratName, stats]) => (
                            <div key={stratName} className="p-4 bg-[var(--bg-secondary)] rounded-xl">
                                <p className="font-semibold mb-3">{stratName}</p>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Total Trades</span>
                                        <span>{stats.total}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Win Rate</span>
                                        <span className={stats.win_rate >= 50 ? "text-green-400" : "text-red-400"}>
                                            {stats.win_rate}%
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Avg Return</span>
                                        <span className={stats.avg_return >= 0 ? "text-green-400" : "text-red-400"}>
                                            {stats.avg_return}%
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Profit Factor</span>
                                        <span className={stats.profit_factor >= 1.5 ? "text-green-400" : "text-amber-400"}>
                                            {stats.profit_factor}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-[var(--text-muted)]">Max Drawdown</span>
                                        <span className="text-red-400">-{stats.max_drawdown}%</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
