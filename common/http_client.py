"""统一请求基类。

所有用例都通过这个类发请求，好处是：
1. BaseURL、超时、公共请求头只在这里维护一份；
2. 请求与响应日志统一记录，排查问题不用再到处 print；
3. 用例里只剩「准备数据 -> 调接口 -> 断言」三段式，可读性好。
"""

import json
import logging
import os
import time

import requests

from config.settings import BASE_URL, LOG_DIR, LOG_FILE, TIMEOUT


def get_logger(name="api_test"):
    """按需创建日志器，重复调用不会叠加 handler。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    if os.getenv("LOG_TO_CONSOLE"):
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
        logger.addHandler(stream)
    return logger


log = get_logger()


class HttpClient:
    """带 Token 注入与日志的 HTTP 客户端。"""

    def __init__(self, base_url=BASE_URL, timeout=TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ---------------- Token ----------------
    def set_token(self, token):
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            self.session.headers.pop("Authorization", None)

    # ---------------- 核心请求 ----------------
    def request(self, method, path, **kwargs):
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)
        started = time.perf_counter()
        log.info(">>> %s %s | body=%s", method.upper(), url, _preview(kwargs.get("json")))
        resp = self.session.request(method.upper(), url, **kwargs)
        cost = (time.perf_counter() - started) * 1000
        log.info("<<< %s %s | %.0fms | %s", resp.status_code, url, cost, _preview(resp.text))
        return Response(resp)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)


class Response:
    """对 requests.Response 的轻量包装，断言时少写一层 .json()。"""

    def __init__(self, resp):
        self.raw = resp
        self.status_code = resp.status_code
        try:
            self.body = resp.json()
        except ValueError:
            self.body = None
        self.elapsed_ms = resp.elapsed.total_seconds() * 1000

    @property
    def code(self):
        return (self.body or {}).get("code")

    @property
    def msg(self):
        return (self.body or {}).get("msg")

    @property
    def data(self):
        return (self.body or {}).get("data")

    def __repr__(self):
        return f"<Response [{self.status_code}] {_preview(self.body)}>"


def _preview(value, limit=300):
    if value is None:
        return "None"
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    return value if len(value) <= limit else value[:limit] + "..."
