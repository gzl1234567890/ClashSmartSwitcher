# V3.0.0 验证报告

本文保留 V3.0.0 发布时的验证结果。后续多轮运行崩溃与 3.1.0 修复见
[稳定性记录](STABILITY.md)；下列短时检查不代表长期运行稳定性。

日期：2026-10-16。环境：Windows 11 x64，10.0.26200，Python 3.12.15，
PySide6 Essentials / shiboken6 6.10.3。

## 字体验收（已完成）

- 定位到可变字重及生成静态字体保留空 STAT 表的问题：Qt 请求 600 时可能选到
  Medium 500 再合成粗体，仅检查 QFont/QRawFont 声明字重不能发现这一问题。
- 静态生成器删除空 STAT，并修正 Windows legacy family 与 Bold 位，真实 OS/2
  字重为 400/500/600。保留源字体、版权和 OFL 许可证，运行包不加载可变源。
- 全局 QFont/QSS 同用系统微软雅黑优先、静态 Clash Sans SC 回退的字体链；
  默认字号统一为 15 逻辑像素。未放大字号、全局加粗或变更布局。
- 38 项页面/字体/交互专项通过。实际字体表检查与像素覆盖量递进通过；中文、英文、
  数字、箭头、勾号、省略号等混合文本没有缺字；状态重绘保持字重。
- 原生 Qt 截图覆盖 100%/125%/150%（真实 DPR 1/1.25/1.5）、1440×900 和
  850×630 的五个主要页面、焦点/忙碌/空状态。精选图在 `docs/images/`，
  完整过程保留在本机 `verification/font-100`、`font-125`、`font-150`。
- 原生 QApplication 主事件循环完成 100 次长中文/英文/符号节点更新、五页切换
  和尺寸变化，零网络请求。记录：`verification/runtime/result.json`。

参考 Clash Verge Rev 的 Windows 字体选择方式：
[上游主题](https://github.com/clash-verge-rev/clash-verge-rev/blob/main/src/pages/_theme.tsx)。
本项目使用 Qt Widgets，不是 WebView；CSS 字体平滑开关不能直接移植。
微软雅黑在部分环境没有独立 500/600 实体，Windows 可合成对应粗细；随包 fallback
三字重已经验证真实数据匹配。不同显示器/ClearType 设置仍会影响观感。

## 最终回归与构建

- 原生 Windows 后端：139 项通过，18.38 秒；`verification/v3-native.xml`。
- offscreen 后端：139 项通过，12.98 秒；`verification/v3-offscreen.xml`。没有跳过命名管道测试。
- 覆盖决策、HTTP/命名管道、配置/DPAPI、取消/退出、运行中设置、重连恢复、后台静默、
  五页导航、搜索/选择/滚动、地区多选、键盘焦点、减少动画、隐藏恢复和字体实际匹配。
- `pip check` 无依赖冲突，`compileall` 编译通过，`git diff --check` 无格式错误。
- 三个静态字体重新生成后的 SHA256 均与生成前一致。
- 最终 V3 截图重采集至 `verification/v3-ui-100`、`v3-ui-125`、`v3-ui-150`；
  已复核主要页面，`docs/images/` 更新为带 v3.0.0 版本的精选截图。
- 原生主循环压力检查再次完成 100 次更新、五页切换，零网络请求。
- 正式 PyInstaller 6.19.0 一目录构建通过，EXE 的 PE File/Product 版本为 3.0.0。
- 已用独立数据目录启动 EXE，创建实际界面、截图并正常退出；退出标记含 event-loop-exit。
- 检查冻结资源中的 400/500/600 实际字重、无 fvar/STAT、源文件字节一致和两份字体
  许可证；图标与内置 HELP 存在，运行包没有可变源字体。
- 构建依赖锁定清单的离线 dry-run 全部满足，无待安装依赖；构建警告仅涉及条件或
  可选平台导入，隔离启动未发生缺失 DLL/入口失败。
- `scripts/package_release.py` 使用新的隔离配置冒烟，确认正常退出后生成
  `dist/ClashSmartSwitcher-3.0.0-windows-x64.zip`（约 57.4 MB）和 `.zip.sha256`。
  ZIP CRC 完整性校验通过；文档保持 README 所需的相对目录，附带 LICENSE/CHANGELOG。
- 完整 ZIP 解压至新的本地目录后再次启动 EXE，隔离配置冒烟与退出通过；共 262 个文件，
  不含个人配置、日志、测试、历史记录和可变字体源，README 文档/图片链接均可解析。

更早版本的开发过程文件已于 2026-10-28 按用户要求清理；历史阶段通过数量不代替本次结果。新版 UI 验证见 [UI_VERIFICATION.md](UI_VERIFICATION.md)。

## 验证边界

- 本轮不向真实节点发送任何切换请求；连接、切换、失败、暂停场景使用模拟接口。
- 曾在 pytest-qt 临时嵌套事件循环复现 pyside6.abi3.dll 原生访问异常。升级 6.10.3
  本身不足以证明消除；固定等待改用 QTest.qWait，保留断言及真实条件等待，另做
  QApplication.exec 运行验证。不能宣称所有电脑或长期运行都已经验证。
- 未新增 Windows 10 实机、其他电脑、所有 Clash Verge 版本或人工物理滚轮验收。
- 旧真实只读接口探针已清理，其结果不作为本轮测试证据。
- 程序未进行商业代码签名，Windows 可能显示未知发布者。
