#!/data/data/com.termux/files/usr/bin/bash
# =============================================================
#  发布脚本: 编译单文件 -> 打 tag -> 上传 GitHub Release
#
#  用法:
#    ./release.sh              用当前 VERSION 发布
#    ./release.sh --draft      发布为草稿(不公开)
#    ./release.sh --no-build   跳过编译, 用现有 dist/ 产物
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
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR" || exit 1

C_OK=$'\033[1;32m'; C_ERR=$'\033[1;31m'; C_WARN=$'\033[1;35m'
C_KEY=$'\033[1;33m'; C_TITLE=$'\033[1;36m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
ok()   { printf "%s[OK]%s %s\n"   "$C_OK"   "$C_RST" "$1"; }
err()  { printf "%s[错误]%s %s\n" "$C_ERR"  "$C_RST" "$1"; }
warn() { printf "%s[警告]%s %s\n" "$C_WARN" "$C_RST" "$1"; }
info() { printf "%s%s%s\n"        "$C_DIM"  "$1"     "$C_RST"; }
step() { printf "\n%s==> %s%s\n"  "$C_TITLE" "$1" "$C_RST"; }

DRAFT=0
DO_BUILD=1
for a in "$@"; do
    case "$a" in
        --draft)    DRAFT=1 ;;
        --no-build) DO_BUILD=0 ;;
        -h|--help)  sed -n '3,11p' "$SELF" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) err "未知参数: $a"; exit 1 ;;
    esac
done

VER="$(cat VERSION 2>/dev/null | tr -d '[:space:]')"
[ -n "$VER" ] || { err "读不到 VERSION 文件"; exit 1; }
TAG="v$VER"
ASSET="$DIR/dist/toolbox-standalone.pyz"

printf "%s\n" "=============================================="
printf "  发布 v%s\n" "$VER"
printf "%s\n" "=============================================="
printf "  版本号 : %s\n" "$VER"
printf "  标签   : %s\n" "$TAG"
printf "  草稿   : %s\n" "$([ "$DRAFT" = 1 ] && echo 是 || echo 否)"
printf "\n"

# ---------------------------------------------------------------- 1. 认证
step "1/5  检查认证"
TOKEN=""
for f in "$HOME/gh_token.txt" "$HOME/.gh_token"; do
    [ -f "$f" ] && TOKEN="$(cat "$f" | tr -d '\n\r ')" && break
done
[ -n "$TOKEN" ] || TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
    err "没有找到 GitHub token"
    info ""
    info "  创建一个(权限只需 Contents: Read and write):"
    info "    细粒度: https://github.com/settings/personal-access-tokens/new"
    info "    经典:   https://github.com/settings/tokens/new"
    info ""
    info "  存起来:"
    info "    echo '你的token' > ~/gh_token.txt && chmod 600 ~/gh_token.txt"
    exit 1
fi
export GH_TOKEN="$TOKEN"
ok "已找到 token (${#TOKEN} 字符)"

# ---------------------------------------------------------------- 2. 提交
step "2/5  提交改动"
if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -q -m "发布 $VER" && ok "已提交"
else
    info "没有需要提交的改动"
fi
if git remote get-url origin >/dev/null 2>&1; then
    git push -q origin HEAD && ok "已推送代码"
fi

# ---------------------------------------------------------------- 3. 编译
step "3/5  编译单文件"
if [ "$DO_BUILD" = 1 ]; then
    python3 build.py pyz --embed 2>&1 | grep -E "OK|错误" | sed 's/^/  /'
fi
[ -f "$ASSET" ] || { err "找不到产物: $ASSET"; exit 1; }
ok "产物: $(basename "$ASSET")  $(ls -lh "$ASSET" | awk '{print $5}')"
info "  SHA256: $(sha256sum "$ASSET" | awk '{print $1}')"

# ---------------------------------------------------------------- 4. 打标签
step "4/5  创建标签 $TAG"
if git rev-parse "$TAG" >/dev/null 2>&1; then
    warn "标签 $TAG 已存在"
else
    git tag -a "$TAG" -m "发布 $VER" && ok "已创建标签"
    git push -q origin "$TAG" && ok "已推送标签"
fi

# ---------------------------------------------------------------- 5. 发布
step "5/5  上传 Release"
PY_ARGS=()
[ "$DRAFT" = 1 ] && PY_ARGS+=(--draft)
if python3 "$DIR/publish_release.py" "${PY_ARGS[@]}"; then
    ok "发布成功"
else
    err "发布失败"
    exit 1
fi
printf "\n"
