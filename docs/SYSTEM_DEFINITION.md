# System Definition

## Product identity
- Product name: **Live Meeting Copilot**
- Repository/runtime folder name: `live-interview-translator` (kept for compatibility)
- Core purpose: real-time transcript, optional translation, coaching, topic tracking, and structured meeting summary.

## Runtime boundaries
- Frontend: `static/` (single-page app, no framework).
- API/WebSocket backend: FastAPI in `app/`.
- Speech and translation: Azure Speech + Azure Translator.
- AI features: Azure AI Foundry agents (coach/topics/summary).

## Agent catalog (official naming)
- **Conversation Coach Agent**: real-time coaching suggestions.
  - Env binding: `AGENT_ID` or `AGENT_NAME`
- **Topic Intelligence Agent**: incremental topic detection and status updates.
  - Env binding: `TOPIC_AGENT_ID` or `TOPIC_AGENT_NAME` (falls back to `AGENT_ID`/`AGENT_NAME`)
- **Summary Intelligence Agent**: final structured summary generation.
  - Env binding: `SUMMARY_AGENT_ID` or `SUMMARY_AGENT_NAME`

Current Azure agent names/IDs can remain unchanged; these are product-facing names only.

## Instruction ownership model

### 1) Azure agent baseline (Foundry)
- Where: Azure AI Foundry agent system instructions.
- Scope: persistent persona and global behavior per agent.

### 2) Code-authored request framing
- Coach: `app/controller/coach_orchestrator.py` (`_build_prompt_unlocked`).
- Topics: `app/controller/topic_orchestrator.py` (structured context payload).
- Summary: `app/services/summary.py` (`_PROMPT_TEMPLATE`).
- Scope: per-request task framing and schema constraints.

### 3) Web-configurable runtime instruction
- Currently supported: `coach_instruction` only.
- Source: Settings UI -> `PUT /api/config` -> `RuntimeConfig.coach_instruction`.
- Scope: per-session/per-user coaching style refinements.

### 4) Request context data
- Transcript turns, speaker labels, agenda definitions, valid utterance-id constraints, and runtime state.
- Scope: highest-signal task context for each call.

## Effective behavior precedence (practical)
- In practice, responses are shaped by:
  1. Request context data
  2. Runtime web instruction (`coach_instruction`, when set)
  3. Code-authored prompt framing
  4. Azure baseline system instruction

This is the governance model to maintain, even though final model behavior is probabilistic.

## What is configurable from where
- Web UI:
  - runtime config (`capture_mode`, language, translation toggle, coach toggle, summary toggle, `coach_instruction`, etc.)
  - topics definitions/settings
- `.env`:
  - credentials, endpoints, model deployment, agent bindings
- Azure Foundry:
  - baseline system instructions and tool wiring for each agent
- Code:
  - strict schema expectations, payload shaping, deterministic post-processing

## Non-goals (current version)
- No web UI editor for topic-agent or summary-agent system instructions.
- No runtime hot-swap of prompt templates for topic/summary from UI.
- No external prompt registry service.
