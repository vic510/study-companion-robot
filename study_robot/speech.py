"""Verbal feedback via offline text-to-speech (SAPI on Windows, pyttsx3 elsewhere)."""

import queue
import random
import sys
import threading

from .state_machine import Event

ZH_VOICE_KEYWORDS = ("chinese", "zh-tw", "zh-cn", "hanhan", "yating", "huihui")

PHRASES = {
    "en": {
        Event.START: ["Let's start studying. I'm right here with you."],
        Event.DISTRACTED: ["Hey, let's get back to it.",
                           "Still with me? Let's keep going."],
        Event.REMINDER: ["Just a gentle reminder to refocus.",
                         "You can do it. Back to your notes?"],
        Event.SUGGEST_BREAK: ["You seem tired. How about a short break?"],
        Event.REFOCUSED: [],  # stay quiet; the face smiles instead
        Event.AWAY: [],
        Event.WELCOME_BACK: ["Welcome back!"],
        Event.ENCOURAGE: ["Keep going, you're doing great."],
        Event.COMPLETE: ["Session complete! Great job today."],
    },
    "zh": {
        Event.START: ["我們開始讀書吧，我會陪著你。"],
        Event.DISTRACTED: ["嘿，我們回來繼續吧。", "還在嗎？一起加油。"],
        Event.REMINDER: ["溫馨提醒，回到書本上吧。", "你可以的，繼續加油。"],
        Event.SUGGEST_BREAK: ["你好像有點累了，要不要休息一下？"],
        Event.REFOCUSED: [],
        Event.AWAY: [],
        Event.WELCOME_BACK: ["歡迎回來！"],
        Event.ENCOURAGE: ["繼續加油，你做得很好。"],
        Event.COMPLETE: ["讀書時間結束！今天辛苦了。"],
    },
}


ZH_TARGET_NAMES = {"screen": "螢幕", "laptop": "筆電", "notes": "筆記", "book": "書本",
                   "monitor": "螢幕", "tablet": "平板", "study material": "書本"}


def calibration_prompt(target: str | None, lang: str, retry: bool = False) -> str:
    """Spoken calibration instruction; target=None means calibration is done."""
    if lang == "zh":
        if target is None:
            return "校正完成。"
        name = ZH_TARGET_NAMES.get(target.lower(), target)
        return f"跟剛才的位置太像了，請再看一次你的{name}。" if retry else f"請看著你的{name}。"
    if target is None:
        return "Calibration done."
    if retry:
        return f"That looked the same as before. Please look at your {target} again."
    return f"Please look at your {target}."


def phrase_for(event: Event, lang: str) -> str | None:
    options = PHRASES.get(lang, PHRASES["en"]).get(event, [])
    return random.choice(options) if options else None


class Speaker:
    """Speaks on a background thread so the camera loop never blocks."""

    def __init__(self, lang: str = "en", enabled: bool = True):
        self.lang = lang
        self.enabled = enabled
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        if enabled:
            self._thread.start()

    def say_event(self, event: Event) -> str | None:
        text = phrase_for(event, self.lang)
        if text:
            self.say_text(text)
        return text

    def say_text(self, text: str):
        if not self.enabled:
            return
        # Drop stale lines so feedback stays relevant to the current state.
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._queue.put(text)

    def _run(self):
        if sys.platform == "win32":
            self._run_sapi()
        else:
            self._run_pyttsx3()

    def _run_sapi(self):
        # pyttsx3 on Windows speaks only the first utterance: later
        # runAndWait() calls return immediately in silence. Calling SAPI
        # directly is reliable.
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        keywords = ZH_VOICE_KEYWORDS if self.lang == "zh" else ("english",)
        voices = voice.GetVoices()
        for i in range(voices.Count):
            if any(k in voices.Item(i).GetDescription().lower() for k in keywords):
                voice.Voice = voices.Item(i)
                break
        while True:
            text = self._queue.get()
            if text is None:
                break
            voice.Speak(text)

    def _run_pyttsx3(self):
        import pyttsx3

        while True:
            text = self._queue.get()
            if text is None:
                break
            # Re-create the engine per line to dodge the same one-shot bug.
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            if self.lang == "zh":
                for v in engine.getProperty("voices"):
                    if any(k in f"{v.name} {v.id}".lower() for k in ZH_VOICE_KEYWORDS):
                        engine.setProperty("voice", v.id)
                        break
            engine.say(text)
            engine.runAndWait()
            engine.stop()

    def close(self):
        if self.enabled:
            self._queue.put(None)
