#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 GitHub API 发布 Release (不依赖 gh)

用法:
    python3 publish_release.py                  发布当前版本
    python3 publish_release.py --draft          发布为草稿
    python3 publish_release.py --token-file F   指定 token 文件

Token 怎么弄(二选一, 都只给最小权限):

  【细粒度 token, 推荐】
    1. 打开 https://github.com/settings/personal-access-tokens/new
    2. Token name 填 toolbox-release
    3. Expiration 选 90 天
    4. Repository access 选 Only select repositories -> LinXiNexus/toolbox
    5. Permissions -> Repository permissions -> Contents 设为 Read and write
    6. 生成, 复制 github_pat_xxx

  【经典 token, 更简单】
    1. 打开 https://github.com/settings/tokens/new
    2. Note 填 toolbox-release, Expiration 选 90 天
    3. 勾选 repo (公开仓库勾 public_repo 即可)
    4. 生成, 复制 ghp_xxx

存起来(不要写在命令行里, 避免留在历史记录):

    echo 'github_pat_xxx' > ~/gh_token.txt
    chmod 600 ~/gh_token.txt
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
UPLOAD = "https://uploads.github.com"
SRC = os.path.dirname(os.path.abspath(__file__))

C_OK = "\033[1;32m"; C_ERR = "\033[1;31m"; C_WARN = "\033[1;35m"
C_DIM = "\033[2m"; C_RST = "\033[0m"


def ok(m):   print("%s[OK]%s %s" % (C_OK, C_RST, m))
def err(m):  print("%s[错误]%s %s" % (C_ERR, C_RST, m))
def warn(m): print("%s[警告]%s %s" % (C_WARN, C_RST, m))
def info(m): print("%s%s%s" % (C_DIM, m, C_RST))


def read_token(path=None):
    """按优先级找 token: 参数 > 环境变量 > ~/gh_token.txt"""
    if path:
        if not os.path.isfile(path):
            err("token 文件不存在: " + path)
            sys.exit(1)
        return open(path, encoding="utf-8").read().strip()
    for k in ("GH_TOKEN", "GITHUB_TOKEN"):
        v = os.environ.get(k, "").strip()
        if v:
            return v
    for p in (os.path.join(os.path.expanduser("~"), "gh_token.txt"),
              os.path.join(os.path.expanduser("~"), ".gh_token")):
        if os.path.isfile(p):
            return open(p, encoding="utf-8").read().strip()
    return ""


def detect_repo():
    """从 git remote 推断 owner/repo"""
    try:
        url = subprocess.run(["git", "-C", SRC, "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        url = ""
    if not url:
        return ""
    if url.startswith("git@"):
        url = url.split(":", 1)[1]
    elif "github.com/" in url:
        url = url.split("github.com/", 1)[1]
    return url[:-4] if url.endswith(".git") else url


def req(method, url, token, payload=None, raw=None, ctype=None, timeout=180):
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "toolbox-release",
    }
    body = None
    if raw is not None:
        body = raw
        headers["Content-Type"] = ctype or "application/octet-stream"
    elif payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            txt = resp.read().decode("utf-8", "ignore")
            return resp.status, (json.loads(txt) if txt.strip() else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, {"message": txt[:300]}
    except Exception as e:
        return 0, {"message": str(e)}


def main():
    ap = argparse.ArgumentParser(description="用 GitHub API 发布 Release")
    ap.add_argument("--draft", action="store_true", help="发布为草稿")
    ap.add_argument("--token-file", default=None, help="token 文件路径")
    ap.add_argument("--asset", default=None, help="要上传的文件")
    args = ap.parse_args()

    # token
    token = read_token(args.token_file)
    if not token:
        err("没有找到 token")
        info("")
        info("  二选一获取(都只给最小权限):")
        info("    细粒度: https://github.com/settings/personal-access-tokens/new")
        info("            Repository permissions -> Contents: Read and write")
        info("    经典:   https://github.com/settings/tokens/new")
        info("            勾选 repo (公开仓库 public_repo 即可)")
        info("")
        info("  存起来:")
        info("    echo '你的token' > ~/gh_token.txt && chmod 600 ~/gh_token.txt")
        sys.exit(1)

    repo = detect_repo()
    if not repo:
        err("无法从 git remote 推断仓库, 请确认在项目目录里运行")
        sys.exit(1)

    ver = open(os.path.join(SRC, "VERSION"), encoding="utf-8").read().strip()
    tag = "v" + ver
    asset = args.asset or os.path.join(SRC, "dist", "toolbox-standalone.pyz")
    if not os.path.isfile(asset):
        err("找不到要上传的文件: " + asset)
        info("  先编译:  python3 build.py pyz --embed")
        sys.exit(1)
    aname = os.path.basename(asset)

    print("=" * 52)
    print("  发布 v%s 到 %s" % (ver, repo))
    print("=" * 52)
    print("  标签  : %s" % tag)
    print("  附件  : %s (%s)" % (aname, human(os.path.getsize(asset))))
    print("  草稿  : %s" % ("是" if args.draft else "否"))
    print()

    # 1. 校验 token
    st, d = req("GET", API + "/user", token)
    if st != 200:
        err("token 无效或无权限: HTTP %d %s" % (st, d.get("message", "")))
        sys.exit(1)
    ok("token 有效: %s" % d.get("login"))

    # 2. 查现有 release
    st, rel = req("GET", "%s/repos/%s/releases/tags/%s" % (API, repo, tag), token)
    if st == 200:
        warn("Release %s 已存在, 将更新附件" % tag)
        rel_id = rel["id"]
    elif st == 404:
        notes = ""
        nf = os.path.join(SRC, "RELEASE_NOTES.md")
        if os.path.isfile(nf):
            notes = open(nf, encoding="utf-8").read()
        st, rel = req("POST", "%s/repos/%s/releases" % (API, repo), token, {
            "tag_name": tag,
            "name": "常用工具集 " + tag,
            "body": notes or ("版本 " + ver),
            "draft": bool(args.draft),
        })
        if st not in (200, 201):
            err("创建 Release 失败: HTTP %d %s" % (st, rel.get("message", "")))
            if st == 403:
                info("  可能是 token 权限不足, 需要 Contents: Read and write")
            sys.exit(1)
        rel_id = rel["id"]
        ok("已创建 Release")
    else:
        err("查询 Release 失败: HTTP %d %s" % (st, rel.get("message", "")))
        sys.exit(1)

    # 3. 删掉同名旧附件
    for a in rel.get("assets", []):
        if a.get("name") == aname:
            st, _ = req("DELETE", "%s/repos/%s/releases/assets/%d" % (API, repo, a["id"]), token)
            if st in (204, 200):
                info("  已删除同名旧附件")

    # 4. 上传
    raw = open(asset, "rb").read()
    url = "%s/repos/%s/releases/%d/assets?name=%s" % (UPLOAD, repo, rel_id, aname)
    st, up = req("POST", url, token, raw=raw, ctype="application/octet-stream")
    if st not in (200, 201):
        err("上传失败: HTTP %d %s" % (st, up.get("message", "")))
        sys.exit(1)
    ok("已上传: %s (%s)" % (up.get("name"), human(up.get("size", 0))))

    print()
    print("=" * 52)
    ok("发布完成")
    print("=" * 52)
    print("  Release : https://github.com/%s/releases/tag/%s" % (repo, tag))
    print("  下载地址: https://github.com/%s/releases/download/%s/%s" % (repo, tag, aname))
    print()
    print("  别人这样用:")
    print("    curl -fsSL %s/releases/download/%s/%s -o toolbox.pyz" % (
        "https://github.com/" + repo, tag, aname))
    print("    python3 toolbox.pyz")
    print()


def human(n):
    n = float(n)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.1f TB" % n


if __name__ == "__main__":
    main()
