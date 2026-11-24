"""页面对象基类。

核心解决一个问题：**元素失效（StaleElementReferenceException）**。
前端每次增删改后都会重新渲染列表，之前拿到的元素句柄就作废了。
如果只是简单 sleep 一下，网络慢一点照样会挂——所以这里用「重试 + 显式等待」，
而不是靠固定等待时间碰运气。

这里刻意区分两种语义，混用会导致「等一个恒为空的结果」这类呆等：
- `retry(fn)`     —— 取一个值：只要不抛可恢复异常就返回，**空列表也算合法结果**；
- `wait_until(cond)` —— 等一个条件：cond 必须返回真值才算成功。
"""

import time

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# 这些异常在轮询过程中属于「暂时还不行」，等下一轮再试即可
RECOVERABLE = (
    StaleElementReferenceException,
    NoSuchElementException,
    ElementClickInterceptedException,
    IndexError,
)


class BasePage:
    def __init__(self, driver, timeout=10):
        self.driver = driver
        self.timeout = timeout

    def retry(self, fn, timeout=None, interval=0.1, message=""):
        """反复执行 fn，直到它不再抛出可恢复异常，返回它的值。

        注意：返回值是 0 / "" / [] 这类假值时也算成功——「列表为空」是合法状态。
        """
        deadline = time.time() + (timeout or self.timeout)
        last_error = None
        while time.time() < deadline:
            try:
                return fn()
            except RECOVERABLE as exc:
                last_error = exc
            time.sleep(interval)
        raise AssertionError(f"操作超时：{message or fn}；最后一次异常：{last_error!r}")

    def wait_until(self, condition, timeout=None, interval=0.1, message=""):
        """反复判断 condition，直到它返回真值；超时则失败。"""
        deadline = time.time() + (timeout or self.timeout)
        last_error = None
        while time.time() < deadline:
            try:
                if condition():
                    return True
            except RECOVERABLE as exc:
                last_error = exc
            time.sleep(interval)
        raise AssertionError(f"等待超时：{message or condition}；最后一次异常：{last_error!r}")

    def find(self, locator):
        """定位元素；元素被重渲染时重试，最终返回定位句柄。"""
        return self.retry(
            lambda: self.driver.find_element(*locator),
            message=f"定位元素 {locator}",
        )

    def find_all(self, locator):
        return self.retry(
            lambda: self.driver.find_elements(*locator),
            message=f"定位元素集合 {locator}",
        )

    def click(self, locator):
        """点击元素，遇到遮挡或失效时重试。"""

        def _do():
            self.driver.find_element(*locator).click()
            return True

        return self.retry(_do, message=f"点击元素失败 {locator}")
