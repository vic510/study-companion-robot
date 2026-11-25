# AI-GENERATED CODE: written by Claude (Anthropic, Claude Opus 5.5) via Claude Code,
# October 2026. Requirements, design decisions and pilot testing by Group 10.
# See AI_DISCLOSURE.md for which parts came from the team.
"""Per-session CSV + JSON logs for the user study analysis."""

import csv
import json
import time
from pathlib import Path


class SessionLog:
    def __init__(self, log_dir: str, participant: str, condition: str):
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        base = Path(log_dir) / f"{participant}_{condition}_{stamp}"
        self.csv_path = base.with_suffix(".csv")
        self.json_path = base.with_suffix(".json")
        self.participant = participant
        self.condition = condition
        self._file = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["wall_time", "elapsed_s", "kind", "value", "detail"])

    def write(self, elapsed: float, kind: str, value, detail: str = ""):
        self._writer.writerow([time.strftime("%H:%M:%S"), f"{elapsed:.2f}", kind, value, detail])

    def summary(self, data: dict):
        data = {"participant": self.participant, "condition": self.condition, **data}
        self.json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def close(self):
        self._file.close()
