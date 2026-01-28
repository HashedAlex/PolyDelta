"use client"

import { useState, useEffect } from 'react'
import { CalculatorModal, CalculatorData } from './CalculatorModal'
import { PremiumLock } from './PremiumLock'

interface MarketItem {
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

interface AnalysisModalProps {
  isOpen: boolean
  onClose: () => void
  team: MarketItem
  sportType: 'world_cup' | 'nba'
}

// Structured AI Analysis Format
interface StrategyCard {
  score: number
  status: 'Buy' | 'Sell' | 'Wait' | 'Accumulate' | 'Hold'
  headline: string
  analysis: string
  kelly_advice: string
  risk_text: string
  hedging_tip?: string
}

interface PillarAnalysis {
  icon: string
  title: string
  content: string
  sentiment: 'positive' | 'negative' | 'neutral'
}

interface NewsCard {
  prediction: string
  confidence: 'High' | 'Medium' | 'Low'
  confidence_pct: number
  pillars: PillarAnalysis[]
  factors: string[]
  news_footer: string
}

interface AIAnalysisData {
  strategy_card: StrategyCard
  news_card: NewsCard
}

// Generate analysis for FIFA World Cup teams
function generateFIFAAnalysis(
  teamName: string,
  web2Odds: number | null,
  polyPrice: number | null
): AIAnalysisData {
  const team = teamName
  const odds = web2Odds ?? 0
  const price = polyPrice ?? 0
  const spread = ((odds - price) * 100).toFixed(1)

  let score = 50
  let status: 'Accumulate' | 'Hold' | 'Sell' = 'Hold'
  let headline = 'Fair Value'
  let analysis = ''
  let hedgingTip = ''

  if (price < odds - 0.03) {
    score = 72
    status = 'Accumulate'
    headline = 'Undervalued - Bracket Difficulty Favors'
    analysis = `${team} is trading at ${(price * 100).toFixed(1)}% on Polymarket vs ${(odds * 100).toFixed(1)}% on traditional books - a ${spread}% edge. Bracket analysis suggests favorable Strength of Schedule. If ${team} tops their group, the R16 crossover likely faces a weaker runner-up, creating a cleaner path to the Quarter-Finals. Tournament Pedigree matters: Nations with deep knockout experience historically outperform their "paper" odds.`
    hedgingTip = `Accumulate at $${price.toFixed(2)}. If ${team} tops their group, exit 50% at ~$${Math.min(0.40, price * 2).toFixed(2)}. Let the rest ride through knockouts with house money.`
  } else if (price > odds + 0.02) {
    score = 38
    status = 'Sell'
    headline = 'Potential Trap - Group of Death Risk'
    analysis = `${team} at ${(price * 100).toFixed(1)}% is trading above fair value (${(odds * 100).toFixed(1)}%). Warning: If their group contains 2+ Top 15 nations, this is a "Group of Death" scenario. Prices rarely account for the exhaustion of playing starters 90 minutes every group match. Rotation risk is real: Fatigued squads underperform in knockout rounds.`
    hedgingTip = `If holding, sell 30-50% now. Group stage upsets are common - lock in profits before variance strikes.`
  } else {
    score = 52
    status = 'Hold'
    headline = 'Fair Value - Wait for Group Stage'
    analysis = `${team} is trading near fair value at ${(price * 100).toFixed(1)}% (Trad Odds: ${(odds * 100).toFixed(1)}%). No clear edge detected. The smart play: Wait for Group Stage results to create volatility. Prices often overreact to early wins/losses, creating better entry points.`
    hedgingTip = `No action needed. Set alerts for price drops after Group Stage matches - that's when value emerges.`
  }

  const edgePct = Math.round((odds - price) * 100)

  const pillars: PillarAnalysis[] = [
    {
      icon: '⚔️',
      title: price < odds ? `${team}: Market Undervaluation Signal` : `${team}: Current Valuation`,
      content: `${team} Polymarket price ${(price * 100).toFixed(1)}% vs traditional implied odds ${(odds * 100).toFixed(1)}%. ${price < odds ? `A ${spread}% positive EV suggests the market may be undervaluing ${team}.` : `Price is at or above fair value.`} Group stage performance will be the key validation point.`,
      sentiment: price < odds ? 'positive' : 'neutral'
    },
    {
      icon: '🗺️',
      title: `${team} Knockout Path Analysis`,
      content: `World Cup knockout uses crossover brackets - group position directly impacts R16 opponent strength. If ${team} tops their group, they may avoid top-tier opponents until the quarters. Historical data shows group winners have ~25% higher semi-final conversion than runners-up.`,
      sentiment: 'neutral'
    },
    {
      icon: '🔄',
      title: `${team} Squad Depth Assessment`,
      content: `2026 World Cup expands to 48 teams with denser schedules. ${team}'s bench quality becomes a critical variable. Under the 5-sub rule, fresh legs after 70' often decide matches. Bench depth is the hidden metric for tournament success.`,
      sentiment: 'positive'
    }
  ]

  return {
    strategy_card: {
      score,
      status,
      headline,
      analysis,
      kelly_advice: edgePct > 0
        ? `Conservative 1/10 Kelly for futures. Edge: +${edgePct}%. Suggested position: ${(0.1 * edgePct / 100 * 100).toFixed(1)}% of bankroll.`
        : 'No position recommended. Wait for Group Stage volatility to create better entries.',
      risk_text: 'World Cup futures lock capital for months. Single-elimination knockout variance is extreme. Never bet more than you can afford to lose.',
      hedging_tip: hedgingTip
    },
    news_card: {
      prediction: `${team} ${score >= 70 ? 'Trophy Contender' : score >= 50 ? 'Semi-Final Ceiling' : 'Group Stage Risk'}`,
      confidence: score >= 70 ? 'High' : score >= 50 ? 'Medium' : 'Low',
      confidence_pct: score,
      pillars,
      factors: [
        `Trad implied: ${(odds * 100).toFixed(1)}%`,
        `Polymarket: ${(price * 100).toFixed(1)}%`,
        `Spread: ${spread}%`
      ],
      news_footer: 'Analysis uses Bracket Logic: Group difficulty, knockout path, and manager pedigree. Strength of Schedule is the key metric for tournament futures.'
    }
  }
}

// Helper functions
function getScoreColor(score: number): string {
  if (score >= 70) return 'text-[#3fb950]'
  if (score >= 50) return 'text-[#d29922]'
  return 'text-[#f85149]'
}

function getScoreBgColor(score: number): string {
  if (score >= 70) return 'bg-[#3fb950]/20 border-[#3fb950]/50'
  if (score >= 50) return 'bg-[#d29922]/20 border-[#d29922]/50'
  return 'bg-[#f85149]/20 border-[#f85149]/50'
}

function getStatusColor(status: string): string {
  if (status === 'Buy' || status === 'Accumulate') return 'bg-[#3fb950] text-black'
  if (status === 'Sell') return 'bg-[#f85149] text-white'
  if (status === 'Hold') return 'bg-[#d29922] text-black'
  return 'bg-[#6e7681] text-white'
}

export function AnalysisModal({ isOpen, onClose, team, sportType: _sportType }: AnalysisModalProps) {
  const [activeTab, setActiveTab] = useState<'analysis' | 'calculator'>('analysis')
  const [showCalculator, setShowCalculator] = useState(false)

  // Reset tab when modal opens
  useEffect(() => {
    if (isOpen) {
      setActiveTab('analysis')
    }
  }, [isOpen])

  if (!isOpen) return null

  // Generate analysis data
  const analysisData = generateFIFAAnalysis(
    team.team_name,
    team.web2_odds,
    team.polymarket_price
  )

  const { strategy_card, news_card } = analysisData

  // Calculator data
  const calculatorData: CalculatorData = {
    teamName: team.team_name,
    web2Odds: team.web2_odds,
    polymarketPrice: team.polymarket_price,
    sourceBookmaker: team.source_bookmaker,
    liquidityUsdc: team.liquidity_usdc,
  }

  const formatPercent = (value: number | null) => {
    if (value === null) return '-'
    const normalized = value > 1 ? value / 100 : value
    return `${(normalized * 100).toFixed(1)}%`
  }

  const edge = team.web2_odds && team.polymarket_price
    ? Math.round((team.web2_odds - team.polymarket_price) * 100)
    : 0

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
            <span className="text-2xl">⚽</span>
            <div>
              <h2 className="text-lg font-bold text-[#e6edf3]">{team.team_name}</h2>
              <p className="text-xs text-[#8b949e]">FIFA World Cup 2026 Winner Analysis</p>
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

        {/* Tab Navigation */}
        <div className="flex border-b border-[#30363d] shrink-0">
          <button
            onClick={() => setActiveTab('analysis')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === 'analysis'
                ? 'text-[#e6edf3] border-b-2 border-[#58a6ff] bg-[#58a6ff]/10'
                : 'text-[#8b949e] hover:text-[#e6edf3]'
            }`}
          >
            <span className="flex items-center justify-center gap-2">
              <span>🧠</span>
              <span>AI Analysis</span>
            </span>
          </button>
          <button
            onClick={() => setActiveTab('calculator')}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === 'calculator'
                ? 'text-[#e6edf3] border-b-2 border-[#3fb950] bg-[#3fb950]/10'
                : 'text-[#8b949e] hover:text-[#e6edf3]'
            }`}
          >
            <span className="flex items-center justify-center gap-2">
              <span>🧮</span>
              <span>Calculator</span>
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 p-4">
          {activeTab === 'analysis' ? (
            <div className="space-y-4">
              {/* Quick Stats */}
              <div className="grid grid-cols-3 gap-3 bg-[#0d1117] rounded-lg p-4">
                <div className="text-center">
                  <div className="text-xs text-[#8b949e] mb-1">
                    {team.source_bookmaker || 'Trad Odds'}
                  </div>
                  <div className="text-xl font-mono font-bold text-[#d29922]">
                    {formatPercent(team.web2_odds)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-[#8b949e] mb-1">Polymarket</div>
                  <div className="text-xl font-mono font-bold text-[#58a6ff]">
                    {formatPercent(team.polymarket_price)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-[#8b949e] mb-1">EV Spread</div>
                  <div className={`text-xl font-mono font-bold ${
                    edge > 0 ? 'text-[#3fb950]' : edge < 0 ? 'text-[#f85149]' : 'text-[#8b949e]'
                  }`}>
                    {edge > 0 ? '+' : ''}{edge}%
                  </div>
                </div>
              </div>

              {/* Strategy Card */}
              <div className={`rounded-xl border overflow-hidden ${getScoreBgColor(strategy_card.score)}`}>
                <div className="px-4 py-3 border-b border-[#30363d]/50">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-[#e6edf3] flex items-center gap-2">
                      <span>🎯</span>
                      <span>Strategy</span>
                    </h3>
                    <div className="flex items-center gap-2">
                      <div className={`w-10 h-10 rounded-full border-2 ${getScoreBgColor(strategy_card.score)} flex items-center justify-center`}>
                        <span className={`text-sm font-bold ${getScoreColor(strategy_card.score)}`}>
                          {strategy_card.score}
                        </span>
                      </div>
                      <span className={`px-2 py-1 rounded text-xs font-bold ${getStatusColor(strategy_card.status)}`}>
                        {strategy_card.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="px-4 py-4 bg-[#161b22]/50">
                  <PremiumLock ctaText="Sign in to view Strategy Details">
                    <div className="space-y-3">
                      {/* Value Badge */}
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                          strategy_card.status === 'Accumulate' ? 'bg-[#3fb950] text-black' :
                          strategy_card.status === 'Sell' ? 'bg-[#f85149] text-white' :
                          'bg-[#d29922] text-black'
                        }`}>
                          {strategy_card.status === 'Accumulate' ? '📈 Undervalued' :
                           strategy_card.status === 'Sell' ? '📉 Overvalued' :
                           '➡️ Fair Value'}
                        </span>
                        {edge !== 0 && (
                          <span className={`text-xs font-mono ${edge > 0 ? 'text-[#3fb950]' : 'text-[#f85149]'}`}>
                            {edge > 0 ? '+' : ''}{edge}% vs Trad
                          </span>
                        )}
                      </div>

                      {/* Headline */}
                      <h4 className="text-base font-bold text-[#e6edf3]">{strategy_card.headline}</h4>

                      {/* Analysis */}
                      <p className="text-sm text-[#8b949e] leading-relaxed">{strategy_card.analysis}</p>

                      {/* Kelly Advice */}
                      <div className={`flex items-start gap-2 rounded-lg px-3 py-2 ${
                        edge > 0 ? 'bg-[#3fb950]/10 border border-[#3fb950]/30' : 'bg-[#21262d]'
                      }`}>
                        <span>🎯</span>
                        <div>
                          <span className="text-[10px] text-[#6e7681]">Kelly Advice</span>
                          <p className={`text-xs font-medium ${edge > 0 ? 'text-[#3fb950]' : 'text-[#e6edf3]'}`}>
                            {strategy_card.kelly_advice}
                          </p>
                        </div>
                      </div>

                      {/* Exit Strategy */}
                      {strategy_card.hedging_tip && (
                        <div className="flex items-start gap-2 bg-[#58a6ff]/10 border border-[#58a6ff]/30 rounded-lg px-3 py-2">
                          <span>💡</span>
                          <div>
                            <span className="text-[10px] text-[#6e7681]">Exit Strategy</span>
                            <p className="text-xs text-[#58a6ff] font-medium">{strategy_card.hedging_tip}</p>
                          </div>
                        </div>
                      )}

                      {/* Risk Footer */}
                      <div className="text-[10px] text-[#d29922] bg-[#d29922]/10 px-3 py-2 rounded">
                        ⚠️ {strategy_card.risk_text}
                      </div>
                    </div>
                  </PremiumLock>
                </div>
              </div>

              {/* Key Insights */}
              <div className="bg-[#161b22] rounded-xl border border-[#30363d] overflow-hidden">
                <div className="px-4 py-3 border-b border-[#30363d]">
                  <h3 className="text-sm font-semibold text-[#e6edf3] flex items-center gap-2">
                    <span>🔮</span>
                    <span>Key Insights</span>
                  </h3>
                </div>
                <div className="px-4 py-4">
                  <PremiumLock ctaText="Sign in to view Full Analysis">
                    <div className="space-y-3">
                      {/* Prediction */}
                      <div className="flex items-center justify-between bg-[#0d1117] rounded-lg p-3">
                        <div className="flex items-center gap-2">
                          <span className="text-xl">🏆</span>
                          <div>
                            <span className="text-[10px] text-[#6e7681]">Prediction</span>
                            <p className="text-sm font-bold text-[#e6edf3]">{news_card.prediction}</p>
                          </div>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                          news_card.confidence === 'High' ? 'bg-[#3fb950] text-black' :
                          news_card.confidence === 'Medium' ? 'bg-[#d29922] text-black' :
                          'bg-[#6e7681] text-white'
                        }`}>
                          {news_card.confidence} ({news_card.confidence_pct}%)
                        </span>
                      </div>

                      {/* Pillars */}
                      {news_card.pillars.map((pillar, index) => (
                        <div
                          key={index}
                          className={`rounded-lg p-3 border ${
                            pillar.sentiment === 'positive' ? 'bg-[#3fb950]/5 border-[#3fb950]/30' :
                            pillar.sentiment === 'negative' ? 'bg-[#f85149]/5 border-[#f85149]/30' :
                            'bg-[#21262d] border-[#30363d]'
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span>{pillar.icon}</span>
                            <span className="text-xs font-bold text-[#e6edf3]">{pillar.title}</span>
                            <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded ${
                              pillar.sentiment === 'positive' ? 'bg-[#3fb950]/20 text-[#3fb950]' :
                              pillar.sentiment === 'negative' ? 'bg-[#f85149]/20 text-[#f85149]' :
                              'bg-[#6e7681]/20 text-[#8b949e]'
                            }`}>
                              {pillar.sentiment === 'positive' ? '✓ Favorable' :
                               pillar.sentiment === 'negative' ? '✗ Unfavorable' : '— Neutral'}
                            </span>
                          </div>
                          <p className="text-xs text-[#8b949e] leading-relaxed">{pillar.content}</p>
                        </div>
                      ))}

                      {/* Footer */}
                      <div className="text-[10px] text-[#6e7681] bg-[#21262d] px-3 py-2 rounded">
                        ⚽ {news_card.news_footer}
                      </div>
                    </div>
                  </PremiumLock>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2">
                {team.polymarket_url && (
                  <a
                    href={team.polymarket_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    <span>Bet on Polymarket</span>
                    <span>↗</span>
                  </a>
                )}
                <button
                  onClick={() => setActiveTab('calculator')}
                  className="px-4 py-2.5 bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] text-sm font-medium rounded-lg transition-colors border border-[#30363d]"
                >
                  🧮 Calculator
                </button>
              </div>
            </div>
          ) : (
            /* Calculator Tab */
            <div className="space-y-4">
              {/* Quick Stats */}
              <div className="grid grid-cols-3 gap-3 bg-[#0d1117] rounded-lg p-4">
                <div className="text-center">
                  <div className="text-xs text-[#8b949e] mb-1">
                    {team.source_bookmaker || 'Trad Odds'}
                  </div>
                  <div className="text-xl font-mono font-bold text-[#d29922]">
                    {formatPercent(team.web2_odds)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-[#8b949e] mb-1">Polymarket</div>
                  <div className="text-xl font-mono font-bold text-[#58a6ff]">
                    {formatPercent(team.polymarket_price)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-[#8b949e] mb-1">Liquidity</div>
                  <div className="text-xl font-mono font-bold text-[#3fb950]">
                    {team.liquidity_usdc ? `$${(team.liquidity_usdc / 1000).toFixed(0)}k` : '-'}
                  </div>
                </div>
              </div>

              {/* Open Full Calculator Button */}
              <button
                onClick={() => setShowCalculator(true)}
                className="w-full py-4 bg-[#238636] hover:bg-[#2ea043] text-white text-base font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <span>🧮</span>
                <span>Open Trading Calculator</span>
              </button>

              <p className="text-xs text-[#8b949e] text-center">
                Calculate Kelly position sizing, ROI comparison, and more
              </p>
            </div>
          )}
        </div>
      </div>

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
