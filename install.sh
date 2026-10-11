#!/usr/bin/env bash
# =============================================================
#  常用工具集 - 统一安装脚本
#
#  特点: 只建立软链接, 不复制任何文件
#        源码改动立即生效, 不占用额外空间
#
#  用法:
#    ./install.sh              安装 toolbox 命令
#    ./install.sh -b DIR       指定命令目录
#    ./install.sh -u           卸载
#    ./install.sh --status     查看安装状态
#    ./install.sh -h           显示帮助
# =============================================================

set -u

# 脚本自身所在目录 = 项目根目录
SELF="$0"
while [ -L "$SELF" ]; do
    _l="$(readlink "$SELF")"
    case "$_l" in
        /*) SELF="$_l" ;;
        *)  SELF="$(dirname "$SELF")/$_l" ;;
    esac
done
SRC="$(cd "$(dirname "$SELF")" && pwd)"

C_OK=$'\033[1;32m'; C_ERR=$'\033[1;31m'; C_WARN=$'\033[1;35m'
C_KEY=$'\033[1;33m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
ok()   { printf "%s[OK]%s %s\n"   "$C_OK"   "$C_RST" "$1"; }
err()  { printf "%s[错误]%s %s\n" "$C_ERR"  "$C_RST" "$1"; }
warn() { printf "%s[警告]%s %s\n" "$C_WARN" "$C_RST" "$1"; }
info() { printf "%s%s%s\n"        "$C_DIM"  "$1"     "$C_RST"; }

CMDNAME="toolbox"
BINDIR=""
BINDIR_SET=0
MODE="install"

usage() {
    cat <<'EOF'
常用工具集 - 统一安装脚本

用法:
  ./install.sh [选项]

选项:
  -b, --bin DIR     命令目录 (默认自动探测可写的 PATH 目录)
  -u, --uninstall   卸载(只删软链接, 不动源码)
      --status      查看安装状态
  -h, --help        显示本帮助

说明:
  本脚本只建立软链接, 不复制任何文件。
  安装后源码目录的改动会立即生效。

安装位置:
  命令  toolbox  ->  <项目目录>/run.sh
  源码  <项目目录>  保持原地不动

示例:
  ./install.sh                  # 安装
  ./install.sh -b ~/bin         # 命令放到 ~/bin
  ./install.sh --status         # 查看状态
  ./install.sh -u               # 卸载
EOF
}

# ---------------------------------------------------------------- 参数
while [ $# -gt 0 ]; do
    case "$1" in
        -b|--bin)        BINDIR="${2:-}"; BINDIR_SET=1; shift 2 ;;
        -u|--uninstall)  MODE="uninstall"; shift ;;
        --status)        MODE="status";    shift ;;
        -h|--help)       usage; exit 0 ;;
        *) err "未知参数: $1"; echo; usage; exit 1 ;;
    esac
done

# ---------------------------------------------------------------- 校验源
if [ ! -f "$SRC/main.py" ] || [ ! -f "$SRC/run.sh" ]; then
    err "当前目录不是工具集项目根目录"
    info "  缺少 main.py 或 run.sh"
    info "  当前目录: $SRC"
    exit 1
fi

# ---------------------------------------------------------------- 探测命令目录
detect_bin() {
    local d
    for d in "${PREFIX:-}/bin" "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
        [ -n "$d" ] && [ "$d" != "/bin" ] && [ -d "$d" ] && [ -w "$d" ] && { printf '%s' "$d"; return; }
    done
    mkdir -p "$HOME/.local/bin" 2>/dev/null && printf '%s' "$HOME/.local/bin"
}

# 未指定时: 先找已存在的、指向本项目的软链接; 否则自动探测
if [ -z "$BINDIR" ]; then
    for _d in "${PREFIX:-}/bin" "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin" \
              $(printf '%s' "$PATH" | tr ':' ' '); do
        [ -n "$_d" ] || continue
        [ -L "$_d/$CMDNAME" ] || continue
        _t="$(readlink "$_d/$CMDNAME")"
        case "$_t" in
            "$SRC/run.sh") BINDIR="$_d"; break ;;
        esac
    done
fi
[ -n "$BINDIR" ] || BINDIR="$(detect_bin)"
[ -n "$BINDIR" ] || { err "无法确定命令目录，请用 -b 指定"; exit 1; }

LINK="$BINDIR/$CMDNAME"

# ---------------------------------------------------------------- 状态
show_status() {
    printf "%s\n" "=============================================="
    printf "  常用工具集 - 安装状态\n"
    printf "%s\n" "=============================================="
    printf "  项目目录: %s\n" "$SRC"
    printf "  命令目录: %s\n" "$BINDIR"
    printf "  命令路径: %s\n" "$LINK"
    printf "\n"
    if [ -L "$LINK" ]; then
        printf "  链接目标: %s\n" "$(readlink "$LINK")"
        if [ "$(readlink "$LINK")" = "$SRC/run.sh" ]; then
            ok "状态: 已安装(指向本项目)"
        else
            warn "状态: 软链接存在, 但指向别处"
        fi
    elif [ -e "$LINK" ]; then
        warn "状态: $LINK 存在但不是软链接"
    else
        info "状态: 未安装"
    fi
    printf "\n"
    if [ -f "$SRC/data/regions.txt" ]; then
        ok "data/regions.txt  ($(wc -l < "$SRC/data/regions.txt") 条)"
    else
        warn "data/regions.txt  缺失"
    fi
    if [ -f "$SRC/data/phone.dat" ]; then
        ok "data/phone.dat    ($(( $(wc -c < "$SRC/data/phone.dat") / 1024 / 1024 )) MB)"
    else
        warn "data/phone.dat    缺失"
    fi
    printf "\n"
    case ":${PATH}:" in
        *":$BINDIR:"*) ok "$BINDIR 已在 PATH 中" ;;
        *) warn "$BINDIR 不在 PATH 中" ;;
    esac
}

case "$MODE" in
    status) show_status; exit 0 ;;
esac

# ---------------------------------------------------------------- 卸载
if [ "$MODE" = "uninstall" ]; then
    printf "卸载常用工具集\n"
    printf "  命令: %s\n" "$LINK"
    printf "  源码: %s  (保持不动)\n" "$SRC"
    printf "\n"
    if [ ! -L "$LINK" ]; then
        if [ -e "$LINK" ]; then
            err "$LINK 存在但不是软链接, 为安全起见不自动删除"
        else
            info "未安装, 无需卸载"
        fi
        exit 0
    fi
    if [ "$(readlink "$LINK")" != "$SRC/run.sh" ]; then
        warn "$LINK 指向的是 $(readlink "$LINK")"
        printf "%s仍要删除? (y/n) %s" "$C_KEY" "$C_RST"
        read -r ans
        case "$ans" in
            y|Y|yes|YES) ;;
            *) info "已取消"; exit 0 ;;
        esac
    fi
    rm -f "$LINK" && ok "已删除命令 $LINK"
    info "源码目录未改动: $SRC"
    ok "卸载完成"
    exit 0
fi

# ---------------------------------------------------------------- 安装
printf "%s\n" "=============================================="
printf "  常用工具集 - 安装\n"
printf "%s\n" "=============================================="
printf "  项目目录: %s\n" "$SRC"
printf "  命令目录: %s\n" "$BINDIR"
printf "  安装方式: 软链接(不复制文件)\n"
printf "\n"

if ! command -v python3 >/dev/null 2>&1; then
    err "未找到 python3，请先安装"
    info "  Termux:  pkg install python"
    exit 1
fi
ok "python3 $(python3 -V 2>&1 | awk '{print $2}')"

# 目标已存在且不是指向本项目的软链接
if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
    err "$LINK 已存在且不是软链接, 请先处理"
    exit 1
fi
if [ -L "$LINK" ] && [ "$(readlink "$LINK")" != "$SRC/run.sh" ]; then
    warn "$LINK 已存在, 指向 $(readlink "$LINK")"
    printf "%s是否覆盖? (y/n) %s" "$C_KEY" "$C_RST"
    read -r ans
    case "$ans" in
        y|Y|yes|YES) ;;
        *) info "已取消"; exit 0 ;;
    esac
fi

# 确保 run.sh 可执行
chmod +x "$SRC/run.sh" 2>/dev/null
[ -f "$SRC/install.sh" ] && chmod +x "$SRC/install.sh" 2>/dev/null

mkdir -p "$BINDIR" 2>/dev/null
if ln -sfn "$SRC/run.sh" "$LINK" 2>/dev/null; then
    ok "已创建软链接: $LINK -> $SRC/run.sh"
else
    err "创建软链接失败: $LINK"
    info "  可改用:  alias toolbox='$SRC/run.sh'"
    exit 1
fi

# ---------------------------------------------------------------- PATH 检查
printf "\n"
case ":${PATH}:" in
    *":$BINDIR:"*)
        ok "$BINDIR 已在 PATH 中"
        ;;
    *)
        warn "$BINDIR 不在 PATH 中"
        RC=""
        case "${SHELL:-}" in
            *zsh)  RC="$HOME/.zshrc" ;;
            *bash) RC="$HOME/.bashrc" ;;
            *)     RC="$HOME/.profile" ;;
        esac
        printf "%s是否把 %s 加入 PATH (写入 %s)? (y/n) %s" "$C_KEY" "$BINDIR" "$RC" "$C_RST"
        read -r ans
        case "$ans" in
            y|Y|yes|YES|"")
                {
                    printf '\n'
                    printf '# 常用工具集\n'
                    printf 'export PATH="%s:$PATH"\n' "$BINDIR"
                } >> "$RC"
                ok "已写入 $RC"
                info "  执行  source $RC  或重开终端后生效"
                ;;
            *)
                info "跳过。手动生效可执行:"
                info "  export PATH=$BINDIR:\$PATH"
                ;;
        esac
        ;;
esac

# ---------------------------------------------------------------- 完成
printf "\n"
printf "%s\n" "=============================================="
ok "安装完成"
printf "%s\n" "=============================================="
printf "  启动    : %s\n" "$CMDNAME"
printf "  直接运行: %s\n" "$SRC/run.sh"
printf "  查看帮助: %s -h\n" "$CMDNAME"
printf "  修复数据: %s --fix-data\n" "$CMDNAME"
printf "  查看状态: %s/install.sh --status\n" "$SRC"
printf "  卸载    : %s/install.sh -u\n" "$SRC"
printf "\n"
info "源码目录: $SRC  (改动立即生效, 无需重装)"
