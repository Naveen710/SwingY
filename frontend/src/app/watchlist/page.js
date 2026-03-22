"use client";

import { useState, useEffect, useMemo } from "react";
import { getStocks } from "@/lib/api";
import Link from "next/link";

export default function WatchlistPage() {
  const [stocks, setStocks] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [sortBy, setSortBy] = useState("symbol");
  const [sortDir, setSortDir] = useState("asc");

  useEffect(() => {
    async function load() {
      try {
        const data = await getStocks();
        setStocks(data.stocks || []);
        setSectors(data.sectors || []);
      } catch (e) {
        console.error("Failed to load stocks", e);
      }
      setLoading(false);
    }
    load();
  }, []);

  const filtered = useMemo(() => {
    let list = [...stocks];

    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (s) =>
          s.symbol.toLowerCase().includes(q) ||
          s.name.toLowerCase().includes(q)
      );
    }

    if (sectorFilter) {
      list = list.filter((s) => s.sector === sectorFilter);
    }

    list.sort((a, b) => {
      const valA = a[sortBy] || "";
      const valB = b[sortBy] || "";
      const cmp = typeof valA === "string" ? valA.localeCompare(valB) : valA - valB;
      return sortDir === "asc" ? cmp : -cmp;
    });

    return list;
  }, [stocks, search, sectorFilter, sortBy, sortDir]);

  const handleSort = (col) => {
    if (sortBy === col) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortBy(col);
      setSortDir("asc");
    }
  };

  const sortIcon = (col) => {
    if (sortBy !== col) return "";
    return sortDir === "asc" ? " ↑" : " ↓";
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-10 w-72" />
        <div className="skeleton h-8 w-full" />
        {[...Array(10)].map((_, i) => (
          <div key={i} className="skeleton h-12 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Stock Universe
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Browse {stocks.length} NSE stocks — click any stock for detailed analysis
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
          <span className="inline-flex items-center gap-1 bg-indigo-500/10 text-indigo-400 px-3 py-1.5 rounded-lg font-medium">
            {filtered.length} stocks
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 mb-6">
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">🔍</span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by symbol or name..."
              className="w-full bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg pl-10 pr-4 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>

          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg px-3 py-2.5 text-sm text-[var(--text-primary)] focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>

          {(search || sectorFilter) && (
            <button
              onClick={() => {
                setSearch("");
                setSectorFilter("");
              }}
              className="text-xs text-[var(--text-muted)] hover:text-white transition-colors underline"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Sector chips */}
      {!sectorFilter && (
        <div className="flex flex-wrap gap-2 mb-6">
          {sectors.slice(0, 15).map((s) => {
            const count = stocks.filter((st) => st.sector === s).length;
            return (
              <button
                key={s}
                onClick={() => setSectorFilter(s)}
                className="text-xs bg-[var(--bg-card)] border border-[var(--border)] hover:border-indigo-500/50 text-[var(--text-secondary)] hover:text-white px-3 py-1.5 rounded-full transition-all duration-200"
              >
                {s}
                <span className="ml-1 text-[var(--text-muted)]">({count})</span>
              </button>
            );
          })}
          {sectors.length > 15 && (
            <span className="text-xs text-[var(--text-muted)] self-center">
              +{sectors.length - 15} more
            </span>
          )}
        </div>
      )}

      {/* Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th className="cursor-pointer" onClick={() => handleSort("symbol")}>
                  Symbol{sortIcon("symbol")}
                </th>
                <th className="cursor-pointer" onClick={() => handleSort("name")}>
                  Company{sortIcon("name")}
                </th>
                <th className="cursor-pointer" onClick={() => handleSort("sector")}>
                  Sector{sortIcon("sector")}
                </th>
                <th>Exchange</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12">
                    <p className="text-3xl mb-3">🔎</p>
                    <p className="text-[var(--text-secondary)]">No stocks match your filters</p>
                  </td>
                </tr>
              ) : (
                filtered.map((s, i) => (
                  <tr
                    key={s.symbol}
                    className="animate-fade-in"
                    style={{ animationDelay: `${Math.min(i * 20, 500)}ms` }}
                  >
                    <td>
                      <Link
                        href={`/stock/${s.symbol.replace(".NS", "")}`}
                        className="font-semibold text-white hover:text-indigo-400 transition-colors"
                      >
                        {s.symbol.replace(".NS", "")}
                      </Link>
                    </td>
                    <td className="text-[var(--text-secondary)]">{s.name}</td>
                    <td>
                      <span className="text-xs bg-[var(--bg-secondary)] border border-[var(--border)] px-2 py-1 rounded-md text-[var(--text-muted)]">
                        {s.sector}
                      </span>
                    </td>
                    <td className="text-[var(--text-muted)]">{s.exchange}</td>
                    <td>
                      <Link
                        href={`/stock/${s.symbol.replace(".NS", "")}`}
                        className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium"
                      >
                        Analyze →
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
