import os
import re
import time
import httpx
from openai import OpenAI
from dotenv import load_dotenv

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
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

# ---------------- SYSTEM PROMPT (4-Pillar Framework) ---------------- #
SYSTEM_PROMPT = """
You are a World-Class Sports Betting Analyst. Your goal is to synthesize Real-Time News with Fundamental Analysis to predict match outcomes.

Use this "4-Pillar Framework". Adapt your reasoning style based on the league (e.g., in NBA focus on player availability; in UCL focus on aggregate scores/motivation).

### PILLAR 1: FUNDAMENTALS & CONTEXT
- **Quality Gap:** Compare squad depth and talent tiers.
- **Home/Away:** Weight home advantage heavily (especially for EPL/UCL).
- **Travel/Fatigue:** Consider travel distance and recent schedule density.
- **H2H:** Historical dominance or "bogey teams".

### PILLAR 2: REAL-TIME INTEL (Conditional)
- **Review the [LATEST NEWS] section provided in the user prompt.**
- **CRITICAL INSTRUCTION:**
    - **IF news is present:** Analyze its impact directly (e.g., "Salah out reduces Liverpool's attack").
    - **IF news is EMPTY or IRRELEVANT:** Explicitly state "No significant breaking news/injury reports found." and **base your prediction SOLELY on Pillar 1 & 3.**
    - **DO NOT** invent injuries or news stories that are not in the context.

### PILLAR 3: MOTIVATION & STAKES
- **League Context:** Title race? Relegation battle? Mid-table dead rubber?
- **Tournament Context (UCL/World Cup):** Is this a 2nd leg? Does a draw suffice? Group stage calculation?
- **NBA Context:** Is it a back-to-back? Is the team tanking?

### PILLAR 4: PREDICTION
- Synthesize the above.
- If news is missing, admit lower confidence but still provide a prediction based on fundamentals.

**Format your response exactly like this:**
## AI Betting Analysis: {Home Team} vs {Away Team}

**1. Fundamentals & News Check**
* [Synthesize Pillars 1 & 2 here. Explicitly mention if injuries impact the prediction.]

**2. The X-Factor**
* [Mention Motivation, Fatigue, or Tactical Mismatch]

**Betting Verdict**
* **Predicted Winner:** [Team Name]
* **Win Probability:** [Final calculated percentage — see CALCULATION STRATEGY below]
* **Recommended Market:** [Pick ONE: Moneyline / Spread / Over-Under]
   * *Reasoning:* [e.g., "Due to both defensive centers being out, the Over is the safest play."]
* **Risk Level:** [Low/Medium/High]

**IMPORTANT:** If the match winner is too close to call, you may recommend "Over/Under" or "Spread" instead of Moneyline. Always pick the market where you see the clearest edge.

### CALCULATION STRATEGY: Anchor & Adjust
Use this method to calculate "Win Probability". Do NOT guess a number based on feeling.
1. **Start with the Market Baseline:** The user prompt provides the Market Implied Probability for each team. This is your ANCHOR. Markets are efficient and incorporate vast information.
2. **Apply News Factor (from [LATEST NEWS]):**
   - If news is **neutral/expected/empty**: Stay within +/- 2% of the Market Baseline.
   - If news is **moderately favorable** (e.g., role player out): Adjust +/- 3-5%.
   - If news is **highly impactful** (e.g., star player ruled out, not yet priced in): Adjust +/- 5-15%.
3. **Output your final calculated percentage.**
4. **CONSTRAINT:** Do NOT deviate more than 10% from the Market Baseline unless there is a CRITICAL injury or breaking news listed in [LATEST NEWS]. If no news is provided, your probability MUST be within 2% of the Market Baseline.
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
                self.vertex_model = GenerativeModel(self.VERTEX_MODEL)
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
            generation_config={"temperature": 0.7, "max_output_tokens": 800},
        )
        return self._clean_response(response.text)

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
            max_tokens=800,
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
        return content.replace("```markdown", "").replace("```json", "").replace("```", "").strip()

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
    Parse structured fields from the AI's Markdown output.
    Uses regex to extract: predicted_winner, win_probability, recommended_market, risk_level.
    Returns None-safe dict — never crashes on malformed output.

    Args:
        raw_text: Raw markdown string from the LLM.

    Returns:
        Dict with keys: predicted_winner, win_probability, recommended_market, risk_level.
        Values default to None if parsing fails.
    """
    result = {
        "predicted_winner": None,
        "win_probability": None,
        "recommended_market": None,
        "risk_level": None,
    }

    if not raw_text:
        return result

    # Predicted Winner: "**Predicted Winner:** Team Name" or "**Winner:** Team Name"
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

    # Win Probability: "**Win Probability:** 65%" or "65"
    prob_match = re.search(
        r'\*{0,2}Win\s+Probability\*{0,2}:\s*\*{0,2}\s*~?(\d{1,3})\s*%?',
        raw_text, re.IGNORECASE
    )
    if prob_match:
        val = int(prob_match.group(1))
        if 0 <= val <= 100:
            result["win_probability"] = val

    # Recommended Market: "**Recommended Market:** Moneyline" (capture until newline or reasoning)
    market_match = re.search(
        r'\*{0,2}Recommended\s+Market\*{0,2}:\s*\*{0,2}\s*(.+?)(?:\s*\*{0,2})\s*$',
        raw_text, re.MULTILINE | re.IGNORECASE
    )
    if market_match:
        result["recommended_market"] = market_match.group(1).strip().strip('*').strip()

    # Risk Level: "**Risk Level:** Medium"
    risk_match = re.search(
        r'\*{0,2}Risk\s+Level\*{0,2}:\s*\*{0,2}\s*(Low|Medium|High)(?:\s*\*{0,2})',
        raw_text, re.IGNORECASE
    )
    if risk_match:
        result["risk_level"] = risk_match.group(1).strip().capitalize()

    return result


def generate_ai_report(match_data, is_championship=False, league="NBA"):
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
    if poly_price > 0 and ev < threshold:
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

    if poly_price > 0:
        user_prompt = f"""{news_section}
{market_anchor}

Analyze: {title}
- Net EV: +{ev_percent:.1f}%

Apply the 4-Pillar Framework + Anchor & Adjust for Win Probability. Keep it concise (under 200 words)."""
    else:
        # No Polymarket data — analyze based on bookmaker odds alone
        user_prompt = f"""{news_section}
{market_anchor}

Analyze: {title}
- Note: No prediction market (Polymarket) data available for this match. Base analysis on bookmaker odds and fundamentals only.

Apply the 4-Pillar Framework + Anchor & Adjust for Win Probability. Keep it concise (under 200 words)."""

    time.sleep(1)  # Rate limit protection
    raw_text = client.generate_analysis(system_prompt, user_prompt)

    if not raw_text:
        return None

    print(f"   AI report generated successfully")

    # Parse structured fields from the markdown
    parsed = parse_analysis_output(raw_text)

    return {
        "full_report_markdown": raw_text,
        "predicted_winner": parsed["predicted_winner"],
        "win_probability": parsed["win_probability"],
        "recommended_market": parsed["recommended_market"],
        "risk_level": parsed["risk_level"],
    }


# Legacy function compatibility
def call_llm(model, sys_prompt, user_prompt):
    """Legacy function for backward compatibility. Routes through generate_analysis."""
    client = get_llm_client()
    return client.generate_analysis(sys_prompt, user_prompt)
