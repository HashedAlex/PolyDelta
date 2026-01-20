"use client"

interface MatchCardProps {
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
}

function formatMatchTime(date: Date): string {
  const now = new Date()
  const matchDate = new Date(date)

  const isToday = matchDate.toDateString() === now.toDateString()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const isTomorrow = matchDate.toDateString() === tomorrow.toDateString()

  const timeStr = matchDate.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })

  if (isToday) {
    return `Today ${timeStr}`
  } else if (isTomorrow) {
    return `Tomorrow ${timeStr}`
  } else {
    const dateStr = matchDate.toLocaleDateString('en-US', {
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
}: MatchCardProps) {
  const homeEV = calculateEV(web2HomeOdds, polyHomePrice)
  const awayEV = calculateEV(web2AwayOdds, polyAwayPrice)

  // 找到最大的 EV 值
  const maxEV = Math.max(
    Math.abs(homeEV || 0),
    Math.abs(awayEV || 0)
  )

  // 高亮颜色逻辑
  const hasArbitrage = maxEV >= 5
  const borderColor = hasArbitrage ? 'border-[#3fb950]' : 'border-[#30363d]'

  return (
    <div className={`bg-[#161b22] rounded-lg p-4 border ${borderColor} hover:border-[#58a6ff] transition-colors`}>
      {/* Header - 比赛时间 */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-[#8b949e] bg-[#21262d] px-2 py-1 rounded">
          {formatMatchTime(commenceTime)}
        </span>
        {hasArbitrage && (
          <span className="text-xs text-[#3fb950] bg-[#3fb950]/10 px-2 py-1 rounded font-medium">
            Arbitrage
          </span>
        )}
      </div>

      {/* Teams - 单行横向展示 */}
      <div className="flex flex-row items-center gap-2 mb-4 min-w-0">
        <span className="text-base font-bold text-[#e6edf3] truncate" title={homeTeam}>
          {homeTeam}
        </span>
        <span className="text-xs text-[#6e7681] flex-shrink-0">vs</span>
        <span className="text-base font-bold text-[#e6edf3] truncate" title={awayTeam}>
          {awayTeam}
        </span>
      </div>

      {/* Odds Comparison Table */}
      <div className="bg-[#0d1117] rounded-lg p-3">
        <div className="grid grid-cols-4 gap-2 text-xs mb-2">
          <div className="text-[#8b949e]">Team</div>
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
              "Web2"
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
          <div className="text-[#8b949e] text-center">EV</div>
        </div>

        {/* Home Team Row */}
        <div className="grid grid-cols-4 gap-2 text-sm py-1.5 border-t border-[#30363d]">
          <div className="text-[#e6edf3] truncate" title={homeTeam}>
            {homeTeam.split(' ').pop()}
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
        </div>

        {/* Away Team Row */}
        <div className="grid grid-cols-4 gap-2 text-sm py-1.5 border-t border-[#30363d]">
          <div className="text-[#e6edf3] truncate" title={awayTeam}>
            {awayTeam.split(' ').pop()}
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
        </div>
      </div>
    </div>
  )
}
