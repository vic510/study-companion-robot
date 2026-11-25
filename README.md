# Adaptive Study Companion Robot

A course project (HRI, Group 10): a webcam-based study companion that estimates the user's attention and responds with an animated robot face and speech.

- **States:** Focused, Distracted, Away, Session Complete
- **Vision:** OpenCV + MediaPipe Face/Pose Landmarker for head direction and presence; shoulder detection separates "head down" from "left the desk"
- **Feedback:** animated robot face (`study_robot/face.py`, `ui.py`) and text-to-speech (Windows SAPI)
- **Calibration:** multi-target (e.g. external screen + laptop), manual recalibration, pause/stop controls
- Proposal: `Group_10_Proposal.pdf`; intermediate presentation: `slides/`; demo media: `media/`

## Run (Windows, Python 3.12+)

```powershell
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python download_model.py
.\.venv\Scripts\python main.py --debug --minutes 3
```

Add `--targets screen` if you only have one screen. Tests: `python -m pytest tests`.
