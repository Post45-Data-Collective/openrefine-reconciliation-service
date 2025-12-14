#!/bin/bash
# Build script for BookReconciler Electron app

set -e  # Exit on error

echo "🔨 Building BookReconciler Electron App"
echo ""

# Check if we're in the electron directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from electron/ directory"
    exit 1
fi

# Step 1: Install Node dependencies
echo "📦 Installing Node dependencies..."
npm install

# Step 2: Copy icon
echo "🎨 Copying icon..."
if [ -f "../images/BookReconcilerAppLogo.icns" ]; then
    cp ../images/BookReconcilerAppLogo.icns icon.icns
    echo "✅ Icon copied"
else
    echo "⚠️  Warning: Icon not found at ../images/BookReconcilerAppLogo.icns"
fi

# Step 3: Build Python executable
echo ""
echo "🐍 Building Python executable with PyInstaller..."
echo "This may take a few minutes..."

cd ..
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
rm -rf electron/python-dist

# Build
pyinstaller electron/app-electron.spec --distpath electron/python-dist --clean

cd electron

# Check if build succeeded
if [ ! -d "python-dist/app" ]; then
    echo "❌ Error: Python build failed"
    exit 1
fi

echo "✅ Python executable built successfully"

# Step 4: Build Electron app
echo ""
echo "⚡ Building Electron app..."

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Building for macOS..."
    npm run build:mac
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "Building for Windows..."
    npm run build:win
else
    echo "Unknown platform, building for current platform..."
    npm run build
fi

echo ""
echo "✅ Build complete!"
echo ""
echo "📂 Output files are in: dist/"
ls -lh dist/
