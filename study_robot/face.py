"""Animated robot face (non-verbal feedback), drawn with OpenCV."""

import math
import random

import cv2
import numpy as np

from .state_machine import State

W, H = 640, 480
BG = (40, 30, 25)
HEAD = (70, 55, 45)
FACE_COLOR = {
    State.FOCUSED: (230, 220, 120),     # calm cyan
    State.DISTRACTED: (80, 180, 255),   # warm orange
    State.AWAY: (170, 150, 140),        # dim grey
    State.COMPLETE: (120, 230, 120),    # green
}

# Target expression per state: eye openness, mouth curve (+ smile), brow tilt.
TARGETS = {
    State.FOCUSED: dict(eye=1.0, mouth=0.6, brow=0.0),
    State.DISTRACTED: dict(eye=1.15, mouth=-0.3, brow=0.6),
    State.AWAY: dict(eye=0.0, mouth=0.0, brow=0.0),
    State.COMPLETE: dict(eye=1.0, mouth=1.0, brow=-0.3),
}


def _lerp(a, b, k):
    return a + (b - a) * k


class RobotFace:
    def __init__(self):
        self.p = dict(TARGETS[State.FOCUSED])
        self._next_blink = 3.0
        self._blink_until = 0.0
        self._confetti = [(random.randint(0, W), random.randint(-H, 0),
                           random.choice([(255, 120, 120), (120, 255, 255),
                                          (255, 255, 120), (200, 120, 255)]))
                          for _ in range(60)]

    def render(self, state: State, now: float, remaining_s: float,
               progress: float, caption: str | None = None,
               condition_label: str = "") -> np.ndarray:
        target = TARGETS[state]
        for k in self.p:
            self.p[k] = _lerp(self.p[k], target[k], 0.15)

        img = np.full((H, W, 3), BG, np.uint8)
        cv2.rectangle(img, (90, 70), (550, 400), HEAD, -1, cv2.LINE_AA)
        color = FACE_COLOR[state]

        # Blinking (not while asleep / celebrating).
        if now >= self._next_blink:
            self._blink_until = now + 0.15
            self._next_blink = now + random.uniform(2.5, 5.5)
        blinking = now < self._blink_until and state in (State.FOCUSED, State.DISTRACTED)

        # Gentle idle bob so the robot feels alive.
        bob = int(4 * math.sin(now * 2.0))
        eye_y = 200 + bob
        for cx, side in ((240, -1), (400, 1)):
            if state == State.COMPLETE:
                cv2.ellipse(img, (cx, eye_y + 10), (35, 30), 0, 200, 340, color, 8, cv2.LINE_AA)
            elif blinking or self.p["eye"] < 0.12:
                cv2.line(img, (cx - 35, eye_y), (cx + 35, eye_y), color, 7, cv2.LINE_AA)
            else:
                cv2.ellipse(img, (cx, eye_y), (32, int(42 * self.p["eye"])), 0, 0, 360, color, -1, cv2.LINE_AA)
            # Brows: inner end raised when concerned.
            tilt = int(18 * self.p["brow"])
            inner, outer = cx - side * 30, cx + side * 30
            cv2.line(img, (outer, eye_y - 65), (inner, eye_y - 65 - tilt), color, 6, cv2.LINE_AA)

        # Mouth as a parabola; positive curve = smile.
        pts = []
        for i in range(21):
            t = i / 20 * 2 - 1
            x = int(320 + t * 70)
            y = int(320 + bob + self.p["mouth"] * 28 * (1 - t * t))
            pts.append((x, y))
        cv2.polylines(img, [np.array(pts, np.int32)], False, color, 7, cv2.LINE_AA)

        if state == State.AWAY:
            for i, s in enumerate((0.8, 1.0, 1.3)):
                y = int(130 - i * 25 - 6 * math.sin(now * 2 + i))
                cv2.putText(img, "z", (470 + i * 22, y), cv2.FONT_HERSHEY_SIMPLEX, s, color, 2, cv2.LINE_AA)

        if state == State.COMPLETE:
            self._draw_confetti(img)

        self._draw_hud(img, remaining_s, progress, color, condition_label)
        if caption:
            self._draw_caption(img, caption)
        return img

    def _draw_confetti(self, img):
        moved = []
        for x, y, c in self._confetti:
            y = y + 6 if y < H else random.randint(-60, 0)
            cv2.rectangle(img, (x, y), (x + 6, y + 10), c, -1)
            moved.append((x, y, c))
        self._confetti = moved

    @staticmethod
    def _draw_hud(img, remaining_s, progress, color, label):
        m, s = divmod(int(math.ceil(remaining_s)), 60)
        cv2.putText(img, f"{m:02d}:{s:02d}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (230, 230, 230), 2, cv2.LINE_AA)
        cv2.rectangle(img, (140, 22), (620, 38), (90, 80, 70), -1)
        cv2.rectangle(img, (140, 22), (140 + int(480 * progress), 38), color, -1)
        if label:
            cv2.putText(img, label, (20, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)

    @staticmethod
    def _draw_caption(img, text):
        # OpenCV's Hershey fonts are ASCII-only; non-ASCII captions are skipped
        # (the line is still spoken aloud).
        if not text.isascii():
            return
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        x = max((W - tw) // 2, 10)
        cv2.rectangle(img, (x - 12, 420), (x + tw + 12, 420 + th + 20), (245, 245, 245), -1)
        cv2.putText(img, text, (x, 420 + th + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 40), 2, cv2.LINE_AA)
