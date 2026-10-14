"""Keep another Python/Conda installation from shadowing bundled Qt DLLs."""
import os
import sys

if getattr(sys, "frozen", False):
    bundled_qt = os.path.join(sys._MEIPASS, "PySide6")
    bundled_shiboken = os.path.join(sys._MEIPASS, "shiboken6")
    os.environ["PATH"] = (bundled_qt + os.pathsep + bundled_shiboken + os.pathsep
                           + sys._MEIPASS + os.pathsep + os.environ.get("PATH", ""))
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(bundled_qt)
        os.add_dll_directory(bundled_shiboken)
        os.add_dll_directory(sys._MEIPASS)
