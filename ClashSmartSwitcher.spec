from pathlib import Path
import tomllib
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo,
    VarStruct, VSVersionInfo,
)

root = Path(SPECPATH)
version = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=(*map(int, version.split('.')), 0),
                      prodvers=(*map(int, version.split('.')), 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('FileDescription', 'Clash Smart Switcher'),
        StringStruct('FileVersion', version), StringStruct('ProductVersion', version),
        StringStruct('ProductName', 'Clash Smart Switcher'),
        StringStruct('OriginalFilename', 'ClashSmartSwitcher.exe'),
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])],
)
font_assets = [(str(root / 'resources' / 'fonts' / name), 'resources/fonts')
               for name in ('ClashSansSC-Regular.ttf', 'ClashSansSC-Medium.ttf',
                            'ClashSansSC-SemiBold.ttf', 'NotoSans-Regular.ttf',
                            'OFL.txt', 'OFL-Latin.txt', 'README.md')]
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'docs' / 'HELP.md'), 'docs'),
           (str(root / 'resources' / 'app.ico'), 'resources'),
           (str(root / 'resources' / 'icons'), 'resources/icons')] + font_assets,
    hiddenimports=['win32crypt', 'win32file', 'win32pipe', 'win32event', 'win32con', 'pywintypes'],
    hookspath=[],
    runtime_hooks=[str(root / 'scripts' / 'packaging' / 'qt_path.py')],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick', 'tkinter', 'pytest'],
    noarchive=False,
)
# PySide6 6.10 links against the unversioned ICU API supplied by Windows.
# PyInstaller can accidentally collect an unrelated ICU 78 DLL from another
# runtime on PATH; that DLL only exports version-suffixed symbols and makes
# Qt6Core fail with Windows error 127 at startup.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icudt78.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ClashSmartSwitcher',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(root / 'resources' / 'app.ico'), version=version_info)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ClashSmartSwitcher')
