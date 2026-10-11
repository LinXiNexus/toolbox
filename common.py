#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用工具: 终端着色、输入、列表展示"""

import sys
import os
import unicodedata


C_TITLE = "\033[1;36m"; C_KEY = "\033[1;33m"; C_OK = "\033[1;32m"
C_ERR = "\033[1;31m"; C_WARN = "\033[1;35m"; C_DIM = "\033[2m"; C_RST = "\033[0m"

HOME = os.path.expanduser("~")


def line():
    print(C_DIM + "-" * 46 + C_RST)


def _disp_width(s):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _center(s, width):
    pad = max(0, width - _disp_width(s))
    left = pad // 2
    return " " * left + s + " " * (pad - left)


class BackToPrev(Exception):
    """用户输入 exit, 返回上一层"""
    pass


def ask(prompt):
    """普通输入(无返回), 用于分页等场景"""
    try:
        return input(prompt)
    except EOFError:
        print()
        print(C_DIM + " 输入结束，退出。" + C_RST)
        sys.exit(0)


BACK_WORDS = ("exit", "back", "返回")


def ask_input(prompt):
    """数据输入: 输入 exit / back / 返回 可回到上一层"""
    try:
        s = input(prompt)
    except EOFError:
        raise BackToPrev()
    s = s.strip()
    if s.lower() in BACK_WORDS:
        raise BackToPrev()
    return s


def show_list(results, save_path=None, title="生成完成"):
    """通用结果展示: 分页预览 + 可选保存; q 直接回主菜单"""
    line()
    print(C_TITLE + title + C_RST)
    line()
    print(" 候选总数: " + C_KEY + ("%d" % len(results)) + C_RST)
    if save_path:
        print(" 保存路径: " + C_KEY + save_path + C_RST)
    print()
    page = 20
    inter = sys.stdin.isatty() and sys.stdout.isatty()
    aborted = False
    if inter and len(results) > page:
        i = 0
        while i < len(results):
            for c in results[i:i + page]:
                print("   " + c)
            i += page
            if i < len(results):
                a = ask(C_DIM + " 回车继续 / q 返回主菜单 > " + C_RST).strip().lower()
                if a in ("q", "quit", "exit", "返回"):
                    aborted = True
                    break
        print(C_DIM + (" ...已中止预览" if aborted else " ...预览结束") + C_RST)
    else:
        for c in results:
            print("   " + c)
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(results) + "\n")
        print()
        print(C_OK + " [OK] 已写入 %d 条到 %s" % (len(results), save_path) + C_RST)
    if aborted:
        raise BackToPrev()
