#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本更新检测

功能:
  - 启动时自动检查新版本(带缓存, 不拖慢启动)
  - 发现新版本时提示: 立即更新 / 跳过此版本 / 屏蔽所有更新 / 稍后
  - 配置保存在 ~/.toolbox_update.json

命令行:
  --check      立即检查更新
  --update     立即更新到最新版
  --mute       屏蔽所有更新提示
  --unmute     恢复更新提示
  --skipped    查看已跳过的版本
  --version    显示当前版本
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

from common import (line, ask_input, BackToPrev,
                    C_TITLE, C_KEY, C_OK, C_ERR, C_WARN, C_DIM, C_RST)

REPO_RAW = "https://raw.githubusercontent.com/LinXiNexus/toolbox/main"
VERSION_URL = REPO_RAW + "/VERSION"
REPO_URL = "https://github.com/LinXiNexus/toolbox.git"

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.expanduser("~"), ".toolbox_update.json")
DEFAULT_INTERVAL = 3600
NET_TIMEOUT = 4


def local_version():
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def parse_ver(v):
    out = []
    for x in str(v).strip().split("."):
        try:
            out.append(int(x))
        except ValueError:
            out.append(0)
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


def is_newer(remote, local):
    return parse_ver(remote) > parse_ver(local)


def fetch_remote_version(timeout=NET_TIMEOUT):
    try:
        req = urllib.request.Request(
            VERSION_URL, headers={"User-Agent": "toolbox-updater"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore").strip() or None
    except Exception:
        return None


def load_config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    d.setdefault("skipped", [])
    d.setdefault("muted", False)
    d.setdefault("last_check", 0)
    d.setdefault("interval", DEFAULT_INTERVAL)
    return d


def save_config(d):
    try:
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def check(force=False):
    """返回 dict: {has_update, local, remote, skipped, muted, error}"""
    cfg = load_config()
    local = local_version()

    if cfg["muted"] and not force:
        return {"has_update": False, "local": local, "remote": None,
                "muted": True, "skipped": cfg["skipped"], "error": None}

    now = time.time()
    if not force and (now - cfg.get("last_check", 0)) < cfg.get("interval", DEFAULT_INTERVAL):
        return {"has_update": False, "local": local, "remote": None,
                "muted": False, "skipped": cfg["skipped"], "error": None,
                "cached": True}

    remote = fetch_remote_version()
    cfg["last_check"] = now
    save_config(cfg)

    if remote is None:
        return {"has_update": False, "local": local, "remote": None,
                "muted": False, "skipped": cfg["skipped"],
                "error": "无法连接更新服务器"}

    newer = is_newer(remote, local)
    skipped = remote in cfg["skipped"]
    return {"has_update": newer and not skipped, "local": local, "remote": remote,
            "muted": False, "skipped": cfg["skipped"], "error": None,
            "newer": newer, "was_skipped": skipped}


def project_is_git():
    return os.path.isdir(os.path.join(HERE, ".git"))


def do_update():
    if not project_is_git():
        return False, "当前目录不是 git 仓库，请重新运行 bootstrap.sh 安装"
    try:
        p = subprocess.run(["git", "-C", HERE, "pull", "--ff-only"],
                           capture_output=True, text=True, timeout=60)
    except Exception as e:
        return False, "执行 git pull 失败: %s" % e
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode == 0:
        return True, out.strip() or "已是最新"
    return False, out.strip() or ("git 返回码 %d" % p.returncode)


def show_update_prompt(info):
    line()
    print(C_TITLE + "发现新版本" + C_RST)
    line()
    print("  当前版本: " + C_KEY + info["local"] + C_RST)
    print("  最新版本: " + C_OK + info["remote"] + C_RST)
    print()
    print("   " + C_KEY + "[1]" + C_RST + " 立即更新")
    print("   " + C_KEY + "[2]" + C_RST + " 跳过此版本   (以后不再提示 " + info["remote"] + ")")
    print("   " + C_KEY + "[3]" + C_RST + " 屏蔽所有更新 (不再检查新版本)")
    print("   " + C_KEY + "[0]" + C_RST + " 稍后再说")
    print()
    while True:
        try:
            ans = ask_input(C_KEY + " 请选择 (exit 稍后) > " + C_RST)
        except BackToPrev:
            return "later"
        if ans == "1":
            return "update"
        if ans == "2":
            return "skip"
        if ans == "3":
            return "mute"
        if ans in ("0", "", "q", "quit"):
            return "later"
        print(C_ERR + " [错误] 请输入 1 / 2 / 3 / 0。" + C_RST)


def apply_choice(action, info):
    cfg = load_config()
    if action == "skip":
        if info.get("remote") and info["remote"] not in cfg["skipped"]:
            cfg["skipped"].append(info["remote"])
            save_config(cfg)
        print(C_OK + " [OK] 已跳过版本 " + str(info.get("remote")) + C_RST)
        return
    if action == "mute":
        cfg["muted"] = True
        save_config(cfg)
        print(C_OK + " [OK] 已屏蔽所有更新提示" + C_RST)
        print(C_DIM + "      恢复: toolbox --unmute" + C_RST)
        return
    if action == "update":
        print()
        print(C_DIM + " 正在更新..." + C_RST)
        ok, msg = do_update()
        if ok:
            print(C_OK + " [OK] 更新完成" + C_RST)
            for ln in msg.splitlines()[-6:]:
                print(C_DIM + "      " + ln + C_RST)
            print()
            print(C_WARN + " [提示] 请重新启动 toolbox 以使用新版本" + C_RST)
        else:
            print(C_ERR + " [错误] " + msg + C_RST)
        return


def maybe_check():
    try:
        info = check(force=False)
    except Exception:
        return
    if info.get("error") or not info.get("has_update"):
        return
    action = show_update_prompt(info)
    apply_choice(action, info)


def manual_check():
    line()
    print(C_TITLE + "检查更新" + C_RST)
    line()
    cfg = load_config()
    print("  当前版本: " + C_KEY + local_version() + C_RST)
    if cfg["muted"]:
        print(C_WARN + "  [注意] 已屏蔽所有更新提示" + C_RST)
    print(C_DIM + "  正在连接更新服务器..." + C_RST)
    info = check(force=True)
    if info.get("error"):
        print(C_ERR + " [错误] " + info["error"] + C_RST)
        return
    if not info.get("newer"):
        print(C_OK + " [OK] 已是最新版本 (" + info["local"] + ")" + C_RST)
        return
    if info.get("was_skipped"):
        print(C_WARN + " [提示] 版本 " + info["remote"] + " 已被你跳过" + C_RST)
        print(C_DIM + "      想安装的话: toolbox --update" + C_RST)
        return
    action = show_update_prompt(info)
    apply_choice(action, info)


def cli(args):
    if not args:
        return False
    a = args[0]
    if a == "--check":
        manual_check(); return True
    if a == "--update":
        info = check(force=True)
        if info.get("error"):
            print(C_ERR + " [错误] " + info["error"] + C_RST); return True
        if not info.get("newer"):
            print(C_OK + " [OK] 已是最新版本 (" + info["local"] + ")" + C_RST); return True
        print("当前 " + info["local"] + "  ->  最新 " + info["remote"])
        apply_choice("update", info)
        return True
    if a == "--mute":
        cfg = load_config(); cfg["muted"] = True; save_config(cfg)
        print(C_OK + " [OK] 已屏蔽所有更新提示" + C_RST); return True
    if a == "--unmute":
        cfg = load_config(); cfg["muted"] = False; cfg["last_check"] = 0; save_config(cfg)
        print(C_OK + " [OK] 已恢复更新检查" + C_RST); return True
    if a == "--skipped":
        cfg = load_config()
        print("已跳过的版本: " + (", ".join(cfg["skipped"]) or "(无)"))
        print("屏蔽所有更新: " + ("是" if cfg["muted"] else "否"))
        print("配置文件: " + CONFIG)
        return True
    if a in ("--version", "-v"):
        print("toolbox " + local_version()); return True
    return False
