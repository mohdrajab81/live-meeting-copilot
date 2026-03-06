# Product Backlog — Live Meeting Copilot
## Post-V2 Strategic Feature Pipeline

> **Scope:** This document captures all product strategy, competitive analysis, and feature
> ideas discussed after V2_PLAN.md was locked. Nothing here changes V2. Everything here
> feeds V2.1, V3, and beyond.
>
> Last updated: 2026-03-05

---

## Table of Contents

1. [Competitive Landscape](#1-competitive-landscape)
2. [Strategic Moat Analysis](#2-strategic-moat-analysis)
3. [High-ROI Feature Backlog](#3-high-roi-feature-backlog)
4. [Knowledge Grounding — Context Packs](#4-knowledge-grounding--context-packs)
5. [Meeting Intelligence — Read.ai-Inspired Features](#5-meeting-intelligence--readai-inspired-features)
6. [Cross-Meeting Memory and Commitment Tracking](#6-cross-meeting-memory-and-commitment-tracking)
7. [Arabic-Specific Differentiators](#7-arabic-specific-differentiators)
8. [Private Knowledge Connector — Enterprise/Government](#8-private-knowledge-connector--enterprisegovernment)
9. [Audio Capture Architecture — Web vs Desktop Evolution](#9-audio-capture-architecture--web-vs-desktop-evolution)
10. [Build Order and Phase Mapping](#10-build-order-and-phase-mapping)
11. [KPIs and Success Metrics](#11-kpis-and-success-metrics)

---

## 1. Competitive Landscape

### Direct competitors

| App | Core strength | Core weakness |
|---|---|---|
| Otter.ai | Live transcription, speaker ID | No real-time coach, English-only |
| Fireflies.ai | Integrations, post-meeting summaries | Post-meeting only, no live features |
| Krisp | Noise cancellation, meeting notes | Transcription-focused only |
| Avoma | Sales coaching cues, conversation intelligence | Limited live coach, English-only |
| Wingman / Clari Copilot | Real-time sales coaching, battlecards | Enterprise pricing, English-only, Teams/Zoom-locked |
| Chorus.ai (Zoominfo) | Enterprise sales coaching | Expensive, English-only, platform-locked |
| Read.ai | Engagement scores, sentiment, action items | Requires bot to join call, no Arabic |

### Full feature comparison

| Feature | **Our App** | Otter.ai | Fireflies | Avoma | Wingman | Chorus | Read.ai |
|---|---|---|---|---|---|---|---|
| Live transcription | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Speaker diarization | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Voice profile memory | ✅ opt-in | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Real-time AI coach | ✅ manual | ❌ | ❌ | ⚠️ limited | ✅ auto | ✅ auto | ❌ |
| On-demand topic analysis | ✅ | ❌ | ❌ | ⚠️ post | ⚠️ limited | ⚠️ limited | ❌ |
| Meeting summary | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Arabic live translation** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Works on any platform** | ✅ | ⚠️ plugin | ⚠️ plugin | ⚠️ plugin | ⚠️ plugin | ⚠️ plugin | ⚠️ plugin |
| **No meeting bot joins call** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Works in-person / offline meeting | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ |
| No audio stored on server | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Simple activation (no account) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Self-hostable | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Knowledge grounding (backlog) | 🔜 V2.1 | ❌ | ⚠️ limited | ❌ | ⚠️ limited | ⚠️ limited | ❌ |
| Sentiment analysis (backlog) | 🔜 V2.1 | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Speaker talk-time (backlog) | 🔜 V2.1 | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Cross-meeting memory (backlog) | 🔜 V3 | ❌ | ❌ | ❌ | ❌ | ⚠️ limited | ❌ |
| **Arabic code-switch retrieval** | 🔜 V3 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 2. Strategic Moat Analysis

### Key insight: no single feature is the moat

Knowledge grounding, sentiment analysis, and speaker analytics are individually table stakes
in 18 months — Microsoft Copilot, Notion AI, and Glean already do parts of this.

The moat is the **combination** targeting a specific underserved user:

```
Arabic code-switching retrieval
+ culturally-aware coaching tone (not Western sales norms)
+ system audio capture (invisible, no bot, no plugin)
+ privacy-first architecture (no audio stored server-side)
+ knowledge grounding with mandatory citations
+ cross-meeting commitment tracking
+ data sovereignty (Private Knowledge Connector for enterprise)
```

No Western vendor will invest in this combination for the Arabic-speaking professional market.
Each layer makes the product harder to replicate, and switching costs compound with every
meeting stored and every knowledge base connected.

### Target user (sharpen this before V3)

**Arabic-speaking professional in enterprise/government who:**
- Uses mixed platforms (Teams, Zoom, in-person, phone) — cannot use a platform-locked tool
- Switches between Arabic and English in the same conversation
- Operates in environments where a bot joining a call is culturally or legally unacceptable
- Needs a coach aware of Arabic business culture (relationship-first, hierarchy-sensitive)
- Works in a regulated sector (government, legal, medical, finance) with data sovereignty requirements

Microsoft Copilot exists but: requires full M365 E5, stores everything on Microsoft servers,
has no Arabic cultural awareness, and costs $30/user/month at pricing that does not fit the
target market.

### "Invisible, no-bot capture" — compliance note

System audio capture (getDisplayMedia) should be positioned as a **configurable mode**,
not a universal default. Legal and compliance requirements vary by organization and country.
Some orgs require explicit recording consent notifications. Add a configurable "consent banner"
option that the admin can enable per deployment. Default: on for pilot (single user),
opt-in for enterprise.

---

## 3. High-ROI Feature Backlog

Features ranked by value-to-effort ratio for your specific market. V2 is locked — these
target V2.1 and V3.

### Tier 1 — High ROI, Low Effort (V2.1)

---

#### BACKLOG-001 — Action Items Extraction

**What:** After every meeting, automatically extract explicit commitments, tasks, and
next steps from the transcript. Tag each item with the speaker who made the commitment
and surface them in the post-meeting summary.

**Why high ROI:**
- Most-used feature in Read.ai, Fireflies, and Otter by actual user surveys
- The coach already calls the LLM with full transcript for summary — action items
  are a second prompt on the same data, near-zero incremental cost
- Immediate, visible value that users can share with their team

**Implementation:**
```
POST /api/summary/generate (existing)
  → add second LLM call: extract_action_items(transcript)
  → return: [{ owner, action, deadline_mentioned, segment_index }]

UI: show action items in a separate card below summary
    allow user to copy as checklist or export to clipboard
```

**Effort:** 1 day (prompt engineering + UI card)

**Arabic note:** Prompt must handle Arabic commitments. Test with Arabic-dominant transcripts.

---

#### BACKLOG-002 — Speaker Talk-Time Visual

**What:** After meeting (or live, updating every 30s), show a horizontal bar chart of
what percentage of the meeting each speaker talked.

**Why high ROI:**
- Zero AI required — pure math from diarized transcript timestamps
- Managers and coaches react to this immediately
- Surfaces dominance imbalances, silent participants, and over-talkers

**Implementation:**
```python
# Already available in TranscriptStore
def talk_time_by_speaker(segments: list[Segment]) -> dict[str, float]:
    totals = defaultdict(float)
    for seg in segments:
        totals[seg.speaker] += seg.duration_seconds
    total = sum(totals.values())
    return {k: round(v / total * 100, 1) for k, v in totals.items()}
```

UI: horizontal stacked bar, color per speaker, live update via WebSocket.

**Effort:** 0.5 day

---

#### BACKLOG-003 — Sentiment Arc

**What:** Plot meeting sentiment (positive / neutral / negative) over time as a line chart.
Correlate dips and peaks with transcript segments so the user can see exactly what caused
the mood shift.

**Why high ROI:**
- One of Read.ai's most-screenshot features
- Gives a manager a single visual to assess meeting health
- Clickable timeline: click any point on the arc → jump to that moment in the transcript

**Implementation:**
```
Option A (fast): per-segment sentiment via LLM batch call at meeting end
Option B (live): lightweight local sentiment model (e.g. cardiffnlp/twitter-roberta-base-sentiment)
                 runs in background, no LLM cost

Recommend Option A for V2.1 (simpler), Option B for V3 (live + Arabic-aware)
```

**Arabic note:** Most sentiment models are English-only and perform poorly on Arabic or
code-switched text. For V2.1, run sentiment on the translated (English) segments. For V3,
invest in an Arabic-aware sentiment model (CAMeL-Lab/bert-base-arabic-camelbert-mix-sentiment
is a good candidate).

**Effort:** 1-2 days

---

#### BACKLOG-004 — Meeting Effectiveness Score

**What:** A single number (0–100) shown at the end of every meeting, combining:
- Talk-time balance (lower variance = higher score)
- Sentiment trend (positive trend = higher score)
- Action items density (more clear commitments = higher score)
- Meeting duration vs topics covered ratio

**Why high ROI:**
- Single shareable metric — easy for managers to track over time
- Creates a feedback loop: users want to improve their score
- Can be trended across meetings to show team communication health

**Formula (starting point, tune with real user data):**
```python
def meeting_score(
    talk_time_variance: float,   # lower = better
    sentiment_positive_pct: float,
    action_items_count: int,
    duration_minutes: float,
    topics_covered: int,
) -> int:
    balance = max(0, 100 - talk_time_variance * 2)
    sentiment = sentiment_positive_pct
    density = min(100, (action_items_count / max(duration_minutes, 1)) * 300)
    coverage = min(100, (topics_covered / max(duration_minutes, 1)) * 200)
    return int((balance * 0.3) + (sentiment * 0.3) + (density * 0.2) + (coverage * 0.2))
```

**Effort:** 1 day (depends on BACKLOG-002 and BACKLOG-003 being done first)

---

### Tier 2 — High ROI, Moderate Effort (V2.1–V3)

---

#### BACKLOG-005 — Pre-Meeting Brief

**What:** Before a recurring meeting starts, show a one-page brief:
- Summary of the last meeting with this group
- Open action items from last time (not yet marked done)
- Topics discussed previously
- Optional: "what to prepare" suggestion from coach

**Why high ROI:**
- Turns every recurring meeting into a continuation, not a restart
- Creates strong retention — users who use pre-meeting briefs churn at much lower rates
  (observed pattern across Otter, Fireflies data)
- Data is already in your DB — no new AI needed for the brief itself

**Requires:** Cross-meeting session linkage (same participants → same meeting series).
Group meetings by participant fingerprint or explicit user-created "meeting series."

**Effort:** 2-3 days

---

#### BACKLOG-006 — Interruption and Overlap Detection

**What:** Detect when a speaker is interrupted mid-sentence by another speaker.
Surface in post-meeting analytics:
- Who interrupts most
- Who gets interrupted most
- Interruption frequency over meeting timeline

**Why high ROI for your market:**
In Arabic business culture, interrupting a senior person is a significant cultural signal.
Being repeatedly interrupted is also meaningful. No Western tool surfaces this with
Arabic cultural context awareness.

**Implementation:**
```python
# Two overlapping speaker segments within a 0.5s window = interruption
def detect_interruptions(segments: list[Segment]) -> list[Interruption]:
    interruptions = []
    for i in range(1, len(segments)):
        prev, curr = segments[i-1], segments[i]
        if curr.start < prev.end - 0.5 and curr.speaker != prev.speaker:
            interruptions.append(Interruption(
                interrupter=curr.speaker,
                interrupted=prev.speaker,
                at_seconds=curr.start,
            ))
    return interruptions
```

**Effort:** 1-2 days

---

#### BACKLOG-007 — Filler Word Detection (Arabic-aware)

**What:** Count filler words per speaker, shown in post-meeting report.
Arabic filler words: يعني (ya'ni), كيف (kif), صح (sah), إيه (eh), يلا (yalla) used mid-sentence.
English filler words: um, uh, like, you know, basically, literally.

**Why high ROI:**
- Self-coaching tool for professionals who present or negotiate
- Arabic filler words are not caught by any existing tool
- High perceived value for sales, legal, and executive users

**Implementation:**
- Maintain a curated list of Arabic + English filler words (regional variants matter: Gulf vs Levantine vs Egyptian)
- Count occurrences in transcript per speaker
- Show as "filler word rate: 3.2/minute" with examples

**Effort:** 1 day (list curation is the main work)

---

## 4. Knowledge Grounding — Context Packs

### Concept

A **Context Pack** is a named collection of documents or folders the user selects before
a meeting. The coach retrieves relevant content from the active Context Pack when answering
questions, and every answer must include a citation or a "don't know" fallback.

This transforms the coach from generic AI to your company's institutional knowledge,
activated in real-time during your meetings.

### Why this is a core layer (not the moat alone)

BYO knowledge grounding is now standard in Microsoft Copilot agents and Notion AI.
The differentiation is in execution:
- Arabic code-switch retrieval (no competitor does this)
- Culturally-aware coaching tone (no competitor does this)
- Strict privacy / audit trail (no competitor offers this for the Arab market)
- No bot joining the call (infrastructure advantage)

### Coach response contract (mandatory from day one)

Every coach answer that uses a Context Pack must follow this structure:

```json
{
  "answer": "Your sales playbook recommends waiting until the third meeting before discussing discounts.",
  "citations": [
    {
      "source": "Sales_Playbook_Q1_2025.pdf",
      "page": 4,
      "excerpt": "Never introduce pricing flexibility before the third qualifying conversation."
    }
  ],
  "confidence": "grounded",
  "fallback": null
}
```

If `confidence == "none"`:
```json
{
  "answer": null,
  "citations": [],
  "confidence": "none",
  "fallback": "I could not find a grounded answer in your active Context Pack. Ask me to answer without sources, or add more documents to this pack."
}
```

**Rule:** Coach never guesses silently. Ungrounded confidence destroys trust faster than
admitting uncertainty. This is the biggest trust differentiator from generic AI coaches.

### Architecture — V2.1 (SharePoint, hybrid retrieval)

**Decision: online search + ephemeral session-level embedding. No full pre-indexing.**

Rationale:
- Lower cost than embedding whole SharePoint sites
- No stale index problems when files change
- Better compliance posture — no permanent copy of customer documents
- Faster to ship

```
Meeting session starts
  ↓
User selects Context Pack (e.g., "Sales Playbook + Client: Ahmed Corp")
  ↓
Coach call triggered (POST /api/coach/ask)
  ↓
1. Graph API search within selected SharePoint folders/files
   → returns top 5 document snippets matching coach query context
   ↓
2. Snippets embedded in-memory (ephemeral, TTL = session duration)
   → semantic re-rank against coach query
   ↓
3. Top 3 snippets injected into coach LLM prompt
   → coach answers with mandatory citations
   ↓
4. Audit log: session_id, query, sources_used, confidence, timestamp
```

**V2.1 simplification (pilot-safe):** Skip step 2 (ephemeral embedding) entirely.
Use Claude's large context window — inject top 5 snippets directly. Add embeddings
only when retrieval quality becomes the user complaint.

### SharePoint connector — Microsoft Graph API

```python
# Read-only, respects existing SharePoint ACLs automatically
async def search_sharepoint(
    query: str,
    folder_ids: list[str],
    access_token: str,
    top: int = 5,
) -> list[SearchResult]:
    response = await httpx_client.post(
        "https://graph.microsoft.com/v1.0/search/query",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "requests": [{
                "entityTypes": ["driveItem"],
                "query": {"queryString": query},
                "from": 0,
                "size": top,
            }]
        },
    )
    return parse_graph_results(response.json())
```

**Permission scope required:** `Files.Read.All` (delegated, user-consented).
Respects SharePoint item-level permissions — users cannot retrieve documents they
cannot access in SharePoint directly.

### Context Pack data model

```json
{
  "pack_id": "pack_abc123",
  "name": "Sales Playbook + Ahmed Corp",
  "owner_key_hash": "sha256...",
  "sources": [
    {
      "type": "sharepoint_folder",
      "folder_id": "01ABC...",
      "display_name": "Sales Playbook 2025",
      "item_count": 12
    },
    {
      "type": "sharepoint_folder",
      "folder_id": "01DEF...",
      "display_name": "Client: Ahmed Corp",
      "item_count": 7
    }
  ],
  "created_at": "2026-03-05T10:00:00Z",
  "last_used_at": "2026-03-05T14:30:00Z"
}
```

### Audit log (per coach answer)

```json
{
  "session_id": "sess_xyz",
  "timestamp": "2026-03-05T14:35:22Z",
  "query_summary": "discount policy before third meeting",
  "sources_searched": ["Sales_Playbook_Q1_2025.pdf", "Pricing_Guide_2025.xlsx"],
  "sources_cited": ["Sales_Playbook_Q1_2025.pdf"],
  "confidence": "grounded",
  "answer_tokens": 87
}
```

### Connector roadmap

| Connector | Version | Notes |
|---|---|---|
| SharePoint (via Graph API) | V2.1 | First and only connector for pilot |
| Google Drive | V2.2 | Second-most common in target market |
| Local files (drag-and-drop) | V2.2 | Fallback for non-M365 users |
| Confluence | V3 | Enterprise/tech teams |
| Private Knowledge Connector | V3 | See Section 8 |

---

## 5. Meeting Intelligence — Read.ai-Inspired Features

Read.ai's most valuable features, ranked by what to adopt and what to skip.

### Adopt

| Feature | Why adopt | Version |
|---|---|---|
| Action items extraction | Highest user retention driver | V2.1 (BACKLOG-001) |
| Speaker talk-time % | Zero AI, instant value | V2.1 (BACKLOG-002) |
| Sentiment arc over time | High insight, one chart | V2.1 (BACKLOG-003) |
| Meeting effectiveness score | Single shareable number | V2.1 (BACKLOG-004) |
| Pre-meeting brief | Strong retention / loyalty | V2.1 (BACKLOG-005) |
| Interruption detection | Culturally significant for Arabic market | V2.1 (BACKLOG-006) |
| Filler word detection | Arabic-aware, unique differentiator | V2.1 (BACKLOG-007) |

### Skip or defer

| Feature | Why skip/defer |
|---|---|
| Attention / "engagement" score | Requires webcam access, too invasive |
| Meeting replay with video | Requires recording — conflicts with privacy model |
| Calendar auto-join | Requires calendar integration, complex OAuth |
| Automatic recurring meeting linking | Defer to V3 (needs cross-session identity) |

### The one feature Read.ai doesn't have

**Commitment tracking across meetings** — see Section 6. This is the highest-value
feature that no competitor has and that directly leverages your architecture.

---

## 6. Cross-Meeting Memory and Commitment Tracking

### Concept

Every competitor treats each meeting as isolated. This is the biggest opportunity
in the space for your target user.

**Commitment tracking:** When a speaker says "I will send the proposal by Thursday"
or "we will confirm the budget next week," the system:
1. Extracts the commitment automatically at meeting end
2. Links it to the speaker identity (voice profile)
3. Surfaces it in the pre-meeting brief for the next meeting with that person
4. Marks it as "resolved" when it is mentioned and confirmed in a later meeting
5. Flags it as "overdue" if it was not mentioned in the next expected meeting

**Example alert in pre-meeting brief:**
> "In your last meeting with Ahmed Corp (2026-02-18), Ahmed said he would send
> the revised contract by 25 February. This has not been confirmed in any subsequent
> meeting."

No tool does this. It is not a meeting tool anymore — it is a **relationship intelligence layer.**

### Data model

```python
class Commitment(BaseModel):
    commitment_id: str
    session_id: str                    # meeting where commitment was made
    speaker_label: str                 # speaker who made it
    speaker_name: str | None           # if voice profile matched
    text: str                          # verbatim or paraphrased
    deadline_mentioned: str | None     # extracted from transcript ("by Thursday")
    deadline_date: date | None         # resolved deadline if parseable
    status: Literal["open", "resolved", "overdue"]
    resolved_in_session: str | None    # session where it was confirmed
    created_at: datetime
```

### Extraction prompt

```
From this meeting transcript, extract all explicit commitments, promises, and next steps.
For each one, identify:
- Who made the commitment (speaker label)
- What they committed to (verbatim or close paraphrase)
- Any deadline mentioned (exact or relative: "by end of week", "next Tuesday")

Return JSON array. If no commitments, return [].
Only include clear commitments, not vague intentions.
```

### Resolution detection

At each meeting end, run a second LLM call:
```
Given these open commitments from previous meetings, and this new meeting transcript,
identify which commitments were:
- Confirmed as done
- Explicitly deferred
- Not mentioned at all

Return status update for each commitment ID.
```

### Why this drives loyalty

Once a user has 3+ months of commitment history in the system, switching to any
other tool means losing that institutional memory. Switching cost becomes extremely high.
This is the retention mechanism that no competitor has.

---

## 7. Arabic-Specific Differentiators

These are features that no Western tool will build for at least 3-5 years, if ever.
They are the hardest layer to replicate and the core of the long-term moat.

### Arabic code-switching retrieval

Arabic professionals do not speak Arabic or English in meetings — they switch mid-sentence.
"نحن agreed على the timeline, لكن the budget needs تعديل."

Current state of all competitors: their NLP pipelines break or silently degrade on
code-switched text. Retrieval against a knowledge base fails on mixed-language queries.

**What to build:**
- Detect language switch at the segment level (already implicit in transcript)
- Generate bilingual embeddings for retrieval (multilingual-e5-large handles this well)
- Coach context includes both the Arabic and English form of key terms
- Knowledge base search uses both languages simultaneously

### Culturally-aware coaching

Western sales coaching coaches for Western norms:
- Urgency creation
- Objection handling with counter-pressure
- First-name informality from first contact
- Direct asks and closes

Arabic business culture runs on:
- Relationship and trust before business (do not rush to the proposal)
- Hierarchy respect (address senior people formally until invited otherwise)
- Indirectness as politeness (not evasion)
- Small talk as mandatory, not optional

A coach that says "you moved to the proposal before sufficient trust was established"
instead of "close faster" does not exist. Building it requires a curated cultural
coaching rule set, not just an LLM.

**Implementation path:**
- Start with a manually curated cultural rules file (YAML)
- Rules injected as system context into every coach call
- Examples: "If topic is pricing and < 2 rapport-building exchanges, suggest relationship first"
- Iterate rules based on user feedback during pilot

### Regional Arabic dialect awareness

Standard Arabic (MSA) is not how most professionals speak in meetings.
Dialects vary significantly:
- Gulf (Saudi, UAE, Kuwait, Qatar) — dominant in GCC enterprise
- Levantine (Jordan, Lebanon, Syria, Palestine) — dominant in tech and consulting
- Egyptian — most-watched media but not dominant in formal settings

Filler words, politeness markers, and commitment phrasing vary by dialect.
A single Arabic model trained on MSA misses all of this.

**V2.1:** Support Gulf dialect as primary (largest enterprise market).
**V3:** Configurable dialect profile per user or organization.

### Data sovereignty — NDMO and PDPL compliance

Saudi Arabia's National Data Management Office (NDMO) and UAE Personal Data Protection
Law (PDPL) both impose restrictions on sensitive data leaving certain geographic boundaries
and on processing personal data without explicit consent.

Your privacy-first architecture (no audio stored server-side) already puts you ahead.
For the enterprise/government market, add:
- Data residency option (Azure region: UAE North or Saudi Arabia)
- Explicit consent flow with audit trail for recording
- Data processing agreement (DPA) template for B2B sales
- "Consent mode" UI: user sees a clear banner that the meeting is being analyzed

---

## 8. Private Knowledge Connector — Enterprise/Government

### The problem with cloud-based knowledge grounding

For government, legal, medical, and financial organizations in the Arab world:
- Raw documents cannot leave the organization's boundary (NDMO, PDPL, internal policy)
- SharePoint cloud sync may not be permitted for classified or sensitive content
- External API calls with document content are not allowed

SharePoint Graph API (V2.1 approach) sends document snippets to your cloud backend.
For most enterprise customers this is acceptable. For government and regulated sectors, it is not.

### Solution: Private Knowledge Connector

A lightweight, signed desktop agent that runs on the user's machine or inside the
organization's network. It:
1. Reads allowed folders, SharePoint sync, or local files
2. Builds and maintains a local vector index (never leaves the machine)
3. When the cloud app sends a search query, the agent returns only top snippets + citations
4. Raw documents and the full index never leave the organization

```
Cloud app                           Local agent (on-premise)
    │                                     │
    │  ── query: "discount policy" ──→    │
    │                                     │  search local index
    │                                     │  retrieve top 3 snippets
    │  ←── snippets + citations ──────    │
    │                                     │
    │  (raw documents never sent)         │
```

### Technical requirements for the agent

- Signed binary (code signing certificate) — required for enterprise IT approval
- Auto-update mechanism with version pinning option for enterprises
- Index encrypted at rest (AES-256)
- ACL mapping: agent respects file system permissions, does not index files the running
  user cannot read
- Incremental reindex: detects file changes via filesystem watcher, updates only changed files
- Health check endpoint for IT monitoring
- Audit log: which files were indexed, which queries were answered, timestamps

### Build order

Do not build this in V2 or V2.1. Build it when:
- You have at least one enterprise/government prospect who specifically requires it
- The SharePoint connector is proven and stable
- You have a signed binary distribution pipeline in place

Estimated effort: 2-3 weeks for a production-quality agent.

### Positioning

Do not make this a mandatory step for all users. Position as:

> "Private Knowledge Connector — for organizations that require all documents to remain
> on-premise. Your meeting intelligence, zero data exposure."

This is the product story that wins government and regulated enterprise contracts.

---

## 9. Audio Capture Architecture — Web vs Desktop Evolution

### Current state (V2 — Windows focus)

On Windows, the web app captures audio via two browser APIs:

- **Mic:** `getUserMedia()` — fully reliable, no caveats.
- **Meeting audio:** `getDisplayMedia({ audio: true })` — reliable for Chrome tab meetings.
  For desktop apps (Teams desktop, Zoom desktop), requires the user to check
  **"Also share system audio"** in Chrome's share dialog.

This works well for the pilot. Windows is a solved problem for web-based capture.

### The Teams desktop problem

Teams desktop on Windows can suppress its own audio output when another app captures
the screen — to prevent feedback during a sharing session. This is a Teams behavior,
not a browser bug.

**V2 mitigation:** instruct pilot users to use **teams.microsoft.com** (browser) instead
of the Teams desktop app. Teams web audio capture is clean and fully reliable.
This is a valid instruction for a small pilot group with direct user contact.

For the longer term, this needs a proper native solution.

### Why not pivot to a full desktop app now

- V2 is planned, architected, and ready to build. Pivoting costs 3-4 weeks with no
  new user value delivered.
- Zero-install web is a deliberate pilot feature — users get a link, open it, done.
- Web deployment means instant updates with no versioning or distribution overhead.
- Native desktop apps require code signing, auto-update infrastructure, and installer
  distribution — real overhead that does not benefit a pilot.

**Decision (confirmed, cross-validated):** Stay web for V2. Evolve to hybrid in V2.1 and V3.

### The hybrid evolution path

The right long-term architecture is not a full rewrite. It is a **companion agent** model:

```
┌─────────────────────────────────────────────────┐
│  Web app (browser)  ←──────────────────────────┐│
│  - All UI, coach, topics, summary              ││
│  - Audio via getDisplayMedia (fallback)        ││
└────────────────────────────┬───────────────────┘│
                             │ ws://localhost:9001  │
                             │ (if agent installed) │
┌────────────────────────────▼───────────────────┐ │
│  Windows Companion Agent (optional, C#)        │ │
│  - WASAPI loopback → captures any app audio    │ │
│  - Streams PCM to web app via local WebSocket  │ │
│  - System tray, auto-start with Windows        │ │
│  - Signed binary, auto-update                  │ │
└────────────────────────────────────────────────┘
```

The web app detects whether the companion is running on `localhost:9001`. If yes, use
the native audio stream (covers all desktop apps cleanly). If no, fall back to
`getDisplayMedia` (covers browser-based meetings). Users who need Teams desktop install
the companion; others do not need to.

**Why C# for the companion:** it is your native language, WASAPI bindings are mature
in .NET (`NAudio` library), and it shares the same deployment story as the Private
Knowledge Connector (Section 8) — one installer, two features in V3.

### Tauri vs companion agent decision

A Tauri wrapper (web tech + native shell) is the alternative path — it wraps the entire
web frontend in a native app with access to WASAPI and the file system.

| | Companion Agent (C#) | Tauri Wrapper |
|---|---|---|
| Web app still works without it | ✅ Yes | ❌ Replaces web app |
| Reuse existing web frontend | ✅ Unchanged | ✅ Unchanged |
| Your language | ✅ C# | ⚠️ Rust for native layer |
| Installer size | Small (~5MB) | Smaller than Electron; size depends on app |
| Deployment model | Optional add-on | Full replacement of web delivery |
| When to choose | V2.1, additive | V3, when web delivery is no longer sufficient |

**Recommendation:** companion agent first (V2.1), Tauri evaluation deferred to V3
based on actual pilot demand.

### Audio capture capability matrix (Windows only, V2 scope)

| Meeting scenario | V2 (web only) | V2.1 (web + companion) |
|---|---|---|
| Google Meet (Chrome tab) | ✅ Tab audio | ✅ Tab audio |
| Teams web (Chrome tab) | ✅ Tab audio | ✅ Tab audio |
| Zoom desktop | ⚠️ "Share system audio" checkbox | ✅ WASAPI, seamless |
| Teams desktop | ⚠️ May suppress audio; use web version | ✅ WASAPI, seamless |
| In-person (mic only) | ✅ getUserMedia | ✅ getUserMedia |
| Any desktop app | ⚠️ System audio checkbox | ✅ WASAPI, seamless |

### Important wording clarifications

- **"Tauri is ~10MB, Electron is 150MB+"** — these are indicative, not fixed. Actual
  sizes vary significantly by app content and bundled assets. The meaningful difference
  is that Tauri uses the OS system webview while Electron bundles its own Chromium.

- **"Web cannot do local inference"** — web *can* run local models (WebGPU, ONNX Runtime
  Web, Transformers.js). However, for enterprise workloads at production scale, native
  inference is more reliable, performant, and operationally simpler. This is a
  reliability and ops concern, not an absolute capability limit.

- **"Teams web is feature parity with Teams desktop"** — not fully true. Microsoft
  maintains a list of features available only in the Teams desktop client (some
  meeting controls, background effects, certain admin features). For the audio capture
  use case, Teams web is sufficient. For power users with desktop-only features,
  the companion agent is the right answer.

### V2.1 companion agent — minimal spec

```csharp
// Responsibilities:
// 1. WASAPI loopback capture (all system audio)
// 2. Resample to 16kHz mono PCM (Deepgram requirement)
// 3. Stream via local WebSocket on ws://localhost:9001
// 4. System tray icon with start/stop control
// 5. Auto-start with Windows (registry key, user-level)

// Dependencies:
// NAudio        — WASAPI capture + resampling
// WebSocketSharp or System.Net.WebSockets — local WS server
```

**Security note:** the local WebSocket must only accept connections from `localhost`.
It must not bind to `0.0.0.0`. Add an origin check to reject non-localhost connections.

---

## 10. Build Order and Phase Mapping

### V2 (current — locked, do not change)

See V2_PLAN.md. Core infrastructure: Deepgram STT, manual coach, on-demand topics,
activation key auth, voice profiles opt-in.

### V2.1 — Meeting Intelligence + Windows Companion Agent

**Goal:** Full meeting intelligence layer + clean audio capture for all Windows scenarios.

Priority order (strict — do not parallelize):

1. **Speaker talk-time visual** (BACKLOG-002) — 0.5 day, zero risk
2. **Action items extraction** (BACKLOG-001) — 1 day, highest user value
3. **Sentiment arc** (BACKLOG-003) — 1-2 days
4. **Meeting effectiveness score** (BACKLOG-004) — 1 day, depends on 002 and 003
5. **Filler word detection — Arabic-aware** (BACKLOG-007) — 1 day
6. **Interruption detection** (BACKLOG-006) — 1-2 days
7. **Pre-meeting brief** (BACKLOG-005) — 2-3 days, depends on cross-session linking
8. **Windows Companion Agent** (Section 9) — 3-5 days, C#, optional install, WASAPI loopback

Total estimated effort: 11-16 days for the full V2.1 layer.

### V2.2 — Knowledge Grounding

**Goal:** Coach that knows your company's documents.

1. Context Pack data model + UI (pack selector in meeting start screen)
2. SharePoint connector (Microsoft Graph API, read-only)
3. Coach response contract (answer + citations + confidence + fallback)
4. Audit log per coach answer
5. "Don't know" fallback behavior (mandatory)
6. KPI tracking: citation acceptance rate, unanswered rate, answer latency

Total estimated effort: 5-7 days.

### V3 — Long-term Moat Layer

**Goal:** Features that are structurally hard for competitors to replicate.

1. Cross-meeting commitment tracking (Section 6)
2. Arabic code-switching retrieval
3. Culturally-aware coaching rule set (Gulf dialect first)
4. Pre-meeting brief (with cross-meeting memory)
5. Private Knowledge Connector — unified with companion agent into one installer (Section 8)
6. Configurable consent/compliance mode
7. Data residency option (Azure UAE North)
8. Tauri wrapper evaluation — only if web delivery becomes a bottleneck based on pilot demand

Total estimated effort: 4-6 weeks.

---

## 11. KPIs and Success Metrics

### V2.1 — Meeting Intelligence

| KPI | Target | Measurement |
|---|---|---|
| Action items extracted per meeting | ≥ 2 for meetings > 20 min | Count in DB |
| Sentiment arc accuracy (user rating) | > 70% "useful" | In-app thumbs up/down |
| Meeting score adoption | > 60% of users view it | Event tracking |
| Pre-meeting brief open rate | > 50% for recurring meetings | Event tracking |

### V2.2 — Knowledge Grounding

| KPI | Target | Measurement |
|---|---|---|
| Citation acceptance rate | > 65% of cited answers rated useful | In-app feedback |
| Unanswered rate (confidence = none) | < 20% of coach calls | Audit log |
| Answer latency with Context Pack active | < 4s p95 | Timing log |
| Context Packs created per active user | ≥ 1 within first week | DB count |

### Retention and moat indicators

| KPI | Target | Notes |
|---|---|---|
| D30 retention | > 40% | Above industry average for meeting tools (~25%) |
| Meetings per active user per week | > 3 | Indicates daily driver, not occasional tool |
| Context Packs per user | > 2 after 30 days | Indicates switching cost accumulation |
| Commitment items tracked | Growing week-over-week | Indicates cross-meeting memory adoption |

---

*This backlog is a living document. Update after every pilot feedback session.
Do not modify V2_PLAN.md based on this document — V2 is locked.*
