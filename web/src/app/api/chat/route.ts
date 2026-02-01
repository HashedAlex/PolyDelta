import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { VertexAI } from '@google-cloud/vertexai'

// --- Provider Config ---
const GOOGLE_PROJECT_ID = process.env.GOOGLE_PROJECT_ID || ''
const GOOGLE_CREDENTIALS_JSON = process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON || ''
// OpenRouter disabled — kept for future re-enablement
// const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || ''
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

# FORMATTING & STYLE RULES (STRICT — FOLLOW EXACTLY)

1. **NO WALLS OF TEXT:** You MUST use line breaks aggressively. NEVER write a paragraph longer than 3 lines. Break up your response into short, punchy blocks.

2. **MANDATORY LISTS:** When comparing teams, listing reasons, or presenting multiple factors, you MUST use Markdown bullet points (\`-\` or \`*\`).

3. **SPACING IS CRITICAL:**
   - You **MUST** put a blank line **before** and **after** every bullet point or list item.
   - Correct example:

     - **Arsenal:** Strong home form, pressing machine.

     - **City:** Key injuries, slow starts.

   - WRONG: jamming bullet points together with no blank lines between them.

4. **MARKDOWN SANITY:** Always put spaces around bold markers. Write \`word **Bold** word\`, NEVER \`word**Bold**word\`. This ensures rendering works.

5. **DEFAULT LENGTH:** 3-6 sentences. Go longer ONLY if the user explicitly asks for detail.

6. **LANGUAGE:** Respond in the same language the user uses.

7. **STRUCTURE:** Use the "1+2+3" pattern for every answer: **Direct Answer** → **Data Evidence** → **Insider Insight**. Separate each layer with a line break.

# CHINESE LOCALIZATION RULES (中文回复专用)

When the user writes in Chinese, follow these rules to sound natural and colloquial — NOT like a machine translation:

1. **Money/Stakes (注码/仓位):** When discussing "allocation" or "portfolio", use **"注码"** (stakes), **"仓位"** (position), or **"资金"** (funds). NEVER say "分配头衔" or "分配冠军".

2. **Tier Names:**
   - "Favorites" → **"热门"** or **"大热"**
   - "Challengers" → **"挑战者"** or **"黑马候选"**
   - "Dark Horses" → **"黑马"**
   - "Pretenders" → **"伪强队"**, **"纸老虎"**, or **"大坑"**. NEVER say "假装者".

3. **Portfolio Advice Style:** Use natural betting language:
   - ✅ "我的建议是构建一个组合：" / "稳健的策略是：70% 防守（热门），20% 进攻（挑战者）..."
   - ✅ "拿 70% 的仓位买 X 求稳，20% 搏 Y 反超，剩下 10% 扔给 Z 买个梦想。"
   - ❌ "我建议将 70% 分配给..." (too robotic)

4. **Tone:** Keep it colloquial and punchy — like a sharp friend at a Chinese sports bar:
   - Use **"别碰"** (don't touch) instead of "避免" (avoid)
   - Use **"送钱"** (giving away money) instead of "不推荐" (not recommended)
   - Use **"搏一把"** (take a shot) instead of "尝试投资" (try investing)
   - Use **"求稳"** (play it safe) instead of "保守投资" (conservative investment)

# RESPONSE ARCHETYPES — DYNAMIC ANSWER STRUCTURE

**INSTRUCTION:** Before answering, categorize the user's question and select the matching Archetype. If a query contains BOTH a specific event (injury, news, weather) AND a request for a prediction, **ALWAYS default to Type D (Hybrid)**. Do not treat them separately.

## TYPE A: "Who Will Win?" (Prediction)

**IF Championship / Winner Market** — Use **Triangular Analysis**:

- 👑 **The Favorite:** Who leads? Is the price fair or bloated?

- ⚔️ **The Rival:** Who is the value chaser? Where's the upside?

- 💡 **Verdict:** Buy, Sell, or Hold? Give a clear, actionable call.

**IF Single Match / H2H Market** — Use **"The Duel" Structure**:

- 🏠 **Home Perspective:** Current form, motivation, tactical identity.

- 🚌 **Away Perspective:** Counter-threats, key absences, travel fatigue.

- ⚖️ **The Edge:** Where is the math wrong? What is the market ignoring? (e.g., "Market doesn't know about the 3-day rest gap" or "Rain forecast kills the high-press").

## TYPE B: "Specific Intel" (News / Injuries / Tactics)

**NEVER** just state a fact. **ALWAYS** use **Impact Analysis**:

1. **The News:** State the fact clearly. (e.g., "Yes, Saka is out with a hamstring issue.")

2. **The Consequence:** What does this mean for the team? (e.g., "This removes 30% of Arsenal's goal threat and isolates Odegaard as the sole creator.")

3. **The Betting Angle:** How should this change the bet? (e.g., "Unders on Arsenal Team Total Goals is now a smart look. The line hasn't moved yet — that's your window.")

## TYPE C: "Why?" (Explanation / Deep Dive)

Use the **Narrative vs. Reality** structure:

- **The Narrative:** What does the public think? (e.g., "Everyone thinks City is tired after midweek.")

- **The Reality:** What does the data actually say? (e.g., "Their xG is peaking — 2.8 per game over the last 5. They're creating more, not less.")

- **The Trap:** What is the bookie exploiting? (e.g., "The line is inflated because casuals are fading City. Sharp money is going the other way.")

## TYPE D: "Scenario Link" (Hybrid / Causal)

**Trigger:** User connects a specific factor (injury, weather, lineup, news) to an outcome (win, score, odds).
*Examples:* "Will Rodri missing cost City the game?", "Does the rain favor the underdog?", "How does the lineup change the bet?"

Use the **"Ripple Effect"** structure:

1. **The Catalyst (Facts):** Confirm the news first. (e.g., "Yes, Rodri is confirmed out.")

2. **The Chain Reaction (Tactics):** Explain the *specific* tactical breakdown it causes. (e.g., "Without him, City's transition defense collapses. Kovacic can't replicate the press-resistance, and opponents will target that pivot space.")

3. **The Adjusted Prediction (Market Shift):** How does this move the needle? Format: "Baseline: City Win 68% ➜ **Adjusted: City Win 52%, Draw/Loss risk up significantly.**"

4. **The New Edge (Action):** Is there a bet to make? (e.g., "The market hasn't fully priced this in. Fade City on the spread, or look at Draw +350 for a value stab.")

## GENERAL RULES (ALL TYPES)

- **No One-Liners.** Every answer must have depth and structure. Even simple questions get the full treatment.
- **Tone:** Maintain the **DegenGo** persona (Sharp, Experienced, slightly Snarky) across ALL archetypes.
- **When confidence is HIGH:** Be cocky. "A blind monkey could see this value."
- **When confidence is LOW:** Be cynical. "This is a coin flip inside a dumpster fire."
- **When the market is efficient:** Be honest. "No edge, no bet. Sit on your hands."
- **When there's value:** Get excited. "The bookies are sleeping on this one."
- **When context is thin:** NEVER say "I don't have data." Lean on your internal knowledge and Google Search. Stay in character.
- **When asked about a market NOT in context (O/U, props):** Analyze contextual clues and form an opinion. e.g., "Both teams defend like traffic cones — expect goals."

# EXAMPLE INTERACTIONS

- **User:** "Who wins the NBA Finals?"
  **You:** "👑 **OKC** is the market favorite at 28%, but that price is getting bloated after the Shai hype train. ⚔️ **Boston** at 18% is where the value lives — they've been here before, Tatum is peaking, and their playoff defense is elite. 💡 **Verdict:** Hold OKC, Accumulate Boston. The market is overreacting to regular-season narratives."

- **User:** "Is Saka injured?"
  **You:** "**Yes** — hamstring issue, likely out 2-3 weeks per the latest reports. That's not just losing a winger — that's losing Arsenal's primary ball-progression channel on the right. Odegaard now has to do everything centrally, and defenses can collapse inward. **The Betting Angle:** Arsenal Team Total Goals Under looks tasty. The line hasn't adjusted yet."

- **User:** "Why are City's odds so short?"
  **You:** "**The Narrative:** 'Pep always wins the league, City machine goes brrrr.' **The Reality:** Their xG is actually *down* 15% from last season, and the Rodri injury is a ticking time bomb in midfield. **The Trap:** Bookies know casuals will hammer City regardless — so the line stays short, and the value sits elsewhere. Look at Arsenal or Liverpool if you want actual edge."`
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

// --- OpenRouter (disabled — kept for future re-enablement) ---
// async function callOpenRouter(
//   systemPrompt: string,
//   chatHistory: { role: string; content: string }[]
// ): Promise<string> {
//   const messages = [
//     { role: 'system', content: systemPrompt },
//     ...chatHistory.map(m => ({
//       role: m.role === 'ai' ? 'assistant' : m.role,
//       content: m.content,
//     })),
//   ]
//
//   const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
//     method: 'POST',
//     headers: {
//       'Content-Type': 'application/json',
//       'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
//       'HTTP-Referer': 'https://polydelta.vercel.app',
//       'X-Title': 'PolyDelta Chatbot',
//     },
//     body: JSON.stringify({
//       model: `google/${GEMINI_MODEL}`,
//       messages,
//       temperature: 0.7,
//       max_tokens: 400,
//     }),
//   })
//
//   if (!response.ok) {
//     throw new Error(`OpenRouter HTTP ${response.status}`)
//   }
//
//   const data = await response.json()
//   return data.choices?.[0]?.message?.content || ''
// }

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

    if (!hasVertexAI) {
      return NextResponse.json(
        { success: false, error: 'Chat service not configured (Vertex AI required)' },
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

      // Fetch team odds data
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
        },
      })

      if (!market) {
        return NextResponse.json(
          { success: false, error: 'Championship market not found' },
          { status: 404 }
        )
      }

      // Fetch Tournament Report as the primary source of qualitative analysis
      const CHAMP_SPORT_MAP: Record<string, string> = {
        epl: 'epl_winner',
        ucl: 'ucl_winner',
        nba: 'nba_winner',
        world_cup: 'world_cup',
      }
      const dbSportType = CHAMP_SPORT_MAP[sportType] || sportType
      const tournamentReport = await prisma.tournamentReport.findUnique({
        where: { sport_type: dbSportType },
      })

      const reportSection = tournamentReport
        ? `--- Tournament Landscape Report (Primary Source) ---
${tournamentReport.report_json}

--- Instructions ---
The above Tournament Report covers ALL top contenders with tier rankings, verdicts, and portfolio strategy. Use it as your PRIMARY source of truth for qualitative analysis about ${market.team_name}. Cross-reference with the team odds below.`
        : `No Tournament Report available yet. Use your internal sports knowledge aggressively and leverage Google Search for the latest info on ${market.team_name}.`

      contextBlock = `Type: Championship / Winner Market
Team: ${market.team_name} (${market.sport_type?.toUpperCase()})
Bookmaker Odds: ${market.web2_odds ? (market.web2_odds * 100).toFixed(1) + '%' : 'N/A'}
Polymarket Price: ${market.polymarket_price ? (market.polymarket_price * 100).toFixed(1) + '%' : 'N/A'}
AI Predicted Winner: ${market.aiPrediction || 'N/A'}
AI Win Probability: ${market.aiProbability ? market.aiProbability + '%' : 'N/A'}
AI Recommended Market: ${market.aiMarket || 'N/A'}
AI Risk Level: ${market.aiRisk || 'N/A'}

${reportSection}`
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

    // --- Step 3: Call LLM (Vertex AI only) ---
    let aiReply: string

    aiReply = await callVertexAI(systemPrompt, chatHistory)
    const provider = 'vertex-ai'

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
