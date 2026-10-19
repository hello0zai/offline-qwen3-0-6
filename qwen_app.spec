# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
project_root = Path.cwd()

# Gather required Transformers dependencies and metadata
datas = [
    (str(project_root / 'model_weights'), 'model_weights'),
]
datas += collect_data_files('transformers')
datas += collect_data_files('torch')

hidden_imports = [
    'transformers',
    'torch',
    'accelerate',
    'safetensors',
] + collect_submodules('transformers.models.qwen3')

a = Analysis(
    ['app/main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'tensorboard'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --onedir mode is strongly recommended for ~1.5GB+ model/runtime bundles to eliminate long startup decompression times.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QwenApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
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
    upx=False,
    upx_exclude=[],
    name='QwenApp'
)