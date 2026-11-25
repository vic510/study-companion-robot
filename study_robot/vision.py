"""Webcam observation: face presence and coarse head direction via MediaPipe."""

from dataclasses import dataclass
from typing import Optional

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

# Face mesh landmark indices.
NOSE_TIP = 1
LEFT_CHEEK = 234
RIGHT_CHEEK = 454
CHIN = 152
LEFT_EYE_OUTER = 33
RIGHT_EYE_OUTER = 263


@dataclass
class Observation:
    face_present: bool
    # ~0.5 when facing the camera straight; moves toward 0 / 1 when turning.
    yaw_ratio: Optional[float] = None
    # Nose position between eye line (0) and chin (1); grows when looking down.
    pitch_ratio: Optional[float] = None
    landmarks: Optional[list] = None


class AttentionEstimator:
    def __init__(self, model_path: str):
        options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)

    def observe(self, frame_bgr, timestamp_ms: int) -> Observation:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_landmarks:
            return Observation(face_present=False)

        lm = result.face_landmarks[0]
        nose, lc, rc = lm[NOSE_TIP], lm[LEFT_CHEEK], lm[RIGHT_CHEEK]
        chin = lm[CHIN]
        eye_y = (lm[LEFT_EYE_OUTER].y + lm[RIGHT_EYE_OUTER].y) / 2

        width = rc.x - lc.x
        height = chin.y - eye_y
        if abs(width) < 1e-6 or abs(height) < 1e-6:
            return Observation(face_present=True, landmarks=lm)

        return Observation(
            face_present=True,
            yaw_ratio=(nose.x - lc.x) / width,
            pitch_ratio=(nose.y - eye_y) / height,
            landmarks=lm,
        )

    def close(self):
        self._landmarker.close()


LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12


class BodyDetector:
    """Checks whether someone is still at the desk when the face is lost
    (e.g. head down over a phone, or turned far away)."""

    def __init__(self, model_path: str):
        options = mp_vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=model_path),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)

    def body_present(self, frame_bgr, timestamp_ms: int) -> bool:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.pose_landmarks:
            return False
        lm = result.pose_landmarks[0]
        return any(lm[i].visibility > 0.5 for i in (LEFT_SHOULDER, RIGHT_SHOULDER))

    def close(self):
        self._landmarker.close()


class Calibration:
    """Learns the user's normal studying pose (often looking down at notes)."""

    def __init__(self):
        self._yaws: list[float] = []
        self._pitches: list[float] = []

    def add(self, obs: Observation):
        if obs.yaw_ratio is not None and obs.pitch_ratio is not None:
            self._yaws.append(obs.yaw_ratio)
            self._pitches.append(obs.pitch_ratio)

    @property
    def ready(self) -> bool:
        return len(self._yaws) >= 10

    def baseline(self) -> tuple[float, float]:
        if not self.ready:
            return 0.5, 0.5
        ys, ps = sorted(self._yaws), sorted(self._pitches)
        return ys[len(ys) // 2], ps[len(ps) // 2]


def is_looking(obs: Observation, baselines: list[tuple[float, float]],
               yaw_tol: float, pitch_tol: float) -> bool:
    """True if the head points at any of the calibrated study targets."""
    if not obs.face_present or obs.yaw_ratio is None:
        return False
    return any(abs(obs.yaw_ratio - yaw0) <= yaw_tol
               and abs(obs.pitch_ratio - pitch0) <= pitch_tol
               for yaw0, pitch0 in baselines)
