#!/bin/bash
# ============================================
# HRM Timesheet Automation - Build Script
# Mac/Linux
# ============================================
# This script builds a standalone executable
# that includes everything: Python, Chrome,
# and all dependencies. No installation needed!
# ============================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  🔨 HRM Timesheet Automation - בנייה"
echo "=========================================="
echo ""

# ---- Step 1: Check Python ----
echo "[1/6] בודק Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 לא מותקן."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   התקן עם: brew install python3"
    else
        echo "   התקן עם: sudo apt-get install python3 python3-pip python3-venv"
    fi
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1)
echo "✅ $PYTHON_VERSION"
echo ""

# ---- Step 2: Create/activate venv ----
echo "[2/6] מכין סביבה וירטואלית..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   סביבה וירטואלית נוצרה"
fi
source venv/bin/activate
echo "✅ סביבה וירטואלית מופעלת"
echo ""

# ---- Step 3: Install dependencies ----
echo "[3/6] מתקין תלויות (עלול לקחת דקה)..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
echo "✅ תלויות הותקנו"
echo ""

# ---- Step 4: Install Playwright browsers ----
echo "[4/6] מוריד דפדפן Chrome (עלול לקחת כמה דקות)..."
playwright install chromium
echo "✅ דפדפן Chrome הותקן"
echo ""

# ---- Step 5: Build with PyInstaller ----
echo "[5/6] בונה אפליקציה (עלול לקחת דקה)..."
pyinstaller build_desktop.spec --clean --noconfirm --log-level WARN
echo "✅ אפליקציה נבנתה"
echo ""

# ---- Step 6: Copy Playwright browsers into dist ----
echo "[6/6] מעתיק דפדפן Chrome לתוך האפליקציה..."

# Find the Python version in the venv
PYTHON_VER=$(python3 -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")
PLAYWRIGHT_BROWSERS="venv/lib/$PYTHON_VER/site-packages/playwright/driver/package/.local-browsers"
DEST_BROWSERS="dist/HRM_Timesheet_Automation/_internal/playwright/driver/package/.local-browsers"

if [ -d "$PLAYWRIGHT_BROWSERS" ]; then
    # Remove partial copy (PyInstaller creates empty dirs)
    rm -rf "$DEST_BROWSERS"
    # Full copy of browsers
    cp -R "$PLAYWRIGHT_BROWSERS" "$DEST_BROWSERS"
    echo "✅ דפדפן Chrome הועתק בהצלחה"
else
    echo "⚠️  לא נמצא דפדפן Playwright ב-venv. הרץ: playwright install chromium"
    exit 1
fi
echo ""

# ---- Done! ----
echo "=========================================="
echo "  🎉 הבנייה הושלמה בהצלחה!"
echo "=========================================="
echo ""
echo "📁 האפליקציה נמצאת בתיקייה:"
echo "   dist/HRM_Timesheet_Automation/"
echo ""
echo "🚀 להפעלה:"
echo "   cd dist/HRM_Timesheet_Automation"
echo "   ./HRM_Timesheet_Automation"
echo ""
echo "🌐 המערכת תיפתח בדפדפן בכתובת:"
echo "   http://localhost:5001"
echo ""
