from __future__ import annotations

import http.client
import io
import json
import socket
import ssl
import time
from urllib.parse import quote, urlencode, urlsplit

from .config import validate_controller

try:
    import pywintypes
    TRANSPORT_ERRORS = (OSError, socket.timeout, http.client.HTTPException, pywintypes.error)
except ImportError:
    TRANSPORT_ERRORS = (OSError, socket.timeout, http.client.HTTPException)


class ApiError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class PipeStream(io.RawIOBase):
    """Timeout-bounded overlapped I/O on Mihomo's documented HTTP named pipe."""

    def __init__(self, path: str, timeout: float):
        super().__init__()
        self.handle = None
        import win32con
        import win32file
        import win32pipe
        self.timeout = timeout
        win32pipe.WaitNamedPipe(path, max(1, int(timeout * 1000)))
        self.handle = win32file.CreateFile(path, win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                                          0, None, win32con.OPEN_EXISTING,
                                          win32con.FILE_FLAG_OVERLAPPED, None)

    def readable(self):
        return True

    def _complete(self, operation):
        import win32event
        import win32file
        if win32event.WaitForSingleObject(operation.hEvent, int(self.timeout * 1000)) != win32event.WAIT_OBJECT_0:
            win32file.CancelIoEx(self.handle, operation)
            win32event.WaitForSingleObject(operation.hEvent, win32event.INFINITE)
            raise TimeoutError("命名管道请求超时")
        return win32file.GetOverlappedResult(self.handle, operation, False)

    def sendall(self, data):
        import pywintypes
        import win32event
        import win32file
        operation = pywintypes.OVERLAPPED()
        operation.hEvent = win32event.CreateEvent(None, True, False, None)
        try:
            win32file.WriteFile(self.handle, data, operation)
            written = self._complete(operation)
            if written != len(data):
                raise OSError("管道请求未完整发送")
        finally:
            operation.hEvent.Close()

    def readinto(self, target):
        import pywintypes
        import win32event
        import win32file
        operation = pywintypes.OVERLAPPED()
        operation.hEvent = win32event.CreateEvent(None, True, False, None)
        buffer = win32file.AllocateReadBuffer(len(target))
        try:
            win32file.ReadFile(self.handle, buffer, operation)
            count = self._complete(operation)
            target[:count] = buffer[:count]
            return count
        except pywintypes.error as exc:
            if exc.winerror in (109, 232):
                return 0
            raise
        finally:
            operation.hEvent.Close()

    def makefile(self, mode):
        return io.BufferedReader(self)

    def close(self):
        if not self.closed and self.handle is not None:
            self.handle.Close()
        super().close()


class MihomoClient:
    def __init__(self, controller: str, secret: str = "", timeout: float = 3):
        validate_controller(controller)
        if any(c in secret for c in "\r\n"):
            raise ValueError("密钥格式无效")
        self.controller = controller.rstrip("/")
        self.secret = secret
        self.timeout = timeout

    def request(self, method: str, path: str, body=None, timeout=None, retry=True):
        attempts = 2 if method == "GET" and retry else 1
        for attempt in range(attempts):
            connection = None
            pipe = None
            try:
                wait = timeout or self.timeout
                payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else b""
                headers = {"Content-Type": "application/json", "Connection": "close"}
                if self.controller.startswith("\\\\.\\pipe\\"):
                    pipe = PipeStream(self.controller, wait)
                    headers.update({"Host": "localhost", "Content-Length": str(len(payload))})
                    head = f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"
                    pipe.sendall(head.encode("ascii") + payload)
                    response = http.client.HTTPResponse(pipe)
                    response.begin()
                else:
                    address = urlsplit(self.controller)
                    if self.secret:
                        headers["Authorization"] = "Bearer " + self.secret
                    # Resolve localhost to loopback explicitly; ignore environment proxies.
                    host = "127.0.0.1" if address.hostname == "localhost" else address.hostname
                    if address.scheme == "https":
                        connection = http.client.HTTPSConnection(host, address.port, timeout=wait, context=ssl.create_default_context())
                    else:
                        connection = http.client.HTTPConnection(host, address.port, timeout=wait)
                    connection.request(method, path, payload, headers)
                    response = connection.getresponse()
                raw = response.read(16 * 1024 * 1024 + 1)
                status = response.status
                response.close()
                if len(raw) > 16 * 1024 * 1024:
                    raise ApiError("接口响应过大，请检查控制地址")
                if 300 <= status < 400:
                    raise ApiError("控制接口发生重定向，已拒绝跟随；请填写直接的本机控制地址", status)
                if status >= 400:
                    messages = {401: "控制密钥不正确，请检查密钥", 403: "控制接口拒绝访问", 404: "代理组或节点已不存在，请重新检测", 504: "测速超时：可能是节点或测速地址不可访问", 503: "测速失败：无法单独判定节点或测速地址故障"}
                    raise ApiError(messages.get(status, f"控制接口返回 HTTP {status}"), status)
                if not raw:
                    return {}
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ApiError("接口返回的数据格式不兼容")
                return result
            except ApiError as exc:
                if attempt + 1 >= attempts or exc.status not in (500, 502, 503, 504):
                    raise
            except TRANSPORT_ERRORS as exc:
                if attempt + 1 >= attempts:
                    raise ApiError("无法连接本机控制接口或请求超时，请确认 Clash Verge 已运行并重新检测") from exc
            except (ValueError, UnicodeError) as exc:
                raise ApiError("接口返回的数据格式不兼容，请确认填写的是控制地址") from exc
            finally:
                if connection is not None:
                    connection.close()
                if pipe is not None:
                    pipe.close()
            time.sleep(0.25 * (attempt + 1))

    def version(self):
        data = self.request("GET", "/version")
        if not isinstance(data.get("version"), str):
            raise ApiError("此地址不是兼容的 Mihomo 控制接口")
        return data["version"]

    def proxies(self):
        data = self.request("GET", "/proxies").get("proxies")
        if not isinstance(data, dict) or any(not isinstance(x, dict) for x in data.values()):
            raise ApiError("代理组数据格式不兼容")
        return data

    def proxy(self, name):
        return self.request("GET", "/proxies/" + quote(name, safe=""))

    def configs(self):
        return self.request("GET", "/configs")

    def delay(self, name, url, timeout_ms):
        query = urlencode({"url": url, "timeout": timeout_ms})
        data = self.request("GET", "/proxies/" + quote(name, safe="") + "/delay?" + query,
                            timeout=timeout_ms / 1000 + 1, retry=False)
        value = data.get("delay")
        if type(value) is not int or value <= 0:
            raise ApiError("节点未返回有效延迟")
        return value

    def switch(self, group, node):
        return self.request("PUT", "/proxies/" + quote(group, safe=""), {"name": node}, retry=False)
