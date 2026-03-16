# Product Overview

> Public-facing overview of Live Meeting Copilot.
> This document explains the product, its users, and its user-visible capabilities without going deep into internal implementation details.

---

## Table of Contents

1. [What It Is](#1-what-it-is)
2. [Problem It Solves](#2-problem-it-solves)
3. [Who It Is For](#3-who-it-is-for)
4. [Core Capabilities](#4-core-capabilities)
5. [How a Session Works](#5-how-a-session-works)
6. [Feature Walkthrough](#6-feature-walkthrough)
7. [UI and UX Highlights](#7-ui-and-ux-highlights)
8. [Deployment and Runtime Model](#8-deployment-and-runtime-model)
9. [Technology Stack](#9-technology-stack)
10. [Known Constraints](#10-known-constraints)
11. [What Makes It Strong Technically](#11-what-makes-it-strong-technically)

---

## 1. What It Is

Live Meeting Copilot is a Windows-based real-time meeting intelligence application.

It listens to a live meeting, produces an English transcript, optionally translates that transcript into Arabic, optionally provides live AI coaching suggestions, and can generate a structured post-meeting summary with action items, decisions, risks, topic coverage, and meeting insights.

The application runs locally on the user's machine. The app itself is not cloud-hosted, but it uses Azure AI services for speech, translation, and optional AI features.

---

## 2. Problem It Solves

Many live meetings create three simultaneous needs:

- understand what is being said right now
- respond intelligently while the conversation is still happening
- preserve a useful, structured record of what happened afterward

Live Meeting Copilot addresses all three in one workflow:
- live transcript for immediate visibility
- live Arabic translation for bilingual meetings
- AI coaching for time-sensitive response support
- structured summary for post-meeting follow-up

---

## 3. Who It Is For

- bilingual meeting participants who need English-to-Arabic live translation
- professionals in high-stakes calls, interviews, negotiations, or sales conversations
- meeting facilitators who want agenda coverage and post-meeting structure
- anyone who wants searchable, exportable meeting records instead of unstructured notes

---

## 4. Core Capabilities

### Live Speech Transcription

- real-time English speech recognition
- support for single-input or dual-input capture modes
- speaker-separated transcript flow in dual-input mode
- automatic per-channel recovery from some Azure idle-channel timeouts

### Live English-to-Arabic Translation

- live Arabic updates during speech
- committed Arabic translation for finalized utterances
- optional higher-quality second-pass Arabic improvement for committed rows
- live translation telemetry for latency and estimated cost tracking

### Live AI Coaching

- optional meeting-time coaching suggestions
- automatic suggestions after eligible speaker turns
- manual coach prompting at any time during the session
- conversation continuity across coach interactions

### Structured Meeting Summary

- executive summary
- key points
- action items
- decisions made
- risks and blockers
- key terms defined
- topic coverage and adherence
- meeting insights and keyword index

### Agenda and Topic Definitions

- configurable topic definitions in Settings
- planned vs actual topic breakdown in summary output
- visual topic journey and coverage displays

### Export and Re-Analysis

- transcript export in JSON or CSV
- summary export in JSON or text
- upload of exported transcript CSV for offline summary generation

---

## 5. How a Session Works

1. Open the application in the browser UI on the local machine.
2. Configure speech, translation, coach, summary, and topic settings.
3. Start the session.
4. Watch live English transcript and optional Arabic translation update in real time.
5. Receive coach suggestions if enabled.
6. Stop the session when the meeting ends.
7. Review the generated summary, insights, and topic coverage.
8. Export transcript or summary if needed.

---

## 6. Feature Walkthrough

### Transcript Experience

The transcript view is the primary live workspace.

It includes:
- dual-column English and Arabic display
- live partial strip for current speech hypotheses
- draggable divider for resizing the live partial area
- bookmarkable transcript rows
- bookmark notes and bookmark jump list
- bookmark filtering
- inline coach-hint indicators
- transcript search
- live counters for entries and bookmarks

### Coach Experience

The coach view is designed for fast, low-friction guidance during a meeting.

It includes:
- manual coach prompt input
- current recommendation display
- older/newer navigation through session hints
- coach pending status feedback

### Summary Experience

The summary view turns raw transcript data into a structured meeting record.

It includes:
- executive summary
- key points
- action items
- decisions and risks
- meeting health and speaking insights
- keyword index
- agenda-vs-actual topic breakdown
- visual topic journey and topic coverage
- from-file analysis workflow

### Settings Experience

The settings area supports:
- speech provider and capture mode selection
- device selection for dual-input Azure sessions
- translation toggles and interval tuning
- coach enablement and tuning
- summary enablement and topic timing mode
- session limits
- topic definitions
- appearance preferences such as theme and fonts

### Logs Experience

The logs view provides built-in operational visibility.

It supports:
- severity filtering
- search
- compact mode
- pinned incidents
- copy, clear, and export actions

---

## 7. UI and UX Highlights

- single-page browser UI
- transcript-first working layout
- draggable transcript/live divider for layout control
- bookmark system with optional notes and quick-jump list
- configurable themes
- responsive navigation for smaller screens
- automatic WebSocket reconnect handling
- snapshot-based state restoration on reconnect
- local persistence of selected UI preferences
- accessibility-focused interaction states and labels
- toast notifications for non-blocking feedback

---

## 8. Deployment and Runtime Model

Live Meeting Copilot is designed as a local-first application:

- backend runs locally as a FastAPI service
- frontend is served locally as a browser-based SPA
- no remote hosting of the application is required
- Azure AI services provide speech, translation, and optional AI features

The application is intended for Windows usage because its capture model depends on Windows audio-device behavior and, in some configurations, Windows-specific audio routing tools.

---

## 9. Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, Uvicorn |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Primary speech recognition | Azure Speech SDK |
| Alternate speech recognition | Nova-3 preview |
| Translation | Azure Translator API |
| AI coaching and summary | Azure AI Foundry |
| Real-time transport | WebSocket |
| Packaging | PyInstaller EXE and deployable package variants |

---

## 10. Known Constraints

- summary generation uses a bounded recent transcript window rather than unlimited historical context
- uploaded transcript analysis is limited to exported CSV input and bounded file size
- Nova-3 support is currently a preview path with opinionated runtime behavior
- the application is intentionally loopback-only for browser/API access
- Azure and optional AI agent dependencies must be configured before related features can be used

---

## 11. What Makes It Strong Technically

- local-first runtime model
- deterministic topic timing and summary enrichment
- bounded-cost design for paid AI operations
- live transcript remains non-blocking while translation and coaching run asynchronously
- resilient handling of live concurrency and async patching
- graceful degradation when optional AI features are unavailable
- strong operational visibility through logs, telemetry, and reconnect state sync
