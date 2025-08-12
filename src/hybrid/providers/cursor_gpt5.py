import os, time, requests
from typing import List, Dict, Any

class CursorGpt5Provider:
    def __init__(self,
                 base_url: str,
                 api_key: str,
                 model: str,
                 timeout_s: int = 45,
                 max_output_tokens: int = 1200):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.max_output_tokens = max_output_tokens

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"   # OpenAI-compatible
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_output_tokens,
        }

        last_err = "unknown"
        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    return {"ok": True, "text": text, "usage": usage}
                if resp.status_code in (429, 500, 502, 503, 504):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {"ok": False, "status": resp.status_code, "err": resp.text}
            except requests.RequestException as e:
                last_err = str(e)
                time.sleep(1.5 * (attempt + 1))
        return {"ok": False, "status": 599, "err": last_err}
