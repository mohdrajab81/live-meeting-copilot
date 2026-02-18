# Topic Agent — Response Handling & Edge Cases

This document covers every possible shape of response from the Topic Tracker agent,
how the code processes each one, and any known design decisions or minor quirks.

---

## Pipeline Overview

```
agent text output
  └─ TopicTrackerService._extract_json()          ← JSON extraction / refusal detection
       └─ payload.get("topics", [])[:30]           ← cap at 30 items
            └─ _normalize_results()
                 └─ _normalize_item()              ← per-item sanitisation
                      └─ _resolve_names_unlocked() ← name → canonical key
                           └─ _classify_incoming_unlocked()  ← confidence gate
                                └─ _apply_merge_unlocked()   ← merge into stored state
```

---

## System Prompt Rules (Quick Reference)

| Rule | What it says |
|---|---|
| 1 | `name` required for every object |
| 4 | Existing agenda names must be returned EXACT |
| 5 | Strong match threshold 0.65 |
| 6 | Below 0.65: ONE new topic if allow_new=true; nothing if false |
| 9 | Do NOT compute or return `time_seconds` |
| 12 | Each `key_statements.text` ≤ 15 words |
| 13 | Present but no new detail → `key_statements=[]`, `topic_presence=true` |
| 14 | `status="covered"` ONLY if explicit closure signal in chunk |
| 15 | Do not return absent/not_started topics |
| 16 | `topic_presence` for returned topics must be true |
| 17 | `match_confidence` in [0.0, 1.0] |
| 22/23 | New topics only: include `suggested_name` + `short_description` |
| 24 | Matched existing topics: OMIT `suggested_name` / `short_description` |

---

## All Possible Response Cases

### Case 1 — Normal valid response

```json
{
  "topics": [{
    "name": "Budget Review",
    "status": "active",
    "topic_presence": true,
    "match_confidence": 0.85,
    "key_statements": [{"ts": 1234567.0, "speaker": "Remote", "text": "Q3 budget overrun."}]
  }]
}
```

**Handling:** Full pipeline — name resolved to key, confidence gate passes, merged into
state, time allocated, broadcast fired.

---

### Case 2 — Empty topics (no assignment)

```json
{"topics": []}
```

**When:** `allow_new_topics=false` and no agenda topic reached 0.65, or chunk was
genuinely off-topic.

**Handling:** `items_raw=[]` → `normalized=[]` → `incoming_meta` empty → no topic state
changes → existing topics preserved unchanged → `topics_update` broadcast with unchanged
state. ✓

---

### Case 3 — New topic with suggested_name / short_description

```json
{
  "topics": [{
    "name": "Education Reform Debate",
    "suggested_name": "Education Reform",
    "short_description": "Discussion about reforming national school curriculum",
    "status": "active",
    "topic_presence": true,
    "match_confidence": 0.88,
    "key_statements": [...]
  }]
}
```

**Handling:**
- `_normalize_item`: reads `suggested_name` (validated by `_is_usable_new_name`),
  reads `short_description` → stored in `comments` (100-char cap).
- `_resolve_names_unlocked`: if `suggested_key` not in known topics AND `raw_key` not
  known either → canonical key becomes `suggested_key`, `name` updated to `suggested_name`.
- New topic stored under `suggested_name` with scope from `short_description`. ✓

**Note:** If the agent returns `suggested_name`/`short_description` for an **existing**
topic (breaking rule 24), the `comments` field for that topic is ignored — existing
comments are always preserved once set. ✓

---

### Case 4 — Topic present but no new detail (empty statements)

```json
{
  "topics": [{
    "name": "Timeline",
    "status": "active",
    "topic_presence": true,
    "match_confidence": 0.80,
    "key_statements": []
  }]
}
```

**Handling:**
- `incoming_has_new_detail = False`, `incoming_presence = True`
- Topic is counted as a time participant (`is_participant = True`)
- Status updated, time allocated
- No new statements merged (merge keeps existing statements unchanged)
- ✓ Correct per rule 13.

---

### Case 5 — Covered status (explicit closure)

```json
{
  "topics": [{"name": "Q3 Budget", "status": "covered", "topic_presence": true, ...}]
}
```

**Handling via `status_rank = {"not_started": 0, "active": 1, "covered": 2}`:**

| Previous status | Incoming | Result | Reason |
|---|---|---|---|
| `not_started` | `covered` | `covered` | Rank 0 < 2, no downgrade |
| `active` | `covered` | `covered` | Rank 1 < 2, `status_reason="explicit_close"` |
| `covered` | `active` + confidence ≥ 0.65 | `active` | Topic reopened |
| `covered` | `active` + confidence < 0.65 | `covered` | No reopen below threshold |

**The covered→active reopen path** catches cases where a topic was closed but comes back
in a later chunk. ✓

---

### Case 6 — Multiple topics

```json
{
  "topics": [
    {"name": "Budget", ...},
    {"name": "Timeline", ...}
  ]
}
```

**Handling:** Each topic is normalised, classified, and merged independently.
Time (`chunk_seconds`) is split proportionally by `topic_presence` weight among all
`participant_keys`. ✓

---

### Case 7 — Agent includes `time_seconds` (breaks rule 9)

```json
{"topics": [{"name": "A", "time_seconds": 45, ...}]}
```

**Handling:** `_normalize_item` does not read `time_seconds` from the agent response.
The field is silently dropped. `time_seconds` in stored state is computed entirely by
the allocator. ✓

---

### Case 8 — `topic_presence: false` (breaks rule 16)

```json
{"topics": [{"name": "Budget", "topic_presence": false, "status": "active", ...}]}
```

**Handling:**
- `incoming_presence = False`
- `is_participant = allow_assignment AND incoming_presence = False` → not in
  `participant_keys` → no time allocated
- For an **existing** topic: merge still runs (if `allow_assignment=True`), status
  may update, but no time is credited
- For a **new** topic: requires `incoming_presence OR incoming_has_new_detail` → if
  both are False the new topic is silently skipped
- Outcome: presence-false existing topics can still have their status updated, which
  is a minor edge case but harmless in practice.

---

### Case 9 — `match_confidence` out of range

```json
{"name": "A", "match_confidence": 1.5}  // or -0.3, NaN, Inf
```

**Handling in `_normalize_item`:**
```python
if math.isnan(match_confidence) or math.isinf(match_confidence):
    match_confidence = 0.0
match_confidence = max(0.0, min(1.0, match_confidence))
```
Always clamped to `[0.0, 1.0]`. ✓

---

### Case 10 — `status: "not_started"` for a present topic (breaks rule 14)

```json
{"name": "A", "status": "not_started", "topic_presence": true, ...}
```

**Handling in `_classify_incoming_unlocked`:**
```python
if (incoming_has_new_detail or incoming_presence) and incoming_status == "not_started":
    incoming_status = "active"
```
Coerced to `"active"` whenever the topic has evidence. ✓

---

### Case 11 — Empty or missing `name` (breaks rule 1)

```json
{"name": "", "status": "active", ...}
```

**Handling in `_normalize_item`:**
```python
name = " ".join(str(item.get("name", "") or "").split()).strip()
if not name:
    return None  # item silently dropped
```
✓

---

### Case 12 — Extra keys in topic object

```json
{"name": "A", "time_seconds": 45, "total_time": 200, "metadata": {...}, ...}
```

**Handling:** `_normalize_item` only reads the defined contract fields. All unknown
keys are silently ignored. ✓

---

### Case 13 — Extra top-level keys in response

```json
{"topics": [...], "total_time": 200, "metadata": {...}}
```

**Handling:** Only `payload.get("topics", [])` is read. All other top-level keys are
ignored. ✓

---

### Case 14 — Markdown-wrapped JSON (model ignores "no markdown" instruction)

````
```json
{"topics": [...]}
```
````

**Handling in `_extract_json`:**
```python
start = raw.find("{")
end = raw.rfind("}")
return json.loads(raw[start : end + 1])
```
Finds the first `{` and last `}`, extracts the JSON substring. ✓

---

### Case 15 — Content filter refusal

```
"I'm sorry, I cannot process this request due to content policy."
```

**Handling:** `_extract_json` checks for refusal markers before attempting parse. If
the text does not start with `{` and contains a refusal phrase, raises:
```
RuntimeError("Topic tracker content filter blocked response: ...")
```
`run_update` catches all exceptions → `topics_last_error` set → run recorded as
`"status": "error"` → existing topic state unchanged → `topics_update` broadcast
with unchanged state. ✓

---

### Case 16 — Completely empty response

**Handling:** `_extract_json` raises `RuntimeError("Topic tracker returned empty
response.")` → same error path as Case 15. ✓

---

### Case 17 — Wrong top-level structure (array instead of dict)

```json
[{"name": "A", ...}]
```

**Handling:**
```python
payload = result.payload if isinstance(result.payload, dict) else {}
items_raw = list(payload.get("topics", []) or [])  # → []
```
Treated as an empty result with no topic changes. ✓

---

### Case 18 — Agent name drift (slight mismatch from agenda)

Agent returns `"name": "Education System Reform"` but agenda has `"Education Reform"`.

**Handling in `_resolve_names_unlocked`:** Uses `raw_key` and optionally `suggested_key`.
If neither matches `known_topic_keys`, the item is treated as a **new** topic.

**Implication:** If the agent drifts from the exact agenda name (breaking rule 4), a
duplicate new topic may be created rather than updating the existing one. This is by
design: the agent is responsible for exact name accuracy. The system prompt explicitly
forbids name drift.

---

### Case 19 — `key_statements` with timestamps outside the chunk range

**Handling in `_filter_statements_to_chunk`:**
```python
min_ts = chunk_min_ts - 1.0   # 1-second tolerance
max_ts = chunk_max_ts + 1.0
```
Statements with `ts` outside `[min_ts, max_ts]` are silently dropped.
`incoming_has_new_detail` is set from the **filtered** list only.

The ±1 second tolerance is deliberate — it absorbs minor timing imprecision in
agent-returned timestamps (the agent paraphrases, so exact `ts` can drift slightly). ✓

---

### Case 20 — `key_statements.text` exceeds 15 words (breaks rule 12)

**Handling:** The code does NOT validate statement text length. Overlong text is stored
as-is. This is aesthetic, not a logic bug — display and export remain functional. The
system prompt enforces the 15-word limit on the agent side.

---

### Case 21 — `match_confidence` missing from response

**Handling:**
```python
float(item.get("match_confidence", 1.0) or 0.0)
```
Default is `1.0` (maximum confidence). If the agent omits the field, the topic is
treated as a full-confidence match. This is a safe conservative default — the agent
should always return confidence.

---

### Case 22 — `topic_presence` missing or non-boolean

| Value | Result |
|---|---|
| `true` / `false` (bool) | Used directly |
| `null` / missing | Inferred: `True` if statements exist OR status is `active`/`covered` |
| `"true"`, `"1"`, `"yes"` (string) | Coerced to `True` |
| `"false"`, `"0"`, `"no"` (string) | Coerced to `False` |

✓ Fully defensive.

---

### Case 23 — More than 30 topics returned

**Handling:** `_normalize_results` caps at `items_raw[:30]`. Excess items are silently
dropped. The agent is expected to return very few topics (2–5 typical). ✓

---

### Case 24 — Low-confidence new topic (confidence < 0.65, allow_new=true)

```json
{"name": "New Subject", "match_confidence": 0.4, "topic_presence": true, ...}
```

**Handling:** `confidence < 0.65`, `allow_new=True`, unknown name →
`create_new_candidate = True`, `allow_assignment = True`. Topic still passes through.
In `_apply_merge_unlocked` it requires `incoming_presence OR incoming_has_new_detail`
to actually be stored. This matches rule 6 (agent returns a new topic even below 0.65
when allow_new=true). ✓

---

### Case 25 — `topics` is a dict instead of a list

```json
{"topics": {"name": "A", "status": "active"}}
```

**Handling:** `list({"name": "A", "status": "active"})` = `["name", "status"]` (dict
keys). Each key string fails `isinstance(raw, dict)` check in `_normalize_results` →
all skipped → treated as empty result. ✓

---

## Error Path Summary

Any unhandled exception in `run_update` is caught by the outer `except Exception`:

1. `topics_pending` set to `False`
2. `topics_last_error` set to exception message
3. Run recorded with `"status": "error"`
4. Existing `topics_items` state left **unchanged**
5. `topics_update` broadcast sent with unchanged state
6. Error message broadcast via `broadcast_log("error", ...)`

This means a failed agent call never corrupts stored topic state. ✓

---

## Known Minor Code Note

In `_apply_merge_unlocked`, the `covered→active` reopen branch has a duplicate
assignment (no functional impact):

```python
if prev_status == "covered" and incoming_presence and incoming_confidence >= threshold:
    next_status = "active"
    next_status = "active"   # ← duplicate, harmless
    status_reason = "reopened"
```

---

## Design Decisions (Intentional Behaviours)

| Behaviour | Reason |
|---|---|
| `comments` for existing topics never updated from agent | Stability: scope is set once at topic creation |
| `time_seconds` not read from agent | Always computed internally by allocator |
| Missing `match_confidence` defaults to 1.0 | Safe conservative: assume full match rather than drop |
| ±1.0 second tolerance in `_filter_statements_to_chunk` | Agent paraphrases; exact timestamps can drift |
| Name drift creates a new topic (not a match update) | Agent is responsible for exact names (rule 4) |
| Low-confidence new topics still stored (allow_new=true) | Matches rule 6 intent |
