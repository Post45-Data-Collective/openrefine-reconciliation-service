#!/bin/bash
# Simplified build using a clean venv instead of conda

set -e

echo "🔨 Building BookReconciler Electron App (Clean Build)"
echo ""

# Step 1: Create clean venv
echo "🐍 Creating clean Python environment..."
cd ..
rm -rf .build-venv
python3 -m venv .build-venv
source .build-venv/bin/activate

# Install only what we need
echo "📦 Installing requirements..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet

# Step 2: Build with PyInstaller
echo "🔧 Building Python executable..."
pyinstaller electron/app-electron.spec --distpath electron/python-dist --clean

deactivate
cd electron

# Step 3: Copy icon
echo "🎨 Copying icon..."
if [ -f "icon.icns" ]; then
    echo "✅ Icon found"
else
    echo "⚠️  Icon not found, using default"
fi

# Step 4: Install npm deps
echo "📦 Installing Node dependencies..."
npm install

# Step 5: Build Electron app
echo "⚡ Building Electron app..."
npm run build:mac

echo ""
echo "✅ Build complete!"
echo "📂 Output: electron/dist/"
ls -lh dist/ | grep -E "\.dmg|\.zip"
