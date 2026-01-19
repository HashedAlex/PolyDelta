import { prisma } from '@/lib/prisma'
import { Dashboard, MarketItem } from '@/components/Dashboard'

// 配置页面为动态渲染，每次请求都重新获取数据
export const dynamic = 'force-dynamic'
export const revalidate = 0

// 计算 EV 差值百分比
function calculateEV(web2Odds: number | null, polyPrice: number | null): number | null {
  if (!web2Odds || !polyPrice || polyPrice === 0) return null
  return ((web2Odds - polyPrice) / polyPrice) * 100
}

export default async function Page() {
  // 从数据库获取所有数据
  const allData = await prisma.marketOdds.findMany({
    orderBy: [
      { sport_type: 'asc' },
      { web2_odds: 'desc' },
    ],
  })

  // 按赛事类型分组并处理数据
  const worldCupMarkets: MarketItem[] = []
  const nbaMarkets: MarketItem[] = []

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
    }

    if (item.sport_type === 'world_cup') {
      worldCupMarkets.push(marketItem)
    } else if (item.sport_type === 'nba') {
      nbaMarkets.push(marketItem)
    }
  })

  // 按 Polymarket 价格（胜率）排序，热门球队在前
  const sortByPolymarketPrice = (a: MarketItem, b: MarketItem) => {
    const priceA = a.polymarket_price || 0
    const priceB = b.polymarket_price || 0
    return priceB - priceA
  }

  worldCupMarkets.sort(sortByPolymarketPrice)
  nbaMarkets.sort(sortByPolymarketPrice)

  // 计算统计数据
  const stats = {
    totalOpportunities: allData.length,
    arbitrageCount: allData.filter(item => {
      const ev = calculateEV(item.web2_odds, item.polymarket_price)
      return ev !== null && Math.abs(ev) >= 5
    }).length,
    lastUpdate: allData[0]?.last_updated
      ? new Date(allData[0].last_updated).toLocaleString()
      : 'N/A',
  }

  return (
    <Dashboard
      worldCupMarkets={worldCupMarkets}
      nbaMarkets={nbaMarkets}
      stats={stats}
    />
  )
}
