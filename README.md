# Anu

Anu is a local security assistant focused on face recognition, process monitoring, and user alerts. It uses Flask for a web dashboard, OpenCV for face detection and recognition, and Windows automation tools for optional system control.

## Features

- Owner face registration and recognition
- Intruder detection using webcam input
- Process monitoring and rule-based enforcement
- Local Flask dashboard for status, rules, and logs
- Windows audio control support using `pycaw`

## Requirements

- Python 3.8+
- `opencv-contrib-python`
- `flask`
- `psutil`
- `pyautogui`
- `pycaw` (Windows-only audio control)
- `transformers`, `torch` (for optional brain integration)

Install dependencies with:

```bash
python -m pip install -r requirements.txt
```

## Setup

1. Run face registration and training:

```bash
python setup_face.py
```

2. After training completes, start the main application:

```bash
python app.py
```

3. Open the displayed local URL in your browser to access the dashboard.

## Usage

- Use `setup_face.py` to collect owner face images and generate `model/trainer.yml`.
- The main app will use that model to identify the registered owner.
- Customize process control rules and monitor alerts from the dashboard.

## Repository Structure

- `app.py` - main application and Flask server
- `brain.py` - AI/brain query helper
- `setup_face.py` - face capture and model training utility
- `requirements.txt` - Python dependencies
- `templates/` - HTML templates for the dashboard
- `static/` - CSS, JavaScript, and intruder media assets
- `data/` - application data and records
- `faces/` - captured face images
- `model/` - trained face recognition model

## Notes

- If OpenCV face functions fail, install `opencv-contrib-python`.
- This project is intended for local development and testing.
- Do not expose face image files or trained owner data if privacy is a concern.

## Common issues

- Webcam not detected: make sure no other application is using the camera and test it with a separate webcam utility.
- `cv2.face` missing: install `opencv-contrib-python` instead of `opencv-python`.
- Permission errors writing files: run the app from a folder where your user account has write access.
- Windows audio control failures: install `pycaw` and verify your device drivers are up to date.
- Slow model training: ensure the captured face images are clear and well-lit, and avoid large background clutter.
