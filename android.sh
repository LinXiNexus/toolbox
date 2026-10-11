#!/data/data/com.termux/files/usr/bin/bash
# =============================================================
#  安卓环境辅助脚本
#
#  用法:
#    ./android.sh            安装桌面快捷方式 + 显示使用指引
#    ./android.sh shortcuts  只建 Termux:Widget 快捷方式
#    ./android.sh guide      只显示使用指引
#    ./android.sh info       显示安卓环境信息
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

C_OK=$'\033[1;32m'; C_ERR=$'\033[1;31m'; C_WARN=$'\033[1;35m'
C_KEY=$'\033[1;33m'; C_TITLE=$'\033[1;36m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
ok()   { printf "%s[OK]%s %s\n"   "$C_OK"   "$C_RST" "$1"; }
err()  { printf "%s[错误]%s %s\n" "$C_ERR"  "$C_RST" "$1"; }
warn() { printf "%s[警告]%s %s\n" "$C_WARN" "$C_RST" "$1"; }
info() { printf "%s%s%s\n"        "$C_DIM"  "$1"     "$C_RST"; }
title(){ printf "\n%s== %s ==%s\n" "$C_TITLE" "$1" "$C_RST"; }

RUN="$DIR/run.sh"
[ -x "$RUN" ] || RUN="bash $DIR/run.sh"

# ---------------------------------------------------------------- 快捷方式
cmd_shortcuts() {
    title "创建 Termux:Widget 桌面快捷方式"
    local sd="$HOME/.shortcuts"
    mkdir -p "$sd"

    cat > "$sd/工具集" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
"$RUN"
EOF
    cat > "$sd/打开网页" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
echo "正在启动网页界面..."
python3 "$DIR/web.py" --port 8765 --open
EOF
    cat > "$sd/检查更新" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
"$RUN" --check
echo
echo "按回车关闭..."
read -r _
EOF
    chmod +x "$sd"/工具集 "$sd"/打开网页 "$sd"/检查更新
    ok "已创建 3 个快捷方式于 $sd"
    info "  工具集 / 打开网页 / 检查更新"
    echo
    warn "需要在桌面添加 Termux:Widget 小部件才能看到它们"
    info "  1. 安装 Termux:Widget (F-Droid 或 Google Play)"
    info "  2. 长按桌面 → 添加小部件 → Termux:Widget"
    info "  3. 选尺寸后即可看到上面 3 个脚本"
    echo
    info "也可用后台任务方式(不弹终端):"
    info "  mkdir -p ~/.shortcuts/tasks"
    info "  cp '$sd/打开网页' ~/.shortcuts/tasks/"
}

# ---------------------------------------------------------------- 环境信息
cmd_info() {
    title "安卓环境信息"
    printf "  Android : %s\n" "$(getprop ro.build.version.release 2>/dev/null || echo '?')"
    printf "  CPU     : %s\n" "$(getprop ro.product.cpu.abi 2>/dev/null || echo '?')"
    printf "  设备    : %s %s\n" "$(getprop ro.product.brand 2>/dev/null)" "$(getprop ro.product.model 2>/dev/null)"
    printf "  Python  : %s\n" "$(python3 -V 2>&1 | awk '{print $2}')"
    printf "  PREFIX  : %s\n" "$PREFIX"
    echo
    printf "  %s可用的 Termux 能力%s\n" "$C_TITLE" "$C_RST"
    for c in termux-open-url termux-share termux-toast termux-wake-lock termux-notification; do
        if command -v "$c" >/dev/null 2>&1; then
            printf "    %s✓%s %s\n" "$C_OK" "$C_RST" "$c"
        else
            printf "    %s✗%s %s (需 pkg install termux-api + 装 Termux:API 应用)\n" "$C_WARN" "$C_RST" "$c"
        fi
    done
    echo
    printf "  桌面快捷方式目录: %s\n" "$HOME/.shortcuts"
    [ -d "$HOME/.shortcuts" ] && ls -1 "$HOME/.shortcuts" | sed 's/^/    /' || info "    (尚未创建)"
    echo
    printf "  开机自启目录: %s\n" "$HOME/.termux/boot"
    [ -d "$HOME/.termux/boot" ] && ls -1 "$HOME/.termux/boot" | sed 's/^/    /' || info "    (尚未创建，需 Termux:Boot 应用)"
}

# ---------------------------------------------------------------- 指引
cmd_guide() {
    title "安卓上怎么用"
    cat <<'EOF'
方案 A：Termux 命令行（功能最全）
────────────────────────────────────────────
  cd ~/toolbox && ./run.sh

  默认会：后台开网页 + 打开浏览器 + 显示命令行菜单
  只想命令行：  ./run.sh --cli
  只想网页：    ./run.sh --web

方案 B：网页版当 App 用（推荐给日常使用）
────────────────────────────────────────────
  1. 先启动网页服务
       toolbox --web           （或 ./run.sh 后选 [4]）
  2. 手机浏览器打开
       http://127.0.0.1:8765/
  3. 浏览器菜单 → 「添加到主屏幕」
       · Chrome: 右上角 ⋮ → 添加到主屏幕
       · 会自动用「工具集」这个名字和图标
  4. 桌面就会出现一个图标，点开全屏运行，跟 App 一样

  已内置 PWA 支持(manifest + 图标)，所以添加到桌面后
  是独立窗口，没有浏览器地址栏。

方案 C：Termux:Widget 桌面快捷方式
────────────────────────────────────────────
  1. 安装 Termux:Widget 应用
  2. 运行：  ./android.sh shortcuts
  3. 长按桌面 → 添加小部件 → Termux:Widget
  4. 会看到「工具集 / 打开网页 / 检查更新」三个快捷方式

方案 D：其他 Python App（有限支持）
────────────────────────────────────────────
  Pydroid 3 / QPython 等自带 Python 的 App：

  · 能跑「源码版」——把整个 toolbox 目录拷到手机存储，
    用这些 App 打开 main.py 运行
  · 但打包产物大多不能用：
      .pyz  需要 Python 3.8+，且 .pyc 与版本绑定
      .so   与 CPU 架构 + Python ABI 绑定，几乎肯定不兼容
  · 这些 App 的 Python 版本通常和 Termux 不同，
    所以 .pyc / .so 版基本没戏，只能用 .py 源码版

方案 E：真正的 APK
────────────────────────────────────────────
  需要 Kivy / BeeWare + buildozer 把界面重写成原生控件，
  属于另起一个项目，成本很高。

  更划算的做法是「方案 B」：网页版 + 添加到主屏幕，
  体验接近原生 App，零额外成本。

EOF
    printf "%s当前推荐：%s" "$C_TITLE" "$C_RST"
    echo "先跑 ./run.sh 试试，然后按方案 B 把网页加到桌面。"
    echo
}

# ---------------------------------------------------------------- 入口
case "${1:-all}" in
    shortcuts) cmd_shortcuts ;;
    info)      cmd_info ;;
    guide)     cmd_guide ;;
    all)
        cmd_info
        cmd_shortcuts
        cmd_guide
        ;;
    -h|--help)
        sed -n '3,11p' "$SELF" | sed 's/^# \{0,1\}//'
        ;;
    *) err "未知参数: $1"; exit 1 ;;
esac
