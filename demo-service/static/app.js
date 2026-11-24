/* 前端逻辑：所有请求都走同源的 /api/*，与接口自动化测试共用同一套后端。 */
(function () {
  "use strict";

  const els = {
    authPanel: document.getElementById("auth-panel"),
    todoPanel: document.getElementById("todo-panel"),
    tabLogin: document.getElementById("tab-login"),
    tabRegister: document.getElementById("tab-register"),
    authForm: document.getElementById("auth-form"),
    authSubmit: document.getElementById("auth-submit"),
    authMessage: document.getElementById("auth-message"),
    username: document.getElementById("username"),
    password: document.getElementById("password"),
    currentUser: document.getElementById("current-user"),
    logoutBtn: document.getElementById("logout-btn"),
    todoForm: document.getElementById("todo-form"),
    todoInput: document.getElementById("todo-input"),
    todoMessage: document.getElementById("todo-message"),
    todoList: document.getElementById("todo-list"),
    todoCount: document.getElementById("todo-count"),
    emptyHint: document.getElementById("empty-hint"),
    clearDone: document.getElementById("clear-done"),
  };

  const state = {
    mode: "login", // login | register
    token: localStorage.getItem("token") || "",
    username: localStorage.getItem("username") || "",
  };

  // ---------------- 基础请求 ----------------
  async function api(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (state.token) headers.Authorization = "Bearer " + state.token;
    const resp = await fetch(path, {
      method: method,
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let payload = null;
    try {
      payload = await resp.json();
    } catch (e) {
      payload = null;
    }
    return { status: resp.status, body: payload || {} };
  }

  function showMessage(el, text, ok) {
    el.textContent = text || "";
    el.classList.toggle("success", !!ok);
  }

  // ---------------- 登录态 ----------------
  function enterApp() {
    els.authPanel.classList.add("hidden");
    els.todoPanel.classList.remove("hidden");
    els.currentUser.textContent = state.username || "已登录";
    loadTodos();
  }

  function leaveApp() {
    state.token = "";
    state.username = "";
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    els.todoPanel.classList.add("hidden");
    els.authPanel.classList.remove("hidden");
    els.currentUser.textContent = "未登录";
    els.authForm.reset();
    showMessage(els.authMessage, "");
    els.todoList.innerHTML = "";
  }

  // ---------------- 认证 ----------------
  els.tabLogin.addEventListener("click", function () {
    state.mode = "login";
    els.tabLogin.classList.add("active");
    els.tabRegister.classList.remove("active");
    els.authSubmit.textContent = "登录";
    showMessage(els.authMessage, "");
  });

  els.tabRegister.addEventListener("click", function () {
    state.mode = "register";
    els.tabRegister.classList.add("active");
    els.tabLogin.classList.remove("active");
    els.authSubmit.textContent = "注册";
    showMessage(els.authMessage, "");
  });

  els.authForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const username = els.username.value.trim();
    const password = els.password.value;
    const path = state.mode === "login" ? "/api/login" : "/api/register";
    const res = await api("POST", path, { username: username, password: password });

    if (res.status >= 400) {
      showMessage(els.authMessage, res.body.msg || "操作失败，请稍后重试");
      return;
    }

    if (state.mode === "register") {
      showMessage(els.authMessage, "注册成功，正在登录…", true);
      const login = await api("POST", "/api/login", {
        username: username,
        password: password,
      });
      if (login.status >= 400) {
        showMessage(els.authMessage, login.body.msg || "自动登录失败，请手动登录");
        return;
      }
      state.token = login.body.data.token;
      state.username = username;
    } else {
      state.token = res.body.data.token;
      state.username = username;
    }

    localStorage.setItem("token", state.token);
    localStorage.setItem("username", state.username);
    showMessage(els.authMessage, "");
    enterApp();
  });

  els.logoutBtn.addEventListener("click", leaveApp);

  // ---------------- 待办 ----------------
  async function loadTodos() {
    const res = await api("GET", "/api/todos");
    if (res.status === 401) {
      leaveApp();
      return;
    }
    if (res.status >= 400) {
      showMessage(els.todoMessage, res.body.msg || "加载失败");
      return;
    }
    renderTodos(res.body.data || []);
  }

  function renderTodos(todos) {
    els.todoList.innerHTML = "";
    todos.forEach(function (todo) {
      els.todoList.appendChild(buildItem(todo));
    });
    els.todoCount.textContent = "共 " + todos.length + " 条";
    els.emptyHint.classList.toggle("hidden", todos.length > 0);
  }

  function buildItem(todo) {
    const li = document.createElement("li");
    li.className = "todo-item" + (todo.done ? " done" : "");
    li.dataset.id = String(todo.id);

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = !!todo.done;
    checkbox.className = "todo-check";
    checkbox.addEventListener("change", function () {
      toggleTodo(todo.id, checkbox.checked);
    });

    const span = document.createElement("span");
    span.className = "todo-title";
    span.textContent = todo.title;

    const del = document.createElement("button");
    del.type = "button";
    del.className = "btn-delete";
    del.textContent = "删除";
    del.addEventListener("click", function () {
      deleteTodo(todo.id);
    });

    li.appendChild(checkbox);
    li.appendChild(span);
    li.appendChild(del);
    return li;
  }

  els.todoForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const title = els.todoInput.value.trim();
    if (!title) {
      showMessage(els.todoMessage, "请输入待办内容");
      return;
    }
    const res = await api("POST", "/api/todos", { title: title });
    if (res.status >= 400) {
      showMessage(els.todoMessage, res.body.msg || "添加失败");
      return;
    }
    els.todoInput.value = "";
    showMessage(els.todoMessage, "");
    loadTodos();
  });

  async function toggleTodo(id, done) {
    const res = await api("PUT", "/api/todos/" + id, { done: done });
    if (res.status >= 400) {
      showMessage(els.todoMessage, res.body.msg || "更新失败");
      return;
    }
    loadTodos();
  }

  async function deleteTodo(id) {
    const res = await api("DELETE", "/api/todos/" + id);
    if (res.status >= 400) {
      showMessage(els.todoMessage, res.body.msg || "删除失败");
      return;
    }
    loadTodos();
  }

  els.clearDone.addEventListener("click", async function () {
    const res = await api("GET", "/api/todos");
    const todos = (res.body.data || []).filter(function (t) {
      return t.done;
    });
    for (const todo of todos) {
      await api("DELETE", "/api/todos/" + todo.id);
    }
    loadTodos();
  });

  // ---------------- 启动 ----------------
  if (state.token) {
    enterApp();
  } else {
    leaveApp();
  }
})();
