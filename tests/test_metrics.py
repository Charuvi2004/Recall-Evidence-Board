"""Hand-built cases with known answers. Run: python -m pytest  (or: python tests/test_metrics.py)"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import metrics as M  # noqa: E402

T0 = pd.Timestamp("2027-01-04 10:00")  # Monday


def ev(rows):
    df = pd.DataFrame(rows, columns=["user_id", "ts", "event", "rating", "review_number", "duration_sec"])
    for c in ("course_id", "video_id", "card_id"):
        df[c] = ""
    return M.prep_events(df)


def h(hours):
    return T0 + pd.Timedelta(hours=hours)


def test_activation_requires_all_steps_within_72h():
    e = ev([
        ("a", h(0), "install", "", "", ""), ("a", h(1), "course_added", "", "", ""),
        *[("a", h(2 + i), "flag_created", "", "", "") for i in range(3)],
        ("a", h(30), "review_session_completed", "", "", 300),
        ("b", h(0), "install", "", "", ""), ("b", h(1), "course_added", "", "", ""),
        *[("b", h(2 + i), "flag_created", "", "", "") for i in range(3)],
        ("b", h(80), "review_session_completed", "", "", 300),          # too late
        ("c", h(0), "install", "", "", ""), ("c", h(1), "course_added", "", "", ""),
        *[("c", h(2 + i), "flag_created", "", "", "") for i in range(2)],  # only 2 flags
        ("c", h(30), "review_session_completed", "", "", 300),
    ])
    u = M.users(e, h(24 * 20))
    assert u.activated.to_dict() == {"a": True, "b": False, "c": False}
    f = M.activation_funnel(u)
    assert f.users.tolist() == [3, 3, 2, 1]


def test_war_counts_three_review_days_and_drops_uninstalled():
    rows = [("a", h(0), "install", "", "", ""), ("b", h(0), "install", "", "", ""),
            ("c", h(0), "install", "", "", ""), ("c", T0 - pd.Timedelta(days=1), "uninstall", "", "", "")]
    rows += [("a", h(24 * d), "review_session_completed", "", "", 60) for d in (0, 2, 4)]   # 3 days
    rows += [("b", h(24 * d), "review_session_completed", "", "", 60) for d in (0, 0.1, 3)]  # 2 days
    e = ev(rows)
    u = M.users(e, h(24 * 7))
    war = M.weekly_active_reviewers(e, u, h(24 * 7))
    wk = war[war.week_start == pd.Timestamp("2027-01-04")].iloc[0]
    assert wk.active_reviewers == 1
    assert wk.installed_base == 2          # c uninstalled before the week began
    assert wk.share == 0.5


def test_week1_retention_only_counts_elapsed_weeks():
    rows = []
    for uid in ("a", "b"):
        rows += [(uid, h(0), "install", "", "", ""), (uid, h(1), "course_added", "", "", "")]
        rows += [(uid, h(2), "flag_created", "", "", "")] * 3
        rows += [(uid, h(5), "review_session_completed", "", "", 60)]
    rows += [("a", h(24 * 8), "review_session_completed", "", "", 60)]   # a reviews in week 1
    e = ev(rows)
    u = M.users(e, h(24 * 15))
    s = M.retention(e, u, h(24 * 15), 1, 0.5)
    assert s.n == 2 and s.value == 0.5 and s.result == "pass"
    s_early = M.retention(e, u, h(24 * 10), 1, 0.5)                    # week 1 not over yet
    assert s_early.result == "no data"


def test_second_review_recall_and_range():
    e = ev([("a", h(1), "card_reviewed", r, 2, "") for r in ("remembered",) * 9 + ("forgot",)])
    s = M.second_review_recall(e)
    assert s.value == 0.9 and s.result == "fail"   # above 85% = too easy


def test_recall_test_paired_difference():
    rt = pd.DataFrame({"user_id": ["a", "a", "b", "b", "c", "c"],
                       "topic_type": ["flagged", "unflagged"] * 3,
                       "score": [5, 3, 4, 3, 4, 2]})
    out = M.recall_test(rt)
    # diffs in points: 40, 20, 40 -> mean 33.3
    assert np.isclose(out["status"].value, 100 / 3)
    assert out["status"].result == "pass"
    lo, hi = out["ci"]
    assert lo < out["status"].value < hi


def test_kill_scorecard_thresholds_and_small_samples():
    base = {"goal": "placements", "device": "laptop", "creators": "1", "last_playlist_progress": "finished",
            "pain_lost_place": "never", "pain_derailed": "never", "pain_cant_find": "never",
            "pain_forgot": "4+", "pain_unsure": "never", "revision_method": "rewatch", "revision_rating": "2",
            "tools_used": "none", "top_problem": "forgot", "installed_study_ext": "yes", "permission_comfort": "5"}
    survey = pd.DataFrame([{**base, "respondent_id": f"r{i}"} for i in range(30)])
    interviews = pd.DataFrame({"participant_id": [f"p{i}" for i in range(15)], "hypothesis": "H7",
                               "verdict": ["supports"] * 8 + ["contradicts"] * 7,
                               "unprompted": "yes", "quote": ""})
    sc = M.kill_scorecard(survey, interviews).set_index("check")
    assert sc.loc["Revision is the core pain", "result"] == "pass"      # 8/15 meets the bar exactly
    assert sc.loc["Playlist drop-off is real", "result"] == "fail"
    small = M.kill_scorecard(survey.head(10), interviews).set_index("check")
    assert (small.result == "too little data").all()


def test_guardrail_early_churn():
    e = ev([("a", h(0), "install", "", "", ""), ("a", h(24 * 3), "uninstall", "", "", ""),
            ("b", h(0), "install", "", "", ""), ("b", h(24 * 10), "uninstall", "", "", ""),
            ("c", h(0), "install", "", "", "")])
    u = M.users(e, h(24 * 12))
    g = M.guardrails(e, u, h(24 * 12))["Uninstalled within 7 days"]
    assert np.isclose(g.value, 1 / 3) and g.result == "fail"


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print("ok ", t.__name__)
    print(f"{len(tests)} passed")
