"""待办接口 /api/todos 测试用例。

覆盖维度：增删改查正向流程、入参边界、对象不存在、跨用户越权、未登录拦截。
"""

import pytest

from common.asserts import assert_code, assert_msg_contains, assert_status
from common.yaml_loader import load_cases
from config.settings import BIZ_CODE, STATUS

TODO_CASES = load_cases("todo_cases.yaml")


class TestTodoCrud:
    @pytest.mark.smoke
    def test_create_todo_success(self, auth_api):
        """正向：新增待办返回 201，字段与入参一致，done 默认 False。"""
        r = auth_api.post(
            "/api/todos", json={"title": "买牛奶", "description": "低脂的"}
        )

        assert_status(r, STATUS["created"])
        assert r.data["title"] == "买牛奶"
        assert r.data["description"] == "低脂的"
        assert r.data["done"] is False

    @pytest.mark.smoke
    def test_list_contains_created_todo(self, auth_api, todo_factory):
        """正向：新建的待办能出现在列表里。"""
        todo = todo_factory(title="列表校验")

        r = auth_api.get("/api/todos")

        assert_status(r, STATUS["ok"])
        ids = [item["id"] for item in r.data]
        assert todo["id"] in ids, f"新建待办 {todo['id']} 未出现在列表中：{ids}"

    @pytest.mark.regression
    def test_get_todo_detail(self, auth_api, todo_factory):
        """正向：按 id 查询待办详情。"""
        todo = todo_factory(title="详情校验")

        r = auth_api.get(f"/api/todos/{todo['id']}")

        assert_status(r, STATUS["ok"])
        assert r.data["id"] == todo["id"]
        assert r.data["title"] == "详情校验"

    @pytest.mark.regression
    def test_update_todo_title_and_done(self, auth_api, todo_factory):
        """正向：更新标题与完成状态，返回更新后的对象。"""
        todo = todo_factory(title="待更新")

        r = auth_api.put(
            f"/api/todos/{todo['id']}", json={"title": "已更新", "done": True}
        )

        assert_status(r, STATUS["ok"])
        assert r.data["title"] == "已更新"
        assert r.data["done"] is True

    @pytest.mark.regression
    def test_delete_todo_then_get_404(self, auth_api, todo_factory):
        """正向：删除后再次查询应返回 404，形成完整闭环。"""
        todo = todo_factory(title="待删除")

        assert_status(auth_api.delete(f"/api/todos/{todo['id']}"), STATUS["ok"])

        r = auth_api.get(f"/api/todos/{todo['id']}")
        assert_status(r, STATUS["not_found"])

    @pytest.mark.regression
    def test_list_only_returns_own_todos(self, auth_api, other_api, todo_factory):
        """隔离性：A 用户的列表里不应出现 B 用户的数据。"""
        mine = todo_factory(title="我的待办")
        other_api.post("/api/todos", json={"title": "别人的待办"})

        r = auth_api.get("/api/todos")

        ids = [item["id"] for item in r.data]
        assert mine["id"] in ids
        assert all(
            item["title"] != "别人的待办" for item in r.data
        ), f"出现了他人数据：{r.data}"


class TestTodoValidation:
    @pytest.mark.regression
    @pytest.mark.parametrize("case", TODO_CASES, ids=[c["id"] for c in TODO_CASES])
    def test_create_todo_parameterized(self, auth_api, case):
        """数据驱动：标题长度边界、类型校验、特殊字符。"""
        r = auth_api.post("/api/todos", json={"title": case["title"]})

        assert_status(r, case["expect_status"])
        if "expect_msg" in case:
            assert_msg_contains(r, case["expect_msg"])

    @pytest.mark.regression
    def test_create_todo_missing_title(self, auth_api):
        """异常：缺少 title 字段时应提示字段缺失。"""
        r = auth_api.post("/api/todos", json={"description": "没有标题"})

        assert_status(r, STATUS["bad_request"])
        assert_msg_contains(r, "缺少必填字段")

    @pytest.mark.regression
    def test_update_todo_invalid_done_type(self, auth_api, todo_factory):
        """异常：done 传入字符串而非布尔值，应被拦截。"""
        todo = todo_factory()

        r = auth_api.put(f"/api/todos/{todo['id']}", json={"done": "yes"})

        assert_status(r, STATUS["bad_request"])
        assert_msg_contains(r, "done 字段必须为布尔类型")

    @pytest.mark.regression
    def test_get_nonexistent_todo(self, auth_api):
        """异常：查询不存在的待办返回 404。"""
        r = auth_api.get("/api/todos/999999")

        assert_status(r, STATUS["not_found"])
        assert_code(r, BIZ_CODE["not_found"])


class TestTodoPermission:
    @pytest.mark.smoke
    def test_request_without_token(self, anon_api):
        """鉴权：不带 Token 访问待办列表应返回 401 而不是 200。"""
        r = anon_api.get("/api/todos")

        assert_status(r, STATUS["unauthorized"])
        assert_msg_contains(r, "未登录")

    @pytest.mark.regression
    def test_request_with_invalid_token(self, anon_api):
        """鉴权：伪造的 Token 应被拒绝。"""
        anon_api.set_token("1.deadbeefdeadbeefdeadbeefdeadbeef")

        r = anon_api.get("/api/todos")

        assert_status(r, STATUS["unauthorized"])
        assert_msg_contains(r, "无效")

    @pytest.mark.regression
    def test_get_other_user_todo_forbidden(self, other_api, todo_factory):
        """越权：A 用户不能查看 B 用户的待办。"""
        mine = todo_factory(title="私有待办")

        r = other_api.get(f"/api/todos/{mine['id']}")

        assert_status(r, STATUS["forbidden"])
        assert_msg_contains(r, "无权")

    @pytest.mark.regression
    def test_update_other_user_todo_forbidden(self, other_api, todo_factory):
        """越权：A 用户不能修改 B 用户的待办。"""
        mine = todo_factory(title="别人的修改目标")

        r = other_api.put(f"/api/todos/{mine['id']}", json={"title": "被篡改"})

        assert_status(r, STATUS["forbidden"])

    @pytest.mark.regression
    def test_delete_other_user_todo_forbidden(self, other_api, auth_api, todo_factory):
        """越权：A 用户不能删除 B 用户的待办，且原数据依然存在。"""
        mine = todo_factory(title="别人的删除目标")

        r = other_api.delete(f"/api/todos/{mine['id']}")
        assert_status(r, STATUS["forbidden"])

        assert_status(auth_api.get(f"/api/todos/{mine['id']}"), STATUS["ok"])
