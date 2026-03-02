#!/bin/bash
# Installation script for HRM Timesheet Automation - Mac/Linux
# This script installs all dependencies and sets up the application

set -e  # Exit on error

echo "========================================"
echo "HRM Timesheet Automation - התקנה"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[שגיאה] Python 3 לא מותקן במערכת"
    echo "אנא התקן Python 3:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  brew install python3"
    else
        echo "  sudo apt-get install python3 python3-pip python3-venv"
    fi
    exit 1
fi

echo "[✓] Python מותקן"
echo ""

# Create virtual environment
echo "[1/5] יוצר סביבה וירטואלית..."
python3 -m venv venv
echo "[✓] סביבה וירטואלית נוצרה"
echo ""

# Activate virtual environment
echo "[2/5] מפעיל סביבה וירטואלית..."
source venv/bin/activate
echo "[✓] סביבה וירטואלית הופעלה"
echo ""

# Upgrade pip
echo "[3/5] מעדכן pip..."
pip install --upgrade pip --quiet
echo "[✓] pip עודכן"
echo ""

# Install requirements
echo "[4/5] מתקין תלויות (זה עלול לקחת מספר דקות)..."
pip install -r requirements.txt --quiet
echo "[✓] תלויות הותקנו"
echo ""

# Install Playwright browsers
echo "[5/5] מוריד דפדפנים (זה עלול לקחת מספר דקות)..."
playwright install chromium
echo "[✓] דפדפנים הותקנו"
echo ""

# Create config file if doesn't exist
if [ ! -f config.json ]; then
    echo "[*] יוצר קובץ הגדרות..."
    cp config.example.json config.json
    echo "[✓] קובץ הגדרות נוצר"
    echo ""
fi

# Create .env file if doesn't exist
if [ ! -f .env ]; then
    echo "[*] יוצר קובץ משתני סביבה..."
    cp .env.example .env
    echo "[✓] קובץ משתני סביבה נוצר"
    echo ""
fi

# Create run script
echo "[*] יוצר סקריפט הפעלה..."
cat > run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python web_server.py
EOF
chmod +x run.sh
echo "[✓] סקריפט הפעלה נוצר"
echo ""

echo "========================================"
echo "ההתקנה הושלמה בהצלחה! 🎉"
echo "========================================"
echo ""
echo "להפעלת המערכת, הרץ:"
echo "  ./run.sh"
echo ""
echo "או:"
echo "  source venv/bin/activate"
echo "  python web_server.py"
echo ""
echo "המערכת תיפתח בדפדפן בכתובת:"
echo "  http://localhost:5001"
echo ""
