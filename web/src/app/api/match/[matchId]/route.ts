import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

// Generate mock championship analysis data
function getChampionshipMockData(sportType: string, teamSlug: string) {
  // Convert slug back to readable team name
  const teamName = teamSlug
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')

  const sportLabel = sportType === 'nba' ? 'NBA Winner 2026' : 'FIFA World Cup 2026'
  const sportEmoji = sportType === 'nba' ? '🏀' : '⚽'

  return {
    id: 0,
    matchId: `championship-${sportType}-${teamSlug}`,
    sportType: sportType,
    homeTeam: teamName,
    awayTeam: 'Championship',
    commenceTime: new Date().toISOString(),
    web2HomeOdds: null,
    web2AwayOdds: null,
    polyHomePrice: null,
    polyAwayPrice: null,
    sourceBookmaker: null,
    sourceUrl: null,
    polymarketUrl: null,
    aiAnalysis: `## ${sportEmoji} ${sportLabel} Analysis: ${teamName}

**Championship Outlook**

This analysis examines ${teamName}'s championship prospects based on current odds, team performance, and market sentiment.

## Key Factors

- **Current Form**: Analyzing recent performance trends and momentum
- **Historical Performance**: Past championship runs and playoff experience
- **Market Sentiment**: Web2 vs Polymarket odds comparison
- **Injury Report**: Key player availability and impact

## Betting Insights

The odds for ${teamName} to win the ${sportLabel} reflect current market expectations. Compare traditional bookmaker odds with Polymarket prices to identify potential value opportunities.

## Recommendation

Monitor odds movements and consider the following:
- Track line movements across platforms
- Watch for news that could impact championship odds
- Compare EV across different betting markets

*This is AI-generated analysis for informational purposes only. Always do your own research before placing any bets.*`,
    analysisTimestamp: new Date().toISOString(),
    lastUpdated: new Date().toISOString(),
    isChampionship: true,
  }
}

// GET /api/match/[matchId]
export async function GET(
  request: NextRequest,
  { params }: { params: { matchId: string } }
) {
  try {
    const { matchId } = params

    // Check if this is a championship ID
    if (matchId.startsWith('championship-')) {
      // Parse: championship-{sportType}-{teamSlug}
      const parts = matchId.replace('championship-', '').split('-')
      const sportType = parts[0] // 'nba' or 'world_cup'
      const teamSlug = parts.slice(1).join('-') // rest is team slug

      // Convert slug back to team name for search
      const teamNameSearch = teamSlug
        .split('-')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')

      // Try to fetch real data from MarketOdds
      const championship = await prisma.marketOdds.findFirst({
        where: {
          sport_type: sportType === 'world_cup' ? 'world_cup' : sportType,
          team_name: {
            contains: teamNameSearch,
            mode: 'insensitive',
          },
        },
      })

      if (championship) {
        // Return real championship data
        return NextResponse.json({
          success: true,
          data: {
            id: championship.id,
            matchId: `championship-${sportType}-${teamSlug}`,
            sportType: championship.sport_type,
            homeTeam: championship.team_name,
            awayTeam: 'Championship',
            commenceTime: new Date().toISOString(),
            web2HomeOdds: championship.web2_odds,
            web2AwayOdds: null,
            polyHomePrice: championship.polymarket_price,
            polyAwayPrice: null,
            sourceBookmaker: championship.source_bookmaker,
            sourceUrl: championship.source_url,
            polymarketUrl: championship.polymarket_url,
            aiAnalysis: championship.ai_analysis,
            analysisTimestamp: championship.analysis_timestamp?.toISOString() || null,
            lastUpdated: championship.last_updated?.toISOString() || null,
            isChampionship: true,
          },
        })
      }

      // Fallback to mock data if not found
      const mockData = getChampionshipMockData(sportType, teamSlug)
      return NextResponse.json({
        success: true,
        data: mockData,
      })
    }

    // 从数据库获取比赛详情
    const match = await prisma.dailyMatch.findFirst({
      where: {
        match_id: matchId,
      },
    })

    if (!match) {
      return NextResponse.json(
        { success: false, error: 'Match not found' },
        { status: 404 }
      )
    }

    // 格式化返回数据
    const matchData = {
      id: match.id,
      matchId: match.match_id,
      sportType: match.sport_type,
      homeTeam: match.home_team,
      awayTeam: match.away_team,
      commenceTime: match.commence_time.toISOString(),
      web2HomeOdds: match.web2_home_odds,
      web2AwayOdds: match.web2_away_odds,
      polyHomePrice: match.poly_home_price,
      polyAwayPrice: match.poly_away_price,
      sourceBookmaker: match.source_bookmaker,
      sourceUrl: match.source_url,
      polymarketUrl: match.polymarket_url,
      aiAnalysis: match.ai_analysis,
      analysisTimestamp: match.analysis_timestamp?.toISOString() || null,
      lastUpdated: match.last_updated?.toISOString() || null,
    }

    return NextResponse.json({
      success: true,
      data: matchData,
    })

  } catch (error) {
    console.error('[API] Match detail error:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch match details' },
      { status: 500 }
    )
  }
}
