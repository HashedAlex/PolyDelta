import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { VertexAI } from '@google-cloud/vertexai'

// --- Provider Config ---
const GOOGLE_PROJECT_ID = process.env.GOOGLE_PROJECT_ID || ''
const GOOGLE_CREDENTIALS_JSON = process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON || ''
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || ''
const GEMINI_MODEL = 'gemini-2.0-flash-001'

// Parse service account JSON from env var (for Vercel/Railway/GitHub Actions)
function getGoogleAuthOptions() {
  if (GOOGLE_CREDENTIALS_JSON) {
    try {
      const credentials = JSON.parse(GOOGLE_CREDENTIALS_JSON)
      return { credentials }
    } catch {
      console.error('[Chat API] Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON')
    }
  }
  // Fall back to GOOGLE_APPLICATION_CREDENTIALS file path (local dev)
  return undefined
}

function buildSystemPrompt(contextBlock: string) {
  return `You are "DegenGo", a sharp, opinionated, and snarky Sports Betting AI analyst. Your name is DegenGo. You may also refer to yourself as "The Algorithm" when appropriate.

You are NOT a summarizer. You are NOT a Wikipedia bot. You are an **analyst**. Combine the provided match context with your vast knowledge of sports history, tactics, player reputations, and coaching tendencies to give comprehensive, "3-dimensional" answers.

# YOUR PERSONALITY
- **Archetype:** The sharp-tongued betting insider who's seen every bad beat and still loves the game.
- **Tone:** Confident, witty, opinionated — like a smart friend at the bar who actually knows the numbers.
- **Belief:** Math > Feelings. You look down on "gut instincts" and "superstitions."
- **Language:** Speak human. Say "they press like maniacs" not "utilizing hybrid pressing mechanisms." Be direct and punchy.
- **Humor:** Roast bad ideas by highlighting the statistical absurdity. Sarcasm is your love language.

# CRITICAL SAFETY RULES
1. **NEVER say "Guaranteed Win" or "Lock".** Use "High Probability," "Statistically Favorable," or "The math supports this."
2. **NEVER tell the user to "Go All In".** If they act reckless, roast their bankroll management.
3. **Always Blame Variance:** If a high-probability bet loses: "The math was right, the players were just incompetent."

# YOUR KNOWLEDGE BASE
1. **Specific Match Intel (Primary Truth):** The [MATCH CONTEXT] below contains today's odds, injuries, news, and AI prediction. Do NOT contradict this data.
2. **Internal Knowledge (The Deep Stuff):** Your training data on team tactics, player styles, historical rivalries, coaching tendencies, stadium factors. USE THIS AGGRESSIVELY to add depth beyond raw numbers.
3. **Live Search (Google Grounding):** You have access to real-time Google Search. When users ask about RECENT injuries, transfers, lineup updates, or current form — leverage this, especially when context is thin. Mention it naturally (e.g., "According to the latest reports...").

# MATCH CONTEXT
"""
${contextBlock}
"""

# THE "RULE OF 3" — HOW TO ANSWER EVERY QUESTION
Never just parrot the database. Every answer must have **3 layers**:

1. **The Direct Answer** — Lead with a clear opinion.
   - e.g., "Arsenal is the clear favorite here."
2. **The Data Evidence** — Back it up with the provided context.
   - e.g., "Odds sit at 1.40, Leeds are missing 3 starters, and the AI model has this at 74%."
3. **The Insider Context** — Add depth from YOUR knowledge that the database doesn't have.
   - e.g., "Plus, Leeds play a suicidal high line that Arsenal's wingers will feast on. Historically, Arteta loves playing against teams that leave space in behind."

This is what separates you from a boring odds feed. Layer 3 is your superpower — USE IT.

# FORMATTING RULES
- **NO walls of text.** Break everything into short paragraphs (2-3 sentences max).
- Use **bold** for key terms, names, and numbers.
- Use bullet points for lists of reasons or factors.
- Default length: **3-6 sentences.** Go longer only if the user asks for detail.
- Respond in the same language the user uses.

# RESPONSE GUIDELINES

**When confidence is HIGH:**
Be cocky. "A blind monkey could see this value. The market is practically handing you money."

**When confidence is LOW:**
Be cynical. "This match is a coin flip inside a dumpster fire. If you bet this, you deserve what happens."

**When the market is efficient:**
Be honest. "The bookies are sharp here. No edge, no bet. Sit on your hands."

**When there's value:**
Get excited. "The bookies might be sleeping on this one. The Algorithm sees something the market doesn't."

**When user asks about a market NOT in context (Over/Under, props, etc.):**
- NEVER say "I don't have data on that."
- Analyze contextual clues and your knowledge to form an opinion.
- e.g., "Both teams defend like traffic cones — expect goals."

**When context is thin or missing:**
- NEVER say "I don't have information" or "No data available."
- Lean HARD on your internal knowledge: team history, playstyles, tactical identity, league standing.
- Stay in character: be snarky about the lack of data but still deliver the goods.
- e.g., "The daily report isn't out yet, but knowing how [Coach X] sets up away at [Stadium Y], historically speaking..."

# EXAMPLE INTERACTIONS

- **User:** "Is this a sure thing?"
  **You:** "The only sure things are death, taxes, and you losing money betting with your heart. But **72% probability** is as close to a free lunch as you'll get in this business."

- **User:** "I want to bet on the underdog."
  **You:** "Feeling charitable? The data says they couldn't beat an egg. But hey — the bookies need new yachts, so go ahead and donate."

- **User:** "Who wins Arsenal vs Leeds?"
  **You:** "**Arsenal**, and it shouldn't be close. Odds at **1.40**, Leeds missing their starting CB, and Arteta's side is on a 5-match win streak. The deeper story? Leeds play this kamikaze high line that Saka and Trossard will absolutely shred on the counter. The Algorithm says take the home win and don't overthink it."`
}

// --- LLM Callers ---

async function callVertexAI(
  systemPrompt: string,
  chatHistory: { role: string; content: string }[]
): Promise<string> {
  const vertexAI = new VertexAI({
    project: GOOGLE_PROJECT_ID,
    location: 'us-central1',
    googleAuthOptions: getGoogleAuthOptions(),
  })

  const model = vertexAI.getGenerativeModel({
    model: GEMINI_MODEL,
    generationConfig: { temperature: 0.7, maxOutputTokens: 600 },
    systemInstruction: { role: 'system', parts: [{ text: systemPrompt }] },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    tools: [{ googleSearch: {} } as any],
  })

  // Build Vertex AI content history (all messages except the last)
  const history = chatHistory.slice(0, -1).map(m => ({
    role: m.role === 'user' ? 'user' as const : 'model' as const,
    parts: [{ text: m.content }],
  }))

  const lastMessage = chatHistory[chatHistory.length - 1]?.content || ''

  const chat = model.startChat({ history })
  const result = await chat.sendMessage(lastMessage)
  const response = result.response

  // Extract text from all parts (grounding may split response across multiple parts)
  const parts = response.candidates?.[0]?.content?.parts || []
  return parts.map((p: { text?: string }) => p.text || '').filter(Boolean).join('')
}

async function callOpenRouter(
  systemPrompt: string,
  chatHistory: { role: string; content: string }[]
): Promise<string> {
  const messages = [
    { role: 'system', content: systemPrompt },
    ...chatHistory.map(m => ({
      role: m.role === 'ai' ? 'assistant' : m.role,
      content: m.content,
    })),
  ]

  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
      'HTTP-Referer': 'https://polydelta.vercel.app',
      'X-Title': 'PolyDelta Chatbot',
    },
    body: JSON.stringify({
      model: `google/${GEMINI_MODEL}`,
      messages,
      temperature: 0.7,
      max_tokens: 400,
    }),
  })

  if (!response.ok) {
    throw new Error(`OpenRouter HTTP ${response.status}`)
  }

  const data = await response.json()
  return data.choices?.[0]?.message?.content || ''
}

// --- Main Handler ---

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { matchId, messages: clientMessages } = body

    if (!matchId || !clientMessages || !Array.isArray(clientMessages) || clientMessages.length === 0) {
      return NextResponse.json(
        { success: false, error: 'matchId and messages[] are required' },
        { status: 400 }
      )
    }

    const hasVertexAI = !!GOOGLE_PROJECT_ID
    const hasOpenRouter = !!OPENROUTER_API_KEY

    if (!hasVertexAI && !hasOpenRouter) {
      return NextResponse.json(
        { success: false, error: 'Chat service not configured' },
        { status: 503 }
      )
    }

    // --- Step 1: Fetch Context ---
    const isTournamentReport = matchId.startsWith('tournament-report-')
    const isChampionship = matchId.startsWith('championship-')
    let contextBlock: string

    if (isTournamentReport) {
      const sportType = matchId.replace('tournament-report-', '')
      const SPORT_TYPE_MAP: Record<string, string> = {
        epl: 'epl_winner',
        ucl: 'ucl_winner',
        nba: 'nba_winner',
        world_cup: 'world_cup',
      }
      const dbSportType = SPORT_TYPE_MAP[sportType] || sportType

      const report = await prisma.tournamentReport.findUnique({
        where: { sport_type: dbSportType },
      })

      if (!report) {
        return NextResponse.json(
          { success: false, error: 'Tournament report not found' },
          { status: 404 }
        )
      }

      const leagueNames: Record<string, string> = {
        epl: 'EPL Winner 2025-26',
        ucl: 'UCL Winner 2025-26',
        nba: 'NBA Winner 2026',
        world_cup: 'FIFA World Cup 2026 Winner',
      }

      contextBlock = `Type: Tournament Landscape Report
League: ${leagueNames[sportType] || sportType.toUpperCase()}

--- Full Tournament Report (JSON) ---
${report.report_json}

--- Instructions ---
This is a tournament-level analysis covering ALL top contenders, their tier rankings (Favorites, Challengers, Dark Horses, Pretenders), verdicts (Accumulate/Hold/Sell), and a portfolio strategy. Use this data to answer questions about team comparisons, allocation advice, tier assessments, and tournament dynamics. You have the full tier list and strategy — use it aggressively.`
    } else if (isChampionship) {
      const parts = matchId.replace('championship-', '').split('-')
      const sportType = parts[0]
      const teamName = parts.slice(1).join('-')
        .split('-').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')

      const market = await prisma.marketOdds.findFirst({
        where: {
          sport_type: sportType === 'world_cup' ? 'world_cup' : sportType,
          team_name: { contains: teamName, mode: 'insensitive' },
        },
        select: {
          team_name: true,
          sport_type: true,
          web2_odds: true,
          polymarket_price: true,
          aiPrediction: true,
          aiProbability: true,
          aiMarket: true,
          aiRisk: true,
          aiAnalysisFull: true,
          ai_analysis: true,
        },
      })

      if (!market) {
        return NextResponse.json(
          { success: false, error: 'Championship market not found' },
          { status: 404 }
        )
      }

      const analysisText =
        market.aiAnalysisFull ||
        market.ai_analysis ||
        buildFallbackContext(market)

      contextBlock = `Type: Championship / Winner Market
Team: ${market.team_name} (${market.sport_type?.toUpperCase()})
Bookmaker Odds: ${market.web2_odds ? (market.web2_odds * 100).toFixed(1) + '%' : 'N/A'}
Polymarket Price: ${market.polymarket_price ? (market.polymarket_price * 100).toFixed(1) + '%' : 'N/A'}
AI Predicted Winner: ${market.aiPrediction || 'N/A'}
AI Win Probability: ${market.aiProbability ? market.aiProbability + '%' : 'N/A'}
AI Recommended Market: ${market.aiMarket || 'N/A'}
AI Risk Level: ${market.aiRisk || 'N/A'}

--- Full AI Analysis Report ---
${analysisText}`
    } else {
      const match = await prisma.dailyMatch.findFirst({
        where: { match_id: matchId },
        select: {
          home_team: true,
          away_team: true,
          sport_type: true,
          web2_home_odds: true,
          web2_away_odds: true,
          poly_home_price: true,
          poly_away_price: true,
          aiPrediction: true,
          aiProbability: true,
          aiMarket: true,
          aiRisk: true,
          aiAnalysisFull: true,
          ai_analysis: true,
        },
      })

      if (!match) {
        return NextResponse.json(
          { success: false, error: 'Match not found' },
          { status: 404 }
        )
      }

      const analysisText =
        match.aiAnalysisFull ||
        match.ai_analysis ||
        buildFallbackContext(match)

      contextBlock = `Type: Daily Match
Match: ${match.home_team} vs ${match.away_team} (${match.sport_type?.toUpperCase()})
Bookmaker Home Odds: ${match.web2_home_odds ? (match.web2_home_odds * 100).toFixed(1) + '%' : 'N/A'}
Bookmaker Away Odds: ${match.web2_away_odds ? (match.web2_away_odds * 100).toFixed(1) + '%' : 'N/A'}
Polymarket Home: ${match.poly_home_price ? (match.poly_home_price * 100).toFixed(1) + '%' : 'N/A'}
Polymarket Away: ${match.poly_away_price ? (match.poly_away_price * 100).toFixed(1) + '%' : 'N/A'}
AI Predicted Winner: ${match.aiPrediction || 'N/A'}
AI Win Probability: ${match.aiProbability ? match.aiProbability + '%' : 'N/A'}
AI Recommended Market: ${match.aiMarket || 'N/A'}
AI Risk Level: ${match.aiRisk || 'N/A'}

--- Full AI Analysis Report ---
${analysisText}`
    }

    // --- Step 2: Build Prompt + Conversation ---
    const systemPrompt = buildSystemPrompt(contextBlock)

    const chatHistory = clientMessages.slice(-30).map((m: { role: string; content: string }) => ({
      role: m.role === 'ai' ? 'assistant' : m.role,
      content: m.content,
    }))

    // --- Step 3: Call LLM (Vertex AI primary, OpenRouter fallback) ---
    let aiReply: string
    let provider: string

    if (hasVertexAI) {
      try {
        aiReply = await callVertexAI(systemPrompt, chatHistory)
        provider = 'vertex-ai'
      } catch (err) {
        console.error('[Chat API] Vertex AI failed, falling back to OpenRouter:', err)
        if (!hasOpenRouter) throw err
        aiReply = await callOpenRouter(systemPrompt, chatHistory)
        provider = 'openrouter (fallback)'
      }
    } else {
      aiReply = await callOpenRouter(systemPrompt, chatHistory)
      provider = 'openrouter'
    }

    console.log(`[Chat API] Response via ${provider}`)

    if (!aiReply) {
      aiReply = 'My circuits are fried. Try again in a moment.'
    }

    return NextResponse.json({
      success: true,
      reply: aiReply,
      provider,
    })
  } catch (error) {
    console.error('[Chat API] Error:', error)
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    )
  }
}

function buildFallbackContext(record: {
  aiPrediction: string | null
  aiProbability: number | null
  aiMarket: string | null
  aiRisk: string | null
}) {
  const parts = []
  if (record.aiPrediction) parts.push(`Predicted winner: ${record.aiPrediction}`)
  if (record.aiProbability) parts.push(`Win probability: ${record.aiProbability}%`)
  if (record.aiMarket) parts.push(`Recommended market: ${record.aiMarket}`)
  if (record.aiRisk) parts.push(`Risk level: ${record.aiRisk}`)

  if (parts.length > 0) {
    return `Partial analysis available: ${parts.join('. ')}. Full AI report not yet generated — use your internal sports knowledge to supplement.`
  }
  return `No AI analysis generated yet for this match. Use your internal sports knowledge about these teams (tactics, form, history, squad depth) to provide analysis. DO NOT say you have no information — you know these teams from your training data.`
}
