from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'docs'), 'docs'), (str(root / 'resources'), 'resources')],
    hiddenimports=['win32crypt', 'win32file', 'win32pipe', 'win32event', 'win32con', 'pywintypes'],
    hookspath=[],
    runtime_hooks=[str(root / 'runtime_hooks' / 'qt_path.py')],
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
          console=False, icon=str(root / 'resources' / 'app.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ClashSmartSwitcher')
