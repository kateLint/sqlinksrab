@echo off
REM ============================================
REM HRM Timesheet Automation - Build Script
REM Windows
REM ============================================
REM This script builds a standalone executable
REM that includes everything: Python, Chrome,
REM and all dependencies. No installation needed!
REM ============================================

echo.
echo ==========================================
echo   HRM Timesheet Automation - בנייה
echo ==========================================
echo.

REM ---- Step 1: Check Python ----
echo [1/6] בודק Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python לא מותקן.
    echo    הורד מ: https://www.python.org/downloads/
    echo    וודא לסמן "Add Python to PATH"
    pause
    exit /b 1
)
python --version
echo.

REM ---- Step 2: Create/activate venv ----
echo [2/6] מכין סביבה וירטואלית...
if not exist "venv" (
    python -m venv venv
    echo    סביבה וירטואלית נוצרה
)
call venv\Scripts\activate.bat
echo [OK] סביבה וירטואלית מופעלת
echo.

REM ---- Step 3: Install dependencies ----
echo [3/6] מתקין תלויות (עלול לקחת דקה)...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [X] התקנת תלויות נכשלה
    pause
    exit /b 1
)
echo [OK] תלויות הותקנו
echo.

REM ---- Step 4: Install Playwright browsers ----
echo [4/6] מוריד דפדפן Chrome (עלול לקחת כמה דקות)...
playwright install chromium
if errorlevel 1 (
    echo [X] הורדת דפדפן נכשלה
    pause
    exit /b 1
)
echo [OK] דפדפן Chrome הותקן
echo.

REM ---- Step 5: Build with PyInstaller ----
echo [5/6] בונה אפליקציה (עלול לקחת דקה)...
pyinstaller build_desktop.spec --clean --noconfirm --log-level WARN
if errorlevel 1 (
    echo [X] הבנייה נכשלה
    pause
    exit /b 1
)
echo [OK] אפליקציה נבנתה
echo.

REM ---- Step 6: Copy Playwright browsers into dist ----
echo [6/6] מעתיק דפדפן Chrome לתוך האפליקציה...

REM Find playwright browsers path
for /f "delims=" %%i in ('python -c "import playwright; import os; print(os.path.join(os.path.dirname(playwright.__file__), 'driver', 'package', '.local-browsers'))"') do set BROWSERS_SRC=%%i

set BROWSERS_DEST=dist\HRM_Timesheet_Automation\_internal\playwright\driver\package\.local-browsers

if exist "%BROWSERS_SRC%" (
    if exist "%BROWSERS_DEST%" rmdir /s /q "%BROWSERS_DEST%"
    xcopy "%BROWSERS_SRC%" "%BROWSERS_DEST%" /E /I /Q /Y >nul 2>&1
    echo [OK] דפדפן Chrome הועתק בהצלחה
) else (
    echo [WARNING] לא נמצא דפדפן Playwright. הרץ: playwright install chromium
    pause
    exit /b 1
)
echo.

REM ---- Done! ----
echo ==========================================
echo   הבנייה הושלמה בהצלחה!
echo ==========================================
echo.
echo האפליקציה נמצאת בתיקייה:
echo    dist\HRM_Timesheet_Automation\
echo.
echo להפעלה:
echo    cd dist\HRM_Timesheet_Automation
echo    HRM_Timesheet_Automation.exe
echo.
echo המערכת תיפתח בדפדפן בכתובת:
echo    http://localhost:5001
echo.
pause
