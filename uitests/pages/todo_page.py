"""待办列表页面对象。

页面每次增删改后都会重新渲染 <ul>，旧元素句柄会失效，
所以取值用 retry（容忍失效、空列表也算正常结果），
状态变化用 wait_until（必须等到条件成立）。
"""

from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class TodoPage(BasePage):
    INPUT = (By.ID, "todo-input")
    ADD_BTN = (By.ID, "todo-add")
    LIST = (By.ID, "todo-list")
    ITEMS = (By.CSS_SELECTOR, "#todo-list .todo-item")
    TITLES = (By.CSS_SELECTOR, "#todo-list .todo-title")
    COUNT = (By.ID, "todo-count")
    EMPTY_HINT = (By.ID, "empty-hint")
    MESSAGE = (By.ID, "todo-message")
    CLEAR_DONE = (By.ID, "clear-done")
    LOGOUT = (By.ID, "logout-btn")
    AUTH_PANEL = (By.ID, "auth-panel")

    # ---------------- 操作 ----------------
    def add(self, title):
        box = self.find(self.INPUT)
        box.clear()
        box.send_keys(title)
        self.click(self.ADD_BTN)
        return self

    def toggle_first(self):
        self.click((By.CSS_SELECTOR, "#todo-list .todo-item .todo-check"))
        return self

    def delete_first(self):
        self.click((By.CSS_SELECTOR, "#todo-list .todo-item .btn-delete"))
        return self

    def logout(self):
        self.click(self.LOGOUT)
        return self

    # ---------------- 读取 ----------------
    def titles(self):
        """读取当前列表标题；读到一半列表被重渲染就重读一遍。"""
        return self.retry(
            lambda: [el.text for el in self.driver.find_elements(*self.TITLES)],
            message="读取待办标题列表",
        )

    def count_text(self):
        return self.retry(
            lambda: self.driver.find_element(*self.COUNT).text, message="读取待办计数"
        )

    def message_text(self):
        return self.find(self.MESSAGE).text

    def empty_hint_visible(self):
        return self.find(self.EMPTY_HINT).is_displayed()

    def auth_panel_visible(self):
        return self.find(self.AUTH_PANEL).is_displayed()

    def first_item_done(self):
        return "done" in (self.find_all(self.ITEMS)[0].get_attribute("class") or "").split()

    # ---------------- 等待 ----------------
    def wait_item_count(self, count):
        self.wait_until(
            lambda: len(self.driver.find_elements(*self.ITEMS)) == count,
            message=f"等待待办数量变为 {count}",
        )
        return self

    def wait_title_present(self, title):
        self.wait_until(
            lambda: title in [e.text for e in self.driver.find_elements(*self.TITLES)],
            message=f"等待待办「{title}」出现",
        )
        return self

    def wait_title_absent(self, title):
        self.wait_until(
            lambda: title not in [e.text for e in self.driver.find_elements(*self.TITLES)],
            message=f"等待待办「{title}」消失",
        )
        return self

    def wait_first_done(self):
        self.wait_until(
            lambda: "done"
            in (self.driver.find_elements(*self.ITEMS)[0].get_attribute("class") or "").split(),
            message="等待首个待办变为已完成状态",
        )
        return self

    def wait_logged_out(self):
        self.wait_until(
            lambda: self.driver.find_element(*self.AUTH_PANEL).is_displayed(),
            message="等待回到登录面板",
        )
        return self
