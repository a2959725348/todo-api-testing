"""YAML 数据加载：把测试数据从用例代码里彻底剥离。"""

import os

import yaml

from config.settings import DATA_DIR


def load_yaml(filename):
    """读取 data/ 目录下的 YAML 文件，返回解析后的对象。"""
    path = filename if os.path.isabs(filename) else os.path.join(DATA_DIR, filename)
    with open(path, encoding="utf-8") as fp:
        return yaml.safe_load(fp)


def load_cases(filename, key="cases"):
    """取出用例列表，供 pytest.mark.parametrize 使用。

    YAML 里的每条用例都带 id 字段，直接作为用例名的一部分，
    失败了看一眼报告就知道是哪一组数据挂的。
    """
    data = load_yaml(filename) or {}
    return data.get(key, [])
