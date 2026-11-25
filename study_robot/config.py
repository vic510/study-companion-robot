"""Tunable parameters. Adjust these after pilot testing."""

from dataclasses import dataclass


@dataclass
class Thresholds:
    # Head-direction tolerance relative to the calibrated "studying" pose.
    # yaw_ratio / pitch_ratio are normalised landmark ratios (see vision.py).
    # Yaw is wider: it gets noisy when the head turns far to the side
    # (pilot 2026-10-20: main-screen yaw spread 0.75–1.2).
    yaw_tolerance: float = 0.18
    pitch_tolerance: float = 0.12

    # How long the user must look away continuously before the robot
    # considers them distracted (avoids reacting to natural short glances).
    distracted_after_s: float = 8.0
    # How long the face must be missing before entering the Away state.
    away_after_s: float = 3.0
    # How long the user must look back before returning to Focused.
    refocus_after_s: float = 1.0

    # While still distracted, repeat a reminder at most this often.
    reminder_interval_s: float = 30.0
    # After this much continuous distraction, suggest a short break instead.
    suggest_break_after_s: float = 60.0


@dataclass
class FixedSchedule:
    # Non-adaptive (control) condition: encouragement at fixed intervals,
    # regardless of what the user is doing.
    encourage_every_s: float = 300.0


CALIBRATION_SECONDS = 3.0
# Pause before sampling each target so the user has time to move their gaze.
CALIBRATION_PREP_SECONDS = 3.0  # includes time to hear the spoken prompt
# Retry a target whose pose matches an earlier target, then accept it anyway.
CALIBRATION_MAX_RETRIES = 2
# Places the user legitimately looks at while studying; each is calibrated.
DEFAULT_TARGETS = "screen,laptop"
MODEL_PATH = "models/face_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
# Body detection tells "looking down / turned away" (face lost, body still
# there) apart from actually leaving the desk.
POSE_MODEL_PATH = "models/pose_landmarker_lite.task"
POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)
