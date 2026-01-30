"""Verification script for Google Vertex AI integration."""
import os
import sys

# Project root is one level up from scripts/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Step 1: Environment Check
print("=" * 50)
print("Step 1: Environment Check")
print("=" * 50)

# Check credentials file
creds_path = os.path.join(PROJECT_ROOT, "google-credentials.json")
if os.path.exists(creds_path):
    print(f"  [OK] google-credentials.json found at {creds_path}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
else:
    print(f"  [WARN] google-credentials.json not found at {creds_path}")
    print("         Will rely on existing GOOGLE_APPLICATION_CREDENTIALS or ADC")

# Check library
try:
    import google.cloud.aiplatform
    print(f"  [OK] google-cloud-aiplatform installed (v{google.cloud.aiplatform.__version__})")
except ImportError:
    print("  [FAIL] google-cloud-aiplatform not installed")
    sys.exit(1)

# Step 2: Integration Test
print()
print("=" * 50)
print("Step 2: Integration Test")
print("=" * 50)

try:
    sys.path.insert(0, PROJECT_ROOT)
    from scraper.ai_analyst import LLMClient

    client = LLMClient()

    print(f"  Provider configured: {client.provider}")
    print(f"  Vertex AI available: {client.vertex_available}")
    print(f"  OpenRouter available: {bool(client.openrouter_client)}")
    print(f"  is_available(): {client.is_available()}")

    # Send test prompt
    print()
    print("  Sending test prompt to LLM...")
    result = client.generate_analysis(
        system_prompt="You are a helpful assistant. Reply in one sentence only.",
        user_prompt="Explain the concept of Sports Arbitrage in one short sentence."
    )

    # Step 3: Output
    print()
    print("=" * 50)
    print("Step 3: Result")
    print("=" * 50)

    if result:
        print(f"  SUCCESS: Google Vertex AI responded: {result}")
    else:
        print("  FAILED: No response received from any provider")

except Exception as e:
    print()
    print("=" * 50)
    print("Step 3: Result")
    print("=" * 50)
    print(f"  FAILED: {e}")
