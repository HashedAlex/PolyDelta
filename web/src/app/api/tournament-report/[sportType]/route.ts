import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

// Map frontend league values to DB sport_type
const SPORT_TYPE_MAP: Record<string, string> = {
  epl: 'epl_winner',
  ucl: 'ucl_winner',
  nba: 'nba_winner',
  world_cup: 'world_cup',
  // Also allow direct DB values
  epl_winner: 'epl_winner',
  ucl_winner: 'ucl_winner',
  nba_winner: 'nba_winner',
}

// GET /api/tournament-report/[sportType]
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ sportType: string }> }
) {
  try {
    const { sportType: rawSportType } = await params
    const sportType = SPORT_TYPE_MAP[rawSportType] || rawSportType

    const report = await prisma.tournamentReport.findUnique({
      where: { sport_type: sportType },
    })

    if (!report) {
      return NextResponse.json(
        { success: false, error: 'No tournament report found for this sport' },
        { status: 404 }
      )
    }

    return NextResponse.json({
      success: true,
      data: {
        sportType: report.sport_type,
        report: report.report_json,
        generatedAt: report.generated_at.toISOString(),
      },
    })
  } catch (error) {
    console.error('[API] Tournament report error:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch tournament report' },
      { status: 500 }
    )
  }
}
