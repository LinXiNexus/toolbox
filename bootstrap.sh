#!/data/data/com.termux/files/usr/bin/bash
# =============================================================
#  常用工具集 - 一键安装脚本
#
#  做三件事:
#    1. 从仓库克隆项目
#    2. 把 toolbox 命令加入 PATH
#    3. 打印使用方法
#
#  用法:
#    bash bootstrap.sh
#    bash bootstrap.sh --repo <仓库地址>
#    bash bootstrap.sh --repo <仓库地址> --dir ~/mytoolbox --bin ~/bin
#    curl -fsSL <raw地址>/bootstrap.sh | bash -s -- --repo <仓库地址>
#
#  可用环境变量:
#    TOOLBOX_REPO    仓库地址
#    TOOLBOX_DIR     安装目录   (默认 ~/toolbox)
#    TOOLBOX_BIN     命令目录   (默认自动探测)
#    TOOLBOX_BRANCH  分支       (默认 main)
# =============================================================

set -u

# ↓↓↓ 发布后把这里改成你的仓库地址, 之后就能免参数运行 ↓↓↓
DEFAULT_REPO="https://github.com/LinXiNexus/toolbox.git"

C_OK=$'\033[1;32m'; C_ERR=$'\033[1;31m'; C_WARN=$'\033[1;35m'
C_KEY=$'\033[1;33m'; C_TITLE=$'\033[1;36m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
ok()   { printf "%s[OK]%s %s\n"   "$C_OK"   "$C_RST" "$1"; }
err()  { printf "%s[错误]%s %s\n" "$C_ERR"  "$C_RST" "$1"; }
warn() { printf "%s[警告]%s %s\n" "$C_WARN" "$C_RST" "$1"; }
info() { printf "%s%s%s\n"        "$C_DIM"  "$1"     "$C_RST"; }
step() { printf "\n%s==> %s%s\n"  "$C_TITLE" "$1" "$C_RST"; }

REPO="${TOOLBOX_REPO:-$DEFAULT_REPO}"
INSTALL_DIR="${TOOLBOX_DIR:-$HOME/toolbox}"
BINDIR="${TOOLBOX_BIN:-}"
BRANCH="${TOOLBOX_BRANCH:-main}"
FORCE=0
NO_LINK=0

usage() {
    cat <<'EOF'
常用工具集 - 一键安装脚本

用法:
  bash bootstrap.sh [选项]

选项:
  --repo URL       仓库地址 (也可用环境变量 TOOLBOX_REPO)
  --dir DIR        安装目录 (默认 ~/toolbox)
  --bin DIR        命令目录 (默认自动探测)
  --branch NAME    分支名   (默认 main)
  --no-link        只克隆, 不建命令软链接
  --force          安装目录已存在时删除重装
  -h, --help       显示本帮助

示例:
  bash bootstrap.sh --repo https://github.com/yourname/toolbox.git
  bash bootstrap.sh --repo git@github.com:yourname/toolbox.git --dir ~/apps/tb
  curl -fsSL https://raw.githubusercontent.com/yourname/toolbox/main/bootstrap.sh \
    | bash -s -- --repo https://github.com/yourname/toolbox.git
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --repo)    REPO="${2:-}";        shift 2 ;;
        --dir)     INSTALL_DIR="${2:-}"; shift 2 ;;
        --bin)     BINDIR="${2:-}";      shift 2 ;;
        --branch)  BRANCH="${2:-}";      shift 2 ;;
        --no-link) NO_LINK=1;            shift ;;
        --force)   FORCE=1;              shift ;;
        -h|--help) usage; exit 0 ;;
        *) err "未知参数: $1"; echo; usage; exit 1 ;;
    esac
done

INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"

printf "%s\n" "=============================================="
printf "  常用工具集 - 一键安装\n"
printf "%s\n" "=============================================="
printf "  仓库地址: %s\n" "${REPO:-<未指定>}"
printf "  安装目录: %s\n" "$INSTALL_DIR"
printf "  分支    : %s\n" "$BRANCH"
printf "\n"

# ---------------------------------------------------------------- 1. 环境检查
step "1/5  环境检查"

if ! command -v git >/dev/null 2>&1; then
    err "未找到 git"
    info "  Termux:  pkg install git"
    info "  Debian:  apt install git"
    exit 1
fi
ok "git $(git --version 2>&1 | awk '{print $3}')"

if ! command -v python3 >/dev/null 2>&1; then
    err "未找到 python3"
    info "  Termux:  pkg install python"
    exit 1
fi
ok "python3 $(python3 -V 2>&1 | awk '{print $2}')"

if [ -z "$REPO" ]; then
    err "未指定仓库地址"
    info ""
    info "  三种指定方式(任选一种):"
    info "    1) bash bootstrap.sh --repo <仓库地址>"
    info "    2) TOOLBOX_REPO=<仓库地址> bash bootstrap.sh"
    info "    3) 把本脚本第 24 行的 DEFAULT_REPO 改成你的仓库地址"
    exit 1
fi

# ---------------------------------------------------------------- 2. 获取代码
step "2/5  获取项目代码"

if [ -d "$INSTALL_DIR/.git" ]; then
    info "目录已是 git 仓库, 尝试更新..."
    if git -C "$INSTALL_DIR" pull --ff-only -q 2>/dev/null; then
        ok "已更新到最新版本"
    else
        warn "更新失败(可能无网络或有本地改动), 继续使用现有版本"
    fi
elif [ -e "$INSTALL_DIR" ]; then
    if [ "$FORCE" = 1 ]; then
        warn "删除已存在的目录: $INSTALL_DIR"
        rm -rf "$INSTALL_DIR"
    else
        err "目录已存在且不是 git 仓库: $INSTALL_DIR"
        info "  处理方式(任选一种):"
        info "    1) 加 --force 删除后重装"
        info "    2) 用 --dir 换一个安装目录"
        exit 1
    fi
fi

if [ ! -d "$INSTALL_DIR/.git" ]; then
    mkdir -p "$(dirname "$INSTALL_DIR")" 2>/dev/null
    info "正在克隆 $REPO ..."
    if git clone -q --depth 1 -b "$BRANCH" "$REPO" "$INSTALL_DIR" 2>/dev/null; then
        ok "克隆成功 ($BRANCH)"
    elif git clone -q --depth 1 "$REPO" "$INSTALL_DIR" 2>/dev/null; then
        ok "克隆成功 (默认分支)"
        BRANCH="$(git -C "$INSTALL_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
    else
        err "克隆失败"
        info "  请检查仓库地址、网络、以及是否有访问权限"
        exit 1
    fi
fi

if [ ! -f "$INSTALL_DIR/main.py" ]; then
    err "克隆下来的目录里没有 main.py, 仓库内容可能不对"
    exit 1
fi

chmod +x "$INSTALL_DIR/run.sh" 2>/dev/null
chmod +x "$INSTALL_DIR/install.sh" 2>/dev/null
ok "项目就绪: $INSTALL_DIR"

# ---------------------------------------------------------------- 3. 加入 PATH
step "3/5  配置 toolbox 命令"

if [ "$NO_LINK" = 1 ]; then
    info "已跳过(--no-link)"
else
    detect_bin() {
        local d
        for d in "${PREFIX:-}/bin" "$HOME/.local/bin" "$HOME/bin" "/usr/local/bin"; do
            [ -n "$d" ] && [ "$d" != "/bin" ] && [ -d "$d" ] && [ -w "$d" ] && { printf '%s' "$d"; return; }
        done
        mkdir -p "$HOME/.local/bin" 2>/dev/null && printf '%s' "$HOME/.local/bin"
    }
    [ -n "$BINDIR" ] || BINDIR="$(detect_bin)"
    if [ -z "$BINDIR" ]; then
        warn "找不到可写的命令目录, 跳过建命令"
    else
        mkdir -p "$BINDIR" 2>/dev/null
        if ln -sfn "$INSTALL_DIR/run.sh" "$BINDIR/toolbox" 2>/dev/null; then
            ok "已创建命令: $BINDIR/toolbox"
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
                    if [ -t 0 ]; then
                        printf "%s是否加入 PATH (写入 %s)? (y/n) %s" "$C_KEY" "$RC" "$C_RST"
                        read -r ans
                    else
                        ans="y"
                    fi
                    case "$ans" in
                        y|Y|yes|YES|"")
                            if ! grep -qs "$BINDIR" "$RC" 2>/dev/null; then
                                {
                                    printf '\n'
                                    printf '# 常用工具集\n'
                                    printf 'export PATH="%s:$PATH"\n' "$BINDIR"
                                } >> "$RC"
                                ok "已写入 $RC"
                            else
                                info "$RC 里已有相关配置"
                            fi
                            info "  执行  source $RC  或重开终端后生效"
                            ;;
                        *) info "已跳过, 可手动: export PATH=\"$BINDIR:\$PATH\"" ;;
                    esac
                    ;;
            esac
        else
            warn "创建软链接失败, 可直接用 $INSTALL_DIR/run.sh 启动"
        fi
    fi
fi

# ---------------------------------------------------------------- 4. 数据文件
step "4/5  检查数据文件"

if [ -f "$INSTALL_DIR/data/regions.txt" ] && [ -f "$INSTALL_DIR/data/phone.dat" ]; then
    ok "数据文件齐备"
else
    warn "数据文件缺失"
    info "  身份证地区码 / 手机号归属地功能需要它们"
    info "  运行下面命令自动下载:"
    info "    $INSTALL_DIR/run.sh --fix-data"
fi

# ---------------------------------------------------------------- 5. 使用方法
step "5/5  安装完成"

if [ "$NO_LINK" = 1 ] || [ -z "$BINDIR" ]; then
    CMD="$INSTALL_DIR/run.sh"
else
    CMD="toolbox"
    case ":${PATH}:" in
        *":$BINDIR:"*) : ;;
        *) CMD="$BINDIR/toolbox" ;;
    esac
fi

printf "\n"
printf "%s\n" "=============================================="
printf "%s  安装完成%s\n" "$C_OK" "$C_RST"
printf "%s\n" "=============================================="
printf "  项目目录: %s\n" "$INSTALL_DIR"
printf "  启动命令: %s\n" "$CMD"
printf "\n"
printf "%s【使用方法】%s\n" "$C_TITLE" "$C_RST"
printf "  %s\n" "$CMD                    # 启动主程序"
printf "  %s\n" "$CMD -h                 # 查看启动脚本帮助"
printf "  %s\n" "$CMD --fix-data         # 下载/修复数据文件"
printf "\n"
printf "%s【主菜单】%s\n" "$C_TITLE" "$C_RST"
printf "  [1] 身份证菜单\n"
printf "      [1] 后四位穷举          [2] 17位补校验位\n"
printf "      [3] 校验18位号码        [4] 批量校验(从文件)\n"
printf "      [5] 信息提取            [6] 按生肖/星座反推号码\n"
printf "  [2] 手机号菜单\n"
printf "      [1] 查询归属地          [2] 前三后二穷举手机号\n"
printf "      [3] 批量归属地查询      [4] 号段反查(按地区)\n"
printf "      [5] 格式化 / 脱敏\n"
printf "  [3] 检查更新\n"
printf "  [0] 退出\n"
printf "\n"
printf "%s【通用操作】%s\n" "$C_TITLE" "$C_RST"
printf "  输入 exit / back / 返回  -> 返回上一层\n"
printf "  分页时输入 q             -> 回主菜单\n"
printf "  Ctrl+C                   -> 随时中断\n"
printf "\n"
printf "%s【维护】%s\n" "$C_TITLE" "$C_RST"
printf "  检查更新: %s --check\n" "$CMD"
printf "  更新代码: %s --update    (或 cd %s && git pull)\n" "$CMD" "$INSTALL_DIR"
printf "  屏蔽更新: %s --mute      (恢复: %s --unmute)\n" "$CMD" "$CMD"
printf "  查看状态: %s/install.sh --status\n" "$INSTALL_DIR"
printf "  卸载命令: %s/install.sh -u\n" "$INSTALL_DIR"
printf "  完整文档: %s/使用说明.md\n" "$INSTALL_DIR"
printf "%s\n" "=============================================="
printf "\n"
info "提示: 结果仅保证格式合法, 请仅用于本人证件或已获授权的合法用途。"
