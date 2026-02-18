# Product Backlog

## Goal
Turn the app into a public-ready meeting intelligence platform with clear value beyond live translation.

## Phase 1 (Near-Term)
1. Voice recording
- Save session audio per speaker/session.
- Support start/stop and export.

2. Full conversation summary
- Session-level summary after stop.
- Include concise executive summary and detailed breakdown.

3. Agenda-aware analysis
- Compare meeting flow against configured agenda.
- Show covered/missed/off-agenda sections and coverage score.

4. Action items extraction
- Extract owner, task, due date (if present), and confidence.
- Export as JSON/CSV.

## Phase 2
1. Meeting performance insights
- Speaking balance, interruptions, topic drift, pace.
- "Meeting health" score with recommendations.

2. Sentiment and tone analysis
- Per-topic and session-level sentiment trend.
- Keep this optional due to language/domain variability.

3. Keyword and keyphrase extraction
- Dynamic extraction from transcript (no fixed backend keyword list).
- Add search-ready keyword index.

## Phase 3 (Public Trial)
1. Invitation code onboarding
- Invite code required for access.
- One code can have configurable limits.

2. 10-minute trial enforcement
- Hard cap at 10 minutes/session for trial accounts.
- UI countdown and graceful stop behavior.

3. Usage controls
- Per-invite usage limits and expiration.
- Basic abuse controls and audit logs.

## Engineering Notes
1. Keep summary/insight pipelines asynchronous to avoid blocking live translation.
2. Add feature flags so new analytics can be rolled out gradually.
3. Add smoke tests for end-to-end flows before public launch.
