"""
PolyDelta AI 分析器的 Prompt 构建引擎
负责根据不同的体育项目 (NBA/FIFA) 和赛事类型 (Daily/Future) 生成定制化的 System Prompt

NBA 使用 "Gauntlet Logic": Path to Finals + Squad Resilience + Hedging Strategy
FIFA 使用 "Bracket Logic": Group Stage Survival + Knockout Path + Squad Depth & Manager

v2.0: 集成 SportsIntelligenceService 实时情报注入
v3.0: 使用 LLMClient 多源轮询架构 (Gemini -> Groq -> SiliconFlow -> OpenRouter)
"""
import os
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 导入 LLMClient (多源轮询架构)
try:
    from .ai_analyst import get_llm_client, LLMClient
except ImportError:
    from ai_analyst import get_llm_client, LLMClient

# 导入情报服务
try:
    from .sports_intelligence_service import (
        get_match_intelligence,
        get_chatbot_context,
        SportType,
        EventType
    )
    HAS_INTELLIGENCE_SERVICE = True
except ImportError:
    try:
        from sports_intelligence_service import (
            get_match_intelligence,
            get_chatbot_context,
            SportType,
            EventType
        )
        HAS_INTELLIGENCE_SERVICE = True
    except ImportError:
        HAS_INTELLIGENCE_SERVICE = False
        print("   SportsIntelligenceService not available. Running without real-time intelligence.")

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class SportsPromptBuilder:
    """
    Polymarket AI 分析器的 Prompt 构建引擎
    负责根据不同的体育项目 (NBA/FIFA) 和赛事类型 (Daily/Future) 生成定制化的 System Prompt

    v2.0: 支持实时情报注入 (Real-Time Intelligence Injection)
    """

    def __init__(self, enable_intelligence: bool = True):
        """
        初始化 Prompt Builder

        Args:
            enable_intelligence: 是否启用实时情报服务 (默认启用)
        """
        self.enable_intelligence = enable_intelligence and HAS_INTELLIGENCE_SERVICE

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
        获取实时情报并格式化为可注入的文本

        Args:
            sport: 运动类型
            event_type: 事件类型
            data_context: 数据上下文

        Returns:
            格式化的情报文本块，如果获取失败返回空字符串
        """
        if not self.enable_intelligence:
            return ""

        try:
            # 提取队伍名称
            if event_type.upper() == "FUTURE":
                team_a = data_context.get('team_name', '')
                team_b = None
            else:
                team_a = data_context.get('home_team', '')
                team_b = data_context.get('away_team', '')

            if not team_a:
                return ""

            # 调用情报服务
            evt = "future" if event_type.upper() == "FUTURE" else "daily"
            intelligence = get_match_intelligence(sport.lower(), team_a, team_b, evt)

            return intelligence

        except Exception as e:
            print(f"   ⚠️ Intelligence fetch error: {str(e)[:50]}")
            return ""

    def get_chatbot_context(self, sport: str, event_type: str, data_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取 Chatbot 可用的情报上下文（用于归因引用）

        Returns:
            包含情报数据的字典，可用于 Chatbot 回答问题时引用来源
        """
        if not self.enable_intelligence:
            return {}

        try:
            if event_type.upper() == "FUTURE":
                team_a = data_context.get('team_name', '')
                team_b = None
            else:
                team_a = data_context.get('home_team', '')
                team_b = data_context.get('away_team', '')

            if not team_a:
                return {}

            evt = "future" if event_type.upper() == "FUTURE" else "daily"
            return get_chatbot_context(sport.lower(), team_a, team_b, evt)

        except Exception as e:
            print(f"   ⚠️ Chatbot context error: {str(e)[:50]}")
            return {}

    # ==============================================================================
    # 🏀 NBA Championship / Playoffs Logic (NBA 季后赛/冠军赛) - "Gauntlet Logic"
    # ==============================================================================
    def _get_nba_playoff_prompt(self, context: Dict[str, Any], intelligence: str = "", lang_instruction: str = "") -> str:
        team_name = context.get('team_name', 'Unknown Team')
        web2_odds = context.get('web2_odds', 0)
        poly_price = context.get('poly_price', 0)
        ev = context.get('ev', 0)

        # 构建情报注入块
        intelligence_block = f"\n{intelligence}\n" if intelligence else ""

        # 无情报时的警告
        no_data_warning = ""
        if not intelligence:
            no_data_warning = """
# ⚠️ NO REAL-TIME INTELLIGENCE AVAILABLE
You have NO external data (injuries, news, tweets). You MUST:
1. State "No specific injury/news data available" for health assessments
2. Focus ONLY on publicly known facts: current standings, historical playoff records, roster construction
3. Do NOT invent statistics (like "fitness drops 12%" or "shooting 38%") - these are hallucinations
4. If uncertain, say "Insufficient data to assess"
"""

        return f"""# Role
You are PolyDelta's NBA Futures Trader & Senior Sports Analyst.
Your goal is to evaluate if the current championship odds for **{team_name}** represent a "+EV Value Bet" or a "Trap".
{lang_instruction}

# CRITICAL INSTRUCTION: ANTI-TEMPLATE RULES

## Rule 1: SELF-EXCLUSION (MANDATORY)
When listing potential opponents, playoff paths, or "death mode" teams, you MUST EXCLUDE **{team_name}** itself.
- The team being analyzed can NEVER appear as its own opponent.
- Before outputting any opponent list, mentally check: "Is {team_name} in this list?" If yes, REMOVE IT.

## Rule 2: NO HALLUCINATED STATISTICS
- Do NOT invent specific percentages (e.g., "fitness drops 12%", "shooting 38% from 3")
- Do NOT fabricate injury timelines unless provided in the context data
- If no data exists, write: "No specific data available" or "Based on publicly known roster..."
- Only cite statistics that are EXPLICITLY provided in the Context Data section below

## Rule 3: NO COPY-PASTE EXAMPLES
- Do NOT reuse any specific team/player combinations from your training
- Every analysis must be UNIQUE to **{team_name}** and their ACTUAL conference/division rivals
- Research {team_name}'s REAL playoff bracket position and likely opponents

## Rule 4: DYNAMIC SENTENCE STRUCTURE
- Vary your opening sentences. NEVER start multiple pillars with the same pattern
- Each pillar title must be a unique, punchy headline - not a generic category name
- Avoid repetitive phrases like "Key rotation healthy" or "Conference difficulty"
{no_data_warning}
# Context Data
- Team: {team_name}
- Web2 Bookmaker Implied Probability: {web2_odds:.1f}%
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%
{intelligence_block}
# Analysis Framework (The "Gauntlet" Logic)

## 1. Projected Playoff Path
* Name the ACTUAL likely opponents based on current standings (NEVER include {team_name} itself)
* Identify specific matchup concerns based on roster construction
* If data is missing, acknowledge it: "Bracket TBD pending final standings"

## 2. Squad Resilience
* Health assessment: Only cite injuries from the Context Data. If none provided, state "No injury data available"
* Depth analysis based on known roster - do not invent bench scoring numbers

## 3. Hedging Strategy
* Provide concrete entry/exit prices based on the Context Data above

# Output Requirements
Return a JSON object with the following structure:
```json
{{
  "strategy_card": {{
    "score": 75,
    "status": "Accumulate",
    "headline": "Dynamic news-style headline UNIQUE to {team_name}",
    "analysis": "Analysis using ONLY data from Context above",
    "kelly_advice": "Kelly recommendation based on the EV spread",
    "risk_text": "Key risk - cite specific opponent (NOT {team_name})",
    "hedging_tip": "Target price based on poly_price above"
  }},
  "news_card": {{
    "prediction": "Team's realistic ceiling based on current standings",
    "confidence": "High/Medium/Low",
    "confidence_pct": 72,
    "pillars": [
      {{
        "icon": "🎯",
        "title": "UNIQUE headline for {team_name}'s specific situation",
        "content": "Analysis using ONLY provided data. If no data, say so.",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad implied: {web2_odds:.1f}%", "Polymarket: {poly_price:.1f}%", "Spread: {ev*100:+.1f}%"],
    "news_footer": "Analysis based on available data as of report generation"
  }}
}}
```

**FINAL CHECK:** Before submitting, verify: (1) {team_name} is NOT listed as its own opponent, (2) No fabricated statistics, (3) Headlines are unique to this team.
"""

    # ==============================================================================
    # ⚽️ FIFA World Cup / Tournament Logic (FIFA 杯赛) - "Bracket Logic"
    # ==============================================================================
    def _get_fifa_tournament_prompt(self, context: Dict[str, Any], intelligence: str = "", lang_instruction: str = "") -> str:
        team_name = context.get('team_name', 'Unknown Team')
        web2_odds = context.get('web2_odds', 0)
        poly_price = context.get('poly_price', 0)
        ev = context.get('ev', 0)

        # 构建情报注入块
        intelligence_block = f"\n{intelligence}\n" if intelligence else ""

        # 无情报时的警告
        no_data_warning = ""
        if not intelligence:
            no_data_warning = """
# ⚠️ NO REAL-TIME INTELLIGENCE AVAILABLE
You have NO external data (injuries, squad news, manager updates). You MUST:
1. State "No specific squad/injury data available" when discussing fitness
2. Focus ONLY on publicly known facts: FIFA rankings, historical tournament records, known squad composition
3. Do NOT invent statistics or specific matchup scenarios that aren't in the Context Data
4. If uncertain about group opponents, say "Group draw pending" or "Opponents TBD"
"""

        return f"""# Role
You are PolyDelta's World Cup Strategist & Senior Football Analyst.
Your goal is to analyze the "Tournament Tree" and evaluate if **{team_name}** is undervalued or a trap.
{lang_instruction}

# CRITICAL INSTRUCTION: ANTI-TEMPLATE RULES

## Rule 1: SELF-EXCLUSION (MANDATORY)
When listing group opponents, knockout path teams, or "Group of Death" scenarios:
- **{team_name}** can NEVER appear as its own opponent
- Before outputting any opponent list, verify {team_name} is NOT included

## Rule 2: NO HALLUCINATED DATA
- Do NOT copy generic examples like "Croatia (Modric) + Italy (Donnarumma)" for EVERY team
- Do NOT invent fitness percentages, injury timelines, or specific stats
- Only reference {team_name}'s ACTUAL group opponents if known and provided in Context Data
- If group draw is unknown, state: "Group opponents pending draw"

## Rule 3: TEAM-SPECIFIC ANALYSIS ONLY
- Research {team_name}'s REAL FIFA ranking, recent tournament history, and known squad
- Do NOT reuse the same "midfielder duel" or "keeper battle" examples for different teams
- Each analysis must reflect {team_name}'s unique strengths/weaknesses

## Rule 4: DYNAMIC SENTENCE STRUCTURE
- Vary your opening sentences across different sections
- Generate headlines SPECIFIC to {team_name}'s situation, not generic templates
- Avoid phrases like "Group of Death" unless {team_name} is ACTUALLY in one
{no_data_warning}
# Context Data
- Team: {team_name}
- Web2 Bookmaker Implied Probability: {web2_odds:.1f}%
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%
{intelligence_block}
# Analysis Framework (The "Bracket" Logic)

## 1. Group Stage Survival
* Name ONLY the actual group opponents from Context Data (if available)
* If group is unknown, state "Awaiting group draw" - do NOT fabricate opponents
* Analyze based on {team_name}'s known playing style and historical performance

## 2. The Knockout Path
* Base crossover analysis on ACTUAL tournament bracket structure
* Historical data: Only cite verifiable tournament records
* If path is unknown, focus on general knockout round challenges for {team_name}'s style

## 3. Squad Depth & Manager
* Only cite players/stats from Context Data
* If no squad data, state "Squad selection pending" and analyze known core players only

# Output Requirements
Return a JSON object with the following structure:
```json
{{
  "strategy_card": {{
    "score": 68,
    "status": "Accumulate",
    "headline": "Headline UNIQUE to {team_name}'s actual situation",
    "analysis": "Analysis using ONLY data from Context above",
    "kelly_advice": "Kelly recommendation based on the EV spread",
    "risk_text": "Key risk - do NOT list {team_name} as opponent",
    "hedging_tip": "Target price based on poly_price above"
  }},
  "news_card": {{
    "prediction": "Team's realistic ceiling based on current data",
    "confidence": "High/Medium/Low",
    "confidence_pct": 65,
    "pillars": [
      {{
        "icon": "⚔️",
        "title": "UNIQUE headline for {team_name}'s specific situation",
        "content": "Analysis using ONLY provided data. If no data, acknowledge uncertainty.",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad implied: {web2_odds:.1f}%", "Polymarket: {poly_price:.1f}%", "Spread: {ev*100:+.1f}%"],
    "news_footer": "Analysis based on available data as of report generation"
  }}
}}
```

**FINAL CHECK:** Before submitting, verify: (1) {team_name} is NOT listed as its own opponent, (2) No fabricated statistics or copied examples, (3) Analysis reflects {team_name}'s real situation.
"""

    # ==============================================================================
    # 🏀/⚽️ Daily Match Logic (单日比赛通用)
    # ==============================================================================
    def _get_daily_match_prompt(self, sport: str, context: Dict[str, Any], intelligence: str = "", lang_instruction: str = "") -> str:
        home_team = context.get('home_team', 'Home')
        away_team = context.get('away_team', 'Away')
        home_odds = context.get('home_odds', 0)
        away_odds = context.get('away_odds', 0)
        poly_home = context.get('poly_home', 0)
        poly_away = context.get('poly_away', 0)
        max_ev = context.get('max_ev', 0)

        # 构建情报注入块
        intelligence_block = f"\n{intelligence}\n" if intelligence else ""

        # 无情报时的警告
        no_data_warning = ""
        if not intelligence:
            no_data_warning = """
# ⚠️ NO REAL-TIME INTELLIGENCE AVAILABLE
You have NO external data (injuries, lineups, recent news). You MUST:
1. For Availability: State "No injury report available" - do NOT invent injuries or "GTD" statuses
2. For Form: State "Recent form data unavailable" - do NOT fabricate win-loss records or shooting percentages
3. For H2H: State "Season series data unavailable" if not provided
4. For Advanced Stats: State "Advanced metrics unavailable" - do NOT invent Net Ratings or efficiency numbers
5. Focus on what IS provided: the odds data and team names
"""

        return f"""# Role
You are a Senior Sports Analyst for {sport}.
{lang_instruction}

# CRITICAL INSTRUCTION: ANTI-TEMPLATE RULES

## Rule 1: NO HALLUCINATED STATISTICS
- Do NOT invent specific numbers like "fitness drops 12%", "7-3 L10", or "Net Rating +4.2"
- Do NOT fabricate injury statuses unless EXPLICITLY provided in the Context Data below
- If a statistic is not in the Context Data, say "Data unavailable" for that category
- NEVER copy percentages from training examples - each game's data is unique

## Rule 2: MATCH-SPECIFIC ANALYSIS ONLY
- This analysis is ONLY for: **{home_team}** vs **{away_team}**
- Do NOT reuse analysis patterns from other team matchups
- Every claim must be verifiable from the Context Data provided

## Rule 3: HONEST UNCERTAINTY
- If injury data is missing: "No injury report available for this matchup"
- If form data is missing: "Recent performance data not provided"
- If H2H data is missing: "Season series records unavailable"
- Honesty about data gaps is MORE valuable than fabricated confidence

## Rule 4: DYNAMIC SENTENCE STRUCTURE
- NEVER start multiple pillars with identical patterns
- Vary your headline style for each pillar
- Avoid the phrase "Key rotation healthy" - it's become a template marker
{no_data_warning}
# Match Data
- **{home_team}** (Home) vs **{away_team}** (Away)
- Web2 Odds: {home_team} {home_odds:.1f}% | {away_team} {away_odds:.1f}%
- Polymarket: {home_team} {poly_home:.1f}% | {away_team} {poly_away:.1f}%
- Max EV: {max_ev*100:+.1f}%
{intelligence_block}
# Analysis Framework (4-Pillar)

1. **Availability:**
   - ONLY cite injuries from the Context Data above
   - If no injury data: State "Injury report: No data available"

2. **Form:**
   - ONLY cite win-loss records from the Context Data
   - If no form data: State "Recent form: Data unavailable"

3. **Head-to-Head:**
   - ONLY cite H2H records from the Context Data
   - If no H2H data: State "Season series: Records unavailable"

4. **Odds Analysis:**
   - Compare the Web2 vs Polymarket odds provided above
   - This is the ONE area where you HAVE data - focus your analysis here

# Output Requirements
Return a JSON object:
```json
{{
  "strategy_card": {{
    "score": 72,
    "status": "Buy",
    "headline": "Headline specific to {home_team} vs {away_team}",
    "analysis": "Analysis using ONLY provided Context Data",
    "kelly_advice": "Kelly recommendation based on {max_ev*100:+.1f}% EV",
    "risk_text": "Key risk - acknowledge data limitations if applicable"
  }},
  "news_card": {{
    "prediction": "Predicted winner based on available data",
    "confidence": "High/Medium/Low (Lower if data is limited)",
    "confidence_pct": 68,
    "pillars": [
      {{
        "icon": "🏥",
        "title": "Availability headline for {home_team}/{away_team}",
        "content": "Injury data from Context, or 'No injury data available'",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "📈",
        "title": "Form headline - UNIQUE to this matchup",
        "content": "Form data from Context, or 'Form data unavailable'",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "⚔️",
        "title": "H2H headline for {home_team} vs {away_team}",
        "content": "H2H data from Context, or 'H2H records unavailable'",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "📊",
        "title": "Odds Analysis: {max_ev*100:+.1f}% Edge",
        "content": "Compare Web2 ({home_odds:.1f}%/{away_odds:.1f}%) vs Poly ({poly_home:.1f}%/{poly_away:.1f}%)",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad implied: {home_team} {home_odds:.1f}%", "Polymarket: {home_team} {poly_home:.1f}%"],
    "news_footer": "Analysis based on available data. Limited data = lower confidence."
  }}
}}
```

**FINAL CHECK:** Before submitting, verify: (1) No fabricated statistics, (2) Data gaps are acknowledged honestly, (3) Analysis is unique to {home_team} vs {away_team}.
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
    if not any([llm_client.gemini_model, llm_client.groq_client,
                llm_client.siliconflow_client, llm_client.openrouter_client]):
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

    user_prompt = f"Analyze the championship futures for {team_name}. Provide your analysis now."

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
    if not any([llm_client.gemini_model, llm_client.groq_client,
                llm_client.siliconflow_client, llm_client.openrouter_client]):
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

    user_prompt = f"Analyze the match: {home_team} vs {away_team}. Provide your analysis now."

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
