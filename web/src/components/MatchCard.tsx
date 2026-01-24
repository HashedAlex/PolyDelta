"use client"

import { useState } from 'react'
import Link from 'next/link'
import { CalculatorModal, CalculatorData } from './CalculatorModal'
import { OddsChart } from './OddsChart'
import { useLanguage } from '@/contexts/LanguageContext'
import { getLocalizedTeamName } from '@/utils/teamNames'

interface MatchCardProps {
  matchId?: string
  homeTeam: string
  awayTeam: string
  commenceTime: Date
  web2HomeOdds: number | null
  web2AwayOdds: number | null
  polyHomePrice: number | null
  polyAwayPrice: number | null
  sourceBookmaker: string | null
  sourceUrl: string | null
  polymarketUrl: string | null
  liquidityHome?: number | null
  liquidityAway?: number | null
}

// Liquidity indicator component
function LiquidityBadge({ liquidity }: { liquidity: number | null | undefined }) {
  if (liquidity === null || liquidity === undefined) {
    return null
  }

  // Format liquidity value
  const formatLiq = (val: number) => {
    if (val >= 1000) return `$${(val / 1000).toFixed(0)}k`
    return `$${val.toFixed(0)}`
  }

  if (liquidity >= 1000) {
    return (
      <span className="text-[10px] text-[#3fb950] bg-[#3fb950]/15 px-1 py-0.5 rounded whitespace-nowrap">
        🟢 {formatLiq(liquidity)}
      </span>
    )
  } else if (liquidity >= 200) {
    return (
      <span className="text-[10px] text-[#d29922] bg-[#d29922]/15 px-1 py-0.5 rounded whitespace-nowrap">
        🟡 {formatLiq(liquidity)}
      </span>
    )
  } else {
    return (
      <span className="text-[10px] text-[#f85149] bg-[#f85149]/15 px-1 py-0.5 rounded whitespace-nowrap">
        🔴 {formatLiq(liquidity)}
      </span>
    )
  }
}

function formatMatchTime(date: Date, lang: string = 'en'): string {
  const now = new Date()
  const matchDate = new Date(date)

  const isToday = matchDate.toDateString() === now.toDateString()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const isTomorrow = matchDate.toDateString() === tomorrow.toDateString()

  // 使用固定 locale 避免 hydration mismatch
  const timeStr = matchDate.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })

  if (isToday) {
    return lang === 'zh' ? `今天 ${timeStr}` : `Today ${timeStr}`
  } else if (isTomorrow) {
    return lang === 'zh' ? `明天 ${timeStr}` : `Tomorrow ${timeStr}`
  } else {
    const dateStr = matchDate.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en-US', {
      month: 'short',
      day: 'numeric'
    })
    return `${dateStr} ${timeStr}`
  }
}

function calculateEV(web2Odds: number | null, polyPrice: number | null): number | null {
  if (!web2Odds || !polyPrice || polyPrice === 0) return null
  return ((web2Odds - polyPrice) / polyPrice) * 100
}

export function MatchCard({
  matchId,
  homeTeam,
  awayTeam,
  commenceTime,
  web2HomeOdds,
  web2AwayOdds,
  polyHomePrice,
  polyAwayPrice,
  sourceBookmaker,
  sourceUrl,
  polymarketUrl,
  liquidityHome,
  liquidityAway,
}: MatchCardProps) {
  const [showCalculator, setShowCalculator] = useState(false)
  const { language } = useLanguage()

  // 翻译文本
  const txt = {
    arbitrage: language === 'zh' ? '套利' : 'Arbitrage',
    team: language === 'zh' ? '球队' : 'Team',
    tradOdds: language === 'zh' ? '传统赔率' : 'Trad Odds',
    ev: language === 'zh' ? '期望值' : 'EV',
    liquidity: language === 'zh' ? '深度' : 'Liquidity',
    betOnPoly: language === 'zh' ? '在 Polymarket 下注' : 'Bet on Polymarket',
    analysis: language === 'zh' ? 'AI 分析' : 'Analysis & Chat',
    polyNotAvailable: language === 'zh' ? 'Polymarket 暂未上线' : 'Polymarket not available yet',
  }

  const homeEV = calculateEV(web2HomeOdds, polyHomePrice)
  const awayEV = calculateEV(web2AwayOdds, polyAwayPrice)

  // 本地化球队名称
  const localHomeTeam = getLocalizedTeamName(homeTeam, language, 'nba')
  const localAwayTeam = getLocalizedTeamName(awayTeam, language, 'nba')

  // Calculate min liquidity for card dimming
  const minLiquidity = Math.min(
    liquidityHome ?? Infinity,
    liquidityAway ?? Infinity
  )
  const isIlliquid = minLiquidity < 200 && minLiquidity !== Infinity

  // Calculator data
  const calculatorData: CalculatorData = {
    homeTeam,
    awayTeam,
    web2HomeOdds,
    web2AwayOdds,
    polyHomePrice,
    polyAwayPrice,
    sourceBookmaker,
    liquidityHome,
    liquidityAway,
  }

  // 找到最大的 EV 值
  const maxEV = Math.max(
    Math.abs(homeEV || 0),
    Math.abs(awayEV || 0)
  )

  // 高亮颜色逻辑
  const hasArbitrage = maxEV >= 5
  const borderColor = hasArbitrage ? 'border-[#3fb950]' : 'border-[#30363d]'

  const hasPoly = polyHomePrice != null || polyAwayPrice != null

  return (
    <div className={`bg-[#161b22] rounded-lg p-4 border ${borderColor} hover:border-[#58a6ff] transition-colors ${isIlliquid ? 'opacity-60' : ''}`}>
      {/* Header - 比赛时间 */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-[#8b949e] bg-[#21262d] px-2 py-1 rounded flex items-center gap-1">
          <span>🌍</span>
          <span>{formatMatchTime(commenceTime, language)}</span>
        </span>
        {hasArbitrage && (
          <span className="text-xs text-[#3fb950] bg-[#3fb950]/10 px-2 py-1 rounded font-medium">
            {txt.arbitrage}
          </span>
        )}
      </div>

      {/* Teams - 单行横向展示 */}
      <div className="flex flex-row items-center gap-2 mb-4 min-w-0">
        <span className="text-base font-bold text-[#e6edf3] truncate" title={localHomeTeam}>
          {localHomeTeam}
        </span>
        <span className="text-xs text-[#6e7681] flex-shrink-0">vs</span>
        <span className="text-base font-bold text-[#e6edf3] truncate" title={localAwayTeam}>
          {localAwayTeam}
        </span>
      </div>

      {/* Odds Comparison Table */}
      <div className="bg-[#0d1117] rounded-lg p-3">
        <div className="grid grid-cols-5 gap-2 text-xs mb-2">
          <div className="text-[#8b949e]">{txt.team}</div>
          <div className="text-[#8b949e] text-center">
            {sourceBookmaker ? (
              sourceUrl ? (
                <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-[#d29922] hover:underline">
                  {sourceBookmaker}
                </a>
              ) : (
                <span className="text-[#d29922]">{sourceBookmaker}</span>
              )
            ) : (
              txt.tradOdds
            )}
          </div>
          <div className="text-[#8b949e] text-center">
            {polymarketUrl ? (
              <a href={polymarketUrl} target="_blank" rel="noopener noreferrer" className="text-[#58a6ff] hover:underline">
                Polymarket
              </a>
            ) : (
              "Polymarket"
            )}
          </div>
          <div className="text-[#8b949e] text-center">{txt.ev}</div>
          <div className="text-[#8b949e] text-center">{txt.liquidity}</div>
        </div>

        {/* Home Team Row */}
        <div className="grid grid-cols-5 gap-2 text-sm py-1.5 border-t border-[#30363d]">
          <div className="text-[#e6edf3] truncate" title={localHomeTeam}>
            {language === 'zh' ? localHomeTeam : homeTeam.split(' ').pop()}
          </div>
          <div className="text-center text-[#e6edf3]">
            {web2HomeOdds ? `${(web2HomeOdds * 100).toFixed(1)}%` : '-'}
          </div>
          <div className="text-center text-[#e6edf3]">
            {polyHomePrice ? `${(polyHomePrice * 100).toFixed(1)}%` : '-'}
          </div>
          <div className={`text-center font-medium ${
            homeEV && homeEV > 0 ? 'text-[#3fb950]' :
            homeEV && homeEV < 0 ? 'text-[#f85149]' :
            'text-[#8b949e]'
          }`}>
            {homeEV ? `${homeEV > 0 ? '+' : ''}${homeEV.toFixed(1)}%` : '-'}
          </div>
          <div className="flex justify-center">
            <LiquidityBadge liquidity={liquidityHome} />
          </div>
        </div>

        {/* Away Team Row */}
        <div className="grid grid-cols-5 gap-2 text-sm py-1.5 border-t border-[#30363d]">
          <div className="text-[#e6edf3] truncate" title={localAwayTeam}>
            {language === 'zh' ? localAwayTeam : awayTeam.split(' ').pop()}
          </div>
          <div className="text-center text-[#e6edf3]">
            {web2AwayOdds ? `${(web2AwayOdds * 100).toFixed(1)}%` : '-'}
          </div>
          <div className="text-center text-[#e6edf3]">
            {polyAwayPrice ? `${(polyAwayPrice * 100).toFixed(1)}%` : '-'}
          </div>
          <div className={`text-center font-medium ${
            awayEV && awayEV > 0 ? 'text-[#3fb950]' :
            awayEV && awayEV < 0 ? 'text-[#f85149]' :
            'text-[#8b949e]'
          }`}>
            {awayEV ? `${awayEV > 0 ? '+' : ''}${awayEV.toFixed(1)}%` : '-'}
          </div>
          <div className="flex justify-center">
            <LiquidityBadge liquidity={liquidityAway} />
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      {hasPoly && polymarketUrl && (
        <div className="mt-3 flex gap-2">
          <a
            href={polymarketUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium rounded-md transition-colors"
          >
            <span>{txt.betOnPoly}</span>
            <span>↗</span>
          </a>
          <button
            onClick={() => setShowCalculator(true)}
            className="px-3 py-2 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] rounded-md transition-colors border border-[#30363d]"
            title="Open Calculator"
          >
            🧮
          </button>
        </div>
      )}

      {/* AI Analysis Link */}
      {matchId && (
        <Link
          href={`/match/${matchId}?from=nba-daily`}
          className="mt-2 flex items-center justify-center gap-2 py-2 px-3 bg-[#1f6feb]/20 hover:bg-[#1f6feb]/30 text-[#58a6ff] text-sm font-medium rounded-md transition-colors border border-[#1f6feb]/40"
        >
          <span>🤖</span>
          <span>{txt.analysis}</span>
        </Link>
      )}

      {/* Fallback: No Polymarket data */}
      {!hasPoly && (
        <div className="mt-3 text-center text-xs text-[#8b949e] py-2">
          {txt.polyNotAvailable}
        </div>
      )}

      {/* History Chart (Home Team) */}
      {matchId && (
        <OddsChart
          eventId={`${matchId}_home`}
          eventType="daily"
          sportType="nba"
          teamName={`${homeTeam} (Home)`}
        />
      )}

      {/* Calculator Modal */}
      <CalculatorModal
        isOpen={showCalculator}
        onClose={() => setShowCalculator(false)}
        data={calculatorData}
        type="match"
      />
    </div>
  )
}
