"""Experimenter control bar (Pause / Recalibrate / Stop) under the robot face."""

import time

import cv2
import numpy as np

BAR_H = 64
STOP_CONFIRM_S = 3.0


class SessionClock:
    """Monotonic clock that stops while paused, so the session timer freezes."""

    def __init__(self):
        self._paused_total = 0.0
        self._paused_at: float | None = None

    @property
    def paused(self) -> bool:
        return self._paused_at is not None

    def now(self) -> float:
        real = self._paused_at if self.paused else time.monotonic()
        return real - self._paused_total

    def pause(self):
        if not self.paused:
            self._paused_at = time.monotonic()

    def resume(self):
        if self.paused:
            self._paused_total += time.monotonic() - self._paused_at
            self._paused_at = None


class ControlBar:
    def __init__(self, width: int, face_height: int):
        self.width = width
        self.face_height = face_height
        self._pending: str | None = None
        self._stop_armed_until = 0.0
        w = (width - 40) // 3
        self._buttons = {
            "pause": (10, w),
            "recalibrate": (20 + w, w),
            "stop": (30 + 2 * w, w),
        }

    def on_mouse(self, event, x, y, flags, param):
        if event != cv2.EVENT_LBUTTONDOWN or y < self.face_height:
            return
        for name, (bx, bw) in self._buttons.items():
            if bx <= x <= bx + bw:
                self._pending = name

    def pop_action(self) -> str | None:
        """Returns 'pause', 'recalibrate' or 'stop'. Stop needs two clicks."""
        action, self._pending = self._pending, None
        if action == "stop":
            now = time.monotonic()
            if now < self._stop_armed_until:
                return "stop"
            self._stop_armed_until = now + STOP_CONFIRM_S
            return None
        return action

    def compose(self, face_img: np.ndarray, paused: bool, enabled: bool = True) -> np.ndarray:
        if paused:
            face_img = (face_img * 0.45).astype(np.uint8)
            text = "PAUSED"
            (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.6, 4)
            cv2.putText(face_img, text, ((self.width - tw) // 2, self.face_height // 2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.6, (240, 240, 240), 4, cv2.LINE_AA)

        bar = np.full((BAR_H, self.width, 3), (30, 24, 20), np.uint8)
        stop_armed = time.monotonic() < self._stop_armed_until
        labels = {
            "pause": ("Resume [space]" if paused else "Pause [space]", (90, 160, 90)),
            "recalibrate": ("Recalibrate [c]", (150, 120, 70)),
            "stop": ("Click again to stop" if stop_armed else "Stop [q]",
                     (60, 60, 220) if stop_armed else (70, 70, 150)),
        }
        for name, (bx, bw) in self._buttons.items():
            label, color = labels[name]
            if not enabled:
                color = (70, 70, 70)
            cv2.rectangle(bar, (bx, 10), (bx + bw, BAR_H - 10), color, -1, cv2.LINE_AA)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.putText(bar, label, (bx + (bw - tw) // 2, (BAR_H + th) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (245, 245, 245), 1, cv2.LINE_AA)
        return np.vstack([face_img, bar])
