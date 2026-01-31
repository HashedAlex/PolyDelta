"use client"

import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

interface TournamentReportModalProps {
  isOpen: boolean
  onClose: () => void
  league: 'epl' | 'ucl' | 'nba' | 'world_cup'
}

interface TierTeam {
  team_name: string
  polymarket_price: number
  web2_odds: number | null
  verdict: 'Accumulate' | 'Hold' | 'Sell'
  one_liner: string
}

interface Tier {
  tier_name: string
  tier_emoji: string
  teams: TierTeam[]
}

interface ReportData {
  strategy_card: {
    headline: string
    analysis: string
    risk_text: string
  }
  news_card: {
    tiers: Tier[]
    portfolio_summary: string
  }
}

const LEAGUE_CONFIG: Record<string, { name: string; icon: string; sportType: string }> = {
  epl: { name: 'EPL Winner 2025-26', icon: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', sportType: 'epl' },
  ucl: { name: 'UCL Winner 2025-26', icon: '⭐', sportType: 'ucl' },
  nba: { name: 'NBA Winner 2026', icon: '🏀', sportType: 'nba' },
  world_cup: { name: 'FIFA World Cup 2026 Winner', icon: '🏆', sportType: 'world_cup' },
}

function getVerdictStyle(verdict: string): string {
  switch (verdict) {
    case 'Accumulate':
      return 'bg-[#3fb950]/20 text-[#3fb950] border-[#3fb950]/40'
    case 'Sell':
      return 'bg-[#f85149]/20 text-[#f85149] border-[#f85149]/40'
    case 'Hold':
    default:
      return 'bg-[#d29922]/20 text-[#d29922] border-[#d29922]/40'
  }
}

function getTierBorderColor(tierName: string): string {
  switch (tierName) {
    case 'Favorites':
      return 'border-l-[#d29922]'
    case 'Challengers':
      return 'border-l-[#58a6ff]'
    case 'Dark Horses':
      return 'border-l-[#bc8cff]'
    case 'Pretenders':
      return 'border-l-[#6e7681]'
    default:
      return 'border-l-[#30363d]'
  }
}

export function TournamentReportModal({ isOpen, onClose, league }: TournamentReportModalProps) {
  const [report, setReport] = useState<ReportData | null>(null)
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const config = LEAGUE_CONFIG[league] || LEAGUE_CONFIG.epl

  useEffect(() => {
    if (!isOpen) return

    setLoading(true)
    setError(null)
    setReport(null)

    fetch(`/api/tournament-report/${config.sportType}`)
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.error || 'Failed to fetch report')
        }
        return res.json()
      })
      .then((data) => {
        if (data.success && data.data) {
          try {
            const parsed = typeof data.data.report === 'string'
              ? JSON.parse(data.data.report)
              : data.data.report
            setReport(parsed)
            setGeneratedAt(data.data.generatedAt)
          } catch {
            setError('Failed to parse report data')
          }
        } else {
          setError(data.error || 'No report available')
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to load report')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [isOpen, config.sportType])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-[#161b22] border border-[#30363d] rounded-xl w-full max-w-2xl mx-4 shadow-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#30363d] shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{config.icon}</span>
            <div>
              <h2 className="text-lg font-bold text-[#e6edf3]">Tournament Landscape</h2>
              <p className="text-xs text-[#8b949e]">
                {config.name}
                {generatedAt && (
                  <> &middot; Updated {new Date(generatedAt).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}</>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#8b949e] hover:text-[#e6edf3] transition-colors p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-4">
          {loading && (
            <div className="flex items-center justify-center py-16">
              <div className="flex items-center gap-3 text-[#8b949e]">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Loading tournament report...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="text-center py-16">
              <p className="text-[#f85149] text-sm mb-2">{error}</p>
              <p className="text-[#6e7681] text-xs">Tournament reports are generated periodically. Check back later.</p>
            </div>
          )}

          {report && (
            <div className="space-y-4">
              {/* Strategy Card */}
              <div className="bg-[#0d1117] rounded-xl border border-[#30363d] overflow-hidden">
                <div className="px-4 py-3 border-b border-[#30363d]">
                  <h3 className="text-sm font-semibold text-[#e6edf3] flex items-center gap-2">
                    <span>🎯</span>
                    <span>{report.strategy_card.headline}</span>
                  </h3>
                </div>
                <div className="px-4 py-4">
                  <div className="text-sm text-[#8b949e] leading-relaxed prose prose-invert prose-sm max-w-none prose-headings:text-[#e6edf3] prose-headings:text-sm prose-headings:font-bold prose-headings:mt-3 prose-headings:mb-1 prose-strong:text-[#e6edf3] prose-p:my-1">
                    <ReactMarkdown>{report.strategy_card.analysis}</ReactMarkdown>
                  </div>
                  <div className="mt-3 text-[10px] text-[#d29922] bg-[#d29922]/10 px-3 py-2 rounded">
                    {report.strategy_card.risk_text}
                  </div>
                </div>
              </div>

              {/* Tier List */}
              {report.news_card.tiers.map((tier) => (
                <div
                  key={tier.tier_name}
                  className={`bg-[#0d1117] rounded-xl border border-[#30363d] border-l-4 ${getTierBorderColor(tier.tier_name)} overflow-hidden`}
                >
                  <div className="px-4 py-2.5 border-b border-[#30363d]/50">
                    <h4 className="text-sm font-bold text-[#e6edf3] flex items-center gap-2">
                      <span>{tier.tier_emoji}</span>
                      <span>{tier.tier_name}</span>
                      <span className="text-[10px] text-[#6e7681] font-normal ml-auto">
                        {tier.teams.length} team{tier.teams.length !== 1 ? 's' : ''}
                      </span>
                    </h4>
                  </div>
                  <div className="divide-y divide-[#30363d]/30">
                    {tier.teams.map((team) => (
                      <div key={team.team_name} className="px-4 py-3 hover:bg-[#161b22]/50 transition-colors">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-sm text-[#e6edf3]">{team.team_name}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-[#58a6ff]">
                              {(team.polymarket_price * 100).toFixed(1)}%
                            </span>
                            {team.web2_odds != null && team.web2_odds > 0 && (
                              <span className="text-xs font-mono text-[#d29922]">
                                ({(team.web2_odds * 100).toFixed(1)}%)
                              </span>
                            )}
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${getVerdictStyle(team.verdict)}`}>
                              {team.verdict}
                            </span>
                          </div>
                        </div>
                        <p className="text-xs text-[#8b949e] leading-relaxed">{team.one_liner}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Portfolio Summary */}
              <div className="bg-[#58a6ff]/5 border border-[#58a6ff]/20 rounded-xl px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span>💼</span>
                  <span className="text-xs font-bold text-[#e6edf3]">Portfolio Strategy</span>
                </div>
                <p className="text-xs text-[#8b949e] leading-relaxed">
                  {report.news_card.portfolio_summary}
                </p>
              </div>

              {/* Disclaimer */}
              <div className="text-[10px] text-[#6e7681] text-center py-2">
                AI analysis based on public data and market pricing. Not financial advice. DYOR.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
