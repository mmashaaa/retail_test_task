"""Gemini client over the REST API.

We use REST (not the gRPC-based google-generativeai SDK) because gRPC name
resolution fails in some network environments. REST is reliable everywhere
curl works and gives us full control over retry/backoff.
"""
import json
import time
import requests

from . import config
from .observability import observe, update_observation

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class LLMError(Exception):
    pass


class GeminiClient:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.GOOGLE_API_KEY
        self.model = model or config.GEMINI_MODEL

    def _post(self, url: str, body: dict, max_attempts: int = 5) -> dict:
        """POST with exponential backoff on transient errors (429/5xx)."""
        last = None
        for attempt in range(max_attempts):
            try:
                r = requests.post(
                    url,
                    headers={"x-goog-api-key": self.api_key,
                             "Content-Type": "application/json"},
                    json=body,
                    timeout=60,
                )
            except requests.RequestException as e:
                last = e
                time.sleep(2 ** attempt)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                last = LLMError(f"{r.status_code}: {r.text[:200]}")
                time.sleep(2 ** attempt)
                continue
            if not r.ok:
                raise LLMError(f"{r.status_code}: {r.text[:300]}")
            return r.json()
        raise LLMError(f"Gemini unavailable after {max_attempts} attempts: {last}")

    @observe(as_type="generation")
    def generate(self, prompt: str, system: str = None,
                 temperature: float = 0.2, json_mode: bool = False) -> str:
        """Single-turn generation. Returns the model's text."""
        url = f"{_BASE}/{self.model}:generateContent"
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"

        data = self._post(url, body)
        # Record model + token usage on the Langfuse generation span (no-op
        # if Langfuse is disabled).
        usage = data.get("usageMetadata", {})
        update_observation(
            model=self.model,
            usage={
                "input": usage.get("promptTokenCount"),
                "output": usage.get("candidatesTokenCount"),
                "total": usage.get("totalTokenCount"),
            },
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected Gemini response: {json.dumps(data)[:300]}") from e

    def generate_json(self, prompt: str, system: str = None,
                      temperature: float = 0.0) -> dict:
        """Generation constrained to JSON output, parsed into a dict."""
        raw = self.generate(prompt, system=system, temperature=temperature,
                             json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Strip markdown fences if the model wrapped the JSON.
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            return json.loads(cleaned)
