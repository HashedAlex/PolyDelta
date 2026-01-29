import { prisma } from '@/lib/prisma'
import { Dashboard, MarketItem, DailyMatchItem } from '@/components/Dashboard'

// 配置页面为动态渲染，每次请求都重新获取数据
export const dynamic = 'force-dynamic'
export const revalidate = 0

// 计算 EV 差值百分比
function calculateEV(web2Odds: number | null, polyPrice: number | null): number | null {
  if (!web2Odds || !polyPrice || polyPrice === 0) return null
  return ((web2Odds - polyPrice) / polyPrice) * 100
}

export default async function Page() {
  // 从数据库获取冠军盘口数据（仅 championship 类型）
  const allData = await prisma.marketOdds.findMany({
    where: {
      prop_type: 'championship',
    },
    orderBy: [
      { sport_type: 'asc' },
      { web2_odds: 'desc' },
    ],
  })

  // Calculate cutoff: matches that started > 3 hours ago are likely finished
  const matchEndCutoff = new Date(Date.now() - 3 * 60 * 60 * 1000)

  // 从数据库获取每日比赛数据 (NBA)
  const dailyMatchesRaw = await prisma.dailyMatch.findMany({
    where: {
      sport_type: 'nba',
      commence_time: { gt: matchEndCutoff },
    },
    orderBy: {
      commence_time: 'asc',
    },
  })

  // 获取 EPL 比赛数据
  const eplMatchesRaw = await prisma.dailyMatch.findMany({
    where: {
      sport_type: 'epl',
      commence_time: { gt: matchEndCutoff },
    },
    orderBy: {
      commence_time: 'asc',
    },
  })

  // 获取 UCL 比赛数据
  const uclMatchesRaw = await prisma.dailyMatch.findMany({
    where: {
      sport_type: 'ucl',
      commence_time: { gt: matchEndCutoff },
    },
    orderBy: {
      commence_time: 'asc',
    },
  })

  // 按赛事类型分组并处理冠军盘口数据
  const worldCupMarkets: MarketItem[] = []
  const nbaMarkets: MarketItem[] = []
  const eplWinnerMarkets: MarketItem[] = []
  const uclWinnerMarkets: MarketItem[] = []

  allData.forEach((item) => {
    const marketItem: MarketItem = {
      id: item.id,
      team_name: item.team_name,
      web2_odds: item.web2_odds,
      source_bookmaker: item.source_bookmaker,
      source_url: item.source_url,
      polymarket_price: item.polymarket_price,
      polymarket_url: item.polymarket_url,
      ev: calculateEV(item.web2_odds, item.polymarket_price),
      liquidity_usdc: item.liquidity_usdc,
    }

    if (item.sport_type === 'world_cup') {
      worldCupMarkets.push(marketItem)
    } else if (item.sport_type === 'nba') {
      nbaMarkets.push(marketItem)
    } else if (item.sport_type === 'epl_winner') {
      eplWinnerMarkets.push(marketItem)
    } else if (item.sport_type === 'ucl_winner') {
      uclWinnerMarkets.push(marketItem)
    }
  })

  // 处理每日比赛数据 (NBA)
  const dailyMatches: DailyMatchItem[] = dailyMatchesRaw.map((match) => ({
    id: match.id,
    match_id: match.match_id,
    home_team: match.home_team,
    away_team: match.away_team,
    commence_time: match.commence_time,
    web2_home_odds: match.web2_home_odds,
    web2_away_odds: match.web2_away_odds,
    web2_draw_odds: match.web2_draw_odds,
    poly_home_price: match.poly_home_price,
    poly_away_price: match.poly_away_price,
    poly_draw_price: match.poly_draw_price,
    source_bookmaker: match.source_bookmaker,
    source_url: match.source_url,
    polymarket_url: match.polymarket_url,
    ai_analysis: match.ai_analysis,
    analysis_timestamp: match.analysis_timestamp,
    liquidity_home: match.liquidity_home,
    liquidity_away: match.liquidity_away,
    liquidity_draw: match.liquidity_draw,
    sport_type: 'nba',
  }))

  // 处理 EPL 比赛数据
  const eplMatches: DailyMatchItem[] = eplMatchesRaw.map((match) => ({
    id: match.id,
    match_id: match.match_id,
    home_team: match.home_team,
    away_team: match.away_team,
    commence_time: match.commence_time,
    web2_home_odds: match.web2_home_odds,
    web2_away_odds: match.web2_away_odds,
    web2_draw_odds: match.web2_draw_odds,
    poly_home_price: match.poly_home_price,
    poly_away_price: match.poly_away_price,
    poly_draw_price: match.poly_draw_price,
    source_bookmaker: match.source_bookmaker,
    source_url: match.source_url,
    polymarket_url: match.polymarket_url,
    ai_analysis: match.ai_analysis,
    analysis_timestamp: match.analysis_timestamp,
    liquidity_home: match.liquidity_home,
    liquidity_away: match.liquidity_away,
    liquidity_draw: match.liquidity_draw,
    sport_type: 'epl',
  }))

  // 处理 UCL 比赛数据
  const uclMatches: DailyMatchItem[] = uclMatchesRaw.map((match) => ({
    id: match.id,
    match_id: match.match_id,
    home_team: match.home_team,
    away_team: match.away_team,
    commence_time: match.commence_time,
    web2_home_odds: match.web2_home_odds,
    web2_away_odds: match.web2_away_odds,
    web2_draw_odds: match.web2_draw_odds,
    poly_home_price: match.poly_home_price,
    poly_away_price: match.poly_away_price,
    poly_draw_price: match.poly_draw_price,
    source_bookmaker: match.source_bookmaker,
    source_url: match.source_url,
    polymarket_url: match.polymarket_url,
    ai_analysis: match.ai_analysis,
    analysis_timestamp: match.analysis_timestamp,
    liquidity_home: match.liquidity_home,
    liquidity_away: match.liquidity_away,
    liquidity_draw: match.liquidity_draw,
    sport_type: 'ucl',
  }))

  // 按 Polymarket 价格（胜率）排序，热门球队在前
  const sortByPolymarketPrice = (a: MarketItem, b: MarketItem) => {
    const priceA = a.polymarket_price || 0
    const priceB = b.polymarket_price || 0
    return priceB - priceA
  }

  worldCupMarkets.sort(sortByPolymarketPrice)
  nbaMarkets.sort(sortByPolymarketPrice)
  eplWinnerMarkets.sort(sortByPolymarketPrice)
  uclWinnerMarkets.sort(sortByPolymarketPrice)

  // 计算统计数据
  const stats = {
    totalOpportunities: allData.length,
    arbitrageCount: allData.filter(item => {
      const ev = calculateEV(item.web2_odds, item.polymarket_price)
      return ev !== null && Math.abs(ev) >= 5
    }).length,
    dailyMatchCount: dailyMatches.length,
    eplMatchCount: eplMatches.length,
    uclMatchCount: uclMatches.length,
    lastUpdate: allData[0]?.last_updated
      ? new Date(allData[0].last_updated).toLocaleString()
      : 'N/A',
  }

  return (
    <Dashboard
      worldCupMarkets={worldCupMarkets}
      nbaMarkets={nbaMarkets}
      eplWinnerMarkets={eplWinnerMarkets}
      uclWinnerMarkets={uclWinnerMarkets}
      dailyMatches={dailyMatches}
      eplMatches={eplMatches}
      uclMatches={uclMatches}
      stats={stats}
    />
  )
}
