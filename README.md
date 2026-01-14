# Hand Puppets (Python + Electron + MediaPipe)

A desktop application that uses Python (MediaPipe/OpenCV) for hand tracking and Electron for the UI. The two processes communicate via a local Socket.IO connection.

## If you are seeing this in github and are on macbook(CLICK THE MAC RELEASE ON THE RIGHT TO INSTALL THE APP)

## Prerequisites

1.  **Python 3.10+**  
    Check with: `python --version`
2.  **Node.js & npm** (Required for Electron)  
    Check with: `node -v`

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Kasperdejong/Python3d.git
cd Python3d
```

## Create the Python environment

This handles the AI and Camera logic.

### On macOS / Linux:

```
python3 -m venv venv
```

#### activate venv (important!)

```
source venv/bin/activate
```

#### install requirements

```
pip install -r requirements.txt
```

### On Windows

```
python -m venv venv
```

#### activate venv (important!)

```
venv\Scripts\activate
```

#### install requirements

```
pip install -r requirements.txt
```

## Install Node.js Dependencies

npm install

## Generate SSL Certificates

The app runs on a secure local server (https://127.0.0.1:5050). You need to generate self-signed certificates for it to work. Run this command in the root folder:
macOS / Linux:

```
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
```

(Just press Enter through all the questions).
Windows:
You will need to generate cert.pem and key.pem using OpenSSL or a tool like Git Bash, and place them in the root folder.

# Development mode (Testing)

Let electron handle running the python script

Make sure the venv is activated
run the start command

```
npm start
```

What happens:
Electron launches.
Electron silently spawns your Python script in the background.
Python activates the camera (Green light on).
The window connects to the Python server.
Note: Logs from Python will appear in your VS Code terminal labeled [PYTHON].

## How to Build (Create a Standalone App)

To send this app to friends, you must package it into a .dmg (Mac) or .exe (Windows).
Step 1: Compile Python
This bundles MediaPipe, OpenCV, and your script into a single binary file.
Make sure venv is active!

```
pyinstaller handpuppets.spec
```

(Type y if asked to overwrite).

Step 2: Build the App
This wraps the Python binary into a clickable Desktop Application.

```
npx electron-builder
```

Where is my app?
Check the dist/ folder.
macOS: You will see Hand Puppets.dmg.
Windows: You will see Hand Puppets Setup.exe.

## Troubleshooting

1. Camera not starting (Green light off)?
   If running on macOS, you might need to reset permissions if you previously denied access.

```
tccutil reset Camera
```

2. "Address already in use" / App stuck on Loading?
   If the app crashed previously, a "Zombie" Python process might still be holding the camera or port 5050. Kill it:

```
killall handpuppets
```

# OR

```
killall Python
```

3. "File is Damaged" when sending to friends?
   Since the app isn't signed by Apple ($99/year), your friends might see a security warning. They need to run this command once after moving the app to their Applications folder:

```
xattr -cr /Applications/"handpuppets.app"
```
