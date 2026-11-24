"""断言封装：失败时给出「期望 vs 实际」的完整上下文。"""


def assert_status(response, expected):
    assert response.status_code == expected, (
        f"状态码不符：期望 {expected}，实际 {response.status_code}；响应体={response.body}"
    )


def assert_code(response, expected_code):
    assert response.code == expected_code, (
        f"业务码不符：期望 {expected_code}，实际 {response.code}；msg={response.msg}"
    )


def assert_msg_contains(response, keyword):
    assert keyword in (response.msg or ""), (
        f"提示语未包含「{keyword}」，实际 msg={response.msg}"
    )


def assert_key(response, key):
    """校验返回体里是否包含指定字段（不校验值）。"""
    data = response.data if isinstance(response.data, dict) else {}
    assert key in data, f"返回数据缺少字段「{key}」，实际 data={data}"


def assert_equal(actual, expected, field=""):
    assert actual == expected, f"{field} 不符：期望 {expected}，实际 {actual}"
