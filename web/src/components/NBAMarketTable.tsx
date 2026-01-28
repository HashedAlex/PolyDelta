"use client"

import { useState, useMemo } from 'react'
import Link from 'next/link'
import { CalculatorModal, CalculatorData } from './CalculatorModal'

// Generate URL-friendly slug from team name
function generateTeamSlug(teamName: string): string {
  return teamName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}


export interface MarketItem {
  id: number
  team_name: string
  web2_odds: number | null
  source_bookmaker: string | null
  source_url: string | null
  polymarket_price: number | null
  polymarket_url: string | null
  ev: number | null
  liquidity_usdc: number | null
}

interface NBAMarketTableProps {
  markets: MarketItem[]
  hideLowOdds: boolean
}

export function NBAMarketTable({ markets, hideLowOdds }: NBAMarketTableProps) {
  const [calculatorTeam, setCalculatorTeam] = useState<MarketItem | null>(null)
  const [showCalculator, setShowCalculator] = useState(false)

  // Filter and sort markets
  const filteredMarkets = useMemo(() => {
    let filtered = markets
    if (hideLowOdds) {
      filtered = markets.filter(item => (item.polymarket_price || 0) >= 0.01)
    }
    // Sort by polymarket price (win probability) descending
    return [...filtered].sort((a, b) => {
      const aPrice = a.polymarket_price ?? 0
      const bPrice = b.polymarket_price ?? 0
      return bPrice - aPrice
    })
  }, [markets, hideLowOdds])

  // Calculate total volume
  const totalVolume = useMemo(() => {
    return markets.reduce((sum, item) => sum + (item.liquidity_usdc || 0), 0)
  }, [markets])

  const formatVolume = (val: number) => {
    if (val >= 1000000) return `$${(val / 1000000).toFixed(2)}M`
    if (val >= 1000) return `$${(val / 1000).toFixed(0)}k`
    return `$${val.toFixed(0)}`
  }

  const formatPercent = (value: number | null) => {
    if (value === null) return '-'
    const normalized = value > 1 ? value / 100 : value
    return `${(normalized * 100).toFixed(1)}%`
  }

  const formatEV = (value: number | null) => {
    if (value === null) return '-'
    const sign = value > 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  const getEVColor = (ev: number | null) => {
    if (ev === null) return 'text-[#8b949e]'
    if (ev >= 5) return 'text-[#3fb950]'
    if (ev <= -5) return 'text-[#f85149]'
    return 'text-[#d29922]'
  }

  return (
    <section>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏆</span>
          <div>
            <h2 className="text-xl font-bold text-[#e6edf3]">NBA Championship 2025</h2>
            <p className="text-sm text-[#8b949e]">
              Total Liquidity: <span className="text-[#3fb950] font-medium">{formatVolume(totalVolume)}</span>
            </p>
          </div>
        </div>
        <div className="px-2 py-0.5 bg-[#30363d] rounded text-xs text-[#8b949e]">
          {hideLowOdds && filteredMarkets.length !== markets.length
            ? `${filteredMarkets.length} / ${markets.length} teams`
            : `${filteredMarkets.length} teams`}
        </div>
      </div>

      {/* Table */}
      {filteredMarkets.length > 0 ? (
        <div className="bg-[#161b22] rounded-lg border border-[#30363d] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#0d1117] text-[#8b949e] border-b border-[#30363d]">
                  <th className="text-left py-3 px-3 font-medium w-10">#</th>
                  <th className="text-left py-3 px-3 font-medium">Team</th>
                  <th className="text-center py-3 px-3 font-medium text-[#58a6ff]">Polymarket</th>
                  <th className="text-center py-3 px-3 font-medium text-[#d29922]">Bookie Odds</th>
                  <th className="text-center py-3 px-3 font-medium">EV</th>
                  <th className="text-center py-3 px-3 font-medium">Liquidity</th>
                  <th className="text-center py-3 px-3 font-medium">Tool</th>
                  <th className="text-center py-3 px-3 font-medium">Analysis</th>
                  <th className="text-center py-3 px-3 font-medium">Bet</th>
                </tr>
              </thead>
              <tbody>
                {filteredMarkets.map((item, index) => {
                  const isValueBet = item.ev !== null && item.ev >= 5
                  return (
                    <tr
                      key={item.id}
                      className={`border-b border-[#30363d]/50 hover:bg-[#21262d]/50 transition-colors ${
                        isValueBet ? 'bg-[#3fb950]/5' : ''
                      }`}
                    >
                      {/* Rank */}
                      <td className="py-3 px-3 text-[#8b949e] font-mono">{index + 1}</td>

                      {/* Team */}
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[#e6edf3]">{item.team_name}</span>
                          {isValueBet && (
                            <span className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] bg-[#58a6ff] text-white rounded font-bold">
                              Value Bet
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Polymarket */}
                      <td className="py-3 px-3 text-center font-mono text-[#58a6ff]">
                        {formatPercent(item.polymarket_price)}
                      </td>

                      {/* Bookie Odds */}
                      <td className="py-3 px-3 text-center">
                        <div className="flex flex-col items-center">
                          <span className="font-mono text-[#d29922]">{formatPercent(item.web2_odds)}</span>
                          {item.source_bookmaker && (
                            <span className="text-[10px] text-[#6e7681]">{item.source_bookmaker}</span>
                          )}
                        </div>
                      </td>

                      {/* EV */}
                      <td className={`py-3 px-3 text-center font-mono font-medium ${getEVColor(item.ev)}`}>
                        {formatEV(item.ev)}
                      </td>

                      {/* Liquidity */}
                      <td className="py-3 px-3 text-center">
                        {item.liquidity_usdc ? (
                          <span className={`text-xs px-2 py-1 rounded ${
                            item.liquidity_usdc >= 10000 ? 'bg-[#3fb950]/15 text-[#3fb950]' :
                            item.liquidity_usdc >= 1000 ? 'bg-[#d29922]/15 text-[#d29922]' :
                            'bg-[#f85149]/15 text-[#f85149]'
                          }`}>
                            {formatVolume(item.liquidity_usdc)}
                          </span>
                        ) : (
                          <span className="text-[#6e7681]">-</span>
                        )}
                      </td>

                      {/* Calculator Button */}
                      <td className="py-3 px-3 text-center">
                        <button
                          onClick={() => {
                            setCalculatorTeam(item)
                            setShowCalculator(true)
                          }}
                          className="px-2.5 py-1.5 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded-md transition-colors border border-[#30363d]"
                          title="Open Calculator"
                        >
                          🧮
                        </button>
                      </td>

                      {/* Analysis Link */}
                      <td className="py-3 px-3 text-center">
                        <Link
                          href={`/match/championship-nba-${generateTeamSlug(item.team_name)}?from=nba-championship`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#58a6ff] bg-[#58a6ff]/10 hover:bg-[#58a6ff]/20 border border-[#58a6ff]/30 rounded-md transition-colors"
                        >
                          <span>📊</span>
                          <span className="hidden sm:inline">View</span>
                        </Link>
                      </td>

                      {/* Bet on Polymarket Button */}
                      <td className="py-3 px-3 text-center">
                        {item.polymarket_url ? (
                          <a
                            href={item.polymarket_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-[#238636] hover:bg-[#2ea043] text-white rounded-md transition-colors"
                          >
                            <span className="hidden sm:inline">Bet</span>
                            <span>↗</span>
                          </a>
                        ) : (
                          <span className="text-[#6e7681] text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-[#8b949e]">
          No NBA Championship data available
        </div>
      )}

      {/* Calculator Modal */}
      {calculatorTeam && (
        <CalculatorModal
          isOpen={showCalculator}
          onClose={() => {
            setShowCalculator(false)
            setCalculatorTeam(null)
          }}
          data={{
            teamName: calculatorTeam.team_name,
            web2Odds: calculatorTeam.web2_odds,
            polymarketPrice: calculatorTeam.polymarket_price,
            sourceBookmaker: calculatorTeam.source_bookmaker,
            liquidityUsdc: calculatorTeam.liquidity_usdc,
          }}
          type="championship"
        />
      )}
    </section>
  )
}
