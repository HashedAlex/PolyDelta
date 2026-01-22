import os
import time
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ---------------- CONFIGURATION ---------------- #
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
YOUR_SITE_URL = "https://polydelta.vercel.app"
APP_NAME = "PolyDelta Arbitrage"

# 策略：优先使用稳定的免费模型
# 参考: https://openrouter.ai/docs/models
PRIMARY_MODEL = "google/gemini-2.0-flash-exp:free"  # Gemini Flash 作为主要模型
FALLBACK_MODEL = "meta-llama/llama-3.2-3b-instruct:free"  # Llama 3.2 作为备用

# 使用 httpx 设置超时
client = None
if OPENROUTER_API_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        timeout=httpx.Timeout(60.0, connect=10.0)
    )

def generate_ai_report(match_data, is_championship=False):
    """
    生成 AI 分析报告。
    策略：优先尝试 DeepSeek R1 进行深度推理；如果超时或报错，切换 Gemini Flash 进行快速总结。
    """
    if not client:
        print("   ⚠️ OPENROUTER_API_KEY 未设置，跳过 AI 分析")
        return None

    ev = float(match_data.get('ev', 0))
    threshold = 0.05 if is_championship else 0.02

    # 门槛过滤：只有高价值机会才分析
    if ev < threshold:
        return None

    title = match_data.get('title', 'Unknown Match')
    web2_odds = match_data.get('web2_odds', 0)
    poly_price = match_data.get('polymarket_price', 0)
    ev_percent = ev * 100

    print(f"🧠 AI Analyst observing: {title} (EV: +{ev_percent:.1f}%)")

    r1_system_prompt = "You are a professional Sports Arbitrage Analyst. Analyze the divergence between Bookmaker Odds (Smart Money) and Polymarket Price (Retail Sentiment). Focus on WHY the gap exists. Output strictly clean Markdown."
    user_content = f"Analyze arbitrage for: {title}. Web2 Odds: {web2_odds:.1f}%. Polymarket Price: {poly_price:.1f}%. Net EV: +{ev_percent:.1f}%. Provide: 1. The Divergence Cause 2. Risk Assessment 3. Verdict. Keep it concise (under 150 words)."

    # 尝试主要模型 (Gemini Flash)
    try:
        time.sleep(1)  # 避免速率限制
        result = call_llm(PRIMARY_MODEL, r1_system_prompt, user_content)
        if result:
            print(f"   ✅ Gemini Flash 报告生成成功")
            return result
    except Exception as e:
        print(f"   ⚠️ Primary model error: {str(e)[:60]}...")

    # Fallback: Llama 3.2
    print(f"   🔄 Switching to Fallback (Llama 3.2)...")
    try:
        time.sleep(1)  # 避免速率限制
        fallback_system_prompt = "You are a fast Trading Assistant. Give a quick TL;DR arbitrage analysis. Be direct and factual. Keep it under 100 words."
        result = call_llm(FALLBACK_MODEL, fallback_system_prompt, user_content)
        if result:
            print(f"   ✅ Llama 3.2 报告生成成功")
            return result
    except Exception as e:
        print(f"   ❌ Fallback model error: {str(e)[:60]}...")

    return None

def call_llm(model, sys_prompt, user_prompt):
    """调用 LLM API"""
    completion = client.chat.completions.create(
        extra_headers={"HTTP-Referer": YOUR_SITE_URL, "X-Title": APP_NAME},
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=500,
    )
    content = completion.choices[0].message.content

    # 清洗 DeepSeek 的思维链
    if content and "<think>" in content:
        parts = content.split("</think>")
        if len(parts) > 1:
            content = parts[-1].strip()

    return content.replace("```markdown", "").replace("```", "").strip() if content else None
