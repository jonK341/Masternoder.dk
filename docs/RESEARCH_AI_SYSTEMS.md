# Research: AI Systems in MasterNoder.dk

Oversigt over alle AI-relaterede tjenester, agents og providers i projektet. **Content:** hvad hver del gør. **Context:** hvordan det bruges (routing, fallback, pipelines).

---

## Quick reference

| Hvad | Hvor |
|------|------|
| API-nøgler til .env | §8 (tabel med links), .env.example, Agent Support → Resources |
| Valgfrie nøgler (nem) | §11 (copy-paste blok) |
| Profile ↔ API keys / agents | §12 (tabel + flow) |
| Production & 404-fix | §10; også `docs/CHECKPOINTS_RECHECK.md` §9 |
| Videre udvikling | §13 |

**Verifikation:** Kør `python scripts/test_url_timing.py` for front/profile URLs. Se `docs/CHECKPOINTS_RECHECK.md` for alle checkpoints og "How to verify".

---

## 1. AI LLM Service (sprogmodeller)

**Fil:** `backend/services/llm_service.py`

Multi-provider med smart routing og fallback. Alle bruger OpenAI-kompatibel REST.

| Provider    | Modeller              | Nøgle (env)        | Tier    | Brug                    |
|------------|------------------------|--------------------|---------|-------------------------|
| **OpenAI** | gpt-4o-mini, gpt-4o   | OPENAI_API_KEY     | paid    | Primær, chat, embeddings |
| **Groq**   | Llama 3.3 70B         | GROQ_API_KEY       | free    | Speed (300+ tok/s)       |
| **Gemini** | Gemini 2.5 Flash/Pro   | GOOGLE_AI_API_KEY  | free    | Lang kontekst (1M), multimodal |
| **OpenRouter** | Llama 4, DeepSeek R1 | OPENROUTER_API_KEY | free    | 30+ modeller, reason     |
| **Cerebras** | Llama 3.3 70B        | CEREBRAS_API_KEY   | free    | 1M tok/dag, hurtig       |
| **DeepSeek** | DeepSeek V3/R1       | DEEPSEEK_API_KEY   | near-free | 5M free tokens        |
| **Mistral**  | Codestral, Large     | MISTRAL_API_KEY    | free    | Code (1B tok/måned)      |

**Task-routing:** `speed` → groq/cerebras; `code` → mistral/groq; `reason` → deepseek/openrouter; `context` → gemini; `free` → alle free providers.

**API:** `chat()`, `complete()`, `embed()`; circuit breakers ved fejl; `get_provider_status()` til debugger.

---

## 2. AI TTS (Text-to-Speech)

**Fil:** `backend/services/tts_service.py`

Prioritet: **Piper** (gratis, lokalt) → **ElevenLabs** (hvis nøgle) → **gTTS** → **pyttsx3**.

| Engine     | Env / krav              | Beskrivelse              |
|------------|--------------------------|---------------------------|
| Piper      | PIPER_MODEL_PATH eller piper_voices/*.onnx | Gratis, lokal, ingen begrænsning |
| ElevenLabs | ELEVENLABS_API_KEY       | 10K tegn/md gratis        |
| gTTS       | —                        | Google TTS, gratis        |
| pyttsx3    | —                        | Offline fallback          |

Bruges i video-pipeline til narration (`generate_narration_for_segments`).

---

## 3. AI Audio Enhancement

**Fil:** `backend/services/audio_enhancement_service.py`

Valgfri lydforbedring på TTS-narration.

| Komponent     | Env                      | Beskrivelse                    |
|---------------|---------------------------|--------------------------------|
| DeepFilterNet | AUDIO_ENHANCE=1 eller AUDIO_ENHANCE_NOISE=1 | AI-støjreduktion (pip: deepfilternet) |
| FFmpeg loudnorm | AUDIO_ENHANCE=1 eller AUDIO_ENHANCE_LOUDNORM=1 | Normalisering, mastering   |

Aktiveres i pipeline når `AUDIO_ENHANCE=1` (fx i `.env`).

---

## 4. AI Agent Research Tracker

**Fil:** `backend/services/agent_research_tracker.py`  
**Routes:** `backend/routes/agent_research_routes.py`

Tracker for agent-drevet research og monitoring.

- **Research topics:** API structure, code quality, performance, security, point systems, triggers, user engagement, economy, exploration, education, events, customization, creativity m.m.
- **Monitoring targets:** API endpoints, database, system resources, agent activity, point systems, triggers, user activity, economy, exploration, education, events, customization, creativity, contributions.
- **Data:** `logs/agent_research/research.json`, `monitoring.json`.

**Endpoints:**

- `POST /api/agent/research/start` — start research (topic_id, agent_id)
- `POST /api/agent/research/finding` — tilføj finding (project_id, finding)
- `GET /api/agent/research/summary` — research-oversigt
- Monitoring-endpoints for targets og alerts

**Integration:** Agent activation (auto_research, auto_research_summary), agent_controller (`agents['research']`), trigger `research_completed` (point-belønning).

---

## 5. AI Intelligence Aggregator

**Fil:** `backend/services/aggregators/intelligence_aggregator.py`  
**Routes:** `backend/routes/intelligence_aggregator_routes.py`

Samler research-papers, nyheder og trending (designet til arXiv, nyhedskilder).

- **Research:** `get_research_papers(limit, category)` — kategorier: ai, machine-learning, computer-vision, all. Lige nu mock-data; kan kobles til arXiv API.
- **News:** `get_news(limit, source)` — TechCrunch, The Verge, Wired, AI News (mock).
- **Trending:** `get_trending(limit)`.
- Cache: research 6t, news 1t, trending 30 min.

**Endpoints:**

- `GET /api/aggregators/intelligence/research?limit=10&category=all`
- `GET /api/aggregators/intelligence/news`
- `GET /api/aggregators/intelligence/trending`
- `GET /api/aggregators/intelligence/all`
- `GET /api/aggregators/intelligence/test`

---

## 6. AI Video / billede

| Tjeneste     | Fil                              | Env                  | Rolle                    |
|--------------|-----------------------------------|----------------------|--------------------------|
| RunwayML     | runwayml_service                 | RUNWAYML_API_KEY     | Gen-4 videoclips         |
| ModelsLab    | modelslab_video_service          | MODELSLAB_API_KEY    | CogVideoX, billeder      |
| Pika        | pika_service                     | PIKA_LABS_API_KEY    | Pika 2.2 clips           |
| Stability   | stability_image_service          | STABILITY_AI_API_KEY | Billeder                 |
| Pollinations| —                                 | —                    | Gratis billeder (ingen nøgle) |

Bruges i `video_generator_service` til AI-clips og billeder til dokumentarflow.

---

## 7. Øvrige AI-relaterede moduler (content + context)

- **AI Content Generator** — generering af indhold (tekst, billeder, video, audio) via LLM + providers.
- **AI Skill Implementations** — video_generation, audio_generation m.fl. der kalder content generator og services.
- **Agent Error Handler** — “Research solution”-step (find lignende løste issues).
- **Master Fix Agent / Debugging** — bruger research og monitoring i fix-flow.
- **AI Intelligence Dashboard / Agent AI Intelligence** — dashboards og agent-brug af LLM.

---

## 8. Konfiguration (env) – API provider links

**Content:** Env-var navne. **Context:** Sæt værdier i `.env`; brug links her eller i `.env.example` til at hente API-nøgler.

| Env var | AI / brug | Provider – link til API key / signup |
|---------|-----------|--------------------------------------|
| **LLM AI** | | |
| `OPENAI_API_KEY` | Primær LLM, embeddings | [OpenAI API keys](https://platform.openai.com/api-keys) |
| `GROQ_API_KEY` | Speed, Llama 3.3 70B | [Groq console](https://console.groq.com/keys) |
| `GOOGLE_AI_API_KEY` | Gemini, lang kontekst | [Google AI Studio](https://aistudio.google.com/apikey) |
| `OPENROUTER_API_KEY` | 30+ modeller, reason | [OpenRouter keys](https://openrouter.ai/keys) |
| `CEREBRAS_API_KEY` | Hurtig, 1M tok/dag | [Cerebras cloud](https://cloud.cerebras.ai/) |
| `DEEPSEEK_API_KEY` | V3/R1 reasoning | [DeepSeek platform](https://platform.deepseek.com/api_keys) |
| `MISTRAL_API_KEY` | Code, Large | [Mistral console](https://console.mistral.ai/api-keys/) |
| **Video/Image AI** | | |
| `RUNWAYML_API_KEY` | Gen-4 video | [Runway settings](https://app.runwayml.com/settings/api) |
| `PIKA_LABS_API_KEY` | Pika 2.2 clips | [Pika](https://pika.art/) / [fal.ai](https://fal.ai) |
| `STABILITY_AI_API_KEY` | Billeder/video | [Stability account](https://platform.stability.ai/account/keys) |
| `MODELSLAB_API_KEY` | CogVideoX, billeder | [ModelsLab dashboard](https://modelslab.com/dashboard/api-keys) |
| **TTS AI** | | |
| `ELEVENLABS_API_KEY` | Voice narration | [ElevenLabs API keys](https://elevenlabs.io/app/settings/api-keys) |
| `PIPER_MODEL_PATH` | Lokal TTS (ingen nøgle) | [Piper GitHub](https://github.com/rhasspy/piper) |
| **Optionals** | | |
| `ANTHROPIC_API_KEY` | Claude | [Anthropic settings](https://console.anthropic.com/settings/keys) |
| `REPLICATE_API_TOKEN` | Run AI models | [Replicate account](https://replicate.com/account/api-tokens) |
| `TOGETHER_API_KEY` | Open-weight models | [Together settings](https://api.together.xyz/settings/api-keys) |
| `COHERE_API_KEY` | Embeddings/chat | [Cohere dashboard](https://dashboard.cohere.com/api-keys) |
| `HUGGINGFACE_HUB_TOKEN` | Inference, hub | [Hugging Face tokens](https://huggingface.co/settings/tokens) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | [Azure portal](https://portal.azure.com/) |

Eksempel i `.env` (kun de du bruger):

```bash
# AI LLM
OPENAI_API_KEY=
GROQ_API_KEY=
GOOGLE_AI_API_KEY=
OPENROUTER_API_KEY=
CEREBRAS_API_KEY=
MISTRAL_API_KEY=
DEEPSEEK_API_KEY=

# AI TTS
ELEVENLABS_API_KEY=
# PIPER_MODEL_PATH=

# AI lydforbedring
AUDIO_ENHANCE=1

# AI Video/billeder
RUNWAYML_API_KEY=
MODELSLAB_API_KEY=
PIKA_LABS_API_KEY=
STABILITY_AI_API_KEY=
```

---

## 9. Kort reference: filer

| Område        | Service-fil                          | Routes-fil                          |
|---------------|--------------------------------------|-------------------------------------|
| LLM           | llm_service.py                       | ai_providers_routes.py              |
| TTS           | tts_service.py                       | (via video_generator + ai_providers)|
| Audio enhance | audio_enhancement_service.py         | (via video_generator)               |
| Research agent| agent_research_tracker.py            | agent_research_routes.py             |
| Intelligence  | aggregators/intelligence_aggregator.py | intelligence_aggregator_routes.py |
| Video         | video_generator_service.py + *video* + *image* services | missing_endpoints (unified generate) |

Denne fil kan opdateres når nye AI-systemer tilføjes eller env-var ændres.

---

## 10. Production & loading

**URL timing:** Kør `python scripts/test_url_timing.py` (eller `BASE_URL=https://masternoder.dk python scripts/test_url_timing.py`) for at tjekke front page og profile page endpoints. Resultater gemmes i `logs/url_timing_results.json`.

**Typiske resultater (reference):**
- **Front page:** Front page init kan timeout (60s) eller være langsom; Stats summary ofte 20–30s. Points all, Battle stats, Agent skillset all, Aggregator frontend bør være 200.
- **Profile page:** Bind session, Profile aggregated, Gallery recent kan give 404 hvis routes ikke er deployet eller blueprints ikke registreret.

**404 deploy checklist:** Ved 404s skrives `logs/production_404_deploy_checklist.txt` med anbefalede route-filer. Tjek:
- Bind session / Profile aggregated → `user_profile_routes.py`, `user_account_routes.py`, og at blueprints er registreret i `register_blueprints.py`.
- Gallery recent → `backend/routes/gallery_routes.py` (fx `/api/gallery/recent-temp`).

**For at få production op at køre:**
1. Sørg for at alle API-nøgler i §8 er sat i `.env` (mindst OPENAI eller GROQ for LLM).
2. Registrér alle relevante blueprints i `register_blueprints.py` så front page init, bind-session, profile/aggregated og gallery/recent-temp svarer.
3. Overvej at forkorte timeout eller cache for stats/summary og front page init for bedre load time.
4. Kør `scripts/add_agent_skill_sets_to_pages.py` for at tilføje agent-skill-sets CSS/JS til alle HTML-sider (inkl. alle vidgenerator-undermapper).

**Troubleshooting:** Hvis front page init timeout: tjek at missing_endpoints eller frontpage-routes svarer hurtigt; overvej cache. Hvis profile 404: se `docs/CHECKPOINTS_RECHECK.md` §9 (Bind session, Profile aggregated, Gallery recent) og `register_blueprints.py`. Resultater fra URL timing: `logs/url_timing_results.json` og `logs/production_404_deploy_checklist.txt`.

---

## 11. Optional API keys (easy add)

**Content:** Valgfrie AI-providers (Claude, Replicate, Together, Cohere, Hugging Face, Azure). **Context:** Kræves ikke for basisk kørsel; tilføjes i `.env` ved behov.

**Nem tilføjelse:** Kopiér blokken herunder ind i `.env`, fjern `#` for den/de nøgler du vil bruge, og indsæt værdi. Links til signup står i §8 og i Agent Support → Resources.

```bash
# Optional – copy into .env, uncomment and set value
# ANTHROPIC_API_KEY=        # Claude: https://console.anthropic.com/settings/keys
# REPLICATE_API_TOKEN=      # https://replicate.com/account/api-tokens
# TOGETHER_API_KEY=         # https://api.together.xyz/settings/api-keys
# COHERE_API_KEY=           # https://dashboard.cohere.com/api-keys
# HUGGINGFACE_HUB_TOKEN=    # https://huggingface.co/settings/tokens
# AZURE_OPENAI_API_KEY=     # https://portal.azure.com/
# AZURE_OPENAI_ENDPOINT=
```

I UI: **Agent Support** → fanen **Resources** viser alle provider-links (inkl. optionals) med env-varnavn, så du kan åbne link, hente nøgle og tilføje til `.env`.

**Enchantment:** For at tilføje en ny optional provider: (1) tilføj linje i §8-tabellen og i .env.example Optional-blokken med link; (2) tilføj evt. i Agent Support backend `ai_api_providers` (agent_support_service.py) så den vises i UI.

---

## 12. Profile & AI connections

**Content:** Hvor brugeren fra profil og AI-agents kan nå API-nøgler og support. **Context:** Én samlet adgang til opsætning af AI-providers og agent-resources.

| Fra | Forbindelse | Hvor |
|-----|-------------|------|
| **Profile** | My Agents-kort | Links: "Full Agent Report" → `/vidgenerator/agents`; "Agent skills" og "API keys & support" → `/vidgenerator/agent_support` |
| **Agents (Agent Report)** | Connections-strip | Links: "Profile & My Agents" → profile; "API keys & optional keys" → Agent Support; "Debugger" → debugger |
| **Agent Support** | Resources-fane | AI API providers (inkl. optionals) med direkte link + env-varnavn; Useful links; API endpoints; Tools |

**Flow:** Profile → Agent skills / API keys & support → Agent Support → Resources → åbn provider-link → hent nøgle → tilføj til `.env`.

---

## 13. Videre research (AI systems)

**Content:** Emner til videre udvikling af AI-systemet. **Context:** LLM-service kan udvides med nye providers (Anthropic, Replicate, Together) ved at tilføje adapter i `llm_service.py` og env-nøgle; TTS med flere stemmer; video-pipeline med flere backends.

- **LLM:** Understøttelse af Anthropic, Replicate, Together (env allerede i §8/§11). Routing i `llm_service.py` udvides med nye provider-keys.
- **Intelligence aggregator:** Koble arXiv API (evt. med optional key for højere rate) til `get_research_papers()`; tilføj flere nyhedskilder.
- **Agent research tracker:** Flere topics og monitoring-targets; integration med point-belønning ved research_completed.
- **Video/Image:** Pollinations kræver ingen nøgle; evt. fal.ai for Pika; flere image-backends.
- **Profile ↔ agents:** Brugerens tildelte agents og skills synkroniseres via `user_agent_skills` og `agent_skillset`; UI-forbindelser er på plads (Profile → Agent Support, Agents → Profile & API keys).

**Enchantments:** (1) Tilføj ny LLM-provider: env i §8 og .env.example, adapter i llm_service.py, evt. i Agent Support ai_api_providers. (2) Tilføj ny optional: §8-tabel + .env.example Optional-blok + evt. agent_support_service ai_api_providers. (3) Verifikation: brug `docs/CHECKPOINTS_RECHECK.md` og `python scripts/test_url_timing.py`.

Opdater denne sektion når nye AI-systemer tilføjes eller env-var ændres.
