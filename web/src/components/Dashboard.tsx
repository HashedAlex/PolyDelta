"use client"

import { useState } from 'react'
import { ArbitrageCard } from './ArbitrageCard'
import { MatchCard } from './MatchCard'

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
}

// 每日比赛类型
export interface DailyMatchItem {
  id: number
  home_team: string
  away_team: string
  commence_time: Date
  web2_home_odds: number | null
  web2_away_odds: number | null
  poly_home_price: number | null
  poly_away_price: number | null
  source_bookmaker: string | null
  source_url: string | null
  polymarket_url: string | null
}

interface DashboardProps {
  worldCupMarkets: MarketItem[]
  nbaMarkets: MarketItem[]
  dailyMatches: DailyMatchItem[]
  stats: {
    totalOpportunities: number
    arbitrageCount: number
    dailyMatchCount: number
    lastUpdate: string
  }
}

// 一级导航类型
type SportType = 'worldcup' | 'nba'
// 二级导航类型 (NBA only)
type NbaSubTab = 'daily' | 'championship'

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

/**
 * 冠军盘口排序：按 EV 降序，数据不全的排在最后
 * - Tier 1: 双边数据齐全，按 EV 从高到低
 * - Tier 2: 数据不全，排在最后
 */
function sortChampionMarkets(markets: MarketItem[]): MarketItem[] {
  return [...markets].sort((a, b) => {
    const aComplete = a.web2_odds != null && a.polymarket_price != null
    const bComplete = b.web2_odds != null && b.polymarket_price != null

    // 数据齐全的排前面
    if (aComplete && !bComplete) return -1
    if (!aComplete && bComplete) return 1

    // 都齐全时，按 EV 降序
    if (aComplete && bComplete) {
      const aEV = a.ev ?? -Infinity
      const bEV = b.ev ?? -Infinity
      return bEV - aEV
    }

    // 都不全时，按 polymarket 价格或 web2 赔率排序
    const aValue = a.polymarket_price ?? a.web2_odds ?? 0
    const bValue = b.polymarket_price ?? b.web2_odds ?? 0
    return bValue - aValue
  })
}

export function Dashboard({ worldCupMarkets, nbaMarkets, dailyMatches, stats }: DashboardProps) {
  const [activeSport, setActiveSport] = useState<SportType>('nba')
  const [nbaSubTab, setNbaSubTab] = useState<NbaSubTab>('daily')
  const [hideLowOdds, setHideLowOdds] = useState(true)

  // 冠军盘口数据过滤
  const filterChampionMarkets = (markets: MarketItem[]) => {
    return hideLowOdds
      ? markets.filter(item => (item.polymarket_price || 0) >= 0.01)
      : markets
  }

  const filteredWorldCupMarkets = filterChampionMarkets(worldCupMarkets)
  const filteredNbaMarkets = filterChampionMarkets(nbaMarkets)

  // 冠军盘口排序：双边齐全 + EV 高的排在前面
  const sortedWorldCupMarkets = sortChampionMarkets(filteredWorldCupMarkets)
  const sortedNbaMarkets = sortChampionMarkets(filteredNbaMarkets)

  // 每日比赛排序：优先显示双边齐全的套利机会
  const sortedDailyMatches = [...dailyMatches].sort(
    (a, b) => getMatchPriority(b) - getMatchPriority(a)
  )

  return (
    <main className="min-h-screen p-6">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">
              PolyDelta
            </h1>
            <p className="text-[#8b949e] mt-1">Real-time Web2 vs Web3 Arbitrage</p>
          </div>
          <div className="flex gap-6 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-[#58a6ff]">{stats.dailyMatchCount}</div>
              <div className="text-[#8b949e]">Today's Games</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[#d29922]">{stats.totalOpportunities}</div>
              <div className="text-[#8b949e]">Champions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[#3fb950]">{stats.arbitrageCount}</div>
              <div className="text-[#8b949e]">Arbitrage</div>
            </div>
          </div>
        </div>
        <div className="mt-2 text-xs text-[#8b949e]">
          Last Updated: {stats.lastUpdate}
        </div>
      </header>

      {/* 一级导航 - Sport Type */}
      <div className="flex items-center gap-4 mb-4">
        <div className="flex gap-2 p-1 bg-[#161b22] rounded-lg">
          <button
            onClick={() => setActiveSport('worldcup')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium
              transition-all duration-200
              ${activeSport === 'worldcup'
                ? 'bg-[#3fb950] text-black'
                : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
              }
            `}
          >
            <span>⚽</span>
            <span>FIFA World Cup</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${activeSport === 'worldcup' ? 'bg-black/20' : 'bg-[#30363d]'}`}>
              {worldCupMarkets.length}
            </span>
          </button>
          <button
            onClick={() => setActiveSport('nba')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium
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

      {/* Hide < 1% Toggle for World Cup */}
      {activeSport === 'worldcup' && (
        <div className="flex items-center gap-4 mb-6">
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

      {/* ========== World Cup Content ========== */}
      {activeSport === 'worldcup' && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">⚽</span>
            <h2 className="text-xl font-bold text-[#e6edf3]">FIFA World Cup 2026</h2>
            <span className="px-2 py-0.5 bg-[#30363d] rounded text-xs text-[#8b949e]">
              {hideLowOdds && filteredWorldCupMarkets.length !== worldCupMarkets.length
                ? `${filteredWorldCupMarkets.length} / ${worldCupMarkets.length} teams`
                : `${filteredWorldCupMarkets.length} teams`}
            </span>
          </div>

          {filteredWorldCupMarkets.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {sortedWorldCupMarkets.map((item) => (
                <ArbitrageCard
                  key={item.id}
                  teamName={item.team_name}
                  web2Odds={item.web2_odds}
                  sourceBookmaker={item.source_bookmaker}
                  sourceUrl={item.source_url}
                  polymarketPrice={item.polymarket_price}
                  polymarketUrl={item.polymarket_url}
                  ev={item.ev}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-[#8b949e]">
              No World Cup data available
            </div>
          )}
        </section>
      )}

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
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">🏆</span>
            <h2 className="text-xl font-bold text-[#e6edf3]">NBA Championship</h2>
            <span className="px-2 py-0.5 bg-[#30363d] rounded text-xs text-[#8b949e]">
              {hideLowOdds && filteredNbaMarkets.length !== nbaMarkets.length
                ? `${filteredNbaMarkets.length} / ${nbaMarkets.length} teams`
                : `${filteredNbaMarkets.length} teams`}
            </span>
          </div>

          {filteredNbaMarkets.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {sortedNbaMarkets.map((item) => (
                <ArbitrageCard
                  key={item.id}
                  teamName={item.team_name}
                  web2Odds={item.web2_odds}
                  sourceBookmaker={item.source_bookmaker}
                  sourceUrl={item.source_url}
                  polymarketPrice={item.polymarket_price}
                  polymarketUrl={item.polymarket_url}
                  ev={item.ev}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-[#8b949e]">
              No NBA Championship data available
            </div>
          )}
        </section>
      )}

      {/* Footer */}
      <footer className="mt-12 pt-6 border-t border-[#30363d] text-center text-xs text-[#8b949e]">
        <p>Data sources: TheOddsAPI (Web2) | Polymarket (Prediction Market)</p>
        <p className="mt-1">Built for educational purposes only. Not financial advice.</p>
      </footer>
    </main>
  )
}
