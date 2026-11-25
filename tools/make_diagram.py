# AI-GENERATED CODE: written by Claude (Anthropic, Claude Opus 5.5) via Claude Code,
# October 2026. Requirements, design decisions and pilot testing by Group 10.
# See AI_DISCLOSURE.md for which parts came from the team.
r"""System pipeline diagram for slides (only method names as text, per the
course's slide rules). Writes media/system_diagram.png (1920x1080).

    .\.venv\Scripts\python tools\make_diagram.py
"""

import math
import sys
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from study_robot.face import RobotFace  # noqa: E402
from study_robot.state_machine import State  # noqa: E402

W, H = 1920, 1080
BG = (255, 255, 255)
INK = (40, 46, 56)
MUTED = (120, 128, 140)
LINE = (170, 178, 190)
ACCENT = (35, 120, 200)
CARD = (244, 246, 249)
STATE_COLOR = {  # matches face.py (converted BGR -> RGB)
    State.FOCUSED: (120, 220, 230),
    State.DISTRACTED: (255, 180, 80),
    State.AWAY: (140, 150, 170),
    State.COMPLETE: (120, 230, 120),
}
FONT_DIR = Path("C:/Windows/Fonts")


def font(size, bold=False):
    for name in (("seguisb.ttf", "segoeuib.ttf") if bold else ("segoeui.ttf",)) + ("arial.ttf",):
        p = FONT_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def face_thumb(state, width):
    f = RobotFace()
    for i in range(40):  # let the expression settle
        img = f.render(state, 1.0 + i * 0.05, 0, 0)
    head = cv2.cvtColor(img[70:400, 90:550], cv2.COLOR_BGR2RGB)
    h = int(head.shape[0] * width / head.shape[1])
    return Image.fromarray(cv2.resize(head, (width, h), interpolation=cv2.INTER_AREA))


def arrow(d, start, end, color=LINE, width=6, head=18):
    d.line([start, end], fill=color, width=width)
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    pts = [end,
           (end[0] - head * math.cos(ang - 0.45), end[1] - head * math.sin(ang - 0.45)),
           (end[0] - head * math.cos(ang + 0.45), end[1] - head * math.sin(ang + 0.45))]
    d.polygon(pts, fill=color)


def label(d, center_x, y, text, size=30, color=INK, bold=True):
    f = font(size, bold)
    w = d.textlength(text, font=f)
    d.text((center_x - w / 2, y), text, font=f, fill=color)


def card(d, box):
    d.rounded_rectangle(box, radius=28, fill=CARD, outline=(225, 229, 235), width=3)


def icon_camera(d, cx, cy):
    d.rounded_rectangle((cx - 70, cy - 48, cx + 70, cy + 48), radius=18, fill=INK)
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=(90, 100, 115))
    d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=(30, 34, 42))
    d.ellipse((cx + 40, cy - 38, cx + 54, cy - 24), fill=(230, 80, 80))
    d.rectangle((cx - 12, cy + 48, cx + 12, cy + 70), fill=INK)
    d.rounded_rectangle((cx - 45, cy + 68, cx + 45, cy + 80), radius=6, fill=INK)


def icon_face_mesh(d, cx, cy):
    # Oval of landmark dots with eyes/nose/mouth clusters.
    for i in range(36):
        a = 2 * math.pi * i / 36
        x, y = cx + 55 * math.cos(a), cy + 72 * math.sin(a)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=ACCENT)
    for ex in (-24, 24):
        for i in range(8):
            a = 2 * math.pi * i / 8
            x, y = cx + ex + 12 * math.cos(a), cy - 18 + 6 * math.sin(a)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=ACCENT)
    for i in range(4):
        d.ellipse((cx - 3, cy - 6 + i * 9, cx + 3, cy + i * 9), fill=ACCENT)
    for i in range(7):
        x = cx - 22 + i * 7.3
        y = cy + 38 + 5 * math.sin(math.pi * i / 6)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=ACCENT)


def icon_pose(d, cx, cy):
    j = {"head": (cx, cy - 52), "neck": (cx, cy - 22), "ls": (cx - 50, cy - 12), "rs": (cx + 50, cy - 12),
         "le": (cx - 64, cy + 34), "re": (cx + 64, cy + 34), "hip": (cx, cy + 62)}
    for a, b in (("neck", "ls"), ("neck", "rs"), ("ls", "le"), ("rs", "re"), ("neck", "hip")):
        d.line([j[a], j[b]], fill=ACCENT, width=6)
    d.ellipse((cx - 24, cy - 76, cx + 24, cy - 28), outline=ACCENT, width=6)
    for k in ("ls", "rs", "le", "re", "neck", "hip"):
        x, y = j[k]
        r = 11 if k in ("ls", "rs") else 7
        d.ellipse((x - r, y - r, x + r, y + r), fill=ACCENT if k not in ("ls", "rs") else (230, 80, 80))


def icon_speaker(d, cx, cy):
    d.polygon([(cx - 50, cy - 20), (cx - 25, cy - 20), (cx + 5, cy - 50), (cx + 5, cy + 50),
               (cx - 25, cy + 20), (cx - 50, cy + 20)], fill=INK)
    for r in (28, 50):
        d.arc((cx + 5 - r, cy - r, cx + 5 + r, cy + r), -45, 45, fill=INK, width=7)


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    label(d, W / 2, 60, "System Pipeline", size=60)

    # Column x-centres
    cam_x, det_x, fsm_x, out_x = 200, 600, 1150, 1690
    mid = 590

    # 1. Camera
    card(d, (cam_x - 130, mid - 150, cam_x + 130, mid + 150))
    icon_camera(d, cam_x, mid - 20)
    label(d, cam_x, mid + 80, "OpenCV")

    # 2. Detection (face + pose)
    face_y, pose_y = mid - 175, mid + 175
    for y in (face_y, pose_y):
        card(d, (det_x - 175, y - 140, det_x + 175, y + 140))
    icon_face_mesh(d, det_x, face_y - 30)
    label(d, det_x, face_y + 62, "MediaPipe", size=26, color=MUTED, bold=False)
    label(d, det_x, face_y + 92, "Face Landmarker", size=30)
    icon_pose(d, det_x, pose_y - 30)
    label(d, det_x, pose_y + 62, "MediaPipe", size=26, color=MUTED, bold=False)
    label(d, det_x, pose_y + 92, "Pose Landmarker", size=30)

    arrow(d, (cam_x + 135, mid - 20), (det_x - 185, face_y))
    arrow(d, (cam_x + 135, mid + 20), (det_x - 185, pose_y))

    # 3. Finite state machine with robot-face states
    box = (fsm_x - 300, mid - 330, fsm_x + 300, mid + 330)
    card(d, box)
    label(d, fsm_x, box[3] - 62, "Finite State Machine", size=30)
    thumb_w = 200
    pos = {
        State.FOCUSED: (fsm_x - 150, mid - 185),
        State.DISTRACTED: (fsm_x + 150, mid - 185),
        State.AWAY: (fsm_x - 150, mid + 90),
        State.COMPLETE: (fsm_x + 150, mid + 90),
    }
    for state, (x, y) in pos.items():
        t = face_thumb(state, thumb_w)
        d.rounded_rectangle((x - thumb_w / 2 - 8, y - t.height / 2 - 8,
                             x + thumb_w / 2 + 8, y + t.height / 2 + 8),
                            radius=16, outline=STATE_COLOR[state], width=6)
        img.paste(t, (int(x - thumb_w / 2), int(y - t.height / 2)))
    # Transitions: focused <-> distracted, focused <-> away, -> complete
    fx, fy = pos[State.FOCUSED]
    dx, dy = pos[State.DISTRACTED]
    ax, ay = pos[State.AWAY]
    cx, cy = pos[State.COMPLETE]
    arrow(d, (fx + 112, fy - 22), (dx - 112, dy - 22), color=STATE_COLOR[State.DISTRACTED], width=5, head=14)
    arrow(d, (dx - 112, dy + 22), (fx + 112, fy + 22), color=STATE_COLOR[State.FOCUSED], width=5, head=14)
    arrow(d, (fx - 22, fy + 82), (ax - 22, ay - 82), color=STATE_COLOR[State.AWAY], width=5, head=14)
    arrow(d, (ax + 22, ay - 82), (fx + 22, fy + 82), color=STATE_COLOR[State.FOCUSED], width=5, head=14)
    arrow(d, (fx + 108, fy + 80), (cx - 108, cy - 80), color=STATE_COLOR[State.COMPLETE], width=5, head=14)

    arrow(d, (det_x + 180, face_y), (box[0] - 10, mid - 40))
    arrow(d, (det_x + 180, pose_y), (box[0] - 10, mid + 40))

    # 4. Outputs: robot face + speech
    rf_y, sp_y = mid - 175, mid + 175
    for y in (rf_y, sp_y):
        card(d, (out_x - 165, y - 140, out_x + 165, y + 140))
    t = face_thumb(State.FOCUSED, 200)
    img.paste(t, (int(out_x - 100), int(rf_y - 30 - t.height / 2)))
    label(d, out_x, rf_y + 62, "OpenCV", size=26, color=MUTED, bold=False)
    label(d, out_x, rf_y + 92, "Animated Face", size=30)
    icon_speaker(d, out_x - 10, sp_y - 30)
    label(d, out_x, sp_y + 62, "Windows SAPI", size=26, color=MUTED, bold=False)
    label(d, out_x, sp_y + 92, "Text-to-Speech", size=30)

    arrow(d, (box[2] + 10, mid - 40), (out_x - 175, rf_y))
    arrow(d, (box[2] + 10, mid + 40), (out_x - 175, sp_y))

    out = Path("media/system_diagram.png")
    out.parent.mkdir(exist_ok=True)
    img.save(out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
