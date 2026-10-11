#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主控: 主菜单与模块分发"""

import sys

from common import (line, ask_input, BackToPrev, _center,
                    C_TITLE, C_KEY, C_ERR, C_DIM, C_RST)
import idcard
import phone
import updater


def banner():
    W = 44
    print()
    print(C_TITLE + "+" + "=" * W + "+")
    print("|" + _center("常用工具集", W) + "|")
    print("|" + _center("v" + updater.local_version(), W) + "|")
    print("+" + "=" * W + "+" + C_RST)


def menu():
    print()
    print(" 请选择功能：")
    print("   " + C_KEY + "[1]" + C_RST + " 身份证菜单")
    print("   " + C_KEY + "[2]" + C_RST + " 手机号菜单")
    print("   " + C_KEY + "[3]" + C_RST + " 检查更新")
    print("   " + C_KEY + "[4]" + C_RST + " 本地 Web 界面")
    print("   " + C_KEY + "[0]" + C_RST + " 退出")
    print(C_DIM + " 提示: 任意输入处输入 exit 可返回上一层。" + C_RST)
    print()
    while True:
        try:
            ans = ask_input(C_KEY + " 请输入序号 (exit 退出) > " + C_RST)
        except BackToPrev:
            return None
        if ans == "1":
            return "id"
        if ans == "2":
            return "phone"
        if ans == "3":
            return "update"
        if ans == "4":
            return "web"
        if ans in ("0", "q", "quit"):
            return None
        print(C_ERR + " [错误] 请输入 1 / 2 / 3 / 4 / 0。" + C_RST)


def _run_web():
    try:
        import web
    except Exception as e:
        print(C_ERR + " [错误] 无法加载 web.py: %s" % e + C_RST)
        return
    print(C_DIM + " 启动 Web 界面，Ctrl+C 可返回主菜单" + C_RST)
    try:
        web.serve()
    except KeyboardInterrupt:
        pass


def main():
    banner()
    updater.maybe_check()
    while True:
        mode = menu()
        if mode is None:
            print(C_DIM + " 再见。" + C_RST)
            break
        print()
        try:
            if mode == "id":
                idcard.run_id_menu()
            elif mode == "phone":
                phone.run_phone_menu()
            elif mode == "update":
                updater.manual_check()
            elif mode == "web":
                _run_web()
        except BackToPrev:
            pass
        line()
        print(C_DIM + " 已返回主菜单。" + C_RST)


if __name__ == "__main__":
    try:
        _args = sys.argv[1:]
        if _args and _args[0] in ("--web", "-w"):
            import web
            _port = web.DEFAULT_PORT
            if len(_args) > 1 and _args[1].isdigit():
                _port = int(_args[1])
            sys.exit(web.serve(port=_port, open_browser=("--open" in _args)))
        if updater.cli(_args):
            sys.exit(0)
        main()
    except KeyboardInterrupt:
        print("\n" + C_ERR + "已取消。" + C_RST)
        sys.exit(130)
