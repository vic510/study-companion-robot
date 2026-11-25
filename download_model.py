# AI-GENERATED CODE: written by Claude (Anthropic, Claude Opus 5.5) via Claude Code,
# October 2026. Requirements, design decisions and pilot testing by Group 10.
# See AI_DISCLOSURE.md for which parts came from the team.
"""Download the MediaPipe models (face ~3.8 MB, pose ~5.5 MB) into models/."""

import urllib.request
from pathlib import Path

from study_robot.config import MODEL_PATH, MODEL_URL, POSE_MODEL_PATH, POSE_MODEL_URL

if __name__ == "__main__":
    for model_path, url in ((MODEL_PATH, MODEL_URL), (POSE_MODEL_PATH, POSE_MODEL_URL)):
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            print(f"Already present: {path}")
            continue
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, path)
        print(f"Saved to {path} ({path.stat().st_size / 1e6:.1f} MB)")
