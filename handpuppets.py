import sys
import os
import time
import math
import logging
import threading 
import numpy as np
import tempfile

# 1. Fix Matplotlib
os.environ['MPLCONFIGDIR'] = os.path.join(tempfile.gettempdir(), 'matplotlib_cache')
# 2. Fix OpenCV
os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"

import cv2
import mediapipe as mp
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO

# clean logging
# If frozen, silence everything.
if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
else:
    # Dev mode helper
    class Unbuffered(object):
       def __init__(self, stream):
           self.stream = stream
       def write(self, data):
           self.stream.write(data); self.stream.flush()
       def writelines(self, datas):
           self.stream.writelines(datas); self.stream.flush()
       def __getattr__(self, attr):
           return getattr(self.stream, attr)
    sys.stdout = Unbuffered(sys.stdout)
    sys.stderr = Unbuffered(sys.stderr)

print(f"PYTHON STARTING... Time: {time.time()}")
print(f"Current Directory: {os.getcwd()}")

# fixes
os.environ['MPLCONFIGDIR'] = os.path.join(tempfile.gettempdir(), 'matplotlib_cache')
os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"

try:
    import cv2
    import mediapipe as mp
    print("Libraries imported successfully")
except Exception as e:
    print(f"CRITICAL IMPORT ERROR: {e}")

from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO


# logging setup
# If running as a real App (Frozen), send all prints to the void (devnull).
# This prevents the app from freezing when there is no terminal attached.
# Logging setup (DEEP SILENCE) 
if getattr(sys, 'frozen', False):
    # IN PRODUCTION:
    # Redirect standard file descriptors (1=stdout, 2=stderr) to /dev/null.
    # This silences Python AND the C++ libraries (MediaPipe/TensorFlow).
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1) # Silence stdout
    os.dup2(devnull, 2) # Silence stderr
    sys.stdout = os.fdopen(devnull, 'w')
    sys.stderr = sys.stdout
else:
    # IN DEVELOPMENT:
    # Flush logs immediately so we see them in VS Code
    class Unbuffered(object):
       def __init__(self, stream):
           self.stream = stream
       def write(self, data):
           self.stream.write(data)
           self.stream.flush()
       def writelines(self, datas):
           self.stream.writelines(datas)
           self.stream.flush()
       def __getattr__(self, attr):
           return getattr(self.stream, attr)

    sys.stdout = Unbuffered(sys.stdout)
    sys.stderr = Unbuffered(sys.stderr)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(__name__, 
            template_folder=resource_path('templates'), 
            static_folder=resource_path('assets'))

socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# logic
class PuppetLogic:
    def __init__(self, start_x):
        self.x = start_x
        self.y = 0.5
        self.state = "NEUTRAL"
        self.last_seen = time.time() 

    def update(self, target_x_norm, target_y_norm, gesture_state):
        self.x += (target_x_norm - self.x) * 0.2
        self.y += (target_y_norm - self.y) * 0.2
        self.state = gesture_state
        self.last_seen = time.time() 

        if self.state == "ANGRY":
            self.x += np.random.uniform(-0.01, 0.01)
            self.y += np.random.uniform(-0.01, 0.01)

def get_finger_status(lm_list):
    fingers = []
    tips = [8, 12, 16, 20]; pips = [6, 10, 14, 18]
    for i in range(4): fingers.append(lm_list[tips[i]][2] < lm_list[pips[i]][2])
    return fingers 

def detect_gesture(lm_list):
    x1, y1 = lm_list[4][1], lm_list[4][2]
    x2, y2 = lm_list[8][1], lm_list[8][2]
    dist_pinch = math.hypot(x2 - x1, y2 - y1)
    
    w_x, w_y = lm_list[0][1], lm_list[0][2]
    m_x, m_y = lm_list[9][1], lm_list[9][2]
    hand_size = math.hypot(m_x - w_x, m_y - w_y)

    fingers = get_finger_status(lm_list)
    count = fingers.count(True)

    if count == 0: return "ANGRY"
    if dist_pinch < (hand_size * 0.20): return "SHY"
    if fingers[0] and not any(fingers[1:]): return "DANCING"
    if count >= 3: return "HAPPY"
    return "NEUTRAL"

def assign_hands_to_puppets(puppets, new_hands):
    if len(new_hands) == 0: return 

    if len(new_hands) == 1:
        hand = new_hands[0]
        d0 = math.hypot(hand['x'] - puppets[0].x, hand['y'] - puppets[0].y)
        d1 = math.hypot(hand['x'] - puppets[1].x, hand['y'] - puppets[1].y)
        target = puppets[0] if d0 < d1 else puppets[1]
        target.update(hand['x'], hand['y'], hand['gesture'])

    elif len(new_hands) >= 2:
        h1 = new_hands[0]
        h2 = new_hands[1]
        dist_straight = math.hypot(h1['x'] - puppets[0].x, h1['y'] - puppets[0].y) + \
                        math.hypot(h2['x'] - puppets[1].x, h2['y'] - puppets[1].y)
        dist_cross = math.hypot(h1['x'] - puppets[1].x, h1['y'] - puppets[1].y) + \
                     math.hypot(h2['x'] - puppets[0].x, h2['y'] - puppets[0].y)

        if dist_straight < dist_cross:
            puppets[0].update(h1['x'], h1['y'], h1['gesture'])
            puppets[1].update(h2['x'], h2['y'], h2['gesture'])
        else:
            puppets[1].update(h1['x'], h1['y'], h1['gesture'])
            puppets[0].update(h2['x'], h2['y'], h2['gesture'])

puppets = [PuppetLogic(0.75), PuppetLogic(0.25)]

# camera loop (main thread)
def run_camera_loop():
    print("🐍 PYTHON: Starting Camera Loop on MAIN THREAD...")
    hands = mp.solutions.hands.Hands(min_detection_confidence=0.7, max_num_hands=2)
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("🐍 PYTHON: Camera Initialized. Entering Loop.")

    while True:
        # 1. CRITICAL FIX: Pump the macOS Event Loop
        # This keeps the window manager alive so it doesn't freeze the video
        cv2.waitKey(1)

        if not cap.isOpened():
            time.sleep(1)
            continue

        success, frame = cap.read()
        if not success: 
            time.sleep(0.01)
            continue

        try:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            detected_hands = []
            if results.multi_hand_landmarks:
                for hand_lms in results.multi_hand_landmarks:
                    wrist = hand_lms.landmark[0]
                    tx = wrist.x
                    ty = wrist.y - 0.2 
                    lm_list = [[id, int(lm.x * w), int(lm.y * h)] for id, lm in enumerate(hand_lms.landmark)]
                    gesture = detect_gesture(lm_list)
                    detected_hands.append({'x': tx, 'y': ty, 'gesture': gesture})

            assign_hands_to_puppets(puppets, detected_hands)

            current_time = time.time()
            for p in puppets:
                if current_time - p.last_seen > 0.5: p.state = "NEUTRAL"

            # Original Data loop
            players_data = []
            for i, p in enumerate(puppets):
                players_data.append({
                    'id': i, 
                    'x': p.x, 
                    'y': p.y, 
                    'state': p.state
                })

            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            byte_data = buffer.tobytes()

            socketio.emit('puppet_data', players_data)
            socketio.emit('video_frame', byte_data)
            
            time.sleep(0.015)
        except Exception as e:
            pass

# server (background thread)
def run_flask_server():
    print("🚀 PYTHON: Starting Flask Server in Background...")
    cert = resource_path('cert.pem')
    key = resource_path('key.pem')
    try:
        socketio.run(app, host='127.0.0.1', port=5050, ssl_context=(cert, key), allow_unsafe_werkzeug=True)
    except Exception as e:
        print("❌ SERVER ERROR:", e)

@app.route('/')
def index(): return render_template('puppetindex.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory(resource_path('assets'), path)

if __name__ == "__main__":
    # 1. Start Server in Background Thread
    server_thread = threading.Thread(target=run_flask_server)
    server_thread.daemon = True
    server_thread.start()

    # 2. Run Camera in Main Thread
    run_camera_loop()