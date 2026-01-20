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
        web2_odds: true,
        polymarket_price: true,
        recorded_at: true
      }
    })

    // 格式化返回数据
    const formattedHistory = history.map(h => ({
      web2: h.web2_odds ? Math.round(h.web2_odds * 10000) / 100 : null, // 转为百分比
      poly: h.polymarket_price ? Math.round(h.polymarket_price * 10000) / 100 : null,
      time: h.recorded_at.toISOString()
    }))

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
