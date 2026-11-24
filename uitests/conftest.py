"""UI 自动化测试 —— 浏览器与页面对象的基础配置。

采用 Page Object 模式：页面上的元素定位与操作集中写在 pages/ 里，
用例里只出现「打开页面 -> 操作 -> 断言」，改版时只需要改页面对象一个文件。
"""

import os
import subprocess
import sys
import time

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE_SCRIPT = os.path.join(ROOT, "demo-service", "app.py")

# 让用例可以直接 import pages.xxx，而不依赖 pytest 的 rootdir 猜测
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
HEADLESS = os.getenv("HEADLESS", "1") != "0"


def _service_alive(timeout=1):
    try:
        requests.get(f"{BASE_URL}/", timeout=timeout)
        return True
    except requests.RequestException:
        return False


@pytest.fixture(scope="session", autouse=True)
def service():
    """UI 测试同样需要被测服务；本地默认地址下自动拉起，用完关掉。"""
    if not BASE_URL.startswith("http://127.0.0.1") or _service_alive():
        yield
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
        pytest.exit("被测服务启动超时", returncode=1)

    try:
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL.rstrip("/")


@pytest.fixture
def driver():
    """每个用例一个干净的浏览器上下文。

    默认无头模式，CI 里无需图形界面；设置 HEADLESS=0 可以在本地看着它跑。
    """
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    browser = webdriver.Chrome(options=options)
    browser.implicitly_wait(0)
    try:
        yield browser
    finally:
        browser.quit()
