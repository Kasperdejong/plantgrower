import os
import json
import requests
import random
from PIL import Image
from io import BytesIO

# --- CONFIGURATION ---
JSON_PATH = os.path.join("JSON", "plants.json")
BUILD_DIR = "build"
ICON_NAME = "icon.icns"

def create_random_icon():
    # 1. Ensure build directory exists
    if not os.path.exists(BUILD_DIR):
        os.makedirs(BUILD_DIR)

    # 2. Load JSON
    print(f"📖 Reading {JSON_PATH}...")
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON: {e}")
        return

    # 3. Gather all valid candidates
    candidates = []
    print("🔎 Scanning for valid plant images...")
    
    for pid, plant in data.items():
        # Try spring, then summer, then low quality
        url = plant.get('springimgpng_med') or plant.get('summerimgpng_med') or plant.get('springimgpng_low')
        
        if url and "http" in url:
            name = plant.get('Common_Name', pid)
            candidates.append((name, url))

    if not candidates:
        print("❌ No images found in JSON.")
        return

    # 4. Pick a Random One
    selected_name, selected_url = random.choice(candidates)
    print(f"\n🎲 Randomly Selected: '{selected_name}'")
    print(f"⬇️  Downloading: {selected_url}")

    try:
        response = requests.get(selected_url, timeout=10)
        img = Image.open(BytesIO(response.content))
    except Exception as e:
        print(f"❌ Failed to download image: {e}")
        return

    # 5. Create macOS Icon (1024x1024 transparent square)
    print("🎨 Processing image...")
    base_size = 1024
    icon = Image.new('RGBA', (base_size, base_size), (0, 0, 0, 0))
    
    # Calculate aspect ratio to fit inside the square
    img_ratio = img.width / img.height
    if img_ratio > 1:
        new_w = base_size
        new_h = int(base_size / img_ratio)
    else:
        new_h = base_size
        new_w = int(base_size * img_ratio)

    # Add padding (90% size) so it doesn't touch edges
    new_w = int(new_w * 0.9)
    new_h = int(new_h * 0.9)

    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Center it
    pos_x = (base_size - new_w) // 2
    pos_y = (base_size - new_h) // 2
    icon.paste(img, (pos_x, pos_y))

    # 6. Save
    save_path = os.path.join(BUILD_DIR, ICON_NAME)
    icon.save(save_path, format='ICNS')
    
    print(f"✅ Icon saved to: {save_path}")
    print("👀 Opening preview...")
    
    # 7. Show the user immediately
    icon.show()

if __name__ == "__main__":
    create_random_icon()