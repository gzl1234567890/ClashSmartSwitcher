from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
from urllib.parse import unquote, urlsplit, parse_qs
import uuid

import pytest

from smart_switcher.api import ApiError, MihomoClient


@pytest.fixture
def server():
    state = {"requests": [], "current": "美国 / A", "delay": 81, "bad_json": False, "redirect": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, code, body):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            if state["bad_json"]:
                data = b"broken json"
            self.send_response(code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            state["requests"].append(("GET", self.path))
            if self.headers.get("Authorization") != "Bearer mock-test-secret":
                self.respond(401, {})
            elif state["redirect"]:
                self.respond(302, {})
            elif self.path == "/version":
                self.respond(200, {"version": "mock"})
            elif self.path == "/proxies":
                self.respond(200, {"proxies": {"美国 / A": {"type": "Shadowsocks"}}})
            elif urlsplit(self.path).path.endswith("/delay"):
                self.respond(200, {"delay": state["delay"]})
            else:
                self.respond(200, {"now": state["current"]})

        def do_PUT(self):
            state["requests"].append(("PUT", self.path))
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["current"] = body["name"]
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield MihomoClient(f"http://127.0.0.1:{httpd.server_port}", "mock-test-secret"), state
    httpd.shutdown()
    httpd.server_close()
    thread.join(2)


def test_real_http_transport_version_proxies_and_put(server):
    client, state = server
    assert client.version() == "mock"
    assert "美国 / A" in client.proxies()
    client.switch("组 / A", "德国")
    assert client.proxy("组 / A")["now"] == "德国"
    assert len([x for x in state["requests"] if x[0] == "PUT"]) == 1


def test_delay_url_encoding_and_timeout(server):
    client, state = server
    assert client.delay("美国 / A", "https://example.test/generate_204?a=1", 5000) == 81
    path = state["requests"][-1][1]
    assert unquote(urlsplit(path).path) == "/proxies/美国 / A/delay"
    query = parse_qs(urlsplit(path).query)
    assert query["timeout"] == ["5000"] and query["url"] == ["https://example.test/generate_204?a=1"]


def test_unauthorized_does_not_retry_or_leak_secret(server):
    client, state = server
    client.secret = "mock-wrong-secret"
    with pytest.raises(ApiError, match="密钥") as exc:
        client.version()
    assert "mock-wrong-secret" not in str(exc.value)
    assert len(state["requests"]) == 1


@pytest.mark.parametrize("delay", [0, -1, "80", None, True])
def test_invalid_delay_never_fabricated(server, delay):
    client, state = server
    state["delay"] = delay
    with pytest.raises(ApiError, match="有效延迟"):
        client.delay("美国 / A", "https://example.test", 5000)


def test_json_corruption_is_clear_error(server):
    client, state = server
    state["bad_json"] = True
    with pytest.raises(ApiError, match="格式不兼容"):
        client.version()


def test_no_remote_redirect_followed(server):
    client, state = server
    state["redirect"] = True
    with pytest.raises(ApiError, match="重定向"):
        client.version()


@pytest.mark.skipif(os.name != "nt", reason="Windows named pipes")
def test_real_named_pipe_http_transport():
    import win32con
    import win32file
    import win32pipe
    path = "\\\\.\\pipe\\clash-smart-switcher-test-" + uuid.uuid4().hex
    handle = win32pipe.CreateNamedPipe(path, win32pipe.PIPE_ACCESS_DUPLEX,
                                     win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
                                     1, 65536, 65536, 1000, None)
    errors = []
    def serve():
        try:
            win32pipe.ConnectNamedPipe(handle, None)
            _, request = win32file.ReadFile(handle, 65536)
            assert request.startswith(b"GET /version HTTP/1.1")
            data = b'{"version":"mock-pipe"}'
            win32file.WriteFile(handle, b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(data)).encode() + b"\r\nConnection: close\r\n\r\n" + data)
            win32file.FlushFileBuffers(handle)
        except Exception as exc:
            errors.append(exc)
        finally:
            handle.Close()
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    assert MihomoClient(path).version() == "mock-pipe"
    thread.join(2)
    assert not errors and not thread.is_alive()
