# 开发与构建

## 环境和模块

Windows x64、Python 3.12，固定依赖见 `requirements*.txt`。`requirements-build.txt`
锁定本轮实际构建的传递工具依赖；正式构建使用它，日常开发可用 requirements-dev。
可使用标准 venv
或 README 中的 Conda prefix；不依赖开发者机器上的全局字体或 Conda 路径。

`api`/`discovery` 负责本机接口，`core` 保持决策逻辑，`monitor` 管理线程与取消。
`ui` 维护草稿、已应用规则和重连意图；`ui_layout` 仅负责页面组成，切页不能启动任务。
`theme` 集中字体与样式，`motion` 集中动画偏好、时长和销毁清理。
`diagnostics` 只记录本地运行指标、退出标记和不含变量值的故障调用位置。
保持当前模块规模，不因目录整理改变 Mihomo 接口或配置格式。

## 本地验证

在项目根目录、激活开发环境后执行：

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
python -m pytest -q --basetemp=verification/pytest-native --junitxml=verification/native.xml
python scripts/check_ui_runtime.py
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest -q --basetemp=verification/pytest-offscreen --junitxml=verification/offscreen.xml
Remove-Item Env:QT_QPA_PLATFORM
```

临时目录、日志、截图均在忽略的 `verification/` 中；每次受限权限环境测试使用新的
`--basetemp`，避免历史目录权限影响。命名管道测试需要普通 Windows 命名对象权限。
测试使用 FakeClient；不要用常规启动代替隔离冒烟，因为常规启动会尝试真实连接。

原生界面截图：

```powershell
$env:QT_QPA_PLATFORM='windows'
python scripts/capture_ui.py --scale 100 --base-scale 150
python scripts/capture_ui.py --scale 125 --base-scale 150
python scripts/capture_ui.py --scale 150 --base-scale 150
```

`--base-scale` 必须填写当前 Windows 显示缩放百分比；offscreen 用 100。
脚本断言真实 DPR 与目标一致，输出 `verification/ui-100` 等目录。截图数据明确为 QA
模拟，覆盖五页、常规/最低尺寸、空状态、焦点和忙碌。

字体测试检查实际 OS/2 字重、无可变轴、混合文本 glyph 和像素覆盖量递增。
UI 固定等待用原生 `QTest.qWait`；信号与任务等待仍检查实际条件。曾在 pytest-qt
临时嵌套事件循环中复现 PySide 原生访问异常，因此另用 `QApplication.exec()` 的
100 次长节点更新检查真实运行路径；这不等同于长期或跨电脑稳定性证明。

多轮后台任务及表格生命周期回归使用 `scripts/soak_ui.py`，每轮经过真实
MonitorController / QThread / SwitchEngine，FakeClient 不访问真实接口。
脚本定期采样内存、线程、句柄与清理状态，支持节点增减、隐藏恢复及最低持续时长。
命令、崩溃复现和长期验证边界见 [稳定性记录](STABILITY.md)。

## 构建与资源

执行根目录 `build.bat`。脚本按 requirements-build 安装、生成静态字体、运行测试、生成图标、PyInstaller
一目录包、隔离配置冒烟、ZIP 完整性校验和 SHA256。依赖版本固定；这是可复现的
构建流程，不保证 PE/ZIP 时间戳等导致的二进制逐字节一致。

字体源与许可证随源码保留。生成器禁用时间戳重算，删除静态实例空 STAT，设置
Windows legacy 与 typographic 命名。运行包仅带四个静态字体和两份许可证。
`ClashSmartSwitcher.spec` 从 pyproject 读取 EXE 版本，允许列表排除参考图、字体源、
历史报告和开发缓存。Qt DLL 搜索路径 hook 位于 `scripts/packaging/qt_path.py`。

ZIP 保留 README 链接所需的 `docs/` 相对路径，包含项目 LICENSE、CHANGELOG；
不会复制个人配置或运行日志。发布前检查 ZIP、EXE 版本、字体许可证和 smoke 退出标记。
发布附件只用当前 `dist/ClashSmartSwitcher-<version>-windows-x64.zip` 及校验文件。

## 目录整理记录

- 单个 `runtime_hooks/qt_path.py` 归入 `scripts/packaging/`，同步 spec。
- 历史 VERIFICATION、脱敏 live-probe 和旧 81 项 XML 归入 `docs/history/`，不作为当前验收。
- 原来跟踪的四张 `.impeccable/review` 截图归档到本地 `verification/archive/ui-v2`；
  新版精选图统一放 `docs/images/`，大量过程截图与工具缓存忽略。
- 用户参考图从 `resources/` 移入本地 `verification/references/` 保留，不打包。
- 检查代码、QSS、测试和下载清单后，删除未使用的六个 Lucide 资源：
  `check`、`x`、`eye`、`eye-off`、`unplug`、`chevron-right`，同步下载列表。
- 保留 `resources/app.png`：它仍是 make_icon 生成 ICO 的中间资源，但不装入运行包。
- 空的旧 pytest 临时目录不包含源码；不将其纳入 Git。Conda、build/dist 保留为本地环境和产物。
