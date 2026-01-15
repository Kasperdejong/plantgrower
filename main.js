const { app, BrowserWindow, systemPreferences } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process'); 
const fs = require('fs');

// Debug Logger
const logPath = path.join(app.getPath('desktop'), 'debug_plantgrower.txt');
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
    width: 1280,
    height: 720,
    title: "AR Plant Grower",
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

  // Note: plantgrower.py runs on port 5050 in the updated code
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
    // Path: Resources/plantgrower/plantgrower (folder/executable)
    script = path.join(process.resourcesPath, 'plantgrower', 'plantgrower');
    
    // Fallback: If for some reason it's just a file (like in your old project)
    if (!fs.existsSync(script)) {
        script = path.join(process.resourcesPath, 'plantgrower');
    }

    if (fs.existsSync(script)) {
        try { fs.chmodSync(script, '755'); } catch (e) {}
    }
    options = { cwd: path.dirname(script), stdio: 'ignore' };
  } else {
    // Development mode
    script = path.join(__dirname, 'plantgrower.py');
    options = { cwd: __dirname, stdio: 'pipe' };
  }

  log(`Spawning Python: ${script}`);
  try {
      // If packaged, we run the file directly. If dev, we use python3 to run the .py file
      const cmd = app.isPackaged ? script : 'python3';
      const args = app.isPackaged ? [] : ['-u', script];
      
      pythonProcess = spawn(cmd, args, options);
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
      try { execSync('killall -9 plantgrower'); } catch (e) {}
  }
}

app.on('ready', () => {
  checkPermissionsAndStart();
});

app.on('before-quit', () => killPython());
app.on('window-all-closed', () => {
  killPython();
  app.quit();
});