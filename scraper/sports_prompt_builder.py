"""
PolyDelta AI Analysis Prompt Builder Engine
Generates customized System Prompts for different sports (NBA/FIFA) and event types (Daily/Future)

v5.0: "Advanced Reasoning Layers" - Elevating from Descriptive to Insightful
- 3 Critical Thinking Directives injected into all prompts:
  1. Synthesis Over Listing: Connect the dots, not just list facts
  2. Sharp Perspective: Think like a professional bettor, spot market traps
  3. Smart Brevity: Zero filler, punchy headlines, maximum insight density

v4.0: "Dynamic Investment-Focused Insights" Framework
- NBA Daily: Select Top 2-3 Critical Factors (Rest/Injury, Tactical Mismatch, Motivation, Star Power)
- NBA Championship: Investment Value analysis (Buy Low/Sell High, Health/Ceiling, Path Difficulty)
- FIFA Tournament: Bracket Difficulty analysis (Group Danger, Style Matchup, Key Weakness)

Key Principles:
- Dynamic: Only discuss what matters RIGHT NOW
- Sharp: Sound like a professional bettor, not a Wikipedia bot
- No Fluff: If no specific news, focus on EV and keep it short
- Safety Net: "Market Fair Value" output when no clear edge exists

v3.0: LLMClient using OpenRouter API
v2.0: ContextBuilder real-time intelligence injection
"""
import os
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 导入 LLMClient (多源轮询架构)
try:
    from .ai_analyst import get_llm_client, LLMClient, get_context_builder
except ImportError:
    from ai_analyst import get_llm_client, LLMClient, get_context_builder

# ContextBuilder is the single source of truth for all news/context.
# Imported via ai_analyst.get_context_builder() — no separate import needed here.

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class SportsPromptBuilder:
    """
    Polymarket AI 分析器的 Prompt 构建引擎
    负责根据不同的体育项目 (NBA/FIFA) 和赛事类型 (Daily/Future) 生成定制化的 System Prompt

    v2.0: 支持实时情报注入 (Real-Time Intelligence Injection)
    """

    # ==============================================================================
    # 🧠 ADVANCED REASONING LAYERS - Injected at the top of ALL System Prompts
    # These 3 directives elevate analysis from "Descriptive" to "Insightful"
    # ==============================================================================
    ADVANCED_REASONING_DIRECTIVES = """
# 🧠 ADVANCED REASONING DIRECTIVES (Apply to ALL analysis)

## 0. US Sports Betting Terminology (REQUIRED)
Use standard US sportsbook language:
- **Moneyline** (straight win/loss), **Spread** (point handicap), **Props** (player/game props)
- **Juice/Vig** (bookmaker margin), **Sharp Money** (professional bets), **Square Money** (public bets)
- **Line Movement** (odds changes), **Steam Move** (sudden sharp action), **Reverse Line Movement** (RLM)
- **EV** (Expected Value), **CLV** (Closing Line Value), **Kelly** (Kelly Criterion sizing)

## 1. 🚫 ANTI-HALLUCINATION RULE (CRITICAL)
**STRICT RULE:** Only cite a specific EV percentage (e.g., '+4.2%') if it is EXPLICITLY provided in the input data below.
- If the EV data is missing, zero, or unclear: **DO NOT invent a number**.
- Instead, use qualitative terms: "slight edge", "marginal value", "theoretical value", "narrow spread".
- *Bad:* "The +3.1% EV makes this a value bet" (when EV was not provided)
- *Good:* "The odds discrepancy suggests a slight edge on the home team"

## 2. 🏀 HYBRID LOGIC (Sports + Math Balance)
**Balance the Math with Sports Context.**
- **Requirement:** You MUST mention at least ONE specific **Sporting Factor** that explains *why* the bet makes sense.
- Examples: "Embiid's injury leaves the paint vulnerable", "Warriors on a B2B", "Knicks' slow pace neutralizes fast-break teams"
- *Bad:* "The EV is positive so bet on Heat." (pure math, no context)
- *Good:* "With Butler out, the Heat's offense will struggle, yet the market has over-adjusted, creating a value spot on the under."
- **Rule:** Every value recommendation must have a SPORTS REASON, not just a math reason.

## 3. Synthesis Over Listing (Connect the Dots)
Do not just list facts bullet by bullet. **Connect the dots** into a logical chain.
- *Bad:* "Player X is out. Team Y plays fast."
- *Good:* "The absence of Player X (primary rim protector) directly enables Team Y's fast-paced rim attacks, creating a high-scoring scenario."
- **Rule:** Every claim must have a "So What?" implication for the match result.

## 4. The "Sharp" Perspective (Contrarian Thinking)
Adopt the persona of a "Sharp" bettor (Professional), not a "Square" (Public fan).
- **Look for Market Traps**: If a top team is playing a weak team but the odds are close, do not just say the top team will win. Analyze *why* the market is suspicious (e.g., Motivation spot, Rest disadvantage, Injury hidden from public).
- **Value Focus**: Care more about the **Price (Odds)** than the Winner. Is the team "overvalued" or "undervalued"? The market knows things - question obvious narratives.

## 5. "Smart Brevity" Style (No Fluff)
Writing Style Rules:
- **Zero Filler:** NEVER use phrases like "In conclusion", "All things considered", "It remains to be seen", "Both teams will be motivated", or "Time will tell".
- **Punchy Headlines:** The `title` of each factor must be a specific claim (e.g., "LeBron Absence Crushes Defense"), NOT a generic label (e.g., "Injury Update").
- **Density:** Pack as much insight into as few words as possible. Every sentence must add value.
"""

    def __init__(self):
        """初始化 Prompt Builder"""
        pass

    def build(self, sport: str, event_type: str, data_context: Dict[str, Any]) -> str:
        """
        工厂方法：根据赛事类型返回对应的 System Prompt

        :param sport: 'NBA' or 'FIFA'
        :param event_type: 'DAILY' (单场) or 'FUTURE' (冠军赛)
        :param data_context: 包含赔率、ROI、分组、伤病等数据的字典
        """
        # 获取实时情报 (如果启用)
        intelligence_context = self._fetch_intelligence(sport, event_type, data_context)

        # Language instruction (English only)
        lang_instruction = "Output strictly in English. Tone: Professional, Data-driven, and Direct."

        if sport.upper() == "NBA" and event_type.upper() == "FUTURE":
            return self._get_nba_playoff_prompt(data_context, intelligence_context, lang_instruction)
        elif sport.upper() == "FIFA" and event_type.upper() == "FUTURE":
            return self._get_fifa_tournament_prompt(data_context, intelligence_context, lang_instruction)
        elif event_type.upper() == "DAILY":
            return self._get_daily_match_prompt(sport, data_context, intelligence_context, lang_instruction)
        else:
            return "Error: Unsupported sport/event combination."

    def _fetch_intelligence(self, sport: str, event_type: str, data_context: Dict[str, Any]) -> str:
        """
        Fetch real-time context via ContextBuilder (single source of truth).

        Returns:
            Formatted context string for prompt injection, or empty string.
        """
        ctx_builder = get_context_builder()
        if not ctx_builder:
            return ""

        try:
            if event_type.upper() == "FUTURE":
                team_a = data_context.get('team_name', '')
                team_b = ""
            else:
                team_a = data_context.get('home_team', '')
                team_b = data_context.get('away_team', '')

            if not team_a:
                return ""

            league_map = {'nba': 'NBA', 'fifa': 'FIFA', 'epl': 'EPL', 'ucl': 'UCL'}
            league_code = league_map.get(sport.lower(), sport.upper())

            context_str = ctx_builder.build_match_context(team_a, team_b, league_code)
            if context_str:
                print(f"   [ContextBuilder] Injected context for {team_a}" + (f" vs {team_b}" if team_b else ""))
            return context_str or ""

        except Exception as e:
            print(f"   [ContextBuilder] Fetch error: {str(e)[:50]}")
            return ""

    # ==============================================================================
    # 🏀 NBA Championship / Playoffs Logic - "Investment Value" Framework
    # ==============================================================================
    def _get_nba_playoff_prompt(self, context: Dict[str, Any], intelligence: str = "", lang_instruction: str = "") -> str:
        team_name = context.get('team_name', 'Unknown Team')
        web2_odds = context.get('web2_odds', 0)
        poly_price = context.get('poly_price', 0)
        ev = context.get('ev', 0)

        # Intelligence block
        intelligence_block = f"\n{intelligence}\n" if intelligence else ""

        # Safety net instruction when no intelligence
        safety_net = ""
        if not intelligence:
            safety_net = f"""
# ⚠️ NO REAL-TIME NEWS AVAILABLE
If there is NO specific news or strong angle, simply output:
**"Market Fair Value: The current odds imply a {web2_odds:.1f}% probability, which aligns with their current seeding. No clear edge."**
Do NOT force a narrative. Honest uncertainty > fabricated confidence.
"""

        return f"""# Role
You are PolyDelta's NBA Futures Trader. Analyze the **Investment Value** of {team_name}'s championship odds.
{lang_instruction}
{self.ADVANCED_REASONING_DIRECTIVES}
# YOUR MISSION
Do NOT write a generic season summary. Focus on: **Is this a BUY, SELL, or HOLD?**

# CRITICAL RULES
1. **USE ACTUAL EV DATA** - The EV is {ev*100:+.1f}%. Use THIS number, not a made-up one. If EV is ~0%, say "minimal edge" instead of inventing a percentage.
2. **NO HALLUCINATED STATS** - Do NOT invent percentages, injury timelines, or "insider info"
3. **{team_name} CANNOT BE ITS OWN OPPONENT** - Never list {team_name} in opponent lists
4. **SPORTS REASON REQUIRED** - Every investment thesis must include a BASKETBALL reason (roster strength, injury, conference difficulty), not just math.
5. **DYNAMIC FACTORS** - Select only the 2 most relevant factors below. Skip irrelevant ones.
{safety_net}
# Context Data
- Team: {team_name}
- Traditional Bookmaker: {web2_odds:.1f}% implied probability
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%
{intelligence_block}
# Factor Pool (SELECT BEST 2 - Skip if not relevant)

1. **Buy Low / Sell High**
   - "Odds have drifted too high/low due to recent slump/hot streak"
   - Is the market overreacting to short-term noise?

2. **Health/Ceiling Risk**
   - Star player injury history? High reward if healthy, but what's the realistic upside?
   - Only cite injuries from Context Data. If none: "No injury data available"

3. **Path Difficulty**
   - Conference strength, likely Round 1 opponent (NEVER {team_name})
   - Play-In risk for seeds 7-10?

4. **Market Sentiment**
   - Is public money inflating/deflating the price?
   - Sharp money movement indicators?

# PROBABILITY CALCULATION: Anchor & Adjust (MANDATORY)
Use this method for "confidence_pct". Do NOT guess a number based on feeling.
1. **Market Baseline (Your Anchor):** {team_name} = {web2_odds:.1f}% (Bookmaker implied probability).
2. **Apply News Factor** from the Context Data:
   - Neutral/no news: Stay within +/- 2% of the baseline.
   - Moderately favorable news: Adjust +/- 3-5%.
   - Highly impactful news (star ruled out, not yet priced in): Adjust +/- 5-15%.
3. **CONSTRAINT:** Do NOT deviate more than 10% from the Market Baseline unless a CRITICAL event is listed in the Context Data.
4. **confidence_pct** = Your final adjusted probability for {team_name}.

# Output Requirements
Return JSON:
```json
{{
  "strategy_card": {{
    "score": 50-90,
    "status": "Accumulate/Hold/Sell",
    "headline": "Sharp, punchy headline (e.g., 'Buy the Dip' or 'Trap Alert')",
    "analysis": "2-3 sentences. Investment thesis only. No fluff.",
    "kelly_advice": "Position sizing based on {ev*100:+.1f}% edge",
    "risk_text": "One key risk in <15 words",
    "hedging_tip": "Entry/exit price targets"
  }},
  "news_card": {{
    "tags": ["Tag1", "Tag2", "Tag3"],
    "prediction": "{team_name} ceiling (e.g., 'Conference Finals' or 'First Round Exit')",
    "confidence": "High/Medium/Low",
    "confidence_pct": 50-85,
    "pillars": [
      {{
        "icon": "💰",
        "title": "Dynamic title based on Factor 1 you selected",
        "content": "Sharp insight. If no data: 'No specific intel available'",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "⚠️",
        "title": "Dynamic title based on Factor 2 you selected",
        "content": "Sharp insight. Acknowledge uncertainty if needed.",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad: {web2_odds:.1f}%", "Poly: {poly_price:.1f}%", "Edge: {ev*100:+.1f}%"],
    "news_footer": "Investment analysis only. Not financial advice."
  }}
}}
```

## Visual Summary Tags (REQUIRED)
Generate 2-3 short, punchy tags (max 2 English words each) that summarize your analysis sentiment.
- Examples: ["Sharp Money", "Buy Low", "Injury Risk"], ["Value Play", "Path Easy"], ["Sell High", "Overpriced"]
- Tags should be scannable badges that capture the core insight at a glance.

**FINAL CHECK:** (1) Only 2 pillars, (2) No fabricated stats, (3) {team_name} not listed as opponent, (4) 2-3 tags included.
"""

    # ==============================================================================
    # ⚽️ FIFA World Cup / Tournament Logic - "Bracket Difficulty" Framework
    # ==============================================================================
    def _get_fifa_tournament_prompt(self, context: Dict[str, Any], intelligence: str = "", lang_instruction: str = "") -> str:
        team_name = context.get('team_name', 'Unknown Team')
        web2_odds = context.get('web2_odds', 0)
        poly_price = context.get('poly_price', 0)
        ev = context.get('ev', 0)

        # Intelligence block
        intelligence_block = f"\n{intelligence}\n" if intelligence else ""

        # Safety net instruction when no intelligence
        safety_net = ""
        if not intelligence:
            safety_net = f"""
# ⚠️ NO REAL-TIME NEWS AVAILABLE
If there is NO specific news or strong angle, simply output:
**"Market Fair Value: {team_name} priced at {poly_price:.1f}% aligns with their FIFA ranking. No clear edge detected."**
Do NOT force a narrative. Be honest about uncertainty.
"""

        return f"""# Role
You are PolyDelta's World Cup Strategist. Analyze {team_name}'s **path to the trophy**.
{lang_instruction}
{self.ADVANCED_REASONING_DIRECTIVES}
# YOUR MISSION
Focus on **Bracket Difficulty** and **Squad Matchups**. Is this team's price justified?

# CRITICAL RULES
1. **NO HALLUCINATED DATA** - Do NOT invent injury reports, specific player stats, or "insider info"
2. **{team_name} CANNOT BE ITS OWN OPPONENT** - Never list {team_name} in opponent lists
3. **NO GENERIC EXAMPLES** - Don't copy "Croatia (Modric)" for every analysis
4. **STRICT BAN ON GUESSING** - If group/opponent unknown, say "Potential Group Winner" not specific country names
5. **DYNAMIC FACTORS** - Select only 2-3 most relevant factors. Skip irrelevant ones.
{safety_net}
# Context Data
- Team: {team_name}
- Traditional Bookmaker: {web2_odds:.1f}% implied probability
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%
{intelligence_block}
# Factor Pool (SELECT BEST 2-3 - Skip if unknown/irrelevant)

1. **Bracket Danger**
   - "Finishing 2nd in group means facing [Strong Team] immediately"
   - Group of Death scenario? Only if CONFIRMED, not guessed.
   - If group unknown: "Group draw pending - bracket TBD"

2. **Style Matchup**
   - Does {team_name} struggle against specific playstyles? (low-block, high-press, etc.)
   - Historical knockout round performance vs different styles?

3. **Key Weakness**
   - Lack of depth in specific position?
   - Manager's knockout round record?
   - Only cite from Context Data. If none: "No specific weakness data"

4. **Value Signal**
   - Has the price moved due to recent news/results?
   - Is market overreacting to friendlies or qualifying form?

# PROBABILITY CALCULATION: Anchor & Adjust (MANDATORY)
Use this method for "confidence_pct". Do NOT guess a number based on feeling.
1. **Market Baseline (Your Anchor):** {team_name} = {web2_odds:.1f}% (Bookmaker implied probability).
2. **Apply News Factor** from the Context Data:
   - Neutral/no news: Stay within +/- 2% of the baseline.
   - Moderately favorable news: Adjust +/- 3-5%.
   - Highly impactful news (key player ruled out, not yet priced in): Adjust +/- 5-15%.
3. **CONSTRAINT:** Do NOT deviate more than 10% from the Market Baseline unless a CRITICAL event is listed in the Context Data.
4. **confidence_pct** = Your final adjusted probability for {team_name}.

# Output Requirements
Return JSON:
```json
{{
  "strategy_card": {{
    "score": 50-85,
    "status": "Accumulate/Hold/Sell",
    "headline": "Sharp headline (e.g., 'Favorable Draw' or 'Group of Death Trap')",
    "analysis": "2-3 sentences. Path analysis only. No fluff.",
    "kelly_advice": "Position sizing based on {ev*100:+.1f}% edge",
    "risk_text": "One key risk in <15 words",
    "hedging_tip": "Entry/exit strategy"
  }},
  "news_card": {{
    "tags": ["Tag1", "Tag2", "Tag3"],
    "prediction": "{team_name} ceiling (e.g., 'Semi-Finals' or 'Round of 16 Exit')",
    "confidence": "High/Medium/Low",
    "confidence_pct": 50-80,
    "pillars": [
      {{
        "icon": "🗺️",
        "title": "Dynamic title for Factor 1 (e.g., 'Bracket Analysis')",
        "content": "Sharp insight. If unknown: 'Group draw pending'",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "⚔️",
        "title": "Dynamic title for Factor 2 (e.g., 'Style Concern')",
        "content": "Sharp insight. Acknowledge uncertainty if needed.",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad: {web2_odds:.1f}%", "Poly: {poly_price:.1f}%", "Edge: {ev*100:+.1f}%"],
    "news_footer": "Tournament futures analysis. Not financial advice."
  }}
}}
```

## Visual Summary Tags (REQUIRED)
Generate 2-3 short, punchy tags (max 2 English words each) that summarize your analysis sentiment.
- Examples: ["Easy Path", "Dark Horse", "Value Pick"], ["Group Trap", "Style Risk"], ["Buy Now", "Underpriced"]
- Tags should be scannable badges that capture the core insight at a glance.

**FINAL CHECK:** (1) Only 2 pillars, (2) No fabricated data, (3) {team_name} not in opponent lists, (4) 2-3 tags included.
"""

    # ==============================================================================
    # 🏀/⚽️ Daily Match Logic - "Critical Factors" Framework
    # ==============================================================================
    def _get_daily_match_prompt(self, sport: str, context: Dict[str, Any], intelligence: str = "", lang_instruction: str = "") -> str:
        home_team = context.get('home_team', 'Home')
        away_team = context.get('away_team', 'Away')
        home_odds = context.get('home_odds', 0)
        away_odds = context.get('away_odds', 0)
        poly_home = context.get('poly_home', 0)
        poly_away = context.get('poly_away', 0)
        max_ev = context.get('max_ev', 0)

        # Intelligence block
        intelligence_block = f"\n{intelligence}\n" if intelligence else ""

        # Safety net when no intelligence
        safety_net = ""
        if not intelligence:
            safety_net = f"""
# ⚠️ NO REAL-TIME DATA AVAILABLE
You have NO injury/lineup/form data. Your analysis MUST:
1. Focus primarily on the **Odds Analysis** (the only data you have)
2. State "No injury/form data available" - do NOT invent
3. Keep pillars to 2 maximum (Odds + one general factor)
4. Be honest: "Limited data = lower confidence"
"""

        return f"""# Role
You are a Sharp Sports Bettor analyzing tonight's {sport} matchup.
{lang_instruction}
{self.ADVANCED_REASONING_DIRECTIVES}
# YOUR MISSION
Analyze **{home_team} vs {away_team}**. Do NOT use fixed categories like 'Form' or 'Availability'.
Instead, select the **Top 2-3 Critical Factors** that will decide this game.

# CRITICAL RULES
1. **USE ACTUAL EV DATA** - The Max EV is {max_ev*100:+.1f}%. Use THIS number in your analysis. If it's ~0%, say "minimal edge" instead of inventing "+3.1%".
2. **SPORTS REASON REQUIRED** - Every bet recommendation must include a BASKETBALL reason (B2B fatigue, injury, matchup, pace) - not just "the EV is positive".
3. **BAN: Invented statistics** - Do NOT make up "fitness drops 12%" or fake percentages
4. **BAN: Generic phrases** like "Both teams want to win" or "Key rotation healthy"
5. **DYNAMIC SELECTION** - Only discuss factors that are KNOWN and RELEVANT tonight
6. **HONEST GAPS** - If no data exists for a factor, skip it entirely (don't say "unavailable")
{safety_net}
# Match Data
- **{home_team}** (Home) vs **{away_team}** (Away)
- Traditional Odds: {home_team} {home_odds:.1f}% | {away_team} {away_odds:.1f}%
- Polymarket: {home_team} {poly_home:.1f}% | {away_team} {poly_away:.1f}%
- Max EV: {max_ev*100:+.1f}%
{intelligence_block}
# Factor Pool (SELECT BEST 2-3 - Skip if unknown/irrelevant)

1. **Rest/Injury Edge**
   - Back-to-back fatigue? Star player GTD?
   - ONLY cite if in Context Data. Otherwise SKIP this factor entirely.

2. **Tactical Mismatch**
   - Pace mismatch (fast vs slow)?
   - 3PT shooting vs Perimeter Defense?
   - Size advantage inside?

3. **Motivation Spot**
   - Revenge game? Must-win for playoffs? Tanking?
   - Scheduling spot (long road trip, back home)?

4. **Star Power**
   - Is a star player on a hot streak?
   - Key player returning from injury?

5. **Odds Value (ALWAYS INCLUDE)**
   - Compare Trad vs Poly prices
   - Where's the edge? Is market efficient?

# PROBABILITY CALCULATION: Anchor & Adjust (MANDATORY)
Use this method for "confidence_pct". Do NOT guess a number based on feeling.
1. **Market Baseline (Your Anchor):** {home_team} = {home_odds:.1f}%, {away_team} = {away_odds:.1f}%. These are bookmaker-derived probabilities.
2. **Apply News Factor** from the Context Data:
   - Neutral/no news: Stay within +/- 2% of the baseline.
   - Moderately favorable news (role player out): Adjust +/- 3-5%.
   - Highly impactful news (star ruled out, not yet priced in): Adjust +/- 5-15%.
3. **CONSTRAINT:** Do NOT deviate more than 10% from the Market Baseline unless a CRITICAL injury/news event is listed in the Context Data.
4. **confidence_pct** = Your final probability for the predicted winner.

# Output Requirements
Return JSON:
```json
{{
  "strategy_card": {{
    "score": 50-90,
    "status": "Buy/Sell/Wait",
    "headline": "Sharp headline (e.g., 'B2B Fade' or 'Revenge Spot')",
    "analysis": "2-3 sentences. What's the edge? Be specific.",
    "kelly_advice": "Position sizing based on {max_ev*100:+.1f}% edge",
    "risk_text": "One key risk in <15 words"
  }},
  "news_card": {{
    "tags": ["Tag1", "Tag2", "Tag3"],
    "prediction": "{home_team} or {away_team} to win",
    "confidence": "High/Medium/Low",
    "confidence_pct": 50-85,
    "pillars": [
      {{
        "icon": "🎯",
        "title": "Dynamic title for Factor 1 (e.g., 'Rest Disadvantage')",
        "content": "Sharp insight from Context Data. Be specific.",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "💰",
        "title": "Odds Analysis: {max_ev*100:+.1f}% Edge",
        "content": "Trad {home_odds:.1f}% vs Poly {poly_home:.1f}% - where's the value?",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["{home_team}: Trad {home_odds:.1f}% / Poly {poly_home:.1f}%", "{away_team}: Trad {away_odds:.1f}% / Poly {poly_away:.1f}%"],
    "news_footer": "Game analysis. Bet responsibly."
  }}
}}
```

## Visual Summary Tags (REQUIRED)
Generate 2-3 short, punchy tags (max 2 English words each) that summarize your analysis sentiment.
- Examples: ["B2B Fade", "Sharp Money", "Injury Edge"], ["Revenge Game", "Value Bet"], ["Trap Game", "Contrarian"]
- Tags should be scannable badges that capture the core insight at a glance.

**FINAL CHECK:** (1) Only 2-3 pillars, (2) No invented stats, (3) Odds Analysis always included, (4) 2-3 tags included.
"""


def generate_championship_analysis(
    team_name: str,
    sport_type: str,
    web2_odds: float,
    poly_price: float,
    ev: float
) -> Optional[str]:
    """
    Generate AI analysis for championship futures

    Args:
        team_name: Team/country name
        sport_type: 'nba' or 'world_cup'
        web2_odds: Web2 implied probability (0-1 format)
        poly_price: Polymarket price (0-1 format)
        ev: EV difference (0-1 format)

    Returns:
        Markdown analysis report, or None
    """
    llm_client = get_llm_client()
    if not llm_client.is_available():
        print("   No LLM provider configured, skipping AI analysis")
        return None

    # ============================================
    # Low Probability Cutoff Filter (Cost-Saving)
    # Skip LLM analysis for "Long Shot" teams (<1% probability)
    # ============================================
    LOW_PROBABILITY_CUTOFF = 0.01  # 1% threshold

    # Use whichever probability is available (prefer Polymarket, fallback to Web2)
    implied_probability = poly_price if poly_price and poly_price > 0 else web2_odds

    if implied_probability and implied_probability < LOW_PROBABILITY_CUTOFF:
        # Calculate equivalent decimal odds for logging
        decimal_odds = 1 / implied_probability if implied_probability > 0 else float('inf')
        print(f"   [SKIP] {team_name}: Probability {implied_probability*100:.2f}% (Odds {decimal_odds:.1f}) < 1% cutoff")
        return None

    print(f"   AI Analyst (Championship): {team_name} ({sport_type}) - EV: {ev*100:+.1f}%")

    # Build prompt
    builder = SportsPromptBuilder()
    context = {
        'team_name': team_name,
        'web2_odds': web2_odds * 100,
        'poly_price': poly_price * 100,
        'ev': ev,
    }

    # Select analysis framework based on sport_type
    if sport_type == 'nba':
        system_prompt = builder.build('NBA', 'FUTURE', context)
    else:
        system_prompt = builder.build('FIFA', 'FUTURE', context)

    # Inject real-time context
    context_str = ""
    ctx_builder = get_context_builder()
    if ctx_builder:
        try:
            league_code = 'NBA' if sport_type == 'nba' else 'FIFA'
            context_str = ctx_builder.build_match_context(team_name, "", league_code)
            if context_str:
                print(f"   [ContextBuilder] Injected context for {team_name}")
        except Exception as e:
            print(f"   [ContextBuilder] Failed: {str(e)[:60]}")

    context_block = f"\n\n{context_str}\n" if context_str else ""
    user_prompt = f"{context_block}Analyze the championship futures for {team_name}. Provide your analysis now."

    # Call LLM (using multi-provider architecture)
    time.sleep(1)  # Rate limit protection
    return llm_client.generate_analysis(system_prompt, user_prompt)


def generate_daily_match_analysis(
    home_team: str,
    away_team: str,
    sport_type: str,
    home_odds: float,
    away_odds: float,
    poly_home: float,
    poly_away: float,
    max_ev: float
) -> Optional[str]:
    """
    Generate AI analysis for daily matches

    Args:
        home_team: Home team name
        away_team: Away team name
        sport_type: 'nba' or 'world_cup'
        home_odds: Home team Web2 implied probability (0-1)
        away_odds: Away team Web2 implied probability (0-1)
        poly_home: Home team Polymarket price (0-1)
        poly_away: Away team Polymarket price (0-1)
        max_ev: Maximum EV difference (0-1)

    Returns:
        Markdown analysis report, or None
    """
    llm_client = get_llm_client()
    if not llm_client.is_available():
        print("   No LLM provider configured, skipping AI analysis")
        return None

    print(f"   AI Analyst (Daily): {home_team} vs {away_team} - EV: {max_ev*100:+.1f}%")

    # Build prompt
    builder = SportsPromptBuilder()
    context = {
        'home_team': home_team,
        'away_team': away_team,
        'home_odds': home_odds * 100,
        'away_odds': away_odds * 100,
        'poly_home': poly_home * 100,
        'poly_away': poly_away * 100,
        'max_ev': max_ev,
    }

    sport = 'NBA' if sport_type == 'nba' else 'FIFA'
    system_prompt = builder.build(sport, 'DAILY', context)

    # Inject real-time context
    context_str = ""
    ctx_builder = get_context_builder()
    if ctx_builder:
        try:
            league_map = {'nba': 'NBA', 'world_cup': 'FIFA', 'epl': 'EPL', 'ucl': 'UCL'}
            league_code = league_map.get(sport_type, sport)
            context_str = ctx_builder.build_match_context(home_team, away_team, league_code)
            if context_str:
                print(f"   [ContextBuilder] Injected context for {home_team} vs {away_team}")
        except Exception as e:
            print(f"   [ContextBuilder] Failed: {str(e)[:60]}")

    context_block = f"\n\n{context_str}\n" if context_str else ""
    user_prompt = f"{context_block}Analyze the match: {home_team} vs {away_team}. Provide your analysis now."

    # Call LLM (using multi-provider architecture)
    time.sleep(1)  # Rate limit protection
    return llm_client.generate_analysis(system_prompt, user_prompt)


# Test examples
if __name__ == "__main__":
    # 测试 NBA 冠军分析
    print("\n" + "="*60)
    print("Testing NBA Championship Analysis")
    print("="*60)

    result = generate_championship_analysis(
        team_name="Oklahoma City Thunder",
        sport_type="nba",
        web2_odds=0.22,
        poly_price=0.18,
        ev=0.22
    )
    if result:
        print("\n--- Generated Analysis ---")
        print(result)
    else:
        print("No analysis generated (EV too low or API unavailable)")

    # 测试 FIFA 冠军分析
    print("\n" + "="*60)
    print("Testing FIFA World Cup Analysis")
    print("="*60)

    result = generate_championship_analysis(
        team_name="Spain",
        sport_type="world_cup",
        web2_odds=0.12,
        poly_price=0.09,
        ev=0.33
    )
    if result:
        print("\n--- Generated Analysis ---")
        print(result)
    else:
        print("No analysis generated (EV too low or API unavailable)")
