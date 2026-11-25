# AI-GENERATED CODE: written by Claude (Anthropic, Claude Opus 5.5) via Claude Code,
# October 2026. Requirements, design decisions and pilot testing by Group 10.
# See AI_DISCLOSURE.md for which parts came from the team.
import unittest

from study_robot.config import FixedSchedule, Thresholds
from study_robot.state_machine import AdaptiveCompanion, Event, FixedCompanion, State

T = Thresholds(distracted_after_s=8, away_after_s=3, refocus_after_s=1,
               reminder_interval_s=30, suggest_break_after_s=60)


def run(companion, start, end, face=True, looking=True, step=0.5):
    """Feed constant observations from start to end; collect events."""
    events, t = [], start
    while t <= end + 1e-9:
        events += companion.update(t, face, looking)
        t += step
    return events


class AdaptiveTests(unittest.TestCase):
    def setUp(self):
        self.c = AdaptiveCompanion(session_s=600, start=0, thresholds=T)

    def test_start_event_and_stays_focused(self):
        events = run(self.c, 0, 20)
        self.assertEqual(events, [Event.START])
        self.assertEqual(self.c.state, State.FOCUSED)

    def test_short_glance_does_not_trigger(self):
        run(self.c, 0, 5)
        run(self.c, 5.5, 10, looking=False)  # 4.5 s away < 8 s
        run(self.c, 10.5, 15)
        self.assertEqual(self.c.state, State.FOCUSED)

    def test_distracted_then_refocus(self):
        run(self.c, 0, 5)
        events = run(self.c, 5.5, 14, looking=False)
        self.assertIn(Event.DISTRACTED, events)
        self.assertEqual(self.c.state, State.DISTRACTED)
        events = run(self.c, 14.5, 16)
        self.assertIn(Event.REFOCUSED, events)
        self.assertEqual(self.c.state, State.FOCUSED)

    def test_reminder_then_break_suggestion(self):
        run(self.c, 0, 1)
        events = run(self.c, 1.5, 80, looking=False)
        self.assertEqual(events.count(Event.DISTRACTED), 1)
        self.assertEqual(events.count(Event.REMINDER), 1)   # at ~39.5 s
        self.assertEqual(events.count(Event.SUGGEST_BREAK), 1)  # at ~61.5 s

    def test_flickering_glances_back_do_not_reset_timer(self):
        # Pilot 3: yaw hovering at the tolerance edge produced L/x flicker
        # that kept resetting the timer, so the reminder never fired.
        run(self.c, 0, 1)
        events, t = [], 1.5
        while t <= 20:
            looking = int(t * 2) % 4 == 0  # one 0.5 s "looking" blip every 2 s
            events += self.c.update(t, True, looking)
            t += 0.5
        self.assertIn(Event.DISTRACTED, events)

    def test_head_down_with_body_present_is_distraction_not_away(self):
        # Pilot 3: looking down at a phone hid the face; the body is still
        # there, so main.py passes present=True, looking=False.
        run(self.c, 0, 1)
        events = run(self.c, 1.5, 12, face=True, looking=False)
        self.assertIn(Event.DISTRACTED, events)
        self.assertNotIn(Event.AWAY, events)

    def test_away_and_welcome_back(self):
        run(self.c, 0, 1)
        events = run(self.c, 1.5, 6, face=False)
        self.assertIn(Event.AWAY, events)
        self.assertEqual(self.c.state, State.AWAY)
        events = run(self.c, 6.5, 7)
        self.assertIn(Event.WELCOME_BACK, events)
        self.assertEqual(self.c.state, State.FOCUSED)

    def test_complete(self):
        events = run(self.c, 0, 600, step=5)
        self.assertEqual(events[-1], Event.COMPLETE)
        self.assertEqual(self.c.state, State.COMPLETE)
        self.assertEqual(run(self.c, 605, 620, looking=False), [])


class FixedTests(unittest.TestCase):
    def test_encourages_on_schedule_regardless_of_attention(self):
        c = FixedCompanion(session_s=600, start=0, schedule=FixedSchedule(encourage_every_s=120))
        events = run(c, 0, 600, looking=False, step=1)
        self.assertEqual(events.count(Event.ENCOURAGE), 4)  # 120, 240, 360, 480
        self.assertNotIn(Event.DISTRACTED, events)
        self.assertEqual(events[-1], Event.COMPLETE)


if __name__ == "__main__":
    unittest.main()
