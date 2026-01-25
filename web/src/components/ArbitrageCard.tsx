"use client"

import { useState } from 'react'
import Link from 'next/link'
import { CalculatorModal, CalculatorData } from './CalculatorModal'
import { OddsChart } from './OddsChart'
import { getLocalizedTeamName } from '@/utils/teamNames'

// Generate URL-friendly slug from team name
function generateTeamSlug(teamName: string): string {
  return teamName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

// Liquidity indicator component
function LiquidityBadge({ liquidity }: { liquidity: number | null | undefined }) {
  if (liquidity === null || liquidity === undefined) {
    return null
  }

  // Format liquidity value
  const formatLiq = (val: number) => {
    if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`
    if (val >= 1000) return `$${(val / 1000).toFixed(0)}k`
    return `$${val.toFixed(0)}`
  }

  if (liquidity >= 10000) {
    return (
      <span className="text-[10px] text-[#3fb950] bg-[#3fb950]/15 px-1.5 py-0.5 rounded whitespace-nowrap">
        🟢 {formatLiq(liquidity)}
      </span>
    )
  } else if (liquidity >= 1000) {
    return (
      <span className="text-[10px] text-[#d29922] bg-[#d29922]/15 px-1.5 py-0.5 rounded whitespace-nowrap">
        🟡 {formatLiq(liquidity)}
      </span>
    )
  } else {
    return (
      <span className="text-[10px] text-[#f85149] bg-[#f85149]/15 px-1.5 py-0.5 rounded whitespace-nowrap">
        🔴 {formatLiq(liquidity)}
      </span>
    )
  }
}

interface ArbitrageCardProps {
  teamName: string
  sportType?: string
  web2Odds: number | null
  sourceBookmaker: string | null
  sourceUrl: string | null
  polymarketPrice: number | null
  polymarketUrl: string | null
  ev: number | null
  liquidity?: number | null
}

export function ArbitrageCard({
  teamName,
  sportType = 'nba',
  web2Odds,
  sourceBookmaker,
  sourceUrl,
  polymarketPrice,
  polymarketUrl,
  ev,
  liquidity,
}: ArbitrageCardProps) {
  const [showCalculator, setShowCalculator] = useState(false)

  const txt = {
    valueBet: 'Value Bet',
    evDiff: 'EV Diff',
    liquidity: 'Liquidity',
    betOnPoly: 'Bet on Polymarket',
    viewOnPoly: 'View on Polymarket',
    noPolyData: 'No Polymarket Data',
    analysis: 'Analysis & Chat',
  }

  const localTeamName = getLocalizedTeamName(teamName)

  // Normalize probability helper (defined early for calculatorData)
  const normalizeProb = (value: number | null): number | null => {
    if (value === null) return null
    return value > 1 ? value / 100 : value
  }

  // Calculator data - normalize values to ensure 0-1 probability format
  const calculatorData: CalculatorData = {
    teamName,
    web2Odds: normalizeProb(web2Odds),
    polymarketPrice: normalizeProb(polymarketPrice),
    sourceBookmaker,
    liquidityUsdc: liquidity,
  }

  // 判断是否为价值投注机会 (|EV| >= 5%)
  const isArbitrage = ev !== null && Math.abs(ev) >= 5
  // 判断方向：正EV表示Web2低估（应该买Polymarket），负EV表示Web2高估（应该卖Polymarket）
  const isPositiveEV = ev !== null && ev > 0

  // 格式化百分比显示 (handles both percentage and probability formats)
  const formatPercent = (value: number | null) => {
    if (value === null) return 'N/A'
    // Normalize: if > 1, it's percentage, else it's probability
    const normalized = value > 1 ? value / 100 : value
    return `${(normalized * 100).toFixed(1)}%`
  }

  const formatEV = (value: number | null) => {
    if (value === null) return 'N/A'
    const sign = value > 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  // 显示的 bookmaker 名称
  const bookmakerDisplay = sourceBookmaker || 'Trad Bookie'

  return (
    <div
      className={`
        relative p-4 rounded-lg border transition-all duration-200
        ${isArbitrage
          ? 'bg-[#0d1f0d] border-[#3fb950] arbitrage-card'
          : 'bg-[#161b22] border-[#30363d] hover:border-[#8b949e]'
        }
      `}
    >
      {/* Value Bet Badge - Show when EV >= 5% */}
      {isArbitrage && (
        <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-[#58a6ff] text-white text-xs font-bold rounded-full">
          {txt.valueBet}
        </div>
      )}

      {/* Team Name */}
      <h3 className="text-lg font-semibold text-[#e6edf3] mb-3 pr-16">
        {localTeamName}
      </h3>

      {/* Odds Comparison */}
      <div className="space-y-2 mb-4">
        {/* Bookmaker Odds */}
        <div className="flex items-center text-sm">
          <div className="flex-1">
            {sourceUrl ? (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#d29922] hover:text-[#f0b429] hover:underline"
              >
                {bookmakerDisplay}
              </a>
            ) : (
              <span className="text-[#8b949e]">{bookmakerDisplay}</span>
            )}
          </div>
          <span className="text-[#e6edf3] font-mono w-16 text-right">
            {formatPercent(web2Odds)}
          </span>
        </div>

        {/* Polymarket Price */}
        <div className="flex items-center text-sm">
          <div className="flex-1">
            <span className="text-[#58a6ff]">Polymarket</span>
          </div>
          <span className="text-[#58a6ff] font-mono w-16 text-right">
            {formatPercent(polymarketPrice)}
          </span>
        </div>

        {/* Divider */}
        <div className="border-t border-[#30363d] my-2"></div>

        {/* EV Display */}
        <div className="flex items-center">
          <span className="text-[#8b949e] text-sm flex-1">{txt.evDiff}</span>
          <span
            className={`
              font-mono font-bold text-lg w-16 text-right
              ${ev === null
                ? 'text-[#8b949e]'
                : isArbitrage
                  ? isPositiveEV
                    ? 'text-[#3fb950]'  // 正EV用绿色
                    : 'text-[#f85149]'  // 负EV用红色
                  : 'text-[#d29922]'    // 非套利用橙色
              }
            `}
          >
            {formatEV(ev)}
          </span>
        </div>

        {/* Liquidity Display */}
        {liquidity !== null && liquidity !== undefined && (
          <div className="flex items-center">
            <span className="text-[#8b949e] text-sm flex-1">{txt.liquidity}</span>
            <LiquidityBadge liquidity={liquidity} />
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {polymarketUrl ? (
        <div className="flex gap-2">
          <a
            href={polymarketUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={`
              flex-1 py-2 px-4 rounded text-center text-sm font-medium
              transition-colors duration-200
              ${isArbitrage
                ? 'bg-[#3fb950] hover:bg-[#2ea043] text-black'
                : 'bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d]'
              }
            `}
          >
            {isArbitrage ? txt.betOnPoly : txt.viewOnPoly}
          </a>
          <button
            onClick={() => setShowCalculator(true)}
            className="px-3 py-2 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded transition-colors border border-[#30363d]"
            title="Open Calculator"
          >
            🧮
          </button>
        </div>
      ) : (
        <div className="w-full py-2 px-4 rounded text-center text-sm text-[#8b949e] bg-[#21262d] border border-[#30363d]">
          {txt.noPolyData}
        </div>
      )}

      {/* AI Analysis Link */}
      <Link
        href={`/match/championship-${sportType}-${generateTeamSlug(teamName)}?from=${sportType === 'nba' ? 'nba-championship' : 'worldcup'}`}
        className="mt-2 flex items-center justify-center gap-2 py-2 px-3 bg-[#1f6feb]/20 hover:bg-[#1f6feb]/30 text-[#58a6ff] text-sm font-medium rounded-md transition-colors border border-[#1f6feb]/40"
      >
        <span>🤖</span>
        <span>{txt.analysis}</span>
      </Link>

      {/* History Chart */}
      <OddsChart
        eventId={teamName}
        eventType="championship"
        sportType={sportType}
        teamName={teamName}
      />

      {/* Calculator Modal */}
      <CalculatorModal
        isOpen={showCalculator}
        onClose={() => setShowCalculator(false)}
        data={calculatorData}
        type="championship"
      />
    </div>
  )
}
