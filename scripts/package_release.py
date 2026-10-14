from pathlib import Path
import shutil
import subprocess
import zipfile

root = Path(__file__).resolve().parent.parent
folder = root / "dist" / "ClashSmartSwitcher"
exe = folder / "ClashSmartSwitcher.exe"
if not exe.exists():
    raise SystemExit("EXE 未生成，无法创建分发包")
subprocess.run([str(exe), "--smoke-test", "--data-dir", str(root / "verification" / "packaged-data"),
                "--screenshot", str(root / "verification" / "packaged-ui.png")], check=True, timeout=30)
shutil.copy2(root / "README.md", folder / "README.md")
shutil.copytree(root / "docs", folder / "使用说明", dirs_exist_ok=True)
archive = root / "dist" / "ClashSmartSwitcher-1.0.0-windows-x64.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            output.write(path, path.relative_to(folder.parent))
print(f"EXE: {exe}")
print(f"ZIP: {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MB)")
