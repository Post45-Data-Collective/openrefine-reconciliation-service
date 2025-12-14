# Quick Start Guide - Electron App

## First Time Setup

### 1. Copy the icon

```bash
cp ../images/BookReconcilerAppLogo.icns icon.icns
```

If you're building for Windows, you'll also need to convert the icon to `.ico` format. You can use an online converter or ImageMagick:

```bash
# Using ImageMagick (install with: brew install imagemagick)
convert ../images/BookReconcilerAppLogo.icns -resize 256x256 icon.ico
```

Or just use the macOS icon for now - Electron will handle it.

### 2. Install dependencies

```bash
npm install
```

## Testing in Development

To test the app without building:

```bash
npm start
```

This will:
- Start your Flask app using your local Python installation
- Open an Electron window
- Point to http://127.0.0.1:5001

**Note:** Make sure you have all Python dependencies installed:
```bash
cd ..
pip install -r requirements.txt
cd electron
```

## Building for Distribution

The automated build script handles everything:

```bash
./build.sh
```

This will:
1. Install npm dependencies
2. Copy the icon
3. Build the Python executable with PyInstaller
4. Package everything into an Electron app
5. Create distributable files in `dist/`

### Manual Build Steps

If you prefer to build manually:

#### Step 1: Build Python executable

```bash
cd ..  # Go to project root
pip install pyinstaller
pyinstaller electron/app-electron.spec --distpath electron/python-dist --clean
cd electron
```

#### Step 2: Build Electron app

**For Mac:**
```bash
npm run build:mac
```

**For Windows:**
```bash
npm run build:win
```

**For both:**
```bash
npm run build:all
```

## Output Files

After building, you'll find in `dist/`:

### macOS
- `BookReconciler-0.2.0.dmg` - Drag-and-drop installer
- `BookReconciler-0.2.0-mac.zip` - Portable zip

### Windows
- `BookReconciler Setup 0.2.0.exe` - Installer
- `BookReconciler-0.2.0-win.zip` - Portable zip

## Troubleshooting

### "Python executable not found"

Make sure you've run the PyInstaller build:
```bash
cd ..
pyinstaller electron/app-electron.spec --distpath electron/python-dist
cd electron
```

### "Port 5001 already in use"

Kill any existing Flask servers:
```bash
lsof -ti:5001 | xargs kill -9
```

### Icon not showing

Make sure you've copied the icon file:
```bash
ls -l icon.icns  # Should exist
```

### Build fails on Windows

Make sure you have Visual C++ Build Tools installed. You may also need to install PyInstaller dependencies for Windows.

## File Size

The built apps include Python + Flask + all dependencies, so they're relatively large:
- macOS: ~150-200 MB
- Windows: ~100-150 MB

This is normal for bundled Python apps.
