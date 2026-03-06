# Live Meeting Copilot — V2 Build Plan

## What V2 Is

A fully browser-based, cloud-hosted version of the meeting copilot.
- Zero installation for end users (open a URL, done)
- No VB-Cable, no drivers, no Python setup
- Deepgram Nova-3 for STT + speaker diarization
- Cross-session voice memory via local voice profiles
- Backend is a lightweight intelligence API (translation + AI only)
- Live transcript audio streams browser → Deepgram directly (backend never sees it)
- Short audio samples (5-10s) sent to backend only for optional voice profile matching

---

## Product Scope

### In scope for V2 GA

- Browser capture from microphone (all browsers).
- Optional mixed capture mode: mic + system audio (Chrome/Edge only).
- Real-time transcript with speaker diarization.
- Translation (EN → AR) and AI features: coach, topics, summary.
- Cross-session voice memory with explicit user consent.
- Activation key auth — issued manually via email for pilot users.
- Cloud deployment (Azure Container Apps) with HTTPS.

### Out of scope for V2 GA

- Native desktop app.
- Full mobile browser parity.
- Enterprise SSO or multi-tenant admin console.
- Guaranteed cross-session biometric identification accuracy.
- Self-service signup or payment flow.

---

## Business Goals and Success Metrics

Ship only after measurable goals are met.

### Adoption metrics

- Setup-to-first-transcript median <= 3 minutes.
- First-session success rate >= 85%.
- Pilot user week-2 retention >= 40%.

### Experience metrics

- Partial transcript latency p95 <= 1.2s.
- Final transcript latency p95 <= 2.5s.
- WebSocket session failure rate <= 2%.

### Cost metrics

- Define target COGS per active meeting hour before launch.
- Track per-session: Deepgram STT cost + Azure Translator cost + Azure AI Foundry cost.
- Require margin-positive pricing assumption before public release.

### Security metrics

- 0 critical findings in pre-release review.
- 100% authenticated API usage in cloud mode.

---

## Architecture Overview

```
BROWSER
  getUserMedia()          → mic (your voice)
  getDisplayMedia(audio)  → system audio (remote party, Chrome only)
  Web Audio API           → mix + resample to 16kHz mono PCM

  Step 1: POST /api/session/token  → backend issues Deepgram temp token (TTL 30s, default)
  Step 2: Open WS to Deepgram directly (wss://api.deepgram.com/v1/listen)
  Step 3: Stream PCM audio → Deepgram returns diarized transcripts
  Step 4: Forward transcripts to backend WS → backend returns translation + AI

BACKEND (FastAPI, cloud-hosted)
  POST /api/auth/activate       → validate activation key, return JWT
  GET  /api/auth/me             → current usage + caps
  POST /api/session/token       → create Deepgram temp token, return to browser
  WS   /ws                      → receive transcripts, return translation + AI results
  POST /api/voices/embed        → run resemblyzer on audio chunk, return embedding
  POST /api/voices/identify     → cosine similarity vs stored embeddings, return name
  POST /api/coach/ask           → manual coach trigger (Quick Coach button or typed question)
  POST /api/topics/analyze-now  → on-demand topic analysis (manual trigger only, no background firing)
  POST /api/summary/generate    → summary (unchanged from v1)

DEEPGRAM (external)
  Receives audio stream directly from browser
  Returns: transcript, speaker (int), speaker_confidence, start, end, is_final

AZURE (external, unchanged)
  Azure Translator → EN→AR
  Azure AI Foundry → coach, topics, summary
```

---

## Capture Modes

| Mode | Mic | System Audio | Use Case |
|---|---|---|---|
| `single` | getUserMedia | — | In-person, everyone around one mic |
| `mixed` | getUserMedia | getDisplayMedia(audio) | Remote calls (Teams/Zoom) |
| `loopback_only` | — | getDisplayMedia(audio) | Demo / testing |

Default: `single`. Offer `mixed` only after capability check passes and user explicitly enables it.
Reason: reduces first-run failure risk and support load on non-Chromium browsers.

Browser compatibility:
- Chrome: full support (getUserMedia + getDisplayMedia with audio)
- Firefox: getUserMedia only → falls back to `single`
- Safari: getUserMedia only → falls back to `single`
- Edge: same as Chrome (Chromium-based)

---

## Session State Machine

Backend must track explicit session state. Browser sends control messages — backend does not infer state from transcript arrival.

States:

- `idle` — no session active
- `starting` — client sent start, backend initializing
- `listening` — actively receiving transcripts
- `stopping` — client sent stop, backend finalizing
- `stopped` — session complete, summary ready
- `error` — unrecoverable error, requires restart

Required behavior:

- Backend must not assume transcript events imply session started.
- Client must send explicit `session_control` messages (`action: start` / `action: stop`).
- Backend must keep current watchdog/finalization semantics.

WebSocket control event (client → server):
```json
{ "type": "session_control", "action": "start" }
{ "type": "session_control", "action": "stop" }
```

---

## Speaker Management

### Within a session
- Deepgram assigns Speaker 0, 1, 2... consistently within a session
- On first utterance from a new speaker → show quick-assign popup in UI
- User types name → assigned for the rest of the session
- If voice profile exists in localStorage → auto-assign (skip popup)

### Cross-session voice memory
- After user assigns a name to a speaker:
  1. Browser sends 5-10s audio chunk to `POST /api/voices/embed`
  2. Backend runs resemblyzer → returns 256-float embedding
  3. Browser stores in localStorage: `{ "Rajab": [0.23, -0.11, ...] }`
- On session start, for each new speaker Deepgram identifies:
  1. Browser collects first 5s of their audio
  2. POST /api/voices/identify with audio + stored embeddings dict
  3. Backend returns best match name + confidence
  4. If confidence > 0.85 → auto-label. If < 0.85 → show quick-assign popup
- Backend is stateless — no biometric data stored server-side (privacy by design)

### Speaker label output format (same as v1)
```json
{
  "type": "final",
  "speaker": "speaker_0",
  "speaker_label": "Rajab",
  "en": "Good morning, how are you?",
  "ar": "صباح الخير، كيف حالك؟",
  "ts": 1234567890.123
}
```

---

## WebSocket Event Schema (Browser ↔ Backend)

### Client → Server

```json
{ "type": "session_control", "action": "start" }
{ "type": "session_control", "action": "stop" }
{ "type": "partial", "speaker": "speaker_0", "speaker_label": "Speaker", "en": "..." }
{ "type": "final", "speaker": "speaker_0", "speaker_label": "Speaker", "en": "...", "ts": 0.0, "start_ts": 0.0, "end_ts": 0.0, "duration_sec": 0.0 }
{ "type": "log", "level": "info", "message": "..." }
```

Note: client does NOT send `status` events. Server owns all state transitions.
Client sends only: `session_control` (to trigger transitions) and `partial`/`final`/`log` (data).
Server derives its own state from control messages — never trusts client status claims.

### Server → Client

- Snapshot payload on connect (full state for reconnect recovery).
- Transcript + translation updates.
- Coach / topics / summary updates.
- Status and error events.

### Validation requirements (backend must enforce)

- Reject payloads over size limit (e.g. 64KB).
- Reject unknown `type` values.
- Reject malformed timestamps and speaker fields.
- Reject `session_control` when state transition is invalid.

---

## Deepgram Token Lifecycle

Strategy (locked): use short-lived tokens so the Deepgram API key never reaches the browser.
**VERIFIED** against Deepgram docs (2026-03-05).

- Endpoint: `POST https://api.deepgram.com/v1/auth/grant`
- Default TTL: 30s. Maximum TTL: 3600s. We use default (30s) — no need to specify longer.
- Response field: `access_token` (JWT string)
- Required API key permission: Member or higher
- NOT `/v1/keys` (creates permanent project keys — wrong for this use case)

**Key finding (verified):** The Deepgram WebSocket connection stays open past token expiry.
The token is only validated at connection establishment. Once the WS handshake completes,
the connection persists indefinitely regardless of token TTL.

Lifecycle:

- Backend mints temp token (30s TTL) → browser uses it to open Deepgram WebSocket
- WebSocket stays open for the entire meeting session (no token rotation needed)
- Token is re-minted only when a new WebSocket connection is opened (reconnect after drop)
- If connection drops → client fetches new token → opens new Deepgram WS → resumes

**Removed:** proactive 45s rotation timer and double-buffer pattern — unnecessary complexity.
Reconnect on drop is the only case requiring a new token mint.

---

## Activation Key Auth

For pilot: users contact you outside the app → you email them a key.

Key format: `LMCP-XXXX-XXXX-XXXX-XXXX` (generated via `secrets.token_hex(8)`)

Keys are never stored plaintext. Store SHA-256 hash of the key + last 4 chars for display.

```python
import hashlib, secrets
raw_key = "LMCP-" + "-".join(secrets.token_hex(2).upper() for _ in range(4))
key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
key_last4 = raw_key[-4:]
# Store key_hash + key_last4 in DB. Raw key only shown once to the user.
# Verification: hashlib.sha256(submitted_key.encode()).hexdigest() == stored_hash
```

Each key record in DB:
```json
{
  "key_hash": "sha256hexstring...",
  "key_last4": "G7H8",
  "email": "user@example.com",
  "expires_at": "2026-06-05T00:00:00Z",
  "plan": "pilot",
  "session_minutes_cap": 600,
  "session_minutes_used": 0,
  "ai_calls_cap": 300,
  "ai_calls_used": 0,
  "summary_calls_cap": 20,
  "summary_calls_used": 0,
  "deepgram_token_calls_cap": 100,  // ~1 mint per session start + reconnects; 10-20 sessions × 2-5 reconnects
  "deepgram_token_calls_used": 0,
  "is_active": true
}
```

Auth flow:

1. User enters key in UI
2. `POST /api/auth/activate { "key": "LMCP-..." }` → validates key → returns JWT (8h TTL)
3. All subsequent requests carry JWT in `Authorization` header
4. Per-endpoint middleware checks quota before executing

Security:

- Rate-limit `/api/auth/activate` to 5 req/min per IP (brute force protection)
- Log all usage per key — key sharing shows up as usage spikes
- `POST /api/auth/revoke` admin endpoint to kill a key
- `scripts/generate_key.py` CLI script for key generation

Future: Stripe webhook → auto-generate + email key (data model unchanged, just issuance trigger).

### Quota persistence semantics

Storage: SQLite for MVP (single-instance), Postgres when scaling.

Atomic increment (SQLite):

```sql
UPDATE keys
SET ai_calls_used = ai_calls_used + 1
WHERE key_hash = ? AND ai_calls_used < ai_calls_cap AND is_active = 1
```

If `rowcount == 0` → quota exceeded → return HTTP 429.

Rules:

- All `_used` counters increment atomically — no read-modify-write in Python.
- No counter resets — caps are lifetime limits. **Pilot-only business policy.** Future plans may add monthly resets; implement as a separate `reset_period` field + scheduled job, not a code change.
- Quota check happens in middleware before the handler executes.
- Session minutes tracked via session start/stop timestamps, not per-request.
- Race condition: multiple concurrent requests from same key are safe because SQL `UPDATE ... WHERE` is atomic in SQLite with WAL mode enabled.

---

## Voice Profile Privacy Model

Voice profile matching is optional and disabled by default.

### Privacy model

- Local-first storage in browser (versioned schema).
- Explicit user consent before enabling voice memory.
- "Clear voice profiles" action in UI.
- Optional profile export/import with user confirmation.

### Legal model

- Do not claim "GDPR-safe" without legal review.
- Treat embeddings as potentially sensitive personal data.
- Add privacy policy text before public launch.

### Storage model

```json
{
  "version": 1,
  "profiles": {
    "Rajab": {
      "embedding": [0.23, -0.11, "...256 floats..."],
      "created": "2026-03-05T10:00:00Z",
      "last_seen": "2026-03-05T10:00:00Z",
      "sessions": 3
    }
  }
}
```

- Schema versioning for future migrations.
- TTL: auto-delete profiles not seen in 90 days.
- Max 20 profiles, max 512KB total localStorage budget.
- Stale profile cleanup runs on app load.

---

## Repository Structure

New repo: `live-meeting-copilot-v2`

```
live-meeting-copilot-v2/
├── .env.example
├── .env
├── requirements.txt
├── Dockerfile
├── app/
│   ├── main.py                        MODIFIED  (add token + voice endpoints, remove speech init)
│   ├── config.py                      MODIFIED  (add DEEPGRAM_API_KEY, remove Azure Speech fields)
│   ├── api/
│   │   ├── auth.py                    NEW       (activation key validation, JWT issue)
│   │   ├── routes.py                  MODIFIED  (add /session/token, /voices/embed, /voices/identify)
│   │   └── websocket.py               MODIFIED  (receives transcript events from browser, not from speech service)
│   ├── controller/
│   │   ├── broadcast_service.py       COPY from v1 (unchanged)
│   │   ├── coach_orchestrator.py      MODIFIED  (remove auto-trigger; handle explicit POST /api/coach/ask only)
│   │   ├── config_store.py            COPY from v1 (unchanged)
│   │   ├── session_manager.py         MODIFIED  (remove SpeechService dependency, accept transcript events via WS)
│   │   ├── summary_orchestrator.py    COPY from v1 (unchanged)
│   │   ├── topic_orchestrator.py      MODIFIED  (remove background timer; handle on-demand POST /api/topics/analyze-now only)
│   │   └── transcript_store.py        COPY from v1 (unchanged)
│   └── services/
│       ├── coach.py                   COPY from v1 (unchanged)
│       ├── meeting_insights.py        COPY from v1 (unchanged)
│       ├── summary.py                 COPY from v1 (unchanged)
│       ├── topic_summary.py           COPY from v1 (unchanged)
│       ├── topic_tracker.py           COPY from v1 (unchanged)
│       ├── translation_pipeline.py    COPY from v1 (unchanged)
│       └── voice_profiles.py          NEW (resemblyzer embed + cosine identify)
│
│   REMOVED from v1:
│       services/speech.py             (replaced by browser audio capture)
│       utils/audio_devices.py         (no local audio enumeration needed)
│
└── static/
    ├── index.html                     MODIFIED  (add capture mode UI, speaker assign popup)
    ├── deepgram-client.js             NEW       (token fetch, WS to Deepgram, reconnect on drop)
    ├── audio-capture.js               NEW       (getUserMedia, getDisplayMedia, Web Audio mixer)
    ├── voice-profiles.js              NEW       (localStorage CRUD, embed/identify API calls)
    └── app.js                         MODIFIED  (wire audio-capture → deepgram-client → backend WS)
```

---

## New Dependencies

### Backend (requirements.txt additions)
```
httpx>=0.27                # direct HTTP call to /v1/auth/grant (no deepgram-sdk needed)
resemblyzer>=0.1.1         # voice embedding extraction
numpy>=1.24                # cosine similarity
scipy>=1.10                # audio resampling for resemblyzer input
python-jose>=3.3           # JWT for activation key auth
```

### Frontend (no npm — vanilla JS)
No new JS dependencies. Uses native browser APIs:
- `navigator.mediaDevices.getUserMedia()`
- `navigator.mediaDevices.getDisplayMedia({ audio: true })`
- `AudioContext`, `AudioWorkletNode`
- `WebSocket`
- `localStorage`

---

## New Backend Endpoints

### POST /api/auth/activate
```
Request:  { "key": "LMCP-A1B2-C3D4-E5F6-G7H8" }
Response: { "token": "eyJ...", "expires_in": 28800 }
          400 if key invalid/expired/over quota

Rate limit: 5 req/min per IP
```

### GET /api/auth/me

```
Response: {
  "email": "user@example.com",
  "plan": "pilot",
  "expires_at": "2026-06-05T00:00:00Z",
  "usage": { "session_minutes": 42, "ai_calls": 15, "summary_calls": 2, "deepgram_token_calls": 8 },
  "caps":  { "session_minutes": 600, "ai_calls": 300, "summary_calls": 20, "deepgram_token_calls": 100 }
}
```

### POST /api/session/token
```
Request:  { }  (authenticated — JWT required)
Response: { "token": "eyJ...", "expires_in": 30 }
  # "token" here is Deepgram's access_token — we rename it to avoid exposing Deepgram terminology

Backend action (verified against Deepgram docs 2026-03-05):
  # POST https://api.deepgram.com/v1/auth/grant
  # No body needed — default TTL is 30s, sufficient for browser handshake
  # Deepgram response field is "access_token"; we map it to "token" in our response
  response = httpx.post(
      "https://api.deepgram.com/v1/auth/grant",
      headers={"Authorization": f"Token {settings.deepgram_api_key}"},
  )
  response.raise_for_status()
  return {"token": response.json()["access_token"], "expires_in": 30}

Rate limit: 30 req/min per user
```

### POST /api/voices/embed
```
Request:  multipart/form-data  { audio: <wav bytes>, sample_rate: 16000 }
Response: { "embedding": [0.23, -0.11, ...] }  # 256 floats

Backend action:
  encoder = GE2EEncoder()  # singleton — load once at startup
  wav = preprocess_wav(audio_bytes)
  embedding = encoder.embed_utterance(wav)
  return embedding.tolist()

Max payload: 5MB
```

### POST /api/voices/identify
```
Request:  {
    "audio": <base64 wav>,
    "sample_rate": 16000,
    "profiles": { "Rajab": [0.23, ...], "Noor": [0.45, ...] }
  }
Response: { "name": "Rajab", "confidence": 0.94 }
          { "name": null, "confidence": 0.31 }  # if no match above threshold

Backend action:
  embed new audio → cosine similarity vs each profile → return best match
  threshold: 0.85

Max payload: 10MB (profiles dict can be large)
```

---

## Coach and Topics — AI Feature Design

### Coach: fully manual trigger only

Coach fires only when the user explicitly requests it. There is no automatic trigger.

Two modes — same endpoint `POST /api/coach/ask`, same request shape:

```
Request:
{
  "context": [ ...new transcript segments not yet sent to coach... ],
  "question": null | "typed question"
}

Response:
{
  "answer": "...",
  "mode": "auto" | "direct"
}
```

Mode `question: null` — **Quick Coach button**:
- User clicks "Coach" button in UI.
- Client sends `transcript[last_coach_sent_index:]` as `context`.
- AI reads the context and decides: if a question was asked → answer it; otherwise → give relevant hints or observations.
- This replaces any automatic post-utterance trigger.

Mode `question: "..."` — **Typed question** (existing behavior):

- User types a question in the input field and submits.
- AI answers that specific question using the meeting context.

Client tracking:

- Client sends `transcript[last_coach_sent_index:]` as `context` on each call.
- After a successful response the client advances its local index to `transcript.length`.
- On reconnect or tab reload the client reads `last_coach_sent_index` from the WS snapshot (server
  is the authoritative source — see below).

Server-side index tracking (authoritative):

- `SessionContext` stores `coach_last_sent_index: int` (starts at 0).
- On each `/api/coach/ask` call the server records the current transcript length as the new index.
- The snapshot payload sent on WS connect includes `coach_last_sent_index` so a reconnected client
  can resume without re-sending already-processed segments.

Server-side context truncation:

- The server accepts the `context` array from the client but caps it at **50 segments** before
  sending to the LLM. If the client sends more, the server takes the most recent 50.
- This prevents runaway token costs on long meetings and keeps response latency predictable.
- 50 segments ≈ 5-10 minutes of typical meeting dialogue — sufficient context for meaningful
  coaching without including hour-old conversation.

Rationale: no speaker-side auto-trigger means no false positives, no speaker identity tracking needed,
lower cost, user stays in control of when coach activates.

### Topics: on-demand only (no background orchestrator)

`TopicOrchestrator` periodic auto-firing is removed. Topic analysis runs only when the user
explicitly requests it.

What stays:

- Topic definitions in `RuntimeConfig` (user-configurable topic list).
- `POST /api/topics/analyze-now` — on-demand endpoint, called manually by user or from summary flow.
- Topic definitions are injected as context into the summary prompt (so summary is topic-aware
  even without a separate topic call).

What is removed:

- Background interval timer in `topic_orchestrator.py`.
- Auto-trigger logic based on transcript length or time elapsed.

The `topic_orchestrator.py` file is kept but reduced to: handle the `/api/topics/analyze-now`
request, run the LLM call, and return results. No scheduling, no background task.

Rationale: summary agent already covers the same ground at end-of-meeting. Real-time topic
classification was imprecise and added cost without proportional value.

### Quota: split ai_calls_cap + protected summary_calls_cap

Coach and topics share `ai_calls_cap` (pilot default: 300). Heavy coach use cannot exhaust this
and starve the end-of-meeting summary because summary has its own separate `summary_calls_cap`
(pilot default: 20). Each cap uses an independent atomic SQL increment — summary quota is never
consumed by coach or topics calls.

---

## Modified: session_manager.py

V1: SpeechService fires events → session_manager.handle_speech_event()
V2: Browser WebSocket fires events → session_manager.handle_speech_event()

The event format is IDENTICAL. Session manager does not need to know the source.

```python
# V1 flow (removed):
# speech_service.on_event → handle_speech_event(payload)

# V2 flow (new):
# websocket.py receives transcript from browser → handle_speech_event(payload)
```

The payload format the browser sends after processing Deepgram output:
```json
{
  "type": "final",
  "speaker": "speaker_0",
  "speaker_label": "Rajab",
  "en": "Good morning.",
  "ar": "",
  "ts": 1234567890.123,
  "start_ts": 1234567888.1,
  "end_ts": 1234567890.1,
  "duration_sec": 2.0
}
```
Same shape as v1 — all downstream code unchanged.

---

## Modified: websocket.py

V1: WebSocket is one-way (server → client only, sink loop for keep-alive)
V2: WebSocket is bidirectional
  - Client → server: transcript events from Deepgram
  - Server → client: translation results, coach, topics, status

```python
async def websocket_endpoint(websocket: WebSocket):
    await controller.broadcast_svc.connect(websocket)
    await websocket.send_text(json.dumps(controller.snapshot()))
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            # Route to session_manager just like speech events in v1
            controller.session.handle_speech_event(payload)
    except WebSocketDisconnect:
        controller.broadcast_svc.disconnect(websocket)
```

---

## New: audio-capture.js

Responsibilities:
1. Open mic stream via getUserMedia
2. Open system audio stream via getDisplayMedia (mode = mixed)
3. Mix both via AudioContext (gain nodes → merger → destination)
4. Resample to 16kHz mono
5. Extract raw PCM via AudioWorkletNode
6. Emit PCM chunks (128ms each) to deepgram-client.js

```javascript
// AudioWorklet extracts Float32 PCM
// Convert to Int16 PCM (Deepgram expects linear16)
// Emit as ArrayBuffer chunks
// Fallback: ScriptProcessorNode for local HTTP testing (AudioWorklet requires HTTPS)
```

---

## New: deepgram-client.js

Responsibilities:

1. POST /api/session/token → get temp token (30s TTL, valid only at WS handshake)
2. Open WebSocket to `wss://api.deepgram.com/v1/listen?model=nova-3&diarize=true&punctuate=true&interim_results=true&encoding=linear16&sample_rate=16000&channels=1`
3. Receive audio chunks from audio-capture.js → send to Deepgram
4. Parse Deepgram responses → emit transcript events
5. On WS disconnect → fetch new token → reopen WS → resume (reconnect only, no proactive rotation)
6. Surface errors to app.js

Note: no 45s proactive refresh timer needed. Deepgram WS stays open past token TTL.
Token is only required at handshake — once connected, connection is independent of token.

Deepgram response parsing:
```javascript
// is_final=true → emit "final" event
// is_final=false → emit "partial" event
// speaker field (int) → "speaker_0", "speaker_1", etc.
// majority-mode speaker assignment: collect per-word speaker → pick mode for utterance
```

---

## New: voice-profiles.js

Responsibilities:
1. CRUD for localStorage: `lmc_voice_profiles` key
2. On new speaker detected → collect 5s audio buffer
3. POST /api/voices/identify with audio + stored profiles → auto-assign if confidence > 0.85
4. Show quick-assign popup if no match
5. After user assigns name → POST /api/voices/embed → store embedding in localStorage
6. Stale profile cleanup on load (TTL 90 days)
7. Export/import profiles (nice-to-have)

---

## New: voice_profiles.py (backend service)

```python
class VoiceProfileService:
    def embed(self, audio_bytes: bytes, sample_rate: int) -> list[float]:
        """Run resemblyzer GE2EEncoder on audio, return 256-float embedding."""

    def identify(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        profiles: dict[str, list[float]],
        threshold: float = 0.85,
    ) -> tuple[str | None, float]:
        """Embed audio, cosine-compare to profiles, return (name, confidence)."""
```

No state. Stateless service — no DB, no file I/O. All profile storage is client-side.
GE2EEncoder loaded as singleton at startup — avoids 17MB model reload per request.

---

## config.py Changes

```python
class Settings(BaseSettings):
    # Existing
    ai_services_key: str = Field(default="", alias="AZURE_AI_SERVICES_KEY")
    ai_services_region: str = Field(default="", alias="AZURE_AI_SERVICES_REGION")

    # New
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")
    # deepgram_project_id: not needed — /v1/auth/grant only requires the API key header
    jwt_secret: str = Field(default="", alias="JWT_SECRET")

    # Optional: keep for fallback or remove entirely
    # project_endpoint, guidance_agent_name, etc. — unchanged

# RuntimeConfig additions
class RuntimeConfig(BaseModel):
    # Existing fields unchanged
    ...
    # New
    dg_capture_mode: Literal["single", "mixed", "loopback_only"] = "single"
    dg_speaker_threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    voice_profiles_enabled: bool = False  # opt-in, disabled by default
```

---

## Security Requirements (Mandatory Before Cloud Deployment)

- Require JWT auth on all endpoints except `/api/auth/activate`.
- Restrict CORS to known origins only.
- Apply rate limits:
  - `/api/auth/activate`: 5 req/min per IP
  - `/api/session/token`: 30 req/min per user
  - `/api/voices/embed`: 20 req/min per user
  - `/api/voices/identify`: 20 req/min per user
  - `/api/coach/ask`, `/api/topics/analyze-now`, `/api/summary/generate`: 60 req/min per user
- Enforce request size limits: 5MB for embed, 10MB for identify, 64KB for WS messages.
- Add structured audit logs: token minting, key activation, key revocation.
- HTTPS required for production (getUserMedia demands it).

---

## Build Sequence

Note: original 4-day estimate was too optimistic for this scope (auth + quotas + realtime + cloud).
Realistic estimate below. Adjust based on available daily hours.

### Phase 1 — Backend skeleton (Days 1-2)

1. Create new repo `live-meeting-copilot-v2`
2. Copy unchanged files from v1
3. Update config.py (add Deepgram + JWT keys)
4. Add activation key store (SQLite) + `/api/auth/activate` + `/api/auth/me` + quota middleware
5. Add `POST /api/session/token` endpoint (VERIFY Deepgram token endpoint first)
6. Modify session_manager.py (remove SpeechService, add 6-state machine)
7. Modify websocket.py (bidirectional + session_control routing)
8. Verify: backend starts, token endpoint returns valid Deepgram token, quota increments atomically

### Phase 2 — Browser audio capture (Days 2-3)

1. Write audio-capture.js (getUserMedia + getDisplayMedia + AudioWorklet mixer)
2. Write deepgram-client.js (token fetch + WS + PCM streaming + reconnect on drop)
3. Test: open browser, verify transcripts appear from Deepgram
4. Verify partial and final events correctly parsed with speaker IDs

### Phase 3 — Wire transcript to backend (Day 3)

1. Modify app.js to forward Deepgram transcripts to backend WS
2. Verify translation appears (Arabic output)
3. Verify coach/topics triggers work
4. Full end-to-end: speak → transcript → Arabic translation

### Phase 4 — Voice profile endpoints (Day 4)

1. Add `POST /api/voices/embed` and `/identify` endpoints
2. Add voice_profiles.py service (resemblyzer + cosine similarity)
3. Write voice-profiles.js (localStorage CRUD + embed/identify calls)
4. Add quick-assign popup to UI
5. Test: new speaker → popup → name assigned → known speaker auto-labeled

### Phase 5 — Hardening (Day 5)

1. Add rate limits to all endpoints
2. Test WS reconnect (drop connection mid-session, verify transcript resumes)
3. Test network-loss recovery
4. 60-minute soak test (no crashes, no data loss)

### Phase 6 — Cloud deployment (Days 6-7)

1. Write Dockerfile
2. Deploy to Azure Container Apps (or App Service)
3. Configure environment variables + HTTPS
4. Test full flow from browser over internet
5. Verify quota enforcement works in production

---

## Testing Strategy

### Tier 1 — Backend E2E (automated, CI, mocked externals) — build alongside Phase 1

High ROI. Catches real regressions in auth, quota, WS pipeline, and AI orchestration without
needing a browser, real audio, or paid API calls.

Tool: `pytest` + `httpx` (async HTTP) + `websockets` library.
Mocks: Deepgram token endpoint, Azure Translator, Azure AI Foundry (via `respx` / `unittest.mock`).

Test flow:

```text
1. POST /api/auth/activate          → get JWT
2. POST /api/session/token          → verify token minted (mocked Deepgram returns fake token)
3. WS connect /ws
4. Send: { "type": "session_control", "action": "start" }
5. Send: series of partial + final transcript events (pre-written text fixture)
6. Assert: translation events arrive on WS (mocked Azure returns fixed Arabic)
7. POST /api/coach/ask (question: null)  → assert response shape, assert quota incremented
8. POST /api/topics/analyze-now          → assert response shape
9. POST /api/summary/generate            → assert response shape, assert summary_calls_used++
10. Send: { "type": "session_control", "action": "stop" }
11. Assert: session state = "stopped"
12. Reconnect WS → assert snapshot includes coach_last_sent_index
```

Auth edge cases:

- Invalid key → 400.
- Expired key → 400.
- Quota exhausted → 429 (test by setting ai_calls_used = ai_calls_cap before request).
- Summary quota protected: exhaust ai_calls_cap → coach returns 429, summary still works.

Fixture file: `tests/fixtures/meeting_transcript.json` — 20 pre-written final segments from a
scripted conversation. Used as input for WS send loop. No audio, no Deepgram, no cost.

### Tier 2 — Browser smoke test (Playwright + golden audio) — post-beta only

Skip for pilot. The browser JS (audio-capture.js, deepgram-client.js) is simple enough that manual
testing finds bugs faster than maintaining a Playwright suite.

Revisit after beta when: JS surface grows, team > 1 developer, or regressions start occurring in
browser-side code. At that point use Playwright with `getUserMedia` override to inject
`tests/fixtures/meeting.wav` and assert on known transcript content.

### Tier 3 — Real-services release validation (manual checklist, pre-release)

Not automated. Run manually before each release using a pre-recorded 3-minute WAV.

Checklist:

- [ ] Play WAV → transcript appears in correct language
- [ ] Arabic translation displays correctly
- [ ] Quick Coach button → response arrives in < 5s
- [ ] Summary generates at end
- [ ] WS reconnect after drop — transcript resumes, no data lost
- [ ] 60-minute soak — no crashes, no memory growth

### Quality baselines

- No data loss in final transcript stream under normal network conditions.
- No unhandled exceptions in backend during 60-minute soak.
- Quota enforcement: 0 calls succeed after cap exhausted.

---

## Multi-User Session Isolation (Critical — Day 1 Requirement)

The v1 backend has a single global `controller` object. In cloud multi-user mode this is a
correctness bug, not just a performance concern: without isolation, User A sees User B's
transcripts, coach responses, and status events.

### Required: per-session context

```python
# DO NOT carry this pattern from v1:
controller = Controller()  # single global

# V2: keyed by the user's activation key_id (extracted from JWT)
active_sessions: dict[str, SessionContext] = {}

class SessionContext:
    broadcast_svc: BroadcastService   # isolated — only this user's websockets
    session_manager: SessionManager   # isolated state machine
    translator: TranslationPipeline   # isolated queue
    transcript_store: TranscriptStore # isolated transcripts
    coach_last_sent_index: int = 0    # authoritative index; sent in snapshot on reconnect
    # NOTE: me_speaker_id is intentionally absent.
    # Coach is manual-trigger only — no per-user speaker identity needed for auto-firing.
```

Each WebSocket connection looks up its own `SessionContext` by `key_id`. Broadcast only
fans out to that user's own sockets (browser tab + optional secondary client).

### Session lifecycle

- Session context created on first WebSocket connect from a key.
- Context persists for the duration of the meeting session.
- Context cleaned up after `stopped` state + configurable idle timeout (e.g. 5 minutes).
- If user reconnects during a session → attach to existing context (transcript recovery).

### Concurrency limits

- Max 1 active meeting session per activation key at a time.
- Max N concurrent active sessions total per replica (N = CPU-tuned, start with 10).
- `POST /api/voices/embed` and `/identify`: semaphore-limited (max 4 concurrent, resemblyzer is CPU-heavy).

### Scalability progression

| Stage | Users | State strategy | Replicas |
| --- | --- | --- | --- |
| MVP pilot | 1-20 | Per-session dict in memory + SQLite | 1 |
| Growth | 20-100 | Postgres for persistence, in-memory sessions | 1 (larger) |
| Multi-replica | 100+ | Redis for ephemeral session state + Postgres | N |

Redis becomes necessary **only when running more than 1 replica**. Single-replica with proper
session isolation can handle the pilot load safely. Do not add Redis prematurely.

When Redis is added (future):

- `active_sessions` dict → Redis hash (keyed by `key_id`, TTL = session timeout)
- Rate-limit counters → Redis atomic INCR
- WebSocket presence/rooms → Redis pub/sub
- SQL (Postgres) stays for: users, keys, quotas, audit history

---

## Key Technical Decisions (locked in)

| Decision | Choice | Reason |
|---|---|---|
| STT provider | Deepgram Nova-3 | Best diarization, 3x cheaper than Azure |
| Auth to Deepgram | Temp tokens (30s TTL, default) | API key never exposed to browser |
| Audio path | Browser → Deepgram direct | No audio proxying through backend |
| System audio capture | getDisplayMedia (Chrome) | No VB-Cable needed |
| Voice embeddings | resemblyzer on backend | Stateless, privacy-preserving |
| Voice profile storage | localStorage | No server biometric storage |
| Voice profiles default | Disabled | Opt-in only; consent first |
| Token refresh | On reconnect only (WS persists past TTL) | No proactive rotation needed |
| User auth | Activation key → JWT | Simple for pilot, upgradeable to Stripe |
| Frontend framework | Vanilla JS | No build step, same as v1 |
| Backend framework | FastAPI | Same as v1, no change |
| Translation | Azure Translator | Same as v1, no change |
| LLM features | Azure AI Foundry | Same as v1, no change |
| Default capture mode | `single` | Safer for first run, broad browser support |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Token minting misuse or rate abuse | Service outage or unexpected cost | Strong rate limits, auth, and audit logs |
| Browser capture incompatibility | User activation drop | Default `single`, capability checks, guided UX |
| Session state mismatch after speech-service removal | Transcript drops or stuck states | Explicit state machine + contract tests |
| Voice profile privacy concerns | Legal and trust risk | Opt-in, consent, retention controls, legal review |
| Realtime latency regressions | Poor user experience | p95 latency SLOs and performance telemetry |
| COGS higher than expected | Business model risk | Early cost measurement and usage guardrails |
| Activation key sharing | Revenue loss / unexpected cost | Usage monitoring per key, per-IP rate limits |
| resemblyzer cold-start latency | Poor first-session UX | Warmup on startup, show loading indicator |
| getDisplayMedia UX friction | User drop at screen-share prompt | Clear UI instructions, skip if `single` mode |

---

## What NOT to Change

### Classes that copy verbatim (internal logic unchanged)

These classes are designed around transcript events — they don't know or care about the audio
source. Their internal logic requires zero modification:

- app/controller/config_store.py
- app/controller/summary_orchestrator.py
- app/controller/transcript_store.py
- app/services/coach.py
- app/services/meeting_insights.py
- app/services/summary.py
- app/services/topic_summary.py
- app/services/topic_tracker.py
- app/services/translation_pipeline.py

### Files that need minor wiring changes for session isolation or redesigned trigger logic

`broadcast_service.py` — class logic unchanged, but instantiated per `SessionContext` instead of
as a global singleton. No code changes inside the class; just instantiation pattern.

`session_manager.py` — SpeechService dependency removed, session_control message handling added.
Internal orchestration logic (watchdog, finalization) unchanged.

`coach_orchestrator.py` — auto-trigger logic (post-utterance firing) removed. Reduced to: receive
explicit POST /api/coach/ask request → build context from transcript[last_sent_index:] → call LLM
→ return result. No scheduling, no speaker-side trigger.

`topic_orchestrator.py` — background interval timer and auto-trigger logic removed. Reduced to:
handle on-demand POST /api/topics/analyze-now → call LLM with topic definitions context → return
results. No background task, no periodic firing.

### Files modified significantly (5 files)

- app/main.py — remove speech init, add `active_sessions` dict, add lifespan for session cleanup
- app/config.py — add Deepgram + JWT settings
- app/api/routes.py — add token + voice + auth endpoints
- app/api/websocket.py — bidirectional, session_control routing, per-session context lookup
- static/app.js — orchestrate audio-capture → deepgram-client → backend WS pipeline

### New files (5 files)

- app/api/auth.py — activation key validation, JWT issuance, quota middleware
- app/services/voice_profiles.py — resemblyzer embed + cosine identify
- static/deepgram-client.js — token fetch, WS to Deepgram, reconnect on drop
- static/audio-capture.js — getUserMedia, getDisplayMedia, Web Audio mixer
- static/voice-profiles.js — localStorage CRUD, embed/identify API calls

The core architectural strength: swapping STT provider left all AI service logic untouched.
Coach and topic orchestrators are modified only in their trigger wiring (auto-fire removed),
not in their LLM call or output logic.

---

## Code Quality Rules

These rules apply to every file written in V2. They are enforced during code review and
take priority over any "nice to have" patterns.

**CI gate (run before every commit):**

```bash
ruff check .          # lint + unused imports
ruff format --check . # formatting
mypy app              # type checking
```

All three must pass with zero errors. Fix errors before committing — do not suppress with `# noqa`
or `# type: ignore` unless the suppression has an inline explanation.

### Python style for a C# developer

Python async/await, type hints, and Pydantic models map directly to C# concepts you already know:

```text
C#                          Python equivalent
────────────────────────    ──────────────────────────────────
public class Foo { }        class Foo:
string Name { get; set; }   name: str  (Pydantic field)
async Task<T> Foo()         async def foo() -> T:
IEnumerable<T>              list[T]
Dictionary<K,V>             dict[K, V]
null                        None
interface IFoo              Protocol (rarely needed, skip for pilot)
```

### Type hints — always

Every function signature must have parameter types and return type. No bare `Any` unless
genuinely unavoidable. This is the single biggest readability win for a C# developer reading Python.

```python
# Wrong
def get_session(key_id):
    ...

# Right
def get_session(key_id: str) -> SessionContext | None:
    ...
```

### One file = one responsibility

Match the repo structure exactly. Do not add helpers, utilities, or base classes unless two or
more files need the exact same logic. One-off helpers inline in the function that uses them.

### No dead code

- No commented-out code blocks.
- No unused imports (`isort` + `ruff` will catch these).
- No `TODO` comments left in committed code — convert to an Open Question in this plan instead.

### No premature abstraction

Wrong: create a `BaseOrchestrator` class because coach and topic orchestrators look similar.
Right: let them be two separate simple functions until a third one proves a pattern exists.

### Small, flat functions

- Aim for under 30 lines per function. This is a guideline, not a hard limit — orchestration
  functions and validation handlers may be longer when splitting them would hurt readability.
  If a function exceeds 50 lines, that is a strong signal to extract a helper.
- Max 2 levels of nesting inside a function body. Extract inner logic to a named function.
- No deeply nested `if/else` trees — use early returns.

```python
# Wrong
async def handle_event(payload):
    if payload.get("type"):
        if payload["type"] == "final":
            if payload.get("en"):
                # ... 20 more lines

# Right
async def handle_event(payload: dict) -> None:
    event_type = payload.get("type")
    if event_type != "final":
        return
    if not payload.get("en"):
        return
    await _process_final(payload)
```

### Error handling at boundaries only

- Validate and handle errors at the API layer (FastAPI route handlers).
- Internal functions raise exceptions — they do not swallow them silently.
- Do not add `try/except` inside orchestrators unless you have a specific recovery action.
- Log errors at the boundary, not deep in the call stack.

### No global mutable state except the session dict and app-initialized services

The only module-level mutable state allowed is `active_sessions: dict[str, SessionContext]`
in `main.py`. Everything else is passed as a parameter or accessed via `SessionContext`.

App-initialized services — objects created once at startup and never reassigned — are
explicitly allowed as module-level constants. The `GE2EEncoder` singleton is an example:
it is loaded once on startup to avoid a 17MB model reload per request, then held as a
read-only reference. This is service initialization, not arbitrary mutable global state.

### Comments: only where logic is non-obvious

Do not add docstrings to every function. Add a one-line comment only when the *why* is not
clear from the code. The plan document (this file) is the place for design rationale.

```python
# Wrong: obvious docstring
def increment_quota(key_hash: str) -> bool:
    """Increments the quota counter for the given key hash."""

# Right: no comment needed, name is self-documenting
def increment_ai_quota(key_hash: str) -> bool:
    ...

# Right: non-obvious reason deserves a comment
# SQLite UPDATE WHERE is atomic under WAL mode — safe without a Python lock
cursor.execute("UPDATE keys SET ai_calls_used = ai_calls_used + 1 WHERE ...")
```

### JS style (same principles)

- `const` by default, `let` only when reassignment is needed.
- No `var`.
- Arrow functions for callbacks, named `function` declarations for top-level logic.
- Module pattern: each `.js` file exports one object or set of functions. No globals on `window`.

**JS lint (no build step — use npx directly):**

```bash
npx eslint static/          # convention enforcement, no bundler needed
```

Minimum `.eslintrc.json`: `"no-var": "error"`, `"prefer-const": "error"`,
`"no-unused-vars": "warn"`. Add to CI gate alongside ruff/mypy.

---

## Environment Variables (.env)

```env
# Azure (unchanged from v1)
AZURE_AI_SERVICES_KEY=...
AZURE_AI_SERVICES_REGION=eastus2
PROJECT_ENDPOINT=...
GUIDANCE_AGENT_NAME=my-profile-agent
SUMMARY_AGENT_NAME=my-summary-agent

# Deepgram (new)
DEEPGRAM_API_KEY=...
# DEEPGRAM_PROJECT_ID — not needed; /v1/auth/grant only requires the API key

# Auth (new)
JWT_SECRET=...
```

---

## Open Questions to Resolve Early

1. **Deepgram temp token endpoint — RESOLVED (2026-03-05).**
   Endpoint: `POST https://api.deepgram.com/v1/auth/grant`. No body needed (default 30s TTL).
   Response field: `access_token`. Required permission: Member+. WS persists past token TTL.
   Plan and code examples updated. Phase 0 gate cleared.
2. **Deepgram project ID — NOT REQUIRED.** `/v1/auth/grant` only needs the API key in the
   Authorization header. No project ID needed for token minting. Removed from config and .env.
3. **Activation key store** — SQLite for MVP? Confirm before Phase 1.
4. **Voice profiles GA vs beta** — ship opt-in in v2.0 or hold for v2.1?
5. **getDisplayMedia UX** — user must click "Share" each session. Add clear UI instruction on first use.
6. **AudioWorklet vs ScriptProcessorNode** — AudioWorklet preferred (off main thread) but requires HTTPS. ScriptProcessorNode works on HTTP for local dev.
7. **resemblyzer model download** — first run downloads ~17MB model. Handle gracefully on startup.
8. **HTTPS for deployment** — getUserMedia requires HTTPS. Azure Container Apps provides this automatically.
9. **Repo strategy** — stay in `v2` branch of this repo, or create `live-meeting-copilot-v2` new repo?
