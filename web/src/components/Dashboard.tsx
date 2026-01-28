"use client"

import { useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
// ArbitrageCard removed - now using table components
import { MatchCard } from './MatchCard'
import { FIFAMarketTable } from './FIFAMarketTable'
import { NBAMarketTable } from './NBAMarketTable'

// 市场数据类型 (冠军盘口)
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

// 每日比赛类型
export interface DailyMatchItem {
  id: number
  match_id: string
  home_team: string
  away_team: string
  commence_time: Date
  web2_home_odds: number | null
  web2_away_odds: number | null
  web2_draw_odds: number | null  // Soccer 3-way
  poly_home_price: number | null
  poly_away_price: number | null
  poly_draw_price: number | null  // Soccer 3-way
  source_bookmaker: string | null
  source_url: string | null
  polymarket_url: string | null
  ai_analysis: string | null
  analysis_timestamp: Date | null
  liquidity_home: number | null
  liquidity_away: number | null
  liquidity_draw: number | null  // Soccer 3-way
  sport_type?: string  // 'nba' | 'epl' | 'ucl'
}

interface DashboardProps {
  worldCupMarkets: MarketItem[]
  nbaMarkets: MarketItem[]
  dailyMatches: DailyMatchItem[]  // NBA daily matches
  eplMatches: DailyMatchItem[]    // EPL daily matches
  uclMatches: DailyMatchItem[]    // UCL daily matches
  stats: {
    totalOpportunities: number
    arbitrageCount: number
    dailyMatchCount: number
    eplMatchCount: number
    uclMatchCount: number
    lastUpdate: string
  }
}

// 一级导航类型
type SportType = 'worldcup' | 'nba' | 'soccer'
// 二级导航类型
type NbaSubTab = 'daily' | 'championship'
type FifaSubTab = 'championship' // 将来可添加: 'group_winners' | 'daily'
type SoccerSubTab = 'epl' | 'ucl'

/**
 * 获取比赛的优先级分数（用于排序）
 * - Tier 1 (3分): Web2 和 Polymarket 都有数据 - 最核心的套利机会
 * - Tier 2 (2分): 仅 Polymarket 有数据 - Web3 领先于 Web2
 * - Tier 3 (1分): 仅 Web2 有数据 - 等待上链的比赛
 * - Tier 0 (0分): 两边都没数据
 */
function getMatchPriority(match: DailyMatchItem): number {
  const hasWeb2 = match.web2_home_odds != null && match.web2_away_odds != null
  const hasPoly = match.poly_home_price != null && match.poly_away_price != null

  if (hasWeb2 && hasPoly) return 3  // 双边齐全 - 最优先
  if (!hasWeb2 && hasPoly) return 2 // 仅 Polymarket - 次优先
  if (hasWeb2 && !hasPoly) return 1 // 仅 Web2 - 最后
  return 0                           // 都没有
}

export function Dashboard({ worldCupMarkets, nbaMarkets, dailyMatches, eplMatches, uclMatches, stats }: DashboardProps) {
  // Use URL as the single source of truth for tab state
  const searchParams = useSearchParams()
  const router = useRouter()

  // Read tab state directly from URL (not useState)
  const tab = searchParams.get('tab')
  const sub = searchParams.get('sub')
  const activeSport: SportType = tab === 'nba' ? 'nba' : tab === 'soccer' ? 'soccer' : 'worldcup'
  const nbaSubTab: NbaSubTab = sub === 'daily' ? 'daily' : 'championship'
  const fifaSubTab: FifaSubTab = 'championship' // 目前只有championship，将来可扩展
  const soccerSubTab: SoccerSubTab = sub === 'ucl' ? 'ucl' : 'epl'

  // Only local UI state uses useState
  const [hideLowOdds, setHideLowOdds] = useState(true)
  const [showBanner, setShowBanner] = useState(true)

  const bannerText = 'Beta Version. Odds may be delayed. Always verify on official platforms.'

  // Navigation handlers - update URL instead of state
  const setActiveSport = (sport: SportType) => {
    if (sport === 'nba') {
      router.push('/?tab=nba&sub=championship', { scroll: false })
    } else if (sport === 'soccer') {
      router.push('/?tab=soccer&sub=epl', { scroll: false })
    } else {
      router.push('/?tab=worldcup&sub=championship', { scroll: false })
    }
  }

  const setNbaSubTab = (subTab: NbaSubTab) => {
    router.push(`/?tab=nba&sub=${subTab}`, { scroll: false })
  }

  const setFifaSubTab = (subTab: FifaSubTab) => {
    router.push(`/?tab=worldcup&sub=${subTab}`, { scroll: false })
  }

  const setSoccerSubTab = (subTab: SoccerSubTab) => {
    router.push(`/?tab=soccer&sub=${subTab}`, { scroll: false })
  }

  // 每日比赛排序：优先显示双边齐全的套利机会
  const sortedDailyMatches = [...dailyMatches].sort(
    (a, b) => getMatchPriority(b) - getMatchPriority(a)
  )
  const sortedEplMatches = [...eplMatches].sort(
    (a, b) => getMatchPriority(b) - getMatchPriority(a)
  )
  const sortedUclMatches = [...uclMatches].sort(
    (a, b) => getMatchPriority(b) - getMatchPriority(a)
  )

  return (
    <main className="min-h-screen p-6 pt-16 sm:pt-6">
      {/* Warning Banner - inline width */}
      {showBanner && (
        <div className="mb-4 -mt-2 bg-[#d29922]/20 border border-[#d29922]/40 rounded-lg px-4 py-3 flex items-center gap-3 w-fit">
          <div className="flex items-center gap-2 text-sm text-[#d29922]">
            <span>⚠️</span>
            <span>{bannerText}</span>
          </div>
          <button
            onClick={() => setShowBanner(false)}
            className="text-[#d29922] hover:text-[#f0b429] p-1 transition-colors"
            aria-label="Dismiss banner"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Header */}
      <header className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">
              PolyDelta
            </h1>
            <p className="text-[#8b949e] mt-1 text-sm sm:text-base">Discover cross-market arbitrage opportunities</p>
          </div>
          <div className="flex items-center gap-4 sm:gap-6">
            {/* Stats */}
            <div className="flex gap-4 sm:gap-6 text-sm">
              <div className="text-center">
                <div className="text-xl sm:text-2xl font-bold text-[#58a6ff]">{stats.dailyMatchCount}</div>
                <div className="text-[#8b949e] text-xs sm:text-sm">Today&apos;s Games</div>
              </div>
              <div className="text-center">
                <div className="text-xl sm:text-2xl font-bold text-[#d29922]">{stats.totalOpportunities}</div>
                <div className="text-[#8b949e] text-xs sm:text-sm">Champions</div>
              </div>
              <div className="text-center">
                <div className="text-xl sm:text-2xl font-bold text-[#3fb950]">{stats.arbitrageCount}</div>
                <div className="text-[#8b949e] text-xs sm:text-sm">Arbitrage</div>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-2 text-xs text-[#8b949e]">
          Last Updated: {stats.lastUpdate}
        </div>
      </header>

      {/* 一级导航 - Sport Type */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex gap-1 sm:gap-2 p-1 bg-[#161b22] rounded-lg">
          <button
            onClick={() => setActiveSport('worldcup')}
            className={`
              flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium
              transition-all duration-200
              ${activeSport === 'worldcup'
                ? 'bg-[#3fb950] text-black'
                : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
              }
            `}
          >
            <span>⚽</span>
            <span className="hidden sm:inline">FIFA World Cup</span>
            <span className="sm:hidden">FIFA</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${activeSport === 'worldcup' ? 'bg-black/20' : 'bg-[#30363d]'}`}>
              {worldCupMarkets.length}
            </span>
          </button>
          <button
            onClick={() => setActiveSport('nba')}
            className={`
              flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium
              transition-all duration-200
              ${activeSport === 'nba'
                ? 'bg-[#58a6ff] text-white'
                : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
              }
            `}
          >
            <span>🏀</span>
            <span>NBA</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${activeSport === 'nba' ? 'bg-white/20' : 'bg-[#30363d]'}`}>
              {nbaMarkets.length + dailyMatches.length}
            </span>
          </button>
          <button
            onClick={() => setActiveSport('soccer')}
            className={`
              flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-4 py-2 rounded-md text-xs sm:text-sm font-medium
              transition-all duration-200
              ${activeSport === 'soccer'
                ? 'bg-[#d29922] text-black'
                : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
              }
            `}
          >
            <span>⚽</span>
            <span className="hidden sm:inline">Soccer Leagues</span>
            <span className="sm:hidden">Soccer</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${activeSport === 'soccer' ? 'bg-black/20' : 'bg-[#30363d]'}`}>
              {eplMatches.length + uclMatches.length}
            </span>
          </button>
        </div>
      </div>

      {/* 二级导航 - NBA Sub-tabs (仅在 NBA 时显示) */}
      {activeSport === 'nba' && (
        <div className="flex items-center gap-4 mb-6">
          <div className="flex gap-2 p-1 bg-[#0d1117] rounded-lg">
            <button
              onClick={() => setNbaSubTab('daily')}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
                transition-all duration-200
                ${nbaSubTab === 'daily'
                  ? 'bg-[#58a6ff] text-white'
                  : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
                }
              `}
            >
              <span>📅</span>
              <span>Daily Matches</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${nbaSubTab === 'daily' ? 'bg-white/20' : 'bg-[#30363d]'}`}>
                {dailyMatches.length}
              </span>
            </button>
            <button
              onClick={() => setNbaSubTab('championship')}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
                transition-all duration-200
                ${nbaSubTab === 'championship'
                  ? 'bg-[#d29922] text-black'
                  : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
                }
              `}
            >
              <span>🏆</span>
              <span>Championship</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${nbaSubTab === 'championship' ? 'bg-black/20' : 'bg-[#30363d]'}`}>
                {nbaMarkets.length}
              </span>
            </button>
          </div>

          {/* Hide < 1% Toggle (仅在 Championship 时显示) */}
          {nbaSubTab === 'championship' && (
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={hideLowOdds}
                  onChange={(e) => setHideLowOdds(e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-10 h-5 rounded-full transition-colors duration-200 ${hideLowOdds ? 'bg-[#3fb950]' : 'bg-[#30363d]'}`} />
                <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${hideLowOdds ? 'translate-x-5' : 'translate-x-0'}`} />
              </div>
              <span className="text-sm text-[#8b949e]">Hide &lt; 1%</span>
            </label>
          )}
        </div>
      )}

      {/* 二级导航 - FIFA Sub-tabs */}
      {activeSport === 'worldcup' && (
        <div className="flex items-center gap-4 mb-6">
          <div className="flex gap-2 p-1 bg-[#0d1117] rounded-lg">
            <button
              onClick={() => setFifaSubTab('championship')}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
                transition-all duration-200
                ${fifaSubTab === 'championship'
                  ? 'bg-[#3fb950] text-black'
                  : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
                }
              `}
            >
              <span>🏆</span>
              <span>Championship</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${fifaSubTab === 'championship' ? 'bg-black/20' : 'bg-[#30363d]'}`}>
                {worldCupMarkets.length}
              </span>
            </button>
            {/* 将来可在此添加更多sub-tabs:
            <button onClick={() => setFifaSubTab('group_winners')}>
              <span>📊</span>
              <span>Group Winners</span>
            </button>
            <button onClick={() => setFifaSubTab('daily')}>
              <span>📅</span>
              <span>Daily Matches</span>
            </button>
            */}
          </div>

          {/* Hide < 1% Toggle */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <div className="relative">
              <input
                type="checkbox"
                checked={hideLowOdds}
                onChange={(e) => setHideLowOdds(e.target.checked)}
                className="sr-only"
              />
              <div className={`w-10 h-5 rounded-full transition-colors duration-200 ${hideLowOdds ? 'bg-[#3fb950]' : 'bg-[#30363d]'}`} />
              <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 ${hideLowOdds ? 'translate-x-5' : 'translate-x-0'}`} />
            </div>
            <span className="text-sm text-[#8b949e]">Hide &lt; 1%</span>
          </label>
        </div>
      )}

      {/* 二级导航 - Soccer Sub-tabs (EPL/UCL) */}
      {activeSport === 'soccer' && (
        <div className="flex items-center gap-4 mb-6">
          <div className="flex gap-2 p-1 bg-[#0d1117] rounded-lg">
            <button
              onClick={() => setSoccerSubTab('epl')}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
                transition-all duration-200
                ${soccerSubTab === 'epl'
                  ? 'bg-[#d29922] text-black'
                  : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
                }
              `}
            >
              <span>🏴󠁧󠁢󠁥󠁮󠁧󠁿</span>
              <span>Premier League</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${soccerSubTab === 'epl' ? 'bg-black/20' : 'bg-[#30363d]'}`}>
                {eplMatches.length}
              </span>
            </button>
            <button
              onClick={() => setSoccerSubTab('ucl')}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
                transition-all duration-200
                ${soccerSubTab === 'ucl'
                  ? 'bg-[#1f6feb] text-white'
                  : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
                }
              `}
            >
              <span>⭐</span>
              <span>Champions League</span>
              <span className={`px-1.5 py-0.5 rounded text-xs ${soccerSubTab === 'ucl' ? 'bg-white/20' : 'bg-[#30363d]'}`}>
                {uclMatches.length}
              </span>
            </button>
          </div>
        </div>
      )}

      {/* ========== FIFA Championship Content ========== */}
      {activeSport === 'worldcup' && fifaSubTab === 'championship' && (
        <FIFAMarketTable
          markets={worldCupMarkets}
          hideLowOdds={hideLowOdds}
        />
      )}

      {/* 将来可在此添加其他FIFA sub-tabs的内容:
      {activeSport === 'worldcup' && fifaSubTab === 'group_winners' && (
        <section>
          Group Winners content here...
        </section>
      )}

      {activeSport === 'worldcup' && fifaSubTab === 'daily' && (
        <section>
          Daily matches content here...
        </section>
      )}
      */}

      {/* ========== NBA Daily Matches Content ========== */}
      {activeSport === 'nba' && nbaSubTab === 'daily' && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">📅</span>
            <h2 className="text-xl font-bold text-[#e6edf3]">NBA Daily Matches</h2>
            <span className="px-2 py-0.5 bg-[#30363d] rounded text-xs text-[#8b949e]">
              {dailyMatches.length} games
            </span>
          </div>

          {sortedDailyMatches.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedDailyMatches.map((match) => (
                <MatchCard
                  key={match.id}
                  matchId={match.match_id}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  commenceTime={new Date(match.commence_time)}
                  web2HomeOdds={match.web2_home_odds}
                  web2AwayOdds={match.web2_away_odds}
                  polyHomePrice={match.poly_home_price}
                  polyAwayPrice={match.poly_away_price}
                  sourceBookmaker={match.source_bookmaker}
                  sourceUrl={match.source_url}
                  polymarketUrl={match.polymarket_url}
                  liquidityHome={match.liquidity_home}
                  liquidityAway={match.liquidity_away}
                  sportType="nba"
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-[#8b949e]">
              <p>No NBA games scheduled for today.</p>
              <p className="text-sm mt-2">Check back later for upcoming matches.</p>
            </div>
          )}
        </section>
      )}

      {/* ========== NBA Championship Content ========== */}
      {activeSport === 'nba' && nbaSubTab === 'championship' && (
        <NBAMarketTable
          markets={nbaMarkets}
          hideLowOdds={hideLowOdds}
        />
      )}

      {/* ========== EPL Daily Matches Content ========== */}
      {activeSport === 'soccer' && soccerSubTab === 'epl' && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">🏴󠁧󠁢󠁥󠁮󠁧󠁿</span>
            <h2 className="text-xl font-bold text-[#e6edf3]">Premier League Matches</h2>
            <span className="px-2 py-0.5 bg-[#30363d] rounded text-xs text-[#8b949e]">
              {eplMatches.length} games
            </span>
          </div>

          {sortedEplMatches.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedEplMatches.map((match) => (
                <MatchCard
                  key={match.id}
                  matchId={match.match_id}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  commenceTime={new Date(match.commence_time)}
                  web2HomeOdds={match.web2_home_odds}
                  web2AwayOdds={match.web2_away_odds}
                  web2DrawOdds={match.web2_draw_odds}
                  polyHomePrice={match.poly_home_price}
                  polyAwayPrice={match.poly_away_price}
                  polyDrawPrice={match.poly_draw_price}
                  sourceBookmaker={match.source_bookmaker}
                  sourceUrl={match.source_url}
                  polymarketUrl={match.polymarket_url}
                  liquidityHome={match.liquidity_home}
                  liquidityAway={match.liquidity_away}
                  liquidityDraw={match.liquidity_draw}
                  sportType="epl"
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-[#8b949e]">
              <p>No Premier League matches scheduled.</p>
              <p className="text-sm mt-2">Check back later for upcoming matches.</p>
            </div>
          )}
        </section>
      )}

      {/* ========== UCL Daily Matches Content ========== */}
      {activeSport === 'soccer' && soccerSubTab === 'ucl' && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">⭐</span>
            <h2 className="text-xl font-bold text-[#e6edf3]">Champions League Matches</h2>
            <span className="px-2 py-0.5 bg-[#30363d] rounded text-xs text-[#8b949e]">
              {uclMatches.length} games
            </span>
          </div>

          {sortedUclMatches.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sortedUclMatches.map((match) => (
                <MatchCard
                  key={match.id}
                  matchId={match.match_id}
                  homeTeam={match.home_team}
                  awayTeam={match.away_team}
                  commenceTime={new Date(match.commence_time)}
                  web2HomeOdds={match.web2_home_odds}
                  web2AwayOdds={match.web2_away_odds}
                  web2DrawOdds={match.web2_draw_odds}
                  polyHomePrice={match.poly_home_price}
                  polyAwayPrice={match.poly_away_price}
                  polyDrawPrice={match.poly_draw_price}
                  sourceBookmaker={match.source_bookmaker}
                  sourceUrl={match.source_url}
                  polymarketUrl={match.polymarket_url}
                  liquidityHome={match.liquidity_home}
                  liquidityAway={match.liquidity_away}
                  liquidityDraw={match.liquidity_draw}
                  sportType="ucl"
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-[#8b949e]">
              <p>No Champions League matches scheduled.</p>
              <p className="text-sm mt-2">Check back later for upcoming matches.</p>
            </div>
          )}
        </section>
      )}

      {/* Footer - Disclaimer */}
      <footer className="mt-12 pt-8 pb-6 bg-[#0d1117] border-t border-[#30363d]">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <p className="text-sm text-[#8b949e] mb-1">
            PolyDelta provides data for informational purposes only.
          </p>
          <p className="text-sm text-[#8b949e] mb-3">
            No financial advice provided. Betting involves risk.
          </p>
          <p className="text-xs text-[#484f58]">
            © {new Date().getFullYear()} PolyDelta. Not affiliated with any betting platform.
          </p>
        </div>
      </footer>
    </main>
  )
}
