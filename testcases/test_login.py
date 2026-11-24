"""登录接口 /api/login 测试用例。

覆盖维度：正常登录、密码错误、空值、未注册账号、大小写敏感、Token 可用性。
"""

import pytest

from common.asserts import assert_code, assert_msg_contains, assert_status
from common.yaml_loader import load_cases
from config.settings import BIZ_CODE, STATUS

CASES = load_cases("login_cases.yaml")


class TestLogin:
    @pytest.mark.smoke
    def test_login_success_returns_token(self, api, user):
        """正向：账号密码正确时返回 token 与 user_id。"""
        r = api.post(
            "/api/login",
            json={"username": user["username"], "password": user["password"]},
        )

        assert_status(r, STATUS["ok"])
        assert_code(r, BIZ_CODE["success"])
        assert r.data["token"], "登录成功必须返回非空 token"
        assert r.data["user_id"] > 0

    @pytest.mark.smoke
    def test_token_grants_access(self, auth_api):
        """正向：拿到的 token 能直接访问需要鉴权的接口。"""
        r = auth_api.get("/api/todos")

        assert_status(r, STATUS["ok"])
        assert_code(r, BIZ_CODE["success"])

    @pytest.mark.regression
    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_login_parameterized(self, api, user, case):
        """数据驱动：YAML 中 password 为 correct 时取真实密码，否则取字面值。"""
        username = case.get("username", user["username"])
        if username == "__UPPER__":
            username = user["username"].upper()
        password = case["password"]
        if password == "correct":
            password = user["password"]

        r = api.post("/api/login", json={"username": username, "password": password})

        assert_status(r, case["expect_status"])
        if "expect_msg" in case:
            assert_msg_contains(r, case["expect_msg"])
        if "expect_field" in case:
            assert case["expect_field"] in r.data

    @pytest.mark.regression
    def test_login_token_is_stable(self, api, user):
        """Token 由 user_id + 时间无关的签名生成，同一账号应稳定一致。"""
        payload = {"username": user["username"], "password": user["password"]}
        first = api.post("/api/login", json=payload).data["token"]
        second = api.post("/api/login", json=payload).data["token"]

        assert first == second, "同一账号连续登录的 token 应保持一致（当前实现为无状态签名）"
