# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

try:
    SCRIPT_DIR = SPECPATH
except NameError:
    SCRIPT_DIR = os.getcwd()

PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'src', 'main.py')
RESOURCES_DIR = os.path.join(PROJECT_ROOT, 'resources')
MODEL_FILE = os.path.join(RESOURCES_DIR, 'best.onnx')

print(f"--- BUILD CONFIG ---")
print(f"Spec Directory: {SCRIPT_DIR}")
print(f"Project Root:   {PROJECT_ROOT}")
print(f"Main Script:    {MAIN_SCRIPT}")
print(f"Resources:      {RESOURCES_DIR}")
print(f"Model:          {MODEL_FILE}")
print(f"--------------------")

datas = [
    (RESOURCES_DIR, 'resources'),
    (MODEL_FILE, '.'),
]

hiddenimports = [
    'PySide6',
    'cv2',
    'numpy',
    'PIL',
    'shutil',
    'onnxruntime',
    'yaml'
]

excludes = [
    'torch',
    'torchvision',
    'ultralytics',
    'matplotlib',
    'scipy',
    'pandas',
    'seaborn',
    'plotly',
    'Pillow',
    'ipython',
    'jupyter',
    'notebook',
    'pytest',
    'pytest-qt',
    'ipdb',
    'debugpy',
    'twisted',
    'pyyaml',
    'requests',
    'urllib3',
    'certifi',
    'charset-normalizer',
    'idna'
]

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_file = None
if sys.platform.startswith('win'):
    icon_check = os.path.join(RESOURCES_DIR, 'icon.ico')
    if os.path.exists(icon_check): icon_file = icon_check
elif sys.platform.startswith('darwin'):
    icon_check = os.path.join(RESOURCES_DIR, 'icon.icns')
    if os.path.exists(icon_check): icon_file = icon_check

APP_NAME = 'Morris'

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=['*'],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=['*'],
    name=APP_NAME,
)

if sys.platform.startswith('darwin'):
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=icon_file,
        bundle_identifier='com.morris.tracking',
    )
