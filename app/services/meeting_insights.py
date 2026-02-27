"""Deterministic transcript analytics used by summary flows."""

from __future__ import annotations

import math
import re
import statistics
from typing import Any

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")
_SPACE_RE = re.compile(r"\s+")

_STOPWORDS = {
    "actually",
    "about",
    "after",
    "again",
    "against",
    "almost",
    "also",
    "among",
    "another",
    "anyone",
    "anything",
    "because",
    "before",
    "being",
    "between",
    "came",
    "come",
    "could",
    "did",
    "didn",
    "does",
    "doing",
    "each",
    "even",
    "every",
    "everything",
    "from",
    "going",
    "gonna",
    "got",
    "have",
    "having",
    "here",
    "herself",
    "himself",
    "idea",
    "into",
    "itself",
    "just",
    "kind",
    "kinda",
    "know",
    "like",
    "more",
    "most",
    "much",
    "other",
    "ourselves",
    "please",
    "probably",
    "really",
    "right",
    "said",
    "same",
    "says",
    "should",
    "some",
    "such",
    "than",
    "that",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "thing",
    "things",
    "think",
    "thought",
    "this",
    "those",
    "through",
    "time",
    "times",
    "today",
    "trying",
    "very",
    "want",
    "wants",
    "well",
    "went",
    "were",
    "work",
    "works",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def _normalize_space(value: Any) -> str:
    return _SPACE_RE.sub(" ", str(value or "")).strip()


def _safe_ts(value: Any) -> float:
    try:
        ts = float(value or 0.0)
    except Exception:
        return 0.0
    return ts if math.isfinite(ts) and ts > 0 else 0.0


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _normalize_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        text = _normalize_space(raw.get("text"))
        if not text:
            continue
        ts = _safe_ts(raw.get("ts"))
        speaker_label = _normalize_space(raw.get("speaker_label") or raw.get("speaker") or "Speaker")
        rows.append(
            {
                "ts": ts,
                "speaker_label": speaker_label or "Speaker",
                "text": text,
                "words": _word_count(text),
            }
        )
    rows.sort(key=lambda row: row["ts"])
    return rows


def build_meeting_insights(entries: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _normalize_entries(entries)
    if not rows:
        return {
            "speaking_balance": [],
            "turn_taking": {
                "total_turns": 0,
                "avg_words_per_turn": 0.0,
                "longest_turn_words": 0,
                "speaker_switches": 0,
                "switch_rate_pct": 0.0,
                "meeting_duration_sec": 0.0,
            },
            "pace": [],
            "health": {"score_0_100": 0, "flags": ["No transcript data."], "recommendations": []},
        }

    per_speaker: dict[str, dict[str, float]] = {}
    turn_spans: list[float] = []
    for idx, row in enumerate(rows):
        speaker = row["speaker_label"]
        bucket = per_speaker.setdefault(speaker, {"turns": 0.0, "words": 0.0, "talk_sec": 0.0})
        bucket["turns"] += 1
        bucket["words"] += row["words"]

        if idx < len(rows) - 1:
            raw_delta = max(0.0, rows[idx + 1]["ts"] - row["ts"])
            if raw_delta > 0:
                turn_spans.append(min(raw_delta, 30.0))

    median_span = statistics.median(turn_spans) if turn_spans else 3.0
    default_span = max(1.0, min(8.0, float(median_span)))

    for idx, row in enumerate(rows):
        speaker = row["speaker_label"]
        if idx < len(rows) - 1:
            delta = max(0.0, rows[idx + 1]["ts"] - row["ts"])
            span = max(1.0, min(delta if delta > 0 else default_span, 30.0))
        else:
            span = default_span
        per_speaker[speaker]["talk_sec"] += span

    total_turns = len(rows)
    total_words = sum(int(row["words"]) for row in rows)
    total_talk_sec = sum(float(bucket["talk_sec"]) for bucket in per_speaker.values()) or 1.0
    meeting_duration_sec = max(0.0, rows[-1]["ts"] - rows[0]["ts"])

    speaking_balance: list[dict[str, Any]] = []
    pace: list[dict[str, Any]] = []
    for speaker, bucket in per_speaker.items():
        turns = int(bucket["turns"])
        words = int(bucket["words"])
        talk_sec = float(bucket["talk_sec"])
        if total_words > 0:
            share_pct = (words / total_words) * 100.0
        else:
            share_pct = (talk_sec / total_talk_sec) * 100.0
        wpm = round((words * 60.0 / talk_sec), 1) if talk_sec > 0 else 0.0
        speaking_balance.append(
            {
                "speaker": speaker,
                "turns": turns,
                "words": words,
                "share_pct": round(share_pct, 1),
                "estimated_talk_sec": round(talk_sec, 1),
            }
        )
        pace.append({"speaker": speaker, "wpm": wpm})

    speaking_balance.sort(key=lambda row: (-float(row["share_pct"]), row["speaker"]))
    pace.sort(key=lambda row: row["speaker"])

    switches = 0
    for idx in range(1, len(rows)):
        if rows[idx - 1]["speaker_label"] != rows[idx]["speaker_label"]:
            switches += 1
    switch_rate = (switches / max(1, total_turns - 1)) * 100.0 if total_turns > 1 else 0.0

    avg_words_per_turn = round(total_words / total_turns, 1) if total_turns > 0 else 0.0
    longest_turn_words = max(int(row["words"]) for row in rows)

    health_score = 100
    flags: list[str] = []
    recommendations: list[str] = []

    dominant = speaking_balance[0] if speaking_balance else None
    dominant_share = float(dominant["share_pct"]) if dominant else 0.0
    if dominant_share >= 75.0:
        health_score -= 25
        flags.append(f"{dominant['speaker']} dominated {dominant_share:.1f}% of words.")
        recommendations.append("Invite shorter turns from the quieter participants.")
    elif dominant_share >= 65.0:
        health_score -= 12
        flags.append(f"Participation was imbalanced ({dominant_share:.1f}% by one speaker).")
        recommendations.append("Use directed questions to rebalance airtime.")

    if total_turns >= 8 and switch_rate < 25.0:
        health_score -= 15
        flags.append("Low interaction: limited speaker switching.")
        recommendations.append("Add checkpoints to confirm alignment every few minutes.")

    if total_words < 60 or total_turns < 4:
        health_score -= 10
        flags.append("Short transcript: confidence in analytics is limited.")

    pace_outliers = [
        row for row in pace if (row["wpm"] > 0 and (row["wpm"] < 90.0 or row["wpm"] > 190.0))
    ]
    if pace_outliers:
        penalty = min(15, 5 * len(pace_outliers))
        health_score -= penalty
        flags.append("Speaking pace varied significantly across participants.")
        recommendations.append("Slow down dense sections and insert concise recaps.")

    health_score = max(0, min(100, int(round(health_score))))
    if not recommendations:
        recommendations.append("Meeting interaction looked healthy; keep the same cadence.")

    return {
        "speaking_balance": speaking_balance,
        "turn_taking": {
            "total_turns": total_turns,
            "avg_words_per_turn": avg_words_per_turn,
            "longest_turn_words": longest_turn_words,
            "speaker_switches": switches,
            "switch_rate_pct": round(switch_rate, 1),
            "meeting_duration_sec": round(meeting_duration_sec, 1),
        },
        "pace": pace,
        "health": {
            "score_0_100": health_score,
            "flags": flags[:5],
            "recommendations": recommendations[:5],
        },
    }


def _keyword_key(value: str) -> str:
    return _normalize_space(value).lower()


def _count_keyword_occurrences(text: str, keyword: str) -> int:
    haystack = text.lower()
    needle = keyword.lower().strip()
    if not needle:
        return 0
    if " " in needle:
        return haystack.count(needle)
    pattern = re.compile(rf"\b{re.escape(needle)}\b", re.IGNORECASE)
    return len(pattern.findall(text))


def build_keyword_index(
    entries: list[dict[str, Any]],
    key_terms_defined: list[dict[str, Any]] | None = None,
    keyword_hints: list[str] | None = None,
    entities: list[dict[str, Any]] | None = None,
    *,
    max_items: int = 40,
) -> list[dict[str, Any]]:
    rows = _normalize_entries(entries)
    if not rows:
        return []

    candidates: dict[str, str] = {}

    for row in key_terms_defined or []:
        if not isinstance(row, dict):
            continue
        term = _normalize_space(row.get("term"))
        if not term:
            continue
        key = _keyword_key(term)
        if " " not in key and key in _STOPWORDS:
            continue
        candidates[key] = term
    for hint in keyword_hints or []:
        phrase = _normalize_space(hint)
        if not phrase:
            continue
        key = _keyword_key(phrase)
        if " " not in key and key in _STOPWORDS:
            continue
        candidates.setdefault(key, phrase)
    allowed_entity_types = {
        "PERSON",
        "ORG",
        "LOCATION",
        "DATE_TIME",
        "PRODUCT",
        "EVENT",
        "MONEY",
        "PERCENT",
    }
    for entity in entities or []:
        if not isinstance(entity, dict):
            continue
        entity_type = str(entity.get("type", "") or "").strip().upper()
        if entity_type not in allowed_entity_types:
            continue
        phrase = _normalize_space(entity.get("text"))
        if not phrase:
            continue
        key = _keyword_key(phrase)
        if " " not in key and key in _STOPWORDS:
            continue
        candidates.setdefault(key, phrase)

    if not candidates:
        return []

    out: list[dict[str, Any]] = []
    for key, keyword in candidates.items():
        occ = 0
        first_ts = 0.0
        last_ts = 0.0
        speakers: set[str] = set()
        for row in rows:
            hits = _count_keyword_occurrences(row["text"], key)
            if hits <= 0:
                continue
            occ += hits
            if first_ts <= 0.0:
                first_ts = row["ts"]
            last_ts = row["ts"]
            speakers.add(row["speaker_label"])
        if occ <= 0:
            continue
        out.append(
            {
                "keyword": keyword,
                "occurrences": occ,
                "first_ts": first_ts,
                "last_ts": last_ts,
                "speakers": sorted(speakers),
            }
        )

    out.sort(key=lambda row: (-int(row["occurrences"]), str(row["keyword"]).lower()))
    return out[:max(1, int(max_items))]
