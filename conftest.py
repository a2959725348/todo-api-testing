"""pytest 全局配置与公共 fixture。

设计说明：
- session 级的 api 客户端只建一次，复用连接；
- 每个用例用独立的测试账号，避免互相污染数据；
- 用例结束后不做破坏性清理，因为服务本身是内存存储、每次 CI 都从零启动。
"""

import os
import subprocess
import sys
import time
import uuid

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.http_client import HttpClient  # noqa: E402
from config.settings import BASE_URL, STATUS  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVICE_SCRIPT = os.path.join(ROOT, "demo-service", "app.py")


def _service_alive(timeout=1):
    try:
        requests.get(f"{BASE_URL}/api/todos", timeout=timeout)
        return True
    except requests.RequestException:
        return False


@pytest.fixture(scope="session", autouse=True)
def managed_service():
    """默认地址下若服务没起，就自动拉起被测服务，跑完再关掉。

    这样新人 clone 下来只需要一条 `pytest` 命令，不用先开另一个终端。
    如果通过 BASE_URL 指向了远端环境，则完全由外部托管，本 fixture 不插手。
    """
    if not BASE_URL.startswith("http://127.0.0.1"):
        yield
        return
    if _service_alive():
        yield  # 已经有服务在跑，复用，不要越权杀掉别人的进程
        return

    proc = subprocess.Popen(
        [sys.executable, SERVICE_SCRIPT],
        cwd=os.path.dirname(SERVICE_SCRIPT),
        env={**os.environ, "TEST_MODE": "1"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        if _service_alive():
            break
        time.sleep(0.2)
    else:
        proc.kill()
        pytest.exit("被测服务启动超时，请检查 demo-service/app.py 是否可正常运行", returncode=1)

    try:
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session", autouse=True)
def fresh_data(managed_service):
    """会话开始时清空测试数据，保证整套用例可重复执行且结果稳定。

    如果被测环境没有开启 TEST_MODE，重置接口会返回 404，此时跳过重置、
    依赖「用例自身使用唯一账号」的隔离策略继续跑。
    """
    r = HttpClient().post("/api/_test/reset")
    return r.status_code == STATUS["ok"]


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api():
    """未登录的公共客户端。"""
    client = HttpClient()
    yield client
    client.session.close()


@pytest.fixture
def anon_api():
    """干净的匿名客户端，专门验证「不带 Token」的场景。"""
    client = HttpClient()
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def user_factory(api):
    """按需生成唯一账号并注册，返回 (username, password, token)。"""

    def _create(username=None, password="Passw0rd"):
        username = username or f"u{uuid.uuid4().hex[:10]}"
        r = api.post(
            "/api/register", json={"username": username, "password": password}
        )
        assert r.status_code == STATUS["created"], f"注册测试账号失败：{r.body}"
        login = api.post(
            "/api/login", json={"username": username, "password": password}
        )
        assert login.status_code == STATUS["ok"], f"测试账号登录失败：{login.body}"
        return {"username": username, "password": password, "token": login.data["token"]}

    return _create


@pytest.fixture
def user(user_factory):
    return user_factory()


@pytest.fixture
def other_user(user_factory):
    """另一个账号，用于验证越权访问。"""
    return user_factory()


@pytest.fixture
def auth_api(user):
    """已登录的客户端。"""
    client = HttpClient()
    client.set_token(user["token"])
    yield client
    client.session.close()


@pytest.fixture
def other_api(other_user):
    client = HttpClient()
    client.set_token(other_user["token"])
    yield client
    client.session.close()


@pytest.fixture
def todo_factory(auth_api):
    """在当前登录用户下创建待办，返回待办对象。"""

    def _create(title="默认待办", description=""):
        r = auth_api.post(
            "/api/todos", json={"title": title, "description": description}
        )
        assert r.status_code == STATUS["created"], f"创建待办失败：{r.body}"
        return r.data

    return _create
