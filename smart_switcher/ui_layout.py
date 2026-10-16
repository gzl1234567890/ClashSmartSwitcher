"""Native page layouts; navigation never starts or resets controller work."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QBoxLayout, QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget,
    QTableWidget, QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from . import __version__
from .config import MAX_CONCURRENCY
from .region_select import RegionMultiSelect
from .theme import COLORS, CONTROL_HEIGHT, ICON_SIZE, SPACE, TABLE_ROW_HEIGHT, interface_font
from .ui_components import ElidedLabel, LatencyTrendWidget, NoticePanel, StatusBadge, icon, resource_path
from .motion import MotionButton


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()


class WindowLayout:
    PAGE_TITLES = (
        ("运行总览", "总览"), ("节点测速", "节点测速"),
        ("自动切换", "自动切换"), ("运行日志", "运行日志"),
        ("连接与设置", "设置"), ("帮助与排查", "帮助与排查"),
    )

    def button(self, text, symbol, callback, primary=False, quiet=False):
        button = MotionButton(text)
        button.setIcon(icon(symbol, "#ffffff" if primary else COLORS["muted"]))
        button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        button.setFixedHeight(CONTROL_HEIGHT)
        if not text:
            button.setFixedWidth(CONTROL_HEIGHT)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(text)
        button.setAccessibleName(text)
        if primary or quiet:
            button.setObjectName("primary" if primary else "quiet")
        button.clicked.connect(callback)
        return button

    @staticmethod
    def label(text, name="muted", wrap=False):
        label = StatusBadge(text) if name == "badge" else QLabel(text)
        label.setObjectName(name)
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(wrap)
        if name == "badge":
            label.setAlignment(Qt.AlignCenter)
        return label

    def _panel(self, title, action=None):
        panel = QFrame()
        panel.setObjectName("dashboardPanel")
        box = QVBoxLayout(panel)
        box.setContentsMargins(*([SPACE["group"]] * 4))
        box.setSpacing(SPACE["control"])
        heading = QHBoxLayout()
        heading.setSpacing(SPACE["small"])
        heading.addWidget(self.label(title, "section"), 1)
        if action:
            heading.addWidget(action)
        box.addLayout(heading)
        return panel, box

    def _scroll_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("pageCanvas")
        box = QVBoxLayout(content)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(SPACE["section"])
        scroll.setWidget(content)
        return scroll, box

    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        sidebar = QFrame()
        self.sidebar = sidebar
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(206)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 24, 16, 20)
        side.setSpacing(8)
        brand = QHBoxLayout()
        brand.setSpacing(8)
        mark = QLabel()
        mark.setPixmap(icon("network", COLORS["accent"]).pixmap(30, 30))
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(2)
        brand_text.addWidget(self.label("Clash", "brandTitle"))
        brand_text.addWidget(self.label("智能节点管家", "brandCaption"))
        brand.addLayout(brand_text, 1)
        side.addLayout(brand)
        side.addSpacing(24)
        self.nav_buttons = []
        symbols = ("activity", "gauge", "refresh-cw", "folder-open", "settings-2")
        for index, symbol in enumerate(symbols):
            button = self.button(self.PAGE_TITLES[index][1], symbol,
                                 lambda checked=False, target=index: self.navigate(target))
            button.setObjectName("sidebarNav")
            button.setFixedHeight(48)
            button.setCheckable(True)
            self.nav_buttons.append(button)
            side.addWidget(button)
        side.addStretch()
        side.addWidget(self.button("帮助与排查", "circle-help", lambda: self.navigate(5), quiet=True))
        self.sidebar_connection = self.label("本机控制器 · 未连接", "sidebarStatus", wrap=True)
        self.sidebar_version = self.label(f"v{__version__}", "sidebarVersion")
        side.addWidget(self.sidebar_connection)
        side.addWidget(self.sidebar_version)
        root_layout.addWidget(sidebar)

        main = QWidget()
        main.setObjectName("appMain")
        body = QVBoxLayout(main)
        body.setContentsMargins(SPACE["page"], SPACE["page"], SPACE["page"], SPACE["control"])
        body.setSpacing(SPACE["section"])
        header = QHBoxLayout()
        header.setSpacing(SPACE["small"])
        self.page_title = self.label("运行总览", "pageTitle")
        header.addWidget(self.page_title, 1)
        self.header_status = self.label("接口未连接", "badge")
        header.addWidget(self.header_status)
        self.header_refresh = self.button("", "refresh-cw", self.connect_api, quiet=True)
        self.header_refresh.setFixedWidth(38)
        self.header_refresh.setToolTip("重新检测本机控制接口")
        self.header_refresh.setAccessibleName("重新检测本机控制接口")
        header.addWidget(self.header_refresh)
        body.addLayout(header)

        self.group_row = QWidget()
        self.group_toolbar = QBoxLayout(QBoxLayout.LeftToRight, self.group_row)
        self.group_toolbar.setContentsMargins(0, 0, 0, 0)
        self.group_toolbar.setSpacing(8)
        self.group_toolbar.addWidget(self.label("代理组", "fieldLabel"))
        self.group = QComboBox()
        self.group.setAccessibleName("需要管理的代理组")
        self.group.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.group.setMinimumContentsLength(8)
        self.group.addItem("请选择代理组", "")
        self.group.currentIndexChanged.connect(self._group_changed)
        self.group_toolbar.addWidget(self.group, 1)
        self.measure_button = self.button("立即测速", "gauge", self.measure, primary=True)
        self.measure_button.setToolTip("检测选定代理组的节点延迟，不切换节点")
        self.group_toolbar.addWidget(self.measure_button)
        self.last_checked = self.label("尚未检测", "muted")
        self.last_checked.setMinimumWidth(120)
        self.group_toolbar.addWidget(self.last_checked)
        body.addWidget(self.group_row)

        self.notice = NoticePanel("尚未连接本机控制接口")
        self.notice_retry = self.button("重新检测", "refresh-cw", self.connect_api, quiet=True)
        self.notice.layout().addWidget(self.notice_retry)
        body.addWidget(self.notice)
        self.task_progress = QProgressBar()
        self.task_progress.setObjectName("taskProgress")
        self.task_progress.setTextVisible(False)
        self.task_progress.setAccessibleName("后台任务忙碌指示，不提供百分比")
        self.task_progress.hide()
        body.addWidget(self.task_progress)
        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        self.tabs.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self._overview_page()
        self._measurement_page()
        self._automation_page()
        self._logs_page()
        self._settings_page()
        self.help = QTextBrowser()
        self.help.setOpenExternalLinks(True)
        self.help.setFont(interface_font())
        help_path = resource_path("docs/HELP.md")
        self.help.setMarkdown(help_path.read_text(encoding="utf-8") if help_path.exists() else "请查看分发包内的中文 README.md。")
        self.tabs.addTab(self.help, "帮助与排查")
        body.addWidget(self.tabs, 1)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.connect_button = self.button("重新检测连接", "refresh-cw", self.connect_api, quiet=True)
        self.discover_button = self.button("自动发现", "radar", self.discover_api, quiet=True)
        footer.addWidget(self.connect_button)
        footer.addWidget(self.discover_button)
        footer.addStretch()
        self.version_label = ElidedLabel("本机控制接口 · 等待检测")
        self.version_label.setObjectName("muted")
        footer.addWidget(self.version_label, 1)
        self.exit_button = self.button("", "power", self.request_exit, quiet=True)
        self.exit_button.setToolTip("退出应用")
        self.exit_button.setAccessibleName("退出应用")
        footer.addWidget(self.exit_button)
        body.addLayout(footer)
        root_layout.addWidget(main, 1)
        self.tabs.currentChanged.connect(self._page_changed)
        self._page_changed(0)
        for field in self.findChildren(QWidget):
            if isinstance(field, (QLineEdit, QComboBox, QSpinBox)) and field.objectName() != "regionSearch":
                if not isinstance(field.parentWidget(), QSpinBox):
                    field.setFixedHeight(CONTROL_HEIGHT)
        self._arrange_actions()
        self.statusBar().hide()

    def navigate(self, index):
        if self.tabs.currentIndex() == index:
            self._page_changed(index)
        else:
            self.tabs.setCurrentIndex(index)

    def _page_changed(self, index):
        self.page_title.setText(self.PAGE_TITLES[index][0])
        for target, button in enumerate(self.nav_buttons):
            button.setChecked(index == target)
        self.group_row.setVisible(index < 3)
        self.measure_button.setVisible(index != 2)
        if index == 4 and not self._settings_loading:
            self._settings_edited()
        if hasattr(self, "motion"):
            self.motion.navigate(index)

    def _open_rules(self):
        self.navigate(4)
        self.settings_scroll.ensureWidgetVisible(self.threshold, 0, 36)
        self.threshold.setFocus()

    def _overview_page(self):
        scroll, page = self._scroll_page()
        self.summary = QWidget()
        self.metric_grid = QGridLayout(self.summary)
        self.metric_grid.setContentsMargins(0, 0, 0, 0)
        self.metric_grid.setSpacing(16)
        self.group_context = ElidedLabel("未选择")
        self.node = ElidedLabel("等待连接")
        self.node.setObjectName("node")
        self.delay = self.label("未测速", "delay")
        self.auto_state = self.label("已关闭", "autoState")
        self.system_state = self.label("未知", "metricValue")
        self.tun_state = self.label("未知", "metricValue")
        self.metric_cards = []
        for title, value, symbol in (
            ("当前代理组", self.group_context, "network"),
            ("当前节点", self.node, "arrow-up-right"),
            ("节点延迟", self.delay, "gauge"),
            ("自动切换", self.auto_state, "refresh-cw"),
            ("系统代理", self.system_state, "circle-check"),
            ("TUN 模式", self.tun_state, "plug"),
        ):
            card = QFrame()
            card.setObjectName("metricCard")
            box = QVBoxLayout(card)
            box.setContentsMargins(*([SPACE["group"]] * 4))
            box.setSpacing(SPACE["small"])
            heading = QHBoxLayout()
            heading.setSpacing(SPACE["small"])
            glyph = QLabel()
            glyph.setFixedSize(ICON_SIZE, ICON_SIZE)
            glyph.setPixmap(icon(symbol, COLORS["accent"]).pixmap(18, 18))
            heading.addWidget(glyph)
            heading.addWidget(self.label(title, "metricTitle"), 1)
            box.addLayout(heading)
            if not value.objectName():
                value.setObjectName("metricValue")
            box.addWidget(value)
            card.setMinimumHeight(108)
            card.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            self.metric_cards.append(card)
        page.addWidget(self.summary)

        self.insight_row = QBoxLayout(QBoxLayout.LeftToRight)
        self.insight_row.setSpacing(16)
        self.trend_caption = self.label("最近 5 次检测")
        trend, box = self._panel("节点延迟趋势", self.trend_caption)
        self.latency_trend = LatencyTrendWidget()
        box.addWidget(self.latency_trend, 1)
        self.insight_row.addWidget(trend, 3)
        connection, box = self._panel("连接状态")
        self.connection_detail = ElidedLabel("等待连接本机控制器")
        self.connection_detail.setObjectName("fieldLabel")
        self.traffic_label = self.label("系统代理：状态无法确认\nTUN：状态无法确认", wrap=True)
        self.traffic_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(self.connection_detail)
        box.addWidget(self.traffic_label)
        box.addStretch()
        quick = QHBoxLayout()
        quick.setSpacing(8)
        self.overview_auto_button = self.button("自动切换", "refresh-cw", lambda: self.navigate(2))
        quick.addWidget(self.overview_auto_button)
        quick.addWidget(self.button("设置", "settings-2", lambda: self.navigate(4), quiet=True))
        box.addLayout(quick)
        self.insight_row.addWidget(connection, 2)
        page.addLayout(self.insight_row)

        self.overview_bottom = QBoxLayout(QBoxLayout.LeftToRight)
        self.overview_bottom.setSpacing(16)
        preview, box = self._panel("当前代理组节点", self.button("查看全部", "arrow-up-right", lambda: self.navigate(1), quiet=True))
        self.overview_table = self._node_table(preview=True)
        self.preview_empty = self.label("连接并选择代理组后显示节点", wrap=True)
        box.addWidget(self.preview_empty)
        box.addWidget(self.overview_table)
        self.overview_bottom.addWidget(preview, 3)
        recent, box = self._panel("最近日志", self.button("全部日志", "arrow-up-right", lambda: self.navigate(3), quiet=True))
        self.recent_logs = self._log_view(5)
        self.recent_logs.setMinimumHeight(170)
        box.addWidget(self.recent_logs, 1)
        self.overview_bottom.addWidget(recent, 2)
        page.addLayout(self.overview_bottom)
        page.addStretch()
        self.tabs.addTab(scroll, "总览")

    def _node_table(self, preview=False):
        table = QTableWidget(0, 3 if preview else 4)
        table.setMouseTracking(True)
        table.setHorizontalHeaderLabels(["节点名称", "延迟", "状态"] if preview else ["节点名称", "延迟", "测速状态", "角色与说明"])
        table.setAccessibleName("节点摘要" if preview else "节点测速结果")
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
        table.horizontalHeader().setFixedHeight(TABLE_ROW_HEIGHT)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table.horizontalHeaderItem(1).setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.horizontalHeaderItem(2).setTextAlignment(Qt.AlignCenter)
        table.horizontalHeader().setMinimumSectionSize(64)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        if not preview:
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        table.setColumnWidth(1, 94)
        table.setColumnWidth(2, 100)
        if preview:
            table.setFixedHeight(TABLE_ROW_HEIGHT * 6)
        else:
            table.setMinimumHeight(180)
        return table

    def _measurement_page(self):
        page_widget = QWidget()
        page = QVBoxLayout(page_widget)
        page.setContentsMargins(0, 0, 0, 0)
        page.setSpacing(16)
        self.measure_context = self.label("尚无测速结果", "section", wrap=True)
        page.addWidget(self.measure_context)
        row = QHBoxLayout()
        row.setSpacing(SPACE["small"])
        self.table_caption = self.label("当前代理组 · 候选节点", "fieldLabel", wrap=True)
        row.addWidget(self.table_caption, 1)
        self.node_search = QLineEdit()
        self.node_search.setPlaceholderText("搜索节点")
        self.node_search.setAccessibleName("筛选展示的节点，不改变测速范围")
        self.node_search.setToolTip("仅筛选表格展示，不改变测速或自动切换范围")
        self.node_search.addAction(icon("search"), QLineEdit.LeadingPosition)
        self.node_search.setClearButtonEnabled(True)
        self.node_search.setMaximumWidth(220)
        self.node_search.setMinimumWidth(130)
        self.node_search.textChanged.connect(self._filter_nodes)
        row.addWidget(self.node_search)
        page.addLayout(row)
        self.result_summary = self.label("等待连接", wrap=True)
        page.addWidget(self.result_summary)
        self.results_stack = QStackedWidget()
        self.table = self._node_table()
        self.results_stack.addWidget(self.table)
        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        self.empty_title = self.label("连接后，开始第一次测速", "section", wrap=True)
        self.empty_title.setAlignment(Qt.AlignCenter)
        self.empty_detail = self.label("尚未连接本机控制接口", wrap=True)
        self.empty_detail.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_detail)
        empty_actions = QHBoxLayout()
        empty_actions.setSpacing(SPACE["small"])
        empty_actions.addStretch()
        self.empty_discover = self.button("自动发现", "radar", self.discover_api)
        self.empty_settings = self.button("连接设置", "settings-2", lambda: self.navigate(4), quiet=True)
        empty_actions.addWidget(self.empty_discover)
        empty_actions.addWidget(self.empty_settings)
        empty_actions.addStretch()
        empty_layout.addLayout(empty_actions)
        empty_layout.addStretch()
        self.results_stack.addWidget(empty)
        self.results_stack.setCurrentIndex(1)
        page.addWidget(self.results_stack, 1)
        self.operation_hint = self.label("", wrap=True)
        page.addWidget(self.operation_hint)
        self.tabs.addTab(page_widget, "节点测速")

    def _automation_page(self):
        scroll, page = self._scroll_page()
        controls = QVBoxLayout()
        controls.setSpacing(12)
        self.auto_detail = self.label("已关闭", "automationState")
        self.auto_context = self.label("只管理选定的代理组", wrap=True)
        self.automation_node = ElidedLabel("当前节点 · 等待连接")
        self.automation_node.setObjectName("fieldLabel")
        controls.addWidget(self.auto_detail)
        controls.addWidget(self.auto_context)
        controls.addWidget(self.automation_node)
        self.action_buttons = QWidget()
        self.auto_actions = QBoxLayout(QBoxLayout.LeftToRight, self.action_buttons)
        self.auto_actions.setContentsMargins(0, 0, 0, 0)
        self.auto_actions.setSpacing(8)
        self.start_button = self.button("开启自动切换", "play", self.start_auto, primary=True)
        self.pause_button = self.button("暂停", "pause", self.pause_auto)
        self.pause_button.setToolTip("停止后续自动操作；已提交的请求不能撤回")
        self.stop_button = self.button("关闭自动切换", "square", self.stop_auto)
        for button in (self.start_button, self.pause_button, self.stop_button):
            self.auto_actions.addWidget(button)
        self.auto_actions.addStretch()
        controls.addWidget(self.action_buttons)
        page.addLayout(controls)
        rules, box = self._panel("自动切换规则", self.button("编辑规则", "settings-2", self._open_rules, quiet=True))
        self.rule_threshold = self.label("延迟阈值    未设置", "ruleValue")
        self.rule_interval = self.label("检测间隔    未设置", "ruleValue")
        self.rule_regions = self.label("排除地区    未设置", "ruleValue", wrap=True)
        self.rule_timeout = self.label("测速超时    未设置", "ruleValue")
        self.rule_cooldown = self.label("最小切换间隔    未设置", "ruleValue")
        for row in (self.rule_threshold, self.rule_interval, self.rule_regions, self.rule_timeout, self.rule_cooldown):
            box.addWidget(row)
        page.addWidget(rules)
        history, box = self._panel("近期切换记录")
        self.switch_history = self._log_view(100)
        self.switch_history.setPlaceholderText("本次运行尚无节点切换记录")
        self.switch_history.setMinimumHeight(160)
        box.addWidget(self.switch_history)
        page.addWidget(history)
        page.addStretch()
        self.tabs.addTab(scroll, "自动切换")

    @staticmethod
    def _log_view(maximum):
        logs = QPlainTextEdit()
        logs.setReadOnly(True)
        logs.setMaximumBlockCount(maximum)
        logs.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        return logs

    def _logs_page(self):
        page_widget = QWidget()
        page = QVBoxLayout(page_widget)
        page.setContentsMargins(0, 0, 0, 0)
        page.setSpacing(16)
        line = QHBoxLayout()
        line.setSpacing(SPACE["small"])
        self.follow_logs = QCheckBox("跟随最新")
        self.follow_logs.setChecked(True)
        self.follow_logs.setToolTip("向上滚动阅读历史时停止跟随")
        self.follow_logs.toggled.connect(self._follow_log_changed)
        line.addWidget(self.follow_logs)
        line.addStretch()
        line.addWidget(self.button("日志目录", "folder-open", self.open_logs, quiet=True))
        line.addWidget(self.button("清空显示", "trash-2", self._clear_logs, quiet=True))
        page.addLayout(line)
        self.logs = self._log_view(2000)
        self.logs.setAccessibleName("运行日志")
        self.logs.verticalScrollBar().valueChanged.connect(self._log_scrolled)
        page.addWidget(self.logs, 1)
        self.tabs.addTab(page_widget, "运行日志")

    def _settings_page(self):
        page_widget = QWidget()
        page = QVBoxLayout(page_widget)
        page.setContentsMargins(0, 0, 0, 0)
        page.setSpacing(0)
        self.settings_lock_hint = self.label("修改后请保存。新的规则从下一轮检测生效；连接信息变更会重新检测连接。", wrap=True)
        self.settings_lock_hint.setContentsMargins(16, 12, 16, 8)
        page.addWidget(self.settings_lock_hint)
        scroll = QScrollArea()
        self.settings_scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        widget = QWidget()
        widget.setObjectName("settingsContent")
        self.settings_widget = widget
        sections = QVBoxLayout(widget)
        sections.setContentsMargins(16, 8, 16, 16)
        sections.setSpacing(16)

        def section(title, hint):
            frame = QFrame()
            frame.setObjectName("settingsSection")
            box = QVBoxLayout(frame)
            box.setContentsMargins(0, 0, 0, 16)
            box.setSpacing(8)
            box.addWidget(self.label(title, "section"))
            box.addWidget(self.label(hint, wrap=True))
            form = QFormLayout()
            form.setContentsMargins(0, 0, 0, 0)
            form.setHorizontalSpacing(24)
            form.setVerticalSpacing(12)
            form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            form.setRowWrapPolicy(QFormLayout.WrapLongRows)
            box.addLayout(form)
            sections.addWidget(frame)
            return form

        connection = section("连接设置", "填写本机控制接口，不是代理流量端口。")
        self.address = QLineEdit()
        self.address.setPlaceholderText("http://127.0.0.1:控制端口，或官方命名管道")
        self.address.setAccessibleName("控制接口地址")
        self.address.setToolTip("仅支持本机 HTTP/HTTPS 控制地址或 Mihomo 官方命名管道")
        self.secret = QLineEdit()
        self.secret.setEchoMode(QLineEdit.Password)
        self.secret.setPlaceholderText("控制接口需要认证时填写")
        self.secret.setAccessibleName("控制密钥")
        connection.addRow("控制接口地址", self.address)
        connection.addRow("控制密钥", self.secret)
        rules = section("检测与切换规则", "当前节点超出阈值或测速失败时，才考虑切换到组内合格节点。")
        self.threshold = self.spin(1, 60000, " ms")
        self.interval = self.spin(5, 86400, " 秒")
        self.timeout = self.spin(500, 30000, " ms")
        self.minimum_switch = self.spin(0, 86400, " 秒")
        for title, control, low, high in (
            ("延迟阈值", self.threshold, 1, 60000),
            ("检测间隔", self.interval, 5, 86400),
            ("单节点测速超时", self.timeout, 500, 30000),
            ("最小切换间隔", self.minimum_switch, 0, 86400),
        ):
            control.setAccessibleName(title)
            rules.addRow(title, self.numeric_row(control, low, high))
        candidates = section("候选与性能", "排除地区只影响自动切换候选。")
        self.concurrency = self.spin(1, MAX_CONCURRENCY, " 个")
        self.concurrency.setAccessibleName("并发测速数量")
        self.concurrency.valueChanged.connect(self._concurrency_edited)
        row = self.numeric_row(self.concurrency, 1, MAX_CONCURRENCY)
        self.concurrency_hint = row.findChild(QLabel, "settingHint")
        candidates.addRow("并发测速数量", row)
        self.test_url = QLineEdit()
        self.test_url.setAccessibleName("测速地址")
        candidates.addRow("测速地址", self.test_url)
        self.region_selector = RegionMultiSelect()
        candidates.addRow("排除地区", self.region_selector)
        app = section("应用与安全", "密钥按当前 Windows 账户加密保存；不勾选时仅本次使用。")
        self.close_to_tray = QCheckBox("关闭窗口时最小化到托盘")
        self.save_secret = QCheckBox("使用 Windows 账户加密保存密钥")
        app.addRow("窗口行为", self.close_to_tray)
        app.addRow("密钥保存", self.save_secret)
        sections.addStretch()
        scroll.setWidget(widget)
        page.addWidget(scroll, 1)
        save_bar = QWidget()
        save_bar.setObjectName("saveBar")
        save = QHBoxLayout(save_bar)
        save.setSpacing(SPACE["small"])
        save.setContentsMargins(16, 12, 16, 12)
        self.settings_feedback = self.label("设置已载入", wrap=True)
        save.addWidget(self.settings_feedback, 1)
        self.save_button = self.button("保存设置", "save", self.save_settings, primary=True)
        save.addWidget(self.save_button)
        page.addWidget(save_bar)
        self.tabs.addTab(page_widget, "连接与设置")
        for field in (self.address, self.secret, self.test_url):
            field.textChanged.connect(self._settings_edited)
        for field in (self.threshold, self.interval, self.timeout, self.minimum_switch, self.concurrency):
            field.valueChanged.connect(self._settings_edited)
        for field in (self.close_to_tray, self.save_secret):
            field.toggled.connect(self._settings_edited)
        self.region_selector.selection_changed.connect(self._settings_edited)

    @staticmethod
    def spin(low, high, suffix):
        control = NoWheelSpinBox()
        control.setRange(low, high)
        control.setSuffix(suffix)
        control.setToolTip(f"可直接输入，或使用右侧箭头调整。允许范围：{low}–{high}")
        return control

    @staticmethod
    def numeric_row(control, low, high):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        control.setMaximumWidth(220)
        layout.addWidget(control, 1)
        hint = QLabel(f"范围：{low}–{high}")
        hint.setObjectName("settingHint")
        hint.setWordWrap(True)
        hint.setMinimumWidth(120)
        layout.addWidget(hint, 2)
        return row

    def _arrange_actions(self):
        if not hasattr(self, "metric_cards"):
            return
        available = self.width() - 254
        columns = 6 if available >= 1100 else 3
        if getattr(self, "_metric_columns", None) != columns:
            self._metric_columns = columns
            for col in range(6):
                self.metric_grid.setColumnStretch(col, 0)
            for index, card in enumerate(self.metric_cards):
                self.metric_grid.removeWidget(card)
                self.metric_grid.addWidget(card, index // columns, index % columns)
            for col in range(columns):
                self.metric_grid.setColumnStretch(col, 1)
        direction = QBoxLayout.TopToBottom if available < 780 else QBoxLayout.LeftToRight
        self.insight_row.setDirection(direction)
        self.overview_bottom.setDirection(direction)
        self.last_checked.setVisible(available >= 740)
        required = sum(button.minimumSizeHint().width() for button in
                       (self.start_button, self.pause_button, self.stop_button)) + 16
        self.auto_actions.setDirection(QBoxLayout.TopToBottom if available - 16 < required else QBoxLayout.LeftToRight)
