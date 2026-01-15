import sys
import os
import time
import math
import logging
import threading 
import numpy as np
import random
import json
import requests
import base64
import tempfile

# 1. Fix Matplotlib/OpenCV for macOS Frozen apps
os.environ['MPLCONFIGDIR'] = os.path.join(tempfile.gettempdir(), 'matplotlib_cache')
os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"

# 2. Silence Output if Frozen (Prevents crash when no terminal exists)
if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
else:
    class Unbuffered(object):
       def __init__(self, stream): self.stream = stream
       def write(self, data): self.stream.write(data); self.stream.flush()
       def writelines(self, datas): self.stream.writelines(datas); self.stream.flush()
       def __getattr__(self, attr): return getattr(self.stream, attr)
    sys.stdout = Unbuffered(sys.stdout)
    sys.stderr = Unbuffered(sys.stderr)

import cv2
import mediapipe as mp
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO

# 3. Resource Path Helper (Critical for finding JSON inside the App)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 4. Flask Setup
app = Flask(__name__, template_folder=resource_path('templates'))
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# logic start

def overlay_image_alpha(img, img_overlay, x, y, width, height):
    try:
        if width <= 0 or height <= 0: return img
        img_overlay = cv2.resize(img_overlay, (width, height))
        y1, y2 = y - height, y
        x1, x2 = x - width // 2, x + width // 2
        h, w, c = img.shape
        
        if y1 < 0: y1 = 0
        if y2 > h: y2 = h
        if x1 < 0: x1 = 0
        if x2 > w: x2 = w
        
        overlay_h, overlay_w = y2 - y1, x2 - x1
        if overlay_h <= 0 or overlay_w <= 0: return img

        small_overlay = img_overlay[0:overlay_h, 0:overlay_w]
        
        if small_overlay.shape[2] == 4:
            alpha_mask = small_overlay[:, :, 3] / 255.0
            alpha_inv = 1.0 - alpha_mask
            for c in range(0, 3):
                img[y1:y2, x1:x2, c] = (alpha_mask * small_overlay[:, :, c] + alpha_inv * img[y1:y2, x1:x2, c])
        else:
            img[y1:y2, x1:x2] = small_overlay
        return img
    except Exception: return img

def is_hand_open(landmarks):
    wrist = landmarks[0]
    fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]
    open_count = 0
    for tip_idx, pip_idx in fingers:
        tip, pip = landmarks[tip_idx], landmarks[pip_idx]
        if ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2) > ((pip.x - wrist.x)**2 + (pip.y - wrist.y)**2):
            open_count += 1
    return open_count >= 3

class PlantSystem:
    def __init__(self, screen_width, screen_height):
        self.w = screen_width
        self.h = screen_height
        self.slot_size = 60
        self.num_slots = screen_width // self.slot_size
        self.plant_heights = np.zeros(self.num_slots, dtype=np.float32)
        self.plant_types = [-1] * self.num_slots
        self.plant_char = np.zeros(self.num_slots, dtype=np.float32)
        self.max_heights = np.random.randint(200, 500, size=self.num_slots)
        self.loaded_images = []
        self.load_plant_data()

    def load_plant_data(self):
        # Use resource_path to find JSON
        json_path = resource_path(os.path.join("JSON", "plants.json"))
        print(f"🌐 Connecting to Plant Database via {json_path}...")
        try:
            if not os.path.exists(json_path): 
                print("JSON NOT FOUND AT:", json_path)
                raise Exception("Missing JSON")
            
            with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
            
            count = 0; max_load = 50 
            for plant_id, plant_info in data.items():
                if count >= max_load: break
                url = plant_info.get('springimgpng_med')
                if not url: url = plant_info.get('summerimgpng_med')
                if not url: url = plant_info.get('springimgpng_low')
                if url and "http" in url:
                    try:
                        response = requests.get(url, timeout=3)
                        image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                        img = cv2.imdecode(image_array, cv2.IMREAD_UNCHANGED)
                        if img is not None:
                            self.loaded_images.append(img)
                            count += 1
                    except Exception: continue
            print(f"✅ Ready! Loaded {len(self.loaded_images)} plant species.")
        except Exception as e:
            print(f"⚠️ Error initializing plants: {e}")
            dummy = np.zeros((100, 100, 4), dtype=np.uint8); dummy[:] = [20, 200, 20, 255]
            self.loaded_images.append(dummy)

    def interact(self, particle):
        slot_idx = int(particle.x // self.slot_size)
        if slot_idx < 0 or slot_idx >= self.num_slots: return False, False

        if particle.element_type == "Water":
            if particle.y >= self.h - 15:
                if self.plant_heights[slot_idx] == 0 and len(self.loaded_images) > 0:
                    self.plant_types[slot_idx] = random.randint(0, len(self.loaded_images)-1)
                    self.plant_char[slot_idx] = 0.0
                if self.plant_char[slot_idx] > 0:
                    self.plant_char[slot_idx] -= 0.1
                    if self.plant_char[slot_idx] < 0: self.plant_char[slot_idx] = 0
                else:
                    if self.plant_heights[slot_idx] < self.max_heights[slot_idx]: self.plant_heights[slot_idx] += 3.0
                return True, False
        elif particle.element_type == "Fire":
            plant_h = self.plant_heights[slot_idx]
            if plant_h > 0:
                if particle.y > (self.h - plant_h):
                    if self.plant_char[slot_idx] < 1.0: self.plant_char[slot_idx] += 0.05
                    else:
                        self.plant_heights[slot_idx] -= 8.0 
                        if self.plant_heights[slot_idx] < 0: 
                            self.plant_heights[slot_idx] = 0; self.plant_types[slot_idx] = -1; self.plant_char[slot_idx] = 0
                    return True, True 
        return False, False

    def draw(self, frame):
        cv2.rectangle(frame, (0, self.h - 15), (self.w, self.h), (20, 50, 20), -1)
        cv2.line(frame, (0, self.h - 15), (self.w, self.h - 15), (50, 200, 50), 2)
        for i in range(self.num_slots):
            height = int(self.plant_heights[i])
            img_idx = self.plant_types[i]
            if height > 0 and img_idx != -1 and img_idx < len(self.loaded_images):
                x_center = i * self.slot_size + (self.slot_size // 2)
                src_img = self.loaded_images[img_idx]
                aspect = src_img.shape[1] / src_img.shape[0]
                draw_w = int(height * aspect); draw_h = height
                resized_plant = cv2.resize(src_img, (draw_w, draw_h))
                if self.plant_char[i] > 0:
                    plant_float = resized_plant.astype(np.float32)
                    plant_float[:, :, :3] *= (1.0 - (self.plant_char[i] * 0.8))
                    resized_plant = plant_float.astype(np.uint8)
                frame = overlay_image_alpha(frame, resized_plant, x_center, self.h - 5, draw_w, draw_h)

class Particle:
    def __init__(self, x, y, element_type, velocity=None):
        self.x = x; self.y = y; self.element_type = element_type; self.life = 1.0 
        if self.element_type == "Fire":
            if velocity: self.vx, self.vy = velocity[0] + random.uniform(-2,2), velocity[1] + random.uniform(-2,2)
            else: self.vx, self.vy = random.uniform(-2,2), random.uniform(-4,-9)
            self.decay = 0.06; self.size = random.randint(4, 10)
        elif self.element_type == "Water":
            self.vx = random.uniform(-0.5, 0.5); self.vy = random.uniform(5, 15)     
            self.size = random.randint(2, 5); self.decay = 0.04
        elif self.element_type == "Ash":
            self.vx, self.vy = random.uniform(-1, 1), random.uniform(-1, -3)
            self.size = random.randint(2, 5); self.decay = 0.03

    def update(self):
        self.life -= self.decay
        if self.element_type == "Water": self.vy += 0.5 
        self.x += self.vx; self.y += self.vy

    def draw(self, frame):
        if self.life <= 0: return
        ix, iy = int(self.x), int(self.y)
        if self.element_type == "Fire":
            color = (255, 255, 255) if self.life > 0.7 else (0, 165, 255) if self.life > 0.4 else (0, 0, 200)
            cv2.circle(frame, (ix, iy), int(self.size * self.life), color, -1)
        elif self.element_type == "Water":
            cv2.line(frame, (ix, iy), (ix, int(iy - self.vy)), (255, 255, 255), self.size)
        elif self.element_type == "Ash":
            col = int(50 + (self.life * 100)); cv2.circle(frame, (ix, iy), self.size, (col, col, col), -1)

# threading architecture
def run_camera_loop():
    print("🎥 Starting Camera Loop (Main Thread)")
    mp_holistic = mp.solutions.holistic
    holistic = mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    hand_connections = mp.solutions.hands.HAND_CONNECTIONS

    cap = cv2.VideoCapture(0)
    width = 1280; height = 720
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    # Initialize Garden (Downloads images, might take a few seconds)
    garden = PlantSystem(width, height)
    particles = []

    while True:
        # CRITICAL: Keep macOS Window Manager happy
        cv2.waitKey(1)

        success, frame = cap.read()
        if not success: 
            time.sleep(0.1); continue

        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = holistic.process(rgb_frame)

        def get_coords(landmark): return int(landmark.x * w), int(landmark.y * h)

        # Right Hand (Fire)
        if results.right_hand_landmarks:
            landmarks = results.right_hand_landmarks.landmark
            if is_hand_open(landmarks):
                wrist, tip = landmarks[0], landmarks[12]
                dx, dy = (tip.x - wrist.x), (tip.y - wrist.y)
                dist = math.sqrt(dx*dx + dy*dy)
                aim_vx, aim_vy = (dx / dist) * 30, (dy / dist) * 30
                for lm in landmarks: 
                    particles.append(Particle(*get_coords(lm), "Fire", velocity=(aim_vx, aim_vy)))

        # Left Hand (Water)
        if results.left_hand_landmarks:
            landmarks = results.left_hand_landmarks.landmark
            if is_hand_open(landmarks):
                for lm in landmarks: 
                    particles.append(Particle(*get_coords(lm), "Water"))

        garden.draw(frame)
        frame = cv2.convertScaleAbs(frame, alpha=0.8, beta=-10)
        
        alive_particles = []
        for p in particles:
            p.update()
            absorbed, spawn_ash = garden.interact(p)
            if spawn_ash:
                for _ in range(2): alive_particles.append(Particle(p.x, p.y, "Ash"))
            if not absorbed and p.life > 0:
                p.draw(frame)
                alive_particles.append(p)
        particles = alive_particles

        _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        b64_string = base64.b64encode(buffer).decode('utf-8')
        
        # Emit to Electron
        socketio.emit('new_frame', {'image': b64_string})
        time.sleep(0.015)

def run_flask_server():
    print("🚀 Starting Flask Server (Background Thread)")
    cert = resource_path('cert.pem')
    key = resource_path('key.pem')
    try:
        # Use simple threading, not eventlet, for compatibility
        socketio.run(app, host='127.0.0.1', port=5050, ssl_context=(cert, key), allow_unsafe_werkzeug=True)
    except Exception as e:
        print("❌ SERVER ERROR:", e)

@app.route('/')
def index(): return render_template('plantindex.html')

if __name__ == "__main__":
    # 1. Start Flask in Background
    server_thread = threading.Thread(target=run_flask_server)
    server_thread.daemon = True
    server_thread.start()

    # 2. Run Camera in Main Thread (Required for macOS)
    try:
        run_camera_loop()
    except KeyboardInterrupt:
        os._exit(0)