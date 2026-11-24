"""注册接口 /api/register 测试用例。

覆盖维度：正向流程 + 用户名/密码长度边界 + 必填字段缺失 + 唯一性。
数据全部来自 data/register_cases.yaml，代码只负责「发请求 + 断言」。
"""

import uuid

import pytest

from common.asserts import assert_code, assert_msg_contains, assert_status
from common.yaml_loader import load_cases
from config.settings import BIZ_CODE, STATUS

CASES = load_cases("register_cases.yaml")


def _unique(prefix="u"):
    """生成唯一用户名，保证同一套用例可以反复执行而互不干扰。

    只用于「不关心用户名长度」的用例；长度边界用例必须用固定数据，
    否则长度就不是被测的那个边界值了。
    """
    return f"{prefix}{uuid.uuid4().hex[:10]}"


class TestRegister:
    @pytest.mark.smoke
    def test_register_success_returns_user(self, api):
        """正向：注册成功返回 201，且返回 id 与 username，不回显密码。"""
        payload = {"username": _unique("smoke_"), "password": "Passw0rd"}
        r = api.post("/api/register", json=payload)

        assert_status(r, STATUS["created"])
        assert_code(r, BIZ_CODE["success"])
        assert r.data["username"] == payload["username"]
        assert isinstance(r.data["id"], int)
        assert "password" not in r.data, "响应体不应回显密码字段"

    @pytest.mark.regression
    def test_register_duplicate_username(self, api):
        """逆向：同名账号二次注册应被拒绝。"""
        payload = {"username": _unique("dup_"), "password": "Passw0rd"}
        assert_status(api.post("/api/register", json=payload), STATUS["created"])

        r = api.post("/api/register", json=payload)

        assert_status(r, STATUS["bad_request"])
        assert_msg_contains(r, "已被占用")

    @pytest.mark.regression
    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_register_parameterized(self, api, case):
        """数据驱动：按 YAML 里的输入与期望结果校验注册接口。

        YAML 里的用户名是固定的，这依赖会话开始时的数据重置（fresh_data fixture）；
        否则第二次执行会撞上「用户名已被占用」。
        """
        payload = {}
        if "username" in case:
            payload["username"] = case["username"]
        if "password" in case:
            payload["password"] = case["password"]

        r = api.post("/api/register", json=payload)

        assert_status(r, case["expect_status"])
        if "expect_msg" in case:
            assert_msg_contains(r, case["expect_msg"])
        if "expect_field" in case:
            assert case["expect_field"] in r.data, f"响应缺少字段 {case['expect_field']}"

    @pytest.mark.regression
    def test_register_empty_body(self, api):
        """异常：不带请求体时不应报 500，而是给出明确的参数错误。"""
        r = api.post("/api/register", json={})

        assert_status(r, STATUS["bad_request"])
        assert_code(r, BIZ_CODE["bad_request"])

    @pytest.mark.regression
    def test_register_non_json_body(self, api):
        """异常：Content-Type 不是 JSON 时，服务应返回 400 而不是崩溃。"""
        r = api.post(
            "/api/register",
            data="username=abc&password=123456",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert r.status_code == STATUS["bad_request"], (
            f"非 JSON 请求体应返回 400，实际 {r.status_code}"
        )
