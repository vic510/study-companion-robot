r"""Images for the intermediate presentation deck -> media/slides/.

Uses the pilot-test logs in logs/ (real data, kept off GitHub).

    .\.venv\Scripts\python tools\make_slide_assets.py
"""

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("media/slides")
EMOJI_FONT = "C:/Windows/Fonts/seguiemj.ttf"
EMOJI = {
    "student": "🎓", "books": "📚", "phone": "📱", "timer": "⏱", "eyes": "👀",
    "walk": "🚶", "finish": "🏁", "desktop": "🖥", "laptop": "💻", "clipboard": "📋",
    "cross": "❌", "check": "✅", "person": "👤", "speech": "💬", "robot": "🤖",
}
# Robot-face state colours (RGB), same as study_robot/face.py.
STATE_RGB = {"focused": (120, 220, 230), "distracted": (255, 180, 80),
             "away": (140, 150, 170), "complete": (120, 230, 120)}


def emoji_icons():
    font = ImageFont.truetype(EMOJI_FONT, 109)
    for name, ch in EMOJI.items():
        img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        box = d.textbbox((0, 0), ch, font=font, embedded_color=True)
        w, h = box[2] - box[0], box[3] - box[1]
        d.text(((160 - w) / 2 - box[0], (160 - h) / 2 - box[1]), ch, font=font, embedded_color=True)
        img.save(OUT / f"icon_{name}.png")


def diagram_without_title():
    img = Image.open("media/system_diagram.png")
    img.crop((0, 230, img.width, 950)).save(OUT / "system_diagram_notitle.png")


def state_timeline(log_path: Path, seconds: int):
    """Per-second robot state reconstructed from the state-change rows."""
    changes = []
    with open(log_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["kind"] == "state":
                changes.append((float(row["elapsed_s"]), row["value"]))
    states, current, i = [], "focused", 0
    for t in range(seconds):
        while i < len(changes) and changes[i][0] <= t:
            current = changes[i][1]
            i += 1
        states.append(current)
    return states


def timeline_strip(states, path: Path, width=1600, height=90):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    n = len(states)
    for t, s in enumerate(states):
        x0, x1 = round(t * width / n), round((t + 1) * width / n)
        d.rectangle((x0, 0, x1, height), fill=STATE_RGB.get(s, STATE_RGB["focused"]))
    # rounded mask
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=height // 3, fill=255)
    img.putalpha(mask)
    img.save(path)


def latest(pattern):
    files = sorted(Path("logs").glob(pattern))
    return files[-1] if files else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    emoji_icons()
    diagram_without_title()
    # Pilot 3 (before fix: head down -> "away") vs pilot 6 (after: -> "distracted").
    before = latest("distract-test_adaptive_*.csv")
    after = latest("distract-test2_adaptive_*.csv")
    if before and after:
        timeline_strip(state_timeline(before, 120), OUT / "timeline_before.png")
        timeline_strip(state_timeline(after, 120), OUT / "timeline_after.png")
    else:
        print("pilot logs missing; skipped timelines")
    print(f"assets written to {OUT}")


if __name__ == "__main__":
    main()
