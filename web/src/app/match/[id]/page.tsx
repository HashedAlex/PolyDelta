"use client"

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { CalculatorModal, CalculatorData } from '@/components/CalculatorModal'

interface MatchData {
  matchId: string
  sportType: string
  homeTeam: string
  awayTeam: string
  commenceTime: string
  web2HomeOdds: number | null
  web2AwayOdds: number | null
  polyHomePrice: number | null
  polyAwayPrice: number | null
  sourceBookmaker: string | null
  sourceUrl: string | null
  polymarketUrl: string | null
  aiAnalysis: string | null
  analysisTimestamp: string | null
  isChampionship?: boolean
}

// Helper function to format relative time
function getRelativeTime(dateString: string | null): string {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffDays > 0) {
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
  } else if (diffHours > 0) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
  } else {
    return 'Just now'
  }
}

// Helper function to format date
function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

// Calculate EV
function calculateEV(web2Odds: number | null, polyPrice: number | null): number | null {
  if (!web2Odds || !polyPrice || polyPrice === 0) return null
  return ((web2Odds - polyPrice) / polyPrice) * 100
}

export default function MatchDetailPage({ params }: { params: { id: string } }) {
  const [match, setMatch] = useState<MatchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCalculator, setShowCalculator] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'ai'; content: string }[]>([])

  useEffect(() => {
    async function fetchMatch() {
      try {
        const response = await fetch(`/api/match/${params.id}`)
        const result = await response.json()

        if (!result.success) {
          setError(result.error || 'Failed to load match')
          return
        }

        setMatch(result.data)
      } catch (err) {
        setError('Failed to fetch match data')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchMatch()
  }, [params.id])

  const handleSendMessage = () => {
    if (!chatInput.trim()) return

    // Add user message
    setChatMessages(prev => [...prev, { role: 'user', content: chatInput }])

    // Simulate AI response (mock for now)
    setTimeout(() => {
      setChatMessages(prev => [...prev, {
        role: 'ai',
        content: "I'm an AI assistant for match analysis. This is a demo response. In the full version, I'll provide real-time insights about odds movements, team news, and betting strategies for this match."
      }])
    }, 1000)

    setChatInput('')
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#0d1117] text-[#e6edf3] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#58a6ff] mx-auto mb-4"></div>
          <p className="text-[#8b949e]">Loading match data...</p>
        </div>
      </main>
    )
  }

  if (error || !match) {
    return (
      <main className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
        <nav className="sticky top-0 z-40 bg-[#161b22] border-b border-[#30363d] px-6 py-4">
          <Link href="/" className="inline-flex items-center gap-2 text-[#8b949e] hover:text-[#e6edf3] transition-colors">
            <span>←</span>
            <span>Back to Dashboard</span>
          </Link>
        </nav>
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-[#161b22] rounded-xl border border-[#f85149] p-6 text-center">
            <p className="text-[#f85149]">{error || 'Match not found'}</p>
          </div>
        </div>
      </main>
    )
  }

  const homeEV = calculateEV(match.web2HomeOdds, match.polyHomePrice)
  const awayEV = calculateEV(match.web2AwayOdds, match.polyAwayPrice)

  const calculatorData: CalculatorData = {
    homeTeam: match.homeTeam,
    awayTeam: match.awayTeam,
    web2HomeOdds: match.web2HomeOdds,
    web2AwayOdds: match.web2AwayOdds,
    polyHomePrice: match.polyHomePrice,
    polyAwayPrice: match.polyAwayPrice,
    sourceBookmaker: match.sourceBookmaker,
  }

  return (
    <main className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      {/* Top Navigation */}
      <nav className="sticky top-0 z-40 bg-[#161b22] border-b border-[#30363d] px-6 py-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-[#8b949e] hover:text-[#e6edf3] transition-colors"
        >
          <span>←</span>
          <span>Back to Dashboard</span>
        </Link>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Match Header */}
        <header className="bg-[#161b22] rounded-xl border border-[#30363d] p-6">
          <div className="flex items-center justify-between">
            <div>
              {match.isChampionship ? (
                <>
                  <h1 className="text-2xl font-bold text-[#e6edf3]">
                    {match.homeTeam}
                  </h1>
                  <p className="text-[#8b949e] mt-1 flex items-center gap-2">
                    <span>{match.sportType === 'nba' ? '🏆' : '⚽'}</span>
                    <span>{match.sportType === 'nba' ? 'NBA Championship Analysis' : 'FIFA World Cup 2026 Analysis'}</span>
                  </p>
                </>
              ) : (
                <>
                  <h1 className="text-2xl font-bold text-[#e6edf3]">
                    {match.homeTeam} <span className="text-[#8b949e] font-normal">vs</span> {match.awayTeam}
                  </h1>
                  <p className="text-[#8b949e] mt-1 flex items-center gap-2">
                    <span>🏀</span>
                    <span>NBA Daily Match</span>
                    <span>•</span>
                    <span>{formatDate(match.commenceTime)}</span>
                  </p>
                </>
              )}
            </div>
            <div className="text-right">
              <div className="text-xs text-[#8b949e]">{match.isChampionship ? 'Team' : 'Match ID'}</div>
              <div className="text-sm font-mono text-[#58a6ff]">{match.isChampionship ? match.homeTeam : params.id}</div>
            </div>
          </div>
        </header>

        {/* Odds Comparison Card - Only show for daily matches */}
        {!match.isChampionship && (
          <section className="bg-[#161b22] rounded-xl border border-[#30363d] p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
                <span>📊</span>
                <span>Odds Comparison</span>
              </h2>
              <button
                onClick={() => setShowCalculator(true)}
                className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                <span>🧮</span>
                <span>Open Calculator</span>
              </button>
            </div>

            {/* Odds Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[#8b949e] border-b border-[#30363d]">
                    <th className="text-left py-3 font-medium">Team</th>
                    <th className="text-center py-3 font-medium text-[#d29922]">{match.sourceBookmaker || 'Web2'}</th>
                    <th className="text-center py-3 font-medium text-[#58a6ff]">Polymarket</th>
                    <th className="text-center py-3 font-medium">EV</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[#30363d]/50">
                    <td className="py-3 font-medium">{match.homeTeam}</td>
                    <td className="py-3 text-center font-mono text-[#d29922]">
                      {match.web2HomeOdds ? `${(match.web2HomeOdds * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td className="py-3 text-center font-mono text-[#58a6ff]">
                      {match.polyHomePrice ? `${(match.polyHomePrice * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td className={`py-3 text-center font-mono ${homeEV && homeEV > 0 ? 'text-[#3fb950]' : homeEV && homeEV < 0 ? 'text-[#f85149]' : 'text-[#8b949e]'}`}>
                      {homeEV ? `${homeEV > 0 ? '+' : ''}${homeEV.toFixed(1)}%` : '-'}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-3 font-medium">{match.awayTeam}</td>
                    <td className="py-3 text-center font-mono text-[#d29922]">
                      {match.web2AwayOdds ? `${(match.web2AwayOdds * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td className="py-3 text-center font-mono text-[#58a6ff]">
                      {match.polyAwayPrice ? `${(match.polyAwayPrice * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td className={`py-3 text-center font-mono ${awayEV && awayEV > 0 ? 'text-[#3fb950]' : awayEV && awayEV < 0 ? 'text-[#f85149]' : 'text-[#8b949e]'}`}>
                      {awayEV ? `${awayEV > 0 ? '+' : ''}${awayEV.toFixed(1)}%` : '-'}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Championship Info Card - Only show for championship */}
        {match.isChampionship && (
          <section className="bg-[#161b22] rounded-xl border border-[#30363d] p-6">
            <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2 mb-4">
              <span>🏆</span>
              <span>Championship Odds</span>
            </h2>
            <p className="text-[#8b949e] text-sm">
              View current championship odds for {match.homeTeam} on the main dashboard.
              Compare Web2 bookmaker odds with Polymarket prices to find value betting opportunities.
            </p>
          </section>
        )}

        {/* AI Analysis Report */}
        <section className="bg-[#1c2128] rounded-xl border border-[#30363d] overflow-hidden">
          {/* Report Header */}
          <div className="bg-[#21262d] px-6 py-4 border-b border-[#30363d]">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
                <span>🤖</span>
                <span>{match.isChampionship ? 'AI Championship Analysis' : 'AI Match Analysis'}</span>
              </h2>
              {match.analysisTimestamp && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-[#d29922]">🕒</span>
                  <span className="text-[#d29922]">
                    Generated: {formatDate(match.analysisTimestamp)}
                  </span>
                  <span className="text-[#8b949e]">
                    ({getRelativeTime(match.analysisTimestamp)})
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Report Content */}
          <div className="px-6 py-6">
            {match.aiAnalysis ? (
              <div className="prose prose-invert max-w-none">
                {match.aiAnalysis.split('\n\n').map((paragraph, index) => {
                  if (paragraph.startsWith('## ')) {
                    return (
                      <h3 key={index} className="text-[#e6edf3] font-semibold text-base mt-4 mb-2">
                        {paragraph.replace('## ', '')}
                      </h3>
                    )
                  } else if (paragraph.startsWith('**')) {
                    return (
                      <p key={index} className="text-[#e6edf3] mb-3 font-medium">
                        {paragraph.replace(/\*\*/g, '')}
                      </p>
                    )
                  } else if (paragraph.startsWith('- ')) {
                    return (
                      <ul key={index} className="list-disc list-inside text-[#8b949e] mb-3 space-y-1">
                        {paragraph.split('\n').map((item, i) => (
                          <li key={i}>{item.replace('- ', '')}</li>
                        ))}
                      </ul>
                    )
                  } else if (paragraph.startsWith('*') && paragraph.endsWith('*')) {
                    return (
                      <p key={index} className="text-[#6e7681] text-sm italic mt-4">
                        {paragraph.replace(/\*/g, '')}
                      </p>
                    )
                  } else {
                    return (
                      <p key={index} className="text-[#8b949e] mb-3 leading-relaxed">
                        {paragraph}
                      </p>
                    )
                  }
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-[#8b949e]">No AI analysis available yet.</p>
                <p className="text-[#6e7681] text-sm mt-2">
                  AI analysis is generated when EV exceeds 2% threshold.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* AI Chat Interface */}
        <section className="bg-[#161b22] rounded-xl border border-[#30363d] overflow-hidden">
          <div className="px-6 py-4 border-b border-[#30363d]">
            <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
              <span>💬</span>
              <span>Ask AI About This Match</span>
            </h2>
          </div>

          {/* Chat Messages */}
          {chatMessages.length > 0 && (
            <div className="px-6 py-4 space-y-4 max-h-64 overflow-y-auto border-b border-[#30363d]">
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
                    {msg.role === 'ai' && <span className="text-xs text-[#8b949e] block mb-1">🤖 AI Assistant</span>}
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              ))}
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
                placeholder="Ask AI about this match..."
                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3 text-[#e6edf3] placeholder-[#6e7681] focus:border-[#58a6ff] focus:outline-none"
              />
              <button
                onClick={handleSendMessage}
                className="px-6 py-3 bg-[#58a6ff] hover:bg-[#4493e6] text-white font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                <span>Send</span>
                <span>→</span>
              </button>
            </div>
            <p className="text-xs text-[#6e7681] mt-2">
              Ask about odds analysis, team form, betting strategies, or market sentiment.
            </p>
          </div>
        </section>
      </div>

      {/* Calculator Modal */}
      <CalculatorModal
        isOpen={showCalculator}
        onClose={() => setShowCalculator(false)}
        data={calculatorData}
        type="match"
      />
    </main>
  )
}
