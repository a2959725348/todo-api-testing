"""接口自动化测试框架 —— 配置与全局常量。

被测服务地址优先级：环境变量 BASE_URL > 本文件默认值，
这样本地调试和 CI 里跑同一套代码只需要改环境变量。
"""

import os

# 被测服务根地址
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")

# 请求默认超时（秒）
TIMEOUT = float(os.getenv("API_TIMEOUT", "10"))

# 日志文件
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "api_test.log")

# 用例数据目录
DATA_DIR = os.getenv("DATA_DIR", "data")

# 各类断言期望的 HTTP 状态码，集中管理避免散落在用例里
STATUS = {
    "ok": 200,
    "created": 201,
    "bad_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "not_found": 404,
}

# 业务错误码
BIZ_CODE = {
    "success": 0,
    "bad_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "not_found": 404,
}
