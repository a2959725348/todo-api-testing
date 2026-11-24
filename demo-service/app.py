"""极简待办事项服务（被测系统 SUT）——用于接口自动化测试练习。

仅使用内存存储，启动快、无外部依赖，方便在 CI 中直接跑。
"""

import os
from functools import wraps

from flask import Flask, g, jsonify, render_template, request

from auth import decode_token, encode_token
from store import Store

SECRET_KEY = "todo-demo-secret-key"

# 只有显式打开测试模式才暴露数据重置接口，避免线上环境被误调
TEST_MODE = os.getenv("TEST_MODE") == "1"

MSG = {
    "ok": "ok",
    "no_auth": "未登录或登录凭证为空",
    "bad_token": "登录凭证无效或已过期",
    "missing_field": "缺少必填字段",
    "username_len": "用户名长度需为 3-20 个字符",
    "password_len": "密码长度需为 6-20 个字符",
    "username_exists": "用户名已被占用",
    "bad_credential": "用户名或密码错误",
    "title_len": "标题长度需为 1-50 个字符",
    "bad_done": "done 字段必须为布尔类型",
    "not_found": "待办不存在",
    "forbidden": "无权操作他人的待办",
}


def _fail(status, msg):
    return jsonify({"code": status, "msg": msg}), status


def _ok(data=None, status=200):
    return jsonify({"code": 0, "msg": MSG["ok"], "data": data}), status


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return _fail(401, MSG["no_auth"])
        user_id = decode_token(header[7:].strip(), request.app_secret)
        if user_id is None:
            return _fail(401, MSG["bad_token"])
        g.user_id = user_id
        return fn(*args, **kwargs)

    return wrapper


def create_app(store=None, secret_key=SECRET_KEY):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secret_key
    app.config["STORE"] = store or Store()
    # request.app_secret 便于装饰器取用，避免循环导入 current_app
    app.app_secret = secret_key

    def store():
        return app.config["STORE"]

    @app.before_request
    def _bind_secret():
        request.app_secret = app.config["SECRET_KEY"]

    # ---------------- 页面 ----------------
    @app.get("/")
    def index():
        """演示用的前端页面，UI 自动化测试的直接被测对象。"""
        return render_template("index.html")

    # ---------------- 认证模块 ----------------
    @app.post("/api/register")
    def register():
        body = request.get_json(silent=True) or {}
        username = body.get("username")
        password = body.get("password")
        if not username or not password:
            return _fail(400, MSG["missing_field"])
        if not isinstance(username, str) or not 3 <= len(username) <= 20:
            return _fail(400, MSG["username_len"])
        if not isinstance(password, str) or not 6 <= len(password) <= 20:
            return _fail(400, MSG["password_len"])
        if store().find_user_by_name(username):
            return _fail(400, MSG["username_exists"])
        user = store().create_user(username, password)
        return _ok({"id": user["id"], "username": user["username"]}, status=201)

    @app.post("/api/login")
    def login():
        body = request.get_json(silent=True) or {}
        username = body.get("username")
        password = body.get("password")
        if not username or not password:
            return _fail(400, MSG["missing_field"])
        user = store().find_user_by_name(username)
        if not user or not store().verify_password(user, password):
            return _fail(400, MSG["bad_credential"])
        return _ok({"token": encode_token(user["id"], app.config["SECRET_KEY"]), "user_id": user["id"]})

    # ---------------- 待办模块 ----------------
    @app.get("/api/todos")
    @require_auth
    def list_todos():
        return _ok(store().list_todos(g.user_id))

    @app.post("/api/todos")
    @require_auth
    def create_todo():
        body = request.get_json(silent=True) or {}
        title = body.get("title")
        if title is None:
            return _fail(400, MSG["missing_field"])
        err = _check_title(title)
        if err:
            return err
        todo = store().create_todo(g.user_id, title, body.get("description", ""))
        return _ok(todo, status=201)

    @app.get("/api/todos/<int:todo_id>")
    @require_auth
    def get_todo(todo_id):
        todo = store().get_todo(todo_id)
        if todo is None:
            return _fail(404, MSG["not_found"])
        if todo["user_id"] != g.user_id:
            return _fail(403, MSG["forbidden"])
        return _ok(todo)

    @app.put("/api/todos/<int:todo_id>")
    @require_auth
    def update_todo(todo_id):
        todo = store().get_todo(todo_id)
        if todo is None:
            return _fail(404, MSG["not_found"])
        if todo["user_id"] != g.user_id:
            return _fail(403, MSG["forbidden"])
        body = request.get_json(silent=True) or {}
        if "title" in body:
            err = _check_title(body["title"])
            if err:
                return err
        if "done" in body and not isinstance(body["done"], bool):
            return _fail(400, MSG["bad_done"])
        return _ok(store().update_todo(todo_id, body))

    @app.delete("/api/todos/<int:todo_id>")
    @require_auth
    def delete_todo(todo_id):
        todo = store().get_todo(todo_id)
        if todo is None:
            return _fail(404, MSG["not_found"])
        if todo["user_id"] != g.user_id:
            return _fail(403, MSG["forbidden"])
        store().delete_todo(todo_id)
        return _ok({"id": todo_id})

    # ---------------- 测试辅助 ----------------
    @app.post("/api/_test/reset")
    def reset_data():
        """清空内存数据，让同一套用例可以反复执行。

        仅在 TEST_MODE=1 时可用；自动化测试在会话开始时调用一次。
        """
        if not TEST_MODE:
            return _fail(404, MSG["not_found"])
        app.config["STORE"] = Store()
        return _ok({"reset": True})

    return app


def _check_title(title):
    if not isinstance(title, str) or not 1 <= len(title) <= 50:
        return _fail(400, MSG["title_len"])
    return None


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
