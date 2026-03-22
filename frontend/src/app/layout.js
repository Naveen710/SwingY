import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata = {
  title: "SwingScanner — AI-Powered NSE Swing Trading Scanner",
  description: "Scan all NSE stocks for high-probability swing trading setups with chart pattern detection, technical indicators, and AI-powered probability scoring.",
  keywords: "NSE, swing trading, scanner, chart patterns, technical analysis, stock market India",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased min-h-screen">
        {/* Navigation */}
        <nav className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--bg-primary)]/90 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <a href="/" className="flex items-center gap-3 group">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/40 transition-all">
                  SS
                </div>
                <div>
                  <span className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                    SwingScanner
                  </span>
                  <span className="hidden sm:inline text-xs text-[var(--text-muted)] ml-2">
                    NSE Trading Scanner
                  </span>
                </div>
              </a>
              <div className="flex items-center gap-4">
                <a href="/" className="text-sm text-[var(--text-secondary)] hover:text-white transition-colors">
                  Dashboard
                </a>
                <a href="/watchlist" className="text-sm text-[var(--text-secondary)] hover:text-white transition-colors">
                  Watchlist
                </a>
              </div>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
