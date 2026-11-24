"""Targets and thresholds for the Recall PM dashboard.

Every number here comes from the Phase 1 / Phase 2 strategy doc and is a
planning assumption set BEFORE data was collected. Change them here, in one
place, and only for a reason you write down in the decision log.
"""

# ---------------------------------------------------------------- pilot targets
NORTH_STAR_MIN_REVIEW_DAYS = 3          # reviews on 3+ distinct days in a week
NORTH_STAR_TARGET = 0.30                # 30% of installed users by pilot week 4

ACTIVATION_WINDOW_HOURS = 72            # course + 3 flags + first review within 72h
ACTIVATION_MIN_FLAGS = 3
ACTIVATION_TARGET = 0.40

FLAGS_PER_HOUR_TARGET = 3.0
REVIEW_DAYS_TARGET = 3.0

RETENTION_W1_TARGET = 0.50
RETENTION_W4_TARGET = 0.25

SECOND_REVIEW_RECALL_RANGE = (0.60, 0.85)   # above 85% = cards too easy
RECALL_TEST_MIN_GAP_PTS = 15.0              # flagged beat unflagged by 15+ points
RECALL_TEST_MAX_SCORE = 5

# guardrails
REVIEW_SESSION_MAX_MIN = 10.0
EARLY_CHURN_MAX = 0.20                  # uninstall within 7 days
LEARNING_NOT_DISPLACED_MIN_RATIO = 0.90 # latest-week completions vs. install week
DETECTION_ERROR_MAX = 0.02

# ---------------------------------------------------------------- kill criteria
SEGMENT_GOAL = "placements"             # survey S2 value that defines the segment
INTERVIEW_TARGET_N = 15

KILL = {
    "laptop_share_min": 0.60,
    "h7_forgot_2plus_min": 0.40,
    "h7_revision_rating_max": 3.0,
    "h7_interview_share_min": 8 / 15,
    "h1_not_finished_min": 0.50,
    "h1_lost_place_2plus_min": 0.30,
    "h8_two_plus_creators_min": 0.40,
    "h4_unsure_2plus_min": 0.40,
    "h2_derailed_2plus_min": 0.30,
    "h2_blocker_use_max": 0.30,
    "ai_tool_use_max": 0.30,
    "adopt_installed_ext_min": 0.40,
    "adopt_comfort_4plus_min": 0.50,
}

# survey answer codes (S8 grid)
TWO_PLUS = {"2-3", "4+"}
FREQ_ORDER = ["never", "once", "2-3", "4+"]
PAIN_COLUMNS = {
    "pain_lost_place": "Lost my place in a playlist (H1)",
    "pain_derailed": "Pulled into unrelated videos (H2)",
    "pain_cant_find": "Couldn't find a part I'd watched (H3)",
    "pain_forgot": "Forgot something I'd learned (H7)",
    "pain_unsure": "Unsure I'd understood a video (H4)",
}

# ---------------------------------------------------------------- chart palette
# Premium dark analytics theme

COLORS = {
    "series_1": "#6EA8FE",       # Soft electric blue
    "series_2": "#F59E7B",       # Warm coral
    "text_primary": "#E8EEF7",   # Main labels
    "text_secondary": "#A7B2C4", # Secondary labels
    "muted": "#77849A",
    "grid": "#2B3443",
    "axis": "#3B4658",
    "surface": "#151B26",        # Chart background
    "good": "#34D399",           # Emerald green
    "critical": "#FB7185",       # Soft red
    "warning": "#FBBF24",        # Amber
}

SEQUENTIAL_BLUE = [
    "#DCEBFF",
    "#A9CEFF",
    "#7DB5FF",
    "#5599F2",
    "#397BD5",
    "#285CA8",
    "#193F78",
]
