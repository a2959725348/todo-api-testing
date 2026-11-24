"""登录/注册页面对象。"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage


class LoginPage(BasePage):
    URL_PATH = "/"

    # 元素定位集中在此，页面改版只需改这里
    USERNAME = (By.ID, "username")
    PASSWORD = (By.ID, "password")
    SUBMIT = (By.ID, "auth-submit")
    MESSAGE = (By.ID, "auth-message")
    TAB_LOGIN = (By.ID, "tab-login")
    TAB_REGISTER = (By.ID, "tab-register")
    AUTH_PANEL = (By.ID, "auth-panel")
    TODO_PANEL = (By.ID, "todo-panel")
    CURRENT_USER = (By.ID, "current-user")

    def __init__(self, driver, base_url, timeout=10):
        super().__init__(driver, timeout)
        self.base_url = base_url.rstrip("/")

    # ---------------- 操作 ----------------
    def open(self):
        self.driver.get(self.base_url + self.URL_PATH)
        self.wait_until(
            lambda: self.driver.find_element(*self.AUTH_PANEL).is_displayed(),
            message="打开首页并等待登录面板出现",
        )
        return self

    def switch_to_register(self):
        self.click(self.TAB_REGISTER)
        self.wait_until(
            lambda: self.driver.find_element(*self.SUBMIT).text == "注册",
            message="切换到注册页签",
        )
        return self

    def register(self, username, password):
        self.switch_to_register()
        self._fill(username, password)
        self.click(self.SUBMIT)
        return self

    def login(self, username, password):
        self.click(self.TAB_LOGIN)
        self._fill(username, password)
        self.click(self.SUBMIT)
        return self

    def _fill(self, username, password):
        user = self.find(self.USERNAME)
        user.clear()
        user.send_keys(username)
        pwd = self.find(self.PASSWORD)
        pwd.clear()
        pwd.send_keys(password)

    # ---------------- 断言辅助 ----------------
    def wait_logged_in(self):
        """等到待办面板可见，说明登录成功且渲染完成。"""
        self.wait_until(
            lambda: self.driver.find_element(*self.TODO_PANEL).is_displayed(),
            message="等待进入待办面板",
        )
        return self

    def message_text(self):
        return self.find(self.MESSAGE).text

    def wait_message(self, keyword):
        self.wait_until(
            lambda: keyword in self.driver.find_element(*self.MESSAGE).text,
            message=f"等待提示语包含「{keyword}」",
        )
        return self

    def current_user(self):
        return self.retry(
            lambda: self.driver.find_element(*self.CURRENT_USER).text,
            message="读取当前登录用户名",
        )

    def auth_panel_visible(self):
        return self.find(self.AUTH_PANEL).is_displayed()
