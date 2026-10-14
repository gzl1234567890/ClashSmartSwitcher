import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
from PySide6.QtWidgets import QApplication, QStyle

root = Path(__file__).resolve().parent.parent
directory = root / "resources"
directory.mkdir(exist_ok=True)
app = QApplication([])
icon = app.style().standardIcon(QStyle.SP_ComputerIcon)
png = directory / "app.png"
icon.pixmap(256, 256).save(str(png))
Image.open(png).save(directory / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
