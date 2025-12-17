const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  // Another instance is already running, quit this one
  app.quit();
} else {
  // This is the first instance
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Someone tried to run a second instance, focus the existing window
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

let mainWindow;
let flaskProcess;
const PORT = 5001;
const BASE_URL = `http://127.0.0.1:${PORT}`;

// Determine the path to the Python executable
function getPythonPath() {
  if (app.isPackaged) {
    // In production, use bundled Python
    const platform = process.platform;
    if (platform === 'darwin') {
      return path.join(process.resourcesPath, 'python-dist', 'app', 'app');
    } else if (platform === 'win32') {
      return path.join(process.resourcesPath, 'python-dist', 'app', 'app.exe');
    }
  } else {
    // In development, use system Python with Flask
    return 'python3';
  }
}

// Start the Flask server
function startFlaskServer() {
  return new Promise((resolve, reject) => {
    const pythonPath = getPythonPath();

    let serverProcess;
    if (app.isPackaged) {
      // Run the bundled executable - set cwd to the directory containing the executable
      // so PyInstaller can find the _internal directory with bundled resources
      const pythonDir = path.dirname(pythonPath);
      serverProcess = spawn(pythonPath, [], {
        cwd: pythonDir,
        env: {
          ...process.env,
          PORT: PORT.toString(),
          RUNNING_IN_ELECTRON: 'true'
        }
      });
    } else {
      // Run Flask in development mode
      const appPath = path.join(__dirname, '..', 'app.py');
      serverProcess = spawn(pythonPath, [appPath], {
        env: {
          ...process.env,
          FLASK_APP: appPath,
          PORT: PORT.toString(),
          RUNNING_IN_ELECTRON: 'true'
        },
        cwd: path.join(__dirname, '..')
      });
    }

    flaskProcess = serverProcess;

    let errorOutput = '';

    serverProcess.stdout.on('data', (data) => {
      console.log(`Flask: ${data}`);
      // Look for Flask startup message
      if (data.toString().includes('Running on') || data.toString().includes('WARNING')) {
        setTimeout(() => resolve(), 2000); // Give it 2 seconds to fully start
      }
    });

    serverProcess.stderr.on('data', (data) => {
      const errorText = data.toString();
      console.error(`Flask Error: ${errorText}`);
      errorOutput += errorText;
    });

    serverProcess.on('error', (error) => {
      console.error(`Failed to start Flask: ${error}`);
      errorOutput += `\nProcess error: ${error}`;
      reject(error);
    });

    serverProcess.on('close', (code) => {
      console.log(`Flask process exited with code ${code}`);
      if (code !== 0 && errorOutput) {
        global.flaskStartupError = errorOutput;
      }
    });

    // If we don't get a startup message within 10 seconds, assume it's ready
    setTimeout(() => resolve(), 10000);
  });
}

// Check if server is ready
async function waitForServer(maxAttempts = 30) {
  const http = require('http');

  for (let i = 0; i < maxAttempts; i++) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(BASE_URL, (res) => {
          resolve();
        });
        req.on('error', reject);
        req.setTimeout(1000, () => {
          req.destroy();
          reject(new Error('Timeout'));
        });
      });
      return true;
    } catch (error) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  return false;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: path.join(__dirname, process.platform === 'darwin' ? 'icon.icns' : 'icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Load a loading page initially
  mainWindow.loadURL(`data:text/html,<html><body style="background:#f0f0f0;display:flex;align-items:center;justify-content:center;font-family:sans-serif;"><div style="text-align:center;"><h1>📘 BookReconciler</h1><p>Starting server...</p></div></body></html>`);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  try {
    // Start Flask server
    console.log('Starting Flask server...');
    await startFlaskServer();

    // Wait for server to be ready
    console.log('Waiting for server to be ready...');
    const serverReady = await waitForServer();

    if (!serverReady) {
      const errorDetails = global.flaskStartupError
        ? `\n\nError details:\n${global.flaskStartupError.substring(0, 500)}`
        : '\n\nNo error details available. Try running from Terminal to see logs.';
      dialog.showErrorBox('Server Error', `Failed to start BookReconciler server. Please try again.${errorDetails}`);
      app.quit();
      return;
    }

    // Open in default browser instead of Electron window
    const { shell } = require('electron');
    await shell.openExternal(BASE_URL);

    // Show a notification window
    const notifWindow = new BrowserWindow({
      width: 550,
      height: 650,
      resizable: true,
      minimizable: true,
      maximizable: true,
      alwaysOnTop: false,
      frame: true,
      title: 'BookReconciler Control Panel',
      icon: path.join(__dirname, process.platform === 'darwin' ? 'icon.icns' : 'icon.ico')
    });

    notifWindow.loadFile(path.join(__dirname, 'notification.html'));

    // Prevent closing without confirmation
    notifWindow.on('close', (e) => {
      const choice = dialog.showMessageBoxSync(notifWindow, {
        type: 'question',
        buttons: ['Cancel', 'Stop Server'],
        title: 'Stop BookReconciler?',
        message: 'Are you sure you want to stop BookReconciler?',
        detail: 'This will shut down the server and end your reconciliation session.',
        defaultId: 0,
        cancelId: 0
      });

      if (choice === 0) {
        // User clicked Cancel
        e.preventDefault();
      }
      // If choice === 1 (Stop Server), allow the window to close
    });

    notifWindow.on('closed', () => {
      app.quit();
    });

    // Auto-minimize window after 2 seconds
    setTimeout(() => {
      notifWindow.minimize();
    }, 2000);

    mainWindow = notifWindow;

  } catch (error) {
    console.error('Error starting application:', error);
    dialog.showErrorBox('Startup Error', `Failed to start BookReconciler: ${error.message}`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('quit', () => {
  // Kill Flask process when app quits
  if (flaskProcess) {
    flaskProcess.kill();
  }
});

// Handle cleanup on various exit signals
process.on('exit', () => {
  if (flaskProcess) {
    flaskProcess.kill();
  }
});

process.on('SIGINT', () => {
  app.quit();
});

process.on('SIGTERM', () => {
  app.quit();
});
