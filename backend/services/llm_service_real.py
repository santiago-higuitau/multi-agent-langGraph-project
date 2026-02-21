"""
AI Dev Team - LLM Service

Abstraction layer for LLM calls.
Supports: Anthropic Claude, OpenAI, Groq, Kimi (Moonshot).
"""

import os
import json
from typing import Optional

# Provider to use
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


# Provider configs: base_url, api_key_env, supports_json_mode
PROVIDER_CONFIGS = {
    "anthropic": {
        "type": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
    },
    "openai": {
        "type": "openai_compat",
        "base_url": None,  # default OpenAI
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
        "supports_json_mode": True,
    },
    "groq": {
        "type": "openai_compat",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "supports_json_mode": True,
    },
    "kimi": {
        "type": "openai_compat",
        "base_url": "https://api.moonshot.cn/v1",
        "api_key_env": "KIMI_API_KEY",
        "default_model": "moonshot-v1-8k",
        "supports_json_mode": False,
    },
}


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 50_000,
    response_format: Optional[str] = "json",
) -> dict:
    """
    Call the configured LLM and return parsed JSON response.
    """
    provider = LLM_PROVIDER.lower()
    config = PROVIDER_CONFIGS.get(provider)

    if not config:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. "
            f"Supported: {list(PROVIDER_CONFIGS.keys())}"
        )
    
    print(f"  🤖 Calling {provider} ({LLM_MODEL})...")
    
    try:
        if config["type"] == "anthropic":
            return await _call_anthropic(
                system_prompt, user_prompt, temperature, max_tokens, response_format
            )
        else:  # openai_compat (OpenAI, Groq, Kimi, etc.)
            return await _call_openai_compat(
                config, system_prompt, user_prompt, temperature, max_tokens, response_format
            )
    except Exception as e:
        print(f"  ❌ LLM call failed: {type(e).__name__}: {e}")
        return {"error": str(e), "raw_text": ""}


async def _call_anthropic(
    system_prompt: str, 
    user_prompt: str, 
    temperature: float, 
    max_tokens: int,
    response_format: Optional[str],
) -> dict:
    """Call Anthropic Claude API."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(timeout=2000.0)

    message = await client.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(
        block.text for block in message.content if block.type == "text"
    )
    
    if response_format == "json":
        return _parse_json_response(raw_text)
    return {"text": raw_text}


async def _call_openai_compat(
    config: dict,
    system_prompt: str, 
    user_prompt: str, 
    temperature: float, 
    max_tokens: int,
    response_format: Optional[str],
) -> dict:
    """
    Call any OpenAI-compatible API (OpenAI, Groq, Kimi, etc.)
    """
    from openai import AsyncOpenAI
    
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise ValueError(f"Missing env var: {config['api_key_env']}")
    
    client_kwargs = {"api_key": api_key}
    if config.get("base_url"):
        client_kwargs["base_url"] = config["base_url"]
    
    client = AsyncOpenAI(**client_kwargs)
    
    kwargs = {
        "model": LLM_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    
    # Add JSON mode if provider supports it
    if response_format == "json" and config.get("supports_json_mode", False):
        kwargs["response_format"] = {"type": "json_object"}
    
    response = await client.chat.completions.create(**kwargs)
    raw_text = response.choices[0].message.content
    
    if response_format == "json":
        return _parse_json_response(raw_text)
    return {"text": raw_text}


def _parse_json_response(raw_text: str) -> dict:
    """
    Parse JSON from LLM response, handling markdown code blocks and edge cases.
    ALWAYS returns a dict. If parsed result is a list, wraps it.
    """
    text = raw_text.strip()

    # Remove markdown code blocks — handle all variations:
    # ```json\n{...}\n```, ```json{...}```, ```\n{...}\n```, etc.
    import re
    # First strip leading/trailing whitespace
    text = text.strip()
    # Remove opening fence: ```json or ``` at the start (with optional whitespace/newlines after)
    text = re.sub(r'^`{3,}(?:json|JSON)?\s*', '', text)
    # Remove closing fence: ``` at the end (with optional whitespace/newlines before)
    text = re.sub(r'\s*`{3,}\s*$', '', text)
    text = text.strip()
    
    def _ensure_dict(val):
        """Ensure the parsed value is a dict."""
        if isinstance(val, dict):
            return val
        if isinstance(val, list):
            if val and isinstance(val[0], dict):
                return val[0]
            return {"items": val}
        return {"value": val}
    
    # Attempt 1: Direct parse
    try:
        return _ensure_dict(json.loads(text))
    except json.JSONDecodeError:
        pass
    
    # Attempt 2: Find outermost JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return _ensure_dict(json.loads(text[start:end]))
        except json.JSONDecodeError:
            pass
    
    # Attempt 3: Find JSON array
    start = text.find("[")
    end = text.rfind("]") + 1
    if start != -1 and end > start:
        try:
            return _ensure_dict(json.loads(text[start:end]))
        except json.JSONDecodeError:
            pass
    
    # Attempt 4: Fix trailing commas
    try:
        cleaned = re.sub(r',\s*([}\]])', r'\1', text)
        return _ensure_dict(json.loads(cleaned))
    except (json.JSONDecodeError, Exception):
        pass
    
    # Attempt 5: Truncated JSON — try to close open braces/brackets
    try:
        # Find the outermost { and try to repair
        start = text.find("{")
        if start != -1:
            fragment = text[start:]
            # Count open vs close braces
            open_braces = fragment.count("{") - fragment.count("}")
            open_brackets = fragment.count("[") - fragment.count("]")
            # Remove any trailing partial key/value (after last comma or colon)
            fragment = re.sub(r',\s*"[^"]*"?\s*:?\s*(?:"[^"]*)?$', '', fragment)
            fragment = re.sub(r',\s*$', '', fragment)
            # Close open structures
            fragment += "]" * open_brackets + "}" * open_braces
            cleaned = re.sub(r',\s*([}\]])', r'\1', fragment)
            return _ensure_dict(json.loads(cleaned))
    except (json.JSONDecodeError, Exception):
        pass
    
    print(f"  ⚠️  Failed to parse JSON from LLM response")
    print(f"     First 300 chars: {raw_text[:300]}")
    return {"error": "Failed to parse JSON", "raw_text": raw_text}
