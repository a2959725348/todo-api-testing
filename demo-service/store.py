"""内存数据存储层：用户表 + 待办表。"""

import hashlib
import hmac
import threading

_ITER = 100_000


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER).hex()


class Store:
    def __init__(self):
        self._lock = threading.Lock()
        self._users = {}
        self._todos = {}
        self._seq_user = 0
        self._seq_todo = 0

    # ---------------- 用户 ----------------
    def create_user(self, username, password):
        with self._lock:
            self._seq_user += 1
            salt = f"salt{self._seq_user}"
            user = {
                "id": self._seq_user,
                "username": username,
                "salt": salt,
                "password": _hash(password, salt),
            }
            self._users[self._seq_user] = user
            return user

    def find_user_by_name(self, username):
        with self._lock:
            for user in self._users.values():
                if user["username"] == username:
                    return user
            return None

    def verify_password(self, user, password):
        return hmac.compare_digest(user["password"], _hash(password, user["salt"]))

    # ---------------- 待办 ----------------
    def create_todo(self, user_id, title, description=""):
        with self._lock:
            self._seq_todo += 1
            todo = {
                "id": self._seq_todo,
                "user_id": user_id,
                "title": title,
                "description": description,
                "done": False,
            }
            self._todos[self._seq_todo] = todo
            return dict(todo)

    def get_todo(self, todo_id):
        with self._lock:
            todo = self._todos.get(todo_id)
            return dict(todo) if todo else None

    def list_todos(self, user_id):
        with self._lock:
            return [dict(t) for t in self._todos.values() if t["user_id"] == user_id]

    def update_todo(self, todo_id, patch):
        with self._lock:
            todo = self._todos.get(todo_id)
            if todo is None:
                return None
            for field in ("title", "description", "done"):
                if field in patch:
                    todo[field] = patch[field]
            return dict(todo)

    def delete_todo(self, todo_id):
        with self._lock:
            return self._todos.pop(todo_id, None) is not None
