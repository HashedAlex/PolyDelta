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
    Robust Hybrid Provider Architecture with Waterfall Fallback.

    Supports two modes:
    - 'free': Direct API calls with waterfall (Gemini -> Groq -> SiliconFlow)
    - 'paid': OpenRouter API (legacy/premium route)
    """

    # Hardcoded Model Constants (Free Tier Optimized)
    GEMINI_MODEL = "gemini-2.0-flash"  # High rate limits, fast
    GROQ_MODEL = "llama-3.3-70b-versatile"  # Best reasoning/speed ratio
    SILICONFLOW_MODEL = "Qwen/Qwen2.5-72B-Instruct"  # Best JSON compliance & Chinese
    OPENROUTER_MODEL = "google/gemini-2.0-flash-exp:free"  # Existing OpenRouter model
    OPENROUTER_FALLBACK = "meta-llama/llama-3.2-3b-instruct:free"

    def __init__(self):
        """Initialize API clients based on available keys."""
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.google_key = os.getenv("GOOGLE_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.siliconflow_key = os.getenv("SILICONFLOW_API_KEY", "")
        self.mode = os.getenv("LLM_MODE", "free")  # 'free' or 'paid'

        # Initialize OpenRouter client (for paid mode or fallback)
        self.openrouter_client = None
        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key,
                timeout=httpx.Timeout(60.0, connect=10.0)
            )

        # Initialize Gemini client
        self.gemini_model = None
        if self.google_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_key)
                self.gemini_model = genai.GenerativeModel(
                    model_name=self.GEMINI_MODEL,
                )
                self._genai = genai
            except ImportError:
                print("   [LLMClient] google-generativeai not installed")

        # Initialize Groq client
        self.groq_client = None
        if self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
            except ImportError:
                print("   [LLMClient] groq package not installed")

        # Initialize SiliconFlow client (OpenAI-compatible)
        self.siliconflow_client = None
        if self.siliconflow_key:
            self.siliconflow_client = OpenAI(
                base_url="https://api.siliconflow.cn/v1",
                api_key=self.siliconflow_key,
                timeout=httpx.Timeout(60.0, connect=10.0)
            )

    def _call_openrouter(self, system_prompt: str, user_prompt: str, model: str = None) -> str:
        """
        Legacy/Paid Route - OpenRouter API.
        Preserves existing implementation for future paid use.
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

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """
        Direct Google Gemini API.
        Model: gemini-1.5-flash (15 RPM free tier, huge context window)
        """
        if not self.gemini_model:
            raise RuntimeError("Google API key not configured or google-generativeai not installed")

        # Recreate model with system instruction
        model = self._genai.GenerativeModel(
            model_name=self.GEMINI_MODEL,
            system_instruction=system_prompt
        )

        response = model.generate_content(
            user_prompt,
            generation_config=self._genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
            )
        )

        return self._clean_response(response.text)

    def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """
        Direct Groq API.
        Model: llama-3.3-70b-versatile (fastest inference, strong reasoning)
        """
        if not self.groq_client:
            raise RuntimeError("Groq API key not configured or groq package not installed")

        completion = self.groq_client.chat.completions.create(
            model=self.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500,
        )
        content = completion.choices[0].message.content
        return self._clean_response(content)

    def _call_siliconflow(self, system_prompt: str, user_prompt: str) -> str:
        """
        Direct SiliconFlow API (OpenAI-compatible).
        Model: Qwen/Qwen2.5-72B-Instruct (best JSON compliance & Chinese support)
        """
        if not self.siliconflow_client:
            raise RuntimeError("SiliconFlow API key not configured")

        completion = self.siliconflow_client.chat.completions.create(
            model=self.SILICONFLOW_MODEL,
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
        Main entry point with Waterfall Fallback logic.

        - Paid Mode: Uses OpenRouter directly
        - Free Mode: Waterfall through Gemini -> Groq -> SiliconFlow -> OpenRouter (emergency)

        Returns: Raw response string (JSON or Markdown depending on prompt)
        """
        # 1. Paid Mode Check
        if self.mode == "paid":
            print("   [LLMClient] Using paid mode (OpenRouter)")
            return self._call_openrouter(system_prompt, user_prompt)

        # 2. Free Mode Waterfall (Failover)
        errors = []

        # Priority 1: Gemini (Best Limits - 15 RPM)
        if self.gemini_model:
            try:
                result = self._call_gemini(system_prompt, user_prompt)
                if result:
                    print("   [LLMClient] Gemini Flash success")
                    return result
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"   [LLMClient] Gemini failed: {error_msg}...")
                errors.append(f"Gemini: {error_msg}")

        # Priority 2: Groq (Fastest Inference)
        if self.groq_client:
            try:
                result = self._call_groq(system_prompt, user_prompt)
                if result:
                    print("   [LLMClient] Groq success")
                    return result
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"   [LLMClient] Groq failed: {error_msg}...")
                errors.append(f"Groq: {error_msg}")

        # Priority 3: SiliconFlow (Reliable Backup)
        if self.siliconflow_client:
            try:
                result = self._call_siliconflow(system_prompt, user_prompt)
                if result:
                    print("   [LLMClient] SiliconFlow success")
                    return result
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"   [LLMClient] SiliconFlow failed: {error_msg}...")
                errors.append(f"SiliconFlow: {error_msg}")

        # Emergency Fallback: OpenRouter (if available)
        if self.openrouter_client:
            try:
                print("   [LLMClient] Trying OpenRouter as emergency fallback...")
                result = self._call_openrouter(system_prompt, user_prompt)
                if result:
                    print("   [LLMClient] OpenRouter emergency fallback success")
                    return result
            except Exception as e:
                error_msg = str(e)[:100]
                print(f"   [LLMClient] OpenRouter failed: {error_msg}")
                errors.append(f"OpenRouter: {error_msg}")

        # All providers failed
        print(f"   [LLMClient] All providers failed. Errors: {errors}")
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
    Strategy: Use waterfall fallback for reliable analysis.
    """
    client = get_llm_client()

    # Check if any provider is available
    if not any([client.gemini_model, client.groq_client,
                client.siliconflow_client, client.openrouter_client]):
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

    system_prompt = "You are a professional Sports Arbitrage Analyst. Analyze the divergence between Bookmaker Odds (Smart Money) and Polymarket Price (Retail Sentiment). Focus on WHY the gap exists. Output strictly clean Markdown."
    user_prompt = f"Analyze arbitrage for: {title}. Web2 Odds: {web2_odds:.1f}%. Polymarket Price: {poly_price:.1f}%. Net EV: +{ev_percent:.1f}%. Provide: 1. The Divergence Cause 2. Risk Assessment 3. Verdict. Keep it concise (under 150 words)."

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
