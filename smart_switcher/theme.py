"""Shared native UI tokens. Sizes are Qt logical pixels and scale with Windows DPI."""
from pathlib import Path
from functools import lru_cache
import sys

from PySide6.QtGui import QFont, QFontDatabase


COLORS = {
    "background": "#f4f7fa", "surface": "#ffffff", "text": "#203040",
    "muted": "#586b7c", "border": "#dce5ec", "accent": "#087f69",
    "accent_hover": "#066953", "tint": "#eaf5ef", "warning": "#936010",
    "warning_bg": "#fff6e5", "error": "#b23f38", "error_bg": "#fff0ed",
}
TYPE = {"small": 13, "body": 15, "section": 17, "heading": 26, "metric": 28}
SPACE = {"small": 8, "control": 12, "group": 16, "section": 16, "page": 24}
CONTROL_HEIGHT = 38
ICON_SIZE = 18
TABLE_ROW_HEIGHT = 44
FONT_FAMILY = "Clash Sans SC"
FONT_FILES = ("ClashSansSC-Regular.ttf", "ClashSansSC-Medium.ttf",
              "ClashSansSC-SemiBold.ttf", "NotoSans-Regular.ttf")


def font_families():
    """Use native Windows CJK metrics, with shipped static faces as a fallback."""
    return ["Microsoft YaHei UI", "Microsoft YaHei", FONT_FAMILY,
            "Segoe UI", "Noto Sans", "Segoe UI Symbol", "Segoe UI Emoji", "Arial", "sans-serif"]


def css_font_families():
    return ", ".join(f"'{family}'" for family in font_families())


@lru_cache(maxsize=1)
def load_app_fonts():
    """Register bundled fonts so Chinese glyphs do not depend on Windows setup."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    loaded = []
    for filename in FONT_FILES:
        path = base / "resources" / "fonts" / filename
        if not path.is_file():
            raise RuntimeError(f"Missing bundled font: {filename}")
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            raise RuntimeError(f"Unable to load bundled font: {filename}")
        loaded.extend(QFontDatabase.applicationFontFamilies(font_id))
    return loaded


def interface_font():
    font = QFont()
    font.setFamilies(font_families())
    font.setStyleHint(QFont.SansSerif)
    font.setPixelSize(TYPE["body"])
    font.setWeight(QFont.Normal)
    return font


def apply_interface_typography(root, numeric_widgets):
    """Apply OpenType features after QSS resolves sizes and weights."""
    families = interface_font().families()
    root.ensurePolished()
    for widget in numeric_widgets:
        widget.ensurePolished()
        font = widget.font()
        font.setFamilies(families)
        font.setFeature(QFont.Tag.fromString("tnum"), 1)
        widget.setFont(font)


def stylesheet():
    c, t = COLORS, TYPE
    return f"""
QWidget {{ color: {c['text']}; font-family: {css_font_families()}; font-size: {t['body']}px; font-weight: 400; }}
QMainWindow, QWidget#root {{ background: {c['background']}; }}
QWidget#appMain {{ background: {c['background']}; }}
QFrame#sidebar {{ background: #ffffff; border-right: 1px solid {c['border']}; }}
QLabel#brandTitle {{ color: {c['text']}; font-size: 20px; font-weight: 600; }}
QLabel#brandCaption {{ color: {c['muted']}; font-size: 13px; }}
QWidget#topbar {{ background: transparent; }}
QWidget#content {{ background: transparent; }}
QWidget#header, QWidget#summary {{ background: {c['surface']}; }}
QWidget#summary {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel#title, QLabel#pageTitle {{ font-size: {t['heading']}px; font-weight: 600; }}
QLabel#muted, QLabel#settingHint {{ color: {c['muted']}; font-size: {t['small']}px; }}
QLabel#node {{ font-size: 17px; font-weight: 500; }}
QLabel#delay {{ font-size: {t['metric']}px; font-weight: 600; }}
QLabel#autoState, QLabel#metricValue {{ font-size: 17px; font-weight: 500; }}
QLabel#automationState {{ font-size: 24px; font-weight: 600; }}
QLabel#fieldLabel {{ font-size: 14px; font-weight: 500; }}
QLabel#section {{ font-size: {t['section']}px; font-weight: 600; }}
QLabel#metricTitle {{ color: {c['muted']}; font-size: 14px; }}
QLabel#ruleValue {{ color: {c['text']}; min-height: 24px; padding: 3px 0; border-bottom: 1px solid #e6eee9; }}
QFrame#metricCard, QFrame#dashboardPanel {{ background: white; border: 1px solid {c['border']}; border-radius: 8px; }}
QLabel#sidebarStatus {{ color: {c['muted']}; padding: 8px 4px; font-size: 13px; }}
QLabel#sidebarStatus[tone="success"] {{ color: {c['accent']}; }}
QLabel#sidebarStatus[tone="warning"] {{ color: {c['warning']}; }}
QLabel#sidebarVersion {{ color: {c['muted']}; padding: 0 4px; font-size: 12px; }}
QPushButton#sidebarNav {{ text-align: left; border: 1px solid transparent; border-radius: 8px; background: transparent; color: #38584e; padding: 0 12px; min-height: 46px; max-height: 46px; font-size: 15px; }}
QPushButton#sidebarNav:hover {{ background: #edf7f2; color: {c['accent']}; }}
QPushButton#sidebarNav:checked {{ background: #e1f3ed; color: {c['accent']}; font-weight: 500; }}
QPushButton#sidebarNav:focus {{ border: 1px solid #7bb69e; }}
QLabel#badge {{ padding: 5px 10px; border-radius: 6px; background: #eef2f0; color: #405850; font-size: {t['small']}px; }}
QLabel#badge[tone="success"] {{ background: {c['tint']}; color: #076a50; }}
QLabel#badge[tone="warning"] {{ background: {c['warning_bg']}; color: {c['warning']}; }}
QLabel#badge[tone="error"] {{ background: {c['error_bg']}; color: {c['error']}; }}
QLabel[tone="success"] {{ color: {c['accent']}; }}
QLabel[tone="warning"] {{ color: {c['warning']}; }}
QLabel[tone="error"] {{ color: {c['error']}; }}
QFrame#noticePanel {{ background: #edf4f0; border-radius: 8px; }}
QFrame#noticePanel[tone="warning"] {{ background: {c['warning_bg']}; }}
QFrame#noticePanel[tone="error"] {{ background: {c['error_bg']}; }}
QFrame#noticePanel QLabel {{ color: #264b3f; font-size: {t['small']}px; }}
QFrame#noticePanel[tone="warning"] QLabel {{ color: {c['warning']}; }}
QFrame#noticePanel[tone="error"] QLabel {{ color: {c['error']}; }}
QTabWidget::pane {{ background: transparent; border: none; }}
QTabBar::tab {{ padding: 11px 18px; background: transparent; color: {c['muted']}; border-bottom: 2px solid transparent; margin-right: 8px; }}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom-color: {c['accent']}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {c['accent']}; background: #edf3ef; }}
QTabBar::tab:focus {{ border-top: 1px solid {c['accent']}; }}
QPushButton {{ background: white; border: 1px solid {c['border']}; border-radius: 6px; padding: 0 12px; min-height: 36px; max-height: 40px; font-size: 14px; font-weight: 500; }}
QPushButton:hover {{ background: #f1f7f3; border-color: #8ba99b; }}
QPushButton:pressed {{ background: #e2eee6; }}
QPushButton:focus {{ border-color: {c['accent']}; background: #edf7f1; }}
QPushButton#primary {{ background: {c['accent']}; color: white; border-color: {c['accent']}; font-weight: 500; }}
QPushButton#primary:hover, QPushButton#primary:focus {{ background: {c['accent_hover']}; border-color: #054f3e; }}
QPushButton#primary:pressed {{ background: #054f3e; }}
QPushButton#quiet {{ border-color: transparent; background: transparent; color: {c['muted']}; }}
QPushButton#quiet:hover, QPushButton#quiet:focus {{ border-color: #b1c5ba; background: #edf4ef; color: {c['text']}; }}
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#quiet:disabled {{ background: #f0f3f1; color: #6b7d74; border-color: #d7e2dc; }}
QLineEdit, QSpinBox, QComboBox {{ background: white; border: 1px solid {c['border']}; border-radius: 6px; padding: 0 10px; min-height: 36px; max-height: 40px; selection-background-color: #cce8db; selection-color: {c['text']}; }}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{ border-color: #92ad9f; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {c['accent']}; background: #fcfffd; }}
QLineEdit[motionFocus="true"]:focus, QSpinBox[motionFocus="true"]:focus, QComboBox[motionFocus="true"]:focus,
QLineEdit[motionFocus="true"]:hover, QSpinBox[motionFocus="true"]:hover, QComboBox[motionFocus="true"]:hover {{ border-color: {c['border']}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ background: #f1f4f2; color: #63766d; border-color: #d7e2dc; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ width: 26px; border: none; }}
QComboBox QAbstractItemView {{ background: white; border: 1px solid {c['border']}; selection-background-color: #e1f0e7; selection-color: {c['text']}; outline: none; padding: 4px; }}
QComboBox QAbstractItemView::item {{ min-height: 32px; }}
/* Keep Qt's native arrow glyphs visible. Position the two subcontrols so the
   Windows style can paint and hit-test its up/down arrows. */
QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 24px; height: 15px; border-left: 1px solid #e0e8e2; }}
QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; height: 15px; border-left: 1px solid #e0e8e2; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: #eaf5ef; }}
QSpinBox::up-arrow {{ image: url(uiicons:chevron-up.svg); width: 10px; height: 10px; }}
QSpinBox::down-arrow {{ image: url(uiicons:chevron-down.svg); width: 10px; height: 10px; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox:focus {{ color: {c['accent']}; }}
QTableWidget {{ background: white; border: none; font-size: 14px; gridline-color: #edf1ee; selection-background-color: #dcefe3; selection-color: {c['text']}; outline: none; }}
QHeaderView::section {{ background: #f3f6f9; border: none; border-bottom: 1px solid {c['border']}; padding: 10px 12px; color: {c['muted']}; font-size: 14px; font-weight: 500; }}
QTableWidget::item {{ border-bottom: 1px solid #eef2ef; padding: 6px 10px; }}
QTableWidget::item:selected {{ background: #dcefe3; color: {c['text']}; }}
QTableWidget::item:hover:!selected {{ background: #f0f7f4; }}
QTableWidget::item:focus {{ border: 1px solid #97bca9; }}
QPlainTextEdit {{ border: none; background: #ffffff; padding: 0; border-radius: 6px; font-size: {t['small']}px; selection-background-color: #cce8db; selection-color: {c['text']}; }}
QPlainTextEdit:focus {{ background: #f0f5f1; }}
QTextBrowser {{ border: none; background: white; padding: 16px; selection-background-color: #cce8db; font-size: 15px; color: #172d28; }}
QScrollArea, QWidget#pageCanvas {{ border: none; background: transparent; }}
QWidget#settingsContent, QWidget#settingsWrap {{ background: white; }}
QFrame#settingsSection {{ border: none; border-bottom: 1px solid #e6ece7; padding-bottom: 8px; }}
QWidget#saveBar {{ background: #f6f9f7; border-top: 1px solid {c['border']}; }}
QProgressBar#taskProgress {{ border: none; background: transparent; max-height: 3px; min-height: 3px; }}
QProgressBar#taskProgress::chunk {{ background: #78b29a; }}
QSplitter::handle:vertical {{ background: #edf2ee; height: 5px; margin: 2px 0; }}
QSplitter::handle:vertical:hover {{ background: #b9d0c2; }}
QStatusBar {{ background: {c['background']}; color: {c['muted']}; font-size: {t['small']}px; }}
QStatusBar::item {{ border: none; }}
QToolTip {{ background: #173b31; color: white; border: 1px solid #173b31; border-radius: 6px; padding: 8px 12px; qproperty-alignment: AlignCenter; }}
QMenu {{ background: white; border: 1px solid {c['border']}; padding: 5px; }}
QMenu::item {{ padding: 8px 22px; }}
QMenu::item:selected {{ background: #e3f0e8; color: {c['text']}; }}
"""


REGION_STYLE = """
QFrame#regionSelect { background: white; border: 1px solid #cbd8d1; border-radius: 7px; }
QFrame#regionSelect:hover, QFrame#regionSelect[focused="true"] { border-color: #087f69; }
QFrame#regionSelect[motionFocus="true"]:hover, QFrame#regionSelect[motionFocus="true"][focused="true"] { border-color: #cbd8d1; }
QFrame#regionSelect:disabled { background: #f1f4f2; border-color: #e1e7e3; }
QLineEdit#regionSearch, QLineEdit#regionSearch:focus { border: none; background: transparent; padding: 2px; min-height: 28px; }
QWidget#regionChip { background: #eaf5ef; border: none; border-radius: 5px; }
QWidget#regionChip QLabel { color: #245640; background: transparent; }
QWidget#regionChip:disabled { background: #edf1ee; }
QToolButton { border: 1px solid transparent; border-radius: 4px; background: transparent; padding: 2px; }
QToolButton:hover { background: #deeee3; }
QToolButton:focus { border-color: #087f69; }
QToolButton:disabled { color: #6b7d74; }
QFrame#regionMenu { background: white; border: none; border-radius: 8px; }
QListWidget { border: none; background: white; outline: none; font-size: 15px; }
QListWidget::item { min-height: 34px; padding: 0 8px; border-radius: 4px; }
QListWidget::item:hover, QListWidget::item:selected { background: #eaf5ef; color: #245640; }
QLabel#regionEmpty { color: #405a52; padding: 12px 8px; }
"""
