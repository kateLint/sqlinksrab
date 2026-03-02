# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for HRM Timesheet Automation
This creates a standalone executable with all dependencies including Playwright browsers
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from playwright
playwright_datas = collect_data_files('playwright')

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
