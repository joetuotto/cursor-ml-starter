import os, time, json, math, re
from typing import Optional, Dict, Any, Tuple
import requests

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
    def _count_tokens(text: str) -> int:
        return len(_ENC.encode(text or ""))
except Exception:
    def _count_tokens(text: str) -> int:
        # karkea arvio fallback: 1 token ~ 4 merkkiä
        return max(1, math.ceil(len((text or "")) / 4))

try:
    from jsonschema import validate as json_validate, ValidationError as JSONSchemaError
except Exception:
    JSONSchemaError = Exception
    def json_validate(instance, schema): 
        return True

JSON_BLOCK = re.compile(r"```json(.*?)```", re.S | re.M)

def _extract_json(text: str) -> str:
    m = JSON_BLOCK.search(text or "")
    return (m.group(1) if m else text or "").strip()

def _to_valid_json(text: str) -> Dict[str, Any]:
    s = _extract_json(text)
    # yritä suoraan
    try:
        return json.loads(s)
    except Exception:
        # yritä siivota trailing-kommaa yms.
        s = re.sub(r",\s*([}\]])", r"\1", s)
        return json.loads(s)

class LLMResponse:
    def __init__(self, content: str, prompt_tokens: int, completion_tokens: int, cost_eur: float, model: str):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.cost_eur = cost_eur
        self.model = model

class BaseClient:
    def __init__(self, name: str, price_in_eur_per_1k_in: float, price_out_eur_per_1k: float):
        self.name = name
        self._pin = price_in_eur_per_1k_in
        self._pout = price_out_eur_per_1k

    def _estimate_cost(self, in_toks: int, out_toks: int) -> float:
        return (in_toks/1000.0)*self._pin + (out_toks/1000.0)*self._pout

    def generate_json(
        self,
        sys_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        temperature: float = 0.3,
        max_output_tokens: int = 800,
        retries: int = 2,
        timeout_s: int = 45,
    ) -> Tuple[Dict[str, Any], LLMResponse]:
        raise NotImplementedError

class DeepSeekClient(BaseClient):
    """
    DeepSeek API (OpenAI-yhteensopiva chat.completions)
    Env:
      DEEPSEEK_API_KEY
      DEEPSEEK_BASE (oletus https://api.deepseek.com)
      DEEPSEEK_MODEL (oletus deepseek-chat)
    Hinnat (päivitä tarvittaessa): in=€0.12/1k, out=€0.24/1k (esimerkit)
    """
    def __init__(self):
        base_in = float(os.getenv("DEEPSEEK_EUR_PER_1K_IN", "0.12"))
        base_out = float(os.getenv("DEEPSEEK_EUR_PER_1K_OUT", "0.24"))
        super().__init__("deepseek", base_in, base_out)
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base = os.getenv("DEEPSEEK_BASE", "https://api.deepseek.com")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY puuttuu")

    def generate_json(self, sys_prompt, user_prompt, schema, temperature=0.3, max_output_tokens=800, retries=2, timeout_s=45):
        url = f"{self.base}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        instruction = (
            "Return ONLY valid JSON matching this schema. Do not add commentary.\n"
            "If a field is unknown, set a safe default.\n\nSCHEMA:\n"
            f"{json.dumps(schema)}"
        )

        in_tokens = _count_tokens(sys_prompt) + _count_tokens(user_prompt) + _count_tokens(instruction)
        last_err = None
        for attempt in range(retries+1):
            payload = {
                "model": self.model,
                "temperature": temperature,
                "max_tokens": max_output_tokens,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                    {"role": "user", "content": instruction},
                ],
            }
            try:
                t0 = time.time()
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
                resp.raise_for_status()
                data = resp.json()
                txt = data["choices"][0]["message"]["content"]
                out_tokens = data.get("usage", {}).get("completion_tokens", _count_tokens(txt))
                cost = self._estimate_cost(in_tokens, out_tokens)
                parsed = _to_valid_json(txt)
                json_validate(parsed, schema)  # no-op if jsonschema not installed
                return parsed, LLMResponse(txt, in_tokens, out_tokens, cost, self.model)
            except (requests.RequestException, JSONSchemaError, ValueError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.8*(attempt+1))
                    continue
                raise last_err

class GPT5Client(BaseClient):
    """
    GPT-5 Thinking via OpenAI-compatible endpoint (esim. Cursor Gateway)
    Env:
      CURSOR_API_KEY
      CURSOR_BASE (oletus https://api.openai.com) → vaihda omaan gatewayhin
      GPT5_MODEL (oletus gpt-5-thinking)
    Hinnat (päivitä): in=€2.50/1k, out=€10.00/1k (esimerkit)
    """
    def __init__(self):
        base_in = float(os.getenv("GPT5_EUR_PER_1K_IN", "2.5"))
        base_out = float(os.getenv("GPT5_EUR_PER_1K_OUT", "10.0"))
        super().__init__("gpt5", base_in, base_out)
        self.api_key = os.getenv("CURSOR_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.base = os.getenv("CURSOR_BASE", "https://api.openai.com")
        self.model = os.getenv("GPT5_MODEL", "gpt-5-thinking")
        if not self.api_key:
            raise RuntimeError("CURSOR_API_KEY tai OPENAI_API_KEY puuttuu")

    def generate_json(self, sys_prompt, user_prompt, schema, temperature=0.25, max_output_tokens=900, retries=2, timeout_s=60):
        url = f"{self.base}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        instruction = (
            "Return ONLY valid JSON matching this schema. No prose, no markdown.\n"
            "If a field is uncertain, provide a short neutral value.\n\nSCHEMA:\n"
            f"{json.dumps(schema)}"
        )

        in_tokens = _count_tokens(sys_prompt) + _count_tokens(user_prompt) + _count_tokens(instruction)
        last_err = None
        for attempt in range(retries+1):
            payload = {
                "model": self.model,
                "temperature": temperature,
                "max_tokens": max_output_tokens,
                "response_format": {"type": "json_object"},  # jos tuettu; muuten ignor.
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt},
                    {"role": "user", "content": instruction},
                ],
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
                resp.raise_for_status()
                data = resp.json()
                txt = data["choices"][0]["message"]["content"]
                out_tokens = data.get("usage", {}).get("completion_tokens", _count_tokens(txt))
                cost = self._estimate_cost(in_tokens, out_tokens)
                parsed = _to_valid_json(txt)
                json_validate(parsed, schema)
                return parsed, LLMResponse(txt, in_tokens, out_tokens, cost, self.model)
            except (requests.RequestException, JSONSchemaError, ValueError) as e:
                last_err = e
                if attempt < retries:
                    time.sleep(0.8*(attempt+1))
                    continue
                raise last_err
