interface ArbitrageCardProps {
  teamName: string
  web2Odds: number | null
  sourceBookmaker: string | null
  sourceUrl: string | null
  polymarketPrice: number | null
  polymarketUrl: string | null
  ev: number | null
}

export function ArbitrageCard({
  teamName,
  web2Odds,
  sourceBookmaker,
  sourceUrl,
  polymarketPrice,
  polymarketUrl,
  ev,
}: ArbitrageCardProps) {
  // 判断是否为套利机会 (|EV| >= 5%)
  const isArbitrage = ev !== null && Math.abs(ev) >= 5
  // 判断方向：正EV表示Web2低估（应该买Polymarket），负EV表示Web2高估（应该卖Polymarket）
  const isPositiveEV = ev !== null && ev > 0

  // 格式化百分比显示
  const formatPercent = (value: number | null) => {
    if (value === null) return 'N/A'
    return `${(value * 100).toFixed(1)}%`
  }

  const formatEV = (value: number | null) => {
    if (value === null) return 'N/A'
    const sign = value > 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  // 显示的 bookmaker 名称
  const bookmakerDisplay = sourceBookmaker || 'Web2'

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
      {/* Arbitrage Badge */}
      {isArbitrage && (
        <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-[#3fb950] text-black text-xs font-bold rounded-full">
          Arbitrage
        </div>
      )}

      {/* Team Name */}
      <h3 className="text-lg font-semibold text-[#e6edf3] mb-3 pr-16">
        {teamName}
      </h3>

      {/* Odds Comparison */}
      <div className="space-y-2 mb-4">
        {/* Bookmaker Odds */}
        <div className="flex justify-between items-center text-sm">
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
          <span className="text-[#e6edf3] font-mono">
            {formatPercent(web2Odds)}
          </span>
        </div>

        {/* Polymarket Price */}
        <div className="flex justify-between items-center text-sm">
          <span className="text-[#58a6ff]">Polymarket</span>
          <span className="text-[#58a6ff] font-mono">
            {formatPercent(polymarketPrice)}
          </span>
        </div>

        {/* Divider */}
        <div className="border-t border-[#30363d] my-2"></div>

        {/* EV Display */}
        <div className="flex justify-between items-center">
          <span className="text-[#8b949e] text-sm">EV Diff</span>
          <span
            className={`
              font-mono font-bold text-lg
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
      </div>

      {/* Action Button */}
      {polymarketUrl ? (
        <a
          href={polymarketUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={`
            block w-full py-2 px-4 rounded text-center text-sm font-medium
            transition-colors duration-200
            ${isArbitrage
              ? 'bg-[#3fb950] hover:bg-[#2ea043] text-black'
              : 'bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d]'
            }
          `}
        >
          {isArbitrage ? 'Bet on Polymarket' : 'View on Polymarket'}
        </a>
      ) : (
        <div className="w-full py-2 px-4 rounded text-center text-sm text-[#8b949e] bg-[#21262d] border border-[#30363d]">
          No Polymarket Data
        </div>
      )}
    </div>
  )
}
