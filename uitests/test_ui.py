"""UI 自动化测试用例。

使用 Page Object 模式 + 显式等待，不用固定 sleep，避免「时快时慢导致的偶发失败」。
"""

import uuid

import pytest

from pages.login_page import LoginPage
from pages.todo_page import TodoPage


def _user():
    """每次注册都用新账号，保证用例之间互不影响、可反复执行。"""
    return "ui" + uuid.uuid4().hex[:8]


class TestAuthFlow:
    def test_register_then_go_to_todo_panel(self, driver, base_url):
        """正向：注册成功后自动登录，直接进入待办面板。"""
        username = _user()
        login_page = LoginPage(driver, base_url).open()

        login_page.register(username, "Passw0rd").wait_logged_in()

        assert username in login_page.current_user()
        assert not login_page.auth_panel_visible()

    def test_login_with_wrong_password_shows_error(self, driver, base_url):
        """逆向：密码错误时停留在登录页并给出提示。"""
        username = _user()
        login_page = LoginPage(driver, base_url).open()
        login_page.register(username, "Passw0rd").wait_logged_in()
        TodoPage(driver).logout().wait_logged_out()

        login_page.login(username, "wrong_password")
        login_page.wait_message("用户名或密码错误")

        assert login_page.auth_panel_visible(), "密码错误时不应进入待办页面"

    def test_register_with_short_password_shows_error(self, driver, base_url):
        """逆向：密码少于 6 位时后端应返回校验提示。"""
        login_page = LoginPage(driver, base_url).open()

        login_page.register(_user(), "123")
        login_page.wait_message("密码长度需为 6-20 个字符")

    def test_logout_returns_to_login_panel(self, driver, base_url):
        """正向：退出登录后回到登录页，用户名重置为未登录。"""
        login_page = LoginPage(driver, base_url).open()
        login_page.register(_user(), "Passw0rd").wait_logged_in()

        TodoPage(driver).logout().wait_logged_out()

        assert login_page.auth_panel_visible()
        assert login_page.current_user() == "未登录"


class TestTodoUi:
    @pytest.fixture
    def todo_page(self, driver, base_url):
        """每个用例用一个全新账号登录，保证列表初始为空。"""
        LoginPage(driver, base_url).open().register(_user(), "Passw0rd").wait_logged_in()
        return TodoPage(driver)

    def test_add_todo_appears_in_list(self, todo_page):
        """正向：新增待办后立即出现在列表中，计数同步更新。"""
        todo_page.add("买牛奶").wait_title_present("买牛奶")

        assert todo_page.titles() == ["买牛奶"]
        assert "共 1 条" in todo_page.count_text()

    def test_add_empty_title_shows_hint(self, todo_page):
        """逆向：空标题不应创建成功，列表保持为空。"""
        todo_page.add("").wait_item_count(0)

        assert "请输入待办内容" in todo_page.message_text()
        assert todo_page.empty_hint_visible()

    def test_toggle_marks_item_done(self, todo_page):
        """正向：勾选复选框后条目进入已完成状态（划线样式）。"""
        todo_page.add("喝水").wait_title_present("喝水")

        todo_page.toggle_first().wait_first_done()

        assert todo_page.first_item_done()

    def test_delete_removes_item(self, todo_page):
        """正向：删除后条目从列表消失，并回到空列表提示。"""
        todo_page.add("临时任务").wait_title_present("临时任务")

        todo_page.delete_first().wait_title_absent("临时任务")

        assert todo_page.empty_hint_visible()

    def test_todos_are_isolated_between_users(self, driver, base_url):
        """隔离性：换一个账号登录后，看不到上一个账号的待办。"""
        LoginPage(driver, base_url).open().register(_user(), "Passw0rd").wait_logged_in()
        first_page = TodoPage(driver)
        first_page.add("账号A的待办").wait_title_present("账号A的待办")
        first_page.logout().wait_logged_out()

        LoginPage(driver, base_url).open().register(_user(), "Passw0rd").wait_logged_in()

        assert "账号A的待办" not in TodoPage(driver).titles()
