"""Interaction logic: turns per-frame observations into robot states and events.

Both companions expose the same interface so main.py can swap them for the
two user-study conditions:
    events = companion.update(now, present, looking)
`present` means someone is at the desk (face or body visible); `looking` means
the head points at a study target (always False when the face is not visible).
Time is passed in explicitly so the logic is deterministic and testable.
"""

from enum import Enum
from typing import Optional

from .config import FixedSchedule, Thresholds


class State(str, Enum):
    FOCUSED = "focused"
    DISTRACTED = "distracted"
    AWAY = "away"
    COMPLETE = "complete"


class Event(str, Enum):
    START = "start"
    DISTRACTED = "distracted"
    REMINDER = "reminder"
    SUGGEST_BREAK = "suggest_break"
    REFOCUSED = "refocused"
    AWAY = "away"
    WELCOME_BACK = "welcome_back"
    ENCOURAGE = "encourage"
    COMPLETE = "complete"


class _Companion:
    def __init__(self, session_s: float, start: float):
        self.session_s = session_s
        self.start = start
        self.state = State.FOCUSED
        self.time_in_state = {s: 0.0 for s in State}
        self._last_now = start
        self._started = False

    def elapsed(self, now: float) -> float:
        return min(now - self.start, self.session_s)

    def remaining(self, now: float) -> float:
        return max(self.session_s - (now - self.start), 0.0)

    def _tick(self, now: float) -> list[Event]:
        """Shared bookkeeping; returns START/COMPLETE events if due."""
        self.time_in_state[self.state] += now - self._last_now
        self._last_now = now
        events = []
        if not self._started:
            self._started = True
            events.append(Event.START)
        if self.state != State.COMPLETE and now - self.start >= self.session_s:
            self.state = State.COMPLETE
            events.append(Event.COMPLETE)
        return events


class AdaptiveCompanion(_Companion):
    """Experimental condition: reacts to the user's attention."""

    def __init__(self, session_s: float, start: float,
                 thresholds: Optional[Thresholds] = None):
        super().__init__(session_s, start)
        self.t = thresholds or Thresholds()
        self._absent_since: Optional[float] = None
        self._look_away_since: Optional[float] = None
        self._look_back_since: Optional[float] = None
        self._last_reminder = 0.0
        self._break_suggested = False

    def update(self, now: float, present: bool, looking: bool) -> list[Event]:
        events = self._tick(now)
        if self.state == State.COMPLETE:
            return events

        if not present:
            self._look_back_since = None
            if self._absent_since is None:
                self._absent_since = now
            if (self.state != State.AWAY
                    and now - self._absent_since >= self.t.away_after_s):
                self.state = State.AWAY
                events.append(Event.AWAY)
            return events

        self._absent_since = None
        if self.state == State.AWAY:
            self.state = State.FOCUSED
            self._look_away_since = None
            events.append(Event.WELCOME_BACK)
            return events

        if looking:
            # Only a sustained look back counts; flickering detections near a
            # tolerance edge must not keep resetting the look-away timer.
            if self._look_back_since is None:
                self._look_back_since = now
            if now - self._look_back_since >= self.t.refocus_after_s:
                self._look_away_since = None
                if self.state == State.DISTRACTED:
                    self.state = State.FOCUSED
                    events.append(Event.REFOCUSED)
            return events

        # Present but looking away (or face hidden, e.g. head down).
        self._look_back_since = None
        if self._look_away_since is None:
            self._look_away_since = now
        away_for = now - self._look_away_since

        if self.state == State.FOCUSED and away_for >= self.t.distracted_after_s:
            self.state = State.DISTRACTED
            self._last_reminder = now
            self._break_suggested = False
            events.append(Event.DISTRACTED)
        elif self.state == State.DISTRACTED:
            if (not self._break_suggested
                    and away_for >= self.t.suggest_break_after_s):
                self._break_suggested = True
                self._last_reminder = now
                events.append(Event.SUGGEST_BREAK)
            elif now - self._last_reminder >= self.t.reminder_interval_s:
                self._last_reminder = now
                events.append(Event.REMINDER)
        return events


class FixedCompanion(_Companion):
    """Control condition: fixed-schedule feedback, ignores the user's attention."""

    def __init__(self, session_s: float, start: float,
                 schedule: Optional[FixedSchedule] = None):
        super().__init__(session_s, start)
        self.schedule = schedule or FixedSchedule()
        self._next_encourage = start + self.schedule.encourage_every_s

    def update(self, now: float, present: bool, looking: bool) -> list[Event]:
        events = self._tick(now)
        if self.state == State.COMPLETE:
            return events
        if now >= self._next_encourage:
            self._next_encourage += self.schedule.encourage_every_s
            events.append(Event.ENCOURAGE)
        return events
