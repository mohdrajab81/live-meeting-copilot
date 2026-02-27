# Product Backlog

## Goal

Turn the app into a public-ready meeting intelligence platform with clear value beyond live translation.

---

## ✅ Shipped

| Feature | Notes |
| --- | --- |
| Stability + reliability hardening | Malformed model output handling, run labeling |
| Deployment package | Self-hosted zip, startup validation, runbooks |
| Full conversation summary | Executive summary, key points, action items, decisions, risks, key terms, metadata |
| Topic key points (LLM + backend) | Per-topic key point grouping with `utterance_ids`; duration resolved deterministically in backend with Agenda/Inferred origin |
| Agenda-aware analysis | Deterministic topic breakdown, adherence %, skipped detection, timeline bar |
| Sentiment arc | Session-level tone progression in summary metadata |
| Optional translation mode | Toggle transcript-only mode for same-language meetings |
| Summary from file | Upload past transcript CSV → result loads in main Summary tab; backend does not mutate transcript/topic runtime state |
| Meeting insights + keyword index (v1) | Deterministic speaking balance / pace / health + clickable keyword chips in Summary |

---

## Phase 1 — Core Intelligence

### 1. Meeting performance insights

Compute purely from existing transcript data — no new agents or services needed.

- **Speaking balance**: per-speaker word count and share of total airtime/words. Show as bar chart. ✅ v1 shipped
- **Turn-taking**: number of speaker turns, average turn length, longest monologue. ✅ v1 shipped
- **Pace**: words per minute per speaker (timestamps already in transcript). ✅ v1 shipped
- **Topic drift**: flag segments where coach/topic agent detected off-agenda content.
- **Meeting health score**: composite 0–100 score with short recommendations (e.g. "One speaker dominated 80% of airtime"). ✅ v1 shipped
- Export in JSON and TXT summary. ✅ v1 shipped

### 2. Keyword / searchable index

We already extract `key_terms_defined` from the LLM. Add discoverability.

- Deduplicated keyword list from transcript + defined terms in summary runs. ✅ v1 shipped
- Click a keyword to jump to matching transcript lines (timestamp anchor). ✅ v1 shipped
- Searchable filter box on the Transcript tab.
- Export keyword list with definitions in summary JSON/TXT. ✅ v1 shipped

### 3. Voice recording

Product-critical: audio replay validates analytics quality and supports post-meeting review.

- Capture raw audio per session (not per speaker initially).
- Start recording when session starts; stop on session stop.
- Export as WAV/MP3 from the UI.
- Store locally (no cloud upload in v1).

---

## ⚙️ Cross-cutting gate: E2E browser smoke tests

**Must be complete before Phase 2 begins.**

- Automated browser tests (Playwright or Selenium) covering the critical user path:
  start session → transcript appears → stop → summary generated → export works.
- Cover modal flows: from-file upload, coach ask, topic configure.
- Run in CI on every PR.

---

## Phase 2 — Launch Readiness

### 4. Public trial flow

Required before sharing the app with external users.

- Invitation code onboarding (codes stored in env/config, not a full user DB).
- 10-minute session cap with visible countdown and controlled auto-stop.
- Per-code usage limits and expiration date.
- Basic abuse controls: rate limiting already exists; add IP-level session cap.
- Friendly expired/over-limit error page.

### 5. Proof assets

Needed to attract first external users.

- 2–3 minute product demo video (screen recording of a live session → summary flow).
- Before/after example: raw transcript vs generated summary.
- One-page outcome-focused product brief for target ICP.

---

## Phase 3 — Platform Expansion

### 6. STT provider / model flexibility

- Abstract speech provider behind a common event contract.
- Add support path for Nova-3 class models (higher accuracy, lower latency).
- Keep Azure Speech SDK as default; new providers are additive.

### 7. Multilingual support

- Expand analysis prompts beyond English-centric assumptions.
- Validate summary quality per language/locale (Arabic, French, Spanish as first targets).
- UI language detection hint — show language badge in transcript.

---

## Phase 4 — Knowledge-Aware Copilot

### 8. Workspace connectors

- SharePoint read-only connector as the first integration.
- Scheduled sync + incremental updates (no full live crawl in v1).
- Coach can retrieve relevant documents during a meeting.

### 9. Multi-datasource selection

- Per-meeting scope selection: no datasource / default workspace / selected source.
- UI dropdown in the Coach panel before or during a session.

### 10. Retrieval trust and controls

- Tenant/workspace permission boundaries enforced server-side.
- Source citations included in coach outputs.
- Admin view: indexed content list, sync status, last-updated timestamps.

---

## Phase 5 — Go-To-Market

### 11. Narrow ICP-first rollout

- Target one segment first (recruiting/interview coaching teams is the strongest fit).
- Collect structured feedback from first 10 users before broadening.

### 12. Trial-to-paid funnel

- Invite-only trial with a clear value moment: summary + action items + agenda score.
- Simple pricing tiers and usage boundaries.
- Upgrade prompt triggered at trial cap or on export of premium features.

---

## Engineering Notes

1. Keep summary/insight pipelines asynchronous — never block live translation.
2. Use feature flags to roll out new analytics incrementally.
3. Keep schema/contract checks between agents and orchestrators strict and versioned.
4. E2E smoke tests must pass before any Phase 2 work ships to external users.
