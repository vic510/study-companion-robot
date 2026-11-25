r"""Build the intermediate presentation deck -> slides/intermediate_presentation.pptx

Course rule: no words on slides except titles and method names, so content is
images, GIFs, icons and pilot data.

Run tools\make_slide_assets.py first.
    .\.venv\Scripts\python tools\make_deck.py
"""

import collections
import csv
import re
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

A = Path("media/slides")
M = Path("media")
OUT = Path("slides/intermediate_presentation.pptx")

BG = RGBColor(0x1E, 0x25, 0x30)
CARD = RGBColor(0x2A, 0x33, 0x40)
TEXT = RGBColor(0xF2, 0xF5, 0xF8)
MUTED = RGBColor(0x9A, 0xA6, 0xB5)
CYAN = RGBColor(0x78, 0xDC, 0xE6)
ORANGE = RGBColor(0xFF, 0xB4, 0x50)
GREY = RGBColor(0x8C, 0x96, 0xAA)
GREEN = RGBColor(0x78, 0xE6, 0x78)
LIGHT = RGBColor(0xD5, 0xDC, 0xE5)
FONT = "Calibri"


# ---------- helpers ----------

def new_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    return s


def text(slide, s, x, y, w, h, size, color=TEXT, bold=False, align=PP_ALIGN.LEFT, name=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = s
    r.font.size, r.font.bold, r.font.name = Pt(size), bold, FONT
    r.font.color.rgb = color
    return tb


def title(slide, s):
    text(slide, s, 0.6, 0.45, 12.1, 0.8, 38, bold=True, name="Title")


def card(slide, x, y, w, h, color=CARD, border=None, name=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = 0.08
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if border is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = border
        shp.line.width = Pt(4)
    shp.shadow.inherit = False
    if name:
        shp.name = name
    return shp


def picture(slide, path, x, y, w=None, h=None, name=None):
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y),
                                   Inches(w) if w else None, Inches(h) if h else None)
    if name:
        pic.name = name
    return pic


def icon(slide, name, x, y, size, circle=None):
    """Emoji icon, optionally on a coloured circle (deck motif)."""
    if circle is not None:
        c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(size), Inches(size))
        c.fill.solid()
        c.fill.fore_color.rgb = circle
        c.line.fill.background()
        c.shadow.inherit = False
        pad = size * 0.2
        return picture(slide, A / f"icon_{name}.png", x + pad, y + pad, w=size - 2 * pad, name=f"icon_{name}")
    return picture(slide, A / f"icon_{name}.png", x, y, w=size, name=f"icon_{name}")


def arrow(slide, x, y, w, h=0.5, color=MUTED):
    a = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    a.fill.solid()
    a.fill.fore_color.rgb = color
    a.line.fill.background()
    a.shadow.inherit = False
    return a



# ---------- slides ----------

def slide_title(prs):
    s = new_slide(prs)
    text(s, "Adaptive Study Companion Robot", 0.8, 2.3, 6.4, 2.0, 46, bold=True, name="Title")
    text(s, "Group 10", 0.8, 4.45, 6.0, 0.6, 24, color=MUTED)
    card(s, 7.3, 1.85, 5.4, 3.95, color=CARD)
    picture(s, M / "face_focused_head.gif", 7.55, 2.1, w=4.9, name="robot_face")


def slide_users(prs):
    s = new_slide(prs)
    title(s, "User-Centered Design")
    # Photo: Sanket Mishra on Unsplash (Unsplash License), cropped to the card.
    photo = A / "student_distracted.jpg"
    if photo.exists():
        pic = picture(s, photo, 0.6, 1.55, w=6.0, h=5.3, name="photo_student")
        pic.crop_left, pic.crop_right = 0.25, 0.05
        pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
    else:
        card(s, 0.6, 1.55, 6.0, 5.3, color=CARD, name="PHOTO_student_studying_alone")
        icon(s, "person", 2.75, 3.35, 1.7, circle=LIGHT)
    # Right: three need rows (icons only)
    rows = [("student", "person", CYAN), ("phone", "eyes", ORANGE), ("timer", "cross", GREY)]
    y = 1.65
    for left, right, col in rows:
        card(s, 7.1, y, 5.6, 1.55)
        icon(s, left, 7.45, y + 0.22, 1.1, circle=col)
        arrow(s, 8.85, y + 0.55, 0.9, 0.45)
        icon(s, right, 10.05, y + 0.22, 1.1, circle=col)
        y += 1.8


def slide_states(prs):
    s = new_slide(prs)
    title(s, "Interaction Design")
    items = [("face_focused_head.gif", CYAN, "eyes"), ("face_distracted_head.gif", ORANGE, "phone"),
             ("face_away_head.gif", GREY, "walk"), ("face_complete_head.gif", GREEN, "finish")]
    x = 0.6
    for gif, col, ic in items:
        card(s, x, 2.0, 2.85, 2.13, border=col)
        picture(s, M / gif, x + 0.15, 2.15, w=2.55)
        icon(s, ic, x + 0.8, 4.55, 1.25, circle=CARD)
        x += 3.1


def slide_pipeline(prs):
    s = new_slide(prs)
    title(s, "System Pipeline")
    picture(s, A / "system_diagram_notitle.png", 0.6, 1.75, w=12.1, name="pipeline_diagram")


def yaw_counts():
    files = sorted(Path("logs").glob("gaze-test_adaptive_*.csv"))
    if not files:
        return None
    ys = []
    with open(files[-1], encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m = re.search(r"yaw=([\d.-]+)", row["detail"]) if row["kind"] == "sample" else None
            if m:
                ys.append(float(m[1]))
    bins = [round(0.25 + 0.05 * i, 2) for i in range(25)]  # 0.25 .. 1.45
    c = collections.Counter(min(max(round(int(y / 0.05) * 0.05, 2), bins[0]), bins[-1]) for y in ys)
    return bins, [c.get(b, 0) for b in bins]


def slide_calibration(prs):
    s = new_slide(prs)
    title(s, "Multi-Target Calibration")
    # Left: the two study targets
    card(s, 0.6, 1.55, 3.4, 5.3)
    icon(s, "desktop", 1.45, 1.95, 1.7, circle=CYAN)
    icon(s, "laptop", 1.45, 4.55, 1.7, circle=CYAN)
    # Right: histogram of head yaw from pilot test 2
    data = yaw_counts()
    card(s, 4.35, 1.55, 8.35, 5.3)
    if data:
        bins, counts = data
        cd = CategoryChartData()
        cd.categories = [f"{b:.2f}" for b in bins]
        cd.add_series("head yaw", counts)
        gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(4.6), Inches(2.45),
                                Inches(7.85), Inches(4.2), cd)
        gf.name = "yaw_histogram"
        ch = gf.chart
        ch.has_legend = False
        ch.has_title = False
        plot = ch.plots[0]
        plot.gap_width = 25
        ser = plot.series[0]
        for i, b in enumerate(bins):
            pt = ser.points[i]
            pt.format.fill.solid()
            in_band = abs(b - 0.449) <= 0.18 or abs(b - 0.928) <= 0.18
            pt.format.fill.fore_color.rgb = CYAN if in_band else GREY
        for ax in (ch.category_axis, ch.value_axis):
            ax.tick_labels.font.size = Pt(12)
            ax.tick_labels.font.color.rgb = MUTED
            ax.tick_labels.font.name = FONT
            ax.format.line.color.rgb = GREY
        ch.value_axis.has_major_gridlines = False
        ch.category_axis.tick_labels.font.size = Pt(10)
        # Icons above the two peaks (laptop ~0.45, screen ~0.90)
        plot_x0, plot_w = 4.6 + 0.55, 7.85 - 0.75
        for name, b in (("laptop", 0.45), ("desktop", 0.90)):
            idx = bins.index(b)
            cx = plot_x0 + plot_w * (idx + 0.5) / len(bins)
            icon(s, name, cx - 0.35, 1.75, 0.7)


def slide_pilot(prs):
    s = new_slide(prs)
    title(s, "Pilot Testing")
    rows = [("cross", "timeline_before.png"), ("check", "timeline_after.png")]
    y = 1.6
    for ic, strip in rows:
        card(s, 0.6, y, 12.1, 1.75)
        icon(s, ic, 0.95, y + 0.37, 1.0)
        if (A / strip).exists():
            picture(s, A / strip, 2.3, y + 0.62, w=10.0, h=0.6, name=strip)
        icon(s, "phone", 2.3 + 10.0 * 10 / 120 - 0.25, y + 0.07, 0.5)
        y += 2.1
    # Colour legend: robot faces framed in their state colour
    x = 3.15
    for gif, col in (("face_focused_head.gif", CYAN), ("face_distracted_head.gif", ORANGE),
                     ("face_away_head.gif", GREY)):
        card(s, x, 5.95, 1.6, 1.15, border=col)
        picture(s, M / gif, x + 0.1, 6.0, w=1.4)
        x += 2.55


def slide_demo(prs):
    s = new_slide(prs)
    title(s, "Live Demo")
    card(s, 3.15, 1.55, 7.0, 5.3)
    picture(s, M / "face_story.gif", 3.4, 1.75, w=6.5, name="demo_story")


def slide_next(prs):
    s = new_slide(prs)
    title(s, "Next Step: User Study")
    # A: adaptive  vs  B: fixed
    card(s, 0.6, 1.55, 5.6, 3.3, border=ORANGE)
    picture(s, M / "face_distracted_head.gif", 0.9, 2.02, w=3.3)
    icon(s, "eyes", 4.55, 1.95, 1.2, circle=CARD)
    icon(s, "speech", 4.6, 3.35, 1.1)
    card(s, 7.1, 1.55, 5.6, 3.3, border=GREY)
    picture(s, M / "face_focused_head.gif", 7.4, 2.02, w=3.3)
    icon(s, "timer", 11.05, 2.6, 1.2, circle=CARD)
    # Bottom: participants -> both conditions -> questionnaire
    card(s, 0.6, 5.15, 12.1, 1.7)
    for i in range(4):
        icon(s, "person", 0.95 + i * 0.82, 5.6, 0.75, circle=LIGHT)
    arrow(s, 4.35, 5.75, 1.0)
    text(s, "Within-Subjects Design", 5.55, 5.72, 3.6, 0.6, 22, bold=True)
    arrow(s, 9.15, 5.75, 1.0)
    icon(s, "clipboard", 10.5, 5.4, 1.0)
    text(s, "Likert", 11.55, 5.72, 1.1, 0.6, 22, bold=True)


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    for build in (slide_title, slide_users, slide_states, slide_pipeline,
                  slide_calibration, slide_pilot, slide_demo, slide_next):
        build(prs)
    OUT.parent.mkdir(exist_ok=True)
    prs.save(OUT)
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
