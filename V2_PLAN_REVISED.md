# Live Meeting Copilot V2 Plan (Revised)

Last revised: 2026-03-05

## 1) Executive Summary

V2 is a browser-first, cloud-hosted version of Live Meeting Copilot. The primary goal is to remove local installation friction while preserving translation, coaching, topic tracking, and summary features.

Core product promise:
- Open a URL and start using the app with no local Python setup.
- No virtual audio cable setup for standard usage.
- Real-time transcript with speaker diarization from Deepgram.
- Translation and AI features remain on Azure services.

Important correction:
- Primary transcript audio should bypass backend and stream browser -> Deepgram.
- Optional voice-profile matching can still send short audio snippets to backend when enabled.

## 2) Product Scope

### In scope for V2 GA
- Browser capture from microphone.
- Optional mixed capture mode (mic + shared tab/system audio where supported).
- Real-time transcript, translation, coach, topics, summary.
- Cloud deployment with secure auth and observability.

### Out of scope for V2 GA
- Native desktop app.
- Full mobile browser parity.
- Enterprise SSO and multi-tenant admin console.
- Guaranteed cross-session biometric identification accuracy.

## 3) Business Goals and Success Metrics

V2 should not ship based only on "it works on my machine." Ship only after measurable goals are met.

### Adoption metrics
- Setup-to-first-transcript median <= 3 minutes.
- First-session success rate >= 85%.
- Pilot user week-2 retention >= 40%.

### Experience metrics
- Partial transcript latency p95 <= 1.2s.
- Final transcript latency p95 <= 2.5s.
- WebSocket session failure rate <= 2%.

### Cost metrics
- Define a target COGS per active meeting hour before launch.
- Track COGS formula per session:
  - Deepgram STT cost
  - Azure Translator cost
  - Azure AI Foundry cost
- Require margin-positive pricing assumptions before public release.

### Security and trust metrics
- 0 critical security findings in pre-release review.
- 100% authenticated API usage in cloud mode.

## 4) Architecture (Corrected)

```text
BROWSER
  getUserMedia() for mic
  getDisplayMedia({audio:true}) for optional shared-audio mode
  Web Audio pipeline for mixing/resampling
  Deepgram WebSocket for realtime STT + diarization
  App WebSocket to backend for transcript event ingestion + AI outputs

BACKEND (FastAPI)
  /api/session/token      -> server-minted Deepgram temporary access token
  /ws                     -> bidirectional transcript/AI stream
  /api/voices/embed       -> optional embedding creation
  /api/voices/identify    -> optional profile matching
  Existing AI routes      -> coach/topics/summary and config/state

DEEPGRAM
  Browser streams audio directly to Deepgram realtime endpoint.
  Returns transcript segments and diarization metadata.

AZURE
  Translator for EN->AR
  AI Foundry for coach/topics/summary
```

Design principle:
- Keep AI orchestration in backend.
- Keep transcript audio transport direct from browser to STT provider.

## 5) Capture Modes and Browser Compatibility

Capture modes:
- `single`: microphone only (default).
- `mixed`: microphone + shared audio capture when browser supports it.
- `loopback_only`: shared audio only (demo/testing).

Default mode strategy:
- Default to `single`.
- Offer `mixed` only when capability check passes and user explicitly enables it.

Reason:
- This reduces first-run failure risk and support load on non-Chromium browsers.

## 6) Session and State Model

V2 must explicitly handle session state because speech service callbacks no longer drive backend state.

Required states:
- `idle`
- `starting`
- `listening`
- `stopping`
- `stopped`
- `error`

Required behavior:
- Backend must not assume transcripts imply session started.
- Client must send explicit start/stop control messages or call start/stop endpoints.
- Backend must keep current watchdog/finalization semantics.

## 7) API and Event Contract

### 7.1 HTTP endpoints

Keep current route naming where possible to minimize migration risk.

Existing routes to keep:
- `POST /api/start`
- `POST /api/stop`
- `POST /api/coach/ask`
- `POST /api/topics/analyze-now`
- `POST /api/summary/generate`

New routes:
- `POST /api/session/token`
- `POST /api/voices/embed`
- `POST /api/voices/identify`

### 7.2 Deepgram token endpoint

`POST /api/session/token`

Request:
```json
{}
```

Response:
```json
{
  "token": "dg_tmp_token",
  "expires_in": 600,
  "issued_at": 1760000000
}
```

Rules:
- Use Deepgram temporary token flow suitable for browser clients.
- Do not create full project keys per refresh cycle.
- Rate-limit this endpoint per user/session/IP.

### 7.3 WebSocket event schema (app <-> backend)

Client to server:
```json
{ "type": "status", "status": "listening", "running": true }
{ "type": "partial", "speaker": "speaker_0", "speaker_label": "Speaker", "en": "..." }
{ "type": "final", "speaker": "speaker_0", "speaker_label": "Speaker", "en": "...", "ts": 0.0, "start_ts": 0.0, "end_ts": 0.0, "duration_sec": 0.0 }
{ "type": "log", "level": "info", "message": "..." }
```

Server to client:
- Snapshot payload on connect.
- Transcript/translation updates.
- Coach/topics/summary updates.
- Status and error events.

Validation requirements:
- Reject oversize payloads.
- Reject unknown event types.
- Reject malformed timestamps and speaker fields.

## 8) Voice Profiles and Privacy

Voice profile matching is optional and should be disabled by default for first release.

Privacy model:
- Local-first storage in browser (versioned schema).
- Explicit user consent before enabling voice memory.
- "Clear voice profiles" action in UI.
- Optional profile export/import with user confirmation.

Legal model:
- Do not claim "GDPR-safe" without legal review.
- Treat embeddings as potentially sensitive personal data.
- Add privacy policy text before public launch.

Storage model:
- Use local storage schema versioning.
- Add TTL and stale profile cleanup.
- Add max profile count and max payload size.

## 9) Repository and Code Strategy

Recommended workflow:
- Build V2 in a long-lived `v2` branch first.
- Create `live-meeting-copilot-v2` repo only after alpha milestone if separation is still needed.

Reason:
- Keeps commit history and release tooling continuity.
- Lowers operational overhead during early iteration.

## 10) Expected Code Changes

This migration affects more than three files. Plan for medium-size refactor.

High-impact backend changes:
- `app/controller/__init__.py`: remove `SpeechService` wiring and add transcript ingestion path.
- `app/controller/session_manager.py`: start/stop semantics without speech service, preserve state machine.
- `app/api/websocket.py`: parse and route incoming transcript events.
- `app/api/routes.py`: add token and voice profile endpoints plus rate limits.
- `app/config.py`: add Deepgram settings and V2 runtime settings.
- `app/main.py`: startup checks and service initialization updates.

Frontend changes:
- Split current large `static/client.js` into focused modules:
  - `audio-capture.js`
  - `deepgram-client.js`
  - `voice-profiles.js`
  - `app.js` (orchestration)
- Update `static/index.html` for capture mode and profile UX.

## 11) Dependencies (Revalidated)

Backend additions:
```text
deepgram-sdk>=3.0
resemblyzer>=0.1.1
numpy>=1.24
scipy>=1.10
```

Frontend:
- No npm dependency required for MVP.
- Use native browser APIs.

Operational caution:
- `resemblyzer` adds heavier startup/runtime footprint.
- Budget for cold-start optimization and model warmup.

## 12) Security Requirements (Mandatory)

Before internet exposure:
- Require API auth token or equivalent auth in cloud mode.
- Restrict CORS to known origins.
- Apply endpoint rate limits:
  - `/api/session/token`
  - `/api/voices/embed`
  - `/api/voices/identify`
  - existing AI endpoints
- Enforce request size limits on upload/base64 payloads.
- Add structured audit logs for token minting and key actions.

## 13) Delivery Plan with Technical and Business Gates

## Phase 0 - Discovery and spikes (2-3 days)

Technical:
- Validate Deepgram temporary token flow in browser.
- Validate mixed-mode capture matrix on target OS/browser combinations.
- Validate Deepgram diarization quality on real meeting audio.

Business:
- Produce first COGS estimate from real audio sample sessions.
- Define launch KPI thresholds.

Exit gate:
- Proceed only if token flow and browser capture are stable enough for pilot.

## Phase 1 - Backend foundation (3-4 days)

Technical:
- Add Deepgram token endpoint with rate limiting.
- Refactor session lifecycle away from speech service ownership.
- Upgrade websocket to bidirectional transcript ingestion.

Business:
- Ensure cloud auth model is production-safe.
- Confirm operational logging visibility.

Exit gate:
- Backend handles transcript events reliably in staging.

## Phase 2 - Browser ingest and transcript path (4-5 days)

Technical:
- Implement `audio-capture.js` and `deepgram-client.js`.
- Stream Deepgram transcript events into backend websocket.
- Preserve transcript event shape expected by orchestration.

Business:
- Measure time-to-first-transcript and user drop-off.

Exit gate:
- End-to-end transcript and translation stable for 30-minute sessions.

## Phase 3 - AI feature integration and parity (3-4 days)

Technical:
- Confirm coach/topics/summary parity with V1 behavior.
- Validate watchdog, stop/finalize flows, and snapshot consistency.

Business:
- Validate pilot users still find coach/topics useful in browser flow.

Exit gate:
- Feature parity accepted by product owner.

## Phase 4 - Voice profiles (optional beta feature, 4-6 days)

Technical:
- Add optional profile enrollment and identification.
- Add confidence threshold tuning and fallback UX.

Business:
- Validate user trust and consent completion rates.
- Decide go/no-go for GA inclusion based on accuracy and privacy risk.

Exit gate:
- Enable by default only if quality and privacy criteria pass.

## Phase 5 - Hardening, cloud rollout, and observability (4-6 days)

Technical:
- Dockerize and deploy to Azure Container Apps or App Service.
- Add runtime dashboards and alerts.
- Add resilience tests (token failure, websocket reconnect, backend restart).

Business:
- Pilot rollout with support playbook.
- Verify COGS against target.

Exit gate:
- Production readiness review passed.

## 14) Testing Strategy

Automated tests:
- Unit tests for token endpoint, voice endpoints, event validation.
- Contract tests for websocket payload schemas.
- Integration tests for transcript -> translation -> AI flow.

Manual tests:
- Browser compatibility matrix test.
- Long-session reliability test (>= 60 minutes).
- Network-loss and reconnect test.
- Permission-denied and capture-failure UX test.

Quality baselines:
- No data loss in final transcript stream under normal network conditions.
- No unhandled exceptions in backend during 60-minute soak.

## 15) Cost and Packaging Strategy

V2 is cloud software, not local install software.

Distribution model:
- Host service URL for users.
- Optional release artifacts for self-hosting only.

Pricing model tasks:
- Define per-seat or per-usage pricing.
- Include STT + translation + AI model usage in gross margin model.
- Add cost guardrails in runtime config (max session length, optional feature throttles).

## 16) Release and Versioning Plan

Recommended version path:
1. `v2.0.0-alpha.1` (internal technical alpha)
2. `v2.0.0-beta.1` (pilot customers)
3. `v2.0.0` (public GA)

Version bump policy:
- Patch for fixes.
- Minor for backward-compatible features.
- Major for breaking contract changes.

## 17) Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Token minting misuse or rate abuse | Service outage or unexpected cost | Strong rate limits, auth, and auditing |
| Browser capture incompatibility | User activation drop | Default to `single`, capability checks, guided UX |
| Session state mismatch after speech-service removal | Transcript drops or stuck states | Explicit state machine and protocol tests |
| Voice profile privacy concerns | Legal and trust risk | Opt-in, consent, retention controls, legal review |
| Realtime latency regressions | Poor user experience | p95 latency SLOs and performance telemetry |
| COGS higher than expected | Business model risk | Early cost measurement and usage guardrails |

## 18) Open Decisions (Resolve Early)

1. Should V2 stay in this repo branch or move immediately to a new repo?
2. Will voice profiles be GA or beta-only behind a feature flag?
3. What are target launch geographies and compliance obligations?
4. What is the exact pricing model and target gross margin?
5. What auth model is required for non-localhost production usage?

## 19) Immediate Next Steps (Next 5 Working Days)

1. Implement Phase 0 spikes and document results.
2. Finalize API/event contract and schema validation rules.
3. Refactor backend session lifecycle to remove direct speech service dependency.
4. Build minimal Deepgram browser ingest path with one stable capture mode.
5. Run first pilot test and collect KPI baseline data.
