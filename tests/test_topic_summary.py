from app.services.topic_summary import apply_topic_durations_from_utterance_ids


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
