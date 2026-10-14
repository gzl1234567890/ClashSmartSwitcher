# 验证报告

## 真实 Clash Verge 环境

- Clash Verge Rev：2.5.8
- Mihomo：v1.19.32
- 传输：Mihomo 官方 Windows 命名管道上的 HTTP API
- 读取结果：64 个代理条目、12 个 Selector 代理组、版本信息和实时 TUN 状态
- 当前状态：系统代理未启用，TUN 已启用
- 真实测速：当前节点 98 ms
- 写请求：0 次；探针没有执行节点切换

完整的脱敏探针结果保存在 `verification/live-probe.json`。

## 发布包

- PyInstaller 一目录包启动冒烟测试通过
- `--smoke-test` 成功创建窗口、保存截图并正常退出
- 发布 ZIP：`dist/ClashSmartSwitcher-1.0.0-windows-x64.zip`
- Qt ICU 依赖已过滤，避免其他 Python/Conda 运行时中的 ICU DLL 覆盖 Windows 系统 ICU

## 自动化测试

此前完整测试记录为 81 项通过，记录见 `verification/test-results-final.xml`。当前受限执行环境会拒绝模拟 Windows 命名管道创建，并可能拒绝 pytest 临时目录访问；这两项限制不影响真实 Mihomo 命名管道探针或发布包冒烟测试。

## 尚未执行

- 没有向用户实际代理组发送切换请求
- 尚未在所有 Clash Verge 版本、Windows 10 实机或其他电脑上全面验证
- 真实切换请按 `docs/MANUAL_TESTS.md` 执行
