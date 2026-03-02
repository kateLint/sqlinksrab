# Building Desktop Executable

## Using PyInstaller

### Prerequisites

```bash
pip install pyinstaller
```

### Build Commands

**Windows:**
```bash
pyinstaller build_desktop.spec
```

**Mac:**
```bash
pyinstaller build_desktop.spec
```

**Linux:**
```bash
pyinstaller build_desktop.spec
```

### Output

The executable will be in `dist/HRM_Timesheet_Automation/`

### Distribution

**Windows:**
1. Zip the entire `dist/HRM_Timesheet_Automation` folder
2. Share the zip file
3. Users extract and run `HRM_Timesheet_Automation.exe`

**Mac:**
1. Create a DMG (optional):
   ```bash
   hdiutil create -volname "HRM Timesheet" -srcfolder dist/HRM_Timesheet_Automation -ov -format UDZO hrm_timesheet.dmg
   ```
2. Share the DMG file

**Linux:**
1. Create a tar.gz:
   ```bash
   cd dist
   tar -czf HRM_Timesheet_Automation.tar.gz HRM_Timesheet_Automation/
   ```
2. Share the tar.gz file

---

## File Size

The executable will be large (~200-400MB) because it includes:
- Python interpreter
- All libraries
- Playwright browsers
- Web templates and static files

This is normal for PyInstaller applications.

---

## Troubleshooting

### "Missing module" error

Add the module to `hiddenimports` in `build_desktop.spec`:

```python
hiddenimports=[
    'playwright',
    'your_missing_module',
],
```

### Antivirus blocks the exe

This is common with PyInstaller. Solutions:
1. Add exception in antivirus
2. Sign the executable (requires code signing certificate)
3. Distribute source code instead

### Playwright browsers not included

Make sure Playwright data files are collected:

```python
playwright_datas = collect_data_files('playwright')
datas=[...] + playwright_datas
```

---

## Alternative: Nuitka

Nuitka creates faster executables:

```bash
pip install nuitka
python -m nuitka --standalone --onefile web_server.py
```

Pros:
- Faster execution
- Smaller file size

Cons:
- Longer build time
- More complex configuration

---

## Alternative: cx_Freeze

Another option:

```bash
pip install cx_Freeze
cxfreeze web_server.py --target-dir dist
```

---

## Creating an Installer

### Windows (Inno Setup)

1. Download [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Create a script:

```iss
[Setup]
AppName=HRM Timesheet Automation
AppVersion=1.0
DefaultDirName={pf}\HRM Timesheet
DefaultGroupName=HRM Timesheet
OutputDir=installer
OutputBaseFilename=HRM_Timesheet_Setup

[Files]
Source: "dist\HRM_Timesheet_Automation\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\HRM Timesheet"; Filename: "{app}\HRM_Timesheet_Automation.exe"
```

3. Compile with Inno Setup

### Mac (create-dmg)

```bash
npm install -g create-dmg
create-dmg dist/HRM_Timesheet_Automation.app
```

---

## Best Practices

1. **Test on clean machine** - Make sure it works without Python installed
2. **Include README** - Add instructions in the dist folder
3. **Version your builds** - Use version numbers in filenames
4. **Sign your code** - For better security and trust
5. **Provide checksums** - SHA256 hash for verification

---

## Continuous Building

Use GitHub Actions to build automatically:

```yaml
name: Build Executables

on: [push]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]
    
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    - run: pip install -r requirements.txt
    - run: pyinstaller build_desktop.spec
    - uses: actions/upload-artifact@v2
      with:
        name: executable-${{ matrix.os }}
        path: dist/
```
