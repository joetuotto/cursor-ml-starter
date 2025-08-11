import os, json, sys
from pathlib import Path

sys.path.append(".")

from src.hybrid.llm_clients import DeepSeekClient, GPT5Client

SCHEMA = {
  "type": "object",
  "required": ["kicker","headline","lede","why_it_matters","refs","confidence","tags","timestamp"],
  "properties": {
    "kicker": {"type":"string"},
    "headline": {"type":"string"},
    "lede": {"type":"string"},
    "why_it_matters": {"type":"string"},
    "refs": {"type":"array","items":{"type":"string"}},
    "confidence": {"type":"number","minimum":0,"maximum":1},
    "tags": {"type":"array","items":{"type":"string"}},
    "timestamp": {"type":"string"}
  }
}

SYS = (
"You're an investigative news analyst. Produce concise, specific, **verifiable** cards. "
"Never invent sources; include 2–5 real references (urls). Output JSON ONLY."
)

def build_user_prompt(example: str) -> str:
    return (
        "SOURCE:\n"
        f"{example}\n\n"
        "Task: extract concrete entities (who/what/where/when), quantify anything you can, "
        "and generate a newswire card for expert readers."
    )

def main():
    sample = os.getenv("NEWS_SAMPLE", "The European Central Bank signalled it may cut rates in September if inflation continues cooling, while core services remain sticky. Local unions in FI/DE announced coordinated actions next week.")
    route = os.getenv("TEST_ROUTE", "gpt5")  # gpt5|deepseek
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"

    if mock_mode:
        # Mock response for testing without API keys
        from datetime import datetime
        js = {
            "kicker": "ECB Watch",
            "headline": f"European Central Bank Signals September Rate Cut Possibility",
            "lede": "The European Central Bank indicated potential rate reductions in September if inflation trends continue cooling, though sticky core services inflation remains a concern for policymakers.",
            "why_it_matters": "Rate cuts would reduce borrowing costs across eurozone, affecting mortgages, business investment, and currency strength. Finnish banks and exporters would benefit from lower rates.",
            "refs": [
                "https://www.ecb.europa.eu/press/pr/",
                "https://www.hs.fi/talous/",
                "https://yle.fi/talous/"
            ],
            "confidence": 0.85,
            "tags": ["ECB", "monetary policy", "inflation", "interest rates"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Mock metadata
        class MockResponse:
            def __init__(self):
                self.content = json.dumps(js)
                self.prompt_tokens = 450
                self.completion_tokens = 180
                self.cost_eur = 0.025 if route == "gpt5" else 0.003
                self.model = f"{route}-mock"
        
        meta = MockResponse()
    else:
        # Real API calls
        if route == "deepseek":
            client = DeepSeekClient()
        else:
            client = GPT5Client()

        js, meta = client.generate_json(
            sys_prompt=SYS,
            user_prompt=build_user_prompt(sample),
            schema=SCHEMA,
            temperature=0.2,
            max_output_tokens=700
        )

    Path("artifacts").mkdir(exist_ok=True, parents=True)
    out = Path("artifacts/report.enriched.json")
    payload = [js]  # UI-yhteensopiva lista

    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"✅ Wrote {out}")
    print(f"Model={meta.model} cost≈€{meta.cost_eur:.4f} promptTok={meta.prompt_tokens} outTok={meta.completion_tokens}")

if __name__ == "__main__":
    main()
