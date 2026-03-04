# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for HRM Timesheet Automation
This creates a standalone executable with all dependencies including Playwright browsers
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from playwright, including browsers which are required for it to run
raw_playwright_datas = collect_data_files('playwright')
playwright_datas = raw_playwright_datas

# Collect all submodules
hidden_imports = [
    'playwright',
    'playwright.sync_api',
    'flask',
    'pdfplumber',
    'python-dotenv',
    'werkzeug',
    'src.pdf_extractor',
    'src.portal_client',
    'src.config',
    'src.email_sender',
    'src.reporting',
]

a = Analysis(
    ['web_server.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('web/templates', 'web/templates'),
        ('web/static', 'web/static'),
        ('config.example.json', '.'),
        ('.env.example', '.'),
    ] + playwright_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries = [b for b in a.binaries if '.local-browsers' not in b[0] and '.local-browsers' not in b[1]]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HRM_Timesheet_Automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to False for GUI-only mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='web/static/favicon.ico' if sys.platform == 'win32' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HRM_Timesheet_Automation',
)

# Append raw playwright browser tree if exists
import os, playwright
from PyInstaller.building.datastruct import Tree
playwright_path = os.path.dirname(playwright.__file__)
local_browsers_path = os.path.join(playwright_path, 'driver', 'package', '.local-browsers')
if os.path.exists(local_browsers_path):
    coll.dependencies.append(Tree(local_browsers_path, prefix='playwright/driver/package/.local-browsers'))

