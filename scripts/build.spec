# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ========================================================
# 1. НАСТРОЙКА ПУТЕЙ (ИСПРАВЛЕНО)
# ========================================================

# PyInstaller добавляет переменную SPECPATH, указывающую на папку со скриптом
# Если вдруг её нет (старая версия), берем текущую директорию
try:
    SCRIPT_DIR = SPECPATH
except NameError:
    SCRIPT_DIR = os.getcwd()

# Корень проекта - это папка на уровень выше папки scripts
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

# Абсолютные пути к файлам
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'src', 'main.py')
RESOURCES_DIR = os.path.join(PROJECT_ROOT, 'resources')
MODEL_FILE = os.path.join(RESOURCES_DIR, 'best.pt')

print(f"--- BUILD CONFIG ---")
print(f"Spec Directory: {SCRIPT_DIR}")
print(f"Project Root:   {PROJECT_ROOT}")
print(f"Main Script:    {MAIN_SCRIPT}")
print(f"Resources:      {RESOURCES_DIR}")
print(f"--------------------")

# ========================================================
# 2. СБОР ДАННЫХ
# ========================================================

# (source, dest)
datas = [
    (RESOURCES_DIR, 'resources'),
    (MODEL_FILE, '.'),
]

datas += collect_data_files('ultralytics')

# ========================================================
# 3. ИМПОРТЫ
# ========================================================

hiddenimports = [
    'PySide6',
    'cv2',
    'numpy',
    'ultralytics',
    'PIL',
    'shutil'
]
hiddenimports += collect_submodules('ultralytics')

# ========================================================
# 4. СБОРКА
# ========================================================

a = Analysis(
    [MAIN_SCRIPT],
    # Добавляем корень и src в PYTHONPATH сборки
    pathex=[PROJECT_ROOT, os.path.join(PROJECT_ROOT, 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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

# ========================================================
# 5. EXE
# ========================================================

# Иконка
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
    strip=False,
    upx=True,
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
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform.startswith('darwin'):
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=icon_file,
        bundle_identifier='com.morris.tracking',
    )