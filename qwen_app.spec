# build.spec
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

torch_datas, torch_binaries, torch_hidden = collect_all("torch")
transformers_datas, transformers_binaries, transformers_hidden = collect_all("transformers")
rapidocr_datas, rapidocr_binaries, rapidocr_hidden = collect_all("rapidocr")
onnx_datas, onnx_binaries, onnx_hidden = collect_all("onnxruntime")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=torch_binaries + transformers_binaries + rapidocr_binaries + onnx_binaries,
    datas=[
        # Include the whole pre-downloaded model folder
        ("models/Qwen3-0.6B", "models/Qwen3-0.6B"),
    ] + torch_datas + transformers_datas + rapidocr_datas + onnx_datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "multipart",
        "PIL",
        "numpy",
        "cv2",
        "onnxruntime",
        "rapidocr",
        "transformers",
        "torch",
        "accelerate",
    ] + torch_hidden + transformers_hidden + rapidocr_hidden + onnx_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas", "IPython", "jupyter"],
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
    name="ocr-summarizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ocr-summarizer",
)