# Clash 智能节点管家

让常用代理组保持合适的连接。智能节点管家为 Clash Verge / Mihomo 提供节点测速、延迟趋势和按规则自动切换，在一个 Windows 桌面工作区查看连接、管理规则与追踪运行动态。

当前版本 **3.2.1**，面向 Windows 10/11 x64。它是围绕 Mihomo 本机控制接口开发的独立工具；系统代理、TUN 和路由模式继续在 Clash Verge 中管理。

## 开始使用

使用分发包时，解压后运行 `ClashSmartSwitcher.exe`，并保留同目录的 `_internal` 文件夹。分发包自带 Python 与 Qt，可以直接启动。

源码工作区中的程序位于 `dist/ClashSmartSwitcher/ClashSmartSwitcher.exe`，便携包为 `dist/ClashSmartSwitcher-3.2.1-windows-x64.zip`，旁边提供 SHA256 校验文件。升级时退出旧版，将新包解压到新目录。

1. 启动 Clash Verge，再打开智能节点管家。
2. 点击“自动发现”，从“代理组”选择要管理的 Selector 组。
3. 点击“立即测速”，查看组内节点延迟。
4. 在 Clash Verge 中启用系统代理或 TUN，进入“自动切换”页，点击“开启自动切换”。

需要手动连接时，在“连接与设置”填写本机控制接口地址和密钥。完整步骤见软件内“帮助与排查”或[使用指南](docs/HELP.md)。

## 一个工作区，完成日常节点管理

- **连接总览：** 当前节点与延迟、代理状态、最近五次延迟趋势、组内节点摘要和运行动态。
- **节点测速：** 展示完整节点表，支持搜索、状态查看和最近检测时间。测速用于观察连接表现，自动切换单独开启。
- **自动切换：** 在同一页查看运行状态、开启或暂停任务、调整规则入口，并追踪切换记录。
- **连接与设置：** 管理控制接口、检测参数、排除地区、并发数量和应用偏好；宽窗口使用双列，窄窗口纵向展开。
- **运行日志：** 跟随最新记录、回看历史，或打开本机日志目录。

切换页面时后台任务持续运行。规则可在测速期间编辑并保存，从下一轮检测生效；连接参数保存后会重新连接，并在状态验证通过后恢复原先的自动运行状态。进度、切换结果与异常都在工作区和日志中呈现。

## 按你的规则选择节点

程序管理你选择的一个 Selector 组，对它的直接服务器成员测速。当前节点超过阈值或测速失败时，从成功测速且未排除的候选中选择延迟最低者；当前已经最快时继续使用它。每轮最多切换一次，并读取实际节点确认结果。

| 设置 | 默认值 |
|---|---|
| 检测间隔 | 60 秒，首次开启立即检测 |
| 延迟阈值 | 120 ms，等于阈值时保持 |
| 单节点测速超时 | 5000 ms |
| 排除地区 | 香港、新加坡 |
| 并发测速 | 按组内节点数自动调整，最多 8 个 |
| 最小切换间隔 | 60 秒 |
| 测速地址 | `https://www.gstatic.com/generate_204` |

排除地区影响自动切换候选，测速表保留这些节点，方便比较。地区列表支持搜索、多选、单项删除、清空和自定义地区。候选整体延迟偏高时，界面会标记当前网络表现。

URLTest、Fallback 等组由 Mihomo 管理；管理嵌套组时，先在 Clash Verge 选择实际服务器，或选择包含直接服务器成员的 Selector 组。测速期间的手动选点优先保留，下一轮再评估。

## 连接与本机数据

自动发现支持 Clash Verge 配置及 Mihomo 官方命名管道，也可手动填写本机 HTTP/HTTPS 控制地址。控制接口使用 `127.0.0.1` 等回环地址，并设置密钥；控制端口与代理流量端口分别配置。连接成功后，工作区会显示控制器与系统代理、TUN 状态。

自动切换需要确认系统代理指向当前 Mihomo，或确认 TUN 已开启且对应网卡活动。手动测速可以独立使用。连接和测速的行动式排查步骤见[使用指南](docs/HELP.md)。

配置位于 `%LOCALAPPDATA%\ClashSmartSwitcher\settings.json`，日志在同目录的 `logs` 子目录。密钥可由当前 Windows 账户加密保存，也可在本次启动期间使用。日志滚动保留约 10 MB；“清空显示”整理屏幕记录，文件日志继续保留。节点、配置和日志保存在本机。

## 界面预览

![连接总览，QA 模拟数据](docs/images/desktop-overview.png)

[节点测速](docs/images/desktop-measurement.png) · [自动切换](docs/images/desktop-automation.png) · [设置](docs/images/desktop-settings.png) · [紧凑窗口](docs/images/compact-settings.png)

## 开发与构建

项目使用 Python 3.12、PySide6 和 PyInstaller。依赖清单为 `requirements.txt`、`requirements-dev.txt` 与 `requirements-build.txt`。

```powershell
conda create --prefix .\.conda\clash-smart-switcher python=3.12 pip -y
.\.conda\clash-smart-switcher\python.exe -m pip install -r requirements-dev.txt
.\.conda\clash-smart-switcher\python.exe main.py
```

在 Windows x64 执行 `build.bat`，即可完成依赖安装、静态字体与图标准备、回归测试、EXE 打包、启动检查以及 ZIP 与 SHA256 生成。字体许可证和运行资源随分发包保留。

模块边界、测试与构建说明见[开发文档](docs/DEVELOPMENT.md)；界面与发布验证见[UI 验证记录](docs/UI_VERIFICATION.md)，真实自动切换场景可按[手动验收清单](docs/MANUAL_TESTS.md)检查。版本更新见 [CHANGELOG](CHANGELOG.md)。项目使用 [MIT 许可证](LICENSE)。
