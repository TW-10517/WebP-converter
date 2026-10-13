# PyInstaller build spec: pyinstaller WebPConverter.spec
import os

block_cipher = None

a = Analysis(
    ["WebP Converter.pyw"],
    pathex=[],
    binaries=[],
    datas=[("assets/logo.png", "assets"), ("assets/icon.ico", "assets")],
    hiddenimports=["tkinterdnd2"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["numpy", "pytest", "urllib3", "requests"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WebP Converter",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join("assets", "icon.ico"),
)
