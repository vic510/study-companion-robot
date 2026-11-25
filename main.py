# AI-GENERATED CODE: written by Claude (Anthropic, Claude Opus 5.5) via Claude Code,
# October 2026. Requirements, design decisions and pilot testing by Group 10.
# See AI_DISCLOSURE.md for which parts came from the team.
"""Adaptive Study Companion Robot — entry point.

Examples:
    python main.py --condition adaptive --minutes 10 --participant P01
    python main.py --condition fixed --minutes 10 --participant P01 --lang zh
    python main.py --debug          # also show the camera view with tracking info
    python main.py --targets screen # calibrate a single study target

Controls (buttons under the face, or keys):
    space  pause / resume (session timer freezes)
    c      recalibrate the studying pose
    q/Esc  stop early (the Stop button needs a second click to confirm)
"""

import argparse
import sys
import time
from pathlib import Path

import cv2

from study_robot.config import (CALIBRATION_MAX_RETRIES, CALIBRATION_PREP_SECONDS, CALIBRATION_SECONDS,
                                DEFAULT_TARGETS, MODEL_PATH, POSE_MODEL_PATH, Thresholds)
from study_robot.face import H as FACE_H, W as FACE_W, RobotFace
from study_robot.session_log import SessionLog
from study_robot.speech import Speaker, calibration_prompt
from study_robot.state_machine import AdaptiveCompanion, Event, FixedCompanion, State
from study_robot.ui import ControlBar, SessionClock
from study_robot.vision import AttentionEstimator, BodyDetector, Calibration, is_looking

WINDOW = "Study Companion"
CAPTION_SECONDS = 4.0


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--condition", choices=["adaptive", "fixed"], default="adaptive")
    p.add_argument("--minutes", type=float, default=10.0, help="study session length")
    p.add_argument("--participant", default="test")
    p.add_argument("--lang", choices=["en", "zh"], default="en")
    p.add_argument("--camera", type=int, default=0)
    p.add_argument("--model", default=MODEL_PATH)
    p.add_argument("--pose-model", default=POSE_MODEL_PATH)
    p.add_argument("--no-tts", action="store_true", help="disable spoken feedback")
    p.add_argument("--debug", action="store_true", help="show camera + tracking values")
    p.add_argument("--log-dir", default="logs")
    p.add_argument("--targets", default=DEFAULT_TARGETS,
                   help="comma-separated study targets to calibrate, e.g. 'screen,laptop' or 'notes'")
    args = p.parse_args()
    args.targets = [t.strip() for t in args.targets.split(",") if t.strip()] or ["study material"]
    return args


def draw_debug(frame, obs, body, looking, targets, baselines):
    color = (0, 200, 0) if looking else (0, 0, 255)
    if obs.landmarks:
        h, w = frame.shape[:2]
        for lm in obs.landmarks[::8]:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 1, color, -1)
    lines = [f"face: {obs.face_present}  body: {body}  looking: {looking}"]
    if obs.yaw_ratio is not None:
        lines.append(f"yaw {obs.yaw_ratio:.2f}  pitch {obs.pitch_ratio:.2f}")
    for t, (y, p) in zip(targets, baselines):
        lines.append(f"  {t}: yaw {y:.2f} pitch {p:.2f}")
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (10, 25 + i * 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    cv2.imshow("Camera (debug)", frame)


def window_closed() -> bool:
    try:
        return cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def _sample_target(cap, estimator, face, bar, t0, target, companion, clock):
    """Prep phase (user moves their gaze), then sample the head pose."""
    calib = Calibration()
    start = time.monotonic()
    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        now = time.monotonic()
        obs = estimator.observe(frame, int((now - t0) * 1000))
        if now - start < CALIBRATION_PREP_SECONDS:
            caption = f"Next: look at your {target.upper()}"
        else:
            calib.add(obs)
            caption = f"Calibrating: keep looking at your {target.upper()}"
            if now - start >= CALIBRATION_PREP_SECONDS + CALIBRATION_SECONDS and calib.ready:
                return calib.baseline()

        if companion:
            s_now = clock.now()
            remaining = companion.remaining(s_now)
            progress = companion.elapsed(s_now) / companion.session_s
        else:
            remaining = progress = 0
        img = face.render(State.FOCUSED, now, remaining, progress, caption=caption)
        cv2.imshow(WINDOW, bar.compose(img, paused=False, enabled=False))
        bar.pop_action()  # ignore clicks while calibrating
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27) or window_closed():
            return None
        if now - start > 20:  # face never found
            print(f"Calibration failed for '{target}': no face detected. Check camera/lighting.")
            return None


def _too_close(a, b, thresholds) -> bool:
    return (abs(a[0] - b[0]) <= thresholds.yaw_tolerance
            and abs(a[1] - b[1]) <= thresholds.pitch_tolerance)


def calibrate(cap, estimator, face, bar, t0, targets, speaker, thresholds,
              companion=None, clock=None):
    """Record the head pose for each study target (e.g. screen, laptop).

    Each target is announced by voice so the user does not have to keep
    reading the robot window (pilots: people kept looking at the window and
    both targets came out identical). A target that lands on top of an
    earlier one is retried.

    Returns one (yaw, pitch) baseline per target, or None if cancelled/failed.
    Also used mid-session (Recalibrate); the session timer keeps running.
    """
    baselines = []
    for target in targets:
        for attempt in range(CALIBRATION_MAX_RETRIES + 1):
            speaker.say_text(calibration_prompt(target, speaker.lang, retry=attempt > 0))
            baseline = _sample_target(cap, estimator, face, bar, t0, target, companion, clock)
            if baseline is None:
                return None
            clash = next((t for t, b in zip(targets, baselines)
                          if _too_close(baseline, b, thresholds)), None)
            if clash is None:
                break
            print(f"'{target}' looks the same as '{clash}' "
                  f"(attempt {attempt + 1}/{CALIBRATION_MAX_RETRIES + 1})")
        baselines.append(baseline)  # after max retries, accept: targets may truly overlap
    speaker.say_text(calibration_prompt(None, speaker.lang))
    return baselines


def format_baselines(targets, baselines) -> str:
    return "; ".join(f"{t}={y:.3f},{p:.3f}" for t, (y, p) in zip(targets, baselines))


def main():
    args = parse_args()
    if not Path(args.model).exists():
        sys.exit(f"Model not found at {args.model}. Run: python download_model.py")

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    if not cap.isOpened():
        sys.exit(f"Cannot open camera {args.camera}")

    thresholds = Thresholds()
    estimator = AttentionEstimator(args.model)
    if Path(args.pose_model).exists():
        body_detector = BodyDetector(args.pose_model)
    else:
        body_detector = None
        print(f"Warning: {args.pose_model} missing; head-down will count as Away. "
              "Run: python download_model.py")
    face = RobotFace()
    bar = ControlBar(FACE_W, FACE_H)
    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, bar.on_mouse)
    speaker = Speaker(args.lang, enabled=not args.no_tts)
    t0 = time.monotonic()

    baselines = calibrate(cap, estimator, face, bar, t0, args.targets, speaker, thresholds)
    if baselines is None:
        speaker.close()
        cap.release()
        cv2.destroyAllWindows()
        return

    log = SessionLog(args.log_dir, args.participant, args.condition)
    clock = SessionClock()
    start = clock.now()
    session_s = args.minutes * 60
    if args.condition == "adaptive":
        companion = AdaptiveCompanion(session_s, start, thresholds)
    else:
        companion = FixedCompanion(session_s, start)
    log.write(0, "calibration", format_baselines(args.targets, baselines), "target=yaw,pitch")

    caption, caption_until = None, 0.0
    event_counts: dict[str, int] = {}
    looking_frames = face_frames = present_frames = total_frames = 0
    next_sample = start
    complete_at = None
    paused_seconds = 0.0
    pause_started = 0.0

    try:
        while True:
            ok, frame = cap.read()
            real_now = time.monotonic()
            if not ok:
                continue
            now = clock.now()  # session time; frozen while paused
            elapsed = companion.elapsed(now)
            ts_ms = int((real_now - t0) * 1000)
            obs = estimator.observe(frame, ts_ms)
            looking = is_looking(obs, baselines, thresholds.yaw_tolerance, thresholds.pitch_tolerance)
            # Face lost: check the body before assuming the user left
            # (head down over a phone hides the face but not the shoulders).
            body = bool(not obs.face_present and body_detector
                        and body_detector.body_present(frame, ts_ms))
            present = obs.face_present or body

            if not clock.paused:
                prev_state = companion.state
                events = companion.update(now, present, looking)

                # Objective attention measure, recorded in both conditions.
                if companion.state != State.COMPLETE:
                    total_frames += 1
                    face_frames += obs.face_present
                    present_frames += present
                    looking_frames += looking
                if now >= next_sample:
                    next_sample += 1.0
                    detail = f"face={int(obs.face_present)} body={int(body)}"
                    if obs.yaw_ratio is not None:
                        detail += f" yaw={obs.yaw_ratio:.3f} pitch={obs.pitch_ratio:.3f}"
                    log.write(elapsed, "sample", int(looking), detail)

                if companion.state != prev_state:
                    log.write(elapsed, "state", companion.state.value, prev_state.value)
                for ev in events:
                    event_counts[ev.value] = event_counts.get(ev.value, 0) + 1
                    text = speaker.say_event(ev)
                    log.write(elapsed, "event", ev.value, text or "")
                    if text:
                        caption, caption_until = text, real_now + CAPTION_SECONDS
                    if ev == Event.COMPLETE:
                        complete_at = real_now

            img = face.render(companion.state, real_now, companion.remaining(now),
                              elapsed / session_s,
                              caption if real_now < caption_until else None,
                              f"{args.participant} / {args.condition}")
            done = companion.state == State.COMPLETE
            cv2.imshow(WINDOW, bar.compose(img, clock.paused, enabled=not done))
            if args.debug:
                draw_debug(frame, obs, body, looking, args.targets, baselines)

            key = cv2.waitKey(1) & 0xFF
            action = bar.pop_action()
            if key == ord(" "):
                action = "pause"
            elif key == ord("c"):
                action = "recalibrate"
            elif key in (ord("q"), 27):
                action = "stop"

            if action == "stop" or window_closed():
                if clock.paused:
                    paused_seconds += real_now - pause_started
                log.write(elapsed, "event", "stopped_early", "experimenter stop")
                break
            if action == "pause" and not done:
                if clock.paused:
                    clock.resume()
                    paused_seconds += time.monotonic() - pause_started
                    log.write(elapsed, "event", "resume", "")
                else:
                    clock.pause()
                    pause_started = time.monotonic()
                    log.write(elapsed, "event", "pause", "")
            if action == "recalibrate" and not done:
                new_baselines = calibrate(cap, estimator, face, bar, t0, args.targets,
                                          speaker, thresholds, companion, clock)
                if new_baselines is not None:
                    baselines = new_baselines
                    log.write(companion.elapsed(clock.now()), "calibration",
                              format_baselines(args.targets, baselines), "recalibrated")
            if complete_at and real_now - complete_at > 8:
                break
    finally:
        total = max(total_frames, 1)
        log.summary({
            "planned_minutes": args.minutes,
            "completed": complete_at is not None,
            "studied_seconds": round(companion.elapsed(clock.now()), 1),
            "paused_seconds": round(paused_seconds, 1),
            "seconds_in_state": {s.value: round(v, 1) for s, v in companion.time_in_state.items()},
            "event_counts": event_counts,
            "face_present_ratio": round(face_frames / total, 3),
            "present_ratio": round(present_frames / total, 3),  # face or body
            "looking_ratio": round(looking_frames / total, 3),
            "baselines": {t: {"yaw": round(y, 3), "pitch": round(p, 3)}
                          for t, (y, p) in zip(args.targets, baselines)},
            "yaw_tolerance": thresholds.yaw_tolerance,
            "pitch_tolerance": thresholds.pitch_tolerance,
        })
        log.close()
        speaker.close()
        estimator.close()
        if body_detector:
            body_detector.close()
        cap.release()
        cv2.destroyAllWindows()
        print(f"Logs saved: {log.csv_path}")


if __name__ == "__main__":
    main()
