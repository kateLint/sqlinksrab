@echo off
REM Installation script for HRM Timesheet Automation - Windows
REM This script installs all dependencies and sets up the application

echo ========================================
echo HRM Timesheet Automation - התקנה
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [שגיאה] Python לא מותקן במערכת
    echo אנא הורד והתקן Python מ: https://www.python.org/downloads/
    echo וודא לסמן "Add Python to PATH" בהתקנה
    pause
    exit /b 1
)

echo [✓] Python מותקן
echo.

REM Create virtual environment
echo [1/5] יוצר סביבה וירטואלית...
python -m venv venv
if errorlevel 1 (
    echo [שגיאה] יצירת סביבה וירטואלית נכשלה
    pause
    exit /b 1
)
echo [✓] סביבה וירטואלית נוצרה
echo.

REM Activate virtual environment
echo [2/5] מפעיל סביבה וירטואלית...
call venv\Scripts\activate.bat
echo [✓] סביבה וירטואלית הופעלה
echo.

REM Upgrade pip
echo [3/5] מעדכן pip...
python -m pip install --upgrade pip --quiet
echo [✓] pip עודכן
echo.

REM Install requirements
echo [4/5] מתקין תלויות (זה עלול לקחת מספר דקות)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [שגיאה] התקנת תלויות נכשלה
    pause
    exit /b 1
)
echo [✓] תלויות הותקנו
echo.

REM Install Playwright browsers
echo [5/5] מוריד דפדפנים (זה עלול לקחת מספר דקות)...
playwright install chromium
if errorlevel 1 (
    echo [שגיאה] הורדת דפדפנים נכשלה
    pause
    exit /b 1
)
echo [✓] דפדפנים הותקנו
echo.

REM Create config file if doesn't exist
if not exist config.json (
    echo [*] יוצר קובץ הגדרות...
    copy config.example.json config.json >nul
    echo [✓] קובץ הגדרות נוצר
    echo.
)

REM Create .env file if doesn't exist
if not exist .env (
    echo [*] יוצר קובץ משתני סביבה...
    copy .env.example .env >nul
    echo [✓] קובץ משתני סביבה נוצר
    echo.
)

REM Create desktop shortcut
echo [*] יוצר קיצור דרך...
echo @echo off > "הפעל מערכת נוכחות.bat"
echo cd /d "%~dp0" >> "הפעל מערכת נוכחות.bat"
echo call venv\Scripts\activate.bat >> "הפעל מערכת נוכחות.bat"
echo python web_server.py >> "הפעל מערכת נוכחות.bat"
echo pause >> "הפעל מערכת נוכחות.bat"
echo [✓] קיצור דרך נוצר
echo.

echo ========================================
echo ההתקנה הושלמה בהצלחה! 🎉
echo ========================================
echo.
echo להפעלת המערכת, לחץ פעמיים על:
echo "הפעל מערכת נוכחות.bat"
echo.
echo או הרץ את הפקודה:
echo   venv\Scripts\activate.bat
echo   python web_server.py
echo.
echo המערכת תיפתח בדפדפן בכתובת:
echo   http://localhost:5001
echo.
pause
