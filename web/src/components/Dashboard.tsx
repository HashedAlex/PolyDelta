"use client"

import { useState } from 'react'
import { ArbitrageCard } from './ArbitrageCard'

// 市场数据类型
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

interface DashboardProps {
  worldCupMarkets: MarketItem[]
  nbaMarkets: MarketItem[]
  stats: {
    totalOpportunities: number
    arbitrageCount: number
    lastUpdate: string
  }
}

type TabType = 'worldcup' | 'nba'

const TAB_CONFIG: Record<TabType, { name: string; icon: string }> = {
  worldcup: { name: 'FIFA World Cup', icon: '⚽' },
  nba: { name: 'NBA', icon: '🏀' },
}

export function Dashboard({ worldCupMarkets, nbaMarkets, stats }: DashboardProps) {
  const [activeTab, setActiveTab] = useState<TabType>('worldcup')
  const [hideLowOdds, setHideLowOdds] = useState(true) // 默认开启：隐藏 < 1% 的队伍

  // 根据当前 Tab 获取数据，并根据开关过滤
  const rawMarkets = activeTab === 'worldcup' ? worldCupMarkets : nbaMarkets
  const currentMarkets = hideLowOdds
    ? rawMarkets.filter(item => (item.polymarket_price || 0) >= 0.01)
    : rawMarkets
  const currentCount = currentMarkets.length
  const totalCount = rawMarkets.length

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
              <div className="text-2xl font-bold text-[#58a6ff]">{stats.totalOpportunities}</div>
              <div className="text-[#8b949e]">Total Markets</div>
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

      {/* Tab 切换栏 + 过滤开关 */}
      <div className="flex items-center gap-4 mb-6">
        {/* Tabs */}
        <div className="flex gap-2 p-1 bg-[#161b22] rounded-lg">
          {(Object.entries(TAB_CONFIG) as [TabType, { name: string; icon: string }][]).map(([key, config]) => {
            const isActive = activeTab === key
            const count = key === 'worldcup' ? worldCupMarkets.length : nbaMarkets.length

            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium
                  transition-all duration-200
                  ${isActive
                    ? 'bg-[#3fb950] text-black'
                    : 'bg-transparent text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
                  }
                `}
              >
                <span>{config.icon}</span>
                <span>{config.name}</span>
                <span className={`
                  px-1.5 py-0.5 rounded text-xs
                  ${isActive ? 'bg-black/20' : 'bg-[#30363d]'}
                `}>
                  {count}
                </span>
              </button>
            )
          })}
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
            <div className={`
              w-10 h-5 rounded-full transition-colors duration-200
              ${hideLowOdds ? 'bg-[#3fb950]' : 'bg-[#30363d]'}
            `} />
            <div className={`
              absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white
              transition-transform duration-200
              ${hideLowOdds ? 'translate-x-5' : 'translate-x-0'}
            `} />
          </div>
          <span className="text-sm text-[#8b949e]">Hide &lt; 1%</span>
        </label>
      </div>

      {/* 内容区域 */}
      <section>
        {/* Section Header */}
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">{TAB_CONFIG[activeTab].icon}</span>
          <h2 className="text-xl font-bold text-[#e6edf3]">
            {TAB_CONFIG[activeTab].name}
          </h2>
          <span className="px-2 py-0.5 bg-[#30363d] rounded text-xs text-[#8b949e]">
            {hideLowOdds && currentCount !== totalCount
              ? `${currentCount} / ${totalCount} teams`
              : `${currentCount} teams`}
          </span>
        </div>

        {/* Cards Grid */}
        {currentMarkets.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {currentMarkets.map((item) => (
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
            No data available for {TAB_CONFIG[activeTab].name}
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="mt-12 pt-6 border-t border-[#30363d] text-center text-xs text-[#8b949e]">
        <p>Data sources: TheOddsAPI (Web2) | Polymarket (Prediction Market)</p>
        <p className="mt-1">Built for educational purposes only. Not financial advice.</p>
      </footer>
    </main>
  )
}
