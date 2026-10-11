#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包脚本 —— 把项目打成少量文件

用法:
    python3 build.py pyz            打包成单文件 toolbox.pyz (源码可见, 体积最小)
    python3 build.py pyc            打包成 .pyc 版 (源码不可见, 需同版本 Python)
    python3 build.py pyz --embed    单文件, 数据也打包进去 (约 5MB, 真正一个文件)
    python3 build.py cython         用 Cython 编译成 .so 机器码 (最难反编译)
    python3 build.py binary         用 Nuitka 编译成可执行文件 (需 pip install nuitka)
    python3 build.py clean          清理 dist/

产物在 dist/ 目录。
"""

import compileall
import os
import py_compile
import shutil
import stat
import importlib.machinery
import subprocess
import sys
import sysconfig
import tempfile
import zipapp

SRC = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(SRC, "dist")
TMP = os.path.join(SRC, ".build_tmp")

MODULES = ["paths.py", "common.py", "lunar.py", "idbase.py", "idcard.py",
           "phonedb.py", "phone.py", "updater.py", "web.py"]
ENTRY = "main.py"
RESOURCES = ["webui.html", "VERSION"]
DATA = ["regions.txt", "phone.dat", "ids_sample.txt"]

C_OK = "\033[1;32m"; C_ERR = "\033[1;31m"; C_WARN = "\033[1;35m"
C_DIM = "\033[2m"; C_RST = "\033[0m"


def ok(m):   print("%s[OK]%s %s" % (C_OK, C_RST, m))
def err(m):  print("%s[错误]%s %s" % (C_ERR, C_RST, m))
def warn(m): print("%s[警告]%s %s" % (C_WARN, C_RST, m))
def info(m): print("%s%s%s" % (C_DIM, m, C_RST))


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.1f TB" % n


def size_of(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total


MAIN_TEMPLATE = '''# -*- coding: utf-8 -*-
"""打包入口"""
import os
import sys

_pkg = os.path.dirname(os.path.abspath(__file__))   # /path/toolbox.pyz
_base = os.path.dirname(_pkg)                       # /path
_embed = __EMBED__


def _prepare_data():
    if _embed:
        import zipfile
        cache = os.path.join(os.path.expanduser("~"), ".cache", "toolbox", "data")
        need = ["regions.txt", "phone.dat"]
        if not all(os.path.isfile(os.path.join(cache, f)) for f in need):
            os.makedirs(cache, exist_ok=True)
            try:
                with zipfile.ZipFile(_pkg) as z:
                    for n in z.namelist():
                        if n.startswith("data/") and not n.endswith("/"):
                            dst = os.path.join(cache, os.path.basename(n))
                            with z.open(n) as s, open(dst, "wb") as d:
                                d.write(s.read())
            except Exception:
                pass
        os.environ["TOOLBOX_DATA_DIR"] = cache
    else:
        if os.path.isdir(_base):
            os.environ.setdefault("TOOLBOX_DATA_DIR", os.path.join(_base, "data"))


_prepare_data()

import main as _main

if __name__ == "__main__":
    try:
        if _main.cli_extra():
            sys.exit(0)
        import updater
        if updater.cli(sys.argv[1:]):
            sys.exit(0)
        _main.main()
    except KeyboardInterrupt:
        print("\\n已取消")
        sys.exit(130)
'''


def clean():
    for d in (DIST, TMP):
        if os.path.isdir(d):
            shutil.rmtree(d)
    ok("已清理 dist/ 和 .build_tmp/")


def prepare(embed=False, as_pyc=False):
    """准备构建目录"""
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)

    # 资源
    for r in RESOURCES:
        src = os.path.join(SRC, r)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(TMP, r))
        else:
            warn("缺少资源: " + r)

    if as_pyc:
        for m in MODULES + [ENTRY]:
            src = os.path.join(SRC, m)
            if not os.path.isfile(src):
                err("缺少模块: " + m)
                return False
            dst = os.path.join(TMP, m[:-3] + ".pyc")
            py_compile.compile(src, cfile=dst, doraise=True)
    else:
        for m in MODULES + [ENTRY]:
            src = os.path.join(SRC, m)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(TMP, m))
            else:
                err("缺少模块: " + m)
                return False

    if embed:
        os.makedirs(os.path.join(TMP, "data"), exist_ok=True)
        for f in DATA:
            src = os.path.join(SRC, "data", f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(TMP, "data", f))

    with open(os.path.join(TMP, "__main__.py"), "w", encoding="utf-8") as f:
        f.write(MAIN_TEMPLATE.replace("__EMBED__", "True" if embed else "False"))
    return True


def build_zipapp(name, embed=False, as_pyc=False):
    os.makedirs(DIST, exist_ok=True)
    if not prepare(embed=embed, as_pyc=as_pyc):
        return None
    out = os.path.join(DIST, name)
    zipapp.create_archive(TMP, target=out, interpreter="/usr/bin/env python3",
                          compressed=True)
    os.chmod(out, os.stat(out).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    shutil.rmtree(TMP, ignore_errors=True)
    return out


def cmd_pyz(embed=False, as_pyc=False):
    print("=" * 52)
    print("  打包: %s" % ("单文件(含数据)" if embed else
                        (".pyc 版" if as_pyc else "单文件")))
    print("=" * 52)

    if as_pyc:
        name = "toolbox-pyc.pyz"
    elif embed:
        name = "toolbox-standalone.pyz"
    else:
        name = "toolbox.pyz"

    out = build_zipapp(name, embed=embed, as_pyc=as_pyc)
    if not out:
        return 1
    ok("已生成 %s  (%s)" % (os.path.relpath(out, SRC), human(size_of(out))))

    # 非内嵌模式: 把数据文件放到 dist/data
    if not embed:
        ddir = os.path.join(DIST, "data")
        os.makedirs(ddir, exist_ok=True)
        n = 0
        for f in DATA:
            src = os.path.join(SRC, "data", f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(ddir, f))
                n += 1
        if n:
            ok("已复制 %d 个数据文件到 dist/data/  (%s)" % (n, human(size_of(ddir))))

    print()
    print("  运行方式:")
    print("    python3 %s" % os.path.relpath(out, SRC))
    if not embed:
        print("    (数据文件需与 .pyz 放在同一目录的 data/ 下)")
    print()
    print("  整体大小: %s" % human(size_of(DIST)))
    print()
    if as_pyc:
        warn("注意: .pyc 与 Python 版本绑定, 当前为 %d.%d" % sys.version_info[:2])
        warn("      换 Python 版本需重新打包")
    if not embed:
        info("提示: 加 --embed 可把数据也打包进去, 变成真正的单个文件")
    return 0


ENTRY_TEMPLATE = """# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main

if __name__ == "__main__":
    try:
        if main.cli_extra():
            sys.exit(0)
        import updater
        if updater.cli(sys.argv[1:]):
            sys.exit(0)
        main.main()
    except KeyboardInterrupt:
        print("\\n已取消")
        sys.exit(130)
"""


def cmd_cython():
    print("=" * 52)
    print("  打包: Cython 编译成机器码 (.so)")
    print("=" * 52)
    try:
        import Cython  # noqa: F401
    except ImportError:
        err("未安装 cython")
        info("  安装:  pip install cython")
        return 1

    inc = sysconfig.get_paths()["include"]
    libdir = sysconfig.get_config_var("LIBDIR") or ""
    pyver = "%d.%d" % sys.version_info[:2]
    suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    cc = os.environ.get("CC", "cc")

    info("  头文件  : " + inc)
    info("  libpython: %s/libpython%s.so" % (libdir, pyver))
    info("  扩展后缀 : " + suffix)
    print()

    outdir = os.path.join(DIST, "toolbox-native")
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    work = os.path.join(TMP, "cy")
    os.makedirs(work, exist_ok=True)

    link = [cc, "-shared", "-fPIC", "-O2", "-I", inc]
    if libdir:
        link += ["-L", libdir, "-lpython" + pyver, "-Wl,-rpath," + libdir]

    targets = MODULES + [ENTRY]
    total = len(targets)
    for i, m in enumerate(targets, 1):
        src = os.path.join(SRC, m)
        if not os.path.isfile(src):
            err("缺少模块: " + m)
            return 1
        base = m[:-3]
        cfile = os.path.join(work, base + ".c")
        sofile = os.path.join(outdir, base + suffix)
        print("  [%d/%d] %-12s 编译中..." % (i, total, m), end="", flush=True)
        try:
            subprocess.run([sys.executable, "-m", "cython", "-3", src, "-o", cfile],
                           check=True, capture_output=True)
            subprocess.run(link + [cfile, "-o", sofile],
                           check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print()
            err("编译失败: " + m)
            msg = (e.stderr or b"").decode("utf-8", "ignore").strip()
            for ln in msg.splitlines()[-8:]:
                info("    " + ln)
            return 1
        print("\r  [%d/%d] %-12s OK          " % (i, total, m))

    # 资源
    for r in RESOURCES:
        src = os.path.join(SRC, r)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(outdir, r))

    # 启动器(仅几行胶水代码)
    with open(os.path.join(outdir, "_entry.py"), "w", encoding="utf-8") as f:
        f.write(ENTRY_TEMPLATE)

    # 数据
    ddir = os.path.join(outdir, "data")
    os.makedirs(ddir, exist_ok=True)
    for f in DATA:
        src = os.path.join(SRC, "data", f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(ddir, f))

    # 启动脚本
    launcher = os.path.join(outdir, "toolbox")
    with open(launcher, "w", encoding="utf-8") as f:
        f.write('#!/data/data/com.termux/files/usr/bin/env bash\n'
                'DIR="$(cd "$(dirname "$0")" && pwd)"\n'
                'exec python3 "$DIR/_entry.py" "$@"\n')
    os.chmod(launcher, 0o755)

    shutil.rmtree(work, ignore_errors=True)
    print()
    ok("已生成 %s  (%s)" % (os.path.relpath(outdir, SRC), human(size_of(outdir))))
    print()
    print("  运行:  %s/toolbox" % os.path.relpath(outdir, SRC))
    print("     或  python3 %s/_entry.py" % os.path.relpath(outdir, SRC))
    print()
    info("  说明: 逻辑全部编译成机器码, 源码不可见")
    info("        _entry.py 只有十几行胶水代码")
    warn("  注意: .so 与 Python 版本/平台绑定, 换环境需重新编译")
    return 0


def cmd_binary():
    print("=" * 52)
    print("  打包: Nuitka 编译可执行文件")
    print("=" * 52)
    try:
        import nuitka  # noqa: F401
    except ImportError:
        err("未安装 nuitka")
        info("  安装:  pip install nuitka")
        info("  编译较慢(几分钟), 且需要 C 编译器")
        return 1

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "toolbox.bin")
    cmd = [sys.executable, "-m", "nuitka",
           "--standalone", "--onefile",
           "--output-dir=" + DIST,
           "--output-filename=toolbox",
           "--include-data-dir=%s=%s" % (os.path.join(SRC, "data"), "data"),
           "--include-data-file=%s=webui.html" % os.path.join(SRC, "webui.html"),
           "--include-data-file=%s=VERSION" % os.path.join(SRC, "VERSION"),
           "--assume-yes-for-downloads",
           os.path.join(SRC, ENTRY)]
    info("  执行: " + " ".join(cmd[:6]) + " ...")
    try:
        subprocess.run(cmd, cwd=SRC, check=True)
    except subprocess.CalledProcessError as e:
        err("编译失败: %s" % e)
        return 1
    ok("已生成可执行文件于 dist/")
    print()
    info("  运行:  ./dist/toolbox.bin")
    return 0


def usage():
    print(__doc__)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        usage()
        return 0

    cmd = args[0]
    embed = "--embed" in args
    if cmd == "clean":
        clean()
        return 0
    if cmd == "pyz":
        return cmd_pyz(embed=embed, as_pyc=False)
    if cmd == "pyc":
        return cmd_pyz(embed=embed, as_pyc=True)
    if cmd == "cython":
        return cmd_cython()
    if cmd == "binary":
        return cmd_binary()
    err("未知命令: " + cmd)
    print()
    usage()
    return 1


if __name__ == "__main__":
    sys.exit(main())
