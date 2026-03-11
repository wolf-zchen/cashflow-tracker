# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Cashflow Tracker
# Build with: pyinstaller CashflowTracker.spec

import os

block_cipher = None

a = Analysis(
    ['cashflow_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        # Bundle the src package
        ('src', 'src'),
        # Bundle data folder (contains learned_rules.json, category_mappings.json)
        # NOTE: transactions.db is user data — it will be created fresh on first run
        ('data/learned_rules.json', 'data'),
        ('data/category_mappings.json', 'data'),
    ],
    hiddenimports=[
        'src.parsers.monarch_parser',
        'src.parsers.chase_credit_parser',
        'src.parsers.chase_checking_parser',
        'src.parsers.amex_parser',
        'src.parsers.amex_csv_parser',
        'src.parsers.bofa_parser',
        'src.database.db_manager',
        'src.categorization',
        'src.category_mapper',
        'src.duplicate_detection',
        'src.learned_rules',
        'src.models',
        'pandas',
        'openpyxl',
        'dateutil',
        'dateutil.parser',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',   # not used in the GUI app
        'scipy',
        'sklearn',
        'IPython',
        'jupyter',
    ],
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
    name='Cashflow Tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # No terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cashflow Tracker',
)

app = BUNDLE(
    coll,
    name='Cashflow Tracker.app',
    icon=None,           # Replace with 'icon.icns' if you have one
    bundle_identifier='com.yourname.cashflowtracker',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1',
        'NSRequiresAquaSystemAppearance': False,  # Supports dark mode
    },
)
