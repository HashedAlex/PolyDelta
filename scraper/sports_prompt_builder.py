"""
PolyDelta AI 分析器的 Prompt 构建引擎
负责根据不同的体育项目 (NBA/FIFA) 和赛事类型 (Daily/Future) 生成定制化的 System Prompt

NBA 使用 "Gauntlet Logic": Path to Finals + Squad Resilience + Hedging Strategy
FIFA 使用 "Bracket Logic": Group Stage Survival + Knockout Path + Squad Depth & Manager
"""
import os
import time
import json
import httpx
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# OpenRouter 配置
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
YOUR_SITE_URL = "https://polydelta.vercel.app"
APP_NAME = "PolyDelta AI Analyst"

# 模型配置
PRIMARY_MODEL = "google/gemini-2.0-flash-exp:free"
FALLBACK_MODEL = "meta-llama/llama-3.2-3b-instruct:free"

# OpenRouter 客户端
_client = None
if OPENROUTER_API_KEY:
    _client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        timeout=httpx.Timeout(60.0, connect=10.0)
    )


class SportsPromptBuilder:
    """
    Polymarket AI 分析器的 Prompt 构建引擎
    负责根据不同的体育项目 (NBA/FIFA) 和赛事类型 (Daily/Future) 生成定制化的 System Prompt
    """

    def build(self, sport: str, event_type: str, data_context: Dict[str, Any]) -> str:
        """
        工厂方法：根据赛事类型返回对应的 System Prompt
        :param sport: 'NBA' or 'FIFA'
        :param event_type: 'DAILY' (单场) or 'FUTURE' (冠军赛)
        :param data_context: 包含赔率、ROI、分组、伤病等数据的字典
        """
        if sport.upper() == "NBA" and event_type.upper() == "FUTURE":
            return self._get_nba_playoff_prompt(data_context)
        elif sport.upper() == "FIFA" and event_type.upper() == "FUTURE":
            return self._get_fifa_tournament_prompt(data_context)
        elif event_type.upper() == "DAILY":
            return self._get_daily_match_prompt(sport, data_context)
        else:
            return "Error: Unsupported sport/event combination."

    # ==============================================================================
    # 🏀 NBA Championship / Playoffs Logic (NBA 季后赛/冠军赛) - "Gauntlet Logic"
    # ==============================================================================
    def _get_nba_playoff_prompt(self, context: Dict[str, Any]) -> str:
        team_name = context.get('team_name', 'Unknown Team')
        web2_odds = context.get('web2_odds', 0)
        poly_price = context.get('poly_price', 0)
        ev = context.get('ev', 0)

        return f"""# Role
You are PolyDelta's NBA Futures Trader & Quantitative Analyst.
Your goal is to evaluate if the current championship odds for **{team_name}** represent a "+EV Value Bet" or a "Trap".

# Context Data
- Team: {team_name}
- Web2 Bookmaker Implied Probability: {web2_odds:.1f}%
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%

# Analysis Framework (The "Gauntlet" Logic)

## 1. Path to Finals (Crucial)
* **Conference Disparity:** Explicitly analyze if the team is in the West (Hard Mode) or East (Easy Mode).
* **Seeding Danger:**
    - If Seed #7-10: WARNING. Must mention "Play-In Tournament volatility" (Single elimination risk).
    - If Seed #4-5: WARNING. No home-court advantage in Round 1.
* **Projected Matchups:** Do they face a "Bad Matchup" (e.g., a small team facing a team with dominant bigs)?

## 2. Squad Resilience
* **Health:** Don't just list injuries. Analyze "Durability". Can their stars survive 4 rounds / 28 games?
* **Rotation Depth:** Futures are won by the bench. Does this team have a reliable 7-8 man rotation?

## 3. Hedging Strategy (For Investors)
* Suggest a specific hedging point.
* Example: "Buy now at low odds. If they reach Conference Finals, their price will double, allowing a risk-free sell-off."

# Output Requirements
Return a concise analysis in Markdown format (under 200 words):
1. **Value Assessment**: Is this +EV or a Trap?
2. **Path Analysis**: Conference difficulty and projected matchups
3. **Risk Factors**: Health, depth, variance concerns
4. **Recommendation**: Buy/Wait/Sell with specific hedging advice

**Tone:** Professional, wary of "recency bias", focused on long-term path.
"""

    # ==============================================================================
    # ⚽️ FIFA World Cup / Tournament Logic (FIFA 杯赛) - "Bracket Logic"
    # ==============================================================================
    def _get_fifa_tournament_prompt(self, context: Dict[str, Any]) -> str:
        team_name = context.get('team_name', 'Unknown Team')
        web2_odds = context.get('web2_odds', 0)
        poly_price = context.get('poly_price', 0)
        ev = context.get('ev', 0)

        return f"""# Role
You are PolyDelta's World Cup Strategist.
Your goal is to analyze the "Tournament Tree" and evaluate if **{team_name}** is undervalued or a trap.

# Context Data
- Team: {team_name}
- Web2 Bookmaker Implied Probability: {web2_odds:.1f}%
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%

# Analysis Framework (The "Bracket" Logic)

## 1. Group Stage Survival (The First Filter)
* **"Group of Death" Check:** If opponents include 2+ Top 15 nations, DRASTICALLY LOWER the win probability.
* **Rotation Risk:** Will they need to play starters 90mins every group game? This leads to fatigue in Knockouts.

## 2. The Knockout Path (Path to Glory)
* **Crossover Analysis:** If {team_name} wins their group, who do they play in R16?
    * Scenario A: Likely plays Runner-up of a weak group → **High Value (Buy)**.
    * Scenario B: Likely plays Brazil/France in R16 → **Trap (Wait)**.
* **Historical Trends:** Mention "Tournament Pedigree" (e.g., Croatia/Germany perform better in tournaments than friendlies).

## 3. Squad Depth & Manager
* **Impact Subs:** In modern football (5 subs rule), bench depth is key. Do they have game-changers?
* **Tournament Management:** Does the manager have a history of pragmatic, defensive tournament play (e.g., Deschamps)?

# Output Requirements
Return a concise analysis in Markdown format (under 200 words):
1. **Value Assessment**: Undervalued or Overpriced?
2. **Bracket Difficulty**: Strength of Schedule analysis
3. **Risk Factors**: Group stage, fatigue, knockout variance
4. **Recommendation**: Buy/Wait/Sell with specific hedging advice

**Keyword Requirement:** You MUST use the phrase "Strength of Schedule" or "Bracket Difficulty" in your analysis.
"""

    # ==============================================================================
    # 🏀/⚽️ Daily Match Logic (单日比赛通用)
    # ==============================================================================
    def _get_daily_match_prompt(self, sport: str, context: Dict[str, Any]) -> str:
        home_team = context.get('home_team', 'Home')
        away_team = context.get('away_team', 'Away')
        home_odds = context.get('home_odds', 0)
        away_odds = context.get('away_odds', 0)
        poly_home = context.get('poly_home', 0)
        poly_away = context.get('poly_away', 0)
        max_ev = context.get('max_ev', 0)

        base_factors = "Injuries, Back-to-back, Home Court" if sport.upper() == "NBA" else "Recent Form, Suspensions, Tactical Matchup"

        return f"""# Role
You are a Quantitative Sports Analyst for {sport}.

# Match Data
- **{home_team}** (Home) vs **{away_team}** (Away)
- Web2 Odds: {home_team} {home_odds:.1f}% | {away_team} {away_odds:.1f}%
- Polymarket: {home_team} {poly_home:.1f}% | {away_team} {poly_away:.1f}%
- Max EV: {max_ev*100:+.1f}%

# Analysis Logic (Daily Match)
1. **Arbitrage Check:**
   - If EV > 0: Identify which side has value and why
   - Analyze as a **Value Bet** using implied probability divergence

2. **The "4-Pillar" Prediction Model:**
   - **Availability:** {base_factors}
   - **Form:** Last 5 games trend
   - **Head-to-Head:** Historical dominance
   - **Advanced Stats:** (Net Rating for NBA, xG for FIFA)

# Output Requirements
Return a concise analysis in Markdown format (under 150 words):
1. **Value Side**: Which team/outcome has edge and why
2. **Divergence Cause**: Why do Web2 and Polymarket disagree?
3. **Risk Assessment**: Key factors that could invalidate the edge
4. **Verdict**: Clear recommendation with confidence level

If No Edge: Output "Wait" and explain why (e.g., "Market is efficient, no value found").
"""


def generate_championship_analysis(
    team_name: str,
    sport_type: str,
    web2_odds: float,
    poly_price: float,
    ev: float
) -> Optional[str]:
    """
    为冠军盘口生成 AI 分析报告

    Args:
        team_name: 球队/国家名称
        sport_type: 'nba' 或 'world_cup'
        web2_odds: Web2 隐含胜率 (0-1 格式)
        poly_price: Polymarket 价格 (0-1 格式)
        ev: EV 差值 (0-1 格式)

    Returns:
        Markdown 格式的分析报告，或 None
    """
    if not _client:
        print("   ⚠️ OPENROUTER_API_KEY 未设置，跳过 AI 分析")
        return None

    # EV 门槛：冠军盘口 >= 5%
    if ev < 0.05:
        return None

    print(f"🧠 AI Analyst (Championship): {team_name} ({sport_type}) - EV: +{ev*100:.1f}%")

    # 构建 prompt
    builder = SportsPromptBuilder()
    context = {
        'team_name': team_name,
        'web2_odds': web2_odds * 100,  # 转换为百分比
        'poly_price': poly_price * 100,
        'ev': ev,
    }

    # 根据 sport_type 选择分析框架
    if sport_type == 'nba':
        system_prompt = builder.build('NBA', 'FUTURE', context)
    else:
        system_prompt = builder.build('FIFA', 'FUTURE', context)

    user_prompt = f"Analyze the championship futures for {team_name}. Provide your analysis now."

    # 调用 LLM
    return _call_llm_with_fallback(system_prompt, user_prompt)


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
    为每日比赛生成 AI 分析报告

    Args:
        home_team: 主队名称
        away_team: 客队名称
        sport_type: 'nba' 或 'world_cup'
        home_odds: 主队 Web2 隐含胜率 (0-1)
        away_odds: 客队 Web2 隐含胜率 (0-1)
        poly_home: 主队 Polymarket 价格 (0-1)
        poly_away: 客队 Polymarket 价格 (0-1)
        max_ev: 最大 EV 差值 (0-1)

    Returns:
        Markdown 格式的分析报告，或 None
    """
    if not _client:
        print("   ⚠️ OPENROUTER_API_KEY 未设置，跳过 AI 分析")
        return None

    # EV 门槛：每日比赛 >= 2%
    if max_ev < 0.02:
        return None

    print(f"🧠 AI Analyst (Daily): {home_team} vs {away_team} - EV: +{max_ev*100:.1f}%")

    # 构建 prompt
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

    return _call_llm_with_fallback(system_prompt, user_prompt)


def _call_llm_with_fallback(system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    调用 LLM，带 fallback 机制
    """
    # 尝试主要模型 (Gemini Flash)
    try:
        time.sleep(1)  # 避免速率限制
        result = _call_llm(PRIMARY_MODEL, system_prompt, user_prompt)
        if result:
            print(f"   ✅ Gemini Flash 报告生成成功")
            return result
    except Exception as e:
        print(f"   ⚠️ Primary model error: {str(e)[:60]}...")

    # Fallback: Llama 3.2
    print(f"   🔄 Switching to Fallback (Llama 3.2)...")
    try:
        time.sleep(1)
        result = _call_llm(FALLBACK_MODEL, system_prompt, user_prompt)
        if result:
            print(f"   ✅ Llama 3.2 报告生成成功")
            return result
    except Exception as e:
        print(f"   ❌ Fallback model error: {str(e)[:60]}...")

    return None


def _call_llm(model: str, system_prompt: str, user_prompt: str) -> Optional[str]:
    """
    调用 LLM API
    """
    completion = _client.chat.completions.create(
        extra_headers={"HTTP-Referer": YOUR_SITE_URL, "X-Title": APP_NAME},
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=600,
    )
    content = completion.choices[0].message.content

    # 清洗思维链标记
    if content and "<think>" in content:
        parts = content.split("</think>")
        if len(parts) > 1:
            content = parts[-1].strip()

    return content.replace("```markdown", "").replace("```", "").strip() if content else None


# 使用示例
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
