import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

// GET /api/history/[eventId]?type=championship|daily&sport=nba|world_cup
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ eventId: string }> }
) {
  try {
    const { eventId } = await params
    const searchParams = request.nextUrl.searchParams
    const eventType = searchParams.get('type') || 'championship'
    const sportType = searchParams.get('sport') || 'nba'

    // 获取历史数据（最近7天）
    const sevenDaysAgo = new Date()
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

    const history = await prisma.oddsHistory.findMany({
      where: {
        event_id: eventId,
        event_type: eventType,
        sport_type: sportType,
        recorded_at: {
          gte: sevenDaysAgo
        }
      },
      orderBy: {
        recorded_at: 'asc'
      },
      select: {
        // Championship fields
        web2_odds: true,
        polymarket_price: true,
        // Daily match fields
        web2_home_odds: true,
        poly_home_price: true,
        recorded_at: true
      }
    })

    // 格式化返回数据 - 根据 eventType 选择正确的字段
    const formattedHistory = history.map(h => {
      // Daily matches use home odds, championship uses single odds
      const web2Value = eventType === 'daily' ? h.web2_home_odds : h.web2_odds
      const polyValue = eventType === 'daily' ? h.poly_home_price : h.polymarket_price

      return {
        web2: web2Value ? Math.round(web2Value * 10000) / 100 : null, // 转为百分比
        poly: polyValue ? Math.round(polyValue * 10000) / 100 : null,
        time: h.recorded_at.toISOString()
      }
    })

    return NextResponse.json({
      success: true,
      eventId,
      eventType,
      sportType,
      data: formattedHistory
    })

  } catch (error) {
    console.error('[API] History error:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch history' },
      { status: 500 }
    )
  }
}
