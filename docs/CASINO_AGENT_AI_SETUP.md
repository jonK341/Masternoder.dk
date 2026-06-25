# Casino agent AI setup

Legitimate API keys for autonomous casino betting agents on Masternoder.dk. **Never search for or use leaked keys** — sign up at each provider and paste keys into server `.env` only.

Related: `docs/CASINO_DEPLOY_OPS.md`, `docs/CASINO_EXPANSION_PLAN.md`, `backend/services/casino_agent_llm_planner.py`.

---

## How it works today

```
cron / POST /api/agent/casino/run-all
  → casino_agents_service.run_all()
    → casino_agent_llm_planner.plan_bet()   [if CASINO_AGENT_LLM=1]
      → agent_ai_router.routed_chat(task_kind="casino_bet_plan")
        → llm_service.chat(task_type="reason")   # or model override
    → casino_service.play_*()                 [execute validated plan]
```

| Component | Role |
|-----------|------|
| `data/casino_agent_models.json` | Agent personas: strategy, skills, `task_kind`, optional `llm_task_type` |
| `data/casino_agents.json` | Runtime agents: `user_id`, `model_id`, policy (`min_bet`, `max_bet`, `allowed_games`) |
| `casino_agent_llm_planner.py` | Builds prompt, calls LLM, parses JSON plan, clamps to policy |
| `agent_ai_router.py` | Maps `casino_bet_plan` → `task_type: reason` (Kelly sizing / game selection) |
| `llm_service.py` | Multi-provider fallback chain from env API keys |

### Expected LLM JSON output

```json
{
  "game": "dice",
  "bet": 25,
  "confidence": 0.72,
  "reasoning": "Rank 8 — small dice grind with positive EV framing.",
  "spectator_line": "Kelly sizes down after two losses.",
  "params": { "guess": 3 }
}
```

Heuristic fallback (no API key or `CASINO_AGENT_LLM=0`) uses `bet_fraction` and `preferred_games` from the model config.

### Env vars (casino-specific)

| Variable | Default | Purpose |
|----------|---------|---------|
| `CASINO_AGENT_LLM` | `0` | `1` = use LLM for bet planning; `0` = heuristics only |
| `AGENT_CASINO_SECRET` | *(empty)* | Auth for `POST /api/agent/casino/*` via header `X-Agent-Casino-Key` |
| `LLM_TIMEOUT_SECONDS` | `10` | LLM request timeout (shared with all agents) |
| `LLM_PREFER_FREE` | off | When `1`, `task_type=default` routes to free-tier chain |

**Documented but not wired in code yet:** `CASINO_AGENT_AUTOMATION`, `CASINO_AGENT_LLM_REQUIRED`, `CASINO_AGENT_LLM_TIMEOUT` — treat as planned; use `CASINO_AGENT_LLM` and `LLM_TIMEOUT_SECONDS` today.

### Model routing (`task_type`)

Default for `casino_bet_plan` is **`reason`** (DeepSeek → OpenRouter → Anthropic → OpenAI → Groq → Cohere).

Override per agent in `data/casino_agent_models.json`:

```json
{
  "models": {
    "casino_kelly_agent": {
      "name": "Kelly Optimizer",
      "task_kind": "casino_bet_plan",
      "llm_task_type": "reason",
      "strategy": "kelly_flat",
      "skills": ["kelly_sizing", "play_dice"],
      "preferred_games": ["dice", "coin_flip"],
      "bet_fraction": 0.05
    },
    "casino_speed_agent": {
      "name": "Speed Grinder",
      "task_kind": "casino_bet_plan",
      "llm_task_type": "speed",
      "preferred_games": ["coin_flip"]
    },
    "casino_free_agent": {
      "name": "Free Tier Scout",
      "task_kind": "casino_bet_plan",
      "llm_task_type": "free",
      "preferred_games": ["dice"]
    }
  }
}
```

| `llm_task_type` | Provider chain (first configured wins) | Best for |
|-----------------|----------------------------------------|----------|
| `reason` | deepseek → openrouter → anthropic → openai → groq | Kelly sizing, strategy, game pick |
| `speed` | groq → cerebras → together → openai | Fast cron ticks, high bet frequency |
| `free` | groq → cerebras → gemini → openrouter → deepseek | Zero-cost dev / low-volume prod |
| `context` | gemini → openai → anthropic | Long leaderboard + history context |

**Bet planning vs chat:** The same call produces structured JSON (`game`, `bet`, `params`) plus natural-language `reasoning` and `spectator_line` for Discord/social. No separate chat endpoint is required for autonomous play.

**Ollama / local:** Not registered in `llm_service.PROVIDERS`. For self-hosted models, run an OpenAI-compatible proxy (e.g. LiteLLM → Ollama) and add a custom provider entry, or route via OpenRouter if the model is listed there.

---

## Provider comparison (2025–2026)

Sign up at official sites only. Rate limits change — check each dashboard after signup.

| Provider | Signup | Env var | Free tier | Best model (agent bets) | Rate limits (typical) | Bet JSON | Chat / NL |
|----------|--------|---------|-----------|-------------------------|------------------------|----------|-----------|
| **Groq** | [console.groq.com/keys](https://console.groq.com/keys) | `GROQ_API_KEY` | Yes, no card | `llama-3.3-70b-versatile` | ~30 RPM; 70B ~1k RPD | Excellent | Good `spectator_line` |
| **DeepSeek** | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | `DEEPSEEK_API_KEY` | 5M tokens / 30 days | `deepseek-chat` (fast), `deepseek-reasoner` (Kelly) | Standard API limits | **Best for strategy** | Strong reasoning text |
| **Google Gemini** | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `GOOGLE_AI_API_KEY` | Flash free tier | `gemini-2.5-flash` | ~10–15 RPM, ~1.5k RPD (Flash) | Good | Good; 1M context for history |
| **OpenRouter** | [openrouter.ai/keys](https://openrouter.ai/keys) | `OPENROUTER_API_KEY` | `:free` models | `deepseek/deepseek-r1:free`, `meta-llama/llama-3.3-70b-instruct:free` | 20 RPM, 50 RPD (no purchase); 1k RPD after $10 credits | Good fallback | Multi-model in one key |
| **Anthropic** | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) | `ANTHROPIC_API_KEY` | ~$5 trial credits (SMS verify) | `claude-3-5-sonnet-20241022` | Tier-based RPM | Excellent | Best prose quality |
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `OPENAI_API_KEY` | No (paid) | `gpt-4o-mini` | Pay-as-you-go | Reliable JSON mode | Strong |
| **Together AI** | [api.together.xyz/settings/api-keys](https://api.together.xyz/settings/api-keys) | `TOGETHER_API_KEY` | Limited promos | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | Account limits | Good | Good |
| **Mistral** | [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys/) | `MISTRAL_API_KEY` | ~1B tok/month | `mistral-small-latest` | Free tier caps | OK | Better for code tasks |
| **Cerebras** | [cloud.cerebras.ai](https://cloud.cerebras.ai/) | `CEREBRAS_API_KEY` | Yes | `llama3.3-70b` | ~1M tok/day free | Good speed backup | Adequate |

### Recommended stacks after deploy

**Minimum (free):** `GROQ_API_KEY` + `GOOGLE_AI_API_KEY` — fast primary + free backup.

**Best strategy (low cost):** add `DEEPSEEK_API_KEY` — first in the `reason` chain for Kelly/game selection.

**Resilient prod:** Groq + DeepSeek + OpenRouter — three keys cover speed, reasoning, and failover.

**Premium quality:** add `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` for harder strategy; keep Groq for high-frequency cron.

---

## Server `.env` example (placeholders only)

```bash
# --- Casino agents ---
AGENT_CASINO_SECRET=REPLACE_WITH_LONG_RANDOM_SECRET
CASINO_AGENT_LLM=1
LLM_TIMEOUT_SECONDS=12

# At least one LLM key (add more for fallback)
GROQ_API_KEY=gsk_REPLACE_ME
DEEPSEEK_API_KEY=sk-REPLACE_ME
GOOGLE_AI_API_KEY=REPLACE_ME
# OPENROUTER_API_KEY=sk-or-v1-REPLACE_ME
# ANTHROPIC_API_KEY=sk-ant-REPLACE_ME

# Optional: prefer free providers for non-casino routes too
# LLM_PREFER_FREE=1
```

After editing on server:

```bash
chmod 640 /var/www/html/.env && chown root:www-data /var/www/html/.env
sudo systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
```

---

## Wiring providers (no code change needed)

`casino_agent_llm_planner.py` does **not** call providers directly. It uses `routed_chat()` → `llm_service.chat()`. Adding a key to `.env` is enough; the first configured provider in the chain wins.

To force a single provider for debugging:

```python
from backend.services.llm_service import chat
resp = chat(messages, provider="groq", task_type="reason")
```

To add a new provider permanently, extend `PROVIDERS` and `TASK_ROUTES` in `backend/services/llm_service.py`.

---

## API auth (`AGENT_CASINO_SECRET`)

Protected routes:

- `POST /api/agent/casino/run-all`
- `POST /api/agent/casino/run/<agent_id>`
- `POST /api/agent/casino/discord/notify`

```bash
curl -X POST https://masternoder.dk/api/agent/casino/run-all \
  -H "Content-Type: application/json" \
  -H "X-Agent-Casino-Key: YOUR_AGENT_CASINO_SECRET" \
  -d '{"dry_run": true}'
```

Public (no secret): `GET /api/agent/casino/models`, `GET /api/agent/casino/agents`.

Generate a secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

## Security

1. **Never commit** `.env`, API keys, or `data/casino_agents.json` with production secrets.
2. Store keys only in server `/var/www/html/.env` (mode `640`, group `www-data`).
3. **Rotate** `AGENT_CASINO_SECRET` and LLM keys if exposed; revoke old keys in provider dashboards.
4. Use **dry_run** when testing: `{"dry_run": true}` returns the plan without placing bets.
5. Set agent policy `max_bet` conservatively in `data/casino_agents.json`.
6. Brain logs (`logs/casino_agent_brain.jsonl`) may contain reasoning — restrict file permissions.

---

## Verify after setup

```bash
# Provider status (if endpoint exposed)
curl -s https://masternoder.dk/api/agents/intelligence/llm-status

# List casino agent models
curl -s https://masternoder.dk/api/agent/casino/models

# Dry-run all agents (requires secret)
curl -X POST https://masternoder.dk/api/agent/casino/run-all \
  -H "X-Agent-Casino-Key: $AGENT_CASINO_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

Unit tests:

```powershell
python -m pytest tests/unit/test_casino_agent_llm.py tests/unit/test_casino_agents.py -q
```

---

## Quick signup checklist

| Step | Action |
|------|--------|
| 1 | [Groq keys](https://console.groq.com/keys) → copy to `GROQ_API_KEY` |
| 2 | [DeepSeek keys](https://platform.deepseek.com/api_keys) → `DEEPSEEK_API_KEY` |
| 3 | [Gemini API key](https://aistudio.google.com/apikey) → `GOOGLE_AI_API_KEY` |
| 4 | Generate `AGENT_CASINO_SECRET`, set `CASINO_AGENT_LLM=1` |
| 5 | Restart uWSGI, dry-run `run-all`, then enable cron |
