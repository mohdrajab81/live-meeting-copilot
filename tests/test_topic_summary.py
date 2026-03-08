from app.services.topic_summary import (
    apply_topic_durations_from_utterance_ids,
    enforce_topic_coverage,
)


def test_enforce_topic_coverage_assigns_missing_id_to_nearest_topic():
    rows = [
        {"utterance_id": "U0001", "duration_sec": 10.0},
        {"utterance_id": "U0002", "duration_sec": 10.0},
        {"utterance_id": "U0003", "duration_sec": 10.0},
    ]
    topics = [
        {
            "topic_name": "Project Status",
            "origin": "Agenda",
            "utterance_ids": ["U0001", "U0003"],
            "key_points": ["Status update"],
        }
    ]
    defs = [{"name": "Project Status", "expected_duration_min": 2}]

    out = enforce_topic_coverage(topics, defs, rows)

    assert len(out) == 1
    assert out[0]["topic_name"] == "Project Status"
    assert out[0]["origin"] == "Agenda"
    assert out[0]["utterance_ids"] == ["U0001", "U0002", "U0003"]


def test_enforce_topic_coverage_dedupes_duplicate_claims_first_wins():
    rows = [
        {"utterance_id": "U0001", "duration_sec": 10.0},
        {"utterance_id": "U0002", "duration_sec": 10.0},
    ]
    topics = [
        {
            "topic_name": "Project Status",
            "origin": "Agenda",
            "utterance_ids": ["U0001"],
            "key_points": [],
        },
        {
            "topic_name": "Marketing campaign",
            "origin": "Agenda",
            "utterance_ids": ["U0001", "U0002"],
            "key_points": [],
        },
    ]
    defs = [
        {"name": "Project Status", "expected_duration_min": 2},
        {"name": "Marketing campaign", "expected_duration_min": 1},
    ]

    out = enforce_topic_coverage(topics, defs, rows)

    assert out[0]["utterance_ids"] == ["U0001"]
    assert out[1]["utterance_ids"] == ["U0002"]


def test_enforce_topic_coverage_forces_non_agenda_origin_to_inferred():
    rows = [
        {"utterance_id": "U0001", "duration_sec": 10.0},
        {"utterance_id": "U0002", "duration_sec": 10.0},
        {"utterance_id": "U0003", "duration_sec": 10.0},
    ]
    topics = [
        {
            "topic_name": "Project Status",
            "origin": "Agenda",
            "utterance_ids": ["U0001"],
            "key_points": [],
        },
        {
            "topic_name": "Team operations and next steps",
            "origin": "Agenda",
            "utterance_ids": ["U0003"],
            "key_points": [],
        },
    ]
    defs = [
        {"name": "Project Status", "expected_duration_min": 2},
        {"name": "Marketing campaign", "expected_duration_min": 1},
    ]

    out = enforce_topic_coverage(topics, defs, rows)

    assert out[0]["origin"] == "Agenda"
    assert out[1]["origin"] == "Inferred"
    assert out[1]["topic_name"] == "Team operations and next steps"
    assert sorted(uid for topic in out for uid in topic["utterance_ids"]) == ["U0001", "U0002", "U0003"]


def test_apply_topic_durations_adds_unassigned_for_missing_ids():
    rows = [
        {"utterance_id": "U0001", "duration_sec": 30.0},
        {"utterance_id": "U0002", "duration_sec": 20.0},
        {"utterance_id": "U0003", "duration_sec": 10.0},
    ]
    topics = [
        {
            "topic_name": "A",
            "origin": "Inferred",
            "utterance_ids": ["U0001", "U0002"],
            "key_points": [],
        }
    ]

    out = apply_topic_durations_from_utterance_ids(topics, rows)
    assert len(out) == 2
    assert out[0]["estimated_duration_minutes"] == 0.8  # 50s
    assert out[1]["topic_name"] == "Unassigned / Other"
    assert out[1]["utterance_ids"] == ["U0003"]
    assert out[1]["estimated_duration_minutes"] == 0.2  # 10s


def test_apply_topic_durations_dedupes_same_id_across_topics_first_wins():
    rows = [
        {"utterance_id": "U0001", "duration_sec": 20.0},
        {"utterance_id": "U0002", "duration_sec": 20.0},
    ]
    topics = [
        {
            "topic_name": "First",
            "origin": "Inferred",
            "utterance_ids": ["U0001"],
            "key_points": [],
        },
        {
            "topic_name": "Second",
            "origin": "Inferred",
            "utterance_ids": ["U0001", "U0002"],
            "key_points": [],
        },
    ]

    out = apply_topic_durations_from_utterance_ids(topics, rows)
    assert out[0]["utterance_ids"] == ["U0001"]
    assert out[1]["utterance_ids"] == ["U0002"]
    assert out[0]["estimated_duration_minutes"] == 0.3
    assert out[1]["estimated_duration_minutes"] == 0.3


def test_apply_topic_durations_no_auto_other_when_no_ids_assigned():
    rows = [
        {"utterance_id": "U0001", "duration_sec": 20.0},
        {"utterance_id": "U0002", "duration_sec": 20.0},
    ]
    topics = [
        {
            "topic_name": "First",
            "origin": "Inferred",
            "utterance_ids": [],
            "estimated_duration_minutes": 1.0,
            "key_points": [],
        }
    ]

    out = apply_topic_durations_from_utterance_ids(topics, rows)
    assert len(out) == 1
    assert out[0]["topic_name"] == "First"
    assert out[0]["estimated_duration_minutes"] is None


def test_apply_topic_durations_coverage_with_gaps_merges_same_topic_small_gap():
    rows = [
        {"utterance_id": "U0001", "start_ts": 0.0, "end_ts": 10.0, "duration_sec": 10.0},
        {"utterance_id": "U0002", "start_ts": 20.0, "end_ts": 30.0, "duration_sec": 10.0},
    ]
    topics = [
        {
            "topic_name": "A",
            "origin": "Inferred",
            "utterance_ids": ["U0001", "U0002"],
            "key_points": [],
        }
    ]

    out_cov = apply_topic_durations_from_utterance_ids(
        topics,
        rows,
        duration_mode="coverage_with_gaps",
        gap_threshold_sec=30,
    )
    out_speech = apply_topic_durations_from_utterance_ids(
        topics,
        rows,
        duration_mode="speech_only",
        gap_threshold_sec=30,
    )

    # coverage_with_gaps = 10 + 10 + 10(gap) = 30s -> 0.5m
    assert out_cov[0]["estimated_duration_minutes"] == 0.5
    # speech_only = 10 + 10 = 20s -> 0.3m
    assert out_speech[0]["estimated_duration_minutes"] == 0.3


def test_apply_topic_durations_coverage_with_gaps_assigns_inter_topic_gap_to_next():
    rows = [
        {"utterance_id": "U0001", "start_ts": 0.0, "end_ts": 10.0, "duration_sec": 10.0},
        {"utterance_id": "U0002", "start_ts": 20.0, "end_ts": 30.0, "duration_sec": 10.0},
    ]
    topics = [
        {
            "topic_name": "A",
            "origin": "Inferred",
            "utterance_ids": ["U0001"],
            "key_points": [],
        },
        {
            "topic_name": "B",
            "origin": "Inferred",
            "utterance_ids": ["U0002"],
            "key_points": [],
        },
    ]

    out = apply_topic_durations_from_utterance_ids(
        topics,
        rows,
        duration_mode="coverage_with_gaps",
        gap_threshold_sec=30,
    )

    # Gap 10s between A and B is assigned fully to the NEXT topic (B).
    assert out[0]["estimated_duration_minutes"] == 0.2  # 10s
    assert out[1]["estimated_duration_minutes"] == 0.3  # 10s + 10s gap
