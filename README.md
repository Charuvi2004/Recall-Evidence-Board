# Recall: PM dashboard

A Streamlit dashboard for the **Recall** pilot, a Chrome extension that turns YouTube playlists into courses and lets students flag key moments for spaced revision. The dashboard does two jobs:

1. **Research (Phase 1):** scores the survey and interview coding against the kill/continue criteria that were fixed *before* data collection.
2. **Pilot (Phase 2):** tracks the North Star (Weekly Active Reviewers), the activation funnel, review retention by install week, learning quality (including an objective recall test) and guardrails.

> **Sample data is fake.** `generate_sample_data.py` creates a synthetic world so the dashboard works today. The app shows a warning banner whenever it's on. Replace it with real exports before quoting any number.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python generate_sample_data.py      # optional; the app generates sample data on first run
streamlit run app.py
```

Run the tests with `python -m pytest` (or `python tests/test_metrics.py` if pytest isn't installed).

To share it, push the folder to a public GitHub repo and deploy on Streamlit Community Cloud (free). Put the repo link on your resume.

## Files

| File | What it does |
| --- | --- |
| `app.py` | The Streamlit app: Overview, Research, Activation, Retention, Learning & guardrails, Definitions |
| `metrics.py` | Every metric, as plain pandas functions (no Streamlit), so they're testable |
| `config.py` | Targets, kill-criteria thresholds and chart colours, all in one place |
| `charts.py` | Plotly chart builders |
| `generate_sample_data.py` | Fake data generator (seeded) |
| `tests/test_metrics.py` | Hand-built cases with known answers |
| `DEFINITIONS.md` | Metric definitions, shown in the app's last tab |

## Data schema

Upload these as CSVs in the sidebar. Column names must match exactly; extra columns are ignored.

### `events.csv`: one row per extension event

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | text | Anonymous ID generated at install. Never an email. |
| `ts` | ISO 8601 timestamp | e.g. `2027-01-04T21:15:03` (UTC, or one consistent timezone) |
| `event` | text | One of the event types below |
| `course_id`, `video_id`, `card_id` | text | Blank when not relevant |
| `rating` | text | `remembered` / `fuzzy` / `forgot` (only on `card_reviewed`) |
| `review_number` | integer | 1 for a card's first review, 2 for its second… (only on `card_reviewed`) |
| `duration_sec` | integer | Watch time on `study_session`; session length on `review_session_completed` |

| `event` | When the extension logs it |
| --- | --- |
| `install` | First run after install |
| `uninstall` | From the uninstall URL page (`chrome.runtime.setUninstallURL`) |
| `course_added` | Student clicks "Track as course" on a playlist |
| `study_session` | A watch session on a tracked course ends (with watch seconds) |
| `video_completed` | A tracked video passes 90% watched |
| `flag_created` | Student presses the flag key |
| `card_reviewed` | One card rated in a review session |
| `review_session_completed` | A review session ends (with its length) |
| `detection_error` | The extension couldn't read the playlist or player |

### `survey.csv`: one row per respondent (question IDs from the research plan)

`respondent_id`, `goal` (S2: `placements` / `gate` / `semester` / `other_exam` / `none`), `device` (S4: `laptop` / `phone` / `tablet` / `split`), `creators` (S6: `1` / `2` / `3+` / `none`), `last_playlist_progress` (S7: `finished` / `over_75` / `25_75` / `under_25` / `dropped_early`), `pain_lost_place`, `pain_derailed`, `pain_cant_find`, `pain_forgot`, `pain_unsure` (S8: `never` / `once` / `2-3` / `4+`), `revision_method` (S9), `revision_rating` (S10: 1–5), `tools_used` (S12: semicolon-separated, using `ask`, `ai_summariser`, `blocker`, `notes_tool`, or `none`), `top_problem` (S13), `installed_study_ext` (S14: `yes` / `no`), `permission_comfort` (S15: 1–5). Optional: `year`, `branch`, `yt_hours`, `tracking_method`.

Recode your Google Forms export into these values (one find-and-replace pass per column).

### `interviews.csv`: one row per interviewee × hypothesis

`participant_id`, `hypothesis` (`H1`–`H8`), `verdict` (`supports` / `contradicts` / `not_discussed`), `unprompted` (`yes` / `no`: did they raise it before you asked?), `quote` (exact words, optional).

### `recall_test.csv`: two rows per volunteer

`user_id`, `topic_type` (`flagged` / `unflagged`), `score` (0–5 correct out of 5).

## Honesty rules for the resume

- Quote only numbers from real data, with the *n* beside them ("31% weekly active reviewers, n = 84").
- The recall test is your strongest claim, because it measures learning rather than clicks. Report the confidence interval, not just the average.
- If a kill criterion fails, say so and say what you did about it. That's a better interview story than a perfect-looking chart.
