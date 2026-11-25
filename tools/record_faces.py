# AI-GENERATED CODE: written by Claude (Anthropic, Claude Opus 5.5) via Claude Code,
# October 2026. Requirements, design decisions and pilot testing by Group 10.
# See AI_DISCLOSURE.md for which parts came from the team.
r"""Render the robot face animations to video/GIF for presentation slides.

No camera needed. Writes to media/:
    face_<state>.mp4 / .gif   one clip per state, no caption (slide-friendly)
    face_<state>_head.*       same, cropped to the head only
    face_story.mp4 / .gif     focused -> distracted -> focused -> away ->
                              welcome back -> complete, with speech captions

Run from the repo root:
    .\.venv\Scripts\python tools\record_faces.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from study_robot.face import RobotFace  # noqa: E402
from study_robot.state_machine import State  # noqa: E402

FPS = 30
GIF_FPS = 15
GIF_WIDTH = 480
OUT = Path("media")

# (state, seconds, caption) segments for the story clip.
STORY = [
    (State.FOCUSED, 3.0, None),
    (State.DISTRACTED, 3.5, "Hey, let's get back to it."),
    (State.FOCUSED, 2.5, None),
    (State.AWAY, 3.5, None),
    (State.FOCUSED, 2.5, "Welcome back!"),
    (State.COMPLETE, 4.0, "Session complete! Great job today."),
]


def render(segments, session_s=600.0, elapsed_start=380.0):
    """Yield frames; the timer/progress bar advance like a real session."""
    face = RobotFace()
    # Settle the first expression so frame 0 (what a PDF export shows) is right.
    for i in range(40):
        face.render(segments[0][0], 0.05 * i, 0, 0)
    t = 0.0
    for state, seconds, caption in segments:
        for _ in range(int(seconds * FPS)):
            elapsed = session_s if state == State.COMPLETE else elapsed_start + t
            yield face.render(state, 1.0 + t, session_s - elapsed, elapsed / session_s, caption)
            t += 1 / FPS


def open_writer(path: Path, size):
    # H.264 plays everywhere (PowerPoint, Google Slides); fall back to MPEG-4.
    for fourcc in ("avc1", "mp4v"):
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*fourcc), FPS, size)
        if writer.isOpened():
            return writer, fourcc
    raise RuntimeError(f"cannot open video writer for {path}")


def save(name: str, frames):
    frames = list(frames)
    h, w = frames[0].shape[:2]
    writer, codec = open_writer(OUT / f"{name}.mp4", (w, h))
    for f in frames:
        writer.write(f)
    writer.release()

    step = FPS // GIF_FPS
    gif_h = int(h * GIF_WIDTH / w)
    imgs = [Image.fromarray(cv2.cvtColor(cv2.resize(f, (GIF_WIDTH, gif_h), interpolation=cv2.INTER_AREA),
                                         cv2.COLOR_BGR2RGB))
            for f in frames[::step]]
    imgs[0].save(OUT / f"{name}.gif", save_all=True, append_images=imgs[1:],
                 duration=int(1000 / GIF_FPS), loop=0, optimize=True)
    print(f"{name}: {len(frames) / FPS:.1f}s  mp4({codec})  gif")


def head_only(frames):
    """Crop to the robot head (no timer bar) for compact slide visuals."""
    return [f[70:400, 90:550] for f in frames]


def main():
    OUT.mkdir(exist_ok=True)
    for state in State:
        frames = list(render([(state, 4.0, None)]))
        save(f"face_{state.value}", frames)
        save(f"face_{state.value}_head", head_only(frames))
    save("face_story", render(STORY))


if __name__ == "__main__":
    main()
