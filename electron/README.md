# BookReconciler Electron App

This is a standalone Electron app that bundles the BookReconciler Flask server into a native desktop application.

## Features

- No Docker required
- No Python installation required
- Native Mac and Windows app
- One-click launch
- Includes custom icon
- Auto-starts Flask server in background

## Development

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+
- PyInstaller

### Setup

1. Install Node dependencies:
```bash
cd electron
npm install
```

2. Build the Python executable (this bundles Flask + all dependencies):

**For Mac:**
```bash
cd ..  # Back to project root
pip install pyinstaller
pyinstaller electron/app-electron.spec --distpath electron/python-dist
```

**For Windows:**
```bash
cd ..
pip install pyinstaller
pyinstaller electron/app-electron.spec --distpath electron/python-dist
```

3. Copy the icon files:
```bash
# From the electron directory
cp ../images/BookReconcilerAppLogo.icns icon.icns
# For Windows, you'll need to convert to .ico format
```

### Run in Development

```bash
cd electron
npm start
```

This will:
1. Launch Electron
2. Start the Flask server (using your local Python environment)
3. Open the app window pointing to http://127.0.0.1:5001

### Build for Production

**Mac:**
```bash
npm run build:mac
```

This creates:
- `dist/BookReconciler-0.2.0.dmg` - DMG installer
- `dist/BookReconciler-0.2.0-mac.zip` - Zip archive

**Windows:**
```bash
npm run build:win
```

This creates:
- `dist/BookReconciler Setup 0.2.0.exe` - Windows installer
- `dist/BookReconciler-0.2.0-win.zip` - Zip archive

**Both platforms:**
```bash
npm run build:all
```

## Distribution

The built apps are self-contained and include:
- Electron runtime
- Bundled Python + Flask server
- All Python dependencies
- Templates, static files, and data
- Application icon

Users just download and run - no installation required (except for the Windows installer version).

## File Size

The bundled apps are approximately:
- Mac: ~150-200 MB
- Windows: ~100-150 MB

This is because they include Python and all dependencies.

## How It Works

1. User launches the Electron app
2. `main.js` spawns the bundled Python executable
3. The Python executable runs the Flask server on port 5001
4. Electron opens a browser window pointing to http://127.0.0.1:5001
5. When the user quits the app, Electron kills the Flask process
