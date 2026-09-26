"""External AI chat-completion providers.

The rest of the system talks to `chat()` in this module, never to a vendor
SDK. Each provider here returns a plain string from a prompt/messages list.

Supported providers (from AI_PROVIDER env var):
  - "openai":   OpenAI-compatible /v1/chat/completions endpoint
                (works with OpenAI, Groq, OpenRouter, Ollama, LM Studio...)
  - "gemini":   Google AI Studio REST API (generativelanguage.googleapis.com)

If no provider/key is configured, `chat()` raises ProviderUnavailable; callers
may catch it and fall back to deterministic offline logic.
"""

import json

import httpx

from django.conf import settings

from .errors import AiParseError, ProviderUnavailable


def _post(url, **kwargs):
    """POST to the provider, converting transport/credential failures into a
    typed error so no HTTP detail, key or traceback reaches feature code."""
    try:
        resp = httpx.post(url, **kwargs)
        resp.raise_for_status()
        return resp
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status in (401, 403):
            raise ProviderUnavailable("AI provider rejected the configured API key")
        if status == 429:
            raise ProviderUnavailable("AI provider rate limit reached; try again shortly")
        raise ProviderUnavailable(f"AI provider returned HTTP {status}")
    except httpx.HTTPError as exc:
        raise ProviderUnavailable(f"AI provider unreachable ({exc.__class__.__name__})")



class _Client:
    """Reads provider configuration from settings on every instantiation.

    Configuration is resolved lazily (per call) rather than at import time so a
    changed environment or an overridden setting is always honoured, and so the
    key never lives longer than a single request.
    """

    def __init__(self):
        self.provider = (settings.AI_PROVIDER or "").lower()
        self.key = settings.AI_API_KEY
        self.base_url = (settings.AI_BASE_URL or "").rstrip("/")
        self.model = settings.AI_MODEL

    def chat(self, messages, *, json_mode=False, temperature=0.4, timeout=60.0):
        if not self.provider or not self.key:
            raise ProviderUnavailable("AI_PROVIDER / AI_API_KEY not configured")
        if self.provider == "openai":
            return self._openai_chat(messages, json_mode=json_mode, temperature=temperature, timeout=timeout)
        if self.provider == "gemini":
            return self._gemini_chat(messages, json_mode=json_mode, temperature=temperature, timeout=timeout)
        raise ProviderUnavailable(f"Unsupported AI_PROVIDER: {self.provider}")


    # ------------------------------------------------------------------
    def _openai_chat(self, messages, *, json_mode, temperature, timeout):
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.key}"}
        resp = _post(url, json=payload, headers=headers, timeout=timeout)
        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderUnavailable("AI provider returned an unexpected response shape")

    def _gemini_chat(self, messages, *, json_mode, temperature, timeout):
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}"
            f":generateContent?key={self.key}"
        )
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        resp = _post(url, json={"contents": contents,
                                "generationConfig": {"temperature": temperature}},
                     timeout=timeout)
        try:
            body = resp.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderUnavailable("Gemini returned no content")
        # Strip markdown code fences that Gemini sometimes wraps JSON in.
        if text.strip().startswith("```"):
            text = text.strip().removeprefix("```json").removeprefix("```JAVA").strip("`")
        return text


def _client():
    """Build a client from the current settings (never cached)."""
    return _Client()


def chat(messages, **kwargs):
    return _client().chat(messages, **kwargs)


def chat_json(messages, *, temperature=0.4, timeout=60.0):
    """Run a chat completion and parse the response as JSON."""
    raw = _client().chat(messages, json_mode=True, temperature=temperature, timeout=timeout)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise AiParseError(f"AI returned invalid JSON: {raw[:200]}")


def is_configured():
    client = _client()
    return bool(client.provider and client.key)


def provider_name():
    return _client().provider or "offline"
