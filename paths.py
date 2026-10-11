#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资源路径解析

让程序同时支持两种运行方式:
  1. 源码运行   python3 main.py
  2. 单文件运行 python3 toolbox.pyz   (zipapp)
"""

import os
import sys


def _here():
    return os.path.dirname(os.path.abspath(__file__))


def is_zipapp():
    """判断当前是否运行在 zipapp 里"""
    return not os.path.isdir(_here())


def base_dirs():
    """返回可能存放数据文件的目录(按优先级去重)"""
    out = []
    env = os.environ.get("TOOLBOX_DATA_DIR")
    if env:
        out.append(env)

    here = _here()
    if os.path.isdir(here):
        # 源码运行
        out.append(os.path.join(here, "data"))
        out.append(here)
    else:
        # zipapp: __file__ = /path/toolbox.pyz/paths.py
        # here = /path/toolbox.pyz  (zip 文件本身)
        # base = /path              (包含 zip 的目录)
        base = os.path.dirname(here)
        out.append(os.path.join(base, "data"))
        out.append(base)

    home = os.path.expanduser("~")
    out.append(os.path.join(home, ".cache", "toolbox", "data"))
    out.append(os.path.join(home, "toolbox", "data"))
    out.append(os.path.join(home, "tools", "toolbox", "data"))
    out.append(home)

    seen, res = set(), []
    for d in out:
        if d and d not in seen:
            seen.add(d)
            res.append(d)
    return res


def find_data(filename):
    """在候选目录里查找数据文件, 返回完整路径或 None"""
    for d in base_dirs():
        p = os.path.join(d, filename)
        if os.path.isfile(p):
            return p
    return None


def read_resource(filename):
    """读取随程序分发的资源(优先磁盘, 其次从 zipapp 里读), 返回 bytes 或 None"""
    p = find_data(filename)
    if p:
        try:
            with open(p, "rb") as f:
                return f.read()
        except OSError:
            pass

    if is_zipapp():
        # _here() 就是 .pyz 文件本身
        try:
            import zipfile
            with zipfile.ZipFile(_here()) as z:
                try:
                    return z.read(filename)
                except KeyError:
                    pass
        except Exception:
            pass

    # 源码目录里再试一次
    p = os.path.join(_here(), filename)
    if os.path.isfile(p):
        try:
            with open(p, "rb") as f:
                return f.read()
        except OSError:
            pass
    return None


def data_dir_for_write():
    """返回一个可写的数据目录(用于自动下载)"""
    home = os.path.expanduser("~")
    d = os.path.join(home, ".cache", "toolbox", "data")
    try:
        os.makedirs(d, exist_ok=True)
        return d
    except OSError:
        return home


def describe():
    here = _here()
    return {
        "运行方式": "zipapp 单文件" if is_zipapp() else "源码目录",
        "模块目录": here,
        "数据候选目录": base_dirs(),
    }
