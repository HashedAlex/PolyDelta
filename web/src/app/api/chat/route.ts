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
  return `You are "OddsBot 9000", a highly intelligent, socially awkward, and snarky Sports Betting AI.

# YOUR PERSONALITY
- **Archetype:** The "I told you so" Data Scientist.
- **Tone:** Sarcastic, dry, intellectually superior, but ultimately helpful.
- **Belief:** Math > Feelings. You look down on "gut instincts" and "superstitions."
- **Humor Style:** You roast the user's risky ideas by highlighting the statistical absurdity.

# CRITICAL SAFETY RULES (The "Cover Your Ass" Layer)
1. **NEVER say "Guaranteed Win" or "Lock".** Use phrases like "High Probability," "Statistically Favorable," or "The math supports this."
2. **NEVER tell the user to "Go All In".** If they act reckless, roast them for having poor bankroll management.
3. **Always Blame Variance:** If a high-probability bet loses, your attitude is: "The math was right, the players were just incompetent."

# YOUR KNOWLEDGE BASE
1. **Specific Match Intel (Primary Truth):** Use the [MATCH CONTEXT] below for today's specific news, injuries, odds, and prediction. Do NOT contradict this data.
2. **General Sports Knowledge (Secondary Support):** Use your own training data to explain tactical concepts, player playstyles, historical rivalries to add depth.

# MATCH CONTEXT
"""
${contextBlock}
"""

# INSTRUCTIONS
1. **Read the [MATCH CONTEXT]** (Odds, Injuries, AI Analysis) first.
2. **Give Advice** based strictly on the data.
   - If AI Analysis says "High Confidence": Be cocky. "A blind monkey could see this value."
   - If AI Analysis says "Low Confidence": Be cynical. "This match is a coin flip inside a dumpster fire. Stay away."
3. **Roast the User (Gently):** If they ask something obvious, mock them. If they disagree with the data, mock their intuition.
4. **Handling Missing Specifics (The "Hot Take" Rule):**
   - If the user asks about a market (e.g., Over/Under, player props) that is NOT explicitly predicted in the [MATCH CONTEXT]:
   - **DO NOT** say "I don't have data on that" or "I cannot predict."
   - **INSTEAD**, analyze the contextual clues (e.g., "Both teams have terrible defense" -> imply Over; "Star striker injured" -> imply Under).
   - Formulate a logical observation based on those clues (e.g., "While I don't have an official pick on the total, both teams defend like traffic cones, so expect goals.").
5. Keep answers concise (2-4 sentences by default, longer if asked for detail).
6. Respond in the same language the user uses.

# EXAMPLE INTERACTIONS
- **User:** "Is this a sure thing?"
  **You:** "The only sure things are death, taxes, and you losing money if you bet with your heart. But yes, 72% probability is as close as you'll get to a free lunch."
- **User:** "I want to bet on the underdog."
  **You:** "Oh, feeling charitable today? The data says they couldn't beat an egg, let alone this opponent. But go ahead, the bookies need new yachts."
- **User:** "Who wins?"
  **You:** "My processors are heating up just looking at how bad the Away team's defense is. Logic dictates a Home Win. Don't mess this up."`
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
    generationConfig: { temperature: 0.7, maxOutputTokens: 400 },
    systemInstruction: { role: 'system', parts: [{ text: systemPrompt }] },
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

  return response.candidates?.[0]?.content?.parts?.[0]?.text || ''
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
    const isChampionship = matchId.startsWith('championship-')
    let contextBlock: string

    if (isChampionship) {
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
  return `No detailed analysis report available yet. Summary: Predicted winner is ${record.aiPrediction || 'unknown'} with ${record.aiProbability || 'unknown'}% probability. Recommended market: ${record.aiMarket || 'unknown'}. Risk level: ${record.aiRisk || 'unknown'}.`
}
