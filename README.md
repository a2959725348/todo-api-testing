# 待办清单接口自动化测试框架

公开仓库：[a2959725348/todo-api-testing](https://github.com/a2959725348/todo-api-testing)

一个可以直接跑起来的接口自动化测试项目：**自带被测服务**，clone 下来一条命令就能看到 45 条用例全绿，不需要你额外找接口、不需要连数据库。

## 为什么做这个项目

学测试最难的不是写断言，而是**没有东西可测**。所以这个项目把一个待办清单服务的后端和前端一起写出来，再针对它写接口自动化和 UI 自动化——被测对象和测试代码放在同一个仓库，任何时候都能复现。

## 技术栈

| 分类 | 选型 | 用途 |
| --- | --- | --- |
| 语言 | Python 3.10+ | 主语言 |
| 测试框架 | pytest | 用例组织、参数化、fixture |
| 请求库 | requests | 封装统一 HTTP 客户端 |
| 数据驱动 | PyYAML | 用例数据放 YAML，与代码解耦 |
| UI 自动化 | Selenium 4 | Page Object 模式驱动浏览器 |
| 被测服务 | Flask | 提供待办清单的 REST 接口与页面 |
| 报告 | Allure | 可读的测试报告 |
| CI | GitHub Actions | 每次 push 自动跑全量用例 |

## 目录结构

```
todo-api-testing/
├── demo-service/              # 被测系统（Flask，内存存储）
│   ├── app.py                 # 接口定义
│   ├── store.py               # 数据层
│   ├── auth.py                # token 签发与校验
│   ├── templates/index.html   # 前端页面
│   └── static/                # 前端 JS / CSS
├── config/
│   └── settings.py            # 地址、超时、状态码等全局配置
├── common/
│   ├── http_client.py         # 统一请求封装 + 日志
│   ├── yaml_loader.py         # 测试数据加载
│   └── asserts.py             # 断言封装（失败时打印期望 vs 实际）
├── data/                      # 用例数据（YAML，数据驱动）
│   ├── register_cases.yaml
│   ├── login_cases.yaml
│   └── todo_cases.yaml
├── testcases/                 # 接口测试用例
│   ├── test_register.py
│   ├── test_login.py
│   └── test_todo.py
├── uitests/                   # UI 自动化测试
│   ├── pages/                 # Page Object
│   └── test_ui.py
├── docs/
│   └── 测试用例设计文档.md      # 手工测试用例设计（含设计方法与用例清单）
├── conftest.py                # pytest 全局 fixture
├── pytest.ini                 # 接口测试配置
├── ui.ini                     # UI 测试配置
└── requirements.txt
```

## 快速开始

```bash
# 1. 克隆并进入目录
git clone https://github.com/a2959725348/todo-api-testing.git
cd todo-api-testing

# 2. 建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

# 3. 跑接口测试（会自动拉起被测服务，跑完自动关闭）
pytest

# 4. 跑 UI 测试
pytest -c ui.ini
```

跑完看到这样的结果就说明环境没问题：

```
45 passed in 6.05s        # 接口测试
9 passed in 29.62s        # UI 测试
```

> 被测服务是自动管理的：脚本发现 `127.0.0.1:5000` 没有服务就自己拉一个，测试结束再关掉。
> 如果你已经手动启动了服务，它会直接复用，不会重复启动或误杀。

本轮本地验证见 [2026-11-24 执行记录](docs/测试执行记录-20261124.md)。仓库包含被测服务、测试代码和用例文档，不包含个人简历、真实账号或工作台数据库。

## 测试覆盖了什么

| 模块 | 用例数 | 覆盖点 |
| --- | --- | --- |
| 用户注册 | 13 | 正向流程、用户名/密码长度边界、必填字段缺失、唯一性、异常请求体 |
| 用户登录 | 8 | 正向登录、密码错误、空值、账号不存在、大小写敏感、token 稳定性 |
| 待办管理 | 17 | 增删改查闭环、标题边界、类型异常、特殊字符与 emoji、跨用户隔离 |
| 鉴权越权 | 5 | 无 token、伪造 token、查看/修改/删除他人数据 |
| UI 流程 | 9 | 注册登录、错误提示、退出、增删改、状态切换、账号隔离 |

手工设计用例合计 **52 条**；落到自动化脚本后为 **54 条**（接口 45 + UI 9），全部通过。

> 自动化条数比手工设计多，是因为参数化会把一条「长度边界」用例展开成多组数据分别执行。

## 这套框架做了什么设计

**1. 请求与断言分层**
用例里只写三段式：准备数据 → 调接口 → 断言。地址、超时、请求头、日志都收在 `common/http_client.py`，想改 BaseURL 只改一处（或设环境变量 `BASE_URL`）。

**2. 数据驱动**
长度边界、必填校验这些「输入不同、逻辑一样」的用例，数据全放 `data/*.yaml`，Python 里只用 `@pytest.mark.parametrize` 跑一遍。加一条用例只改 YAML，不碰代码。

**3. 用例相互隔离**
每个用例用独立账号（`uuid` 生成），配合会话开始时的数据重置，保证整套用例可以反复执行、结果稳定——这一点很重要，很多人的自动化跑第二遍就挂在这里。

**4. 断言失败信息可读**
断言不是裸 `assert a == b`，而是封装成带上下文的函数：

```
状态码不符：期望 400，实际 200；响应体={'code': 0, 'msg': 'ok', ...}
```

**5. UI 自动化不用 sleep**
前端每次操作后都会重渲染列表，旧元素句柄会立刻失效（`StaleElementReferenceException`）。框架用「重试 + 显式等待」代替固定 `sleep`，并区分了「取值」和「等条件」两种语义——这是手写 UI 自动化最容易踩的坑。

**6. CI 里自动跑**
`.github/workflows/test.yml` 在每次 push 时自动装依赖、拉服务、跑全量用例并上传 Allure 报告。

## 用例设计

完整的用例设计文档见 [`docs/测试用例设计文档.md`](docs/测试用例设计文档.md)，里面写了模块划分、每种设计方法用在哪、以及全部用例清单和预期结果。

核心是在用「等价类 + 边界值 + 判定表 + 场景法」四件套，而不是凭感觉列功能点。

## 已知限制

- 被测服务是内存存储，重启数据就没了，不适合做持久化相关测试；
- 没做性能和兼容性测试，不在本项目范围内；
- UI 用例默认无头模式运行，设置 `HEADLESS=0` 可以在本地看着浏览器执行。

## License

MIT
