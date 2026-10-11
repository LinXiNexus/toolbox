#!/usr/bin/env bash
# =============================================================
#  常用工具集 - 发布脚本
#  把当前项目初始化并推送到远程仓库
#
#  用法:
#    ./publish.sh <仓库地址> [分支名]
#
#  示例:
#    ./publish.sh git@github.com:yourname/toolbox.git
#    ./publish.sh https://github.com/yourname/toolbox.git main
# =============================================================

set -u

SELF="$0"
while [ -L "$SELF" ]; do
    _l="$(readlink "$SELF")"
    case "$_l" in
        /*) SELF="$_l" ;;
        *)  SELF="$(dirname "$SELF")/$_l" ;;
    esac
done
SRC="$(cd "$(dirname "$SELF")" && pwd)"
cd "$SRC" || exit 1

C_OK=$'\033[1;32m'; C_ERR=$'\033[1;31m'; C_WARN=$'\033[1;35m'
C_KEY=$'\033[1;33m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
ok()   { printf "%s[OK]%s %s\n"   "$C_OK"   "$C_RST" "$1"; }
err()  { printf "%s[错误]%s %s\n" "$C_ERR"  "$C_RST" "$1"; }
warn() { printf "%s[警告]%s %s\n" "$C_WARN" "$C_RST" "$1"; }
info() { printf "%s%s%s\n"        "$C_DIM"  "$1"     "$C_RST"; }

REPO="${1:-}"
BRANCH="${2:-main}"

if [ -z "$REPO" ]; then
    err "缺少仓库地址"
    info "  用法: ./publish.sh <仓库地址> [分支名]"
    info "  示例: ./publish.sh git@github.com:yourname/toolbox.git"
    exit 1
fi

command -v git >/dev/null 2>&1 || { err "未找到 git"; info "  pkg install git"; exit 1; }

printf "%s\n" "=============================================="
printf "  常用工具集 - 发布\n"
printf "%s\n" "=============================================="
printf "  项目目录: %s\n" "$SRC"
printf "  仓库地址: %s\n" "$REPO"
printf "  分支    : %s\n" "$BRANCH"
printf "\n"

# ---------------------------------------------------------------- 初始化
if [ ! -d .git ]; then
    git init -q || { err "git init 失败"; exit 1; }
    ok "已初始化 git 仓库"
else
    ok "已是 git 仓库"
fi

# ---------------------------------------------------------------- 身份
if [ -z "$(git config --get user.name 2>/dev/null)" ]; then
    printf "%s未配置 git 用户名, 请输入: %s" "$C_KEY" "$C_RST"
    read -r gname
    [ -n "$gname" ] && git config user.name "$gname"
fi
if [ -z "$(git config --get user.email 2>/dev/null)" ]; then
    printf "%s未配置 git 邮箱, 请输入: %s" "$C_KEY" "$C_RST"
    read -r gmail
    [ -n "$gmail" ] && git config user.email "$gmail"
fi

# ---------------------------------------------------------------- 提交
git add -A
if git diff --cached --quiet 2>/dev/null; then
    info "没有需要提交的改动"
else
    git commit -q -m "更新: $(date '+%Y-%m-%d %H:%M')" && ok "已提交改动"
fi

# ---------------------------------------------------------------- 远程
if git remote get-url origin >/dev/null 2>&1; then
    cur="$(git remote get-url origin)"
    if [ "$cur" != "$REPO" ]; then
        git remote set-url origin "$REPO"
        ok "已更新远程地址: $cur -> $REPO"
    else
        ok "远程地址已是: $REPO"
    fi
else
    git remote add origin "$REPO"
    ok "已添加远程 origin"
fi

git branch -M "$BRANCH" 2>/dev/null

# ---------------------------------------------------------------- 推送
printf "\n"
info "正在推送..."
if git push -u origin "$BRANCH"; then
    printf "\n"
    ok "推送成功"
    printf "\n"
    printf "  仓库地址: %s\n" "$REPO"
    printf "  分支    : %s\n" "$BRANCH"
    printf "\n"
    info "接下来可以在别的设备上一键安装:"
    info "  bash bootstrap.sh --repo $REPO"
else
    err "推送失败"
    info "  常见原因: 未配置 SSH key / 未登录 / 仓库不存在"
    info "  可先手动执行: git push -u origin $BRANCH"
    exit 1
fi
