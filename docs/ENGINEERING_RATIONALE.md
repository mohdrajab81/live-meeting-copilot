# Engineering Rationale

> This document explains why the system is designed the way it is.
> It owns tradeoffs, historical evolution, and plain-English explanations of tricky implementation choices.
> Exact contracts and normative behavior live in `ARCHITECTURE.md`.

---

## Table of Contents

1. [Purpose and Audience](#1-purpose-and-audience)
2. [Design Goals](#2-design-goals)
3. [Big Picture](#3-big-picture)
4. [Concurrency Problem](#4-concurrency-problem)
5. [Shared Lock Rationale](#5-shared-lock-rationale)
6. [Azure Speech Runtime Behavior](#6-azure-speech-runtime-behavior)
7. [Buffer Overflow and Auto-Restart](#7-buffer-overflow-and-auto-restart)
8. [Dual Mode and Bleed Suppression](#8-dual-mode-and-bleed-suppression)
9. [Translation Journey](#9-translation-journey)
10. [Translation Identity and Staleness Model](#10-translation-identity-and-staleness-model)
11. [Coach Orchestrator Rationale](#11-coach-orchestrator-rationale)
12. [Summary Design Rationale](#12-summary-design-rationale)
13. [Watchdog and Finalization](#13-watchdog-and-finalization)
14. [API Design Tradeoffs](#14-api-design-tradeoffs)
15. [Configuration Tradeoffs](#15-configuration-tradeoffs)
16. [Windows Audio Realities](#16-windows-audio-realities)
17. [Key Tradeoffs and Alternatives](#17-key-tradeoffs-and-alternatives)
18. [Known Constraints with Rationale](#18-known-constraints-with-rationale)
19. [Evolution Notes](#19-evolution-notes)

---

## 1. Purpose and Audience

This file is for:
- engineers onboarding to the codebase
- maintainers trying to understand why a pattern exists
- interview preparation and technical storytelling
- future contributors deciding whether a current design should be changed

This file is not the contract source of truth. It is the explanation source of truth.

---

## 2. Design Goals

The system is shaped by five primary goals:

- low-latency live transcript updates
- deterministic correctness where facts matter
- bounded cost when paid AI services are involved
- resilience under mixed thread/async execution
- good operator visibility when something goes wrong

Several design decisions that might look unusual make sense only in the context of these goals.

---

## 3. Big Picture

At a high level, the application does this:

1. capture speech from one or two sources
2. turn that speech into live English text
3. optionally translate the text into Arabic
4. optionally ask an AI coach for timely suggestions
5. optionally turn the completed session into a structured summary

That sounds simple until you add the real constraints:
- the speech SDK emits callbacks from its own background threads
- the web server and WebSocket stack run on an asyncio event loop
- translation and agent calls are network-bound and can be slow
- the transcript must stay correct under out-of-order async completions
- the UI must keep feeling live even when some subsystems lag

The rest of this document explains how those constraints shaped the design.

---

## 4. Concurrency Problem

The central concurrency problem is that the application lives in two worlds at once:

- the speech backend world, which fires callbacks from background threads
- the FastAPI world, which expects async work on a single event loop

Why this matters:
- you cannot safely `await` inside a random SDK callback thread
- you cannot let a slow blocking network call freeze the event loop
- you cannot allow two concurrent state updates to interleave halfway through a transcript mutation

The practical answer was:
- normalize speech callbacks into simple events
- bridge from thread callbacks into the event loop with `asyncio.run_coroutine_threadsafe`
- move blocking coach and summary calls into worker threads with `asyncio.to_thread`
- centralize shared mutable runtime state under one lock

This is not the most theoretically elegant design. It is the most robust design for this particular mix of libraries and runtime models.

---

## 5. Shared Lock Rationale

The system uses one shared `threading.RLock` across the controller modules that coordinate runtime state.

Why one shared lock instead of many smaller locks?

Because the real unit of correctness is not "one module at a time." The real unit is "one cross-cutting state transition at a time."

When a final utterance arrives, the system may need to:
- append the utterance to transcript state
- clear live partial state for that speaker
- update last-speech-activity timestamps
- decide whether coach should trigger
- prepare translation work
- apply bleed suppression policy in dual mode

If those actions are not treated atomically, subtle race conditions appear:
- coach may reason on a transcript row that has not been appended yet
- translation may patch a row that was already cleared or superseded
- stop/reset may occur halfway through state changes

The shared `RLock` deliberately chooses simplicity and correctness over fine-grained parallelism.

The `_unlocked` naming convention is also intentional. It makes the lock contract visible in the code instead of hiding it.

---

## 6. Azure Speech Runtime Behavior

Azure Speech emits two kinds of useful text:

- partial text while the speaker is still talking
- final text after the SDK commits an utterance

This distinction drives the entire transcript design:
- partials are volatile and can change many times
- finals are stable and are the only safe point for durable transcript logic such as coach triggering and final Arabic patching

Two timeouts matter:
- end silence timeout controls when a sentence is considered finished
- initial silence timeout controls how long the recognizer waits before giving up on an empty recognition attempt

These are utterance-level behaviors, not session-level controls.

That distinction matters because a long-running meeting can still be active while individual recognizer attempts start and stop underneath it.

---

## 7. Buffer Overflow and Auto-Restart

One of the most important production lessons in the project is that Azure Speech sessions can become unhealthy during long silent periods.

Observed behavior:
- after extended silence, Azure-side transport can time out
- when speech resumes, the client buffer can overflow before the old channel drains
- the SDK reports a cancellation with the message `client buffer exceeded`

Naive response:
- treat every cancellation as fatal
- stop the entire session

Why that is wrong:
- in dual mode, one channel may be healthy while the other goes idle
- killing both channels creates unnecessary disruption
- the error is recoverable in common idle cases

Implemented response:
- detect the specific recoverable cancellation
- restart only the affected Azure recognizer
- leave the other channel running

This is a strong example of the design principle used throughout the app: degrade locally when possible, not globally.

---

## 8. Dual Mode and Bleed Suppression

Dual mode introduces a physical-world problem that software alone cannot fully eliminate: microphone bleed.

The problem:
- remote participant audio comes out of the speakers
- the local microphone picks up some of that audio
- the same sentence can appear once on the remote channel and again as delayed local echo

Without suppression, the transcript becomes misleading and downstream analytics get worse.

The chosen suppression design has two layers:

- active bleed suppression: if remote has a live partial right now, suppress local immediately
- recent activity suppression: if remote was active very recently, keep suppressing local for a short window

Why this is better than exact text deduplication:
- echo often arrives with timing and wording drift
- waiting to compare full text is too late for live suppression
- speaker-channel activity is a cheaper and more robust signal in real time

Why the window matters:
- too short: echo slips through
- too long: legitimate local replies get suppressed

The production-tuned window is 1.6 seconds. That number was chosen empirically: long enough to cover speaker playback plus recognizer lag in common setups, short enough to avoid muting real local replies during normal back-and-forth conversation.

This is a tuned compromise, not a mathematically perfect solution.

---

## 9. Translation Journey

The translation design evolved in four stages.

### Stage 1: Streaming Translation

The most direct idea was to translate the live speech stream continuously.

Why it was rejected:
- Arabic output flickered constantly as English partials changed
- users could not comfortably read text that rewrote itself every few moments
- every unstable partial cost money

Technically elegant, product-wise bad.

### Stage 2: Throttled Partial Translation

The next step was to keep live partial translation but throttle how often it is sent.

Why it helped:
- lower API usage
- less visual churn
- still gave live Arabic feedback

New problem discovered:
- a request sent for an older partial can return after a newer partial is already visible

That led directly to revision-based staleness guards.

### Stage 3: Final Translation Patching

Committed utterances became the stable unit for durable Arabic translation.

Why this is better:
- the user gets a final trustworthy row
- translation requests correspond to stable transcript units
- async patching is predictable

This stage introduced `segment_id` and revision identity to match translated text back to the correct transcript row.

### Stage 4: Optional Shadow Final Translation

The final step was separating speed from quality:
- fast path: standard translator result
- quality path: optional LLM-based second pass

Why this matters:
- users do not wait on the high-latency path
- terminology can improve later without blocking the main experience
- failure of the second pass does not degrade the baseline experience

This is one of the cleanest examples in the system of layered quality rather than single-path perfectionism.

---

## 10. Translation Identity and Staleness Model

The translation system is built around three simple identity tools:

- per-speaker revisions
- per-segment IDs
- generation counters

### Revisions

Every live partial update increments revision.

Why:
- old partial results should not overwrite newer visible text
- integer monotonicity is simpler and less error-prone than timestamp reasoning

### Segment IDs

Every committed utterance has a stable `segment_id`.

Why:
- multiple finals can be translated asynchronously
- results must be patched onto the exact correct row
- queue order is not a safe proxy for transcript identity

### Generation Counters

Generation increments on reset/stop.

Why:
- in-flight work from a previous session must not patch state after a reset
- a simple generation mismatch cleanly invalidates stale async work

This is an intentionally pragmatic design. It avoids distributed-systems-style complexity by using simple local identity primitives.

---

## 11. Coach Orchestrator Rationale

The coach is useful only if it is timely.

That single fact drives most of the coach design.

### Why trigger on final utterances

Partials are too unstable for meaningful coaching prompts.

Using finals gives:
- stable language to reason about
- clearer turn boundaries
- fewer pointless coach calls

### Why incremental prompting

Resending the full transcript on every coach call is wasteful and eventually noisy.

The chosen model sends only the transcript delta since the last coach request, while relying on conversation continuity to preserve context.

### Why persistent conversation continuity

Conversation state in the agent is cheaper and semantically cleaner than rebuilding full context each time.

This also makes the coach more coherent across a session.

### Why queue depth = 1

If the coach is already busy, a backlog of old triggers is mostly useless.

Three choices existed:
- queue nothing and miss opportunities
- queue everything and produce stale hints
- keep only the latest pending trigger

The app chooses the latest-only option because live usefulness beats completeness here.

### Why resume without cooldown

If a trigger waited in queue while the coach was busy, applying cooldown again would punish the user twice.

Ignoring cooldown on resumed queued work is intentional.

---

## 12. Summary Design Rationale

Summary generation combines AI and deterministic code on purpose.

### Why not trust the model for everything

Models are good at:
- writing narrative
- grouping semantically related statements
- extracting structured text

Models are not consistently good at:
- exact durations
- exact coverage totals
- reproducible percentage math

So the system draws a line:
- AI for language tasks
- code for factual computation

### Why sort by `start_ts`

In dual-recognizer mode, arrival order can diverge from speech order.

If the summary model sees utterances in the wrong order, topic grouping and timeline understanding degrade immediately.

### Why use utterance IDs

Asking the model to return `utterance_ids` is a compromise:
- the model still groups the language
- the backend computes deterministic durations from the transcript itself

### Why repair topic coverage

Model output may omit or misassign some utterances.

Repair logic guarantees:
- every utterance is accounted for
- duration coverage stays complete
- agenda adherence is computed against a full assignment, not a partial guess

### Why append `Unassigned / Other`

Because dropping unmatched speech would silently distort time allocation.

It is better to admit uncertainty explicitly than to hide it.

---

## 13. Watchdog and Finalization

The watchdog is both an operational safety feature and a cost-control feature.

### Why auto-stop exists

Without auto-stop:
- a forgotten session can run indefinitely
- translation and AI costs can accumulate unexpectedly
- users may lose trust in unattended runtime behavior

### Why there are two limits

Silence limit protects against abandoned sessions.
Max-session limit protects against runaway total runtime.

These are different failure modes and need different controls.

### Why summary is attempted before cleanup

If a meeting timed out and the app simply stopped, the user would lose the final artifact they likely cared about most.

The system therefore tries to flush summary before final cleanup on async stop paths.

That attempt is intentionally bounded. The stop path wraps summary generation in `asyncio.wait_for(..., timeout=60.0)` so a hung or slow summary call cannot block session cleanup forever. This is a production guard, not just a convenience.

### Finalization invariant

Runtime state reset must be safe regardless of how stop is reached:
- user stop
- auto-stop
- backend status transition to stopped

This is why reset/cleanup paths are intentionally idempotent and generation-based invalidation exists for background workers.

---

## 14. API Design Tradeoffs

### WebSocket vs Polling

Polling would be simpler conceptually but worse in practice:
- higher overhead
- delayed partial updates
- more state-sync edge cases

WebSocket is the correct choice for transcript-like live updates.

### Sliding Window vs Fixed Window Rate Limiting

Fixed windows allow burst loopholes at minute boundaries.

Sliding windows are slightly more stateful but much more accurate for paid AI operations.

### Localhost-Only Access

Adding remote browser auth and remote deployment support would multiply complexity:
- auth token design
- CORS considerations
- deployment hardening
- session security

This app deliberately avoids that surface area.

### Blocking Config Changes While Running

Some runtime settings only matter at session start.

Allowing them to change mid-session would create a worse user experience than a hard `409` because it would look like the config applied when it did not.

---

## 15. Configuration Tradeoffs

The app uses three ownership zones because one config system was not enough.

### `.env`

Best for:
- secrets
- service endpoints
- deployment-time agent bindings

### Runtime Config

Best for:
- operational toggles
- session behavior
- UI-selected meeting behavior

### Azure Portal

Best for:
- hosted agent persona
- model-level hosted configuration

This separation keeps each type of configuration where it changes at the right cadence.

---

## 16. Windows Audio Realities

This application is unapologetically shaped by Windows audio behavior.

### Device Enumeration

Capture-device discovery is Windows-specific and registry-based.

That is not glamorous, but it is practical and stable for the target environment.

### Azure Dual Mode

Azure dual mode usually depends on explicit device routing, often through virtual audio tools such as VB-CABLE or Voicemeeter.

Why that matters:
- it is operationally more fragile
- but it gives explicit control over local and remote channels

### Nova-3 Preview

Nova-3 preview deliberately uses a more opinionated model:
- default microphone
- default WASAPI loopback

Why:
- easier setup for the preview path
- less manual routing

Tradeoff:
- less configurability
- more assumptions about system defaults

---

## 17. Key Tradeoffs and Alternatives

### One Shared Lock vs Many Smaller Locks

Chosen:
- one shared runtime `RLock`

Alternative:
- per-module locks with strict acquisition ordering

Reason for current choice:
- much easier correctness story
- lower risk of deadlock
- acceptable performance for this workload

### Queue-Latest vs Queue-All for Coach

Chosen:
- queue latest only

Alternative:
- queue all pending triggers

Reason for current choice:
- timeliness matters more than completeness

### Deterministic Durations vs Model-Estimated Durations

Chosen:
- deterministic duration calculation from transcript data

Alternative:
- trust the model's time estimates

Reason for current choice:
- reproducibility
- predictable totals
- easier debugging

### Optional Shadow Translation vs Blocking for Quality

Chosen:
- fast baseline translation now, optional improved translation later

Alternative:
- block until the highest-quality translation is ready

Reason for current choice:
- preserves real-time feel
- degrades gracefully

### Rolling Telemetry Window vs Full Historical Window

Chosen:
- bounded latency history

Alternative:
- keep all historical samples

Reason for current choice:
- bounded memory use
- a 240-sample window is long enough to smooth out short spikes
- the retained window reflects roughly the recent several minutes of network behavior instead of stale early-session conditions

---

## 18. Known Constraints with Rationale

### 500-Utterance Summary Window

Why it exists:
- prompt cost control
- bounded latency
- predictable context size

Tradeoff:
- very long sessions are summarized from the latest transcript window, not the entire historical session.

### 5 MB Transcript Upload Limit

Why it exists:
- bounded request size
- predictable parsing cost
- safer offline re-analysis behavior

### Manual Coach Prompt Limit

Why it exists:
- bounded request size
- abuse control
- more consistent coach latency

### History Caps

Why they exist:
- coach hints, logs, finals, and latency windows are bounded to keep runtime memory predictable

### Nova-3 Preview Constraints

Why they exist:
- simplified preview path
- faster onboarding for alternate STT testing

Tradeoff:
- fewer knobs than the Azure dual-input path

---

## 19. Evolution Notes

This section captures important implementation lessons that matter to future maintainers.

### Translation Evolution

The translation system moved away from naive always-live translation toward:
- throttled partials
- committed-final patching
- optional quality-improvement second pass

That progression reflects real UX and cost lessons, not just code preference.

### Buffer Overflow Recovery

The Azure idle-buffer overflow issue was not obvious from API documentation. The per-channel restart behavior is there because real sessions proved it was necessary.

Future maintainers should be careful not to "simplify" this back into a global-stop behavior.

### Bleed Suppression

Dual-mode echo suppression exists because transcript correctness degraded in real use. It is not just an academic guard.

Future maintainers should treat suppression-window changes as behavior tuning, not cosmetic refactoring.

### Summary Determinism

The summary pipeline intentionally moved away from trusting AI for timing facts.

Future maintainers should preserve that split unless there is strong evidence that another design is equally reproducible.

### Topic Tracking Simplification

Topic orchestration is currently definitions-only. Earlier ideas around richer live topic tracking were removed in favor of a cleaner one-shot summary-driven model.

This is a simplification, not a regression in architecture clarity.

### Future Extension Points

Likely future areas:
- richer summary schemas
- stronger export workflows
- broader offline analysis
- more formal prompt/version management
- broader speech backend maturity beyond preview paths

Any future expansion should preserve the current documentation ownership rule:
- contracts in `ARCHITECTURE.md`
- reasons in `ENGINEERING_RATIONALE.md`
