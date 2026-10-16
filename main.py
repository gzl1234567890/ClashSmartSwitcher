import argparse
import os
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from smart_switcher.config import ConfigStore
from smart_switcher import __version__
from smart_switcher.instance import SingleInstance
from smart_switcher.logging_service import setup_logging
from smart_switcher.ui import MainWindow
from smart_switcher.theme import interface_font, load_app_fonts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, help="独立配置目录，供测试或便携部署")
    parser.add_argument("--smoke-test", action="store_true", help="检查界面和 Qt 资源后自动退出，不连接真实控制器")
    parser.add_argument("--screenshot", type=Path, help="冒烟测试界面截图路径")
    args = parser.parse_args()
    startup_marker = args.data_dir / "startup.log" if args.data_dir else None
    if startup_marker:
        try:
            startup_marker.parent.mkdir(parents=True, exist_ok=True)
            startup_marker.write_text("parsed\n", encoding="utf-8")
        except OSError:
            pass
    def mark(text):
        if startup_marker:
            try:
                startup_marker.open("a", encoding="utf-8").write(text + "\n")
            except OSError:
                pass
    app = QApplication(sys.argv[:1])
    mark("qapplication")
    app.setApplicationName("ClashSmartSwitcher")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("ClashSmartSwitcher")
    app.setQuitOnLastWindowClosed(False)
    try:
        load_app_fonts()
        app.setFont(interface_font())
        store = ConfigStore(args.data_dir)
        instance = SingleInstance(store.directory)
        if not instance.acquire():
            return 0
        app.aboutToQuit.connect(instance.release)
        settings = store.load()
        logger, redactor = setup_logging(store.directory / "logs")
        window = MainWindow(store, settings, logger, redactor)
        mark("window-created")
        instance.show_requested.connect(window.show_window)
        window.show()
        mark("window-shown")
        if args.smoke_test:
            def finish():
                mark("finish")
                if args.screenshot:
                    args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                    window.grab().save(str(args.screenshot))
                window.request_exit()
            QTimer.singleShot(1000, finish)
        else:
            QTimer.singleShot(200, window.start_auto if settings.auto_enabled else window.connect_api)
        code = app.exec()
        mark("event-loop-exit")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        return code
    except Exception as exc:
        if args.smoke_test:
            import traceback
            traceback.print_exc()
            if startup_marker:
                try:
                    startup_marker.write_text(traceback.format_exc(), encoding="utf-8")
                except OSError:
                    pass
            return 1
        QMessageBox.critical(None, "启动失败", f"无法启动程序（{type(exc).__name__}）。请检查用户数据目录权限或重新解压完整分发包。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
