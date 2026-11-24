"""Generate FAKE sample data so the dashboard can be explored before the pilot.

Nothing produced here is a research finding. Never quote these numbers on a
resume, in a write-up or in an interview. Replace with real exports.

    python generate_sample_data.py            # writes data/sample/*.csv
    python generate_sample_data.py --seed 7   # a different fake world
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PILOT_START = pd.Timestamp("2026-12-14 09:00")   # a Monday
PILOT_DAYS = 42                                  # 6 weeks
N_USERS = 130
N_SURVEY = 90
N_INTERVIEWS = 15
N_RECALL = 24


def gen_events(rng: np.random.Generator) -> pd.DataFrame:
    rows = []

    def add(uid, ts, event, **kw):
        rows.append({"user_id": uid, "ts": ts, "event": event, "course_id": kw.get("course_id", ""),
                     "video_id": kw.get("video_id", ""), "card_id": kw.get("card_id", ""),
                     "rating": kw.get("rating", ""), "review_number": kw.get("review_number", ""),
                     "duration_sec": kw.get("duration_sec", "")})

    end = PILOT_START + pd.Timedelta(days=PILOT_DAYS)
    for i in range(N_USERS):
        uid = f"u{i:03d}"
        install = PILOT_START + pd.Timedelta(hours=float(rng.uniform(0, 24 * 28)))
        eng = rng.beta(2, 2.5)                       # latent engagement 0..1
        add(uid, install, "install")

        if rng.random() > 0.15 + 0.2 * (1 - eng):    # most add a course
            add(uid, install + pd.Timedelta(minutes=float(rng.uniform(2, 600))), "course_added", course_id=f"{uid}-c1")
        else:
            if rng.random() < 0.5:
                add(uid, install + pd.Timedelta(days=float(rng.uniform(1, 6))), "uninstall")
            continue

        uninstall_at = None
        if rng.random() < 0.25 * (1 - eng):
            uninstall_at = install + pd.Timedelta(days=float(rng.uniform(2, 20)))
            add(uid, uninstall_at, "uninstall")
        stop = min(end, uninstall_at) if uninstall_at is not None else end

        flag_rate = rng.uniform(1.0, 5.5) * (0.5 + eng)      # flags per study hour
        cards, card_no, vid_no = [], 0, 0
        day = install.normalize()
        while day < stop:
            weeks_in = (day - install).days / 7
            # study session
            if rng.random() < 0.25 + 0.55 * eng:
                t0 = day + pd.Timedelta(hours=float(rng.uniform(9, 23)))
                if t0 < install:
                    t0 = install + pd.Timedelta(minutes=30)
                if t0 >= stop:
                    break
                dur = float(rng.uniform(20, 100) * 60)
                add(uid, t0, "study_session", course_id=f"{uid}-c1", duration_sec=round(dur))
                if rng.random() < 0.012:
                    add(uid, t0 + pd.Timedelta(minutes=1), "detection_error")
                for _ in range(int(dur // (16 * 60))):
                    vid_no += 1
                    add(uid, t0 + pd.Timedelta(seconds=float(rng.uniform(0, dur))), "video_completed",
                        course_id=f"{uid}-c1", video_id=f"{uid}-v{vid_no}")
                for _ in range(rng.poisson(flag_rate * dur / 3600)):
                    card_no += 1
                    cid = f"{uid}-k{card_no}"
                    ft = t0 + pd.Timedelta(seconds=float(rng.uniform(0, dur)))
                    add(uid, ft, "flag_created", course_id=f"{uid}-c1", card_id=cid)
                    cards.append({"id": cid, "due": ft + pd.Timedelta(days=1), "box": 0})
            # review session on due cards
            due = [c for c in cards if c["due"] <= day + pd.Timedelta(days=1)]
            p_review = (0.3 + 0.65 * eng) * (0.93 ** weeks_in)
            if due and rng.random() < p_review:
                t1 = day + pd.Timedelta(hours=float(rng.uniform(7, 23)))
                if install < t1 < stop:
                    batch = due[:10]
                    for c in batch:
                        p_rem = min(0.92, 0.55 + 0.1 * c["box"] + 0.15 * eng)
                        r = rng.choice(["remembered", "fuzzy", "forgot"],
                                       p=[p_rem, (1 - p_rem) * 0.55, (1 - p_rem) * 0.45])
                        add(uid, t1, "card_reviewed", card_id=c["id"], rating=r, review_number=c["box"] + 1)
                        c["box"] = c["box"] + 1 if r == "remembered" else (c["box"] if r == "fuzzy" else 0)
                        c["due"] = t1 + pd.Timedelta(days=[1, 3, 7, 14, 30][min(c["box"], 4)])
                    add(uid, t1 + pd.Timedelta(minutes=1), "review_session_completed",
                        duration_sec=round(len(batch) * float(rng.uniform(35, 75))))
            day += pd.Timedelta(days=1)

    ev = pd.DataFrame(rows).sort_values("ts")
    ev["ts"] = ev.ts.dt.strftime("%Y-%m-%dT%H:%M:%S")
    return ev


def gen_survey(rng: np.random.Generator) -> pd.DataFrame:
    def pick(opts, p, n=N_SURVEY):
        return rng.choice(opts, size=n, p=p)

    freq = ["never", "once", "2-3", "4+"]
    tools = []
    for _ in range(N_SURVEY):
        t = [x for x, p in [("ask", 0.18), ("ai_summariser", 0.12), ("blocker", 0.2), ("notes_tool", 0.1)]
             if rng.random() < p]
        tools.append(";".join(t) if t else "none")
    return pd.DataFrame({
        "respondent_id": [f"r{i:03d}" for i in range(N_SURVEY)],
        "year": pick(["2", "3", "4"], [0.3, 0.4, 0.3]),
        "branch": pick(["CSE", "IT", "ECE", "EEE", "Mech"], [0.45, 0.15, 0.2, 0.1, 0.1]),
        "goal": pick(["placements", "gate", "semester", "other_exam", "none"], [0.68, 0.1, 0.12, 0.05, 0.05]),
        "yt_hours": pick(["0", "<2", "2-5", "5-10", "10+"], [0.03, 0.17, 0.4, 0.28, 0.12]),
        "device": pick(["laptop", "phone", "tablet", "split"], [0.66, 0.2, 0.02, 0.12]),
        "creators": pick(["1", "2", "3+", "none"], [0.4, 0.38, 0.17, 0.05]),
        "last_playlist_progress": pick(["finished", "over_75", "25_75", "under_25", "dropped_early"],
                                       [0.12, 0.18, 0.35, 0.2, 0.15]),
        "pain_lost_place": pick(freq, [0.25, 0.3, 0.3, 0.15]),
        "pain_derailed": pick(freq, [0.15, 0.25, 0.35, 0.25]),
        "pain_cant_find": pick(freq, [0.2, 0.3, 0.3, 0.2]),
        "pain_forgot": pick(freq, [0.1, 0.2, 0.4, 0.3]),
        "pain_unsure": pick(freq, [0.2, 0.3, 0.32, 0.18]),
        "revision_method": pick(["rewatch", "own_notes", "sheet", "practice", "ai_tool", "none"],
                                [0.35, 0.25, 0.1, 0.15, 0.05, 0.1]),
        "revision_rating": pick(["1", "2", "3", "4", "5"], [0.1, 0.3, 0.35, 0.2, 0.05]),
        "tracking_method": pick(["none", "yt_history", "spreadsheet", "notion", "notebook", "extension"],
                                [0.35, 0.25, 0.15, 0.1, 0.12, 0.03]),
        "tools_used": tools,
        "top_problem": pick(["forgot", "lost_place", "derailed", "cant_find", "unsure", "planning"],
                            [0.3, 0.15, 0.15, 0.1, 0.12, 0.18]),
        "installed_study_ext": pick(["yes", "no"], [0.45, 0.55]),
        "permission_comfort": pick(["1", "2", "3", "4", "5"], [0.08, 0.12, 0.25, 0.35, 0.2]),
    })


def gen_interviews(rng: np.random.Generator) -> pd.DataFrame:
    support_p = {"H1": 0.55, "H2": 0.35, "H3": 0.45, "H4": 0.5, "H5": 0.4, "H6": 0.2, "H7": 0.7, "H8": 0.45}
    rows = []
    for i in range(N_INTERVIEWS):
        for h, p in support_p.items():
            r = rng.random()
            verdict = "supports" if r < p else ("contradicts" if r < p + 0.2 else "not_discussed")
            rows.append({"participant_id": f"p{i:02d}", "hypothesis": h, "verdict": verdict,
                         "unprompted": "yes" if verdict != "not_discussed" and rng.random() < 0.7 else "no",
                         "quote": "[sample placeholder - replace with a real quote]" if verdict == "supports" else ""})
    return pd.DataFrame(rows)


def gen_recall(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for i in range(N_RECALL):
        skill = rng.uniform(-0.15, 0.15)
        rows.append({"user_id": f"u{i:03d}", "topic_type": "flagged", "score": int(rng.binomial(5, 0.74 + skill))})
        rows.append({"user_id": f"u{i:03d}", "topic_type": "unflagged", "score": int(rng.binomial(5, 0.55 + skill))})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).parent / "data" / "sample"))
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    gen_events(rng).to_csv(out / "events.csv", index=False)
    gen_survey(rng).to_csv(out / "survey.csv", index=False)
    gen_interviews(rng).to_csv(out / "interviews.csv", index=False)
    gen_recall(rng).to_csv(out / "recall_test.csv", index=False)
    (out / "README.txt").write_text("FAKE SAMPLE DATA generated by generate_sample_data.py.\n"
                                    "Not research findings. Do not quote these numbers anywhere.\n")
    print(f"Wrote fake sample data to {out}")


if __name__ == "__main__":
    main()
