"""
LLM Service — Multi-provider AI integration with smart routing and automatic fallback.

Providers (OpenAI-compatible unless noted):
  openai     : GPT-4o-mini            — paid, primary
  groq       : Llama 3.3 70B          — FREE, fastest (300+ tok/sec)
  gemini     : Gemini 2.5 Flash       — FREE, 1M context, multimodal
  openrouter : DeepSeek R1 / Llama 4  — FREE tier, 30+ models in one key
  cerebras   : Llama 3.3 70B          — FREE, 1M tok/day, ultra-fast
  deepseek   : DeepSeek V3 / R1       — 5M free tokens, then $0.14/M
  mistral    : Codestral / Large      — FREE 1B tok/month, best for code
  together   : Llama 3.3 70B / Llama 4 — optional, OpenAI-compatible
  fireworks  : Llama 3.3 70B         — optional, fast hosted inference
  huggingface: HF Inference router   — optional (HF_TOKEN / HUGGINGFACE_HUB_TOKEN)
  ollama     : Local models          — optional (OLLAMA_BASE_URL, OpenAI-compatible)
  anthropic  : Claude 3.5 Sonnet     — optional, native API
  azure      : Azure OpenAI          — optional, same client (AZURE_OPENAI_ENDPOINT + key)
  cohere     : Command R+            — optional, OpenAI-compatible compatibility API

Smart routing by task_type:
  'speed'   -> groq -> cerebras -> together -> openai
  'code'    -> mistral -> groq -> openai -> anthropic
  'reason'  -> deepseek -> openrouter -> anthropic -> openai
  'context' -> gemini -> openai -> anthropic
  'free'    -> groq -> cerebras -> gemini -> openrouter -> deepseek -> mistral -> together
  'default' -> openai -> groq -> gemini -> openrouter -> together -> anthropic

Env: LLM_PREFER_FREE=1 maps task_type "default" to the free-tier chain (same as "free").

Backward-compatible: existing calls to chat() / complete() / embed() unchanged.
"""
import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "base_url": None,
        "api_key_env": "OPENAI_API_KEY",
        "default_model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "best_model": os.environ.get("OPENAI_MODEL_BEST", "gpt-4o"),
        "embed_model": "text-embedding-3-small",
        "cost_tier": "paid",
        "label": "OpenAI",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "best_model": "llama-3.3-70b-versatile",
        "embed_model": None,
        "cost_tier": "free",
        "label": "Groq (Llama 3.3 70B)",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GOOGLE_AI_API_KEY",
        "default_model": "gemini-2.5-flash",
        "best_model": "gemini-2.5-pro",
        "embed_model": None,
        "cost_tier": "free",
        "label": "Google Gemini 2.5 Flash",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "best_model": "deepseek/deepseek-r1:free",
        "embed_model": None,
        "cost_tier": "free",
        "label": "OpenRouter (Llama 4 / DeepSeek R1)",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "default_model": "llama3.3-70b",
        "best_model": "llama3.3-70b",
        "embed_model": None,
        "cost_tier": "free",
        "label": "Cerebras (Llama 3.3 70B)",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "best_model": "deepseek-reasoner",
        "embed_model": None,
        "cost_tier": "near-free",
        "label": "DeepSeek V3 / R1",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "default_model": "mistral-small-latest",
        "best_model": "mistral-large-latest",
        "embed_model": "mistral-embed",
        "cost_tier": "free",
        "label": "Mistral (Codestral / Large)",
        "code_model": "codestral-latest",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "api_key_env": "TOGETHER_API_KEY",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "best_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "embed_model": None,
        "cost_tier": "paid",
        "label": "Together AI (Llama 3.3 70B)",
    },
    "anthropic": {
        "base_url": None,
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-3-5-sonnet-20241022",
        "best_model": "claude-3-5-sonnet-20241022",
        "embed_model": None,
        "cost_tier": "paid",
        "label": "Anthropic Claude 3.5 Sonnet",
    },
    "azure": {
        "base_url": os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip() or None,
        "api_key_env": "AZURE_OPENAI_API_KEY",
        "default_model": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        "best_model": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        "embed_model": None,
        "cost_tier": "paid",
        "label": "Azure OpenAI",
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "api_key_env": "COHERE_API_KEY",
        "default_model": "command-r-plus",
        "best_model": "command-r-plus",
        "embed_model": "embed-english-v3.0",
        "cost_tier": "paid",
        "label": "Cohere (Command R+)",
    },
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key_env": "FIREWORKS_API_KEY",
        "default_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "best_model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        "embed_model": None,
        "cost_tier": "paid",
        "label": "Fireworks AI (Llama 3.3 70B)",
    },
    "huggingface": {
        "base_url": "https://router.huggingface.co/v1",
        "api_key_env": "HF_TOKEN",
        "default_model": os.environ.get("HF_INFERENCE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct"),
        "best_model": os.environ.get("HF_INFERENCE_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct"),
        "embed_model": None,
        "cost_tier": "paid",
        "label": "Hugging Face Inference",
    },
    "ollama": {
        "base_url": os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").strip() or None,
        "api_key_env": "OLLAMA_API_KEY",
        "default_model": os.environ.get("OLLAMA_MODEL", "llama3.3"),
        "best_model": os.environ.get("OLLAMA_MODEL", "llama3.3"),
        "embed_model": None,
        "cost_tier": "free",
        "label": "Ollama (local)",
        "optional_key": True,
    },
}

# Task-type → ordered provider preference list (first available + not tripped wins)
TASK_ROUTES: Dict[str, List[str]] = {
    "speed":   ["groq", "cerebras", "fireworks", "together", "openai", "gemini"],
    "code":    ["mistral", "groq", "fireworks", "openai", "anthropic", "deepseek"],
    "reason":  ["deepseek", "openrouter", "fireworks", "anthropic", "openai", "groq", "cohere", "huggingface"],
    "context": ["gemini", "openai", "anthropic", "openrouter", "cohere", "huggingface"],
    "free":    ["groq", "cerebras", "gemini", "openrouter", "deepseek", "mistral", "together", "ollama", "cohere"],
    "default": ["openai", "groq", "gemini", "openrouter", "together", "fireworks", "anthropic", "cohere", "azure", "huggingface", "ollama"],
}

# Per-provider circuit breakers: provider_name -> monotonic time until retry allowed
_circuit_breakers: Dict[str, float] = {}
_CIRCUIT_COOLDOWN = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_api_key(provider_name: str) -> str:
    cfg = PROVIDERS[provider_name]
    key_env = cfg["api_key_env"]
    # Gemini: prefer GOOGLE_GEMINI_API_KEY (script/data), then GOOGLE_AI_API_KEY
    if provider_name == "gemini":
        key = os.environ.get("GOOGLE_GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_AI_API_KEY", "").strip()
    elif provider_name == "huggingface":
        key = (
            os.environ.get("HF_TOKEN", "").strip()
            or os.environ.get("HUGGINGFACE_HUB_TOKEN", "").strip()
            or os.environ.get("HUGGINGFACE_API_KEY", "").strip()
        )
    elif provider_name == "ollama":
        key = os.environ.get(key_env, "").strip() or "ollama"
    else:
        key = os.environ.get(key_env, "").strip()
    return key


def _is_provider_configured(provider_name: str) -> bool:
    cfg = PROVIDERS.get(provider_name) or {}
    if provider_name == "azure":
        return bool(_get_api_key(provider_name)) and bool(cfg.get("base_url"))
    if provider_name == "ollama":
        enabled = os.environ.get("OLLAMA_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")
        return enabled and bool(cfg.get("base_url"))
    if cfg.get("optional_key"):
        return bool(_get_api_key(provider_name)) and bool(cfg.get("base_url"))
    if not _get_api_key(provider_name):
        return False
    return True


def _is_circuit_open(provider_name: str) -> bool:
    until = _circuit_breakers.get(provider_name, 0.0)
    return time.monotonic() < until


def _trip_circuit(provider_name: str) -> None:
    _circuit_breakers[provider_name] = time.monotonic() + _CIRCUIT_COOLDOWN


def _reset_circuit(provider_name: str) -> None:
    _circuit_breakers.pop(provider_name, None)


def _prefer_free_env() -> bool:
    """When True, task_type 'default' routes like 'free' (Groq/Gemini first, not OpenAI)."""
    return os.environ.get("LLM_PREFER_FREE", "").strip().lower() in ("1", "true", "yes", "on")


def _effective_task_type(task_type: str) -> str:
    if task_type == "default" and _prefer_free_env():
        return "free"
    return task_type


def _provider_chain_for(task_type: str) -> List[str]:
    """Return ordered provider list for a task type, skipping unconfigured ones."""
    chain = TASK_ROUTES.get(_effective_task_type(task_type), TASK_ROUTES["default"])
    return [p for p in chain if _is_provider_configured(p)]


# ---------------------------------------------------------------------------
# Response type
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """Structured response from LLM calls — backward-compatible."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    raw: Optional[Dict] = None


def accumulate_llm_usage_from_response(total: Dict[str, int], response: Any) -> None:
    """
    Merge LLMResponse.usage into a running totals dict (prompt / completion / total tokens).
    Used by video_ai_bridge + COGS so planning/enhancement calls aggregate to one job total.
    """
    if not response or not isinstance(total, dict):
        return
    u = getattr(response, "usage", None)
    if not isinstance(u, dict):
        return
    pt = int(u.get("prompt_tokens") or 0)
    ct = int(u.get("completion_tokens") or 0)
    tt = int(u.get("total_tokens") or 0)
    if tt <= 0 and (pt > 0 or ct > 0):
        tt = pt + ct
    total["prompt_tokens"] = int(total.get("prompt_tokens") or 0) + pt
    total["completion_tokens"] = int(total.get("completion_tokens") or 0) + ct
    total["total_tokens"] = int(total.get("total_tokens") or 0) + max(tt, pt + ct)


# ---------------------------------------------------------------------------
# Anthropic (native API)
# ---------------------------------------------------------------------------

def _call_anthropic(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int,
    timeout: int,
    provider_name: str,
) -> LLMResponse:
    """Call Anthropic Messages API. Converts OpenAI-format messages to Anthropic format."""
    system_parts: List[str] = []
    chat_messages: List[Dict[str, Any]] = []
    for m in messages:
        role = (m.get("role") or "user").lower()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            chat_messages.append({"role": role, "content": content})
    if not chat_messages:
        return LLMResponse(success=False, provider=provider_name, error="anthropic: no user/assistant messages")
    system_text = "\n\n".join(system_parts) if system_parts else None
    body: Dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": chat_messages,
    }
    if system_text:
        body["system"] = system_text
    try:
        import requests
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
            timeout=timeout,
        )
    except Exception as e:
        err = str(e)
        if "timeout" in err.lower():
            return LLMResponse(success=False, provider=provider_name, error=f"anthropic: request timed out")
        return LLMResponse(success=False, provider=provider_name, error=f"anthropic: {err[:200]}")
    if r.status_code != 200:
        err = (r.json() or {}).get("error", {}).get("message", r.text[:200])
        quota = r.status_code == 429 or "rate" in err.lower() or "overloaded" in err.lower()
        auth_fail = r.status_code == 401 or "invalid" in err.lower() or "unauthorized" in err.lower()
        if quota or auth_fail:
            _trip_circuit(provider_name)
        return LLMResponse(success=False, provider=provider_name, error=f"anthropic: {err}")
    data = r.json()
    content_blocks = (data.get("content") or [])
    text = ""
    for block in content_blocks:
        if block.get("type") == "text":
            text += (block.get("text") or "")
    usage = None
    if "usage" in data:
        u = data["usage"]
        usage = {
            "prompt_tokens": u.get("input_tokens") or 0,
            "completion_tokens": u.get("output_tokens") or 0,
            "total_tokens": (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0),
        }
    _reset_circuit(provider_name)
    return LLMResponse(
        success=True,
        content=text or "",
        model=model,
        provider=provider_name,
        usage=usage,
        raw={"id": data.get("id"), "model": model},
    )


# ---------------------------------------------------------------------------
# Core provider call
# ---------------------------------------------------------------------------

def _call_provider(
    provider_name: str,
    messages: List[Dict[str, str]],
    model: Optional[str],
    temperature: float,
    max_tokens: int,
    timeout: int,
    use_best: bool = False,
) -> LLMResponse:
    """Call a single provider. Returns LLMResponse (success or failure)."""
    cfg = PROVIDERS[provider_name]
    api_key = _get_api_key(provider_name)

    if not api_key and not cfg.get("optional_key"):
        return LLMResponse(success=False, provider=provider_name,
                           error=f"{provider_name}: API key not configured ({cfg['api_key_env']})")
    if not api_key:
        api_key = "ollama"

    if _is_circuit_open(provider_name):
        remaining = int(_circuit_breakers[provider_name] - time.monotonic())
        return LLMResponse(success=False, provider=provider_name,
                           error=f"{provider_name}: circuit breaker open, retry in {remaining}s")

    if model is None:
        model = cfg["best_model"] if use_best else cfg["default_model"]

    # Anthropic: native Messages API (not OpenAI-compatible)
    if provider_name == "anthropic":
        return _call_anthropic(api_key, messages, model, max_tokens, timeout, provider_name)

    # Mistral code tasks: swap to codestral automatically
    if provider_name == "mistral" and model == cfg["default_model"]:
        pass  # caller can pass model='codestral-latest' explicitly

    try:
        from openai import OpenAI
        kwargs: Dict[str, Any] = {"api_key": api_key, "max_retries": 0, "timeout": timeout}
        if cfg["base_url"]:
            kwargs["base_url"] = cfg["base_url"]

        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else ""
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        _reset_circuit(provider_name)
        return LLMResponse(
            success=True,
            content=content or "",
            model=model,
            provider=provider_name,
            usage=usage,
            raw={"id": getattr(response, "id", None), "model": getattr(response, "model", model)},
        )

    except Exception as e:
        err = str(e)
        quota_hit = any(k in err.lower() for k in (
            "rate_limit", "429", "insufficient_quota", "quota_exceeded",
            "too_many_requests", "rate limit",
        ))
        auth_fail = any(k in err.lower() for k in ("invalid_api_key", "401", "unauthorized"))

        if quota_hit or auth_fail:
            _trip_circuit(provider_name)
            return LLMResponse(success=False, provider=provider_name,
                               error=f"{provider_name}: quota/auth error — circuit tripped for 5 min. ({err[:120]})")
        if "timeout" in err.lower():
            return LLMResponse(success=False, provider=provider_name,
                               error=f"{provider_name}: request timed out")

        return LLMResponse(success=False, provider=provider_name,
                           error=f"{provider_name}: {err[:200]}")


# ---------------------------------------------------------------------------
# Public API  (backward-compatible)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = int(os.environ.get("LLM_TIMEOUT_SECONDS", "10"))


def is_available() -> bool:
    """True if at least one provider is configured."""
    return any(_is_provider_configured(p) for p in PROVIDERS)


def configured_providers() -> List[str]:
    """Return list of provider names that have API keys set."""
    return [p for p in PROVIDERS if _is_provider_configured(p)]


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: Optional[int] = None,
    provider: Optional[str] = None,
    task_type: str = "default",
    use_best: bool = False,
) -> LLMResponse:
    """
    Send a chat completion request.

    Args:
        messages:   List of {"role": "user"|"assistant"|"system", "content": "..."}
        model:      Override model name. None = provider default.
        temperature: 0-2, lower = more deterministic.
        max_tokens: Max tokens in response.
        timeout:    Request timeout in seconds.
        provider:   Force a specific provider (e.g. "groq"). None = auto-route.
        task_type:  Routing hint: "speed" | "code" | "reason" | "context" | "free" | "default"
                    When LLM_PREFER_FREE=1 in .env, "default" uses the same chain as "free".
        use_best:   Use the provider's best/larger model instead of the default.

    Returns:
        LLMResponse — always returns, never raises. Includes .provider field.
    """
    timeout = timeout or DEFAULT_TIMEOUT

    # Single provider forced
    if provider:
        if provider not in PROVIDERS:
            return LLMResponse(success=False, error=f"Unknown provider: {provider}")
        return _call_provider(provider, messages, model, temperature, max_tokens, timeout, use_best)

    # Auto-route: try each provider in chain until one succeeds
    chain = _provider_chain_for(task_type)
    if not chain:
        return LLMResponse(
            success=False,
            error="No AI providers configured. Add at least one API key to .env — "
                  "try GROQ_API_KEY (free at console.groq.com) or GOOGLE_AI_API_KEY (free at ai.google.dev).",
        )

    errors: List[str] = []
    for pname in chain:
        result = _call_provider(pname, messages, model, temperature, max_tokens, timeout, use_best)
        if result.success:
            return result
        errors.append(result.error or f"{pname}: unknown error")

    return LLMResponse(
        success=False,
        error=f"All providers failed. Tried: {', '.join(chain)}. "
              f"Errors: {' | '.join(errors[:3])}",
    )


def complete(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: Optional[int] = None,
    provider: Optional[str] = None,
    task_type: str = "default",
    use_best: bool = False,
) -> LLMResponse:
    """
    Simple single-prompt completion with optional system message.
    Wraps chat() for convenience — backward-compatible.
    """
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return chat(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        provider=provider,
        task_type=task_type,
        use_best=use_best,
    )


def embed(
    texts: List[str],
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> LLMResponse:
    """
    Get text embeddings.
    Primary: OpenAI text-embedding-3-small
    Fallback: Mistral mistral-embed (free, 1B tokens/month)

    Returns LLMResponse with raw['embeddings'] as list of float lists on success.
    """
    if not texts:
        return LLMResponse(success=False, error="No texts provided.")

    # Build ordered embed provider chain
    embed_providers = []
    if provider:
        embed_providers = [provider]
    else:
        for pname in ["openai", "mistral"]:
            if _is_provider_configured(pname) and not _is_circuit_open(pname):
                embed_providers.append(pname)

    if not embed_providers:
        return LLMResponse(success=False, error="No embedding providers configured (need OPENAI_API_KEY or MISTRAL_API_KEY).")

    errors: List[str] = []
    for pname in embed_providers:
        cfg = PROVIDERS[pname]
        api_key = _get_api_key(pname)
        if not api_key:
            continue

        embed_model = model or cfg.get("embed_model")
        if not embed_model:
            errors.append(f"{pname}: no embedding model available")
            continue

        try:
            from openai import OpenAI
            kwargs: Dict[str, Any] = {"api_key": api_key}
            if cfg["base_url"]:
                kwargs["base_url"] = cfg["base_url"]
            client = OpenAI(**kwargs)

            response = client.embeddings.create(input=texts, model=embed_model)
            embeddings = [d.embedding for d in response.data]
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens or 0,
                    "total_tokens": response.usage.total_tokens or 0,
                }
            return LLMResponse(
                success=True,
                model=embed_model,
                provider=pname,
                usage=usage,
                raw={"embeddings": embeddings},
            )
        except Exception as e:
            errors.append(f"{pname}: {str(e)[:120]}")

    return LLMResponse(success=False, error=f"Embedding failed. {' | '.join(errors)}")


# ---------------------------------------------------------------------------
# Provider status (used by /api/ai/providers route)
# ---------------------------------------------------------------------------

def get_provider_status() -> List[Dict[str, Any]]:
    """Return status of every provider — configured, circuit state, models."""
    result = []
    for name, cfg in PROVIDERS.items():
        key_set = _is_provider_configured(name)
        circuit_open = _is_circuit_open(name) if key_set else False
        remaining = max(0, int(_circuit_breakers.get(name, 0) - time.monotonic())) if circuit_open else 0
        row: Dict[str, Any] = {
            "provider": name,
            "label": cfg["label"],
            "cost_tier": cfg["cost_tier"],
            "configured": key_set,
            "available": key_set and not circuit_open,
            "circuit_open": circuit_open,
            "circuit_retry_in_sec": remaining,
            "default_model": cfg["default_model"],
            "best_model": cfg["best_model"],
            "api_key_env": cfg["api_key_env"],
        }
        # Gemini accepts GOOGLE_GEMINI_API_KEY or GOOGLE_AI_API_KEY — surface which is active
        if name == "gemini" and key_set:
            if os.environ.get("GOOGLE_GEMINI_API_KEY", "").strip():
                row["key_source"] = "GOOGLE_GEMINI_API_KEY"
            else:
                row["key_source"] = "GOOGLE_AI_API_KEY"
        result.append(row)
    return result


def reset_circuit(provider_name: str) -> bool:
    """Manually reset a provider's circuit breaker. Returns True if provider exists."""
    if provider_name not in PROVIDERS:
        return False
    _reset_circuit(provider_name)
    return True


# ---------------------------------------------------------------------------
# Convenience shortcuts for common task types
# ---------------------------------------------------------------------------

def fast(prompt: str, **kwargs) -> LLMResponse:
    """Speed-optimised call — routes to Groq/Cerebras first."""
    return complete(prompt, task_type="speed", **kwargs)


def reason(prompt: str, **kwargs) -> LLMResponse:
    """Reasoning/strategy call — routes to DeepSeek R1 first."""
    return complete(prompt, task_type="reason", **kwargs)


def code(prompt: str, **kwargs) -> LLMResponse:
    """Code generation call — routes to Mistral Codestral first."""
    kwargs.setdefault("model", None)
    # Auto-select codestral when mistral is the provider
    result = complete(prompt, task_type="code", **kwargs)
    return result


def long_context(prompt: str, **kwargs) -> LLMResponse:
    """Long document / 1M-token context call — routes to Gemini Flash first."""
    return complete(prompt, task_type="context", **kwargs)


def free_only(prompt: str, **kwargs) -> LLMResponse:
    """Only use free-tier providers — never hits paid OpenAI."""
    return complete(prompt, task_type="free", **kwargs)


def stream_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: Optional[int] = None,
    provider: Optional[str] = None,
    task_type: str = "speed",
):
    """
    Generator that yields text token strings from a streaming LLM call.
    Falls back through the provider chain until one succeeds.
    Yields empty string on failure (so callers don't need to handle StopIteration).

    Usage:
        for token in stream_chat(messages, task_type="speed"):
            yield token
    """
    timeout = timeout or DEFAULT_TIMEOUT
    chain = [provider] if provider else _provider_chain_for(task_type)

    for pname in chain:
        cfg = PROVIDERS[pname]
        api_key = _get_api_key(pname)
        if not api_key or _is_circuit_open(pname):
            continue

        use_model = model or cfg["default_model"]
        try:
            from openai import OpenAI
            kwargs: Dict[str, Any] = {"api_key": api_key, "max_retries": 0, "timeout": timeout}
            if cfg["base_url"]:
                kwargs["base_url"] = cfg["base_url"]
            client = OpenAI(**kwargs)

            stream = client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
            _reset_circuit(pname)
            return  # success — stop trying providers

        except Exception as e:
            err = str(e)
            if any(k in err.lower() for k in ("rate_limit", "429", "quota", "unauthorized", "401")):
                _trip_circuit(pname)
            # try next provider
            continue

    # All providers failed — yield nothing (caller gets empty stream)


# ---------------------------------------------------------------------------
# Singleton-style access (backward-compatible)
# ---------------------------------------------------------------------------
llm_service = type("LLMService", (), {
    "is_available": staticmethod(is_available),
    "chat": staticmethod(chat),
    "complete": staticmethod(complete),
    "embed": staticmethod(embed),
    "fast": staticmethod(fast),
    "reason": staticmethod(reason),
    "code": staticmethod(code),
    "long_context": staticmethod(long_context),
    "free_only": staticmethod(free_only),
    "get_provider_status": staticmethod(get_provider_status),
    "configured_providers": staticmethod(configured_providers),
    "reset_circuit": staticmethod(reset_circuit),
})()
