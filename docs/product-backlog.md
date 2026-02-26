# Product Backlog

## Goal
Turn the app into a public-ready meeting intelligence platform with clear value beyond live translation.

## Phase 0 (Stability + Packaging)
1. Reliability hardening
- Keep topic/coach pipelines resilient to malformed model output.
- Improve run labeling (`success` vs `no_effect` vs `error`) for observability.

2. Deployment package
- Maintain self-hosted deployment zip and documented install flow.
- Keep startup validation clear for all required environment settings.

3. Cross-platform runtime
- Validate Linux support (service startup, audio setup guidance, docs).
- Keep Windows and Linux runbooks aligned.

## Phase 1 (Core Meeting Intelligence)
1. Voice recording
- Save session audio per speaker/session.
- Support start/stop and export.

2. Full conversation summary
- Session-level summary after stop.
- Include concise executive summary and detailed breakdown.

3. Action items extraction
- Extract owner, task, due date (if present), and confidence.
- Export as JSON/CSV.

4. Agenda-aware analysis
- Compare meeting flow against configured agenda.
- Show covered/missed/off-agenda sections and coverage score.

5. Meeting performance insights
- Speaking balance, interruptions, topic drift, pace.
- "Meeting health" score with practical recommendations.

## Phase 2 (Advanced Analytics)
1. Sentiment and tone analysis (optional module)
- Per-topic and session-level sentiment trend.
- Keep opt-in due to domain/language variability.

2. Keyword and keyphrase extraction
- Dynamic extraction from transcript (no fixed backend keyword list).
- Add searchable keyword index for recap/exploration.

3. Optional translation mode
- Implemented on February 26, 2026: users can disable translation and run transcript-only intelligence mode.
- Reduce cost and support same-language meetings.

## Phase 3 (Platform + Market Expansion)
1. Multilingual support
- Expand beyond English-centric assumptions in analysis and UX.
- Validate quality per language and locale.

2. STT provider/model flexibility
- Add support path for additional STT engines (including Nova-3 class models).
- Preserve common event contract across providers.

3. Public trial flow
- Invitation code onboarding.
- 10-minute trial cap with visible countdown and controlled auto-stop.
- Per-code usage limits, expiration, and basic abuse controls.

## Phase 4 (Knowledge-Aware Copilot)
1. Workspace connectors
- Start with SharePoint read-only connector.
- Add scheduled sync + incremental updates (not full live crawl first).

2. Multi-datasource selection
- Let users choose data scope per meeting:
  - no datasource
  - default workspace
  - selected datasource

3. Retrieval trust and controls
- Enforce tenant/workspace permission boundaries.
- Include source citations in coach outputs.
- Add admin visibility into indexed content and sync status.

## Go-To-Market Backlog
1. Narrow ICP-first rollout
- Target one segment first (for example recruiting/interview coaching teams).

2. Trial-to-paid funnel
- Invite-only trial, clear value moment (summary + actions + agenda score).
- Simple pricing tiers and usage boundaries.

3. Proof assets
- Short product demos, before/after examples, and outcome-focused messaging.

## Engineering Notes
1. Keep summary/insight pipelines asynchronous to avoid blocking live translation.
2. Add feature flags so new analytics can be rolled out gradually.
3. Add smoke tests for critical end-to-end flows before public launch.
4. Keep schema/contract checks between agents and orchestrators strict and versioned.
