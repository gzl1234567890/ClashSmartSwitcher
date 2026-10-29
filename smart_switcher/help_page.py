"""A readable, sectioned native guide backed by the distributed Markdown source."""
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextBlockFormat, QTextCursor, QTextFormat
from PySide6.QtWidgets import (
    QBoxLayout, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QTextBrowser, QVBoxLayout, QWidget,
)

from .glass import GlassSurface
from .theme import COLORS, FONT_FAMILY, configure_document_typography, interface_font


def guide_sections(markdown):
    """H2 headings are the shared topic contract for app and standalone help."""
    parts = re.split(r"(?m)^##\s+(.+?)\s*$", markdown)
    return [(parts[index].strip(), parts[index + 1].strip())
            for index in range(1, len(parts), 2)]


class HelpCenter(QWidget):
    def __init__(self, markdown, parent=None):
        super().__init__(parent)
        self.setObjectName("helpCenter")
        self.sections = guide_sections(markdown) or [("使用指南", markdown)]
        self.current_topic = -1
        self._scroll_positions = {}
        self.columns = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.columns.setContentsMargins(0, 0, 0, 0)
        self.columns.setSpacing(20)

        self.topic_panel = GlassSurface(opacity=130)
        self.topic_panel.setFixedWidth(180)
        topics = QVBoxLayout(self.topic_panel)
        topics.setContentsMargins(12, 18, 12, 14)
        topics.setSpacing(6)
        caption = QLabel("使用指南")
        caption.setObjectName("helpContentsTitle")
        caption.setContentsMargins(10, 0, 10, 10)
        topics.addWidget(caption)
        self.topic_buttons = []
        for index, (title, _) in enumerate(self.sections):
            button = QPushButton(title)
            button.setObjectName("helpTopic")
            button.setCheckable(True)
            button.setMinimumHeight(42)
            button.setCursor(Qt.PointingHandCursor)
            button.setAccessibleName("阅读" + title)
            button.clicked.connect(lambda checked=False, target=index: self.select_topic(target))
            self.topic_buttons.append(button)
            topics.addWidget(button)
        topics.addStretch()
        self.columns.addWidget(self.topic_panel)

        reading = QVBoxLayout()
        reading.setContentsMargins(0, 0, 0, 0)
        reading.setSpacing(12)
        self.compact_selector = QWidget()
        selector = QHBoxLayout(self.compact_selector)
        selector.setContentsMargins(0, 0, 0, 0)
        selector.setSpacing(12)
        selector.addWidget(QLabel("阅读章节"))
        self.topic_picker = QComboBox()
        self.topic_picker.setAccessibleName("选择帮助章节")
        self.topic_picker.addItems([title for title, _ in self.sections])
        self.topic_picker.currentIndexChanged.connect(self.select_topic)
        selector.addWidget(self.topic_picker, 1)
        reading.addWidget(self.compact_selector)

        self.reading_surface = GlassSurface(opacity=190)
        self.reading_surface.setObjectName("helpReadingSurface")
        self.reading_surface.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content = QVBoxLayout(self.reading_surface)
        content.setContentsMargins(28, 24, 28, 24)
        content.setSpacing(16)
        self.chapter_title = QLabel()
        self.chapter_title.setObjectName("helpChapterTitle")
        self.chapter_title.setWordWrap(True)
        content.addWidget(self.chapter_title)
        self.browser = QTextBrowser()
        self.browser.setObjectName("helpBody")
        self.browser.setAccessibleName("帮助正文")
        self.browser.setFrameShape(QFrame.NoFrame)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.browser.setLineWrapMode(QTextBrowser.WidgetWidth)
        self.browser.setMaximumWidth(960)
        self.browser.anchorClicked.connect(self._follow_topic_link)
        content.addWidget(self.browser, 1)
        reading.addWidget(self.reading_surface, 1)
        self.columns.addLayout(reading, 1)
        self.select_topic(0)
        self._adapt()

    def select_topic(self, index):
        if index < 0 or index >= len(self.sections) or index == self.current_topic:
            return
        if self.current_topic >= 0:
            self._scroll_positions[self.current_topic] = self.browser.verticalScrollBar().value()
        self.current_topic = index
        title, body = self.sections[index]
        self.chapter_title.setText(title)
        for position, button in enumerate(self.topic_buttons):
            button.setChecked(position == index)
        self.topic_picker.blockSignals(True)
        self.topic_picker.setCurrentIndex(index)
        self.topic_picker.blockSignals(False)
        self.browser.setMarkdown(body)
        document = self.browser.document()
        configure_document_typography(document, pixel_size=15)
        document.setDocumentMargin(0)
        self._set_reading_rhythm(document)
        self.browser.verticalScrollBar().setValue(self._scroll_positions.get(index, 0))

    @staticmethod
    def _set_reading_rhythm(document):
        """Set native document blocks, keeping Markdown lists and links intact."""
        block = document.begin()
        code_ranges = []
        while block.isValid():
            cursor = QTextCursor(block)
            paragraph = block.blockFormat()
            heading = paragraph.headingLevel() > 0
            fenced_code = bool(paragraph.property(QTextFormat.BlockCodeLanguage)) or paragraph.nonBreakableLines()
            paragraph.setLineHeight(28 if heading else 25, QTextBlockFormat.FixedHeight.value)
            paragraph.setTopMargin(18 if heading and block.position() > 0 else 0)
            paragraph.setBottomMargin(10 if heading else 8 if block.textList() else 14)
            cursor.setBlockFormat(paragraph)
            if heading:
                cursor.select(QTextCursor.BlockUnderCursor)
                text_format = cursor.charFormat()
                font = text_format.font()
                font.setPixelSize(17)
                font.setWeight(QFont.DemiBold)
                text_format.setFont(font)
                text_format.setForeground(QColor(COLORS["text"]))
                cursor.mergeCharFormat(text_format)
            fragment_iterator = block.begin()
            while not fragment_iterator.atEnd():
                fragment = fragment_iterator.fragment()
                if fragment.isValid() and (fenced_code or fragment.charFormat().fontFixedPitch()):
                    code_ranges.append((fragment.position(), fragment.length()))
                fragment_iterator += 1
            block = block.next()
        for position, length in code_ranges:
            cursor = QTextCursor(document)
            cursor.setPosition(position)
            cursor.setPosition(position + length, QTextCursor.KeepAnchor)
            text_format = cursor.charFormat()
            code_font = interface_font()
            code_font.setFamilies(["Consolas", FONT_FAMILY, "Noto Sans"])
            code_font.setStyleHint(QFont.TypeWriter)
            code_font.setFixedPitch(True)
            code_font.setPixelSize(14)
            text_format.setFont(code_font)
            text_format.setForeground(QColor("#365785"))
            text_format.setBackground(QColor("#eaf0fc"))
            cursor.mergeCharFormat(text_format)

    def _follow_topic_link(self, url):
        if url.isRelative() and url.fragment():
            for index, (title, _) in enumerate(self.sections):
                if url.fragment() == title:
                    self.select_topic(index)
                    break

    def _adapt(self):
        compact = self.width() < 1000
        self.topic_panel.setVisible(not compact)
        self.compact_selector.setVisible(compact)
        self.columns.setSpacing(0 if compact else 20)
        margin = 20 if compact else 28
        self.reading_surface.layout().setContentsMargins(margin, 20, margin, 20)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adapt()
