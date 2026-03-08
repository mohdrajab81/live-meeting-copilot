"""Unit tests for deterministic meeting analytics helpers."""

from app.services.meeting_insights import build_keyword_index, build_meeting_insights


def test_build_meeting_insights_empty_input():
    result = build_meeting_insights([])
    assert result["speaking_balance"] == []
    assert result["turn_taking"]["total_turns"] == 0
    assert result["pace"] == []
    assert result["health"]["score_0_100"] == 0


def test_build_meeting_insights_speaker_balance_and_switches():
    rows = [
        {"ts": 100.0, "speaker_label": "You", "text": "Hello team thanks for joining today"},
        {"ts": 106.0, "speaker_label": "Remote", "text": "Thanks we can start with architecture"},
        {"ts": 114.0, "speaker_label": "You", "text": "Great let us cover roadmap and risks"},
    ]
    result = build_meeting_insights(rows)
    assert result["turn_taking"]["total_turns"] == 3
    assert result["turn_taking"]["speaker_switches"] == 2
    assert len(result["speaking_balance"]) == 2
    speakers = {row["speaker"] for row in result["speaking_balance"]}
    assert speakers == {"You", "Remote"}


def test_build_meeting_insights_single_speaker_suppresses_balance_and_interaction_penalties():
    rows = [
        {"ts": 100.0, "speaker_label": "Remote", "text": "We are reviewing the launch plan today."},
        {"ts": 106.0, "speaker_label": "Remote", "text": "The remaining work is payment testing and bug fixing."},
        {"ts": 114.0, "speaker_label": "Remote", "text": "Marketing assets are due next week."},
        {"ts": 122.0, "speaker_label": "Remote", "text": "Operations will confirm support coverage."},
    ]
    result = build_meeting_insights(rows)
    flags = result["health"]["flags"]
    recs = result["health"]["recommendations"]

    assert any("Single-speaker session" in flag for flag in flags)
    assert not any("dominated" in flag for flag in flags)
    assert not any("Low interaction" in flag for flag in flags)
    assert not any("quieter participants" in rec for rec in recs)
    assert result["turn_taking"]["speaker_switches"] == 0
    assert len(result["speaking_balance"]) == 1


def test_build_keyword_index_uses_defined_terms_and_frequency():
    rows = [
        {"ts": 100.0, "speaker_label": "You", "text": "Communication quality drives performance."},
        {"ts": 110.0, "speaker_label": "Remote", "text": "Communication and leadership are key."},
        {"ts": 121.0, "speaker_label": "You", "text": "Leadership consistency matters."},
    ]
    keywords = build_keyword_index(
        rows,
        key_terms_defined=[{"term": "Communication", "definition": "How we exchange ideas"}],
    )
    names = [str(row.get("keyword", "")).lower() for row in keywords]
    assert "communication" in names
    comm = next(row for row in keywords if str(row.get("keyword", "")).lower() == "communication")
    assert int(comm["occurrences"]) >= 2
    assert comm["first_ts"] == 100.0
    assert comm["last_ts"] == 110.0


def test_build_keyword_index_uses_agent_keyword_hints():
    rows = [
        {"ts": 100.0, "speaker_label": "You", "text": "We discussed retrieval augmented generation patterns."},
        {"ts": 112.0, "speaker_label": "Remote", "text": "Retrieval augmented generation improves grounding."},
    ]
    keywords = build_keyword_index(
        rows,
        key_terms_defined=[],
        keyword_hints=["retrieval augmented generation", "think"],
    )
    names = [str(row.get("keyword", "")).lower() for row in keywords]
    assert "retrieval augmented generation" in names
    assert "think" not in names


def test_build_keyword_index_uses_entities_as_additional_candidates():
    rows = [
        {"ts": 100.0, "speaker_label": "You", "text": "Alice spoke from London office."},
        {"ts": 112.0, "speaker_label": "Remote", "text": "London was confirmed by Alice."},
    ]
    keywords = build_keyword_index(
        rows,
        key_terms_defined=[],
        keyword_hints=[],
        entities=[
            {"type": "PERSON", "text": "Alice", "mentions": 2},
            {"type": "LOCATION", "text": "London", "mentions": 2},
        ],
    )
    names = [str(row.get("keyword", "")).lower() for row in keywords]
    assert "alice" in names
    assert "london" in names


def test_build_keyword_index_empty_when_no_entries():
    assert build_keyword_index([], key_terms_defined=[{"term": "X"}]) == []


def test_build_keyword_index_no_fallback_without_terms_or_hints():
    rows = [
        {"ts": 100.0, "speaker_label": "You", "text": "Education and creativity are important."},
        {"ts": 110.0, "speaker_label": "Remote", "text": "Education systems can suppress creativity."},
    ]
    assert build_keyword_index(rows, key_terms_defined=[], keyword_hints=[]) == []
