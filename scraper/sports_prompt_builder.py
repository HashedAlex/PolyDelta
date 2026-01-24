"""
PolyDelta AI 分析器的 Prompt 构建引擎
负责根据不同的体育项目 (NBA/FIFA) 和赛事类型 (Daily/Future) 生成定制化的 System Prompt

NBA 使用 "Gauntlet Logic": Path to Finals + Squad Resilience + Hedging Strategy
FIFA 使用 "Bracket Logic": Group Stage Survival + Knockout Path + Squad Depth & Manager

v2.0: 集成 SportsIntelligenceService 实时情报注入
"""
import os
import time
import json
import httpx
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

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
        print("⚠️ SportsIntelligenceService not available. Running without real-time intelligence.")

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

    v2.0: 支持实时情报注入 (Real-Time Intelligence Injection)
    v3.0: 支持双语输出 (Bilingual Support - EN/ZH)
    """

    # 中文模式指令集 (Chinese Mode Instruction Set)
    CHINESE_INSTRUCTION = """
# LANGUAGE REQUIREMENT: SIMPLIFIED CHINESE (简体中文)

1. **Native Thought Process (原生思维):**
   - Do not translate the English context word-for-word. Understand the data (RSS/Tweets) and synthesize a native Chinese analysis.
   - 不要逐字翻译英文内容。理解数据后，用地道的中文撰写分析。

2. **Identity Preservation (名称保留规则):**
   - **Player/Team Names:** For the first mention, use: **中文名 (English Name)**.
     - Example: "勒布朗·詹姆斯 (LeBron James) 出战成疑。"
   - **Source Names:** Keep data source names in English.
     - Example: "据 Underdog NBA 报道..." (NOT "据下风NBA...")

3. **Professional Terminology (专业术语映射):**
   - "Spread" -> "让分盘"
   - "Moneyline" -> "独赢盘"
   - "Total / Over-Under" -> "大小分"
   - "Odds" -> "赔率"
   - "Vig / Juice" -> "水位 / 抽水"
   - "Liquidity" -> "流动性 / 深度"
   - "Game Time Decision (GTD)" -> "赛前决定 (GTD)"
   - "Arbitrage" -> "套利"
   - "Expected Value (EV)" -> "期望值 (EV)"
   - "Kelly Criterion" -> "凯利公式"
   - "Polymarket" -> "Polymarket (链上市场)"

4. **Tone (语气):**
   - Professional, Objective, Analytical. 专业、客观、分析性强。
   - Avoid generic translation style. 避免翻译腔。
"""

    def __init__(self, enable_intelligence: bool = True):
        """
        初始化 Prompt Builder

        Args:
            enable_intelligence: 是否启用实时情报服务 (默认启用)
        """
        self.enable_intelligence = enable_intelligence and HAS_INTELLIGENCE_SERVICE

    def build(self, sport: str, event_type: str, data_context: Dict[str, Any], language: str = "en") -> str:
        """
        工厂方法：根据赛事类型返回对应的 System Prompt

        :param sport: 'NBA' or 'FIFA'
        :param event_type: 'DAILY' (单场) or 'FUTURE' (冠军赛)
        :param data_context: 包含赔率、ROI、分组、伤病等数据的字典
        :param language: 'en' (English, default) or 'zh' (Chinese)
        """
        # 获取实时情报 (如果启用)
        intelligence_context = self._fetch_intelligence(sport, event_type, data_context)

        # 获取语言指令 (Anti-Regression Logic)
        lang_instruction = self._get_language_instruction(language)

        if sport.upper() == "NBA" and event_type.upper() == "FUTURE":
            return self._get_nba_playoff_prompt(data_context, intelligence_context, lang_instruction)
        elif sport.upper() == "FIFA" and event_type.upper() == "FUTURE":
            return self._get_fifa_tournament_prompt(data_context, intelligence_context, lang_instruction)
        elif event_type.upper() == "DAILY":
            return self._get_daily_match_prompt(sport, data_context, intelligence_context, lang_instruction)
        else:
            return "Error: Unsupported sport/event combination."

    def _get_language_instruction(self, language: str) -> str:
        """
        Anti-Regression Logic: 获取语言指令

        严格分支逻辑确保英文版本不受影响
        """
        if language == "zh":
            # 中文模式：注入专业术语和思维指令
            return self.CHINESE_INSTRUCTION
        else:
            # 英文模式 (默认)：保持原有逻辑不变
            return "Output strictly in English. Tone: Professional, Data-driven, and Direct."

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

        return f"""# Role
You are PolyDelta's NBA Futures Trader & Senior Sports Analyst.
Your goal is to evaluate if the current championship odds for **{team_name}** represent a "+EV Value Bet" or a "Trap".
{lang_instruction}

# CRITICAL INSTRUCTION: BAN GENERIC EXPLANATIONS

* **NO DEFINITIONS:** Do NOT explain what "Home Court Advantage" is. Do NOT explain what "Western Conference difficulty" means. The user already knows this.
* **SPECIFICITY RULE:** Every claim must be backed by a **Proper Noun** (Player Name, Opponent Team Name) or a **Number** (Stat, Date).
  - BAD: "The team has a hard schedule."
  - GOOD: "Facing Denver (Jokic) and Boston (Tatum) back-to-back is a nightmare scenario."
* **NO REPETITION:** Do NOT use generic phrases like "Western Conference = Hard Mode". Instead, analyze the SPECIFIC matchup (e.g., "Thunder vs Nuggets: OKC lacks the size to guard Jokic").
* **DYNAMIC HEADLINES:** Generate punchy, news-style headlines for each analysis point. NOT "Path to Finals", but "首轮即遇湖人？" or "Round 2 Nightmare: Denver Awaits".

# Context Data
- Team: {team_name}
- Web2 Bookmaker Implied Probability: {web2_odds:.1f}%
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%
{intelligence_block}
# Analysis Framework (The "Gauntlet" Logic)

## 1. Projected Playoff Path (BE SPECIFIC)
* **Name the opponents:** "R1 vs Lakers (LeBron/AD), R2 vs Nuggets (Jokic), WCF vs Clippers (Kawhi)"
* **Matchup Analysis:** Identify the SPECIFIC weakness. Example: "Holmgren has never guarded Jokic in playoffs. This single matchup reduces OKC's EV significantly."
* If Play-In: "Single-game variance against Miami's zone defense is a trap."

## 2. Squad Resilience (CITE PLAYERS)
* **Health:** Don't say "injury concerns". Say "SGA has played 78+ games for 3 seasons - elite durability" or "Kawhi's load management means he'll miss 1-2 playoff games guaranteed."
* **Depth Analysis:** "Bench mob averaging 42 PPG (3rd in NBA)" or "No reliable backup center behind Embiid."

## 3. Hedging Strategy (SPECIFIC NUMBERS)
* "Buy at {poly_price:.1f}%. Target sell at Conference Finals (~35%). Risk-free hedge possible."

# Output Requirements
Return a JSON object with the following structure:
```json
{{
  "strategy_card": {{
    "score": 75,
    "status": "Accumulate",
    "headline": "Dynamic news-style headline here",
    "analysis": "Specific analysis with player names and stats",
    "kelly_advice": "Specific Kelly recommendation",
    "risk_text": "Key risk with specific opponent/player",
    "hedging_tip": "Specific hedge target price"
  }},
  "news_card": {{
    "prediction": "Team's ceiling (Trophy Contender/Semi-Final/etc)",
    "confidence": "High/Medium/Low",
    "confidence_pct": 72,
    "pillars": [
      {{
        "icon": "🎯",
        "title": "DYNAMIC: Generate a punchy headline like '首轮噩梦：湖人等候' or 'Round 1 Trap: Lakers Await'",
        "content": "SPECIFIC analysis with player names, not generic explanations",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad implied: X%", "Polymarket: Y%", "Spread: Z%"],
    "news_footer": "Brief methodology note"
  }}
}}
```

**REMEMBER:** NO generic explanations. Every sentence must have a proper noun or number.
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

        return f"""# Role
You are PolyDelta's World Cup Strategist & Senior Football Analyst.
Your goal is to analyze the "Tournament Tree" and evaluate if **{team_name}** is undervalued or a trap.
{lang_instruction}

# CRITICAL INSTRUCTION: BAN GENERIC EXPLANATIONS

* **NO DEFINITIONS:** Do NOT explain what a "Group of Death" is. Do NOT explain what "tournament fatigue" means. The user already knows this.
* **SPECIFICITY RULE:** Every claim must be backed by a **Proper Noun** (Player Name, Opponent Team Name) or a **Number** (Stat, Date).
  - BAD: "They have a tough group."
  - GOOD: "Group with Croatia (Modric) and Italy (Donnarumma) - must beat both midfield battles."
* **NO REPETITION:** Do NOT use generic phrases like "Group of Death scenarios". Instead, analyze the SPECIFIC matchup (e.g., "Spain vs Croatia: Pedri vs Modric midfield duel").
* **DYNAMIC HEADLINES:** Generate punchy, news-style headlines. NOT "Group Stage Analysis", but "莫德里奇的复仇？" or "Modric's Revenge: Croatia Awaits".

# Context Data
- Team: {team_name}
- Web2 Bookmaker Implied Probability: {web2_odds:.1f}%
- Polymarket Price: {poly_price:.1f}%
- EV Spread: {ev*100:+.1f}%
{intelligence_block}
# Analysis Framework (The "Bracket" Logic)

## 1. Group Stage Survival (NAME THE OPPONENTS)
* **Specific Matchups:** "Must beat Croatia's aging but elite midfield (Modric/Kovacic). A draw vs Italy puts pressure on dead rubber."
* **Key Battles:** Identify the tactical mismatch. "Spain's possession style struggles against Croatia's compact 4-3-3."

## 2. The Knockout Path (NAME THE R16 OPPONENT)
* **Crossover Analysis:** "Group winner plays Runner-up of Group F (likely Belgium/Morocco). Morocco's low block is Spain's worst nightmare."
* **Historical Data:** "Spain has lost 3 of last 4 knockout games on penalties."

## 3. Squad Depth & Manager (CITE PLAYERS)
* **Impact Subs:** "Bench includes Ferran Torres (12 goals last 20 caps) and Nico Williams (elite pace)."
* **Manager Style:** "Luis de la Fuente favors 4-3-3 possession - vulnerable to counter-attacks."

# Output Requirements
Return a JSON object with the following structure:
```json
{{
  "strategy_card": {{
    "score": 68,
    "status": "Accumulate",
    "headline": "Dynamic news-style headline (e.g., '死亡之组：克罗地亚+意大利')",
    "analysis": "Specific analysis with player names and tactical details",
    "kelly_advice": "Specific Kelly recommendation",
    "risk_text": "Key risk with specific opponent/player",
    "hedging_tip": "Specific hedge target price"
  }},
  "news_card": {{
    "prediction": "Team's ceiling (Trophy Contender/Quarter-Final/etc)",
    "confidence": "High/Medium/Low",
    "confidence_pct": 65,
    "pillars": [
      {{
        "icon": "⚔️",
        "title": "DYNAMIC: Generate a punchy headline like '莫德里奇的复仇？' or 'Midfield Battle: Modric Awaits'",
        "content": "SPECIFIC tactical analysis, not generic explanations",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad implied: X%", "Polymarket: Y%", "Spread: Z%"],
    "news_footer": "Brief methodology note"
  }}
}}
```

**REMEMBER:** NO generic explanations. Every sentence must have a proper noun (player/team/manager) or number (stat/date).
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

        return f"""# Role
You are a Senior Sports Analyst for {sport}.
{lang_instruction}

# CRITICAL INSTRUCTION: BAN GENERIC EXPLANATIONS

* **NO DEFINITIONS:** Do NOT explain what "Home Court Advantage" is. Do NOT say "Key rotation healthy." The user already knows this.
* **SPECIFICITY RULE:** Every claim must be backed by a **Proper Noun** (Player Name) or a **Number** (Stat).
  - BAD: "Key rotation healthy."
  - GOOD: "Cade Cunningham (25 PPG last 5) is peaking. Ivey questionable (ankle)."
  - BAD: "Team has good form."
  - GOOD: "7-3 in last 10, including wins over Celtics and Bucks."
* **TACTICAL MISMATCH:** Identify the SPECIFIC matchup advantage.
  - "Rockets allow 38% 3PT shooting; Pistons' spacing will punish this."
  - "Lakers' paint defense (ranked 3rd) neutralizes Embiid's post game."
* **DYNAMIC HEADLINES:** Generate news-style headlines for each pillar. NOT "Availability", but "Cunningham热火状态" or "Cade's Hot Streak".

# Match Data
- **{home_team}** (Home) vs **{away_team}** (Away)
- Web2 Odds: {home_team} {home_odds:.1f}% | {away_team} {away_odds:.1f}%
- Polymarket: {home_team} {poly_home:.1f}% | {away_team} {poly_away:.1f}%
- Max EV: {max_ev*100:+.1f}%
{intelligence_block}
# Analysis Framework (4-Pillar with SPECIFICITY)

1. **Availability (CITE PLAYERS):**
   - Name the injured players: "Jimmy Butler (knee) OUT. Herro GTD."
   - Rest advantage: "Lakers on 2nd night of B2B, Pistons rested 3 days."

2. **Form (CITE STATS):**
   - "Pistons 7-3 L10 with league-best 3PT% (41.2%)."
   - "Lakers struggling: 4-6 L10, worst road record in West."

3. **Head-to-Head (CITE GAMES):**
   - "Season series 1-1. Last meeting: Pistons won 112-108 (Cade 32pts)."

4. **Advanced Stats (CITE NUMBERS):**
   - "Net Rating: Pistons +4.2 (8th) vs Lakers -1.3 (18th)."
   - "Key edge: Pistons Rebound Rate 52% vs Lakers 47%."

# Output Requirements
Return a JSON object:
```json
{{
  "strategy_card": {{
    "score": 72,
    "status": "Buy",
    "headline": "Dynamic headline (e.g., 'Cade热火状态碾压湖人')",
    "analysis": "Specific analysis with player names and stats",
    "kelly_advice": "Quarter Kelly. Edge: +X%",
    "risk_text": "Key risk (e.g., 'If Butler returns, invalidates edge')"
  }},
  "news_card": {{
    "prediction": "Team to Win",
    "confidence": "High/Medium/Low",
    "confidence_pct": 68,
    "pillars": [
      {{
        "icon": "🏥",
        "title": "DYNAMIC: 'Butler伤缺+Herro待定' or 'Butler OUT, Herro GTD'",
        "content": "Specific injury analysis with player names",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "📈",
        "title": "DYNAMIC: 'Cade 近5场25分' or 'Cade Averaging 25 PPG'",
        "content": "Specific form stats",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "⚔️",
        "title": "DYNAMIC: '赛季交锋1-1' or 'Season Series Split 1-1'",
        "content": "Specific H2H analysis",
        "sentiment": "positive/negative/neutral"
      }},
      {{
        "icon": "📊",
        "title": "DYNAMIC: '净效率差距+5.5' or 'Net Rating Gap +5.5'",
        "content": "Specific advanced stat comparison",
        "sentiment": "positive/negative/neutral"
      }}
    ],
    "factors": ["Trad implied: X%", "Polymarket: Y%"],
    "news_footer": "4-Pillar analysis based on public data."
  }}
}}
```

**REMEMBER:** NO generic explanations. Every sentence must have a player name or stat number.
"""


def generate_championship_analysis(
    team_name: str,
    sport_type: str,
    web2_odds: float,
    poly_price: float,
    ev: float,
    language: str = "en"
) -> Optional[str]:
    """
    为冠军盘口生成 AI 分析报告

    Args:
        team_name: 球队/国家名称
        sport_type: 'nba' 或 'world_cup'
        web2_odds: Web2 隐含胜率 (0-1 格式)
        poly_price: Polymarket 价格 (0-1 格式)
        ev: EV 差值 (0-1 格式)
        language: 'en' (English) or 'zh' (Chinese)

    Returns:
        Markdown 格式的分析报告，或 None
    """
    if not _client:
        print("   ⚠️ OPENROUTER_API_KEY 未设置，跳过 AI 分析")
        return None

    # EV 门槛：冠军盘口 >= 5%
    if ev < 0.05:
        return None

    lang_label = "中文" if language == "zh" else "EN"
    print(f"🧠 AI Analyst (Championship/{lang_label}): {team_name} ({sport_type}) - EV: +{ev*100:.1f}%")

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
        system_prompt = builder.build('NBA', 'FUTURE', context, language)
    else:
        system_prompt = builder.build('FIFA', 'FUTURE', context, language)

    # 用户提示也根据语言调整
    if language == "zh":
        user_prompt = f"请分析 {team_name} 的冠军期货市场。现在提供你的分析。"
    else:
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
    max_ev: float,
    language: str = "en"
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
        language: 'en' (English) or 'zh' (Chinese)

    Returns:
        Markdown 格式的分析报告，或 None
    """
    if not _client:
        print("   ⚠️ OPENROUTER_API_KEY 未设置，跳过 AI 分析")
        return None

    # EV 门槛：每日比赛 >= 2%
    if max_ev < 0.02:
        return None

    lang_label = "中文" if language == "zh" else "EN"
    print(f"🧠 AI Analyst (Daily/{lang_label}): {home_team} vs {away_team} - EV: +{max_ev*100:.1f}%")

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
    system_prompt = builder.build(sport, 'DAILY', context, language)

    # 用户提示也根据语言调整
    if language == "zh":
        user_prompt = f"请分析比赛：{home_team} vs {away_team}。现在提供你的分析。"
    else:
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
