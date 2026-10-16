"""Shared native UI tokens. Sizes are Qt logical pixels and scale with Windows DPI."""
from PySide6.QtGui import QFont


COLORS = {
    "background": "#f4f7f6", "surface": "#ffffff", "text": "#172d28",
    "muted": "#405a52", "border": "#c7d5ce", "accent": "#087f69",
    "accent_hover": "#066953", "tint": "#eaf5ef", "warning": "#936010",
    "warning_bg": "#fff6e5", "error": "#b23f38", "error_bg": "#fff0ed",
}
TYPE = {"small": 13, "body": 15, "section": 16, "heading": 21, "metric": 26}
SPACE = {"small": 8, "group": 12, "section": 20, "page": 24}


def interface_font():
    font = QFont()
    font.setFamilies(["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "sans-serif"])
    font.setPointSizeF(10.5)
    return font


def stylesheet():
    c, t = COLORS, TYPE
    return f"""
QWidget {{ color: {c['text']}; font-size: {t['body']}px; }}
QMainWindow, QWidget#root {{ background: {c['background']}; }}
QWidget#header, QWidget#summary {{ background: {c['surface']}; }}
QWidget#summary {{ border-bottom: 1px solid {c['border']}; }}
QLabel {{ background: transparent; }}
QLabel#title, QLabel#pageTitle {{ font-size: {t['heading']}px; font-weight: 600; }}
QLabel#muted, QLabel#settingHint {{ color: {c['muted']}; font-size: {t['small']}px; }}
QLabel#node {{ font-size: 23px; font-weight: 600; }}
QLabel#delay {{ font-size: {t['metric']}px; font-weight: 600; }}
QLabel#autoState {{ font-size: 19px; font-weight: 600; }}
QLabel#section {{ font-size: {t['section']}px; font-weight: 600; }}
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
QTabWidget::pane {{ background: white; border: 1px solid {c['border']}; border-radius: 10px; top: -1px; }}
QTabBar::tab {{ padding: 11px 18px; background: transparent; color: {c['muted']}; border-bottom: 2px solid transparent; margin-right: 8px; }}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom-color: {c['accent']}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {c['accent']}; background: #edf3ef; }}
QTabBar::tab:focus {{ border-top: 1px solid {c['accent']}; }}
QPushButton {{ background: white; border: 1px solid #ccd8d2; border-radius: 7px; padding: 7px 12px; min-height: 24px; }}
QPushButton:hover {{ background: #f1f7f3; border-color: #8ba99b; }}
QPushButton:pressed {{ background: #e2eee6; }}
QPushButton:focus {{ border-color: {c['accent']}; background: #edf7f1; }}
QPushButton#primary {{ background: {c['accent']}; color: white; border-color: {c['accent']}; font-weight: 600; }}
QPushButton#primary:hover, QPushButton#primary:focus {{ background: {c['accent_hover']}; border-color: #054f3e; }}
QPushButton#primary:pressed {{ background: #054f3e; }}
QPushButton#quiet {{ border-color: transparent; background: transparent; color: {c['muted']}; }}
QPushButton#quiet:hover, QPushButton#quiet:focus {{ border-color: #b1c5ba; background: #edf4ef; color: {c['text']}; }}
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#quiet:disabled {{ background: #f0f3f1; color: #6b7d74; border-color: #d7e2dc; }}
QLineEdit, QSpinBox, QComboBox {{ background: white; border: 1px solid #cbd8d1; border-radius: 7px; padding: 7px 10px; min-height: 24px; selection-background-color: #cce8db; selection-color: {c['text']}; }}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{ border-color: #92ad9f; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {c['accent']}; background: #fcfffd; }}
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
QTableWidget {{ background: white; border: none; alternate-background-color: #f8faf9; gridline-color: #edf1ee; selection-background-color: #dcefe3; selection-color: {c['text']}; outline: none; }}
QHeaderView::section {{ background: #f4f7f5; border: none; border-bottom: 1px solid {c['border']}; padding: 10px 12px; color: {c['muted']}; font-size: {t['small']}px; font-weight: 600; }}
QTableWidget::item {{ border-bottom: 1px solid #eef2ef; padding: 6px 10px; }}
QTableWidget::item:selected {{ background: #dcefe3; color: {c['text']}; }}
QTableWidget::item:focus {{ border: 1px solid #97bca9; }}
QPlainTextEdit {{ border: none; background: #f6f8f7; padding: 10px; border-radius: 7px; font-size: {t['small']}px; selection-background-color: #cce8db; selection-color: {c['text']}; }}
QPlainTextEdit:focus {{ background: #f0f5f1; }}
QTextBrowser {{ border: none; background: white; padding: 16px; selection-background-color: #cce8db; font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI'; font-size: 15px; color: #172d28; }}
QScrollArea {{ border: none; background: white; }}
QWidget#settingsContent, QWidget#settingsWrap {{ background: white; }}
QFrame#settingsSection {{ border: none; border-bottom: 1px solid #e6ece7; padding-bottom: 8px; }}
QWidget#saveBar {{ background: #f6f9f7; border-top: 1px solid {c['border']}; }}
QProgressBar#taskProgress {{ border: none; background: transparent; max-height: 3px; min-height: 3px; }}
QProgressBar#taskProgress::chunk {{ background: #78b29a; }}
QSplitter::handle:vertical {{ background: #edf2ee; height: 5px; margin: 2px 0; }}
QSplitter::handle:vertical:hover {{ background: #b9d0c2; }}
QStatusBar {{ background: {c['background']}; color: {c['muted']}; font-size: {t['small']}px; }}
QStatusBar::item {{ border: none; }}
QToolTip {{ background: #173b31; color: white; border: none; padding: 6px 9px; }}
QMenu {{ background: white; border: 1px solid {c['border']}; padding: 5px; }}
QMenu::item {{ padding: 8px 22px; }}
QMenu::item:selected {{ background: #e3f0e8; color: {c['text']}; }}
"""


REGION_STYLE = """
QFrame#regionSelect { background: white; border: 1px solid #cbd8d1; border-radius: 7px; }
QFrame#regionSelect:hover, QFrame#regionSelect[focused="true"] { border-color: #087f69; }
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
