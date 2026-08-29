# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir：无控制台，配置写在 exe 同目录。"""
import glob
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

ROOT = os.path.dirname(os.path.abspath(SPEC))
DIST = os.path.join(ROOT, "dist")
EXE_NAME = "TelegramViewOnce_1"
ICON = os.path.join(ROOT, "icon.ico")

_datas = []
_binaries = []
_hiddenimports = [
    "tg_service",
    "qrcode",
    "qrcode.image.pil",
    "PIL",
    "PIL.Image",
    "PIL.ImageGrab",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "certifi",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "shiboken6",
]
_hiddenimports += collect_submodules("telethon")
_datas += collect_data_files("certifi")
_datas.append((os.path.join(ROOT, "icon.ico"), "."))

try:
    import PySide6
    import shiboken6

    _datas += collect_data_files(
        "PySide6",
        includes=[
            "plugins/platforms/qwindows.*",
            "plugins/styles/*",
            "plugins/imageformats/*",
            "plugins/iconengines/*",
            "plugins/tls/*",
        ],
    )
    _pyside_dir = os.path.dirname(PySide6.__file__)
    _shiboken_dir = os.path.dirname(shiboken6.__file__)
    _qt_dll_allow = {
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
        "Qt6Network.dll",
        "Qt6Svg.dll",
        "Qt6OpenGL.dll",
        "pyside6.abi3.dll",
        "opengl32sw.dll",
    }
    for _dll_name in _qt_dll_allow:
        _dll_path = os.path.join(_pyside_dir, _dll_name)
        if os.path.isfile(_dll_path):
            _binaries.append((_dll_path, "PySide6"))
    for _dll_path in glob.glob(os.path.join(_shiboken_dir, "*.dll")):
        _binaries.append((_dll_path, "shiboken6"))
except Exception:
    pass

_excludes = [
    "tkinter",
    "unittest",
    "pydoc",
    "setuptools",
    "pip",
    "pytest",
    "IPython",
    "notebook",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuick3D",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtWebSockets",
    "PySide6.QtHttpServer",
    "PySide6.QtRemoteObjects",
    "PySide6.QtDesigner",
    "PySide6.QtUiTools",
    "PySide6.QtWebView",
    "PySide6.QtWebChannel",
    "PySide6.QtTextToSpeech",
    "PySide6.QtTest",
    "PySide6.QtSql",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSerialBus",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtSvgWidgets",
]

a = Analysis(
    [os.path.join(ROOT, "app.py")],
    pathex=[ROOT],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        os.path.join(ROOT, "hooks", "rthook_qt_plugins.py"),
        os.path.join(ROOT, "hooks", "rthook_certifi.py"),
    ],
    excludes=_excludes,
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
    name=EXE_NAME,
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
    icon=ICON if os.path.isfile(ICON) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
        "Qt6Network.dll",
        "qwindows.dll",
        "PySide6",
        "shiboken6",
    ],
    name=EXE_NAME,
)
