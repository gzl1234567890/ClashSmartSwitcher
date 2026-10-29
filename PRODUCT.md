# Clash 智能节点管家

<!-- impeccable:product-schema 1 -->

## Platform
Windows 10/11 原生桌面应用。

## Stack
用户指定 Python、PySide6、PyInstaller。

## Users
使用 Clash Verge 的普通 Windows 用户，需要持续监测节点并按规则自动切换。

## Product Purpose
仅在用户选择的代理组内，将高延迟或测速失败的当前节点切换到最低延迟的合格节点。

## Capabilities and Constraints
默认 60 秒、120 ms、5000 ms，排除香港和新加坡。真实接口数据；后台测速；单实例；托盘；中文界面。仅读取系统代理和 TUN，不修改它们或路由模式。密钥不写入普通日志。

## Brand Commitments
独立第三方工具，现代、简洁、专业的浅色桌面工具；采用用户指定的 iOS 风格磨砂玻璃与卡片，允许重构前端结构，保持功能完整与行为一致；不得冒充 Clash Verge 官方软件。

## Product Principles
实际状态优先；单组范围；失败可恢复；自动操作有验证；普通用户可直接运行 EXE。
