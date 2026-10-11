#!/usr/bin/env bash
# =============================================================
#  常用工具集 - 启动脚本
#  用法:  ./run.sh
#         ./run.sh -h          查看帮助
#         ./run.sh --fix-data  只检查/修复数据文件
# =============================================================

set -u

# 解析软链接, 拿到脚本真实所在目录(否则通过 toolbox 命令调用时会找错目录)
SELF="$0"
while [ -L "$SELF" ]; do
    _link="$(readlink "$SELF")"
    case "$_link" in
        /*) SELF="$_link" ;;
        *)  SELF="$(dirname "$SELF")/$_link" ;;
    esac
done
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR" || exit 1

PY="python3"
REGION_URL="https://raw.githubusercontent.com/modood/Administrative-divisions-of-China/master/dist/pcas-code.json"
PHONE_URL="https://raw.githubusercontent.com/ls0f/phone/master/phone/phone.dat"

C_OK=$'\033[1;32m'; C_ERR=$'\033[1;31m'; C_WARN=$'\033[1;35m'
C_KEY=$'\033[1;33m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'

ok()   { printf "%s[OK]%s %s\n"   "$C_OK"   "$C_RST" "$1"; }
err()  { printf "%s[错误]%s %s\n" "$C_ERR"  "$C_RST" "$1"; }
warn() { printf "%s[警告]%s %s\n" "$C_WARN" "$C_RST" "$1"; }
info() { printf "%s%s%s\n"        "$C_DIM"  "$1"     "$C_RST"; }

usage() {
    cat <<'EOF'
常用工具集 - 启动脚本

用法:
  ./run.sh                 启动(默认后台开网页 + 命令行菜单)
  ./run.sh --cli           只用命令行(不开网页)
  ./run.sh --web [端口]    只开网页(前台, 默认 8765)
  ./run.sh --web-port N    指定后台网页端口
  ./run.sh --check         检查更新
  ./run.sh --update        立即更新
  ./run.sh --version       显示版本
  ./run.sh --fix-data      只检查并下载缺失的数据文件
  ./run.sh -h|--help       显示本帮助

默认行为:
  启动后在后台跑一个本地网页服务, 并尝试打开浏览器,
  同时命令行菜单照常可用 —— 两边可以同时操作。
  退出命令行时网页服务会自动关闭。

主菜单:
  [1] 身份证菜单   [2] 手机号菜单
  [3] 检查更新     [4] 打开网页
  [0] 退出

通用操作:
  输入 exit / back / 返回  -> 返回上一层
  分页时输入 q            -> 直接回主菜单
  Ctrl+C                  -> 随时中断

数据文件:
  data/regions.txt   行政区划码表(2978 条)  - 身份证地区校验用
  data/phone.dat     手机号段库(499527 条)  - 手机号归属地查询用
  两者缺失时脚本会自动提示下载。
EOF
}

need() { command -v "$1" >/dev/null 2>&1; }

fetch_regions() {
    local tmp
    tmp="$(mktemp 2>/dev/null || echo "/tmp/reg.$$")"
    info "  正在下载行政区划数据..."
    if need curl; then
        curl -sSL -o "$tmp" "$REGION_URL" || { err "  下载失败"; rm -f "$tmp"; return 1; }
    elif need wget; then
        wget -qO "$tmp" "$REGION_URL" || { err "  下载失败"; rm -f "$tmp"; return 1; }
    else
        err "  未找到 curl 或 wget"; return 1
    fi
    "$PY" - "$tmp" "$DIR/data/regions.txt" <<'PYEOF'
import json, sys, os
src, dst = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(src, encoding="utf-8"))
except Exception as e:
    print("  解析失败: %s" % e); sys.exit(1)
codes = {}
def walk(ns):
    for n in ns:
        c = n.get("code", "")
        if len(c) == 6:
            codes[c] = n.get("name", "")
        if n.get("children"):
            walk(n["children"])
walk(data)
os.makedirs(os.path.dirname(dst), exist_ok=True)
with open(dst, "w", encoding="utf-8") as f:
    for c in sorted(codes):
        f.write("%s %s\n" % (c, codes[c]))
print("  已生成 regions.txt: %d 条" % len(codes))
PYEOF
    rm -f "$tmp"
}

fetch_phone() {
    info "  正在下载手机号段库(约 4.3MB)..."
    mkdir -p "$DIR/data"
    if need curl; then
        curl -sSL -o "$DIR/data/phone.dat" "$PHONE_URL" || { err "  下载失败"; return 1; }
    elif need wget; then
        wget -qO "$DIR/data/phone.dat" "$PHONE_URL" || { err "  下载失败"; return 1; }
    else
        err "  未找到 curl 或 wget"; return 1
    fi
    local sz
    sz=$(wc -c < "$DIR/data/phone.dat" 2>/dev/null || echo 0)
    if [ "$sz" -lt 100000 ]; then
        err "  下载异常(文件过小)"; return 1
    fi
    ok "  已下载 phone.dat ($((sz / 1024 / 1024)) MB)"
}

check_data() {
    local missing=0
    if [ -f "$DIR/data/regions.txt" ]; then
        ok "data/regions.txt  ($(wc -l < "$DIR/data/regions.txt") 条)"
    else
        warn "缺少 data/regions.txt  (身份证地区码校验不可用)"
        missing=1
    fi
    if [ -f "$DIR/data/phone.dat" ]; then
        ok "data/phone.dat    ($(( $(wc -c < "$DIR/data/phone.dat") / 1024 / 1024 )) MB)"
    else
        warn "缺少 data/phone.dat  (手机号归属地查询不可用)"
        missing=1
    fi
    return $missing
}

# ---------------------------------------------------------------- 参数
case "${1:-}" in
    -h|--help)
        usage; exit 0 ;;
    --fix-data)
        printf "检查数据文件...\n"
        if ! check_data; then
            printf "\n开始下载缺失文件...\n"
            [ -f "$DIR/data/regions.txt" ] || fetch_regions
            [ -f "$DIR/data/phone.dat" ]   || fetch_phone
            printf "\n重新检查:\n"
            check_data && ok "数据文件齐备"
        fi
        exit 0 ;;
esac
# 其余参数原样交给 main.py (如 --check / --update / --version)

# ---------------------------------------------------------------- 环境检查
printf "%s\n" "=============================================="
printf "  常用工具集 - 环境检查\n"
printf "%s\n" "=============================================="

if ! need "$PY"; then
    err "未找到 python3，请先安装"
    info "  Termux:  pkg install python"
    exit 1
fi
ok "python3 $($PY -V 2>&1 | awk '{print $2}')"

if ! need curl && ! need wget; then
    warn "未找到 curl / wget，缺失数据文件时无法自动下载"
fi

if ! check_data; then
    printf "\n"
    printf "%s是否现在下载缺失的数据文件? (y/n) %s" "$C_KEY" "$C_RST"
    read -r ans
    case "$ans" in
        y|Y|yes|YES|"")
            [ -f "$DIR/data/regions.txt" ] || fetch_regions
            [ -f "$DIR/data/phone.dat" ]   || fetch_phone
            printf "\n"
            check_data || warn "仍有文件缺失，相关功能会自动跳过"
            ;;
        *)
            warn "跳过下载，相关功能可能不可用"
            ;;
    esac
fi

printf "\n"

# ---------------------------------------------------------------- 启动
if [ ! -f "$DIR/main.py" ]; then
    err "找不到 main.py，请确认当前目录结构完整"
    exit 1
fi

exec "$PY" "$DIR/main.py" "$@"
