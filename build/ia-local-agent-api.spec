# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


block_cipher = None
project_root = os.path.abspath(os.path.join(SPECPATH, ".."))


def optional_submodules(package):
    try:
        return collect_submodules(package)
    except Exception:
        return []


def optional_datas(package):
    try:
        return collect_data_files(package)
    except Exception:
        return []


hiddenimports = []
for package in (
    "chromadb",
    "fastapi",
    "openai",
    "pydantic",
    "pypdf",
    "sentence_transformers",
    "tokenizers",
    "uvicorn",
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
    "watchfiles",
    "websockets",
):
    hiddenimports += optional_submodules(package)


datas = []
for package in ("chromadb", "sentence_transformers", "tokenizers"):
    datas += optional_datas(package)


a = Analysis(
    [os.path.join(project_root, "src", "api", "desktop_entry.py")],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "tests",
        "tkinter",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ia-local-agent-api",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
