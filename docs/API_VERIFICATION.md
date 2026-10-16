# 接口依据

开发时读取了 Mihomo 官方仓库以下文件，日期为 2026-10-14：

- https://github.com/MetaCubeX/mihomo/blob/Meta/hub/route/server.go
- https://github.com/MetaCubeX/mihomo/blob/Meta/hub/route/proxies.go

`server.go` 的路由包含 GET /version、/configs、/proxies。HTTP 控制器用 Authorization: Bearer secret；`startPipe` 使用相同 HTTP 路由并将认证参数设为空，权限由 Windows 管道控制。

`proxies.go` 的 GET /proxies/{name}/delay 接受 url 与毫秒 timeout，返回正整数 delay。官方当前实现将 timeout 解析为有符号 16 位整数，因此本程序限制为 500 至 30000 ms。PUT /proxies/{name} 接受 JSON `{"name": "目标节点"}`，成功返回 204；仅 SelectAble 组可控，本程序保守支持 Selector。名称使用 URL 编码。

不重试 PUT。请求返回成功后仍读取组状态验证 now。GET 控制状态最多重试一次，测速请求在 API 层不重试；决策层仅在短于 5 秒的测速收到 Mihomo 504 时，以 5 秒预算补测一次。HTTP 请求直接连接本机，忽略系统和环境代理，不跟随重定向。

命名管道只使用上述已确认的 HTTP 协议，不访问 Clash Verge 的私有应用 IPC。管道使用 Windows overlapped I/O 和有限超时。
