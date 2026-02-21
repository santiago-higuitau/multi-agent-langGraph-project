"""
AI Dev Team - LLM Service

Each agent specifies its model as "provider/model-id", e.g.:
  - "anthropic/claude-sonnet-4-6"
  - "openai/gpt-4o"
  - "groq/llama-3.3-70b-versatile"
  - "gemini/gemini-1.5-pro"

API keys are read from env vars per provider:
  ANTHROPIC_API_KEY, OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, etc.

Per-agent model is set via MODEL_<AGENT> env vars.
Falls back to DEFAULT_MODEL if not set.
"""

import os
import json
import re
from typing import Optional

# Default model used if a per-agent override is not set
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "anthropic/claude-sonnet-4-6")

# Per-agent model overrides — format: "provider/model-id"
AGENT_MODELS = {
    "ba_agent":              os.getenv("MODEL_BA",          DEFAULT_MODEL),
    "po_agent":              os.getenv("MODEL_PO",          DEFAULT_MODEL),
    "architect_agent":       os.getenv("MODEL_ARCHITECT",   DEFAULT_MODEL),
    "backend_builder":       os.getenv("MODEL_BACKEND",     DEFAULT_MODEL),
    "frontend_builder":      os.getenv("MODEL_FRONTEND",    DEFAULT_MODEL),
    "qa_agent":              os.getenv("MODEL_QA",          DEFAULT_MODEL),
    "integration_validator": os.getenv("MODEL_VALIDATOR",   DEFAULT_MODEL),
    "devops_agent":          os.getenv("MODEL_DEVOPS",      DEFAULT_MODEL),
    "planning_evaluator":    os.getenv("MODEL_EVALUATOR",   DEFAULT_MODEL),
}

# API key env var per provider
PROVIDER_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "groq":      "GROQ_API_KEY",
    "gemini":    "GEMINI_API_KEY",
    "kimi":      "KIMI_API_KEY",
    "mistral":   "MISTRAL_API_KEY",
}

# OpenAI-compatible base URLs for non-OpenAI providers
OPENAI_COMPAT_BASE_URLS = {
    "groq":    "https://api.groq.com/openai/v1",
    "kimi":    "https://api.moonshot.cn/v1",
    "mistral": "https://api.mistral.ai/v1",
}

# Providers that support JSON mode in OpenAI-compat API
JSON_MODE_PROVIDERS = {"openai", "groq"}


def _parse_model_string(model_str: str) -> tuple[str, str]:
    """
    Parse "provider/model-id" into (provider, model_id).
    If no slash, assumes 'anthropic' as provider.
    """
    if "/" in model_str:
        provider, model_id = model_str.split("/", 1)
        return provider.lower().strip(), model_id.strip()
    return "anthropic", model_str.strip()


def _get_api_key(provider: str) -> str:
    key_env = PROVIDER_API_KEY_ENV.get(provider, f"{provider.upper()}_API_KEY")
    key = os.getenv(key_env, "")
    if not key:
        raise ValueError(f"Missing API key: set {key_env} in your .env file")
    return key


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 50_000,
    response_format: Optional[str] = "json",
    agent: Optional[str] = None,
) -> dict:
    """
    Call the LLM for the given agent.
    Model is resolved from MODEL_<AGENT> env var or DEFAULT_MODEL.
    """
    model_str = AGENT_MODELS.get(agent, DEFAULT_MODEL) if agent else DEFAULT_MODEL
    provider, model_id = _parse_model_string(model_str)

    print(f"  🤖 [{agent or 'default'}] {provider}/{model_id}")

    try:
        if provider == "anthropic":
            return await _call_anthropic(system_prompt, user_prompt, temperature, max_tokens, response_format, model_id)
        elif provider == "gemini":
            return await _call_gemini(system_prompt, user_prompt, temperature, max_tokens, response_format, model_id)
        else:
            # OpenAI-compatible: openai, groq, kimi, mistral, etc.
            return await _call_openai_compat(provider, model_id, system_prompt, user_prompt, temperature, max_tokens, response_format)
    except Exception as e:
        print(f"  ❌ LLM call failed [{provider}/{model_id}]: {type(e).__name__}: {e}")
        return {"error": str(e), "raw_text": ""}


async def _call_anthropic(system_prompt, user_prompt, temperature, max_tokens, response_format, model_id):
    from anthropic import AsyncAnthropic
    api_key = _get_api_key("anthropic")
    client = AsyncAnthropic(api_key=api_key, timeout=2000.0)
    message = await client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = "".join(block.text for block in message.content if block.type == "text")
    return _parse_json_response(raw_text) if response_format == "json" else {"text": raw_text}


async def _call_openai_compat(provider, model_id, system_prompt, user_prompt, temperature, max_tokens, response_format):
    from openai import AsyncOpenAI
    api_key = _get_api_key(provider)
    base_url = OPENAI_COMPAT_BASE_URLS.get(provider)
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)
    kwargs = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if response_format == "json" and provider in JSON_MODE_PROVIDERS:
        kwargs["response_format"] = {"type": "json_object"}
    response = await client.chat.completions.create(**kwargs)
    raw_text = response.choices[0].message.content
    return _parse_json_response(raw_text) if response_format == "json" else {"text": raw_text}


async def _call_gemini(system_prompt, user_prompt, temperature, max_tokens, response_format, model_id):
    """Google Gemini via google-generativeai SDK."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("Install google-generativeai: pip install google-generativeai")
    api_key = _get_api_key("gemini")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=model_id,
        system_instruction=system_prompt,
    )
    response = await model.generate_content_async(
        user_prompt,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )
    raw_text = response.text
    return _parse_json_response(raw_text) if response_format == "json" else {"text": raw_text}


def _parse_json_response(raw_text: str) -> dict:
    """
    Parse JSON from LLM response, handling markdown code blocks and edge cases.
    Always returns a dict.
    """
    text = raw_text.strip()
    text = re.sub(r'^`{3,}(?:json|JSON)?\s*', '', text)
    text = re.sub(r'\s*`{3,}\s*$', '', text)
    text = text.strip()

    def _ensure_dict(val):
        if isinstance(val, dict): return val
        if isinstance(val, list):
            return val[0] if val and isinstance(val[0], dict) else {"items": val}
        return {"value": val}

    # Attempt 1: direct parse
    try:
        return _ensure_dict(json.loads(text))
    except json.JSONDecodeError:
        pass

    # Attempt 2: outermost object
    start, end = text.find("{"), text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return _ensure_dict(json.loads(text[start:end]))
        except json.JSONDecodeError:
            pass

    # Attempt 3: array
    start, end = text.find("["), text.rfind("]") + 1
    if start != -1 and end > start:
        try:
            return _ensure_dict(json.loads(text[start:end]))
        except json.JSONDecodeError:
            pass

    # Attempt 4: fix trailing commas
    try:
        cleaned = re.sub(r',\s*([}\]])', r'\1', text)
        return _ensure_dict(json.loads(cleaned))
    except Exception:
        pass

    # Attempt 5: repair truncated JSON
    try:
        start = text.find("{")
        if start != -1:
            fragment = text[start:]
            open_braces = fragment.count("{") - fragment.count("}")
            open_brackets = fragment.count("[") - fragment.count("]")
            fragment = re.sub(r',\s*"[^"]*"?\s*:?\s*(?:"[^"]*)?$', '', fragment)
            fragment = re.sub(r',\s*$', '', fragment)
            fragment += "]" * open_brackets + "}" * open_braces
            cleaned = re.sub(r',\s*([}\]])', r'\1', fragment)
            return _ensure_dict(json.loads(cleaned))
    except Exception:
        pass

    print(f"  ⚠️  Failed to parse JSON. First 300 chars: {raw_text[:300]}")
    return {"error": "Failed to parse JSON", "raw_text": raw_text}
