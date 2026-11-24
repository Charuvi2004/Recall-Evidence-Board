"""Metric definitions for the Recall pilot and Phase 1 research.

Pure pandas, no Streamlit: every number on the dashboard comes from a function
here, so it can be unit-tested and reused in a notebook.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import config as C

# ------------------------------------------------------------------ schemas
REQUIRED_COLUMNS = {
    "events": ["user_id", "ts", "event", "course_id", "video_id", "card_id",
               "rating", "review_number", "duration_sec"],
    "survey": ["respondent_id", "goal", "device", "creators", "last_playlist_progress",
               *C.PAIN_COLUMNS.keys(), "revision_method", "revision_rating",
               "tools_used", "top_problem", "installed_study_ext", "permission_comfort"],
    "interviews": ["participant_id", "hypothesis", "verdict", "unprompted", "quote"],
    "recall_test": ["user_id", "topic_type", "score"],
}

EVENT_TYPES = {
    "install", "uninstall", "course_added", "study_session", "video_completed",
    "flag_created", "review_session_completed", "card_reviewed", "detection_error",
}

MIN_SURVEY_N = 30   # below this, research checks report "too little data"


def missing_columns(df: pd.DataFrame, table: str) -> list[str]:
    return [c for c in REQUIRED_COLUMNS[table] if c not in df.columns]


def prep_events(events: pd.DataFrame) -> pd.DataFrame:
    ev = events.copy()
    ev["ts"] = pd.to_datetime(ev["ts"], utc=True).dt.tz_convert(None)
    ev["day"] = ev["ts"].dt.normalize()
    ev["review_number"] = pd.to_numeric(ev["review_number"], errors="coerce")
    ev["duration_sec"] = pd.to_numeric(ev["duration_sec"], errors="coerce")
    return ev.sort_values("ts").reset_index(drop=True)


@dataclass
class Status:
    value: float | None
    target: str
    result: str          # "pass" | "fail" | "no data"
    n: int = 0


def _status(value, ok: bool | None, target: str, n: int) -> Status:
    if value is None or (isinstance(value, float) and np.isnan(value)) or ok is None:
        return Status(None, target, "no data", n)
    return Status(float(value), target, "pass" if ok else "fail", n)


# ------------------------------------------------------------------ users
def users(ev: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """One row per installed user: install time, uninstall, activation."""
    inst = ev[ev.event == "install"].groupby("user_id")["ts"].min().rename("install_ts")
    uninst = ev[ev.event == "uninstall"].groupby("user_id")["ts"].min().rename("uninstall_ts")
    u = pd.concat([inst, uninst], axis=1).dropna(subset=["install_ts"])
    u = u[u.install_ts <= as_of]

    win = pd.Timedelta(hours=C.ACTIVATION_WINDOW_HOURS)
    e = ev.merge(u[["install_ts"]], left_on="user_id", right_index=True)
    e = e[(e.ts >= e.install_ts) & (e.ts <= e.install_ts + win)]
    u["course_72h"] = e[e.event == "course_added"].groupby("user_id").size().reindex(u.index).fillna(0) > 0
    u["flags_72h"] = e[e.event == "flag_created"].groupby("user_id").size().reindex(u.index).fillna(0)
    u["review_72h"] = e[e.event == "review_session_completed"].groupby("user_id").size().reindex(u.index).fillna(0) > 0
    u["activated"] = u.course_72h & (u.flags_72h >= C.ACTIVATION_MIN_FLAGS) & u.review_72h
    u["install_week"] = u.install_ts.dt.to_period("W-SUN").dt.start_time
    return u


def activation_funnel(u: pd.DataFrame) -> pd.DataFrame:
    steps = [
        ("Installed", pd.Series(True, index=u.index)),
        ("Added a course", u.course_72h),
        (f"{C.ACTIVATION_MIN_FLAGS}+ flags", u.course_72h & (u.flags_72h >= C.ACTIVATION_MIN_FLAGS)),
        ("First review (activated)", u.activated),
    ]
    rows, prev = [], None
    total = len(u)
    for name, mask in steps:
        n = int(mask.sum())
        rows.append({"step": name, "users": n,
                     "pct_of_installed": n / total if total else np.nan,
                     "pct_of_previous": (n / prev) if prev else np.nan})
        prev = n
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ north star
def weekly_active_reviewers(ev: pd.DataFrame, u: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Share of installed (not yet uninstalled) users reviewing on 3+ days, per Mon-Sun week."""
    if u.empty:
        return pd.DataFrame(columns=["week_start", "active_reviewers", "installed_base", "share", "complete"])
    reviews = ev[ev.event == "review_session_completed"][["user_id", "day"]].drop_duplicates()
    reviews = reviews.assign(week_start=reviews.day.dt.to_period("W-SUN").dt.start_time)
    days_per_week = reviews.groupby(["week_start", "user_id"]).size()

    weeks = pd.period_range(u.install_ts.min(), as_of, freq="W-SUN").start_time
    rows = []
    for w in weeks:
        w_end = w + pd.Timedelta(days=7)
        base = u[(u.install_ts < w_end) & (u.uninstall_ts.isna() | (u.uninstall_ts >= w))]
        if w in days_per_week.index.get_level_values(0):
            d = days_per_week.loc[w]
            active = d[(d >= C.NORTH_STAR_MIN_REVIEW_DAYS) & d.index.isin(base.index)]
        else:
            active = []
        rows.append({"week_start": w, "active_reviewers": len(active), "installed_base": len(base),
                     "share": len(active) / len(base) if len(base) else np.nan,
                     "complete": w_end <= as_of + pd.Timedelta(days=1)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ engagement
def flags_per_hour(ev: pd.DataFrame) -> Status:
    hours = ev.loc[ev.event == "study_session", "duration_sec"].sum() / 3600
    flags = (ev.event == "flag_created").sum()
    val = flags / hours if hours > 0 else None
    return _status(val, None if val is None else val >= C.FLAGS_PER_HOUR_TARGET,
                   f"≥ {C.FLAGS_PER_HOUR_TARGET:g}", int(flags))


def last_complete_week(war: pd.DataFrame) -> pd.Timestamp | None:
    done = war[war.complete]
    return None if done.empty else done.week_start.max()


def weekly_engagement(ev: pd.DataFrame, week_start: pd.Timestamp | None) -> dict:
    """Review days and videos completed per active learner in one week."""
    if week_start is None:
        return {"review_days": Status(None, f"≥ {C.REVIEW_DAYS_TARGET:g}", "no data"),
                "videos": Status(None, "track", "no data")}
    wk = ev[(ev.ts >= week_start) & (ev.ts < week_start + pd.Timedelta(days=7))]
    rv = wk[wk.event == "review_session_completed"].groupby("user_id")["day"].nunique()
    vids = wk[wk.event == "video_completed"].groupby("user_id").size().reindex(rv.index).fillna(0)
    rd = rv.mean() if len(rv) else None
    return {
        "review_days": _status(rd, None if rd is None else rd >= C.REVIEW_DAYS_TARGET,
                               f"≥ {C.REVIEW_DAYS_TARGET:g}", len(rv)),
        "videos": Status(float(vids.mean()) if len(vids) else None, "track (no target)",
                         "info" if len(vids) else "no data", len(vids)),
    }


# ------------------------------------------------------------------ retention
def _week_k_reviewers(ev: pd.DataFrame, u: pd.DataFrame, k: int, as_of: pd.Timestamp):
    """Activated users whose week k since install has fully elapsed, and who reviewed in it."""
    act = u[u.activated]
    start = act.install_ts + pd.Timedelta(days=7 * k)
    end = start + pd.Timedelta(days=7)
    eligible = act[end <= as_of]
    if eligible.empty:
        return eligible.index, pd.Index([])
    r = ev[ev.event == "review_session_completed"].merge(
        pd.DataFrame({"s": start, "e": end}).loc[eligible.index], left_on="user_id", right_index=True)
    hit = r[(r.ts >= r.s) & (r.ts < r.e)].user_id.unique()
    return eligible.index, pd.Index(hit)


def retention(ev, u, as_of, k: int, target: float) -> Status:
    elig, hit = _week_k_reviewers(ev, u, k, as_of)
    val = len(hit) / len(elig) if len(elig) else None
    return _status(val, None if val is None else val >= target, f"≥ {target:.0%}", len(elig))


def cohort_matrix(ev, u, as_of, max_k: int = 6) -> pd.DataFrame:
    """Rows: install week. Columns: weeks since install. Values: share of activated users reviewing."""
    rows = []
    for wk, grp in u[u.activated].groupby("install_week"):
        row = {"install_week": wk, "activated": len(grp)}
        for k in range(max_k + 1):
            elig, hit = _week_k_reviewers(ev, u.loc[grp.index], k, as_of)
            row[k] = len(hit) / len(elig) if len(elig) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ learning quality
def second_review_recall(ev: pd.DataFrame) -> Status:
    c = ev[(ev.event == "card_reviewed") & (ev.review_number == 2)]
    lo, hi = C.SECOND_REVIEW_RECALL_RANGE
    if c.empty:
        return _status(None, None, f"{lo:.0%}–{hi:.0%}", 0)
    val = (c.rating == "remembered").mean()
    return _status(val, lo <= val <= hi, f"{lo:.0%}–{hi:.0%}", len(c))


def recall_test(rt: pd.DataFrame) -> dict:
    """Paired comparison: each volunteer's flagged vs unflagged score, in percentage points."""
    p = rt.pivot_table(index="user_id", columns="topic_type", values="score", aggfunc="mean")
    p = p.dropna(subset=[c for c in ("flagged", "unflagged") if c in p.columns])
    if not {"flagged", "unflagged"} <= set(p.columns) or len(p) < 2:
        return {"status": _status(None, None, f"≥ +{C.RECALL_TEST_MIN_GAP_PTS:g} pts", len(p)),
                "per_user": p, "ci": (np.nan, np.nan), "means": {}}
    pts = p / C.RECALL_TEST_MAX_SCORE * 100
    diff = pts.flagged - pts.unflagged
    n = len(diff)
    se = diff.std(ddof=1) / np.sqrt(n)
    try:
        from scipy import stats
        t = stats.t.ppf(0.975, n - 1)
    except ImportError:          # normal approximation if scipy is absent
        t = 1.96
    mean = diff.mean()
    return {
        "status": _status(mean, mean >= C.RECALL_TEST_MIN_GAP_PTS, f"≥ +{C.RECALL_TEST_MIN_GAP_PTS:g} pts", n),
        "per_user": pts,
        "ci": (mean - t * se, mean + t * se),
        "means": {"flagged": pts.flagged.mean(), "unflagged": pts.unflagged.mean()},
    }


# ------------------------------------------------------------------ guardrails
def guardrails(ev: pd.DataFrame, u: pd.DataFrame, as_of: pd.Timestamp) -> dict[str, Status]:
    out = {}
    sess = ev.loc[ev.event == "review_session_completed", "duration_sec"].dropna() / 60
    med = sess.median() if len(sess) else None
    out["Median review session (min)"] = _status(
        med, None if med is None else med <= C.REVIEW_SESSION_MAX_MIN, f"≤ {C.REVIEW_SESSION_MAX_MIN:g}", len(sess))

    old = u[u.install_ts <= as_of - pd.Timedelta(days=7)]
    churn = (old.uninstall_ts.notna() & (old.uninstall_ts <= old.install_ts + pd.Timedelta(days=7))).mean() \
        if len(old) else None
    out["Uninstalled within 7 days"] = _status(
        churn, None if churn is None else churn < C.EARLY_CHURN_MAX, f"< {C.EARLY_CHURN_MAX:.0%}", len(old))

    # learning not displaced: activated users' completions, latest full personal week vs install week
    act = u[u.activated & (u.install_ts <= as_of - pd.Timedelta(days=14))]
    vids = ev.loc[(ev.event == "video_completed") & ev.user_id.isin(act.index), ["user_id", "ts"]].copy()
    first = latest = 0
    if not vids.empty:
        install = vids.user_id.map(act.install_ts.to_dict())
        k = (vids.ts - install).dt.days // 7
        last_k = vids.user_id.map(((as_of - act.install_ts).dt.days // 7 - 1).to_dict())  # latest full week
        first = int((k == 0).sum())
        latest = int((k == last_k).sum())
    ratio = latest / first if first else None
    out["Videos completed, latest week vs first"] = _status(
        ratio, None if ratio is None else ratio >= C.LEARNING_NOT_DISPLACED_MIN_RATIO,
        f"≥ {C.LEARNING_NOT_DISPLACED_MIN_RATIO:.0%}", len(act))

    sessions = (ev.event == "study_session").sum()
    errs = (ev.event == "detection_error").sum()
    rate = errs / sessions if sessions else None
    out["Sessions with a detection error"] = _status(
        rate, None if rate is None else rate < C.DETECTION_ERROR_MAX, f"< {C.DETECTION_ERROR_MAX:.0%}", int(sessions))
    return out


# ------------------------------------------------------------------ research
def segment(survey: pd.DataFrame) -> pd.DataFrame:
    return survey[survey.goal == C.SEGMENT_GOAL]


def _share(mask: pd.Series) -> float:
    return float(mask.mean()) if len(mask) else np.nan


def _has(col: pd.Series, *needles: str) -> pd.Series:
    s = col.fillna("").str.lower()
    return s.apply(lambda v: any(n in v.split(";") for n in needles))


def interview_share(interviews: pd.DataFrame, hyp: str) -> tuple[float, int]:
    """Share of interviewees who raised a hypothesis unprompted AND supported it."""
    n = interviews.participant_id.nunique()
    hit = interviews[(interviews.hypothesis == hyp) & (interviews.verdict == "supports")
                     & (interviews.unprompted.astype(str).str.lower() == "yes")].participant_id.nunique()
    return (hit / n if n else np.nan), n


def pain_frequency(seg: pd.DataFrame) -> pd.DataFrame:
    rows = [{"pain": label, "share_2plus": _share(seg[col].isin(C.TWO_PLUS)), "n": len(seg)}
            for col, label in C.PAIN_COLUMNS.items()]
    return pd.DataFrame(rows).sort_values("share_2plus", ascending=False)


def kill_scorecard(survey: pd.DataFrame, interviews: pd.DataFrame) -> pd.DataFrame:
    """Score every Phase 1 kill/continue criterion. All parts of a check must pass."""
    s = segment(survey)
    K = C.KILL
    n = len(s)
    rows = []

    def add(check, hyp, parts, if_fail):
        enough = n >= MIN_SURVEY_N
        res = "pass" if all(ok for _, ok in parts) else "fail"
        rows.append({"check": check, "hypothesis": hyp,
                     "evidence": " · ".join(t for t, _ in parts),
                     "result": res if enough else "too little data",
                     "if it fails": if_fail})

    laptop = _share(s.device == "laptop")
    add("Chrome extension is the right vehicle", "device",
        [(f"laptop {laptop:.0%} (need ≥ {K['laptop_share_min']:.0%})", laptop >= K["laptop_share_min"])],
        "Switch to a web app / PWA, or reconsider the segment")

    forgot = _share(s.pain_forgot.isin(C.TWO_PLUS))
    rating = pd.to_numeric(s.revision_rating, errors="coerce").mean()
    i7, ni = interview_share(interviews, "H7")
    add("Revision is the core pain", "H7",
        [(f"forgot 2+ times {forgot:.0%} (≥ {K['h7_forgot_2plus_min']:.0%})", forgot >= K["h7_forgot_2plus_min"]),
         (f"revision rated {rating:.1f}/5 (≤ {K['h7_revision_rating_max']:g})", rating <= K["h7_revision_rating_max"]),
         (f"interviews {i7:.0%} of {ni} (≥ {K['h7_interview_share_min']:.0%})", (i7 >= K["h7_interview_share_min"]) if ni else False)],
        "Drop revision as the wedge; promote H1, H8 or H4")

    not_fin = _share(~s.last_playlist_progress.isin(["finished", "over_75"]))
    lost = _share(s.pain_lost_place.isin(C.TWO_PLUS))
    add("Playlist drop-off is real", "H1",
        [(f"didn't reach 75% {not_fin:.0%} (≥ {K['h1_not_finished_min']:.0%})", not_fin >= K["h1_not_finished_min"]),
         (f"lost place 2+ times {lost:.0%} (≥ {K['h1_lost_place_2plus_min']:.0%})", lost >= K["h1_lost_place_2plus_min"])],
        "Progress tracking becomes minor or is cut")

    multi = _share(s.creators.astype(str).isin(["2", "3+"]))
    add("Students learn from several creators", "H8",
        [(f"2+ creators {multi:.0%} (≥ {K['h8_two_plus_creators_min']:.0%})", multi >= K["h8_two_plus_creators_min"])],
        "Single-playlist courses only")

    unsure = _share(s.pain_unsure.isin(C.TWO_PLUS))
    add("Understanding goes unchecked", "H4",
        [(f"unsure 2+ times {unsure:.0%} (≥ {K['h4_unsure_2plus_min']:.0%})", unsure >= K["h4_unsure_2plus_min"])],
        "Skip checks; link to practice problems")

    derailed = _share(s.pain_derailed.isin(C.TWO_PLUS))
    blocker = _share(_has(s.tools_used, "blocker"))
    add("Distraction is worth building for", "H2",
        [(f"derailed 2+ times {derailed:.0%} (≥ {K['h2_derailed_2plus_min']:.0%})", derailed >= K["h2_derailed_2plus_min"]),
         (f"already use a blocker {blocker:.0%} (< {K['h2_blocker_use_max']:.0%})", blocker < K["h2_blocker_use_max"])],
        "Basic toggle only, or skip")

    ai = _share(_has(s.tools_used, "ask", "ai_summariser"))
    add("AI summaries aren't already covered", "AI",
        [(f"use Ask / AI summariser {ai:.0%} (< {K['ai_tool_use_max']:.0%})", ai < K["ai_tool_use_max"])],
        "Don't build summaries; AI only for revision")

    inst = _share(s.installed_study_ext.astype(str).str.lower() == "yes")
    comfort = _share(pd.to_numeric(s.permission_comfort, errors="coerce") >= 4)
    add("Students will install it", "adoption",
        [(f"installed a study extension {inst:.0%} (≥ {K['adopt_installed_ext_min']:.0%})", inst >= K["adopt_installed_ext_min"]),
         (f"comfortable with permissions {comfort:.0%} (≥ {K['adopt_comfort_4plus_min']:.0%})", comfort >= K["adopt_comfort_4plus_min"])],
        "Heavier onboarding, local-only storage, privacy messaging")

    return pd.DataFrame(rows)
