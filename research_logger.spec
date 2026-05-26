# research_logger.spec
# PyInstaller build spec for Research Logger
# Build with:  pyinstaller research_logger.spec

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect PySide6 data (plugins, translations, etc.)
pyside6_datas = collect_data_files('PySide6', includes=['*.dll', '*.so', '*.pyd'])

# Project root
project_root = os.path.abspath('.')

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        # Stylesheets
        (os.path.join(project_root, 'styles.qss'),       '.'),
        (os.path.join(project_root, 'styles_dark.qss'),  '.'),
    ],
    hiddenimports=[
        # PySide6 core modules
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSql',
        'PySide6.QtNetwork',
        # WebEngine (optional — imported with try/except in editor_panel.py)
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebChannel',
        # Standard lib modules sometimes missed
        'sqlite3',
        '_sqlite3',
        'json',
        'math',
        'calendar',
        're',
        'collections',
        'datetime',
        'pathlib',
        'shutil',
        # Third-party
        'reportlab',
        'reportlab.platypus',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.lib.enums',
        'markdown2',
        # Ensure Pillow (PIL) is bundled for ReportLab image support
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
        'cv2',
        'torch',
        'tensorflow',
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
    name='ResearchLogger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',      # Uncomment and add icon.ico to use a custom icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ResearchLogger',
)
