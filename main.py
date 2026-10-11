#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主控: 默认后台启动 Web 界面 + 保留命令行菜单

用法:
    toolbox              默认: 后台开 Web + 打开浏览器 + 命令行菜单
    toolbox --cli        只用命令行(不开 Web)
    toolbox --web [端口] 只开 Web(前台)
    toolbox --web-port N 指定后台 Web 的端口
    toolbox --check      检查更新
    toolbox --update     立即更新
    toolbox --version    显示版本
"""

import sys
import threading

from common import (line, ask_input, BackToPrev, _center,
                    C_TITLE, C_KEY, C_OK, C_ERR, C_WARN, C_DIM, C_RST)
import idcard
import phone
import updater

WEB_PORT = 8765
_web = {"url": None, "err": None}


def banner():
    W = 44
    print()
    print(C_TITLE + "+" + "=" * W + "+")
    print("|" + _center("常用工具集", W) + "|")
    print("|" + _center("v" + updater.local_version(), W) + "|")
    print("+" + "=" * W + "+" + C_RST)


def start_web(port):
    """在后台线程启动 Web 服务, 返回 (url, err)"""
    try:
        import web
    except Exception as e:
        return None, "无法加载 web.py: %s" % e
    if not web.port_free("127.0.0.1", port):
        return None, "端口 %d 已被占用" % port
    t = threading.Thread(
        target=lambda: web.serve(host="127.0.0.1", port=port, quiet=True),
        daemon=True)
    t.start()
    url = web.web_url(port)
    _web["url"] = url
    return url, None


def open_browser():
    if not _web["url"]:
        return False
    try:
        import web
        threading.Thread(target=lambda: web.open_url(_web["url"]), daemon=True).start()
        return True
    except Exception:
        return False


def menu():
    print()
    print(" 请选择功能：")
    print("   " + C_KEY + "[1]" + C_RST + " 身份证菜单")
    print("   " + C_KEY + "[2]" + C_RST + " 手机号菜单")
    print("   " + C_KEY + "[3]" + C_RST + " 检查更新")
    if _web["url"]:
        print("   " + C_KEY + "[4]" + C_RST + " 打开网页  " + C_DIM + _web["url"] + C_RST)
    else:
        print("   " + C_KEY + "[4]" + C_RST + " 启动网页界面")
    print("   " + C_KEY + "[0]" + C_RST + " 退出")
    print(C_DIM + " 提示: 输入 exit 返回上一层；网页和命令行可同时使用" + C_RST)
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


def _open_web():
    """菜单 [4]: 有就打开浏览器, 没有就启动"""
    if _web["url"]:
        print(C_OK + " [OK] 网页地址: " + _web["url"] + C_RST)
        if open_browser():
            print(C_DIM + "      已尝试打开浏览器" + C_RST)
        else:
            print(C_DIM + "      请在浏览器里手动打开上面的地址" + C_RST)
        return
    url, e = start_web(WEB_PORT)
    if url:
        print(C_OK + " [OK] Web 界面已启动: " + url + C_RST)
        open_browser()
    else:
        print(C_ERR + " [错误] " + str(e) + C_RST)


def main(enable_web=True, port=WEB_PORT):
    banner()
    updater.maybe_check()

    if enable_web:
        url, e = start_web(port)
        if url:
            print(C_DIM + " Web 界面已启动: " + url + C_RST)
            print(C_DIM + " 已尝试打开浏览器；菜单 [4] 可再次打开" + C_RST)
            open_browser()
        else:
            print(C_WARN + " [警告] Web 界面未启动: " + str(e) + C_RST)
            print(C_DIM + "       可换端口: toolbox --web-port 9000" + C_RST)

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
                _open_web()
        except BackToPrev:
            pass
        line()
        print(C_DIM + " 已返回主菜单。" + C_RST)


def cli_extra():
    """处理本模块特有的参数, 返回 True 表示已处理"""
    args = sys.argv[1:]
    if not args:
        return False

    if "--cli" in args or "--no-web" in args:
        main(enable_web=False)
        return True

    if "--web" in args:
        try:
            import web
        except Exception as e:
            print(C_ERR + " [错误] 无法加载 web.py: %s" % e + C_RST)
            return True
        port = web.DEFAULT_PORT
        i = args.index("--web")
        if i + 1 < len(args) and args[i + 1].isdigit():
            port = int(args[i + 1])
        web.serve(port=port, open_browser=True)
        return True

    if "--web-port" in args:
        i = args.index("--web-port")
        if i + 1 < len(args) and args[i + 1].isdigit():
            main(port=int(args[i + 1]))
            return True

    if "--help-extra" in args:
        print("额外参数:")
        print("  --cli           只用命令行(不开 Web)")
        print("  --web [端口]    只开 Web 界面(前台)")
        print("  --web-port N    指定后台 Web 的端口")
        return True

    return False


if __name__ == "__main__":
    try:
        if cli_extra():
            sys.exit(0)
        if updater.cli(sys.argv[1:]):
            sys.exit(0)
        main()
    except KeyboardInterrupt:
        print("\n" + C_ERR + "已取消。" + C_RST)
        sys.exit(130)
