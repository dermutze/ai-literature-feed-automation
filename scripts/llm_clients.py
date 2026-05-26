from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
DEFAULT_OPENAI_COMPATIBLE_BASE_URL = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "")
DEFAULT_OPENAI_COMPATIBLE_MODEL = os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4o-mini")


class LLMError(RuntimeError):
    """Raised when an LLM provider call fails."""


def call_ollama(
    prompt: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 180,
) -> str:
    """Call a local Ollama text-generation endpoint.

    This keeps the Streamlit app fully local when Ollama is installed, but the
    same function can also be used by the CLI/API if desired.
    """
    try:
        response = requests.post(
            url,
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", "")).strip()
    except Exception as exc:  # pragma: no cover - network dependent
        raise LLMError(f"Ollama request failed: {exc}") from exc


def call_openai_compatible(
    prompt: str,
    base_url: str,
    api_key: str,
    model: str = DEFAULT_OPENAI_COMPATIBLE_MODEL,
    system_prompt: str = "You are a concise scientific literature assistant.",
    timeout: int = 180,
) -> str:
    """Call an OpenAI-compatible chat-completions endpoint using requests.

    The app does not require the openai Python package. Any provider exposing a
    /v1/chat/completions-compatible route can be used by setting base_url and key.
    """
    if not base_url:
        raise LLMError("Missing OpenAI-compatible base URL.")
    if not api_key:
        raise LLMError("Missing API key.")

    base_url = base_url.rstrip("/")
    url = f"{base_url}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except Exception as exc:  # pragma: no cover - network dependent
        raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc


def call_llm(
    provider: str,
    prompt: str,
    *,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
    api_base_url: str = DEFAULT_OPENAI_COMPATIBLE_BASE_URL,
    api_key: str = "",
    api_model: str = DEFAULT_OPENAI_COMPATIBLE_MODEL,
    timeout: int = 180,
) -> str:
    """Provider router used by the Streamlit dashboard."""
    provider_norm = provider.lower().strip()
    if provider_norm == "ollama/local":
        return call_ollama(prompt, model=ollama_model, url=ollama_url, timeout=timeout)
    if provider_norm == "openai-compatible api":
        return call_openai_compatible(
            prompt,
            base_url=api_base_url,
            api_key=api_key,
            model=api_model,
            timeout=timeout,
        )
    raise LLMError(f"Unsupported LLM provider: {provider}")
