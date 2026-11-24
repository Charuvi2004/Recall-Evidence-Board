### Metric definitions

All targets are planning assumptions from the strategy doc, set before any data. They live in `config.py`.

| Metric | Definition | Target |
| --- | --- | --- |
| **North Star: Weekly Active Reviewers** | Share of installed, not-yet-uninstalled users who completed a review session on 3+ distinct days in a Monday–Sunday week. Only complete weeks are charted. | ≥ 30% by pilot week 4 |
| Activation | Within 72 hours of install: added a course, created 3+ flags, completed a first review session. | ≥ 40% of installs |
| Flags per hour watched | Flags ÷ hours in `study_session` events. | ≥ 3 |
| Review days per active learner | In the last complete week, among users with 1+ review: average distinct review days. | ≥ 3 |
| Videos completed per active learner | Same users, same week: average `video_completed` events. | Tracked, no target |
| Week-1 / week-4 review retention | Among activated users whose week k (days 7k to 7k+6 after install) has fully passed: share with 1+ review session in it. | ≥ 50% / ≥ 25% |
| Second-review recall | Share of `card_reviewed` events with `review_number = 2` rated *remembered*. | 60–85% |
| Recall test gap | Per volunteer, flagged-topic score minus unflagged-topic score, in points out of 100; averaged, with a 95% t-interval. | ≥ +15 points |
| Guardrail: review burden | Median review-session length. | ≤ 10 min |
| Guardrail: early churn | Users installed 7+ days ago who uninstalled within 7 days. | < 20% |
| Guardrail: learning not displaced | Activated users installed 14+ days ago: videos completed in their latest full week ÷ in their first week. | ≥ 90% |
| Guardrail: reliability | `detection_error` events ÷ `study_session` events. | < 2% |

### Research checks

Scored on survey respondents whose goal is `placements` (the MVP segment). A check reports *too little data* below 30 segment responses. Every part of a check must pass. Interview evidence counts participants who raised a hypothesis **unprompted and supported it**, out of all interviewees.

### Reading this honestly

- Small pilots swing a lot from week to week. Look at the trend and the *n*, not one week's number.
- Self-rated recall can be inflated. The recall test is the only learning measure here that isn't self-reported.
- A failed check is a result, not a bug. Record it in the decision log and follow the fallback plan.
