import os
import time
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ---------------- CONFIGURATION ---------------- #
YOUR_SITE_URL = "https://polydelta.vercel.app"
APP_NAME = "PolyDelta Arbitrage"


class LLMClient:
    """
    LLM Client using OpenRouter API.
    """

    # OpenRouter Model Configuration
    OPENROUTER_MODEL = "google/gemini-2.0-flash-001"
    OPENROUTER_FALLBACK = "deepseek/deepseek-chat"

    def __init__(self):
        """Initialize OpenRouter client."""
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

        self.openrouter_client = None
        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key,
                timeout=httpx.Timeout(60.0, connect=10.0)
            )

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
            max_tokens=500,
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

        Returns: Raw response string (JSON or Markdown depending on prompt)
        """
        if not self.openrouter_client:
            print("   [LLMClient] OpenRouter not configured")
            return None

        try:
            result = self._call_openrouter(system_prompt, user_prompt)
            if result:
                print("   [LLMClient] OpenRouter success")
                return result
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"   [LLMClient] OpenRouter failed: {error_msg}")

        return None


# Global LLMClient instance
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get or create the global LLMClient instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def generate_ai_report(match_data, is_championship=False):
    """
    Generate AI analysis report using the LLMClient.
    """
    client = get_llm_client()

    if not client.openrouter_client:
        print("   No LLM provider configured, skipping AI analysis")
        return None

    ev = float(match_data.get('ev', 0))
    threshold = 0.05 if is_championship else 0.02

    # Threshold filter: only analyze high-value opportunities
    if ev < threshold:
        return None

    title = match_data.get('title', 'Unknown Match')
    web2_odds = match_data.get('web2_odds', 0)
    poly_price = match_data.get('polymarket_price', 0)
    ev_percent = ev * 100

    print(f"   AI Analyst observing: {title} (EV: +{ev_percent:.1f}%)")

    system_prompt = "You are a professional US Sports Betting Analyst. Use standard US sports betting terminology (Spread, Moneyline, Props, Juice, Sharp Money, Square Money). Analyze the divergence between Bookmaker Odds (Sharp Money) and Polymarket Price (Retail Sentiment). Focus on WHY the gap exists. Output strictly clean Markdown."
    user_prompt = f"Analyze arbitrage for: {title}. Web2 Odds: {web2_odds:.1f}%. Polymarket Price: {poly_price:.1f}%. Net EV: +{ev_percent:.1f}%. Provide: 1. Divergence Cause 2. Risk Assessment 3. Verdict. Keep it concise (under 150 words)."

    time.sleep(1)  # Rate limit protection
    result = client.generate_analysis(system_prompt, user_prompt)

    if result:
        print(f"   AI report generated successfully")

    return result


# Legacy function compatibility
def call_llm(model, sys_prompt, user_prompt):
    """Legacy function for backward compatibility. Uses OpenRouter."""
    client = get_llm_client()
    if client.openrouter_client:
        return client._call_openrouter(sys_prompt, user_prompt, model=model)
    return None
