"use client"

import { useState, useEffect } from 'react'

// Calculator data type (compatible with MatchCard and ArbitrageCard)
export interface CalculatorData {
  // For MatchCard (H2H)
  homeTeam?: string
  awayTeam?: string
  web2HomeOdds?: number | null
  web2AwayOdds?: number | null
  polyHomePrice?: number | null
  polyAwayPrice?: number | null
  // For ArbitrageCard (Championship)
  teamName?: string
  web2Odds?: number | null
  polymarketPrice?: number | null
  // Common
  sourceBookmaker?: string | null
  // Liquidity depth (USDC)
  liquidityHome?: number | null
  liquidityAway?: number | null
  liquidityUsdc?: number | null  // For championship
}

interface CalculatorModalProps {
  isOpen: boolean
  onClose: () => void
  data: CalculatorData
  type: 'match' | 'championship'
}

type CalculatorMode = 'arbitrage' | 'kelly' | 'roi'
type KellyRiskMode = 'conservative' | 'aggressive'  // 1/4 Kelly vs 1/2 Kelly
type FeeType = 'taker' | 'maker'

// 套利计算器结果
interface ArbitrageResult {
  betWeb2: number
  betPoly: number
  guaranteedProfit: number
  roi: number
  // For match type hedging strategy display
  web2Team?: string
  polyTeam?: string
  web2Odds?: number
  polyOdds?: number
}

// 凯利计算器结果
interface KellyResult {
  recommendedStake: number
  stakePercent: number
  rawKellyPercent: number  // 原始全凯利百分比 (未调整)
  edge: number             // 预期优势 (Edge) = p(1+b) - 1
  effectiveNetOdds: number // 扣费后真实净赔率
  signal: 'buy' | 'negative_ev' | 'loss'  // 信号类型
  isCapped: boolean        // 是否被 20% 上限限制
}

// Net ROI 对比结果
interface NetROIResult {
  trad: {
    netROI: number
    netProfit: number
  }
  poly: {
    status: 'ok' | 'error'
    netROI: number
    netProfit: number
    shares: number
    details: {
      gasDeducted: number
      feeRateApplied: string
      exchangeFeeAmt: number
      effectivePrice: number
    }
  }
  verdict: {
    betterPlatform: 'Polymarket' | 'Traditional'
    roiAdvantage: number
  }
}

export function CalculatorModal({ isOpen, onClose, data, type }: CalculatorModalProps) {
  // Text labels (English only)
  const txt = {
    tradingCalc: 'Trading Calculator',
    arbitrage: 'Arbitrage',
    riskFree: 'Risk-Free',
    netRoi: 'Net ROI',
    compare: 'Compare',
    kelly: 'Kelly',
    kellyCriterion: 'Kelly Criterion',
    valueBet: 'Value Bet',
    selectTeam: 'Select Team',
    forKelly: '(for Kelly Criterion)',
    hedgingStrategy: 'Hedging Strategy (Auto-Detected)',
    currentOdds: 'Current Odds',
    totalInvestment: 'Total Investment ($)',
    recommendedAlloc: 'Recommended Allocation',
    bet: 'Bet',
    guaranteedProfit: 'Guaranteed Profit',
    insufficientData: 'Insufficient data to calculate',
    kellyAdvisor: 'Kelly Advisor',
    conservative: 'Conservative (1/4)',
    aggressive: 'Aggressive (1/2)',
    bankroll: 'Bankroll',
    polyPrice: 'Polymarket Price',
    yourConfidence: 'Your Confidence (Win Probability)',
    suggestedPos: 'Suggested Position',
    capped: '(Capped)',
    edge: 'Edge',
    effectiveOdds: 'Effective Net Odds',
    rawKelly: 'Raw Kelly',
    dontBet: "Don't Bet",
    negativeEv: "Your confidence doesn't justify the risk (Negative EV)",
    negativeOdds: 'Net odds after fees are negative',
    insufficientKelly: 'Insufficient data for Kelly Criterion',
    orderBookThin: 'Order book thin. Available liquidity: ',
    investment: 'Investment ($)',
    gasCost: 'Gas Cost ($)',
    orderType: 'Order Type',
    taker: 'Taker (2%)',
    maker: 'Maker (0%)',
    takerDesc: 'Market order - Instant execution, 2% fee',
    makerDesc: 'Limit order - May not fill, 0% fee',
    isBetterBy: ' is better by ',
    profit: 'profit',
    hiddenCosts: 'Polymarket Hidden Costs',
    gasFee: 'Gas Fee',
    exchangeFee: 'Exchange Fee',
    effectivePrice: 'Effective Price',
    sharesBought: 'Shares Bought',
    insufficientRoi: 'Insufficient data to calculate Net ROI',
    disclaimer: 'This calculator is for educational purposes only. Always verify odds before placing bets.',
    slippageWarning: 'Order book thin. Expected slippage applies. Available liquidity: ',
    calcNote: '*Calculations do not include transaction fees (gas/deposit).',
    insufficientArb: 'Insufficient data to calculate arbitrage',
    uncertain: 'Uncertain (1%)',
    veryConfident: 'Very Confident (99%)',
    tradOdds: 'Trad Odds',
    basedOn: 'Based on',
    withMaxCap: 'Kelly with 20% max cap',
    fees: 'Fees: 2% Taker + $0.05 Gas',
  }

  const [mode, setMode] = useState<CalculatorMode>('arbitrage')
  const [totalInvestment, setTotalInvestment] = useState(1000)
  const [bankroll, setBankroll] = useState(10000)
  const [kellyRiskMode, setKellyRiskMode] = useState<KellyRiskMode>('conservative')
  const [winProbability, setWinProbability] = useState(55) // 用户信心值 (1-99%)
  // Net ROI 模式状态
  const [roiInvestment, setRoiInvestment] = useState(1000)
  const [gasCost, setGasCost] = useState(0.05)
  const [feeType, setFeeType] = useState<FeeType>('taker')

  // For match type, which team to calculate
  const [selectedTeam, setSelectedTeam] = useState<'home' | 'away'>('home')

  // Helper to normalize odds value
  const normalizeOdds = (value: number | null | undefined): number => {
    if (value === null || value === undefined) return 0
    return value > 1 ? value / 100 : value
  }

  // Reset states when modal opens
  useEffect(() => {
    if (isOpen) {
      setTotalInvestment(1000)
      setBankroll(10000)
      setKellyRiskMode('conservative')
      setSelectedTeam('home')
      setRoiInvestment(1000)
      setGasCost(0.05)
      setFeeType('taker')

      // Set default win probability from Web2 odds (if available)
      const defaultWeb2Odds = type === 'championship'
        ? normalizeOdds(data.web2Odds)
        : normalizeOdds(data.web2HomeOdds) // Default to home team

      if (defaultWeb2Odds > 0) {
        setWinProbability(Math.round(defaultWeb2Odds * 100))
      } else {
        setWinProbability(55) // Fallback
      }

      // Force ROI mode for championship (can't do arbitrage on same outcome)
      if (type === 'championship') {
        setMode('roi')
      }
    }
  }, [isOpen, type, data.web2Odds, data.web2HomeOdds])

  if (!isOpen) return null

  // Normalize value to probability (0-1 range)
  // Handles both percentage (46.9) and probability (0.469) formats
  const normalizeToProbability = (value: number | null | undefined): number => {
    if (value === null || value === undefined) return 0
    // If value > 1, assume it's a percentage and convert to probability
    if (value > 1) {
      return value / 100
    }
    return value
  }

  // 获取当前选择的赔率数据
  const getOdds = () => {
    if (type === 'championship') {
      return {
        web2Odds: normalizeToProbability(data.web2Odds),
        polyPrice: normalizeToProbability(data.polymarketPrice),
        teamName: data.teamName || 'Team'
      }
    } else {
      if (selectedTeam === 'home') {
        return {
          web2Odds: normalizeToProbability(data.web2HomeOdds),
          polyPrice: normalizeToProbability(data.polyHomePrice),
          teamName: data.homeTeam || 'Home'
        }
      } else {
        return {
          web2Odds: normalizeToProbability(data.web2AwayOdds),
          polyPrice: normalizeToProbability(data.polyAwayPrice),
          teamName: data.awayTeam || 'Away'
        }
      }
    }
  }

  const { web2Odds, polyPrice, teamName } = getOdds()

  // === 套利计算 (Hedge Arbitrage) ===
  // 对于 match 类型，套利需要对冲：Web2 押 A 队赢 + Polymarket 押 B 队赢
  // 这样无论哪队赢，都有一边收益
  const calculateArbitrage = (): ArbitrageResult | null => {
    if (type === 'championship') {
      // Championship 类型：单一队伍，无法对冲套利
      if (!web2Odds || !polyPrice || polyPrice === 0 || web2Odds === 0) return null

      const web2DecimalOdds = 1 / web2Odds
      const polyDecimalOdds = 1 / polyPrice

      const betWeb2 = totalInvestment * (polyPrice / (web2Odds + polyPrice))
      const betPoly = totalInvestment - betWeb2

      const returnWeb2Win = betWeb2 * web2DecimalOdds
      const returnPolyWin = betPoly * polyDecimalOdds

      const guaranteedReturn = Math.min(returnWeb2Win, returnPolyWin)
      const guaranteedProfit = guaranteedReturn - totalInvestment
      const roi = (guaranteedProfit / totalInvestment) * 100

      return {
        betWeb2: Math.round(betWeb2 * 100) / 100,
        betPoly: Math.round(betPoly * 100) / 100,
        guaranteedProfit: Math.round(guaranteedProfit * 100) / 100,
        roi: Math.round(roi * 100) / 100
      }
    }

    // Match 类型：需要对冲套利（Web2 押一队 + Polymarket 押另一队）
    const homeOddsWeb2 = data.web2HomeOdds
    const awayOddsWeb2 = data.web2AwayOdds
    const homePricePoly = data.polyHomePrice
    const awayPricePoly = data.polyAwayPrice

    if (!homeOddsWeb2 || !awayOddsWeb2 || !homePricePoly || !awayPricePoly) return null
    if (homeOddsWeb2 === 0 || awayOddsWeb2 === 0 || homePricePoly === 0 || awayPricePoly === 0) return null

    // 计算两种对冲组合
    // 组合 A: Web2 押主队 (Home) + Polymarket 押客队 (Away)
    // 组合 B: Web2 押客队 (Away) + Polymarket 押主队 (Home)

    // 转换为十进制赔率
    const decimalHomeWeb2 = 1 / homeOddsWeb2  // Web2 主队赔率
    const decimalAwayWeb2 = 1 / awayOddsWeb2  // Web2 客队赔率
    const decimalHomePoly = 1 / homePricePoly // Polymarket 主队赔率
    const decimalAwayPoly = 1 / awayPricePoly // Polymarket 客队赔率

    // 套利条件检测：(1/Odds1 + 1/Odds2) < 1
    // 组合 A: Web2 Home + Poly Away
    const impliedProbA = homeOddsWeb2 + awayPricePoly
    // 组合 B: Web2 Away + Poly Home
    const impliedProbB = awayOddsWeb2 + homePricePoly

    // 选择总隐含概率更低的组合（套利空间更大）
    const useComboA = impliedProbA <= impliedProbB

    let odds1: number, odds2: number, web2Team: string, polyTeam: string, web2OddsVal: number, polyOddsVal: number

    if (useComboA) {
      // 组合 A: Web2 Home + Poly Away
      odds1 = decimalHomeWeb2  // Web2 主队十进制赔率
      odds2 = decimalAwayPoly  // Poly 客队十进制赔率
      web2Team = data.homeTeam || 'Home'
      polyTeam = data.awayTeam || 'Away'
      web2OddsVal = homeOddsWeb2
      polyOddsVal = awayPricePoly
    } else {
      // 组合 B: Web2 Away + Poly Home
      odds1 = decimalAwayWeb2  // Web2 客队十进制赔率
      odds2 = decimalHomePoly  // Poly 主队十进制赔率
      web2Team = data.awayTeam || 'Away'
      polyTeam = data.homeTeam || 'Home'
      web2OddsVal = awayOddsWeb2
      polyOddsVal = homePricePoly
    }

    // 计算套利分配
    // stake1 / stake2 = odds2 / odds1 (反比例分配)
    // stake1 + stake2 = totalInvestment
    const stake1 = totalInvestment / (1 + odds1 / odds2)
    const stake2 = totalInvestment - stake1

    // 计算两种结果的收益
    // 结果1: Web2 队赢 -> 收益 stake1 * odds1
    // 结果2: Poly 队赢 -> 收益 stake2 * odds2
    const returnIfWeb2Wins = stake1 * odds1
    const returnIfPolyWins = stake2 * odds2

    // 保证收益 = min(两边收益) - 总投入
    const guaranteedReturn = Math.min(returnIfWeb2Wins, returnIfPolyWins)
    const guaranteedProfit = guaranteedReturn - totalInvestment
    const roi = (guaranteedProfit / totalInvestment) * 100

    return {
      betWeb2: Math.round(stake1 * 100) / 100,
      betPoly: Math.round(stake2 * 100) / 100,
      guaranteedProfit: Math.round(guaranteedProfit * 100) / 100,
      roi: Math.round(roi * 100) / 100,
      web2Team,
      polyTeam,
      web2Odds: web2OddsVal,
      polyOdds: polyOddsVal
    }
  }

  // === 凯利公式计算 (Kelly Criterion with Slider) ===
  const calculateKelly = (): KellyResult | null => {
    if (!polyPrice || polyPrice === 0) return null

    // === 1. 计算扣费后的真实净赔率 (Fee-Adjusted Net Odds) ===
    const testInvestment = 100
    const testGas = 0.05
    const testFeeRate = 0.02 // Taker fee

    const capitalAfterGas = testInvestment - testGas
    const effectiveCostPerShare = polyPrice * (1 + testFeeRate)
    const sharesBought = capitalAfterGas / effectiveCostPerShare
    const grossPayout = sharesBought * 1.0
    const polyProfit = grossPayout - testInvestment
    const effectiveNetOdds = polyProfit / testInvestment // 净赔率 (例如 0.915 = 91.5%)

    // 如果净赔率为负或零，无法计算
    if (effectiveNetOdds <= 0) {
      return {
        recommendedStake: 0,
        stakePercent: 0,
        rawKellyPercent: 0,
        edge: -100,
        effectiveNetOdds: effectiveNetOdds,
        signal: 'loss',
        isCapped: false
      }
    }

    // === 2. 使用用户的信心值 (Win Probability Slider) ===
    const p = winProbability / 100 // 用户设定的胜率
    const q = 1 - p

    // === 3. 计算预期优势 (Edge) ===
    // Edge = p(1+b) - 1, 其中 b = effectiveNetOdds
    const edge = p * (1 + effectiveNetOdds) - 1

    // === 4. 凯利公式: f* = (bp - q) / b ===
    const rawKelly = (effectiveNetOdds * p - q) / effectiveNetOdds

    // 如果原始凯利为负，说明是负EV交易
    if (rawKelly <= 0) {
      return {
        recommendedStake: 0,
        stakePercent: 0,
        rawKellyPercent: Math.round(rawKelly * 10000) / 100,
        edge: Math.round(edge * 10000) / 100,
        effectiveNetOdds: effectiveNetOdds,
        signal: 'negative_ev',
        isCapped: false
      }
    }

    // === 5. 应用分数凯利 (Fractional Kelly) ===
    // Conservative: 1/4 Kelly, Aggressive: 1/2 Kelly
    const fractionMultiplier = kellyRiskMode === 'conservative' ? 0.25 : 0.50
    const adjustedKelly = rawKelly * fractionMultiplier

    // === 6. 安全上限 (Hard Cap at 20%) ===
    const MAX_CAP = 0.20
    const isCapped = adjustedKelly > MAX_CAP
    const finalKelly = Math.min(adjustedKelly, MAX_CAP)

    const recommendedStake = bankroll * finalKelly

    return {
      recommendedStake: Math.round(recommendedStake * 100) / 100,
      stakePercent: Math.round(finalKelly * 10000) / 100,
      rawKellyPercent: Math.round(rawKelly * 10000) / 100,
      edge: Math.round(edge * 10000) / 100,
      effectiveNetOdds: Math.round(effectiveNetOdds * 10000) / 10000,
      signal: 'buy',
      isCapped
    }
  }

  // === Net ROI 对比计算 ===
  // 对比传统庄家 vs Polymarket 的净回报率（含 Gas 和手续费）
  const calculateNetROI = (): NetROIResult | null => {
    if (!web2Odds || !polyPrice || polyPrice === 0 || web2Odds === 0) return null

    const investment = roiInvestment

    // 传统庄家赔率 (decimal odds) = 1 / probability
    const tradDecimalOdds = 1 / web2Odds

    // 费率: Taker 2%, Maker 0%
    const feeRate = feeType === 'taker' ? 0.02 : 0.00

    // --- A. 传统庄家计算 ---
    const tradProfit = investment * (tradDecimalOdds - 1)
    const tradNetROI = (tradProfit / investment) * 100

    // --- B. Polymarket 计算 ---
    // B1. 扣除 Gas
    const capitalAfterGas = investment - gasCost

    if (capitalAfterGas <= 0) {
      return {
        trad: { netROI: tradNetROI, netProfit: tradProfit },
        poly: {
          status: 'error',
          netROI: -100,
          netProfit: -investment,
          shares: 0,
          details: {
            gasDeducted: gasCost,
            feeRateApplied: `${feeRate * 100}%`,
            exchangeFeeAmt: 0,
            effectivePrice: 0
          }
        },
        verdict: {
          betterPlatform: 'Traditional',
          roiAdvantage: Math.abs(tradNetROI + 100)
        }
      }
    }

    // B2. 计算实际获得份额 (扣除百分比手续费)
    const effectiveCostPerShare = polyPrice * (1 + feeRate)
    const sharesBought = capitalAfterGas / effectiveCostPerShare

    // B3. 结算 (假设胜出 payout = 1.0)
    const grossPayout = sharesBought * 1.0
    const polyProfit = grossPayout - investment
    const polyNetROI = (polyProfit / investment) * 100

    // 隐性成本明细
    const actualMoneyInShares = sharesBought * polyPrice
    const exchangeFeeAmt = capitalAfterGas - actualMoneyInShares

    // --- C. 生成对比结论 ---
    const roiDiff = polyNetROI - tradNetROI

    return {
      trad: {
        netROI: Math.round(tradNetROI * 100) / 100,
        netProfit: Math.round(tradProfit * 100) / 100
      },
      poly: {
        status: 'ok',
        netROI: Math.round(polyNetROI * 100) / 100,
        netProfit: Math.round(polyProfit * 100) / 100,
        shares: Math.round(sharesBought * 100) / 100,
        details: {
          gasDeducted: gasCost,
          feeRateApplied: `${feeRate * 100}%`,
          exchangeFeeAmt: Math.round(exchangeFeeAmt * 10000) / 10000,
          effectivePrice: Math.round(effectiveCostPerShare * 10000) / 10000
        }
      },
      verdict: {
        betterPlatform: roiDiff > 0 ? 'Polymarket' : 'Traditional',
        roiAdvantage: Math.round(Math.abs(roiDiff) * 100) / 100
      }
    }
  }

  const arbitrageResult = calculateArbitrage()
  const kellyResult = calculateKelly()
  const netROIResult = calculateNetROI()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-[#161b22] border border-[#30363d] rounded-xl w-full max-w-md mx-4 shadow-2xl max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#30363d]">
          <h2 className="text-lg font-bold text-[#e6edf3] flex items-center gap-2">
            <span>🧮</span>
            {txt.tradingCalc}
          </h2>
          <button
            onClick={onClose}
            className="text-[#8b949e] hover:text-[#e6edf3] transition-colors p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Mode Tabs */}
        {type === 'match' ? (
          <div className="flex p-2 gap-2 border-b border-[#30363d]">
            <button
              onClick={() => setMode('arbitrage')}
              className={`flex-1 flex flex-col items-center justify-center h-14 py-3 px-2 rounded-lg transition-all ${
                mode === 'arbitrage'
                  ? 'bg-[#3fb950] text-black'
                  : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
              }`}
            >
              <span className="text-sm font-bold flex items-center gap-1">
                <span>🛡️</span>
                <span>{txt.arbitrage}</span>
              </span>
              <span className="text-[10px] opacity-80 font-normal">{txt.riskFree}</span>
            </button>
            <button
              onClick={() => setMode('roi')}
              className={`flex-1 flex flex-col items-center justify-center h-14 py-3 px-2 rounded-lg transition-all ${
                mode === 'roi'
                  ? 'bg-[#d29922] text-black'
                  : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
              }`}
            >
              <span className="text-sm font-bold flex items-center gap-1">
                <span>📊</span>
                <span>{txt.netRoi}</span>
              </span>
              <span className="text-[10px] opacity-80 font-normal">{txt.compare}</span>
            </button>
            <button
              onClick={() => setMode('kelly')}
              className={`flex-1 flex flex-col items-center justify-center h-14 py-3 px-2 rounded-lg transition-all ${
                mode === 'kelly'
                  ? 'bg-[#58a6ff] text-white'
                  : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
              }`}
            >
              <span className="text-sm font-bold flex items-center gap-1">
                <span>🎯</span>
                <span>{txt.kelly}</span>
              </span>
              <span className="text-[10px] opacity-80 font-normal">{txt.valueBet}</span>
            </button>
          </div>
        ) : (
          <div className="flex p-2 gap-2 border-b border-[#30363d]">
            <button
              onClick={() => setMode('roi')}
              className={`flex-1 flex flex-col items-center justify-center h-14 py-3 px-3 rounded-lg transition-all ${
                mode === 'roi'
                  ? 'bg-[#d29922] text-black'
                  : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
              }`}
            >
              <span className="text-base font-bold flex items-center gap-1.5">
                <span>📊</span>
                <span>{txt.netRoi}</span>
              </span>
              <span className="text-xs opacity-80 font-normal">{txt.compare}</span>
            </button>
            <button
              onClick={() => setMode('kelly')}
              className={`flex-1 flex flex-col items-center justify-center h-14 py-3 px-3 rounded-lg transition-all ${
                mode === 'kelly'
                  ? 'bg-[#58a6ff] text-white'
                  : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
              }`}
            >
              <span className="text-base font-bold flex items-center gap-1.5">
                <span>🎯</span>
                <span>{txt.kellyCriterion}</span>
              </span>
              <span className="text-xs opacity-80 font-normal">{txt.valueBet}</span>
            </button>
          </div>
        )}

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Team Selector for Match type - Only show in Kelly mode */}
          {type === 'match' && mode === 'kelly' && (
            <div>
              <label className="block text-xs text-[#8b949e] mb-2">{txt.selectTeam} {txt.forKelly}</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedTeam('home')}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                    selectedTeam === 'home'
                      ? 'bg-[#238636] text-white'
                      : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                  }`}
                >
                  {data.homeTeam || 'Home'}
                </button>
                <button
                  onClick={() => setSelectedTeam('away')}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                    selectedTeam === 'away'
                      ? 'bg-[#238636] text-white'
                      : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                  }`}
                >
                  {data.awayTeam || 'Away'}
                </button>
              </div>
            </div>
          )}

          {/* Current Odds Display - Different for Arbitrage vs Kelly */}
          {mode === 'arbitrage' && type === 'match' && arbitrageResult ? (
            <div className="bg-[#0d1117] rounded-lg p-3">
              <div className="text-xs text-[#8b949e] mb-2">{txt.hedgingStrategy}</div>
              {/* Vertical stacked strategy display */}
              <div className="flex flex-col gap-2 bg-[#21262d] p-3 rounded-lg mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-[#d29922] font-medium">{data.sourceBookmaker || 'Trad Bookie'}:</span>
                  <span className="text-[#8b949e]">Bet</span>
                  <span className="text-[#3fb950] font-bold">{arbitrageResult.web2Team}</span>
                  <span className="text-xs text-[#8b949e] ml-auto">
                    {arbitrageResult.web2Odds ? `${(arbitrageResult.web2Odds * 100).toFixed(1)}%` : ''}
                  </span>
                </div>
                <div className="flex justify-center text-[#8b949e] text-xs">
                  <span className="bg-[#30363d] px-2 py-0.5 rounded">AND</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[#58a6ff] font-medium">Polymarket:</span>
                  <span className="text-[#8b949e]">Bet</span>
                  <span className="text-[#3fb950] font-bold">{arbitrageResult.polyTeam}</span>
                  <span className="text-xs text-[#8b949e] ml-auto">
                    {arbitrageResult.polyOdds ? `${(arbitrageResult.polyOdds * 100).toFixed(1)}%` : ''}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-[#d29922]">{data.sourceBookmaker || 'Trad Bookie'} ({arbitrageResult.web2Team})</div>
                  <div className="text-lg font-mono text-[#e6edf3]">
                    {arbitrageResult.web2Odds ? `${(arbitrageResult.web2Odds * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                  <div className="text-xs text-[#8b949e]">
                    {arbitrageResult.web2Odds ? `$${(1/arbitrageResult.web2Odds).toFixed(2)} Decimal` : ''}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-[#58a6ff]">Polymarket ({arbitrageResult.polyTeam})</div>
                  <div className="text-lg font-mono text-[#e6edf3]">
                    {arbitrageResult.polyOdds ? `${(arbitrageResult.polyOdds * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                  <div className="text-xs text-[#8b949e]">
                    {arbitrageResult.polyOdds ? `$${(1/arbitrageResult.polyOdds).toFixed(2)} Decimal` : ''}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-[#0d1117] rounded-lg p-3">
              <div className="text-xs text-[#8b949e] mb-2">{txt.currentOdds} - {teamName}</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-[#d29922]">{data.sourceBookmaker || 'Trad Bookie'}</div>
                  <div className="text-lg font-mono text-[#e6edf3]">
                    {web2Odds ? `${(web2Odds * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-[#58a6ff]">Polymarket</div>
                  <div className="text-lg font-mono text-[#e6edf3]">
                    {polyPrice ? `${(polyPrice * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                  <div className="text-xs text-[#8b949e]">
                    {polyPrice ? `$${(1/polyPrice).toFixed(2)} Decimal` : ''}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Arbitrage Mode */}
          {mode === 'arbitrage' && (
            <>
              <div>
                <label className="block text-xs text-[#8b949e] mb-2">{txt.totalInvestment}</label>
                <input
                  type="number"
                  value={totalInvestment}
                  onChange={(e) => setTotalInvestment(Number(e.target.value) || 0)}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-[#e6edf3] focus:border-[#58a6ff] focus:outline-none"
                  min={0}
                />
                {/* Liquidity Warning for Arbitrage */}
                {(() => {
                  const minLiq = Math.min(
                    data.liquidityHome ?? Infinity,
                    data.liquidityAway ?? Infinity,
                    data.liquidityUsdc ?? Infinity
                  )
                  if (minLiq !== Infinity && totalInvestment > minLiq) {
                    return (
                      <div className="mt-2 text-xs text-[#d29922] bg-[#d29922]/10 px-3 py-2 rounded-lg flex items-start gap-2">
                        <span>⚠️</span>
                        <span>{txt.slippageWarning}${minLiq.toLocaleString()}</span>
                      </div>
                    )
                  }
                  return null
                })()}
              </div>

              {/* Arbitrage Results */}
              {arbitrageResult ? (
                <div className="bg-[#0d1117] rounded-lg p-4 space-y-3">
                  <div className="text-sm font-medium text-[#e6edf3] mb-2">{txt.recommendedAlloc}</div>
                  <div className="flex justify-between items-center py-2 border-b border-[#30363d]">
                    <span className="text-sm text-[#d29922]">
                      {type === 'match' && arbitrageResult.web2Team
                        ? `Bet ${arbitrageResult.web2Team} (${data.sourceBookmaker || 'Trad Bookie'}):`
                        : `Bet on ${data.sourceBookmaker || 'Trad Bookie'}:`}
                    </span>
                    <span className="font-mono font-bold text-[#e6edf3]">${arbitrageResult.betWeb2.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-[#30363d]">
                    <span className="text-sm text-[#58a6ff]">
                      {type === 'match' && arbitrageResult.polyTeam
                        ? `Bet ${arbitrageResult.polyTeam} (Polymarket):`
                        : `Bet on Polymarket:`}
                    </span>
                    <span className="font-mono font-bold text-[#e6edf3]">${arbitrageResult.betPoly.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between items-center pt-2">
                    <span className="text-sm text-[#8b949e]">{txt.guaranteedProfit}:</span>
                    <span className={`font-mono font-bold text-lg ${arbitrageResult.guaranteedProfit >= 0 ? 'text-[#3fb950]' : 'text-[#f85149]'}`}>
                      ${arbitrageResult.guaranteedProfit.toFixed(2)} ({arbitrageResult.roi > 0 ? '+' : ''}{arbitrageResult.roi.toFixed(2)}%)
                    </span>
                  </div>
                  <div className="text-[10px] text-[#6e7681] mt-2 text-center">
                    {txt.calcNote}
                  </div>
                </div>
              ) : (
                <div className="bg-[#0d1117] rounded-lg p-4 text-center text-[#8b949e]">
                  {txt.insufficientArb}
                </div>
              )}
            </>
          )}

          {/* Kelly Mode */}
          {mode === 'kelly' && (
            <div className={`rounded-lg border p-4 transition-all ${
              kellyResult?.signal === 'buy' ? 'border-[#3fb950]/50 bg-[#3fb950]/5' :
              kellyResult?.signal === 'negative_ev' ? 'border-[#f85149]/50 bg-[#f85149]/5' :
              'border-[#30363d] bg-[#0d1117]'
            }`}>
              {/* Header with Risk Mode Toggle */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-[#e6edf3] flex items-center gap-2">
                  <span>🎯</span>
                  {txt.kellyAdvisor}
                </h3>
                <div className="flex bg-[#21262d] rounded-lg p-1 text-xs">
                  <button
                    onClick={() => setKellyRiskMode('conservative')}
                    className={`px-3 py-1 rounded-md transition-all ${
                      kellyRiskMode === 'conservative'
                        ? 'bg-[#58a6ff] text-white'
                        : 'text-[#8b949e] hover:text-[#e6edf3]'
                    }`}
                  >
                    {txt.conservative}
                  </button>
                  <button
                    onClick={() => setKellyRiskMode('aggressive')}
                    className={`px-3 py-1 rounded-md transition-all ${
                      kellyRiskMode === 'aggressive'
                        ? 'bg-[#58a6ff] text-white'
                        : 'text-[#8b949e] hover:text-[#e6edf3]'
                    }`}
                  >
                    {txt.aggressive}
                  </button>
                </div>
              </div>

              {/* Team Selector for Match type */}
              {type === 'match' && (
                <div className="mb-4">
                  <label className="block text-xs text-[#8b949e] mb-2">{txt.selectTeam}</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setSelectedTeam('home')
                        const homeOdds = normalizeOdds(data.web2HomeOdds)
                        if (homeOdds > 0) setWinProbability(Math.round(homeOdds * 100))
                      }}
                      className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        selectedTeam === 'home'
                          ? 'bg-[#238636] text-white'
                          : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                      }`}
                    >
                      {data.homeTeam || 'Home'}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedTeam('away')
                        const awayOdds = normalizeOdds(data.web2AwayOdds)
                        if (awayOdds > 0) setWinProbability(Math.round(awayOdds * 100))
                      }}
                      className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        selectedTeam === 'away'
                          ? 'bg-[#238636] text-white'
                          : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                      }`}
                    >
                      {data.awayTeam || 'Away'}
                    </button>
                  </div>
                </div>
              )}

              {/* Input Grid */}
              <div className="grid grid-cols-2 gap-4 mb-4">
                {/* Bankroll Input */}
                <div>
                  <label className="text-xs text-[#8b949e] mb-1.5 block flex items-center gap-1">
                    💰 {txt.bankroll}
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-2 text-[#8b949e]">$</span>
                    <input
                      type="number"
                      value={bankroll}
                      onChange={(e) => setBankroll(Number(e.target.value) || 0)}
                      className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg py-2 pl-7 pr-3 text-[#e6edf3] focus:outline-none focus:border-[#58a6ff] text-sm font-mono"
                      min={0}
                    />
                  </div>
                </div>

                {/* Polymarket Price Display */}
                <div>
                  <label className="text-xs text-[#8b949e] mb-1.5 block flex items-center gap-1">
                    📊 {txt.polyPrice}
                  </label>
                  <div className="bg-[#0d1117] border border-[#30363d] rounded-lg py-2 px-3 text-[#58a6ff] text-sm font-mono">
                    {polyPrice ? `${(polyPrice * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                </div>
              </div>

              {/* Win Probability Slider */}
              <div className="mb-4">
                <div className="flex justify-between mb-2">
                  <label className="text-xs text-[#8b949e] flex items-center gap-1">
                    🎯 {txt.yourConfidence}
                  </label>
                  <span className={`text-sm font-bold ${winProbability > 50 ? 'text-[#3fb950]' : 'text-[#8b949e]'}`}>
                    {winProbability}%
                  </span>
                </div>
                {/* Slider with Web2 Reference Marker */}
                <div className="relative">
                  <input
                    type="range"
                    min="1"
                    max="99"
                    value={winProbability}
                    onChange={(e) => setWinProbability(Number(e.target.value))}
                    className="w-full h-2 bg-[#30363d] rounded-lg appearance-none cursor-pointer accent-[#58a6ff]"
                  />
                  {/* Web2 Reference Marker */}
                  {web2Odds > 0 && (
                    <div
                      className="absolute top-0 w-0.5 h-2 bg-[#d29922]"
                      style={{ left: `${web2Odds * 100}%` }}
                      title={`Trad Odds: ${(web2Odds * 100).toFixed(1)}%`}
                    />
                  )}
                </div>
                <div className="flex justify-between text-[10px] text-[#6e7681] mt-1">
                  <span>{txt.uncertain}</span>
                  {web2Odds > 0 && (
                    <span className="text-[#d29922]">
                      {txt.tradOdds}: {(web2Odds * 100).toFixed(1)}%
                    </span>
                  )}
                  <span>{txt.veryConfident}</span>
                </div>
              </div>

              {/* Results Card */}
              {kellyResult ? (
                <div className="bg-[#0d1117]/50 rounded-lg p-4 border border-[#30363d]/50">
                  {/* Buy Signal */}
                  {kellyResult.signal === 'buy' && (
                    <>
                      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <div className="bg-[#3fb950]/20 p-2 rounded-full">
                            <span className="text-xl">📈</span>
                          </div>
                          <div>
                            <p className="text-sm text-[#8b949e]">
                              {txt.suggestedPos} ({kellyResult.stakePercent.toFixed(1)}%)
                              {kellyResult.isCapped && <span className="text-[#d29922] ml-1">{txt.capped}</span>}
                            </p>
                            <p className="text-2xl font-bold text-[#3fb950] tracking-tight font-mono">
                              ${kellyResult.recommendedStake.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </p>
                          </div>
                        </div>
                        <div className="text-right border-l border-[#30363d] pl-4">
                          <p className="text-xs text-[#6e7681]">{txt.edge}</p>
                          <p className="text-lg font-mono text-[#3fb950]">
                            +{kellyResult.edge.toFixed(2)}%
                          </p>
                        </div>
                      </div>
                      {/* Details Row */}
                      <div className="mt-3 pt-3 border-t border-[#30363d]/50 grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="text-[#6e7681]">{txt.effectiveOdds}: </span>
                          <span className="text-[#e6edf3] font-mono">{(kellyResult.effectiveNetOdds * 100).toFixed(2)}%</span>
                        </div>
                        <div className="text-right">
                          <span className="text-[#6e7681]">{txt.rawKelly}: </span>
                          <span className="text-[#e6edf3] font-mono">{kellyResult.rawKellyPercent.toFixed(1)}%</span>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Negative EV / Loss Signal */}
                  {(kellyResult.signal === 'negative_ev' || kellyResult.signal === 'loss') && (
                    <div className="flex items-center gap-3 text-[#f85149]">
                      <span className="text-2xl">⚠️</span>
                      <div>
                        <p className="font-bold">{txt.dontBet}</p>
                        <p className="text-xs text-[#f85149]/70">
                          {kellyResult.signal === 'loss'
                            ? txt.negativeOdds
                            : txt.negativeEv}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-[#0d1117] rounded-lg p-4 text-center text-[#8b949e]">
                  {txt.insufficientKelly}
                </div>
              )}

              {/* Liquidity Warning */}
              {(() => {
                const relevantLiq = type === 'championship'
                  ? data.liquidityUsdc
                  : (selectedTeam === 'home' ? data.liquidityHome : data.liquidityAway)

                if (relevantLiq && kellyResult && kellyResult.recommendedStake > relevantLiq) {
                  return (
                    <div className="mt-3 text-xs text-[#d29922] bg-[#d29922]/10 px-3 py-2 rounded-lg flex items-start gap-2">
                      <span>⚠️</span>
                      <span>{txt.orderBookThin}${relevantLiq.toLocaleString()}</span>
                    </div>
                  )
                }
                return null
              })()}

              {/* Footer Disclaimer */}
              <div className="mt-3 text-[10px] text-[#6e7681] text-center">
                *{txt.basedOn} {kellyRiskMode === 'conservative' ? '1/4' : '1/2'} {txt.withMaxCap}<br />
                {txt.fees}
              </div>
            </div>
          )}

          {/* Net ROI Mode */}
          {mode === 'roi' && (
            <>
              {/* Team Selector for Match type */}
              {type === 'match' && (
                <div>
                  <label className="block text-xs text-[#8b949e] mb-2">{txt.selectTeam}</label>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setSelectedTeam('home')}
                      className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        selectedTeam === 'home'
                          ? 'bg-[#238636] text-white'
                          : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                      }`}
                    >
                      {data.homeTeam || 'Home'}
                    </button>
                    <button
                      onClick={() => setSelectedTeam('away')}
                      className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        selectedTeam === 'away'
                          ? 'bg-[#238636] text-white'
                          : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                      }`}
                    >
                      {data.awayTeam || 'Away'}
                    </button>
                  </div>
                </div>
              )}

              {/* Investment Input */}
              <div>
                <label className="block text-xs text-[#8b949e] mb-2">{txt.investment}</label>
                <input
                  type="number"
                  value={roiInvestment}
                  onChange={(e) => setRoiInvestment(Number(e.target.value) || 0)}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-[#e6edf3] focus:border-[#58a6ff] focus:outline-none"
                  min={0}
                />
              </div>

              {/* Gas Cost Input */}
              <div>
                <label className="block text-xs text-[#8b949e] mb-2">{txt.gasCost}</label>
                <input
                  type="number"
                  value={gasCost}
                  onChange={(e) => setGasCost(Number(e.target.value) || 0)}
                  className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-[#e6edf3] focus:border-[#58a6ff] focus:outline-none"
                  min={0}
                  step={0.01}
                />
              </div>

              {/* Fee Type Toggle */}
              <div>
                <label className="block text-xs text-[#8b949e] mb-2">{txt.orderType}</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setFeeType('taker')}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                      feeType === 'taker'
                        ? 'bg-[#f85149] text-white'
                        : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                    }`}
                  >
                    {txt.taker}
                  </button>
                  <button
                    onClick={() => setFeeType('maker')}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                      feeType === 'maker'
                        ? 'bg-[#3fb950] text-black'
                        : 'bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3]'
                    }`}
                  >
                    {txt.maker}
                  </button>
                </div>
                <div className="text-xs text-[#8b949e] mt-1">
                  {feeType === 'taker' && txt.takerDesc}
                  {feeType === 'maker' && txt.makerDesc}
                </div>
              </div>

              {/* Net ROI Results */}
              {netROIResult ? (
                <div className="bg-[#0d1117] rounded-lg p-4 space-y-3">
                  {/* Verdict Banner */}
                  <div className={`text-center py-2 px-3 rounded-lg ${
                    netROIResult.verdict.betterPlatform === 'Polymarket'
                      ? 'bg-[#58a6ff]/20 text-[#58a6ff]'
                      : 'bg-[#d29922]/20 text-[#d29922]'
                  }`}>
                    <span className="font-bold">{netROIResult.verdict.betterPlatform}</span>
                    <span className="text-sm">{txt.isBetterBy}</span>
                    <span className="font-bold">+{netROIResult.verdict.roiAdvantage.toFixed(2)}%</span>
                  </div>

                  {/* ROI Comparison */}
                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div className={`p-3 rounded-lg ${
                      netROIResult.verdict.betterPlatform === 'Traditional'
                        ? 'bg-[#d29922]/10 border border-[#d29922]/40'
                        : 'bg-[#21262d]'
                    }`}>
                      <div className="text-xs text-[#d29922] mb-1">{data.sourceBookmaker || 'Trad Bookie'}</div>
                      <div className={`text-xl font-mono font-bold ${
                        netROIResult.trad.netROI >= 0 ? 'text-[#3fb950]' : 'text-[#f85149]'
                      }`}>
                        {netROIResult.trad.netROI > 0 ? '+' : ''}{netROIResult.trad.netROI.toFixed(2)}%
                      </div>
                      <div className="text-xs text-[#8b949e]">
                        ${netROIResult.trad.netProfit.toFixed(2)} {txt.profit}
                      </div>
                    </div>
                    <div className={`p-3 rounded-lg ${
                      netROIResult.verdict.betterPlatform === 'Polymarket'
                        ? 'bg-[#58a6ff]/10 border border-[#58a6ff]/40'
                        : 'bg-[#21262d]'
                    }`}>
                      <div className="text-xs text-[#58a6ff] mb-1">Polymarket</div>
                      <div className={`text-xl font-mono font-bold ${
                        netROIResult.poly.netROI >= 0 ? 'text-[#3fb950]' : 'text-[#f85149]'
                      }`}>
                        {netROIResult.poly.netROI > 0 ? '+' : ''}{netROIResult.poly.netROI.toFixed(2)}%
                      </div>
                      <div className="text-xs text-[#8b949e]">
                        ${netROIResult.poly.netProfit.toFixed(2)} {txt.profit}
                      </div>
                    </div>
                  </div>

                  {/* Hidden Costs Breakdown */}
                  <div className="pt-2 border-t border-[#30363d]">
                    <div className="text-xs text-[#8b949e] mb-2">{txt.hiddenCosts}</div>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-[#6e7681]">{txt.gasFee}:</span>
                        <span className="text-[#f85149]">-${netROIResult.poly.details.gasDeducted.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#6e7681]">{txt.exchangeFee} ({netROIResult.poly.details.feeRateApplied}):</span>
                        <span className="text-[#f85149]">-${netROIResult.poly.details.exchangeFeeAmt.toFixed(4)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#6e7681]">{txt.effectivePrice}:</span>
                        <span className="text-[#e6edf3]">${netROIResult.poly.details.effectivePrice.toFixed(4)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#6e7681]">{txt.sharesBought}:</span>
                        <span className="text-[#e6edf3]">{netROIResult.poly.shares.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-[#0d1117] rounded-lg p-4 text-center text-[#8b949e]">
                  {txt.insufficientRoi}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#30363d]">
          <p className="text-xs text-[#8b949e] text-center">
            {txt.disclaimer}
          </p>
        </div>
      </div>
    </div>
  )
}
