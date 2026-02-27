# Technical Concepts Explained — Plain English Guide

This document explains every significant technical concept in the Live Interview Translator project in clear, plain language. It is intended to help you understand *why* the code is built the way it is, so you can explain it to others (e.g., in a technical interview) without needing to look at the code.

---

## Table of Contents

1. [Big Picture: How the System Works](#1-big-picture)
2. [The Concurrency Problem — Two Worlds Colliding](#2-concurrency-model)
3. [The Shared Lock — One Lock to Rule Them All](#3-shared-lock)
4. [Azure Speech SDK — How Speech Recognition Works](#4-azure-speech-sdk)
5. [The Buffer Overflow Problem and Auto-Restart](#5-buffer-overflow-and-auto-restart)
6. [Dual Mode and Bleed Suppression](#6-dual-mode-and-bleed-suppression)
7. [The Translation Pipeline](#7-translation-pipeline)
8. [Session Lifecycle — Start, Run, Stop](#8-session-lifecycle)
9. [The Coach Orchestrator](#9-coach-orchestrator)
10. [The Topic Orchestrator](#10-topic-orchestrator)
11. [WebSocket and the Real-Time Frontend](#11-websocket-and-frontend)
12. [API Design — Rate Limiting and Auth](#12-api-design)
13. [Configuration System](#13-configuration-system)
14. [Watchdog Loop — Automated Session Management](#14-watchdog-loop)
15. [Windows Audio Devices](#15-windows-audio-devices)
16. [Design Trade-offs You Should Know](#16-design-trade-offs)
17. [Summary Intelligence and From-File Analysis](#17-summary-intelligence-and-from-file-analysis)

---

## 1. Big Picture

The system does six things during a live interview session:

1. **Captures speech** from one or two microphones using Azure Speech SDK.
2. **Produces a live English transcript** — both partial (live preview) and final (committed) text.
3. **Optionally translates English to Arabic** asynchronously in the background.
4. **Optionally provides AI coaching hints** based on what the interviewer just said.
5. **Optionally tracks which interview topics** have been covered and for how long.
6. **Optionally generates a structured meeting summary** (either from live session stop or uploaded transcript CSV).

All of this streams to the browser in real time over a WebSocket connection.

The backend is built with **FastAPI** (Python's async web framework). The frontend is plain HTML/CSS/JavaScript — no framework. The AI features use **Azure AI Foundry** agents.

---

## 2. Concurrency Model

### The core problem

The Azure Speech SDK operates in its own background thread. It fires callbacks when speech is detected. But FastAPI runs in an `asyncio` event loop — a single-threaded async system. These two worlds cannot directly talk to each other.

**Why can't you just `await` inside a speech callback?**
Because `await` only works inside an `async` function running on the asyncio event loop. A callback running on the SDK's thread has no connection to that event loop.

### The solution: `asyncio.run_coroutine_threadsafe()`

When the SDK fires a speech event (partial, final, error), the callback calls `broadcast_from_thread()`. This function uses Python's `asyncio.run_coroutine_threadsafe()` to schedule a coroutine on the event loop from the SDK thread — safely, without blocking anything.

Think of it like dropping a note through a slot in a door. The SDK thread drops the note; the event loop picks it up and processes it when it's ready.

```
Azure SDK Thread                         asyncio Event Loop
────────────────                         ──────────────────
speech detected
  → on_recognized callback
    → broadcast_from_thread(payload)
      → run_coroutine_threadsafe(...)  ──→  await broadcast(payload)
                                              → send to all WebSocket clients
```

### Three concurrent contexts

| Context | What runs there | How it communicates out |
|---|---|---|
| Azure SDK thread | Speech callbacks (on_recognized, on_canceled) | `run_coroutine_threadsafe` → event loop |
| asyncio event loop | FastAPI routes, WebSocket sends, AI agent calls | Direct `await` |
| Watchdog (async task) | Auto-stop timer, periodic topic analysis | Runs on event loop, uses `await` |

---

## 3. Shared Lock

### Why one lock across all modules?

The app has several modules that each manage a piece of state: the transcript store, the session manager, the coach orchestrator, the topic orchestrator. Many operations need to touch multiple modules at the same time — for example, when a final speech event arrives, you need to:

- Append it to the transcript
- Check if coach should trigger
- Update the topic tracker's last-seen index
- Check bleed suppression state

All of this must happen atomically (as one indivisible unit). If you used separate locks per module, you would risk a **deadlock** (each module waiting for the other's lock) or a **race condition** (another thread sees an inconsistent state halfway through the update).

**Solution**: One shared `threading.RLock` is created in `AppController` and passed to every module. An `RLock` (reentrant lock) means the same thread can acquire it multiple times without deadlocking — useful because methods call other methods.

### The `_unlocked` convention

Any method with `_unlocked` in its name expects the caller to already hold the lock. It does NOT acquire the lock itself. This prevents double-locking and makes the call chain explicit and safe.

```python
with self._lock:
    self._append_final_unlocked(item)   # safe — lock is already held
    self._trigger_coach_unlocked(item)  # safe — same lock still held
```

---

## 4. Azure Speech SDK

### How it works

The Azure Speech SDK sends your audio to Microsoft's cloud service and streams back text results in real time. There are two types of results:

- **Partial (recognizing)**: The service's best guess *right now*, while you're still talking. Updates every fraction of a second. Can change.
- **Final (recognized)**: The committed result once you stop talking. Does not change.

### SDK configuration via `SpeechConfig`

You configure the recognizer before starting it:

- `speech_recognition_language`: which language to recognize (e.g., `en-US`)
- `EndSilenceTimeoutMs`: how many milliseconds of silence after a word before the SDK finalizes the utterance (default: 250ms)
- `InitialSilenceTimeoutMs`: how long to wait for the first word before giving up on the current recognition attempt (default: 3000ms)

**Important**: These are utterance-level timeouts, not session-level. They control when each sentence is "committed", not when the overall session ends.

### Continuous recognition

The app uses `start_continuous_recognition_async()` which keeps listening forever (until you stop it) rather than listening for just one utterance. The SDK fires events continuously as speech is detected.

---

## 5. Buffer Overflow and Auto-Restart

### The "client buffer exceeded" problem

Azure's speech recognition runs over a WebSocket connection from the SDK to Microsoft's cloud. If you're in a period of silence, that connection can go idle. Azure's infrastructure has its own idle timeout — observed in production to be roughly 60-90 seconds — after which it drops the underlying WebSocket connection. This is service-side behavior; the SDK provides no setting to control it.

When the connection goes idle and then audio arrives again, the SDK's local audio buffer fills up faster than the stale connection can drain it. Eventually the buffer overflows, and Azure sends back a cancellation event with the error message: `"client buffer exceeded"`.

**Before the fix**: The `on_canceled` callback treated all cancellations the same — it set the global stop event, ending the entire session. This is why transcription stopped during your interview.

**After the fix**: The callback inspects the error message. If it contains `"client buffer exceeded"`, it's a recoverable timeout. It signals only that channel's `restart_event` (a `threading.Event`). The monitor loop in the worker thread sees this flag and restarts just that one recognizer — the other channel continues uninterrupted.

### Per-channel restart in dual mode

In dual mode (two microphones), if the "You" channel goes quiet while the interviewer is talking, only the "You" channel risks buffer overflow. The fix ensures that restarting the "You" channel never interrupts the "Remote" channel that is actively transcribing speech.

Each channel carries its own `restart_event`. The monitoring loop checks both independently every 200ms.

---

## 6. Dual Mode and Bleed Suppression

### What dual mode is

Dual mode runs two independent Azure Speech recognizers simultaneously — one on your local microphone, one on a virtual audio cable that captures the remote side of a call (e.g., via Voicemeeter). Each recognizer streams into a separate "speaker" track.

### The bleed problem

Audio hardware is imperfect. Your local microphone can pick up sound from your speakers (the remote voice bleeding into the local channel). Without suppression, the remote speaker's words would appear twice — once from the remote channel and once as echo from the local channel.

### The solution: 1.6-second suppression window

When the remote channel produces any speech activity, the local channel is suppressed for 1.6 seconds. The logic is:

- If the remote channel has an active live partial right now → suppress local.
- If the remote channel was active within the last 1.6 seconds → suppress local.
- Otherwise → allow local through.

1.6 seconds was chosen to be long enough to cover audio propagation + SDK processing delay without being so long that it mutes the local speaker during genuine back-and-forth conversation.

---

## 7. Translation Pipeline

### Async-first, priority-based

Translation requests are placed into a queue. The pipeline processes them asynchronously. Final translation requests have higher priority than partial ones — because finals are committed text and matter more to the user.

If `translation_enabled=false`, requests are not enqueued at all. English transcript, coach, and topics still run normally.

### Stale-guard: don't translate old partials

Partials update many times per second. If a new partial arrives before the old one is translated, the old one is discarded — no point sending a translation for text that has already been replaced. This is controlled by a "revision" number: each new partial increments the revision, and the translation result is only applied if the revision hasn't changed.

### Segment IDs: matching results to finals

When the Azure SDK commits a final result, the app assigns it a `segment_id`. When the translation pipeline finishes translating that segment, it uses the `segment_id` to find the correct entry in the transcript and patch the Arabic (`ar`) field. This is called a `final_patch` event.

Without segment IDs, you couldn't match the async translation result to the right transcript entry — especially if multiple finals are in flight at the same time.

### Translation metrics

The pipeline tracks:
- **Latency**: How long each translation took (kept as a rolling window of the last 240 samples)
- **Median latency**: Calculated from the rolling window — median is used instead of average because outliers (network spikes) would distort the average
- **Character count**: For cost estimation (translation APIs typically charge per character)

---

## 8. Session Lifecycle

### Three phases

1. **Idle**: No recognition running. Config can be changed freely.
2. **Running**: Azure recognizers are active, speech events flowing, watchdog running.
3. **Stopping/Finalized**: All recognizers stopped, topics finalized (active → covered), coach conversation cleared, final state broadcast to UI.

### The finalization invariant

No matter how a session stops, `_do_finalize()` is always called. There are three paths that can trigger it:

1. **`stop()`** — user clicks Stop; calls `_do_finalize()` directly after signalling the speech service to stop.
2. **`stop_async()`** — async version of the same; also calls `_do_finalize()` directly.
3. **Status event handler** — when the Azure Speech SDK worker finishes, it emits a `status: stopped` event; the session manager detects the transition from running to not-running and calls `_do_finalize()`.

Because both the explicit stop calls and the status handler can reach `_do_finalize()`, the function is designed to be safe if called more than once. The status handler guards with `if was_running and not self.running` to avoid a redundant call when `stop()` already finalized first, but the function itself is also robust to double invocation.

### Start validation

Before starting, the system checks:
- If dual mode: both device IDs must be configured.
- If coach enabled: the coach service must be set up AND must support conversation creation (tested at start time, not at config time).

This gives the user a clear error message before starting rather than failing silently mid-session.

---

## 9. Coach Orchestrator

### What it does

After each sentence the interviewer says (a "final" speech event), the coach orchestrator decides whether to ask the AI coach for a hint. If yes, it builds a prompt from recent transcript, sends it to Azure AI Foundry, and streams the result back to the UI.

### Trigger conditions

All of these must be true to trigger:
1. Coach is enabled in config
2. Coach service is configured (agent ID set)
3. The speaker matches the trigger setting (e.g., only trigger on "remote" speaker)
4. Enough time has passed since the last coach hint (cooldown, default 8 seconds)
5. Coach is not already busy with another request

### Incremental prompting

The coach maintains a conversation across the whole session. Each prompt only sends the *new* transcript since the last coach call — not the entire session transcript. This is called a "delta". The AI coach remembers the earlier context through the conversation history maintained by the Azure AI Foundry service.

Exception: the first call of a session sends the full transcript so far, to give the coach full context.

### The queue (depth 1)

If the coach is busy processing a request and a new trigger arrives, the system queues it. But the queue depth is 1 — only the most recent trigger is kept. If two triggers arrive while the coach is busy, only the second one is remembered. This is intentional: by the time the coach finishes, the older queued trigger's context would be stale anyway.

After the current hint is done, the system checks if something is queued. If yes, it immediately processes it (ignoring the cooldown, since the user was waiting). This creates a chain — one hint finishing automatically starts the next one if queued.

### Conversation continuity

The coach service keeps a `conversation_id` and `previous_response_id`. This means the AI model genuinely remembers earlier exchanges in the session — it's not reconstructing context from the transcript alone. This is more efficient and produces more contextually relevant hints.

---

## 10. Topic Orchestrator

This is the most complex module (~1660 lines). It tracks which topics from the interview agenda have been discussed and for how long.

### The three topic statuses

- `not_started`: Topic hasn't been mentioned yet
- `active`: Topic is currently being discussed
- `covered`: Topic was discussed and is now done

When the session ends, all `active` topics are automatically moved to `covered`.

### How time is allocated

Every time the topic agent runs, it looks at a chunk of the transcript and estimates which topics were discussed. For each topic, it calculates how many seconds of that chunk were spent on it. These seconds are accumulated in `time_seconds` across all agent runs.

This gives you a running total: "We spent 4 minutes on system design and 2 minutes on algorithms."

### Chunk modes

- **`window`**: Send the last N seconds of transcript to the agent on every run. Good for real-time accuracy. Drawback: may re-analyze the same words multiple times.
- **`since_last`**: Send only what's new since the last run. More efficient. Drawback: requires careful tracking of where we left off.

### First-chunk detection

On the first agent run after a session starts, there's a subtle edge case: what if the user kept their transcript from a previous session? The `time_seconds` from old topics would be preserved. The system detects this by comparing `topics_last_run_ts` (when we last ran the agent) to `topics_session_started_ts` (when this session began). If the last run was before this session started, it's the first chunk.

### Context reset detection

If more than 45 seconds of silence passed between the last transcript entry analyzed and the first entry of the new chunk, the system marks this as a `possible_context_reset`. This flag is sent to the AI agent so it knows the conversation may have jumped — not to extrapolate continuity across the gap.

### Statement deduplication

The agent returns key statements (quotes from the transcript) for each topic. On the next run, it might return some of the same quotes again. To avoid duplicates in the UI, statements are deduplicated using a `speaker:text` key. Only the 20 most recent unique statements are kept per topic.

### Confidence threshold

The agent returns a `match_confidence` score (0.0 to 1.0) for each topic it detects. The threshold is 0.65. What happens below it depends on context:

- **Known topic** (already in the agenda or previously tracked): low confidence → result is discarded. The system won't demote or update a known topic based on a weak signal.
- **New topic** (not previously seen) with `allow_new_topics = True` and a usable name: low confidence → the topic is still created as a candidate. Allowing new topics is an explicit user choice; the system respects it even with uncertain confidence.
- **New topic** with `allow_new_topics = False`, or with an unusable name: low confidence → discarded.

In short: 0.65 is a hard gate for known topics, but a soft gate for new topics when the user has opted into discovering new ones.

---

## 11. WebSocket and Frontend

### Why WebSocket, not polling?

The alternative to WebSocket would be the frontend repeatedly asking "any updates?" (HTTP polling) every half-second. WebSocket is a persistent connection — the server pushes updates the moment they happen. This is essential for real-time transcription where partials change dozens of times per second.

### Message types

The server sends structured JSON messages over WebSocket. Each message has a `type` field:

| Type | When sent | Content |
|---|---|---|
| `snapshot` | On initial connection | Full current state (transcript, topics, logs, config, status) |
| `status` | When session starts/stops | `running: bool`, `status: string` |
| `partial` | While speaking | Live preview text (EN + AR) |
| `final` | After each utterance | Committed sentence (EN + empty AR initially) |
| `final_patch` | After translation completes | Updated AR text for an existing final |
| `telemetry` | After each translation | Latency, cost, character count |
| `coach` | After AI coach responds | Hint text and metadata |
| `topics_update` | After topic agent runs | Full topic state snapshot |
| `summary` | After summary generation | Structured summary payload + topic coverage |
| `summary_cleared` | After clear action | Resets summary state in UI |
| `log` | Any time | System log entries (info, debug, error) |

### Snapshot on reconnect

When a browser tab reconnects (or the user opens a second tab), the server immediately sends a `snapshot` message with the full current state. This means the UI never shows a blank page — it reconstructs everything from the snapshot. Runtime state (transcript, topics, coach hints, session status) is read consistently while holding the shared lock. Config and logs use their own independent access paths, so the snapshot is not a single atomic operation across all subsystems — but in practice it is consistent enough for UI reconstruction.

### Dead connection cleanup

WebSocket connections can go stale without either side knowing. When the server tries to send a message to a dead connection, it gets an exception. Rather than maintaining a separate background cleanup job, the broadcast function simply removes any connections that fail on the next send. This is simpler and sufficient.

---

## 12. API Design

### Authentication

Two modes:
1. **Token-based** (for remote access): Set the `API_AUTH_TOKEN` environment variable. Clients must send this token as a Bearer token, `X-API-Key` header, or URL query parameter.
2. **Loopback-only** (default): If no token is set, only requests from `localhost` / `127.0.0.1` / `::1` are allowed. Safe for local use.

**Timing-safe comparison**: Token comparison uses `secrets.compare_digest()` instead of `==`. The reason: a normal string comparison short-circuits as soon as it finds a mismatch, so an attacker can measure response times to guess the token character by character. `compare_digest` always takes the same time regardless of where the mismatch is.

### Rate limiting

Rate-limited endpoints protect AI-backed operations (which cost money):
- **Coach ask**: 6 requests per minute per IP
- **Topics analyze-now**: 4 requests per minute per IP
- **Summary generate**: 2 requests per minute per IP
- **Summary from-transcript**: shares the same 2/min pool as summary generate

Implementation: a sliding window using a `deque` per IP address. Each request timestamp is appended. On each request, old timestamps (outside the 1-minute window) are removed. If the deque has >= limit entries, the request is rejected with HTTP 429.

The cleanup happens at request time — no background timer needed. This keeps the code simple and the memory usage proportional to actual traffic.

### Summary from-file endpoint

`POST /api/summary/from-transcript` accepts:
- an exported transcript CSV file,
- optional topic definitions JSON from the current UI state.

This route:
- parses CSV rows into normalized transcript utterances and renders prompt lines as `[MM:SS] [id:UXXXX] Speaker: text`,
- prepends optional agenda definitions context when provided,
- calls the same summary service used by live summaries,
- returns summary output directly; frontend loads it into the main Summary tab without mutating transcript/topic runtime state.

### Why config changes are blocked during a running session

Some config values (like capture mode, device IDs) are consumed once when the session starts. Changing them mid-session would have no effect on the running recognizers, which would be confusing. So the `/config` PUT endpoint returns an error if the session is running. The user must stop first.

---

## 13. Configuration System

### Pydantic model

All configuration lives in a `RuntimeConfig` Pydantic model. Pydantic validates every field on assignment — wrong types, out-of-range values, and invalid enum values all raise errors before any code runs.

Config is persisted to `web_translator_settings.json`. On startup, the app tries to load this file. If it doesn't exist, it uses defaults.

### Why `get()` returns a copy

The `ConfigStore.get()` method returns a Pydantic model copy, not a direct reference to the stored object. This means callers cannot accidentally mutate the stored config without going through the proper `set()` method. It's a defensive pattern to prevent "who changed this?" bugs.

### Separate lock for config

The config store has its own independent lock — it does not share the main `RLock`. Config reads/writes are infrequent and never need to be atomic with transcript or coach operations. Keeping a separate lock avoids unnecessary contention on the main shared lock.

---

## 14. Watchdog Loop

The watchdog is an async task that runs every 1 second during a session. It checks two things:

### Auto-stop on silence

If no speech activity has been detected for longer than `auto_stop_silence_sec` (default: 75 seconds), the watchdog automatically stops the session. "Speech activity" means any partial or final result from the Azure SDK — not just committed finals. The timestamp `last_speech_activity_ts` is updated by both partial events (live preview) and final events (committed sentences). This prevents runaway sessions when a user forgets to click Stop.

Setting this to 0 disables auto-stop entirely (useful for testing or long pauses).

### Session duration limit

If the session has been running longer than `max_session_sec` (default: 3600 = 1 hour), the watchdog stops it. This prevents unbounded recording and protects against accidentally leaving the app running.

### Periodic topic analysis

The watchdog also triggers the topic agent on a schedule (default every 60 seconds). After each trigger, it waits for the result before scheduling the next one. This ensures topic analysis doesn't pile up if one run takes longer than the interval.

---

## 15. Windows Audio Devices

### How device enumeration works

Azure Speech SDK can be told to listen on a specific audio device (not just the default microphone). To show the user a friendly list of devices, the app reads directly from the **Windows Registry** at:

`HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture`

Each sub-key is a device, with properties stored as binary values. The app extracts:
- **Friendly name** (e.g., "Microphone (Realtek Audio)")
- **Endpoint ID** (the GUID that Azure SDK uses to select the device)
- **State** (only enabled devices are returned)

This is Windows-specific. On other platforms, the registry doesn't exist and device enumeration returns an empty list.

### Virtual audio cables

For dual mode to work (separate local + remote audio), you typically need a virtual audio cable application (e.g., Voicemeeter, VB-Cable). This creates a virtual input device that captures whatever is playing through your speakers — effectively a loopback from the remote call audio.

---

## 16. Design Trade-offs You Should Know

These are decisions where there was a real choice between approaches. Being able to explain the reasoning shows architectural thinking.

### One RLock vs. per-module locks

**Chosen**: One shared RLock.
**Alternative**: Separate locks per module with careful acquire ordering.
**Why**: The operations that span modules (speech event → transcript + coach + topics) need to be atomic. With multiple locks, you'd need to define a consistent acquisition order to avoid deadlock — complex and error-prone. One lock is simpler and correctness is guaranteed.

### Coach queue depth = 1

**Chosen**: Keep only the latest pending trigger.
**Alternative**: Queue all triggers (unbounded) or use a fixed-size queue.
**Why**: The coach hint is only useful if it's timely. A hint about something said 30 seconds ago is less useful than one about the most recent statement. If the queue overflows, you'd rather process the latest than the oldest.

### Sliding window rate limiting vs. fixed window

**Chosen**: Sliding window (deque of timestamps).
**Alternative**: Fixed window (reset counter every minute).
**Why**: Fixed windows have a loophole — send 6 requests at 00:59 and 6 more at 01:01 for 12 requests in 2 seconds. Sliding window prevents this: only 6 per any rolling 60-second window.

### Bleed suppression window: 1.6 seconds

**Chosen**: 1.6 seconds.
**Why**: Empirically chosen to cover audio propagation + SDK processing delay. Too short = echo gets through. Too long = legitimate replies from the local speaker get muted.

### Translation: deque maxlen = 240 for median

**Chosen**: Rolling window of 240 samples.
**Why**: 240 translations at roughly one per 2-3 seconds = about 8-12 minutes of history. Long enough to be statistically meaningful, short enough to reflect current network conditions rather than what the network was doing an hour ago.

### `asyncio.to_thread` for AI agent calls

Both coach and topic agent calls are blocking HTTP requests (they call the Azure AI Foundry REST API synchronously). Running them directly in the event loop would block all other async operations — no WebSocket sends, no route handling — for the duration of the API call (often 2-10 seconds).

`asyncio.to_thread()` runs the blocking call on a thread pool thread, so the event loop stays free. The `await` waits for the result without blocking anything else.

---

## 17. Summary Intelligence and From-File Analysis

### Deterministic summary topic timing

Topic timing in summary is now resolved in backend Python from utterance IDs:

1. The prompt asks the model to return `topic_key_points` with `utterance_ids` (e.g., `U0001`).
2. Transcript rows already contain deterministic per-utterance durations.
3. Backend maps `utterance_ids` to those durations and computes `estimated_duration_minutes`.
4. If the model omits some utterances (while still assigning others), backend appends `Unassigned / Other` to preserve full duration coverage.

This removes dependence on model-side time math and makes durations reproducible across runs.

### Output fields to know

- `topic_key_points`: grouped key points by topic, `utterance_ids`, origin (`Agenda` or `Inferred`), with `estimated_duration_minutes` resolved deterministically in backend.
- `topic_breakdown`: UI timeline data (`name`, `planned_min`, `actual_min`, `status`, `over_under_min`).
- `agenda_adherence_pct`: computed when planned minutes exist, using continuous adherence formula `sum(min(actual, planned)) / sum(planned)`.

---

*Last updated: 2026-02-27*
