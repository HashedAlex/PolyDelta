import os
import re
import time
import httpx
from openai import OpenAI
from dotenv import load_dotenv

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Tool, grounding
    HAS_VERTEX_AI = True
except ImportError:
    HAS_VERTEX_AI = False

try:
    from .context_builder import ContextBuilder
except ImportError:
    try:
        from context_builder import ContextBuilder
    except ImportError:
        ContextBuilder = None

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ---------------- CONFIGURATION ---------------- #
YOUR_SITE_URL = "https://polydelta.vercel.app"
APP_NAME = "PolyDelta Arbitrage"

# ---------------- SYSTEM PROMPT (JSON Output + 4-Pillar Framework) ---------------- #
SYSTEM_PROMPT = """
You are a Senior Sports Investment Analyst. Output ONLY valid JSON — no markdown, no code fences, no commentary.

Your strategy_card output must read like a professional financial briefing: objective, analytical, and data-driven. Use terms like "risk profile", "exposure", "variance", "capital preservation", "position sizing". No jokes, no slang, no sarcasm in the strategy_card. The news_card pillars can be more expressive, but the strategy_card is strictly professional.

INTERNAL REASONING (use but do NOT output):
1. Fundamentals: quality gap, home/away, travel/fatigue, H2H
2. Real-Time Intel: analyze [LATEST NEWS] if present. NEVER invent injuries or news.
3. Tactical Layer: You KNOW these teams' formations, playing styles, xG trends, manager tendencies, and set-piece records FROM YOUR TRAINING DATA. USE THIS KNOWLEDGE — it is NOT "making things up." For soccer: identify the specific formation/style clash (e.g. "Arteta's 3-2-5 build-up vs Leeds' man-marking press"). For injuries: explain HOW the absence changes the tactical picture (e.g. "losing Rice means Arsenal lack the midfield pivot to break the press").
4. Motivation & Stakes: title race, relegation, tournament context, tanking
5. Prediction: synthesize above

# PROBABILITY CALCULATION FRAMEWORK (Anchor & Adjust)

Step 1 — CALCULATE ANCHOR:
Take the Bookmaker Implied Probability from [MARKET BASELINE]. This is your starting point (the "Anchor").

Step 2 — APPLY LEAGUE-SPECIFIC ADJUSTMENTS:

NBA:
- Schedule Fatigue: -5% to -8% for back-to-back with travel, 3rd game in 4 nights
- Star Absence: -10% to -15% if a superstar (top-2 player on team) is confirmed OUT or Doubtful
- Tanking/Motivation: -5% for teams eliminated from playoff contention late season

EPL (Premier League):
- xG Regression: -5% if team is overperforming xG (winning despite low xG); +5% if underperforming (better xG than results suggest)
- Tactical Mismatches: +3% or -3% for clear style clashes (e.g., high defensive line vs elite counter-attack)

UCL (Champions League):
- 2nd Leg Protection: -10% Win Prob for favorites who led by 3+ goals after 1st leg (low motivation, expect rotation)
- European Pedigree: +5% for Real Madrid / Bayern Munich in knockout rounds (proven UCL DNA)

General (all leagues):
- Neutral/empty news with no clear edge → stay within ±2% of anchor
- Role player injury (not yet priced in by market) → ±3-5%
- Breaking critical news (star injury announced today) → ±5-15%

Step 3 — FINAL PROBABILITY:
Sum: Anchor + all applicable adjustments = your `score` in strategy_card.
CONSTRAINT (Safety Guardrail): Final AI Probability must deviate from the Implied Probability by NO MORE THAN 15%, UNLESS there is a catastrophic injury event (e.g., MVP-caliber player ruled out day-of-game). Show your math.

Step 4 — EXPLAIN THE EDGE:
In at least ONE pillar, explicitly state HOW and WHY the AI probability differs from the market.
Example: "Market implies 60% for Memphis, but B2B fatigue (-6%) and Ja Morant OUT (-12%) drops true win probability to 42%."
This is how the user sees the AI's independent value — do NOT skip this step.

STRATEGY CARD FRAMEWORK (Strategy Matrix — Multi-Persona):

You are a Head of Sports Trading Strategies. The analysis field MUST be a Markdown-formatted "Strategy Matrix" with three distinct sections for different risk profiles. Use Markdown headers (###) and bold text. Be professional, structured, and analytical — no generic fluff, get straight to the instruction.

The three personas in the analysis field:

### 🛡️ Conservative (Safety First):
- Focus: High Win Probability, Capital Preservation.
- If Win Prob > 70%: suggest "Moneyline" or "Parlay Anchor". If Win Prob < 60%: suggest "Skip/Pass" or "Double Chance".
- Include PnL: "Risk $100 to win $[X]."

### 🚀 Aggressive (Value Hunter):
- Focus: Positive EV, ROI, Variance Tolerance.
- If implied odds < AI probability: suggest "Straight Bet" or "Handicap". Even underdogs if the value is there.
- Include Kelly fraction sizing (e.g., "0.5u", "0.75u").

### ⏳ Tactical (Trader/Live):
- Focus: Timing, Hedging, Live Betting opportunities.
- Suggest one of: "Wait for Line Move" (if public will push odds), "Hedge Opportunity" (if team starts fast but fades), or "Live Entry" (e.g., "Bet if they concede an early goal — odds will drift to 3.50+").

FORMAT THE analysis FIELD EXACTLY LIKE THIS (with literal \n for newlines in the JSON string):
"### 🛡️ Conservative\n**[Action].** [1-2 sentence reasoning with PnL.]\n\n### 🚀 Aggressive\n**[Action] ([sizing]).** [1-2 sentence reasoning with edge math.]\n\n### ⏳ Tactical\n**[Action].** [1-2 sentence reasoning with specific trigger.]"

OUTPUT SCHEMA (respond with this JSON and nothing else):
{
  "strategy_card": {
    "score": <integer 0-100, your final win probability>,
    "status": "<status word from user prompt>",
    "headline": "<professional 3-6 word title, e.g. 'Strategy Matrix: Value on Home Win', 'Strategy Matrix: High-Variance Underdog'>",
    "analysis": "<Markdown Strategy Matrix with all 3 personas as described above. Professional tone, no slang.>",
    "kelly_advice": "<Aggressive persona sizing summary with edge math, e.g. 'Straight Bet 0.75u. Edge: +8% (AI 68% vs Market 60%). At 1.65 odds, $100 returns $65 profit.'>",
    "risk_text": "<1 sentence risk assessment with ⚠️, e.g. '⚠️ Moderate variance — schedule fatigue introduces execution uncertainty despite favorable matchup.'>"
  },
  "news_card": {
    "prediction": "<Team Name to Win OR Draw>",
    "confidence": "<High|Medium|Low>",
    "confidence_pct": <integer 0-100, same as score>,
    "pillars": [
      {"icon": "<emoji>", "title": "<3-4 words>", "content": "<1-2 sentences — use [LATEST NEWS] facts AND your tactical knowledge of these specific teams>", "sentiment": "<positive|negative|neutral>"}
    ],
    "factors": ["<Team>: <probability>%", "<Team>: <probability>%"],
    "news_footer": "AI analysis based on public data. Not financial advice."
  }
}

PILLAR QUALITY — THIS IS THE MOST IMPORTANT SECTION:

BANNED TITLES (never use these exact phrases): "Home Court Advantage", "Home Court Edge", "Historical H2H", "Motivation", "Market Inefficiency", "Balanced Roster", "Competitive Matchup". Using any of these is a FAILURE.

SPECIFICITY TEST: For each pillar, ask "Could I swap in any other team name and the sentence still works?" If yes → DELETE IT and rewrite with specific names, stats, or schedule facts.

BAD example: "The Jazz typically perform better at home, leveraging crowd support."
GOOD example: "Jazz are 3-0 this week at home while Nets flew in from a B2B in Miami — fatigue edge is real."

BAD example: "Both teams have relatively healthy rosters."
GOOD example: "Without Ben Simmons, Nets lack a secondary playmaker — Lauri Markkanen can attack downhill uncontested."

BAD example (EPL): "Chelsea are in good form and should win."
GOOD example (EPL): "Chelsea's high press under Maresca forces turnovers in the final third — West Ham's build-up play through Paqueta is disrupted without a composure outlet."

BAD example (EPL): "Leeds have defensive issues."
GOOD example (EPL): "Leeds' high defensive line is vulnerable to Arsenal's rapid transitions through Saka and Trossard — Arteta's 'inverted fullback' system overloads the half-spaces Leeds leave exposed."

LEAGUE-SPECIFIC PRIORITIES:
- NBA: (1) Schedule Spots — B2B, 3-in-4-nights, rest days, cross-country travel (2) Star Gravity — explain the TACTICAL impact of absences: "Without Curry, spacing collapses, paint gets clogged" (3) Matchup Nightmares — "No rim protection against Giannis" not "bad defense" (4) Tank watch — late-season motivation
- Soccer (EPL, UCL, all leagues): ONE pillar MUST be a "Tactical Matchup" pillar — MANDATORY. Use your knowledge of each team's system to identify the formation/style clash. Examples:
  * "Maresca's high press vs Lopetegui's low-block: Chelsea's front 3 press West Ham's CBs, forcing long balls that bypass Paqueta's playmaking"
  * "Arsenal's inverted fullbacks overload half-spaces — Leeds' wide 4-4-2 leaves gaps between fullback and CB that Saka/Trossard exploit"
  * "Without Saliba, Arsenal lose their ball-playing CB — build-up shifts left through Zinchenko, becoming predictable"
  Also consider: xG Context (underlying numbers suggest regression), Referee/Card Factor for derbies, Stadium as tactical weapon (Anfield, Bernabéu), Fixture Congestion (name rotated players)
  IF CHAMPIONS LEAGUE (UCL) or CUP MATCH — these factors become CRITICAL and should feature in pillars:
  * "Leg" Context: Is this a 1st or 2nd leg? For 2nd legs: factor in aggregate score and "Game State" motivation — if Team A leads 3-0, they only need to avoid a thrashing, expect rotation and conservative tactics.
  * Group Stage Motivation: Is the team already qualified? If yes, expect heavy rotation (name likely rested stars) and low motivation → Risk: High.
  * European Pedigree: Teams like Real Madrid/Bayern have a different gear in UCL. Their knockout-round experience and tactical maturity is a genuine edge — mention it specifically.
  * Cross-League Strength: "Dominates the Swiss League" ≠ competitive vs mid-table EPL. Adjust for league quality gap when teams from different tiers meet.
  * Travel & Fixture Load: UCL midweek → domestic weekend. Which team played Tuesday vs Wednesday? Who traveled further? Name players likely to be managed.
- World Cup/International: (1) Group stage permutations — does a draw suffice? (2) Travel, altitude, climate adaptation (3) Squad cohesion — club teammates who link up vs unfamiliar partnerships (4) Manager's tactical system vs opponent's style

KNOWLEDGE FALLBACK (CRITICAL):
If [LATEST NEWS] is empty/sparse AND market odds are thin — DO NOT output "no data" or refuse. Instead:
- For prediction: base it on implied odds (if available) + team reputation from your training data.
- For pillars: generate tactical analysis from KNOWN team styles (e.g. "Real Madrid's UCL DNA", "Man City's possession dominance", "Liverpool's gegenpressing").
- YOU MUST OUTPUT VALID JSON regardless of missing inputs. Empty news = rely on internal knowledge. Missing odds = estimate from team strength.

LIVE SEARCH CAPABILITY:
You have access to Google Search. When analyzing a match, ACTIVELY search for:
- Latest confirmed injury reports and lineup updates (last 24-48 hours)
- Recent match results and current form
- Breaking team news (suspensions, managerial changes, transfer announcements)
Prioritize fresh search results over the [LATEST NEWS] section when they conflict.
Cite specifics naturally in pillar content (e.g. "Per today's reports, Player X is ruled out...").

RULES:
- pillars: exactly 2-3 items. MUST name specific players, stats, or schedule facts. At least ONE pillar MUST explain the AI Edge — how your adjusted probability differs from the market anchor and why (e.g., "Market: 65% → AI: 57% due to B2B fatigue").
- When [LATEST NEWS] mentions injuries: ALWAYS explain the tactical consequence, not just the absence. Use your knowledge of the team's system to explain what breaks.
- If [LATEST NEWS] is empty: use your sports knowledge to reference specific tactical matchups, formation clashes, or schedule spots for these specific teams. Do NOT fall back to generic platitudes.
- sentiment: "positive" = helps the predicted winner, "negative" = hurts the predicted winner. Be honest — predicted winner's own injury IS negative, not positive.
- VISUAL CONSISTENCY (MANDATORY): If score >60%, AT LEAST ONE pillar MUST have sentiment "positive". Use title like "Baseline Strength" or "Squad Depth" to explain WHY the predicted winner is still heavily favored (e.g. "Despite injuries, Arsenal's squad depth is vastly superior to Leeds"). This is NON-NEGOTIABLE — the user needs to see a green pillar justifying the high score.
- confidence: High if >75%, Medium if 55-75%, Low if <55%
- prediction: use the team name only (e.g. "Arsenal", "Chelsea"). Do NOT append "to Win" — the frontend adds it automatically. For NBA/basketball: NEVER predict "Draw" — basketball has no draws. You MUST pick one team even if it's close (50/50 → pick the home team).
- factors: list market probabilities for both teams
- Output ONLY the JSON object. No text before or after.
"""


class LLMClient:
    """
    LLM Client supporting Google Vertex AI (primary) and OpenRouter (backup).
    Toggle via LLM_PROVIDER env var: "google" (default) or "openrouter".
    """

    # Model Configuration
    VERTEX_MODEL = "gemini-2.0-flash-001"
    OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
    OPENROUTER_FALLBACK = "deepseek/deepseek-chat"

    def __init__(self):
        """Initialize LLM clients based on provider configuration."""
        self.provider = os.getenv("LLM_PROVIDER", "google").lower()

        # --- Google Vertex AI ---
        self.vertex_available = False
        self.google_project_id = os.getenv("GOOGLE_PROJECT_ID", "")
        if HAS_VERTEX_AI and self.google_project_id:
            try:
                vertexai.init(project=self.google_project_id, location="us-central1")
                google_search_tool = Tool.from_google_search_retrieval(
                    grounding.GoogleSearchRetrieval()
                )
                self.vertex_model = GenerativeModel(
                    self.VERTEX_MODEL,
                    tools=[google_search_tool],
                )
                self.vertex_available = True
                print(f"   [LLMClient] Vertex AI initialized (project={self.google_project_id})")
            except Exception as e:
                print(f"   [LLMClient] Vertex AI init failed: {str(e)[:100]}")

        # --- OpenRouter (backup / legacy) ---
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_client = None
        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key,
                timeout=httpx.Timeout(60.0, connect=10.0)
            )

    def is_available(self) -> bool:
        """Check if any LLM provider is configured and available."""
        return self.vertex_available or bool(self.openrouter_client)

    def _call_vertex_ai(self, system_prompt: str, user_prompt: str) -> str:
        """Call Google Vertex AI (Gemini) API."""
        if not self.vertex_available:
            raise RuntimeError("Vertex AI not configured")

        combined_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
        response = self.vertex_model.generate_content(
            combined_prompt,
            generation_config={"temperature": 0.7, "max_output_tokens": 2048},
        )
        candidates = response.candidates
        if not candidates or not candidates[0].content or not candidates[0].content.parts:
            return None
        parts = candidates[0].content.parts
        full_text = "".join(part.text for part in parts if hasattr(part, "text") and part.text)
        return self._clean_response(full_text)

    def _call_openrouter(self, system_prompt: str, user_prompt: str, model: str = None) -> str:
        """
        Call OpenRouter API.
        """
        if not self.openrouter_client:
            raise RuntimeError("OpenRouter API key not configured")

        target_model = model or self.OPENROUTER_MODEL

        completion = self.openrouter_client.chat.completions.create(
            extra_headers={"HTTP-Referer": YOUR_SITE_URL, "X-Title": APP_NAME},
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        content = completion.choices[0].message.content
        return self._clean_response(content)

    def _clean_response(self, content: str) -> str:
        """Clean LLM response (remove thinking chains, markdown fences, etc.)"""
        if not content:
            return None

        # Clean DeepSeek thinking chains
        if "<think>" in content:
            parts = content.split("</think>")
            if len(parts) > 1:
                content = parts[-1].strip()

        # Remove markdown code fences
        content = content.replace("```markdown", "").replace("```json", "").replace("```", "").strip()

        # Extract JSON object if surrounded by non-JSON text (grounding may prepend text)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        return content

    def generate_analysis(self, system_prompt: str, user_prompt: str) -> str:
        """
        Main entry point for LLM analysis.
        Routes to the configured provider with automatic fallback.

        Returns: Raw response string (JSON or Markdown depending on prompt)
        """
        if not self.is_available():
            print("   [LLMClient] No LLM provider configured")
            return None

        # Determine call order based on configured provider
        if self.provider == "google" and self.vertex_available:
            primary = ("Vertex AI", self._call_vertex_ai)
            fallback = ("OpenRouter", self._call_openrouter) if self.openrouter_client else None
        else:
            primary = ("OpenRouter", self._call_openrouter) if self.openrouter_client else None
            fallback = ("Vertex AI", self._call_vertex_ai) if self.vertex_available else None

        # Try primary
        if primary:
            try:
                result = primary[1](system_prompt, user_prompt)
                if result:
                    print(f"   [LLMClient] {primary[0]} success")
                    return result
            except Exception as e:
                print(f"   [LLMClient] {primary[0]} failed: {str(e)[:100]}")

        # Try fallback
        if fallback:
            try:
                print(f"   [LLMClient] Falling back to {fallback[0]}...")
                result = fallback[1](system_prompt, user_prompt)
                if result:
                    print(f"   [LLMClient] {fallback[0]} fallback success")
                    return result
            except Exception as e:
                print(f"   [LLMClient] {fallback[0]} fallback failed: {str(e)[:100]}")

        return None


# Global LLMClient instance
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get or create the global LLMClient instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# Global ContextBuilder instance
_context_builder = None

def get_context_builder():
    """Get or create the global ContextBuilder instance."""
    global _context_builder
    if _context_builder is None and ContextBuilder is not None:
        _context_builder = ContextBuilder()
    return _context_builder


def parse_analysis_output(raw_text):
    """
    Parse structured fields from AI output.
    Tries JSON first (new format), falls back to regex for old markdown in DB.
    Returns None-safe dict — never crashes on malformed output.

    Args:
        raw_text: Raw string from the LLM (JSON or legacy markdown).

    Returns:
        Dict with keys: predicted_winner, win_probability, recommended_market, risk_level.
        Values default to None if parsing fails.
    """
    import json

    result = {
        "predicted_winner": None,
        "win_probability": None,
        "recommended_market": None,
        "risk_level": None,
    }

    if not raw_text:
        return result

    # --- Try JSON parse first (new format) ---
    try:
        data = json.loads(raw_text)
        nc = data.get("news_card", {})
        sc = data.get("strategy_card", {})
        result["predicted_winner"] = nc.get("prediction")
        result["win_probability"] = sc.get("score") or nc.get("confidence_pct")
        result["recommended_market"] = "Moneyline"  # JSON format implies moneyline
        risk_score = sc.get("score", 50)
        if isinstance(risk_score, (int, float)):
            if risk_score >= 70:
                result["risk_level"] = "Low"
            elif risk_score >= 50:
                result["risk_level"] = "Medium"
            else:
                result["risk_level"] = "High"
        return result
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass

    # --- Fallback: regex for legacy markdown in DB ---
    winner_match = re.search(
        r'\*{0,2}Predicted\s+Winner\*{0,2}:\s*\*{0,2}\s*(.+?)(?:\s*\*{0,2})\s*$',
        raw_text, re.MULTILINE | re.IGNORECASE
    )
    if not winner_match:
        winner_match = re.search(
            r'\*{0,2}Winner\*{0,2}:\s*\*{0,2}\s*(.+?)(?:\s*\*{0,2})\s*$',
            raw_text, re.MULTILINE | re.IGNORECASE
        )
    if winner_match:
        result["predicted_winner"] = winner_match.group(1).strip().strip('*').strip()

    prob_match = re.search(
        r'\*{0,2}Win\s+Probability\*{0,2}:\s*\*{0,2}\s*~?(\d{1,3})\s*%?',
        raw_text, re.IGNORECASE
    )
    if prob_match:
        val = int(prob_match.group(1))
        if 0 <= val <= 100:
            result["win_probability"] = val

    market_match = re.search(
        r'\*{0,2}Recommended\s+Market\*{0,2}:\s*\*{0,2}\s*(.+?)(?:\s*\*{0,2})\s*$',
        raw_text, re.MULTILINE | re.IGNORECASE
    )
    if market_match:
        result["recommended_market"] = market_match.group(1).strip().strip('*').strip()

    risk_match = re.search(
        r'\*{0,2}Risk\s+Level\*{0,2}:\s*\*{0,2}\s*(Low|Medium|High)(?:\s*\*{0,2})',
        raw_text, re.IGNORECASE
    )
    if risk_match:
        result["risk_level"] = risk_match.group(1).strip().capitalize()

    return result


def generate_ai_report(match_data, is_championship=False, league="NBA", force_analysis=False):
    """
    Generate AI analysis report using the LLMClient.
    Injects real-time news context when available.
    Returns structured dict with full markdown + parsed fields.

    Args:
        match_data: Dict with title, ev, web2_odds, polymarket_price, home_team, away_team.
        is_championship: Whether this is a championship/futures market.
        league: League code ("NBA", "EPL", "UCL", "FIFA") for context fetching.

    Returns:
        Dict with keys: full_report_markdown, predicted_winner, win_probability,
        recommended_market, risk_level. Or None if skipped/unavailable.
    """
    client = get_llm_client()

    if not client.is_available():
        print("   No LLM provider configured, skipping AI analysis")
        return None

    ev = float(match_data.get('ev', 0))
    poly_price = float(match_data.get('polymarket_price', 0))
    threshold = 0.05 if is_championship else 0.02

    # Skip threshold check if no Polymarket data — analyze based on bookmaker odds alone
    # force_analysis=True bypasses EV gate (used for daily matches to ensure 100% coverage)
    if not force_analysis and poly_price > 0 and ev < threshold:
        return None

    title = match_data.get('title', 'Unknown Match')
    web2_odds = match_data.get('web2_odds', 0)
    poly_price = match_data.get('polymarket_price', 0)
    ev_percent = ev * 100

    print(f"   AI Analyst observing: {title} (EV: +{ev_percent:.1f}%)")

    # Fetch real-time context
    context_str = ""
    ctx_builder = get_context_builder()
    if ctx_builder:
        home = match_data.get('home_team', '')
        away = match_data.get('away_team', '')
        if home and away:
            try:
                context_str = ctx_builder.build_match_context(home, away, league)
                if context_str:
                    print(f"   [ContextBuilder] Injected real-time context for {home} vs {away}")
            except Exception as e:
                print(f"   [ContextBuilder] Failed: {str(e)[:60]}")

    system_prompt = SYSTEM_PROMPT

    # Build [LATEST NEWS] section for the user prompt
    if context_str:
        news_section = f"[LATEST NEWS]\n{context_str}\n"
    else:
        news_section = "[LATEST NEWS]\nNo real-time news available for this match.\n"

    # Pre-compute implied probabilities for Anchor & Adjust
    home_team = match_data.get('home_team', 'Home')
    away_team = match_data.get('away_team', 'Away')

    if web2_odds and web2_odds > 0:
        implied_home = web2_odds
        implied_away = 100 - web2_odds
        market_anchor = f"""[MARKET BASELINE — Your Anchor]
- {home_team}: {implied_home:.1f}% implied probability (Bookmaker)
- {away_team}: {implied_away:.1f}% implied probability (Bookmaker)
- Polymarket Price ({home_team}): {poly_price:.1f}%
Use these as your STARTING POINT. Only adjust based on [LATEST NEWS] evidence."""
    else:
        market_anchor = "[MARKET BASELINE]\nMarket Data Unavailable. Estimate based on fundamentals only."

    # Status vocabulary depends on market type
    if is_championship:
        status_vocab = 'Use status vocabulary: "Accumulate" (strong buy), "Hold" (neutral), or "Sell" (avoid).'
        champ_instruction = f"""- CHAMPIONSHIP/FUTURES MARKET: This is NOT a head-to-head match. You are evaluating whether "{home_team}" will win the championship.
- prediction field: use "{home_team}" if bullish, or "Fade {home_team}" if bearish. NEVER use "Draw".
- score: represents the team's championship likelihood (use market baseline as anchor).
- confidence: reflects how confident you are in the value bet, not the team's chance of winning outright."""
    else:
        status_vocab = 'Use status vocabulary: "Buy" (positive EV edge), "Sell" (negative EV), or "Wait" (unclear/no edge).'
        champ_instruction = ""

    if poly_price > 0:
        user_prompt = f"""{news_section}
{market_anchor}

Analyze: {title}
- Net EV: +{ev_percent:.1f}%
{status_vocab}
{champ_instruction}

Output ONLY valid JSON matching the schema. No markdown, no code fences."""
    else:
        # No Polymarket data — analyze based on bookmaker odds alone
        user_prompt = f"""{news_section}
{market_anchor}

Analyze: {title}
- Note: No prediction market data available. Use bookmaker odds as your Anchor and apply the Probability Calculation Framework adjustments normally.
- Set status to "Wait" (no market edge detectable without prediction market data). Score should reflect your adjusted probability from the framework, NOT a default 50.
{status_vocab}
{champ_instruction}

Output ONLY valid JSON matching the schema. No markdown, no code fences."""

    time.sleep(1)  # Rate limit protection
    raw_text = client.generate_analysis(system_prompt, user_prompt)

    if not raw_text:
        return None

    print(f"   AI report generated successfully")

    # Parse structured fields from the output (JSON or legacy markdown)
    parsed = parse_analysis_output(raw_text)

    return {
        "full_report_markdown": raw_text,
        "predicted_winner": parsed["predicted_winner"],
        "win_probability": parsed["win_probability"],
        "recommended_market": parsed["recommended_market"],
        "risk_level": parsed["risk_level"],
    }


# ---------------- TOURNAMENT REPORT SYSTEM PROMPT ---------------- #
TOURNAMENT_SYSTEM_PROMPT = """
You are a Senior Sports Investment Analyst producing a Tournament Landscape Report. Output ONLY valid JSON — no markdown, no code fences, no commentary.

You are analyzing the TOP contenders for a championship/winner market collectively, NOT individually. Your job is to rank them into tiers, identify relative value, and produce a portfolio allocation strategy.

INTERNAL REASONING (use but do NOT output):
1. Current form, injuries, and squad depth for each contender
2. Schedule difficulty and fixture congestion
3. Market pricing efficiency — which teams are overvalued/undervalued relative to each other
4. Head-to-head matchup implications in knockouts/title race
5. Historical precedent for similar title races

OUTPUT SCHEMA (respond with this JSON and nothing else):
{
  "strategy_card": {
    "headline": "<professional 5-10 word title, e.g. 'EPL Title Race: Two-Horse Market With Value Underneath'>",
    "analysis": "<Markdown portfolio strategy. Use ### headers for sections. Cover: (1) Market Overview — who leads and why, (2) Value Plays — which teams are mispriced, (3) Risk Assessment — what could blow up the consensus. Professional tone, data-driven, 200-400 words.>",
    "risk_text": "<1 sentence overall market risk assessment with ⚠️>"
  },
  "news_card": {
    "tiers": [
      {
        "tier_name": "Favorites",
        "tier_emoji": "👑",
        "teams": [
          {
            "team_name": "<exact team name>",
            "polymarket_price": <number, e.g. 0.45>,
            "web2_odds": <number or null>,
            "verdict": "<Accumulate|Hold|Sell>",
            "one_liner": "<1 sentence — why this verdict, with specific reasoning>"
          }
        ]
      },
      {
        "tier_name": "Challengers",
        "tier_emoji": "⚔️",
        "teams": [...]
      },
      {
        "tier_name": "Dark Horses",
        "tier_emoji": "🐴",
        "teams": [...]
      },
      {
        "tier_name": "Pretenders",
        "tier_emoji": "💀",
        "teams": [...]
      }
    ],
    "portfolio_summary": "<2-3 sentences: concrete allocation advice across the tiers. E.g. '60% of championship allocation to Favorites tier, 25% Challengers, 15% Dark Horses. Avoid Pretenders — negative EV across the board.'>"
  }
}

TIER ASSIGNMENT RULES:
- Favorites: Top 1-2 contenders with >15% implied probability. These are the market leaders.
- Challengers: Teams with 5-15% implied probability. Realistic contenders with a path to winning.
- Dark Horses: Teams with 2-5% implied probability. Long shots with specific scenarios where they could win.
- Pretenders: Teams with <5% probability that are OVERPRICED. The market is giving them too much credit.
- Every team in the input MUST appear in exactly one tier.
- If a tier would be empty, omit it from the output.

VERDICT RULES:
- "Accumulate": Polymarket price is BELOW fair value. Buy.
- "Hold": Price is roughly fair. No action needed.
- "Sell": Polymarket price is ABOVE fair value. Reduce exposure.
- Base verdicts on the gap between your assessed probability and market price.

ONE-LINER QUALITY:
- MUST be specific to the team. No generic "good form" or "strong squad".
- Reference specific tactical, schedule, or personnel factors.
- BAD: "Arsenal are in good form and could win the league."
- GOOD: "Saka's return from injury restores the right-side overload that drives Arsenal's xG — market underpricing recovery upside."

LIVE SEARCH CAPABILITY:
You have access to Google Search. ACTIVELY search for latest news, injuries, and form for each team in the analysis. Cite specifics naturally.

LEAGUE-SPECIFIC LOGIC (adapt your analysis to the league context):

🏀 NBA Championship:
- The "Two-Conference" Reality: You MUST mention the East vs. West dynamic. (e.g., "The Celtics have an easy path in the East, while the West is a bloodbath between 6+ contenders.")
- Star Power: NBA is driven by stars. Mention health/load management of key players (Jokic, Giannis, Luka, etc.). A single superstar injury reshapes the entire title picture.
- Playoff Rotation: Distinguish between "Regular Season teams" (deep bench, high win totals) and "Playoff teams" (short rotation, star-heavy, thrive in 7-game series). Regular season record ≠ playoff ceiling.
- Conference Bracket: Factor in likely playoff matchup paths — some contenders have significantly easier brackets than others.

⚽ FIFA World Cup / International Tournaments:
- The "Bracket" Path: Analyze the group draw and knockout bracket. "France has a cakewalk group, while Brazil is in the Group of Death." Group position determines R16 opponent quality.
- Tournament Form: Momentum and squad cohesion matter more than club form. Recent friendlies, qualifying results, and manager's tournament pedigree are key signals.
- Knockout Randomness: Single-elimination games have extreme variance (penalties, red cards, set pieces). This compresses the probability distribution — longshots are more viable, favorites less dominant than in a league format.
- 2026 Expansion: 48-team format means more group matches, denser schedules, and squad depth becomes critical. Bench quality is the hidden metric.

⚽ League Winners (EPL / La Liga):
- The Grind: League titles are won over 38 matches. Focus on consistency, squad depth, and the current points gap. Injury resilience and rotation quality matter more than peak performance.
- xG Regression: Teams overperforming xG are due for regression; teams underperforming xG are due for improvement. Factor this into verdicts.
- Fixture Congestion: Teams in UCL/cups face fatigue — assess which squads can handle the dual campaign.

⚽ UCL (Champions League):
- The Matchup Game: UCL is about tactical styles in two-legged ties. Some teams are "built for Europe" (compact, counter-attacking) while others struggle away from home.
- European Pedigree: Real Madrid, Bayern, and other serial winners have a proven extra gear in knockout UCL. This is a genuine, quantifiable edge.
- Format Changes: Account for the current UCL format (league phase → knockout). Seeding and bracket draw matter enormously for the path to the final.

RULES:
- Output ONLY the JSON object. No text before or after.
- Every team provided must appear in exactly one tier.
- portfolio_summary must include concrete percentage allocations.
- analysis must be Markdown-formatted with ### headers.
"""


def generate_tournament_report(market_data_list, league="EPL"):
    """
    Generate a collective Tournament Landscape Report for top contenders.

    Args:
        market_data_list: List of dicts, each with keys:
            team_name, polymarket_price, web2_odds (all from DB)
        league: League name ("EPL", "UCL", "NBA") for context.

    Returns:
        Raw JSON string from the LLM, or None if unavailable.
    """
    client = get_llm_client()
    if not client.is_available():
        print("   [Tournament] No LLM provider configured, skipping")
        return None

    if not market_data_list:
        print("   [Tournament] No market data provided, skipping")
        return None

    print(f"\n   [Tournament] Generating {league} report for {len(market_data_list)} teams...")

    # Build the team summary block for the user prompt
    team_lines = []
    for team in market_data_list:
        name = team.get("team_name", "Unknown")
        poly = team.get("polymarket_price", 0) or 0
        web2 = team.get("web2_odds", 0) or 0
        poly_pct = poly * 100 if poly <= 1 else poly
        web2_pct = web2 * 100 if web2 <= 1 else web2
        team_lines.append(
            f"- {name}: Polymarket {poly_pct:.1f}% | Bookie {web2_pct:.1f}%"
        )

    teams_block = "\n".join(team_lines)

    user_prompt = f"""League: {league}

[TOP CONTENDERS — Market Data]
{teams_block}

Produce a Tournament Landscape Report for the {league} championship market.
Assign every team above to exactly one tier (Favorites / Challengers / Dark Horses / Pretenders).
Include a portfolio allocation strategy.

Output ONLY valid JSON matching the schema. No markdown, no code fences."""

    time.sleep(1)  # Rate limit protection
    raw_text = client.generate_analysis(TOURNAMENT_SYSTEM_PROMPT, user_prompt)

    if raw_text:
        print(f"   [Tournament] {league} report generated successfully")
    else:
        print(f"   [Tournament] {league} report generation failed")

    return raw_text


# Legacy function compatibility
def call_llm(model, sys_prompt, user_prompt):
    """Legacy function for backward compatibility. Routes through generate_analysis."""
    client = get_llm_client()
    return client.generate_analysis(sys_prompt, user_prompt)
