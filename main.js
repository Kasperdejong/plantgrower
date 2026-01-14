const { app, BrowserWindow, systemPreferences } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process'); 
const fs = require('fs');

// Debug Logger
const logPath = path.join(app.getPath('desktop'), 'debug_electron.txt');
function log(msg) {
    try { fs.appendFileSync(logPath, `[${new Date().toLocaleTimeString()}] ${msg}\n`); } catch (e) {}
}
try { fs.writeFileSync(logPath, "--- APP STARTING ---\n"); } catch(e) {}

process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';
app.commandLine.appendSwitch('ignore-certificate-errors');

let mainWindow;
let pythonProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    title: "Hand Puppets",
    fullscreen: true, 
    autoHideMenuBar: true,
    backgroundColor: '#111111',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      backgroundThrottling: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'templates', 'loading.html'));

  const startUrl = 'https://127.0.0.1:5050'; 

  const loadWindow = () => {
    fetch(startUrl)
      .then(() => {
        log("✅ Server responded! Switching screen...");
        mainWindow.loadURL(startUrl);
      })
      .catch((err) => {
        setTimeout(loadWindow, 1000); 
      });
  };

  loadWindow();

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

// ask for camera permission
async function checkPermissionsAndStart() {
  if (process.platform === 'darwin') {
    log("Checking Camera Permissions...");
    const status = systemPreferences.getMediaAccessStatus('camera');
    log(`Current Status: ${status}`);

    if (status !== 'granted') {
      log("Requesting Access...");
      const success = await systemPreferences.askForMediaAccess('camera');
      log(`Request result: ${success}`);
    }
  }
  startPython();
  createWindow();
}

function startPython() {
  let script;
  let options = {};
  
  if (app.isPackaged) {
    script = path.join(process.resourcesPath, 'handpuppets');
    if (fs.existsSync(script)) {
        try { fs.chmodSync(script, '755'); } catch (e) {}
    }
    options = { cwd: path.dirname(script), stdio: 'ignore' };
  } else {
    const pythonExec = path.join(__dirname, 'venv', 'bin', 'python');
    script = path.join(__dirname, 'handpuppets.py');
    options = { cwd: __dirname, stdio: 'pipe' };
  }

  log("Spawning Python...");
  try {
      pythonProcess = spawn(app.isPackaged ? script : path.join(__dirname, 'venv', 'bin', 'python'), app.isPackaged ? [] : ['-u', script], options);
      log(`Process Spawned. PID: ${pythonProcess ? pythonProcess.pid : 'FAIL'}`);
  } catch (e) {
      log(`Spawn Error: ${e.message}`);
  }
}

function killPython() {
  if (pythonProcess) {
    try { pythonProcess.kill('SIGKILL'); } catch (e) {}
    pythonProcess = null;
  }
  if (process.platform === 'darwin') {
      try { execSync('killall -9 handpuppets'); } catch (e) {}
  }
}

app.on('ready', () => {
  // Use the new permission check instead of starting immediately
  checkPermissionsAndStart();
});

app.on('before-quit', () => killPython());
app.on('window-all-closed', () => {
  killPython();
  app.quit();
});