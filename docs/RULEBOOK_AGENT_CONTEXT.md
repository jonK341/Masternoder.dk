# Rulebook V1–V16 — Agent Context API

**Purpose:** Serve rulebook knowledge (V1–V16) as agent prompts, tech specs, user guides, and manuals. Feed to agents via prompts.

**Readers:** See [RULEBOOK_READERS.md](./RULEBOOK_READERS.md) for UI surfaces and progress APIs.

## Schema

Each rulebook (V1–V16) includes:

| Field | Purpose |
|-------|---------|
| `agent_prompt` | Instruction text for agent system prompts. Undergoing knowledge. |
| `tech_spec` | Technical specs, APIs, endpoints. For agent tool use. |
| `user_guide` | User-facing guidance. Agents cite when helping users. |
| `manual` | Agent manual section. How to behave, what to do. |
| `image_url` | Optional illustration. Path or URL. |
| `images` | Optional array of `{url, alt, caption}` for multiple illustrations. |

## API

### GET /api/rulebooks/agent-context
### GET /vidgenerator/api/rulebooks/agent-context

**Query params:**

| Param | Values | Default |
|-------|--------|---------|
| `versions` | `all` or `v1,v4,v7` (comma-separated) | `all` |
| `format` | `json` or `prompt` | `json` |
| `sections` | `all` or `agent_prompt,tech_spec,user_guide,manual` | `all` |

**Examples:**

```
GET /vidgenerator/api/rulebooks/agent-context
→ JSON with all rulebooks, all sections

GET /vidgenerator/api/rulebooks/agent-context?versions=v1,v7,v8&format=prompt
→ Plain text for system prompt (V1, V7, V8 only)

GET /vidgenerator/api/rulebooks/agent-context?sections=agent_prompt,manual
→ Only agent_prompt and manual per rulebook
```

## Usage in agents

1. **System prompt:** Fetch `?format=prompt` and prepend to agent system prompt.
2. **RAG:** Store rulebook content, retrieve by query.
3. **Tool context:** Pass `tech_spec` when agent needs API/endpoint info.
4. **User help:** Use `user_guide` when answering user questions.

## Data files

- `data/rulebook_index_v15.json` — master index (V1–V16 catalog) + agent_schema
- `data/rulebook_v1_core.json` … `rulebook_v16_sync.json`
- `data/hunters_rulebook_v2.json`
- `data/communication_psychology_theories.json` (V3)
- `docs/LAB.md` — **Lab companion** (not a numbered V1–V15 volume): `/api/lab/*`, profile keys, `lab_progression_catalog.json`, cooldowns; use with `rulebook_v9_shop.json` **`cross_rulebook_routing.lab_research`** when agents explain shop ↔ lab identity.

## Images in rulebooks

**AI for images:** The project has `image_generation` in `ai_skill_implementations` (returns descriptions via LLM, not pixel output). For actual image generation, use external services (DALL·E, Stable Diffusion) or Cursor’s GenerateImage. Rulebook schema supports `image_url` and `images[]`; add paths to serve illustrations.
