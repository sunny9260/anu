# Anu

Anu is a desktop security and face recognition assistant built with Flask, OpenCV, and system automation tools. It monitors processes, handles authorized face recognition, and provides a local web interface for alerts, task tracking, and rule control.

## Features

- Face recognition for owner authentication
- Process control and intruder detection
- Local Flask-based dashboard
- Task and rule management
- System audio control support on Windows

## Requirements

- Python 3.8+
- OpenCV
- Flask
- psutil
- pyautogui
- pycaw (Windows audio control)

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

Then open the local Flask interface in your browser.

## Repository Structure

- `app.py` - main Flask application and security logic
- `brain.py` - AI/brain query integration
- `setup_face.py` - face dataset setup and training
- `templates/` - Flask HTML templates
- `static/` - CSS, JavaScript, and intruder media
- `data/` - stored JSON records and brain data
- `faces/` - face image storage
- `model/` - trained model files

## Notes

This project is designed for local use and Windows-based audio/control support. Ensure face dataset and model training are completed before relying on the recognition features.
