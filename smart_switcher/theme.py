"""Shared native UI tokens. Sizes are Qt logical pixels and scale with Windows DPI."""
from pathlib import Path
from functools import lru_cache
import sys

from PySide6.QtGui import QFont, QFontDatabase, QTextCursor, QTextOption


COLORS = {
    "background": "#edf2fb", "surface": "#ffffff", "text": "#202c42",
    "muted": "#5e6e86", "border": "#ced9eb", "accent": "#1762d6",
    "accent_hover": "#104fb5", "accent_tint": "#e5edff",
    "success": "#23764e", "tint": "#e8f5ed", "warning": "#8b5b12",
    "warning_bg": "#fff5e3", "error": "#b23f38", "error_bg": "#fff0ed",
}
TYPE = {"small": 13, "body": 15, "section": 17, "heading": 28, "metric": 30}
SPACE = {"small": 8, "control": 12, "group": 16, "section": 16, "page": 24}
CONTROL_HEIGHT = 38
CONTROL_RADIUS = 10
SURFACE_RADIUS = 16
ICON_SIZE = 18
TABLE_ROW_HEIGHT = 44
FONT_FAMILY = "Clash Sans SC"
FONT_FILES = ("ClashSansSC-Regular.ttf", "ClashSansSC-Medium.ttf",
              "ClashSansSC-SemiBold.ttf", "NotoSans-Regular.ttf")


def font_families():
    """Keep real UI weights and glyph metrics consistent on every Windows setup."""
    return [FONT_FAMILY, "Microsoft YaHei UI", "Microsoft YaHei",
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
    _configure_font_rendering(font)
    return font


def _configure_font_rendering(font):
    """Use smooth outlines instead of size-specific bitmap or snapped strokes."""
    font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferOutline)
    font.setHintingPreference(QFont.PreferNoHinting)


def configure_document_typography(document, pixel_size=16):
    """Configure rich text after loading content, including real emphasis weights."""
    font = interface_font()
    font.setPixelSize(pixel_size)
    document.setDefaultFont(font)
    document.setUseDesignMetrics(True)
    option = document.defaultTextOption()
    option.setUseDesignMetrics(True)
    option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
    document.setDefaultTextOption(option)
    # Markdown imports bold as 700; the bundled UI deliberately ships real 600
    # emphasis. Keep body, code families, sizes, links and paragraphs intact.
    changes = []
    block = document.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid() and fragment.charFormat().fontWeight() > QFont.DemiBold:
                changes.append((fragment.position(), fragment.length()))
            iterator += 1
        block = block.next()
    for position, length in changes:
        cursor = QTextCursor(document)
        cursor.setPosition(position)
        cursor.setPosition(position + length, QTextCursor.KeepAnchor)
        format_ = cursor.charFormat()
        format_.setFontWeight(QFont.DemiBold)
        cursor.mergeCharFormat(format_)


def apply_interface_typography(root, numeric_widgets):
    """Preserve QSS role sizes/weights while sharing rendering and numeric features."""
    from PySide6.QtWidgets import QWidget

    families = interface_font().families()
    root.ensurePolished()
    for widget in (root, *root.findChildren(QWidget)):
        widget.ensurePolished()
        font = widget.font()
        font.setFamilies(families)
        _configure_font_rendering(font)
        widget.setFont(font)
    for widget in numeric_widgets:
        font = widget.font()
        font.setFeature(QFont.Tag.fromString("tnum"), 1)
        widget.setFont(font)


def stylesheet():
    c, t = COLORS, TYPE
    return f"""
QWidget {{ color: {c['text']}; font-family: {css_font_families()}; font-size: {t['body']}px; font-weight: 400; }}
QMainWindow {{ background: {c['background']}; }}
QWidget#root, QWidget#summary, QWidget#pageCanvas, QWidget#settingsContent {{ background: transparent; }}
QFrame#navigationBar, QFrame#currentConnection, QFrame#dashboardPanel, QFrame#groupToolbar, QFrame#settingsSection, QFrame#saveBar {{ background: transparent; border: none; }}
QLabel {{ background: transparent; }}
QLabel#brandMark {{ background: transparent; }}
QLabel#brandTitle {{ font-size: 21px; font-weight: 600; }}
QLabel#brandCaption {{ color: {c['muted']}; font-size: 12px; }}
QLabel#pageTitle {{ font-size: {t['heading']}px; font-weight: 600; }}
QLabel#pageDescription, QLabel#muted, QLabel#settingHint {{ color: {c['muted']}; font-size: {t['small']}px; }}
QLabel#activeNode {{ font-size: 28px; font-weight: 600; }}
QLabel#groupContext {{ font-size: 14px; font-weight: 500; }}
QLabel#trafficState {{ font-size: 14px; font-weight: 500; }}
QLabel#delay {{ font-size: {t['metric']}px; font-weight: 600; }}
QLabel#automationState {{ font-size: 26px; font-weight: 600; }}
QLabel#fieldLabel {{ font-size: 14px; font-weight: 500; }}
QLabel#section {{ font-size: {t['section']}px; font-weight: 600; }}
QLabel#ruleValue {{ min-height: 26px; padding: 5px 0; border-bottom: 1px solid rgba(110, 133, 172, 25); }}
QLabel#connectionStatus {{ color: {c['muted']}; font-size: 12px; }}
QLabel#appVersion {{ color: {c['muted']}; padding: 4px 0; font-size: 12px; }}
QPushButton#workspaceNav {{ border: 1px solid transparent; border-radius: 12px; background: transparent; color: #4b5e7c; padding: 0 12px; min-height: 46px; max-height: 46px; font-size: 14px; }}
QPushButton#workspaceNav:hover {{ background: rgba(255, 255, 255, 130); }}
QPushButton#workspaceNav:checked {{ background: rgba(255, 255, 255, 232); color: {c['accent']}; font-weight: 600; }}
QPushButton#workspaceNav:focus {{ border: 1px solid {c['accent']}; }}
QLabel#badge {{ padding: 6px 12px; border-radius: 12px; background: #e8edf5; color: #4b5e7c; font-size: {t['small']}px; }}
QLabel#badge[tone="success"] {{ background: {c['tint']}; color: {c['success']}; }}
QLabel#badge[tone="warning"] {{ background: {c['warning_bg']}; color: {c['warning']}; }}
QLabel#badge[tone="error"] {{ background: {c['error_bg']}; color: {c['error']}; }}
QLabel[tone="success"] {{ color: {c['success']}; }}
QLabel[tone="warning"] {{ color: {c['warning']}; }}
QLabel[tone="error"] {{ color: {c['error']}; }}
QFrame#noticePanel {{ background: {c['accent_tint']}; border-radius: 12px; }}
QFrame#noticePanel[tone="warning"] {{ background: {c['warning_bg']}; }}
QFrame#noticePanel[tone="error"] {{ background: {c['error_bg']}; }}
QFrame#noticePanel QLabel {{ color: #315a98; font-size: {t['small']}px; }}
QFrame#noticePanel[tone="warning"] QLabel {{ color: {c['warning']}; }}
QFrame#noticePanel[tone="error"] QLabel {{ color: {c['error']}; }}
QTabWidget::pane {{ background: transparent; border: none; }}
QTabBar::tab {{ padding: 11px 18px; background: transparent; color: {c['muted']}; }}
QTabBar::tab:selected {{ color: {c['accent']}; }}
QPushButton {{ background: rgba(255, 255, 255, 210); border: 1px solid {c['border']}; border-radius: {CONTROL_RADIUS}px; padding: 0 12px; min-height: 36px; max-height: 36px; font-size: 14px; font-weight: 500; }}
QPushButton:hover {{ background: white; border-color: #9cb6de; }}
QPushButton:pressed {{ background: #e5edfc; }}
QPushButton:focus {{ border-color: {c['accent']}; background: #edf3ff; }}
QPushButton#primary {{ background: {c['accent']}; color: white; border-color: {c['accent']}; }}
QPushButton#primary:hover, QPushButton#primary:focus {{ background: {c['accent_hover']}; border-color: #0b3f94; }}
QPushButton#primary:pressed {{ background: #0b3f94; }}
QPushButton#quiet {{ border-color: transparent; background: transparent; color: {c['muted']}; }}
QPushButton#quiet:hover, QPushButton#quiet:focus {{ border-color: #b6c8e5; background: rgba(255, 255, 255, 160); color: {c['accent']}; }}
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#quiet:disabled {{ background: #e8edf5; color: #67758b; border-color: #d5deec; }}
QLineEdit, QSpinBox, QComboBox {{ background: rgba(255, 255, 255, 215); border: 1px solid {c['border']}; border-radius: {CONTROL_RADIUS}px; padding: 0 10px; min-height: 36px; max-height: 36px; selection-background-color: #d5e4ff; selection-color: {c['text']}; }}
QLineEdit {{ placeholder-text-color: {c['muted']}; }}
QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{ border-color: #9cb6de; }}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {c['accent']}; background: white; }}
QLineEdit[motionFocus="true"]:focus, QSpinBox[motionFocus="true"]:focus, QComboBox[motionFocus="true"]:focus,
QLineEdit[motionFocus="true"]:hover, QSpinBox[motionFocus="true"]:hover, QComboBox[motionFocus="true"]:hover {{ border-color: {c['border']}; }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ background: #e8edf5; color: #67758b; border-color: #d5deec; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ width: 26px; border: none; }}
QComboBox::down-arrow {{ image: url(uiicons:chevron-down.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: white; border: 1px solid {c['border']}; selection-background-color: #e5edff; selection-color: {c['text']}; outline: none; padding: 6px; }}
QComboBox QAbstractItemView::item {{ min-height: 34px; }}
QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 24px; height: 15px; border-left: 1px solid #d8e2f1; }}
QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; height: 15px; border-left: 1px solid #d8e2f1; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {c['accent_tint']}; }}
QSpinBox::up-arrow {{ image: url(uiicons:chevron-up.svg); width: 10px; height: 10px; }}
QSpinBox::down-arrow {{ image: url(uiicons:chevron-down.svg); width: 10px; height: 10px; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox:focus {{ color: {c['accent']}; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 6px; border: 1px solid #aebed7; background: white; }}
QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']}; image: url(uiicons:check.svg); }}
QCheckBox::indicator:disabled {{ background: #e8edf5; border-color: #ced9eb; }}
QCheckBox::indicator:checked:disabled {{ background: #829ac0; image: url(uiicons:check.svg); }}
QTableWidget {{ background: rgba(255, 255, 255, 165); border: none; border-radius: 12px; font-size: 14px; gridline-color: #e8edf5; selection-background-color: #dce8ff; selection-color: {c['text']}; outline: none; }}
QTableWidget#nodePreview {{ background: transparent; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{ background: #eef3fb; border: none; border-bottom: 1px solid #e1e8f3; padding: 10px 12px; color: {c['muted']}; font-size: 13px; font-weight: 500; }}
QTableWidget::item {{ border-bottom: 1px solid rgba(155, 174, 204, 35); padding: 6px 10px; }}
QTableWidget::item:selected {{ background: #dce8ff; color: {c['text']}; }}
QTableWidget::item:hover:!selected {{ background: #edf3ff; }}
QTableWidget::item:focus {{ border: 1px solid #91b2eb; }}
QPlainTextEdit {{ border: none; background: rgba(255, 255, 255, 165); padding: 12px; border-radius: 12px; font-size: {t['small']}px; selection-background-color: #d5e4ff; selection-color: {c['text']}; }}
QPlainTextEdit#embeddedLog {{ background: transparent; padding: 0; }}
QPlainTextEdit:focus {{ border: 1px solid #91b2eb; }}
QTextBrowser {{ border: none; border-radius: 16px; background: rgba(255, 255, 255, 190); padding: 20px; selection-background-color: #d5e4ff; font-size: 15px; }}
QWidget#helpCenter {{ background: transparent; }}
QLabel#helpContentsTitle {{ color: {c['muted']}; font-size: 13px; font-weight: 500; }}
QLabel#helpChapterTitle {{ font-size: 22px; font-weight: 600; }}
QTextBrowser#helpBody {{ border: none; border-radius: 0; padding: 0; background: transparent; font-size: 15px; }}
QPushButton#helpTopic {{ text-align: left; border: 1px solid transparent; background: transparent; color: {c['muted']}; border-radius: 10px; min-height: 40px; max-height: 40px; padding: 0 10px; font-size: 14px; }}
QPushButton#helpTopic:hover {{ background: rgba(255, 255, 255, 170); color: {c['accent']}; }}
QPushButton#helpTopic:checked {{ background: white; color: {c['accent']}; font-weight: 500; }}
QPushButton#helpTopic:focus {{ border-color: {c['accent']}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 14px; margin: 2px 0; }}
QScrollBar::handle:vertical {{ background: #acbcd6; border: 3px solid #edf2fb; border-radius: 7px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: #7d9ac5; }}
QScrollBar::handle:vertical:pressed {{ background: {c['accent']}; }}
QScrollBar:horizontal {{ background: transparent; height: 14px; margin: 0 2px; }}
QScrollBar::handle:horizontal {{ background: #acbcd6; border: 3px solid #edf2fb; border-radius: 7px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover {{ background: #7d9ac5; }}
QScrollBar::handle:horizontal:pressed {{ background: {c['accent']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; background: transparent; border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QProgressBar#taskProgress {{ border: none; background: transparent; max-height: 3px; min-height: 3px; }}
QProgressBar#taskProgress::chunk {{ background: #6e9ce8; }}
QSplitter::handle:vertical {{ background: #e1e9f6; height: 5px; margin: 2px 0; }}
QStatusBar {{ background: {c['background']}; color: {c['muted']}; }}
QStatusBar::item {{ border: none; }}
QToolTip {{ background: #243650; color: white; border: 1px solid #243650; border-radius: 8px; padding: 8px 12px; qproperty-alignment: AlignCenter; }}
QMenu {{ background: #f8faff; border: 1px solid {c['border']}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 8px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c['accent_tint']}; color: {c['text']}; }}
"""


REGION_STYLE = """
QFrame#regionSelect { background: #f9fbff; border: 1px solid #ced9eb; border-radius: 10px; }
QFrame#regionSelect:hover, QFrame#regionSelect[focused="true"] { border-color: #1762d6; }
QFrame#regionSelect[motionFocus="true"]:hover, QFrame#regionSelect[motionFocus="true"][focused="true"] { border-color: #ced9eb; }
QFrame#regionSelect:disabled { background: #e8edf5; border-color: #d5deec; }
QLineEdit#regionSearch, QLineEdit#regionSearch:focus { border: none; background: transparent; padding: 2px; min-height: 28px; }
QWidget#regionChip { background: #e5edff; border: none; border-radius: 8px; }
QWidget#regionChip QLabel { color: #315a98; background: transparent; }
QWidget#regionChip:disabled { background: #e8edf5; }
QToolButton { border: 1px solid transparent; border-radius: 6px; background: transparent; padding: 2px; }
QToolButton:hover { background: #d5e4ff; }
QToolButton:focus { border-color: #1762d6; }
QToolButton:disabled { color: #67758b; }
QFrame#regionMenu { background: white; border: none; border-radius: 12px; }
QListWidget { border: none; background: white; outline: none; font-size: 15px; }
QListWidget::item { min-height: 34px; padding: 0 8px; border-radius: 6px; }
QListWidget::item:hover, QListWidget::item:selected { background: #e5edff; color: #315a98; }
QLabel#regionEmpty { color: #5e6e86; padding: 12px 8px; }
"""
