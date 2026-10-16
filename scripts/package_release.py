from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import tomllib
import zipfile

from pefile import PE

root = Path(__file__).resolve().parent.parent
folder = root / "dist" / "ClashSmartSwitcher"
exe = folder / "ClashSmartSwitcher.exe"
if not exe.exists():
    raise SystemExit("EXE 未生成，无法创建分发包")
with (root / "pyproject.toml").open("rb") as source:
    version = tomllib.load(source)["project"]["version"]
expected_version = (*map(int, version.split(".")), 0)
pe = PE(str(exe))
fixed = pe.VS_FIXEDFILEINFO[0]
for prefix in ("FileVersion", "ProductVersion"):
    major_minor = getattr(fixed, prefix + "MS")
    patch_build = getattr(fixed, prefix + "LS")
    actual = (major_minor >> 16, major_minor & 65535, patch_build >> 16, patch_build & 65535)
    if actual != expected_version:
        raise SystemExit(f"EXE {prefix} {actual} does not match project {version}; rebuild first")
pe.close()
verification = root / "verification"
verification.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="packaged-", dir=verification) as isolated:
    subprocess.run([str(exe), "--smoke-test", "--data-dir", isolated,
                    "--screenshot", str(verification / "packaged-ui.png")], check=True, timeout=60)
    marker = Path(isolated, "startup.log").read_text(encoding="utf-8")
    if "event-loop-exit" not in marker:
        raise SystemExit("Packaged application did not complete its event loop")
    (verification / "packaged-startup.txt").write_text(marker, encoding="utf-8")
    status = Path(isolated, "logs", "runtime-status.json").read_text(encoding="utf-8")
    runtime = json.loads(status)
    if runtime.get("application") != version or not runtime.get("clean_exit"):
        raise SystemExit("Packaged application version or clean exit check failed")
    (verification / "packaged-runtime.json").write_text(status, encoding="utf-8")
for name in ("README.md", "LICENSE", "CHANGELOG.md"):
    shutil.copy2(root / name, folder / name)
(folder / "docs").mkdir(exist_ok=True)
for name in ("HELP.md", "MANUAL_TESTS.md", "API_VERIFICATION.md", "VERIFICATION.md", "DEVELOPMENT.md", "STABILITY.md", "UI_VERIFICATION.md"):
    shutil.copy2(root / "docs" / name, folder / "docs" / name)
shutil.copytree(root / "docs" / "images", folder / "docs" / "images", dirs_exist_ok=True)
archive = root / "dist" / f"ClashSmartSwitcher-{version}-windows-x64.zip"
files = sorted(path for path in folder.rglob("*") if path.is_file())
for path in files:
    if path.suffix.lower() in {".log", ".env"} or path.name in {"settings.json", "NotoSansSC-VF.ttf"}:
        raise SystemExit(f"Local/development file must not be distributed: {path.name}")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    for path in files:
        output.write(path, path.relative_to(folder.parent))
with zipfile.ZipFile(archive) as output:
    if output.testzip() is not None:
        raise SystemExit("ZIP integrity check failed")
with archive.open("rb") as source:
    digest = hashlib.file_digest(source, "sha256").hexdigest()
checksum = archive.with_suffix(".zip.sha256")
checksum.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
print(f"EXE: {exe}")
print(f"ZIP: {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MB)")
print(f"SHA256: {digest}")
