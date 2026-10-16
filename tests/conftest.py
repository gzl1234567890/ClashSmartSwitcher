import os
import sys

# Exercise the supported desktop backend on Windows, including native font,
# focus and popup lifetimes. Headless captures can still select offscreen.
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if sys.platform == "win32" else "offscreen")
