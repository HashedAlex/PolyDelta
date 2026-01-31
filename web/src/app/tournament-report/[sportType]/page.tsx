"use client"

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'

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

const LEAGUE_CONFIG: Record<string, { name: string; icon: string; sportType: string; backTab: string }> = {
  epl: { name: 'EPL Winner 2025-26', icon: '\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}', sportType: 'epl', backTab: 'soccer' },
  ucl: { name: 'UCL Winner 2025-26', icon: '\u2B50', sportType: 'ucl', backTab: 'soccer' },
  nba: { name: 'NBA Winner 2026', icon: '\u{1F3C0}', sportType: 'nba', backTab: 'nba' },
  world_cup: { name: 'FIFA World Cup 2026 Winner', icon: '\u{1F3C6}', sportType: 'world_cup', backTab: 'worldcup' },
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

function TournamentReportPage({ params }: { params: { sportType: string } }) {
  const router = useRouter()
  const [report, setReport] = useState<ReportData | null>(null)
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Chat state
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'ai'; content: string }[]>([])
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  const config = LEAGUE_CONFIG[params.sportType] || LEAGUE_CONFIG.epl

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, chatLoading])

  // Fetch report
  useEffect(() => {
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
  }, [config.sportType])

  // Chat handler
  const handleSendMessage = async () => {
    if (!chatInput.trim() || chatLoading) return

    const userMessage = chatInput.trim()
    setChatInput('')

    const updatedMessages: { role: 'user' | 'ai'; content: string }[] = [
      ...chatMessages,
      { role: 'user', content: userMessage },
    ]
    setChatMessages(updatedMessages)
    setChatLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          matchId: `tournament-report-${config.sportType}`,
          messages: updatedMessages,
        }),
      })

      const data = await res.json()

      if (data.success && data.reply) {
        setChatMessages(prev => [...prev, { role: 'ai', content: data.reply }])
      } else {
        setChatMessages(prev => [...prev, { role: 'ai', content: data.error || 'Sorry, something went wrong.' }])
      }
    } catch {
      setChatMessages(prev => [...prev, { role: 'ai', content: 'Network error. Please try again.' }])
    } finally {
      setChatLoading(false)
    }
  }

  const handleBack = () => {
    router.push(`/?tab=${config.backTab}`)
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0d1117] text-[#e6edf3] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#58a6ff] mx-auto mb-4"></div>
          <p className="text-[#8b949e]">Loading tournament report...</p>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      {/* Top Navigation */}
      <nav className="sticky top-0 z-40 bg-[#161b22] border-b border-[#30363d] px-6 py-4">
        <button
          onClick={handleBack}
          className="inline-flex items-center gap-2 text-[#8b949e] hover:text-[#e6edf3] transition-colors"
        >
          <span>&larr;</span>
          <span>Back to Dashboard</span>
        </button>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Header */}
        <header className="bg-[#161b22] rounded-xl border border-[#30363d] p-6">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{config.icon}</span>
            <div>
              <h1 className="text-2xl font-bold text-[#e6edf3]">Tournament Landscape</h1>
              <p className="text-sm text-[#8b949e]">
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
        </header>

        {error && (
          <div className="bg-[#161b22] rounded-xl border border-[#f85149] p-6 text-center">
            <p className="text-[#f85149] text-sm mb-2">{error}</p>
            <p className="text-[#6e7681] text-xs">Tournament reports are generated periodically. Check back later.</p>
          </div>
        )}

        {report && (
          <>
            {/* Strategy Card */}
            <section className="bg-[#161b22] rounded-xl border border-[#30363d] overflow-hidden">
              <div className="px-6 py-4 border-b border-[#30363d]">
                <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
                  <span>🎯</span>
                  <span>{report.strategy_card.headline}</span>
                </h2>
              </div>
              <div className="px-6 py-5">
                <div className="text-sm text-[#8b949e] leading-relaxed prose prose-invert prose-sm max-w-none prose-headings:text-[#e6edf3] prose-headings:text-sm prose-headings:font-bold prose-headings:mt-3 prose-headings:mb-1 prose-strong:text-[#e6edf3] prose-p:my-1">
                  <ReactMarkdown>{report.strategy_card.analysis}</ReactMarkdown>
                </div>
                <div className="mt-4 text-xs text-[#d29922] bg-[#d29922]/10 px-4 py-2 rounded-lg">
                  {report.strategy_card.risk_text}
                </div>
              </div>
            </section>

            {/* Tier List */}
            {report.news_card.tiers.map((tier) => (
              <section
                key={tier.tier_name}
                className={`bg-[#161b22] rounded-xl border border-[#30363d] border-l-4 ${getTierBorderColor(tier.tier_name)} overflow-hidden`}
              >
                <div className="px-6 py-3 border-b border-[#30363d]/50">
                  <h3 className="text-base font-bold text-[#e6edf3] flex items-center gap-2">
                    <span>{tier.tier_emoji}</span>
                    <span>{tier.tier_name}</span>
                    <span className="text-xs text-[#6e7681] font-normal ml-auto">
                      {tier.teams.length} team{tier.teams.length !== 1 ? 's' : ''}
                    </span>
                  </h3>
                </div>
                <div className="divide-y divide-[#30363d]/30">
                  {tier.teams.map((team) => (
                    <div key={team.team_name} className="px-6 py-4 hover:bg-[#21262d]/50 transition-colors">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-medium text-[#e6edf3]">{team.team_name}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono text-[#58a6ff]">
                            {(team.polymarket_price * 100).toFixed(1)}%
                          </span>
                          {team.web2_odds != null && team.web2_odds > 0 && (
                            <span className="text-sm font-mono text-[#d29922]">
                              ({(team.web2_odds * 100).toFixed(1)}%)
                            </span>
                          )}
                          <span className={`px-2 py-0.5 rounded text-xs font-bold border ${getVerdictStyle(team.verdict)}`}>
                            {team.verdict}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-[#8b949e] leading-relaxed">{team.one_liner}</p>
                    </div>
                  ))}
                </div>
              </section>
            ))}

            {/* Portfolio Summary */}
            <section className="bg-[#58a6ff]/5 border border-[#58a6ff]/20 rounded-xl px-6 py-4">
              <div className="flex items-center gap-2 mb-2">
                <span>💼</span>
                <span className="text-sm font-bold text-[#e6edf3]">Portfolio Strategy</span>
              </div>
              <p className="text-sm text-[#8b949e] leading-relaxed">
                {report.news_card.portfolio_summary}
              </p>
            </section>

            {/* Disclaimer */}
            <div className="text-xs text-[#6e7681] text-center py-1">
              AI analysis based on public data and market pricing. Not financial advice. DYOR.
            </div>
          </>
        )}

        {/* DegenGo Chat Interface */}
        <section className="bg-[#161b22] rounded-xl border border-[#30363d] overflow-hidden">
          <div className="px-6 py-4 border-b border-[#30363d]">
            <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
              <span>💬</span>
              <span>Ask AI About This Tournament</span>
            </h2>
          </div>

          {/* Chat Messages */}
          {chatMessages.length > 0 && (
            <div
              className="px-6 py-4 space-y-4 overflow-y-auto border-b border-[#30363d]"
              style={{ maxHeight: 'calc(100vh - 200px)' }}
            >
              {chatMessages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-2 rounded-lg ${
                      msg.role === 'user'
                        ? 'bg-[#238636] text-white'
                        : 'bg-[#21262d] text-[#e6edf3]'
                    }`}
                  >
                    {msg.role === 'ai' && <span className="text-xs text-[#8b949e] block mb-1">DegenGo 🎲</span>}
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              ))}
              {chatLoading && (
                <div className="flex justify-start">
                  <div className="max-w-[80%] px-4 py-2 rounded-lg bg-[#21262d] text-[#8b949e]">
                    <span className="text-xs block mb-1">DegenGo 🎲</span>
                    <p className="text-sm animate-pulse">Thinking...</p>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}

          {/* Chat Input */}
          <div className="px-6 py-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Ask about tournament odds, team comparisons, betting strategies..."
                disabled={chatLoading}
                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3 text-[#e6edf3] placeholder-[#6e7681] focus:border-[#58a6ff] focus:outline-none disabled:opacity-50"
              />
              <button
                onClick={handleSendMessage}
                disabled={chatLoading}
                className="px-6 py-3 bg-[#58a6ff] hover:bg-[#4493e6] text-white font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span>{chatLoading ? '...' : 'Send'}</span>
                <span>&rarr;</span>
              </button>
            </div>
            <p className="text-xs text-[#6e7681] mt-2">
              Ask about tier analysis, portfolio allocation, team comparisons, or market sentiment.
            </p>
          </div>
        </section>
      </div>
    </main>
  )
}

export default TournamentReportPage
