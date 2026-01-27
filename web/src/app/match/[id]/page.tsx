"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
// Link removed - using router.push for navigation
import ReactMarkdown from 'react-markdown'
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

// Structured AI Analysis Format
interface StrategyCard {
  score: number           // 0-100
  status: 'Buy' | 'Sell' | 'Wait' | 'Accumulate' | 'Hold'  // Daily: Buy/Sell/Wait, Championship: Accumulate/Hold/Sell
  headline: string
  analysis: string
  kelly_advice: string
  risk_text: string
  hedging_tip?: string  // Championship only: exit strategy suggestion
}

// Key Insights Analysis Model
interface PillarAnalysis {
  icon: string
  title: string
  content: string
  sentiment: 'positive' | 'negative' | 'neutral'  // 对 home team 的影响
}

interface NewsCard {
  prediction: string
  confidence: 'High' | 'Medium' | 'Low'  // >75%, 55-75%, <55%
  confidence_pct: number
  pillars: PillarAnalysis[]  // Key Insights (2-3 max)
  factors: string[]  // Legacy support
  news_footer: string
}

interface AIAnalysisData {
  strategy_card: StrategyCard
  news_card: NewsCard
}

// Extended AI Analysis with Kelly Suggestion
interface AIAnalysisDataExtended extends AIAnalysisData {
  kelly_suggestion?: KellySuggestion
}

// === CHAMPIONSHIP FUTURES ANALYSIS GENERATOR ===
// NBA uses "Gauntlet Logic" (Path to Finals, Squad Resilience, Hedging Strategy)
// FIFA uses "Bracket Logic" (Group Stage Survival, Knockout Path, Squad Depth & Manager)
// Note: This function is available for future use when backend AI analysis is not available

function _generateChampionshipAnalysis(
  teamName?: string,
  web2Odds?: number | null,
  polyPrice?: number | null,
  kellySuggestion?: KellySuggestion,
  sportType?: string
): AIAnalysisDataExtended {
  const team = teamName || 'Team'
  const isNBA = sportType === 'nba'

  const odds = web2Odds ?? 0
  const price = polyPrice ?? 0
  const spread = ((odds - price) * 100).toFixed(1)
  const edgePct = kellySuggestion?.edge ?? 0

  // Determine status based on value spread
  let score = 50
  let status: 'Accumulate' | 'Hold' | 'Sell' = 'Hold'
  let headline = 'Fair Value'
  let analysis = ''
  let hedgingTip = ''

  if (isNBA) {
    // === NBA GAUNTLET LOGIC ===
    // Analyze: Path to Finals + Squad Resilience + Hedging Strategy

    if (price < odds - 0.03) {
      // Undervalued - potential +EV Value Bet
      score = 75
      status = 'Accumulate'
      headline = '+EV Value Bet Detected'
      analysis = `${team} is trading at ${(price * 100).toFixed(1)}% on Polymarket vs ${(odds * 100).toFixed(1)}% implied by traditional bookmakers — a ${spread}% spread. This represents a potential +EV opportunity if the team's playoff path is navigable. Key consideration: Conference strength matters. Western Conference teams face "Hard Mode" with deeper competition, while Eastern teams may have easier paths. Monitor seeding closely — Play-In Tournament (seeds 7-10) adds single-elimination volatility that prices often underweight.`
      hedgingTip = `Buy now at $${price.toFixed(2)}. If ${team} reaches the Conference Finals, their price could double to ~$${Math.min(0.50, price * 2.5).toFixed(2)}, allowing a risk-free partial exit while letting the rest ride.`
    } else if (price > odds + 0.02) {
      // Overvalued - potential Trap
      score = 35
      status = 'Sell'
      headline = 'Potential Trap - Recency Bias Risk'
      analysis = `${team} at ${(price * 100).toFixed(1)}% is trading above fair value (${(odds * 100).toFixed(1)}%). ⚠️ Warning: Market may be exhibiting recency bias from recent wins. Futures are won over 4 rounds / 28+ games — current hot streaks rarely sustain. Squad durability is critical: Can their stars survive the playoff grind? Historically, teams with injury-prone cores (Kawhi, Embiid-type situations) underperform their regular season prices.`
      hedgingTip = `If holding, consider selling 30-50% into this strength. Lock in profits before potential injury news or playoff matchup reveals.`
    } else {
      // Fair value - Hold
      score = 55
      status = 'Hold'
      headline = 'Fair Value - No Clear Edge'
      analysis = `${team} is trading near fair value at ${(price * 100).toFixed(1)}% (Trad Odds: ${(odds * 100).toFixed(1)}%). Markets appear efficient — no arbitrage or value edge detected. Rotation depth is key for futures success. Does ${team} have a reliable 7-8 man rotation? Bench units win playoff series when starters fatigue. Monitor trade deadline activity for potential roster upgrades that could shift the value equation.`
      hedgingTip = `No immediate action needed. Set price alerts for dips below $${Math.max(0.05, price * 0.8).toFixed(2)} — that's when value may emerge.`
    }

    // NBA Gauntlet Pillars - DYNAMIC based on team and EV status
    const pillars: PillarAnalysis[] = [
      {
        icon: '🛤️',
        title: price < odds ? `${team}: Market Undervaluation Signal` : `${team}: Overvaluation Warning`,
        content: `${team} Polymarket price ${(price * 100).toFixed(1)}% vs traditional implied odds ${(odds * 100).toFixed(1)}%. ${price < odds ? `A ${spread}% positive EV suggests the market may be undervaluing ${team}'s title chances.` : `Price above fair value - beware of recency bias premium.`} Playoff matchups will be the key validation point.`,
        sentiment: price < odds ? 'positive' : 'neutral'
      },
      {
        icon: '💪',
        title: `${team} Squad Health Factor`,
        content: `NBA playoffs demand 4 rounds / up to 28 games of high-intensity competition. ${team}'s core player availability and injury history are key metrics. Healthy cores perform more consistently in playoffs, while injury-prone teams tend to be overvalued. Bench depth becomes critical in late-series situations.`,
        sentiment: 'neutral'
      },
      {
        icon: '🎯',
        title: `${team} Seeding Impact`,
        content: `Playoff seeding directly impacts championship probability. Seeds 1-3 have home court and face weaker first-round opponents. Seeds 7-10 must survive Play-In with extreme single-game variance. ${team}'s current standing will determine their playoff path difficulty and title EV.`,
        sentiment: price < 0.15 ? 'positive' : 'neutral'
      },
      {
        icon: '📈',
        title: `${team} Hedge Exit Strategy`,
        content: `Futures strategy: Enter at $${price.toFixed(2)} → If ${team} reaches Conference Finals, price projected ~$${Math.min(0.50, price * 2.5).toFixed(2)}, sell 50% to lock profits → Let remainder ride for upside. Key checkpoints: Trade deadline, playoff bracket reveal, Round 1 performance.`,
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
          ? `Conservative 1/10 Kelly for futures. Edge: +${edgePct.toFixed(1)}%. Suggested position: ${(0.1 * edgePct / 100 * 100).toFixed(1)}% of bankroll.`
          : 'No position recommended. Wait for better entry or market inefficiency.',
        risk_text: '⚠️ NBA Futures lock capital for months. Smart contract risk, liquidity risk, and injury variance all apply. Never bet more than you can afford to lose.',
        hedging_tip: hedgingTip
      },
      news_card: {
        prediction: `${team} ${score >= 70 ? 'Championship Contender' : score >= 50 ? 'Conference Finals Ceiling' : 'Early Exit Risk'}`,
        confidence: score >= 70 ? 'High' : score >= 50 ? 'Medium' : 'Low',
        confidence_pct: score,
        pillars,
        factors: [
          `Trad implied: ${(odds * 100).toFixed(1)}%`,
          `Polymarket: ${(price * 100).toFixed(1)}%`,
          `Spread: ${spread}%`
        ],
        news_footer: '🏀 Analysis uses Gauntlet Logic: Path difficulty, squad durability, and hedging opportunities. Recency bias is the enemy of futures investing.'
      },
      kelly_suggestion: kellySuggestion
    }

  } else {
    // === FIFA BRACKET LOGIC ===
    // Analyze: Group Stage Survival + Knockout Path + Squad Depth & Manager

    if (price < odds - 0.03) {
      // Undervalued - potential value
      score = 72
      status = 'Accumulate'
      headline = 'Undervalued - Bracket Difficulty Favors'
      analysis = `${team} is trading at ${(price * 100).toFixed(1)}% on Polymarket vs ${(odds * 100).toFixed(1)}% on traditional books — a ${spread}% edge. Bracket analysis suggests favorable Strength of Schedule. If ${team} tops their group, the R16 crossover likely faces a weaker runner-up, creating a cleaner path to the Quarter-Finals. Tournament Pedigree matters: Nations like Germany, Croatia, and France historically outperform their "paper" odds in knockout football.`
      hedgingTip = `Accumulate at $${price.toFixed(2)}. If ${team} tops their group, exit 50% at ~$${Math.min(0.40, price * 2).toFixed(2)}. Let the rest ride through knockouts with house money.`
    } else if (price > odds + 0.02) {
      // Overvalued - potential trap
      score = 38
      status = 'Sell'
      headline = 'Potential Trap - Group of Death Risk'
      analysis = `${team} at ${(price * 100).toFixed(1)}% is trading above fair value (${(odds * 100).toFixed(1)}%). ⚠️ Warning: If their group contains 2+ Top 15 nations, this is a "Group of Death" scenario. Prices rarely account for the exhaustion of playing starters 90 minutes every group match. Rotation risk is real: Fatigued squads underperform in knockout rounds. Wait for Group Stage volatility before buying.`
      hedgingTip = `If holding, sell 30-50% now. Group stage upsets are common — lock in profits before variance strikes.`
    } else {
      // Fair value - Hold
      score = 52
      status = 'Hold'
      headline = 'Fair Value - Wait for Group Stage'
      analysis = `${team} is trading near fair value at ${(price * 100).toFixed(1)}% (Trad Odds: ${(odds * 100).toFixed(1)}%). No clear edge detected. The smart play: Wait for Group Stage results to create volatility. Prices often overreact to early wins/losses, creating better entry points. Monitor squad announcements and tactical setups — managers with tournament pedigree (e.g., Deschamps, Low) often employ pragmatic, defensive strategies that outperform expectations.`
      hedgingTip = `No action needed. Set alerts for price drops after Group Stage matches — that's when value emerges.`
    }

    // FIFA Bracket Pillars - DYNAMIC based on team and EV status
    const pillars: PillarAnalysis[] = [
      {
        icon: '⚔️',
        title: price < odds ? `${team}: Market Undervaluation Signal` : `${team}: Overvaluation Warning`,
        content: `${team} Polymarket price ${(price * 100).toFixed(1)}% vs traditional implied odds ${(odds * 100).toFixed(1)}%. ${price < odds ? `A ${spread}% positive EV suggests the market may be undervaluing ${team}.` : `Price above fair value - beware of recency bias premium.`} Group stage performance will be the key validation point.`,
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
      },
      {
        icon: '🧠',
        title: `${team} Tournament Experience Factor`,
        content: `World Cup winners often rely on pragmatic tactics over flair. Does ${team}'s manager have knockout experience? Has the core squad been tested in major tournaments? These intangibles carry heavy weight in crucial matches but are often underpriced by markets.`,
        sentiment: 'neutral'
      }
    ]

    return {
      strategy_card: {
        score,
        status,
        headline,
        analysis,
        kelly_advice: edgePct > 0
          ? `Conservative 1/10 Kelly for futures. Edge: +${edgePct.toFixed(1)}%. Suggested position: ${(0.1 * edgePct / 100 * 100).toFixed(1)}% of bankroll.`
          : 'No position recommended. Wait for Group Stage volatility to create better entries.',
        risk_text: '⚠️ World Cup futures lock capital for months. Single-elimination knockout variance is extreme. Never bet more than you can afford to lose.',
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
        news_footer: '⚽ Analysis uses Bracket Logic: Group difficulty, knockout path, and manager pedigree. Strength of Schedule is the key metric for tournament futures.'
      },
      kelly_suggestion: kellySuggestion
    }
  }
}

// Helper to parse AI analysis JSON
function parseAIAnalysis(
  aiAnalysis: string | null,
  homeTeam?: string,
  awayTeam?: string,
  web2Odds?: number | null,
  polyPrice?: number | null,
  isChampionship?: boolean,
  _sportType?: string  // Reserved for future use
): AIAnalysisDataExtended | null {
  // 计算 Kelly 建议 (冠军赛不用套利模式)
  const kellySuggestion = isChampionship
    ? { mode: 'Value Bet (+EV)' as const, win_prob: web2Odds ?? 0.5, net_odds: polyPrice ? (1/polyPrice - 1) : 0, suggestion: 'Accumulate', edge: Math.round(((web2Odds ?? 0) - (polyPrice ?? 0)) * 100) }
    : getKellySuggestion(web2Odds ?? null, polyPrice ?? null, web2Odds ?? 0.5)

  // === CHAMPIONSHIP: 只有数据库有 AI 分析时才显示 ===
  // 如果后端因 <1% 概率跳过了 AI 生成，前端也不显示 Card 3
  if (isChampionship) {
    // 如果数据库没有 AI 分析，不渲染 Card 3
    if (!aiAnalysis) {
      return null
    }

    // 尝试解析数据库中的 AI 分析 (英文或中文，取决于传入的 aiAnalysis)
    try {
      // 尝试多种格式：
      // 1. ```json ... ``` (markdown code block)
      // 2. json\n{...} (AI 返回的格式)
      // 3. 纯 JSON
      let jsonStr = aiAnalysis

      // 格式1: markdown code block
      const markdownMatch = aiAnalysis.match(/```json\n?([\s\S]*?)\n?```/)
      if (markdownMatch) {
        jsonStr = markdownMatch[1]
      }
      // 格式2: "json\n{...}" - AI 返回的格式
      else if (aiAnalysis.startsWith('json\n') || aiAnalysis.startsWith('json\r\n')) {
        jsonStr = aiAnalysis.replace(/^json\s*/, '')
      }
      // 格式3: 纯 JSON (以 { 开头)
      else if (aiAnalysis.trim().startsWith('{')) {
        jsonStr = aiAnalysis.trim()
      }

      const parsed = JSON.parse(jsonStr) as AIAnalysisData
      return { ...parsed, kelly_suggestion: kellySuggestion }
    } catch (e) {
      // JSON解析失败，打印错误以便调试
      console.error('[parseAIAnalysis] JSON parse failed:', e, 'Input:', aiAnalysis?.substring(0, 100))
      return null  // 解析失败也不显示
    }
  }

  // === DAILY MATCH: 需要aiAnalysis才生成 ===
  if (!aiAnalysis) return null

  // 优先尝试解析数据库中的 AI 分析 (英文或中文，取决于传入的 aiAnalysis)
  try {
    // 尝试多种格式：
    // 1. ```json ... ``` (markdown code block)
    // 2. json\n{...} (AI 返回的格式)
    // 3. 纯 JSON
    let jsonStr = aiAnalysis

    // 格式1: markdown code block
    const markdownMatch = aiAnalysis.match(/```json\n?([\s\S]*?)\n?```/)
    if (markdownMatch) {
      jsonStr = markdownMatch[1]
    }
    // 格式2: "json\n{...}" - AI 返回的格式
    else if (aiAnalysis.startsWith('json\n') || aiAnalysis.startsWith('json\r\n')) {
      jsonStr = aiAnalysis.replace(/^json\s*/, '')
    }
    // 格式3: 纯 JSON (以 { 开头)
    else if (aiAnalysis.trim().startsWith('{')) {
      jsonStr = aiAnalysis.trim()
    }

    const parsed = JSON.parse(jsonStr) as AIAnalysisData
    return { ...parsed, kelly_suggestion: kellySuggestion }
  } catch (e) {
    console.error('[parseAIAnalysis] Daily match JSON parse failed:', e, 'Input:', aiAnalysis?.substring(0, 100))
  }

  // Fallback: JSON解析失败时使用前端生成器
  {
    // 日常比赛的fallback分析

    // === DAILY MATCH ANALYSIS ===
    // 根据 Kelly 建议生成动态内容
    let score = 45
    let status: 'Buy' | 'Sell' | 'Wait' = 'Wait'
    let headline = 'No Clear Edge'
    let analysis = ''
    let kellyAdvice = ''

    if (kellySuggestion.mode === 'Arbitrage (Risk-Free)') {
      score = 90
      status = 'Buy'
      headline = 'Arbitrage Opportunity Detected!'
      analysis = `Polymarket price (${((polyPrice ?? 0) * 100).toFixed(1)}%) is significantly lower than ${homeTeam}'s traditional implied odds (${((web2Odds ?? 0) * 100).toFixed(1)}%). This creates a ${kellySuggestion.edge}% edge after fees. The spread indicates traditional books haven't adjusted yet.`
      kellyAdvice = `Full Kelly suggests high confidence buy. Edge: +${kellySuggestion.edge}%`
    } else if (kellySuggestion.mode === 'Value Bet (+EV)') {
      score = 72
      status = 'Buy'
      headline = 'Value Bet Opportunity (+EV)'
      analysis = `Market price (${((polyPrice ?? 0) * 100).toFixed(1)}%) appears undervalued based on AI analysis. Expected edge of ${kellySuggestion.edge}% based on fundamentals. Line movement and news sentiment support this position.`
      kellyAdvice = `Quarter Kelly position recommended. Calculated edge: +${kellySuggestion.edge}%`
    } else {
      score = 40
      status = 'Wait'
      headline = 'No Clear Edge - Wait'
      analysis = `Traditional odds (${((web2Odds ?? 0) * 100).toFixed(1)}%) and Polymarket (${((polyPrice ?? 0) * 100).toFixed(1)}%) are closely aligned. No arbitrage or value opportunity detected after fees. Markets appear efficient.`
      kellyAdvice = 'Do not bet. Edge is below threshold. Wait for better entry.'
    }

    return {
      strategy_card: {
        score,
        status,
        headline,
        analysis,
        kelly_advice: kellyAdvice,
        risk_text: '⚠️ Smart contract risk. Liquidity depth may vary. Always verify before trading.'
      },
      news_card: {
        prediction: `${homeTeam || 'Home Team'} to Win`,
        confidence: (web2Odds ?? 0.5) > 0.65 ? 'High' : (web2Odds ?? 0.5) > 0.5 ? 'Medium' : 'Low',
        confidence_pct: Math.round((web2Odds ?? 0.5) * 100),
        pillars: [
          {
            icon: '🏥',
            title: `Injury/Availability Report`,
            content: `No real-time injury data available for ${homeTeam} vs ${awayTeam}. Check official injury reports before game time. Rest days and back-to-back situations can significantly impact team performance.`,
            sentiment: 'neutral'
          },
          {
            icon: '📈',
            title: `Recent Form`,
            content: `Detailed recent form data unavailable. Consider checking both teams' last 10 games record, home/away splits, and offensive/defensive efficiency rankings to assess current momentum.`,
            sentiment: 'neutral'
          },
          {
            icon: '⚔️',
            title: `Head-to-Head`,
            content: `No season series data available for ${homeTeam} vs ${awayTeam}. H2H records can reveal stylistic matchup advantages, but should be weighed against current roster changes.`,
            sentiment: 'neutral'
          },
          {
            icon: '📊',
            title: `Odds Analysis`,
            content: `Traditional: ${homeTeam} ${((web2Odds ?? 0) * 100).toFixed(1)}% | Polymarket: ${((polyPrice ?? 0) * 100).toFixed(1)}%. ${(web2Odds ?? 0) > (polyPrice ?? 0) ? 'Market may be undervaluing home team.' : (web2Odds ?? 0) < (polyPrice ?? 0) ? 'Market may be overvaluing home team.' : 'Odds closely aligned.'}`,
            sentiment: (web2Odds ?? 0) > (polyPrice ?? 0) ? 'positive' : 'neutral'
          }
        ],
        factors: [
          `Trad implied: ${((web2Odds ?? 0) * 100).toFixed(1)}%`,
          `Polymarket: ${((polyPrice ?? 0) * 100).toFixed(1)}%`
        ],
        news_footer: '🚫 AI analysis based on public data. AI cannot predict random sports events.'
      },
      kelly_suggestion: kellySuggestion
    }
  }
}

// Score color helper
function getScoreColor(score: number): string {
  if (score >= 80) return 'text-[#3fb950]'
  if (score >= 60) return 'text-[#d29922]'
  return 'text-[#f85149]'
}

function getScoreBgColor(score: number): string {
  if (score >= 80) return 'bg-[#3fb950]/20 border-[#3fb950]/50'
  if (score >= 60) return 'bg-[#d29922]/20 border-[#d29922]/50'
  return 'bg-[#f85149]/20 border-[#f85149]/50'
}

function getStatusColor(status: string): string {
  if (status === 'Buy' || status === 'Accumulate') return 'bg-[#3fb950] text-black'
  if (status === 'Sell') return 'bg-[#f85149] text-white'
  if (status === 'Hold') return 'bg-[#d29922] text-black'
  return 'bg-[#6e7681] text-white'  // Wait
}

// Kelly Suggestion Logic - 判断套利/价值投注/无优势
interface KellySuggestion {
  mode: 'Arbitrage (Risk-Free)' | 'Value Bet (+EV)' | 'No Edge'
  win_prob: number
  net_odds: number
  suggestion: string
  edge?: number  // 优势百分比
}

function getKellySuggestion(
  tradOdds: number | null,  // Traditional implied probability (0-1)
  polyPrice: number | null, // Polymarket price (0-1)
  aiWinProb: number = 0.5   // AI predicted win probability (0-1)
): KellySuggestion {
  // 默认无数据时
  if (!tradOdds || !polyPrice || polyPrice === 0) {
    return { mode: 'No Edge', win_prob: 0, net_odds: 0, suggestion: 'Wait - Insufficient data' }
  }

  const marketProb = polyPrice
  const tradProb = tradOdds  // Traditional odds already in probability format

  // 1. 先看有没有套利 (Arbitrage)
  // 如果 Poly 价格显著低于传统庄家 (存在套利)
  if (polyPrice < (tradProb - 0.02)) { // 0.02是手续费缓冲
    const netOdds = (1 / polyPrice) - 1
    const edge = ((tradProb / polyPrice) - 1) * 100
    return {
      mode: 'Arbitrage (Risk-Free)',
      win_prob: 1.0, // 视为必胜
      net_odds: netOdds,
      suggestion: 'Buy High Confidence',
      edge: Math.round(edge * 100) / 100
    }
  }

  // 2. 如果没套利，看有没有价值 (Value Bet)
  // 用 AI 预测的胜率去打败市场的价格
  if (aiWinProb > marketProb + 0.05) { // 至少有 5% 的优势才出手
    const netOdds = (1 / polyPrice) - 1
    const edge = (aiWinProb - marketProb) * 100
    return {
      mode: 'Value Bet (+EV)',
      win_prob: aiWinProb,
      net_odds: netOdds,
      suggestion: 'Buy (AI Edge)',
      edge: Math.round(edge * 100) / 100
    }
  }

  // 3. 既没套利也没价值
  return { mode: 'No Edge', win_prob: aiWinProb, net_odds: 0, suggestion: 'Wait' }
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

function MatchDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [match, setMatch] = useState<MatchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCalculator, setShowCalculator] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'ai'; content: string }[]>([])
  const [fromParam, setFromParam] = useState<string | null>(null)

  const txt = {
    loading: 'Loading match data...',
    notFound: 'Match not found',
    backWorldcup: 'Back to FIFA World Cup',
    backNbaChamp: 'Back to NBA Championship',
    backNbaDaily: 'Back to NBA Daily',
    backDashboard: 'Back to Dashboard',
    nbaChampAnalysis: 'NBA Championship Analysis',
    worldcupAnalysis: 'FIFA World Cup 2026 Analysis',
    nbaDailyMatch: 'NBA Daily Match',
    team: 'Team',
    matchId: 'Match ID',
    oddsComparison: 'Odds Comparison',
    openCalculator: 'Open Calculator',
    championshipOdds: 'Championship Odds',
    viewChampionshipOdds: 'View current championship odds on the main dashboard. Compare traditional bookmaker odds with Polymarket prices to find value betting opportunities.',
    aiAnalysis: 'AI Analysis',
    aiGenerating: 'AI analysis is generating...',
    checkBackLater: 'Check back later. Analysis is generated when EV exceeds threshold.',
    strategy: 'Strategy',
    kellyAdvice: 'Kelly Advice',
    action: 'Action',
    exitStrategy: 'Exit Strategy',
    updated: 'Updated',
    aiPrediction: 'AI Analysis',
    prediction: 'Prediction',
    analysisBreakdown: 'Analysis Breakdown',
    favorable: 'Favorable',
    unfavorable: 'Unfavorable',
    neutral: 'Neutral',
    keyFactors: 'Key Factors',
    askAi: 'Ask AI About This Match',
    askPlaceholder: 'Ask AI about this match...',
    send: 'Send',
    askAbout: 'Ask about odds analysis, team form, betting strategies, or market sentiment.',
    high: 'High',
    medium: 'Medium',
    low: 'Low',
    undervalued: '📈 Undervalued',
    overvalued: '📉 Overvalued',
    fairValue: '➡️ Fair Value',
    vsTrad: 'vs Trad',
    edge: 'Edge',
  }

  // Read URL params on client side
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    setFromParam(urlParams.get('from'))
  }, [])

  // Handle back navigation with explicit router.push
  const handleBack = () => {
    let backUrl = '/'
    switch (fromParam) {
      case 'worldcup':
        backUrl = '/?tab=worldcup'
        break
      case 'nba-championship':
        backUrl = '/?tab=nba&sub=championship'
        break
      case 'nba-daily':
        backUrl = '/?tab=nba&sub=daily'
        break
    }
    router.push(backUrl)
  }

  const getBackLabel = () => {
    switch (fromParam) {
      case 'worldcup':
        return txt.backWorldcup
      case 'nba-championship':
        return txt.backNbaChamp
      case 'nba-daily':
        return txt.backNbaDaily
      default:
        return txt.backDashboard
    }
  }

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
          <p className="text-[#8b949e]">{txt.loading}</p>
        </div>
      </main>
    )
  }

  if (error || !match) {
    return (
      <main className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
        <nav className="sticky top-0 z-40 bg-[#161b22] border-b border-[#30363d] px-6 py-4">
          <button
            onClick={handleBack}
            className="inline-flex items-center gap-2 text-[#8b949e] hover:text-[#e6edf3] transition-colors"
          >
            <span>←</span>
            <span>{getBackLabel()}</span>
          </button>
        </nav>
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="bg-[#161b22] rounded-xl border border-[#f85149] p-6 text-center">
            <p className="text-[#f85149]">{error || txt.notFound}</p>
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
        <button
          onClick={handleBack}
          className="inline-flex items-center gap-2 text-[#8b949e] hover:text-[#e6edf3] transition-colors"
        >
          <span>←</span>
          <span>{getBackLabel()}</span>
        </button>
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
                    <span>{match.sportType === 'nba' ? txt.nbaChampAnalysis : txt.worldcupAnalysis}</span>
                  </p>
                </>
              ) : (
                <>
                  <h1 className="text-2xl font-bold text-[#e6edf3]">
                    {match.homeTeam} <span className="text-[#8b949e] font-normal">vs</span> {match.awayTeam}
                  </h1>
                  <p className="text-[#8b949e] mt-1 flex items-center gap-2">
                    <span>🏀</span>
                    <span>{txt.nbaDailyMatch}</span>
                    <span>•</span>
                    <span>{formatDate(match.commenceTime)}</span>
                  </p>
                </>
              )}
            </div>
            <div className="text-right">
              <div className="text-xs text-[#8b949e]">{match.isChampionship ? txt.team : txt.matchId}</div>
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
                <span>{txt.oddsComparison}</span>
              </h2>
              <button
                onClick={() => setShowCalculator(true)}
                className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                <span>🧮</span>
                <span>{txt.openCalculator}</span>
              </button>
            </div>

            {/* Odds Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[#8b949e] border-b border-[#30363d]">
                    <th className="text-left py-3 font-medium">Team</th>
                    <th className="text-center py-3 font-medium text-[#d29922]">{match.sourceBookmaker || 'Trad Odds'}</th>
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

        {/* Championship Odds Card - Only show for championship */}
        {match.isChampionship && (
          <section className="bg-[#161b22] rounded-xl border border-[#30363d] p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
                <span>🏆</span>
                <span>{txt.championshipOdds}</span>
              </h2>
              <button
                onClick={() => setShowCalculator(true)}
                className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                <span>🧮</span>
                <span>{txt.openCalculator}</span>
              </button>
            </div>

            {/* Odds Display */}
            <div className="bg-[#0d1117] rounded-lg p-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                {/* Traditional Bookmaker */}
                <div>
                  <div className="text-xs text-[#8b949e] mb-1">
                    {match.sourceBookmaker ? (
                      match.sourceUrl ? (
                        <a href={match.sourceUrl} target="_blank" rel="noopener noreferrer" className="text-[#d29922] hover:underline">
                          {match.sourceBookmaker}
                        </a>
                      ) : (
                        <span className="text-[#d29922]">{match.sourceBookmaker}</span>
                      )
                    ) : (
                      'Trad Odds'
                    )}
                  </div>
                  <div className="text-2xl font-mono font-bold text-[#d29922]">
                    {match.web2HomeOdds ? `${(match.web2HomeOdds * 100).toFixed(1)}%` : '-'}
                  </div>
                </div>

                {/* Polymarket */}
                <div>
                  <div className="text-xs text-[#8b949e] mb-1">
                    {match.polymarketUrl ? (
                      <a href={match.polymarketUrl} target="_blank" rel="noopener noreferrer" className="text-[#58a6ff] hover:underline">
                        Polymarket
                      </a>
                    ) : (
                      'Polymarket'
                    )}
                  </div>
                  <div className="text-2xl font-mono font-bold text-[#58a6ff]">
                    {match.polyHomePrice ? `${(match.polyHomePrice * 100).toFixed(1)}%` : '-'}
                  </div>
                </div>

                {/* EV */}
                <div>
                  <div className="text-xs text-[#8b949e] mb-1">EV Diff</div>
                  <div className={`text-2xl font-mono font-bold ${
                    homeEV && homeEV > 0 ? 'text-[#3fb950]' :
                    homeEV && homeEV < 0 ? 'text-[#f85149]' :
                    'text-[#8b949e]'
                  }`}>
                    {homeEV ? `${homeEV > 0 ? '+' : ''}${homeEV.toFixed(1)}%` : '-'}
                  </div>
                </div>
              </div>

              {/* Value indicator */}
              {homeEV && Math.abs(homeEV) >= 5 && (
                <div className={`mt-4 px-4 py-2 rounded-lg text-center text-sm font-medium ${
                  homeEV > 0
                    ? 'bg-[#3fb950]/10 text-[#3fb950] border border-[#3fb950]/30'
                    : 'bg-[#f85149]/10 text-[#f85149] border border-[#f85149]/30'
                }`}>
                  {homeEV > 0
                    ? `📈 Polymarket undervalued by ${homeEV.toFixed(1)}% - Potential value bet`
                    : `📉 Polymarket overvalued by ${Math.abs(homeEV).toFixed(1)}% - Consider selling`
                  }
                </div>
              )}
            </div>
          </section>
        )}

        {/* AI Analysis Cards */}
        {(() => {
          const analysisData = parseAIAnalysis(
            match.aiAnalysis,
            match.homeTeam,
            match.awayTeam,
            match.web2HomeOdds,
            match.polyHomePrice,
            match.isChampionship,
            match.sportType
          )

          if (!analysisData) {
            // If no AI analysis data available, don't render Card 3 at all
            // Only show legacy markdown view if there's actual content
            if (!match.aiAnalysis) {
              return null  // No AI analysis - skip rendering entirely
            }
            // Fallback: Show legacy markdown view for non-JSON content
            return (
              <section className="bg-[#1c2128] rounded-xl border border-[#30363d] overflow-hidden">
                <div className="bg-[#21262d] px-6 py-4 border-b border-[#30363d]">
                  <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
                    <span>🤖</span>
                    <span>{txt.aiAnalysis}</span>
                  </h2>
                </div>
                <div className="px-6 py-6">
                  <div className="prose prose-invert prose-sm max-w-none prose-p:text-[#8b949e]">
                    <ReactMarkdown>{match.aiAnalysis}</ReactMarkdown>
                  </div>
                </div>
              </section>
            )
          }

          const { strategy_card, news_card, kelly_suggestion } = analysisData

          // Mode badge colors
          const getModeColor = (mode: string) => {
            if (mode === 'Arbitrage (Risk-Free)') return 'bg-[#3fb950] text-black'
            if (mode === 'Value Bet (+EV)') return 'bg-[#58a6ff] text-white'
            return 'bg-[#6e7681] text-white'
          }

          return (
            <>
              {/* Card 2: Strategy Card (The Brain) */}
              <section className={`rounded-xl border overflow-hidden ${getScoreBgColor(strategy_card.score)}`}>
                {/* Header with Score */}
                <div className="px-6 py-4 border-b border-[#30363d]/50">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
                      <span>🧠</span>
                      <span>{txt.strategy}</span>
                    </h2>
                    <div className="flex items-center gap-3">
                      {/* Score Circle */}
                      <div className={`w-14 h-14 rounded-full border-4 ${getScoreBgColor(strategy_card.score)} flex items-center justify-center`}>
                        <span className={`text-xl font-bold ${getScoreColor(strategy_card.score)}`}>
                          {strategy_card.score}
                        </span>
                      </div>
                      {/* Status Badge */}
                      <span className={`px-3 py-1.5 rounded-lg text-sm font-bold ${getStatusColor(strategy_card.status)}`}>
                        {strategy_card.status}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="px-6 py-5 space-y-4 bg-[#161b22]/50">
                  {/* Mode Badge - Different for Championship vs Daily */}
                  {match.isChampionship ? (
                    // Championship: Show Undervalued/Fair/Overvalued
                    <div className="flex items-center gap-3">
                      <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${
                        strategy_card.status === 'Accumulate' ? 'bg-[#3fb950] text-black' :
                        strategy_card.status === 'Sell' ? 'bg-[#f85149] text-white' :
                        'bg-[#d29922] text-black'
                      }`}>
                        {strategy_card.status === 'Accumulate' ? '📈 Undervalued' :
                         strategy_card.status === 'Sell' ? '📉 Overvalued' :
                         '➡️ Fair Value'}
                      </span>
                      {kelly_suggestion?.edge && Math.abs(kelly_suggestion.edge) > 0 && (
                        <span className={`text-sm font-mono ${kelly_suggestion.edge > 0 ? 'text-[#3fb950]' : 'text-[#f85149]'}`}>
                          {kelly_suggestion.edge > 0 ? '+' : ''}{kelly_suggestion.edge}% vs Trad
                        </span>
                      )}
                    </div>
                  ) : (
                    // Daily Match: Show Arbitrage/Value Bet/No Edge
                    kelly_suggestion && (
                      <div className="flex items-center gap-3">
                        <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${getModeColor(kelly_suggestion.mode)}`}>
                          {kelly_suggestion.mode}
                        </span>
                        {kelly_suggestion.edge && kelly_suggestion.edge > 0 && (
                          <span className="text-sm font-mono text-[#3fb950]">
                            +{kelly_suggestion.edge}% Edge
                          </span>
                        )}
                      </div>
                    )
                  )}

                  {/* Headline */}
                  <div>
                    <h3 className="text-lg font-bold text-[#e6edf3]">{strategy_card.headline}</h3>
                  </div>

                  {/* Analysis */}
                  <div>
                    <p className="text-sm text-[#8b949e] leading-relaxed">{strategy_card.analysis}</p>
                  </div>

                  {/* Kelly Advice */}
                  <div className={`flex items-start gap-2 rounded-lg px-4 py-3 ${
                    kelly_suggestion?.mode === 'Arbitrage (Risk-Free)' ? 'bg-[#3fb950]/10 border border-[#3fb950]/30' :
                    kelly_suggestion?.mode === 'Value Bet (+EV)' ? 'bg-[#58a6ff]/10 border border-[#58a6ff]/30' :
                    'bg-[#21262d]'
                  }`}>
                    <span>🎯</span>
                    <div>
                      <span className="text-xs text-[#6e7681]">{txt.kellyAdvice}</span>
                      <p className={`text-sm font-medium ${
                        kelly_suggestion?.mode !== 'No Edge' ? 'text-[#3fb950]' : 'text-[#e6edf3]'
                      }`}>{strategy_card.kelly_advice}</p>
                      {kelly_suggestion && (
                        <p className="text-xs text-[#8b949e] mt-1">
                          {txt.action}: <span className="font-medium">{kelly_suggestion.suggestion}</span>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Hedging Tip - Championship Only */}
                  {strategy_card.hedging_tip && (
                    <div className="flex items-start gap-2 bg-[#58a6ff]/10 border border-[#58a6ff]/30 rounded-lg px-4 py-3">
                      <span>💡</span>
                      <div>
                        <span className="text-xs text-[#6e7681]">{txt.exitStrategy}</span>
                        <p className="text-sm text-[#58a6ff] font-medium">{strategy_card.hedging_tip}</p>
                      </div>
                    </div>
                  )}

                  {/* Risk Footer */}
                  <div className="text-xs text-[#d29922] bg-[#d29922]/10 px-4 py-2 rounded-lg">
                    {strategy_card.risk_text}
                  </div>
                </div>

                {/* Timestamp */}
                {match.analysisTimestamp && (
                  <div className="px-6 py-2 bg-[#0d1117]/50 text-xs text-[#6e7681] flex items-center gap-2">
                    <span>🕒</span>
                    <span>{txt.updated}: {getRelativeTime(match.analysisTimestamp)}</span>
                  </div>
                )}
              </section>

              {/* Card 3: News Card (AI Analysis) */}
              <section className="bg-[#161b22] rounded-xl border border-[#30363d] overflow-hidden">
                {/* Header */}
                <div className="px-6 py-4 border-b border-[#30363d]">
                  <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
                    <span>🔮</span>
                    <span>{txt.aiPrediction}</span>
                  </h2>
                </div>

                {/* Content */}
                <div className="px-6 py-5 space-y-4">
                  {/* Prediction with Confidence */}
                  <div className="flex items-center justify-between bg-[#0d1117] rounded-lg p-4">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">🏆</span>
                      <div>
                        <span className="text-xs text-[#6e7681]">{txt.prediction}</span>
                        <p className="text-xl font-bold text-[#e6edf3]">{news_card.prediction}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${
                        news_card.confidence === 'High' ? 'bg-[#3fb950] text-black' :
                        news_card.confidence === 'Medium' ? 'bg-[#d29922] text-black' :
                        'bg-[#6e7681] text-white'
                      }`}>
                        {news_card.confidence} ({news_card.confidence_pct}%)
                      </span>
                    </div>
                  </div>

                  {/* Key Insights */}
                  {news_card.pillars && news_card.pillars.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs text-[#6e7681] uppercase tracking-wider">{txt.analysisBreakdown}</h4>
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
                            <span className="text-sm font-bold text-[#e6edf3]">{pillar.title}</span>
                            <span className={`ml-auto text-xs px-2 py-0.5 rounded ${
                              pillar.sentiment === 'positive' ? 'bg-[#3fb950]/20 text-[#3fb950]' :
                              pillar.sentiment === 'negative' ? 'bg-[#f85149]/20 text-[#f85149]' :
                              'bg-[#6e7681]/20 text-[#8b949e]'
                            }`}>
                              {pillar.sentiment === 'positive' ? `✓ ${txt.favorable}` :
                               pillar.sentiment === 'negative' ? `✗ ${txt.unfavorable}` : `— ${txt.neutral}`}
                            </span>
                          </div>
                          <p className="text-sm text-[#8b949e] leading-relaxed">{pillar.content}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Legacy Factors (fallback) */}
                  {(!news_card.pillars || news_card.pillars.length === 0) && news_card.factors && (
                    <div>
                      <h4 className="text-xs text-[#6e7681] mb-2">{txt.keyFactors}</h4>
                      <ul className="space-y-2">
                        {news_card.factors.map((factor, index) => (
                          <li key={index} className="flex items-start gap-2 text-sm text-[#8b949e]">
                            <span className="text-[#58a6ff] mt-0.5">•</span>
                            <span>{factor}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Disclaimer Footer */}
                  <div className="text-xs text-[#6e7681] bg-[#21262d] px-4 py-2 rounded-lg">
                    {news_card.news_footer}
                  </div>
                </div>
              </section>
            </>
          )
        })()}

        {/* AI Chat Interface */}
        <section className="bg-[#161b22] rounded-xl border border-[#30363d] overflow-hidden">
          <div className="px-6 py-4 border-b border-[#30363d]">
            <h2 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
              <span>💬</span>
              <span>{txt.askAi}</span>
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
                placeholder={txt.askPlaceholder}
                className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-3 text-[#e6edf3] placeholder-[#6e7681] focus:border-[#58a6ff] focus:outline-none"
              />
              <button
                onClick={handleSendMessage}
                className="px-6 py-3 bg-[#58a6ff] hover:bg-[#4493e6] text-white font-medium rounded-lg transition-colors flex items-center gap-2"
              >
                <span>{txt.send}</span>
                <span>→</span>
              </button>
            </div>
            <p className="text-xs text-[#6e7681] mt-2">
              {txt.askAbout}
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

export default MatchDetailPage
