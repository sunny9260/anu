import os
import cv2
import numpy as np
import threading
import time
import subprocess
import webbrowser
import json
import psutil
import datetime
from flask import Flask, render_template, Response, jsonify, request
from brain import query_brain

# Import pyautogui for GUI actions
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

# Import pycaw for Windows audio control
has_pycaw = False
volume_interface = None
try:
    import ctypes
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_interface = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
    has_pycaw = True
except Exception as e:
    print(f"[WARN] Audio control initialization failed (pycaw): {e}. Fallback to simulated keys will be used.")

app = Flask(__name__)

# Directory creations
os.makedirs("data", exist_ok=True)
os.makedirs("static/intruders", exist_ok=True)
os.makedirs("model", exist_ok=True)

# Persistent Database Setup
db_lock = threading.Lock()
db_data = {
    "tasks": [
        {"id": 1, "text": "Set up J.A.R.V.I.S. Core Security Suite", "completed": True, "timestamp": "12:00 PM"},
        {"id": 2, "text": "Train personal face recognition profile", "completed": False, "timestamp": "12:05 PM"},
        {"id": 3, "text": "Configure process control rules", "completed": False, "timestamp": "12:10 PM"}
    ],
    "rules": [
        {"id": 1, "process": "notepad.exe", "description": "Prevent Notepad during secure sessions"}
    ],
    "records": []
}

def load_database():
    global db_data
    if os.path.exists("data/records.json"):
        try:
            with open("data/records.json", "r") as f:
                loaded = json.load(f)
                # Safeguard keys
                for key in ["tasks", "rules", "records"]:
                    if key in loaded:
                        db_data[key] = loaded[key]
            print("[DB] Records database loaded successfully.")
        except Exception as e:
            print(f"[DB] Error loading records database: {e}")

def save_database():
    with db_lock:
        try:
            with open("data/records.json", "w") as f:
                json.dump(db_data, f, indent=4)
        except Exception as e:
            print(f"[DB] Error saving records database: {e}")

def add_record(category, message, metadata=None):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "category": category, # 'security', 'task', 'system', 'voice'
        "message": message,
        "metadata": metadata or {}
    }
    with db_lock:
        db_data["records"].insert(0, entry)
        # Cap records in json to prevent massive file bloating
        if len(db_data["records"]) > 200:
            db_data["records"].pop()
    save_database()

# Global state
status_lock = threading.Lock()
system_status = {
    "locked": False,
    "owner_detected": False,
    "presence": False,
    "absence_timer": 0.0,
    "lock_mode": "overlay",  # 'overlay' or 'windows'
    "lock_timeout": 10.0,    # seconds of absence before locking
    "violation_alert": None, # process name that triggered blacklist violation
    "logs": []
}

# Video streaming globals
latest_frame = None
frame_lock = threading.Lock()
intruder_cooldown = 0.0

# Camera performance tuning
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 20
FACE_DETECTION_SKIP_FRAMES = 2
JPEG_QUALITY = 70

# Face Recognition Model
face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(face_cascade_path)

recognizer = None
model_loaded = False

def load_recognizer_model():
    global recognizer, model_loaded
    if os.path.exists("model/trainer.yml"):
        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read("model/trainer.yml")
            model_loaded = True
            add_log("J.A.R.V.I.S. face recognition model loaded successfully.")
            # Set the task completed
            with db_lock:
                for t in db_data["tasks"]:
                    if t["id"] == 2:
                        t["completed"] = True
            save_database()
        except Exception as e:
            add_log(f"Error loading face model: {e}")
            model_loaded = False
    else:
        add_log("No face recognition model found. Please run setup_face.py to register your face.")
        model_loaded = False

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with status_lock:
        system_status["logs"].append(log_entry)
        if len(system_status["logs"]) > 40:
            system_status["logs"].pop(0)

# Volume control helper
def set_volume(level):
    level = max(0, min(100, level))
    if has_pycaw and volume_interface:
        try:
            volume_interface.SetMasterVolumeLevelScalar(level / 100.0, None)
            add_log(f"System volume set to {level}%.")
            add_record("system", f"System volume set to {level}%.")
            return True
        except Exception as e:
            add_log(f"Failed to set volume via pycaw: {e}")
    
    if pyautogui:
        add_log("Attempting volume control via simulated keys...")
        if level == 0:
            pyautogui.press('volumemute')
        else:
            pyautogui.press('volumeup')
        return True
    return False

# Open applications helper
def open_application(app_name):
    app_name = app_name.lower()
    # Check if app is in blacklist before launching
    with db_lock:
        blacklist = [rule["process"].lower().split(".")[0] for rule in db_data["rules"]]
    
    for blocked in blacklist:
        if blocked in app_name:
            msg = f"Blocked attempt to open restricted application: '{app_name}'."
            add_log(msg)
            add_record("security", msg)
            return f"I cannot do that, Sir. Opening {app_name} is currently restricted by your active directives."

    if "youtube" in app_name:
        webbrowser.open("https://youtube.com")
        add_log("Opening YouTube in browser.")
        add_record("system", "Opened YouTube in browser.")
        return "Opening YouTube, Sir."
    elif "google" in app_name:
        webbrowser.open("https://google.com")
        add_log("Opening Google in browser.")
        add_record("system", "Opened Google in browser.")
        return "Opening Google, Sir."
    elif "notepad" in app_name:
        subprocess.Popen("notepad.exe")
        add_log("Launching Notepad.")
        add_record("system", "Launched Notepad.")
        return "Opening Notepad, Sir."
    elif "calculator" in app_name or "calc" in app_name:
        subprocess.Popen("calc.exe")
        add_log("Launching Calculator.")
        add_record("system", "Launched Calculator.")
        return "Opening Calculator, Sir."
    elif "command prompt" in app_name or "cmd" in app_name:
        subprocess.Popen("cmd.exe")
        add_log("Launching Command Prompt.")
        add_record("system", "Launched Command Prompt.")
        return "Opening Command Prompt, Sir."
    else:
        webbrowser.open(f"https://www.google.com/search?q={app_name}")
        add_log(f"Searching web for: {app_name}")
        add_record("system", f"Searched web for: '{app_name}'.")
        return f"I couldn't find a local app for {app_name}, so I searched for it online, Sir."

# System locking action
def lock_pc():
    with status_lock:
        if system_status["locked"]:
            return
        system_status["locked"] = True
    
    mode = system_status["lock_mode"]
    add_log(f"Initiating security lock sequence. Mode: {mode.upper()}.")
    add_record("security", f"PC Status locked. Mode: {mode.upper()}.")
    
    if mode == "windows":
        try:
            ctypes.windll.user32.LockWorkStation()
            add_log("Windows Workstation locked.")
        except Exception as e:
            add_log(f"Failed to lock Windows: {e}")
            with status_lock:
                system_status["lock_mode"] = "overlay"
            add_log("Falling back to J.A.R.V.I.S. overlay lock.")

# System unlocking action
def unlock_pc():
    with status_lock:
        if not system_status["locked"]:
            return
        system_status["locked"] = False
        system_status["absence_timer"] = 0.0
    add_log("Security clearance verified. Welcome back, Sir.")
    add_record("security", "Security clearance verified. PC unlocked.")

# Process Scanner Thread (What not to do)
def process_blacklist_scanner():
    add_log("J.A.R.V.I.S. Process Scanner thread active.")
    while True:
        with db_lock:
            blacklist = [rule["process"].lower() for rule in db_data["rules"]]
            
        if blacklist:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pname = proc.info['name'].lower()
                    # Check matching process name
                    if pname in blacklist or any(blocked in pname for blocked in blacklist if blocked.endswith('*')):
                        proc.kill()
                        msg = f"Rule Violation: Auto-terminated restricted application '{proc.info['name']}'."
                        add_log(msg)
                        add_record("security", msg, {"pid": proc.info['pid'], "process_name": proc.info['name']})
                        
                        # Trigger vocal and sound warning in UI
                        with status_lock:
                            system_status["violation_alert"] = proc.info['name']
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        time.sleep(3.0)

# Background Webcam, Presence, and Intruder Capture Thread
def webcam_loop():
    global latest_frame, recognizer, model_loaded, intruder_cooldown
    
    time.sleep(1.5)
    load_recognizer_model()
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    if not cap.isOpened():
        add_log("CRITICAL ERROR: Unable to access webcam.")
        return
        
    last_time = time.time()
    intruder_absence_duration = 0.0
    frame_counter = 0
    last_faces = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue
            
        frame_counter += 1
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        # Resize once for faster detection, but keep original frame for display
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detection_scale = 0.5
        small_gray = cv2.resize(gray, (0, 0), fx=detection_scale, fy=detection_scale)
        if frame_counter % FACE_DETECTION_SKIP_FRAMES == 0:
            faces = face_cascade.detectMultiScale(small_gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
            last_faces = [(int(x / detection_scale), int(y / detection_scale), int(w / detection_scale), int(h / detection_scale)) for (x, y, w, h) in faces]
        else:
            faces = last_faces
        
        owner_found = False
        unauthorized_found = False
        
        # Check if training model exists and reload if it was created after startup
        if not model_loaded and os.path.exists("model/trainer.yml"):
            load_recognizer_model()
            
        for (x, y, w, h) in faces:
            label_text = "FACE DETECTED"
            color = (0, 165, 255) # Cyan/Orange alert color
            
            if model_loaded and recognizer is not None:
                try:
                    label, confidence = recognizer.predict(gray[y:y+h, x:x+w])
                    if label == 1 and confidence < 80:
                        owner_found = True
                        label_text = f"OWNER (Match: {int(100 - confidence)}%)"
                        color = (0, 255, 0) # Green for authorized
                    else:
                        unauthorized_found = True
                        label_text = f"UNKNOWN (Diff: {int(confidence)})"
                        color = (0, 0, 255) # Red for unauthorized
                except Exception as e:
                    label_text = "RECOGNITION ERROR"
                    color = (0, 0, 255)
            else:
                label_text = "UNREGISTERED FACE"
                color = (0, 255, 255)
                
            # Draw overlay box
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, label_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        # Presence detection state updates
        with status_lock:
            system_status["owner_detected"] = owner_found
            system_status["presence"] = (len(faces) > 0)
            
            if owner_found:
                system_status["absence_timer"] = 0.0
                if system_status["locked"] and system_status["lock_mode"] == "overlay":
                    threading.Thread(target=unlock_pc).start()
            else:
                if not system_status["locked"]:
                    system_status["absence_timer"] += dt
                    if system_status["absence_timer"] >= system_status["lock_timeout"]:
                        threading.Thread(target=lock_pc).start()
                        
        # Intruder snapshot logic
        if system_status["locked"] and (unauthorized_found or (len(faces) > 0 and not owner_found)):
            intruder_absence_duration += dt
            # If intruder stands in front of locked PC for > 2.5 seconds
            if intruder_absence_duration >= 2.5 and time.time() > intruder_cooldown:
                intruder_cooldown = time.time() + 15.0 # Cooldown of 15 seconds to avoid flooding
                
                # Capture frame
                timestamp_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"intruder_{timestamp_file}.jpg"
                filepath = os.path.join("static/intruders", filename)
                
                # Write file
                cv2.imwrite(filepath, frame)
                
                # Save record in db
                msg = "Intruder Alert: Snapshot captured during session lock."
                add_log(msg)
                add_record("security", msg, {
                    "image_path": f"/static/intruders/{filename}",
                    "details": "Unknown face biometric scanning mismatch"
                })
        else:
            # Reset timer if no intruder or unlocked
            intruder_absence_duration = 0.0
                    
        # Render clean Jarvis interface design in frame
        cv2.putText(frame, "J.A.R.V.I.S. SECURITY HUB", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        status_text = "SECURED / OWNER PRESENT" if owner_found else "SCANNING FOR OWNER..."
        if system_status["locked"]:
            status_text = "SYSTEM LOCKED"
        cv2.putText(frame, f"STATUS: {status_text}", (15, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 
                    (0, 255, 0) if owner_found else (0, 0, 255) if system_status["locked"] else (0, 255, 255), 1)
                    
        # Encode as JPEG with lower quality to reduce bandwidth and latency
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if ret:
            with frame_lock:
                latest_frame = jpeg.tobytes()
                
        if dt < 1.0 / CAMERA_FPS:
            time.sleep(max(0.0, 1.0 / CAMERA_FPS - dt))

# Web Server Routes
@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    global latest_frame
    while True:
        with frame_lock:
            if latest_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
        time.sleep(0.02)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status', methods=['GET'])
def get_status():
    with status_lock:
        return jsonify(system_status)

@app.route('/clear_alert', methods=['POST'])
def clear_alert():
    with status_lock:
        system_status["violation_alert"] = None
    return jsonify({"success": True})

@app.route('/set_lock_mode', methods=['POST'])
def set_lock_mode():
    data = request.get_json() or {}
    mode = data.get("lock_mode")
    timeout = data.get("lock_timeout")
    
    with status_lock:
        if mode in ["windows", "overlay"]:
            system_status["lock_mode"] = mode
            add_log(f"Lock mode set to: {mode}")
        if timeout is not None:
            try:
                system_status["lock_timeout"] = float(timeout)
                add_log(f"Lock timeout set to: {timeout} seconds")
            except ValueError:
                pass
    return jsonify({"success": True, "status": system_status})

@app.route('/trigger_lock', methods=['POST'])
def trigger_lock():
    lock_pc()
    return jsonify({"success": True, "status": system_status})

@app.route('/trigger_unlock', methods=['POST'])
def trigger_unlock():
    data = request.get_json() or {}
    password = data.get("password", "")
    
    if password == "jarvis123" or system_status["owner_detected"]:
        unlock_pc()
        return jsonify({"success": True, "status": system_status})
    else:
        add_log("Bypass unlock attempt rejected: Invalid credentials.")
        add_record("security", "Invalid bypass code entered.")
        return jsonify({"success": False, "error": "Invalid Passcode"}), 403

# API Telemetry route
@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        bat_percent = battery.percent if battery else 100
        bat_plugged = battery.power_plugged if battery else True
        return jsonify({
            "cpu": cpu,
            "ram": ram,
            "battery": bat_percent,
            "plugged": bat_plugged,
            "process_count": len(psutil.pids())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API Processes route
@app.route('/processes', methods=['GET'])
def get_processes():
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            if info['name']:
                procs.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu": round(info['cpu_percent'] or 0.0, 1),
                    "mem": round(info['memory_percent'] or 0.0, 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    # Sort by memory usage, top 30
    procs = sorted(procs, key=lambda x: x['mem'], reverse=True)[:30]
    return jsonify(procs)

@app.route('/processes/<int:pid>', methods=['DELETE'])
def terminate_process(pid):
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        proc.kill()
        msg = f"User terminated process '{name}' (PID: {pid})."
        add_log(msg)
        add_record("system", msg, {"pid": pid, "process_name": name})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# Tasks APIs ("What to do")
@app.route('/tasks', methods=['GET', 'POST'])
def manage_tasks():
    if request.method == 'GET':
        with db_lock:
            return jsonify(db_data["tasks"])
            
    elif request.method == 'POST':
        data = request.get_json() or {}
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"success": False, "error": "Task empty"}), 400
            
        with db_lock:
            new_id = max([t["id"] for t in db_data["tasks"]] + [0]) + 1
            timestamp = datetime.datetime.now().strftime("%I:%M %p")
            new_task = {"id": new_id, "text": text, "completed": False, "timestamp": timestamp}
            db_data["tasks"].append(new_task)
            
        save_database()
        msg = f"Directive added: '{text}'."
        add_log(msg)
        add_record("task", msg)
        return jsonify({"success": True, "task": new_task})

@app.route('/tasks/<int:tid>', methods=['PUT', 'DELETE'])
def update_task(tid):
    if request.method == 'PUT':
        data = request.get_json() or {}
        completed = data.get("completed")
        
        found_task = None
        with db_lock:
            for t in db_data["tasks"]:
                if t["id"] == tid:
                    t["completed"] = completed
                    found_task = t
                    break
        if found_task:
            save_database()
            status_word = "completed" if completed else "reopened"
            msg = f"Directive {status_word}: '{found_task['text']}'."
            add_log(msg)
            add_record("task", msg)
            return jsonify({"success": True, "task": found_task})
        return jsonify({"success": False, "error": "Task not found"}), 404
        
    elif request.method == 'DELETE':
        found_task = None
        with db_lock:
            for i, t in enumerate(db_data["tasks"]):
                if t["id"] == tid:
                    found_task = db_data["tasks"].pop(i)
                    break
        if found_task:
            save_database()
            msg = f"Directive deleted: '{found_task['text']}'."
            add_log(msg)
            add_record("task", msg)
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Task not found"}), 404

# Process Rules APIs ("What not to do")
@app.route('/rules', methods=['GET', 'POST'])
def manage_rules():
    if request.method == 'GET':
        with db_lock:
            return jsonify(db_data["rules"])
            
    elif request.method == 'POST':
        data = request.get_json() or {}
        proc_name = data.get("process", "").strip().lower()
        desc = data.get("description", "").strip() or f"Restricted process rule for {proc_name}"
        
        if not proc_name:
            return jsonify({"success": False, "error": "Process name required"}), 400
        if not proc_name.endswith('.exe'):
            proc_name += '.exe'
            
        with db_lock:
            new_id = max([r["id"] for r in db_data["rules"]] + [0]) + 1
            new_rule = {"id": new_id, "process": proc_name, "description": desc}
            db_data["rules"].append(new_rule)
            
        save_database()
        msg = f"Security Rule Active: Restricted '{proc_name}'."
        add_log(msg)
        add_record("security", msg)
        return jsonify({"success": True, "rule": new_rule})

@app.route('/rules/<int:rid>', methods=['DELETE'])
def delete_rule(rid):
    found_rule = None
    with db_lock:
        for i, r in enumerate(db_data["rules"]):
            if r["id"] == rid:
                found_rule = db_data["rules"].pop(i)
                break
    if found_rule:
        save_database()
        msg = f"Security Rule Removed: Allowed '{found_rule['process']}'."
        add_log(msg)
        add_record("security", msg)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Rule not found"}), 404

# Records API
@app.route('/records', methods=['GET'])
def get_records():
    with db_lock:
        return jsonify(db_data["records"])

# Voice Command Route
@app.route('/command', methods=['POST'])
def handle_command():
    data = request.get_json() or {}
    cmd_text = data.get("command", "").strip().lower()
    
    if not cmd_text:
        return jsonify({"success": False, "reply": "I didn't hear anything, Sir."})
        
    add_log(f"Voice Command: '{cmd_text}'")
    add_record("voice", f"Voice command received: '{cmd_text}'")
    
    # 1. Run through J.A.R.V.I.S. Local SLM & LLM core
    brain_response = query_brain(cmd_text)
    reply = brain_response["reply"]
    tag = brain_response["tag"]
    success = True
    
    # 2. Handle SLM control actions
    if brain_response["type"] == "control":
        if tag == "lock":
            lock_pc()
        elif tag == "unlock":
            if system_status["owner_detected"]:
                unlock_pc()
            else:
                reply = "Biometric check failed. I cannot unlock without verifying your presence, Sir."
                success = False
        elif tag == "volume_up":
            current = 50
            if has_pycaw and volume_interface:
                current = int(volume_interface.GetMasterVolumeLevelScalar() * 100)
            set_volume(current + 15)
        elif tag == "volume_down":
            current = 50
            if has_pycaw and volume_interface:
                current = int(volume_interface.GetMasterVolumeLevelScalar() * 100)
            set_volume(current - 15)
        elif tag == "volume_mute":
            set_volume(0)
        elif tag == "volume_unmute":
            set_volume(30)
        elif tag == "minimize":
            if pyautogui:
                pyautogui.hotkey('win', 'd')
            else:
                reply = "PyAutoGUI interface is offline, Sir."
                success = False
            
    # 3. Dynamic argument fallback controls (adding tasks, opening specific apps)
    if "task" in cmd_text or "schedule" in cmd_text or "todo" in cmd_text or "to do" in cmd_text:
        if "add" in cmd_text:
            task_content = ""
            if "task to" in cmd_text:
                task_content = cmd_text.split("task to", 1)[1].strip()
            elif "task" in cmd_text:
                task_content = cmd_text.split("task", 1)[1].strip()
            elif "add" in cmd_text:
                task_content = cmd_text.split("add", 1)[1].strip()
                
            if task_content:
                with db_lock:
                    new_id = max([t["id"] for t in db_data["tasks"]] + [0]) + 1
                    timestamp = datetime.datetime.now().strftime("%I:%M %p")
                    new_task = {"id": new_id, "text": task_content.capitalize(), "completed": False, "timestamp": timestamp}
                    db_data["tasks"].append(new_task)
                save_database()
                msg = f"Voice added directive: '{new_task['text']}'"
                add_log(msg)
                add_record("task", msg)
                reply = f"Understood, Sir. I have added {task_content} to your planner."
                success = True
            else:
                reply = "What task would you like me to add, Sir?"
                success = False
                
        elif "read" in cmd_text or "what" in cmd_text or "list" in cmd_text:
            with db_lock:
                active_tasks = [t["text"] for t in db_data["tasks"] if not t["completed"]]
            if active_tasks:
                tasks_joined = ", ".join(active_tasks)
                reply = f"Sir, you have {len(active_tasks)} pending system directives: {tasks_joined}."
            else:
                reply = "You have no pending tasks in your planner, Sir. Excellent work."
            success = True
            
    elif "open" in cmd_text:
        parts = cmd_text.split("open", 1)
        if len(parts) > 1:
            target_app = parts[1].strip()
            reply = open_application(target_app)
            success = True
            
    return jsonify({"success": success, "reply": reply})

if __name__ == '__main__':
    load_database()
    
    # Start Webcam and Face check thread
    t = threading.Thread(target=webcam_loop, daemon=True)
    t.start()
    
    # Start Process Scanner thread (what not to do rule watcher)
    p = threading.Thread(target=process_blacklist_scanner, daemon=True)
    p.start()
    
    # Run server
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
