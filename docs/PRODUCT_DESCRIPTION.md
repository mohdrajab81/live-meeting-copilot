# Live Meeting Copilot — Complete Product Description

> Legacy document. Public-facing product description now lives in [`PRODUCT_OVERVIEW.md`](PRODUCT_OVERVIEW.md).
> Deep design reasoning and engineering stories now live in
> [`ENGINEERING_RATIONALE.md`](ENGINEERING_RATIONALE.md).
> Keep this file only as migration-era background material.

> **What this document is**: A comprehensive description of the Live Meeting Copilot project covering
> the product, its full feature set, the UI/UX design, the system architecture, and the key
> engineering decisions. Intended for recruiters, interviewers, LinkedIn audiences, and anyone
> who wants a deep understanding of the project without reading the source code.

---

## Table of Contents

1. [What It Is](#1-what-it-is)
2. [Who It Is For](#2-who-it-is-for)
3. [Full Feature Inventory](#3-full-feature-inventory)
4. [UI/UX Design](#4-uiux-design)
5. [System Architecture](#5-system-architecture)
6. [The Translation Journey — Four-Stage Evolution](#6-the-translation-journey)
7. [Five Sophisticated Engineering Decisions](#7-five-sophisticated-engineering-decisions)
8. [Technology Stack](#8-technology-stack)
9. [Design Philosophy](#9-design-philosophy)
10. [Known Constraints and Tradeoffs](#10-known-constraints-and-tradeoffs)

---

## 1. What It Is

**Live Meeting Copilot** is a real-time bilingual meeting intelligence platform for Windows. It listens
to a live meeting, produces a simultaneous English transcript and Arabic translation, gives the local
speaker AI coaching hints as the conversation progresses, and generates a structured summary when the
session ends.

It runs entirely on the local machine. No cloud hosting is required. Azure AI services handle the
speech, translation, and AI features, but the application itself is a locally-run Python/FastAPI
backend with a browser-based single-page UI.

The project was built entirely by one developer as a solo production-quality system, including backend
architecture, all AI integration, and the browser-based frontend.

---

## 2. Who It Is For

- **Bilingual meeting participants** who need live Arabic translation of English speech
- **Professionals in high-stakes meetings** (sales, negotiations, interviews) who want real-time
  AI coaching on what to say next
- **Meeting facilitators** who need agenda adherence tracking and structured post-meeting summaries
- **Anyone** who wants an automated record of what was discussed, decided, and actioned

---

## 3. Full Feature Inventory

### Speech Transcription
- Real-time English speech recognition using Azure Speech SDK (continuous recognition)
- Alternative Nova-3 (Deepgram) STT engine with automatic fallback to Azure if unavailable
- **Dual-channel mode**: captures local microphone and remote speaker audio simultaneously as
  separate speaker tracks
- Dual-channel mode for Nova-3 uses Windows WASAPI loopback — no virtual audio cable required
- Dual-channel mode for Azure uses standard recording devices (compatible with VB-CABLE/Voicemeeter)
- Per-channel auto-restart after Azure idle timeout ("client buffer exceeded" recovery)
- Configurable silence segmentation and initial silence timeouts

### Live Translation (English → Arabic)
- Live partial translation: Arabic appears in real-time as you speak, updating every few seconds
- Full final translation: each committed utterance is fully translated when STT finalizes it
- Optional shadow translation: an async LLM-powered secondary pass quietly patches the Arabic
  with higher accuracy and correct technical terms, without disrupting the live experience
- Per-speaker partial throttling to control translation API cost
- Revision-based staleness guard: old partials are never translated if newer ones arrive
- Translation cost telemetry: per-character tracking, estimated USD cost, rolling latency median

### AI Coaching (Azure AI Foundry)
- Triggers automatically after the remote speaker finishes a sentence
- Configurable trigger speaker (local / remote / any), cooldown interval (default 8s), max turns
- Sends only the delta since the last coach call — not the full transcript — using conversation
  continuity via Azure AI Foundry persistent conversation sessions
- Custom meeting brief: enter background context in Settings that the coach incorporates
- Manual ask: type a direct question to the coach at any time during the session
- Coach hints appear inline in the transcript, linked to the triggering utterance
- Coach history persists across stop/start events; cleared only when user explicitly resets

### Meeting Summary (Azure AI Foundry)
- Auto-triggered when the session stops; also available as a manual endpoint
- Multi-section structured output: executive summary, key points, action items, decisions made,
  risks and blockers, key terms defined
- Summary generation uses the most recent 500 utterances / transcript rows to keep prompts bounded
- Agenda-driven topic coverage: if topics are defined in Settings, the summary shows planned
  vs actual time per topic, with over/under indicators and an agenda adherence percentage
- Topic journey visualization: a horizontal timeline of topics in the order they actually occurred
- Meeting health score: composite deterministic score from speaking balance, pace, turn-taking,
  transcript density, and interaction quality signals
- Speaker insights: speaking time, turn count, average turn length per speaker
- Keyword index: merged from AI-extracted terms, key terms defined, and named entities
  (PERSON / ORG / LOCATION / DATE_TIME / PRODUCT / EVENT / MONEY / PERCENT)
- From-file analysis: upload an exported transcript CSV (UTF-8, up to 5 MB) to generate a summary
  without a live session
- Deterministic post-processing: topic durations are computed from real utterance timestamps, not
  AI estimates — reproducible results across runs

### Agenda / Topic Definitions
- Define up to 80 topics in Settings with name, expected duration (minutes), priority, and notes
- Topics feed into the summary prompt as expected agenda context
- Topic breakdown in summary shows planned vs actual, over/under, and adherence percentage
- Topic colors are deterministically assigned (same topic always gets the same color)

### Session Management
- Configurable auto-stop on silence (default 75 seconds, configurable or disabled)
- Hard session cap (default 60 minutes, configurable) — cost protection
- Watchdog loop triggers final summary on timeout so the user always gets a summary
- Session start validates the critical prerequisites needed for live capture and coach startup
  before beginning

### Export
- Transcript export: JSON or CSV format; Standard (clean) or Diagnostic (full metadata) detail level
- Full transcript or bookmarks-only export
- Summary export: JSON (full structured payload) or plain text (readable format)
- Exported CSV can be re-fed to the from-file summary endpoint for offline re-analysis

### API and Security
- FastAPI backend with loopback-only authentication — no remote access by design
- Rate limiting on AI-backed endpoints: coach ask (6/min), summary generate (2/min)
- Sliding window rate limiter — no fixed-window loophole
- All AI operations run on thread pool via `asyncio.to_thread` — event loop never blocked

---

## 4. UI/UX Design

The frontend is a single-page application built in vanilla HTML/CSS/JavaScript (no framework).
Every interactive feature was designed and implemented by the same developer who built the backend.

### Transcript Tab

The primary working view during a meeting:

- **Bilingual dual-column layout**: English on the left, Arabic on the right, scrolling in sync
- **Live partials strip**: a dedicated panel at the bottom shows the real-time speech hypothesis for
  both speakers simultaneously, separate from the committed transcript above
- **Draggable divider**: the split between the committed transcript and the live strip is
  user-adjustable and position is remembered
- **Per-entry bookmarks**: click any transcript row to bookmark it; optionally add a note; jump
  to any bookmark via the bookmark list panel
- **Bookmark filter**: toggle to show only bookmarked entries
- **Coach hint popovers**: each transcript entry that triggered a coach hint shows an indicator;
  clicking opens a popover with the hint text inline
- **Unread coach hints**: entries with unread hints are visually marked until viewed
- **Full-text search**: searches across all English transcript text in real time
- **Entry metadata**: entry count and bookmark count are shown as live counters

### Coach Tab

- Single active recommendation view with older / newer navigation through session hints
- Manual prompt input: ask the coach a direct question at any point
- Coach pending indicator: visual status when a coach call is in flight

### Summary Tab

- **Executive Summary section**: the top-level meeting narrative
- **Key Points, Action Items, Decisions Made, Risks and Blockers**: each in its own dedicated section
- **Key Terms Defined**: expandable list of technical/domain terms with definitions
- **Topic Breakdown table**: planned minutes vs actual minutes per topic with over/under status chips
- **Donut chart**: visual proportional breakdown of time spent per topic
- **Topic Journey Timeline**: a horizontal bar chart showing topics in chronological order as they
  actually occurred in the meeting — not just a summary table
- **Agenda Adherence chip**: percentage score showing how closely the meeting followed the agenda
- **Meeting Health Score chip**: composite 0-100 score with color coding (green/amber/red)
- **Speaker Insights section**: per-speaker statistics
- **Keyword Index with search**: all extracted keywords searchable; usage counts per term
- **Export buttons**: JSON (structured) and text (human-readable) export
- **File Analysis modal**: drag-and-drop or browse to upload a past transcript CSV and regenerate
  a summary for it — the result loads directly into this tab

### Settings Tab

A comprehensive configuration panel with approximately 20+ configurable parameters:

**Speech Configuration**
- Provider selector: Azure Speech or Nova-3
- Capture mode: single channel or dual channel
- Audio device selectors: separate dropdowns for local mic and remote capture in dual mode
- Device list auto-populated from Windows audio devices

**Translation**
- Enable/disable toggle
- Partial translation interval slider (how often partial updates are sent, in seconds)

**AI Coach**
- Enable/disable
- Trigger speaker selector
- Cooldown interval
- Max turns per session
- Meeting brief text area (background context for the coach)
- Preset buttons (Quick Meeting, Interview, Sales Call, etc.)

**Session Limits**
- Auto-stop silence timer (seconds, or 0 to disable)
- Max session duration (minutes)
- Preset buttons (Short / Standard / Long / Unlimited)

**Summary**
- Enable/disable
- Topic duration mode (from utterance IDs or estimated)
- Topic grouping gap threshold

**Display**
- Font selector for English text (separate from Arabic)
- Font selector for Arabic text
- Font size sliders — separate English scale and Arabic scale

**Settings UX**
- Dirty indicator: visual warning when unsaved changes exist
- Inline validation: field-level error messages before Apply
- Impact Summary sidebar: shows which running features will be affected by pending changes
- Sticky commit bar: Apply / Save / Reload / Restore Defaults always visible when changes exist
- Applying or reloading runtime config is blocked while a session is running

### Logs Tab

- Live system log stream during and after sessions
- Severity filter chips: All / Info / Warning / Error / Debug
- Compact mode toggle (dense vs. spacious)
- Pinned logs: pin important entries to always show at top
- Log search
- KPI counters: visible entries and error count
- Copy / Export / Clear actions

### Global UX

- **4 themes**: Dark, Light, Graphite, Sand — switchable at any time
- **Collapsible navigation rail**: the left sidebar collapses to icons-only to maximize content area
- **Mobile-responsive**: hamburger menu with slide-in navigation and backdrop overlay on small screens
- **Real-time status bar**: current time, session start time, recording duration, auto-stop countdown
- **WebSocket reconnect**: automatic reconnect with a badge indicator while disconnected; full state
  snapshot received on reconnect so the UI never shows stale data
- **Toast notification system**: non-blocking notifications with optional action buttons
- **Accessibility**: ARIA labels, roles, `aria-current`, `aria-pressed`, `aria-expanded` throughout
  all interactive components
- **State persistence**: UI preferences (theme, fonts, layout, nav state) and bookmarks are
  persisted to localStorage and restored on reload
- **Deterministic topic colors**: topic colors are assigned by name hash — the same topic always
  gets the same color across sessions

---

## 5. System Architecture

### Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Browser UI  (vanilla JS/HTML/CSS)                          │
│  WebSocket client + REST control plane                      │
└──────────────────────┬──────────────────────────────────────┘
                       │  WebSocket + HTTP
┌──────────────────────▼──────────────────────────────────────┐
│  FastAPI Backend                                            │
│  ┌────────────────┐  ┌──────────────────────────────────┐   │
│  │  API Layer     │  │  Controller Layer                │   │
│  │  routes.py     │  │  session_manager                 │   │
│  │  websocket.py  │  │  transcript_store                │   │
│  │  auth.py       │  │  coach_orchestrator              │   │
│  └────────────────┘  │  summary_orchestrator            │   │
│                      │  topic_orchestrator              │   │
│                      │  config_store                    │   │
│                      │  broadcast_service               │   │
│                      └──────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  Service Layer                                        │   │
│  │  speech_provider → speech.py / speech_nova3.py        │   │
│  │  translation_pipeline + shadow_translation_pipeline   │   │
│  │  coach.py + summary.py (Azure AI Foundry clients)     │   │
│  │  meeting_insights.py + topic_summary.py               │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │  Azure SDKs / REST APIs
┌──────────────────────▼──────────────────────────────────────┐
│  Azure Cloud Services                                       │
│  Azure Speech SDK (STT)  |  Azure Translator API            │
│  Azure AI Foundry (Coach Agent + Summary Agent)             │
│  Deepgram Nova-3 (optional STT alternative)                 │
└─────────────────────────────────────────────────────────────┘
```

### Four Concurrent Execution Contexts

The backend operates across four concurrent execution contexts — correctly bridged without deadlocks:

| Context | What runs there | How it communicates |
|---|---|---|
| Azure Speech SDK threads | STT callbacks (`on_recognized`, `on_canceled`) | `run_coroutine_threadsafe` → event loop |
| Nova-3 pump threads | WASAPI audio capture + Deepgram WebSocket | `run_coroutine_threadsafe` → event loop |
| asyncio event loop | FastAPI routes, WebSocket sends, translation worker | Direct `await` |
| Thread pool | Blocking AI agent calls (coach, summary) via `asyncio.to_thread` | `await` result back on event loop |

### One Shared Lock

All controller modules (`SessionManager`, `TranscriptStore`, `CoachOrchestrator`,
`TopicOrchestrator`, `SummaryOrchestrator`) share a single `threading.RLock` from `AppController`.
This ensures that operations spanning multiple modules — for example, a speech final event that
simultaneously updates the transcript, checks bleed suppression, and decides whether to trigger the
coach — are atomic and race-condition-free.

Any method suffixed `_unlocked` expects the caller to already hold the lock. This naming convention
makes the lock contract explicit in the code.

---

## 6. The Translation Journey

The translation system went through four engineering stages before reaching its final form.
Each stage solved a real problem discovered in practice.

### Stage 1: Live Streaming Translation Pipeline — Scrapped

The first approach used Azure's live streaming translation: audio goes in, translated text comes out
in real time. This is the most direct approach and technically elegant.

**Problem**: It was expensive and produced terrible UX. The translation updates on every word —
the Arabic text flickered and changed constantly as speech was recognized. Users cannot read a
translation that is changing several times per second. The cost was also high because every partial
hypothesis was translated, including the many that are immediately replaced.

### Stage 2: Throttled Partial Translation via Azure Translator API

The second approach switched to Azure Translator REST API, called at most every N seconds (configurable,
default every few seconds) on the current partial text. This dramatically reduced cost and API calls.

**The staleness problem**: partials change many times per second. A translation request is sent for
revision 42 of a partial. By the time the response arrives, revision 48 is already showing. The old
response must be discarded — not applied — or it would briefly show wrong text.

**Solution**: a monotonic revision counter per speaker. Each new partial increments the revision.
A translation result is only applied if its revision matches the current revision. Older results are
silently dropped. No timestamps needed — a simple integer comparison.

### Stage 3: Full Final Translation on STT Commit

When the STT engine commits a final utterance (the speaker finishes a sentence), that text is
immediately queued for a full translation via Azure Translator. This translation is applied to the
transcript as a `final_patch` update — the Arabic field on that row updates asynchronously.

Finals always have higher queue priority than partials, so the full final translation arrives quickly.

**Segment ID matching**: multiple finals can be in-flight simultaneously (translated asynchronously
in parallel). The translation result must be matched back to the correct transcript row. This is done
via a `segment_id` — each committed utterance gets a stable ID that travels with the translation
request and is used to find the correct row when the result arrives.

### Stage 4: Optional Shadow LLM Translation Pass

The final stage adds an optional second-pass worker: `ShadowFinalTranslationPipeline`.

After a final utterance is committed and its standard translation applied, the shadow worker
sends the same utterance to an LLM (via Azure AI Foundry) for a higher-quality Arabic translation
— one that understands context, domain-specific terms, and technical vocabulary.

When the shadow result arrives, it silently replaces the standard Arabic translation as a
`final_shadow_patch` event. The user sees the improved translation appear without any disruption
to the live flow.

**The generation counter**: the shadow worker runs asynchronously and may take several seconds.
If the session is stopped or reset while a shadow request is in flight, the result must be discarded
— applying it to a cleared transcript would corrupt state. A monotonic generation counter is
incremented on every stop/reset. The shadow result checks if its generation matches the current
generation before applying. If not, it is silently dropped.

**The key design insight**: the shadow translation never blocks or replaces the fast path. The user
gets an instant (if slightly lower quality) Arabic translation immediately, and may notice it
silently improve a second or two later. The fast path and the quality path operate independently.

---

## 7. Five Sophisticated Engineering Decisions

### 1. CoachOrchestrator — The Queue-Drain Pattern

**The problem**: an AI coach call takes 2–4 seconds. What happens if the remote speaker finishes
another sentence while the previous coach call is still in flight?

Three naive options: ignore new triggers (miss coaching opportunities), queue all triggers
(hints about things said minutes ago are useless), or run multiple calls in parallel (race conditions,
out-of-order responses, confusing hints).

**The solution** — a single-slot queue with drain-on-completion:

1. When a coach call starts, `coach_pending = True` blocks new automatic triggers
2. If a new trigger arrives while busy, it is stored in `coach_queued_trigger` — overwriting any
   previous queued trigger (only the latest matters)
3. When the current call finishes, the `finally` block atomically reads and clears the queued
   trigger, then immediately schedules the next call with `ignore_cooldown=True` (since the user
   has already waited)
4. If no trigger is queued, the loop ends cleanly

**Why this is correct**: in a live meeting, by the time the coach finishes, the most recently spoken
sentence is the one that matters. A hint about something said 30 seconds ago is already stale. The
single-slot design guarantees the coach always catches up to the most recent context, never a stale one.

### 2. TranscriptStore — Three-Layer Translation Application

Translations arrive asynchronously and must be applied to the exact correct transcript segment
without race conditions. There are three separate application paths, each with its own staleness guard:

- **Partial translation**: checked against `is_current_partial_unlocked()` AND a monotonic
  `ar_revision` counter. Older revisions are silently dropped without any timestamp comparison —
  a pure sequence number.
- **Final patch**: the pipeline reverse-scans `finals[]` by `segment_id` + revision. Correct even
  if new finals have arrived since the translation was enqueued — the scan goes backwards from newest
  to find the matching entry.
- **Shadow patch**: same reverse-scan as final patch, but additionally only promotes the shadow
  translation to the `ar` field when the entry's translation `status == "completed"` — the shadow
  result silently supersedes the primary translation for that entry without creating a visible flash.

The revision monotonicity check for partials is particularly clean: no timestamps, no additional
locks, just a single integer comparison.

### 3. SessionManager — Dual-Channel Bleed Suppression

When running in dual-channel mode (local mic + remote speaker captured separately), the local
microphone physically picks up sound from the speakers — the remote voice bleeds into the local
channel with a short delay. Without suppression, every remote utterance would appear twice in the
transcript: once from the remote channel, and once as echo from the local channel 50–200ms later.

The suppression logic has two tiers:

- **Active bleed**: if the remote channel has a live partial with text right now → suppress the
  local channel immediately (highest confidence: remote speaker is currently talking)
- **Recent activity bleed**: if the remote channel produced any speech activity within the last
  1.6 seconds → suppress local (covers the audio propagation + SDK processing lag window)

The 1.6-second window is production-tuned: long enough to catch all echo, short enough to allow
genuine fast back-and-forth replies from the local speaker.

Local final utterances use a shorter 0.5-second window (vs. 1.6 seconds for partials) because by
the time a final commits, there is more certainty that it is genuine speech rather than echo.

### 4. SummaryOrchestrator — AI for Language, Deterministic Code for Facts

The summary pipeline is not a single AI call — it is a multi-stage pipeline that uses AI for what
AI is good at (understanding language, grouping topics, writing prose) and uses deterministic Python
code for what needs to be exact (timing, durations, adherence percentages):

```
finals[] → sorted by start_ts (not arrival order — dual-channel recognizers interleave)
         → prepare_transcript_utterances (500-item window)
         → build_expected_agenda_context (prepend agenda to prompt)
         → SummaryService.generate() [Azure AI Foundry — AI call]
         → enforce_topic_coverage() [repair topics the AI missed or hallucinated]
         → apply_topic_durations_from_utterance_ids() [OVERRIDE AI timing estimates]
         → build_topic_breakdown_from_definitions() [planned vs actual from your agenda]
         → build_meeting_insights() [fully deterministic — zero AI]
         → build_keyword_index() [merge AI keywords + entities + key terms]
         → broadcast full payload
```

**The sorting insight**: in dual-channel sessions, the two recognizers run in parallel and their
finals arrive interleaved in queue order, not speech order. Sorting by `start_ts` (when speech
actually began) reconstructs the actual conversation timeline before feeding it to the AI model.
Wrong sort order would make the model see a collapsed timeline at session start.

**The timing override**: the AI model is not reliable for duration estimates. Instead, the prompt
asks the model to return `utterance_ids` with each topic group. Backend Python maps those IDs to
the actual transcript utterance timestamps and computes exact durations. If the model omits some
utterances, backend appends an `Unassigned / Other` topic to preserve full coverage. The result is
reproducible across runs — the same transcript always produces the same topic durations.

### 5. Watchdog — Cost-Aware Auto-Stop with Guaranteed Summary

The watchdog loop runs every second and enforces two limits:

- **Silence auto-stop** (`auto_stop_silence_sec`): stops after N seconds of no speech activity
  — catches meetings where the user forgot to stop, or recording sessions that ended silently
- **Hard session cap** (`max_session_sec`): prevents unbounded recording and runaway AI costs

On auto-stop, the watchdog calls `stop_async()` which flushes a final summary **before** cleanup.
The user always gets a structured summary even on a timeout stop — the session is never just
silently terminated.

`stop_async()` wraps the summary flush in `asyncio.wait_for(..., timeout=60.0)`. If summary
generation is slow or fails, cleanup happens anyway after 60 seconds — the timeout ensures summary
failure never permanently blocks session shutdown.

Both thresholds are explicitly tagged as cost-control measures in log messages — not just
operational limits but a deliberate production cost-awareness pattern.

---

## 8. Technology Stack

| Layer | Technology |
|---|---|
| Backend language | Python 3.12 |
| Web framework | FastAPI + uvicorn |
| Frontend | Vanilla HTML/CSS/JavaScript, no framework |
| Primary STT | Azure Cognitive Services — Speech SDK (continuous recognition) |
| Alternative STT | Deepgram Nova-3 (WebSocket streaming, WASAPI loopback capture) |
| Translation | Azure AI Services — Translator REST API |
| AI Coaching | Azure AI Foundry — persistent conversation agent |
| AI Summary | Azure AI Foundry — structured JSON extraction agent |
| Audio capture | PyAudioWPatch (WASAPI loopback), Windows MMDEVAPI via registry |
| Real-time transport | WebSocket (FastAPI/Starlette native) |
| Concurrency | threading.RLock + asyncio + asyncio.to_thread |
| Tests | pytest (405 passing tests as of 2026-03-16) |
| Distribution | PyInstaller EXE, offline wheel archive, standard deploy package |

---

## 9. Design Philosophy

Several consistent design principles run through the entire codebase:

**Cost awareness as a first-class concern**: every component that touches a paid API has explicit
cost controls — translation throttling, per-character telemetry, shadow translation as opt-in,
coach cooldowns, watchdog auto-stop, rate limiting on AI endpoints. The system is designed to never
run away on the user's Azure bill.

**Deterministic over probabilistic where facts are needed**: the AI model is trusted for language
tasks (summarizing, grouping, coaching). It is not trusted for numeric facts (durations, percentages,
counts). Wherever a number matters, deterministic Python code computes it from the actual transcript
data. AI outputs are post-processed and validated, not used raw.

**Single responsibility per module**: each module owns exactly one concern. `TranscriptStore` owns
transcript state. `CoachOrchestrator` owns coach scheduling. `BroadcastService` owns WebSocket
fanout. No circular dependencies. No module reaching into another's state directly.

**Fail loud on critical startup prerequisites**: session start validates the pieces that would make
live capture or coach startup fail immediately. If the coach agent cannot establish a conversation,
the session does not start. Better a clear pre-session error than an obscure failure once the user
is already recording.

**Operationally important failures are surfaced**: degraded paths such as provider fallback,
translation errors, summary failures, rate limiting, and watchdog auto-stop are logged and surfaced
to the UI. Some stale async results are intentionally dropped as part of normal correctness guards.

**Graceful degradation**: Nova-3 auto-falls back to Azure if it cannot start. Translation errors
are logged and the transcript continues in English. Coach and summary failures surface to the UI
but do not interrupt the running session.

---

## 10. Known Constraints and Tradeoffs

- **Summary prompt window is bounded**: live-summary generation and from-file analysis both use the
  most recent 500 utterances / transcript rows.
- **Uploaded transcript analysis is constrained**: the CSV must be UTF-8 encoded and at most 5 MB.
- **Coach state is intentionally bounded**: manual coach prompts are limited to 2,000 characters,
  and in-memory coach history is capped to the most recent 120 hints.
- **Nova-3 is a preview path with opinionated routing**: the current implementation forces dual
  capture using the default microphone plus default WASAPI loopback, and ignores Azure-style manual
  local / remote device routing.
- **Runtime API access is intentionally local-only**: HTTP and WebSocket access are restricted to
  loopback / localhost clients by design.

---

*Document version: 2026-03-16*
*Author: Mohammad Rajab*
