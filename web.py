#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""常用工具集 - 本地 Web 界面

纯标准库实现, 复用现有模块, 不依赖任何第三方包。

启动:
    python3 web.py                 # 127.0.0.1:8765
    python3 web.py --port 9000
    python3 web.py --host 0.0.0.0  # 局域网可访问(注意安全)

浏览器打开提示的地址即可使用。
"""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import idbase
import lunar
import phonedb
import updater

HERE = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(HERE, "webui.html")
DEFAULT_PORT = 8765

_region_cache = None
_phone_db = None


def region_codes():
    global _region_cache
    if _region_cache is None:
        _region_cache, _ = idbase.load_region_table()
    return _region_cache


def phone_db():
    global _phone_db
    if _phone_db is None:
        _phone_db = phonedb.PhoneDB()
    return _phone_db


def _norm_prefix(p):
    return re.sub(r"[\s\-]", "", str(p or ""))


# ---------------------------------------------------------------- 身份证 API
def api_id_brute(d):
    prefix = _norm_prefix(d.get("prefix"))
    gender = "男" if d.get("gender") in ("男", "m", "male", 1, "1") else "女"
    if len(prefix) != 14:
        raise ValueError("前 14 位长度应为 14，当前 %d 位" % len(prefix))
    if set(prefix) - set("0123456789?"):
        raise ValueError("只能包含数字和 ? 占位符")

    rc = region_codes()
    ok, errs, infos = idbase.validate_prefix(prefix, rc)

    prefixes = idbase.expand(prefix)
    kept = [p for p in prefixes if idbase.validate_prefix(p, rc)[0]]
    results = []
    for p in kept:
        results.extend(idbase.brute_force(p, gender))
    return {"total": len(results), "results": results[:5000],
            "truncated": len(results) > 5000,
            "valid": ok, "errors": errs, "infos": infos,
            "combos": len(prefixes), "kept": len(kept)}


def api_id_check(d):
    raw = str(d.get("raw", ""))
    norm, err = idbase.normalize_id(raw)
    if err:
        return {"format_error": err, "checks": [], "valid": False}
    ok, checks, gender = idbase.id_check_all(norm, region_codes())
    return {"number": norm, "valid": ok, "gender": gender,
            "checks": [{"name": n, "pass": s, "detail": t} for n, s, t in checks]}


def api_id_checkdigit(d):
    raw = _norm_prefix(d.get("raw"))
    if len(raw) != 17 or not raw.isdigit():
        raise ValueError("需要 17 位数字，当前 %d 位" % len(raw))
    cd = idbase.check_digit(raw)
    y, mo, dd = int(raw[6:10]), int(raw[10:12]), int(raw[12:14])
    ok, msg = idbase.validate_date(raw[6:14])
    return {"prefix": raw, "check": cd, "full": raw + cd,
            "gender": "男" if int(raw[16]) % 2 else "女",
            "birth": "%04d-%02d-%02d" % (y, mo, dd), "date_ok": ok, "date_msg": msg}


def api_id_info(d):
    raw = str(d.get("raw", ""))
    norm, err = idbase.normalize_id(raw)
    if err:
        raise ValueError(err)
    y, mo, dd = int(norm[6:10]), int(norm[10:12]), int(norm[12:14])
    ok, msg = idbase.validate_date(norm[6:14])
    rc = region_codes()
    region = rc.get(norm[:6], "") if rc else ""
    out = {
        "number": norm,
        "province": idbase.PROVINCES.get(norm[:2], "未知") + " (" + norm[:2] + ")",
        "region": (region + " (" + norm[:6] + ")") if region else "不在行政区划表中",
        "birth": "%04d-%02d-%02d" % (y, mo, dd),
        "gender": "男" if int(norm[16]) % 2 else "女",
    }
    if ok:
        out["age"] = lunar.age_of(y, mo, dd)
        out["zodiac"] = lunar.shengxiao_of(y, mo, dd)
        out["constellation"] = lunar.xingzuo_of(mo, dd)
    else:
        out["warn"] = msg
    return out


def api_id_derive(d):
    sx = d.get("zodiac") or None
    xz = d.get("constellation") or None
    a1, a2 = d.get("age_min"), d.get("age_max")
    a1 = int(a1) if a1 not in (None, "") else None
    a2 = int(a2) if a2 not in (None, "") else None
    if sx and sx not in lunar.SHENGXIAO:
        raise ValueError("生肖取值: " + " ".join(lunar.SHENGXIAO))
    names = [nm for _, _, nm in lunar.XINGZUO]
    if xz and xz not in names:
        raise ValueError("星座取值: " + " ".join(names))

    bds = idcard_derive(sx, xz, a1, a2)
    return {"count": len(bds),
            "birthdays": ["%04d%02d%02d" % b for b in bds[:3000]],
            "truncated": len(bds) > 3000}


def idcard_derive(sx, xz, a1, a2):
    import idcard
    return idcard.derive_birthdays(sx, xz, a1, a2)


def api_id_batch(d):
    text = str(d.get("text", ""))
    rc = region_codes()
    rows, ok_cnt = [], 0
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        norm, err = idbase.normalize_id(s)
        if err:
            rows.append({"input": s, "ok": False, "reason": "格式错误: " + err})
            continue
        good, checks, gender = idbase.id_check_all(norm, rc)
        if good:
            ok_cnt += 1
            rows.append({"input": s, "ok": True, "reason": "合法 (%s)" % gender})
        else:
            reason = "；".join("%s %s" % (n, t) for n, st, t in checks if st is False)
            rows.append({"input": s, "ok": False, "reason": reason})
    return {"total": len(rows), "ok": ok_cnt, "bad": len(rows) - ok_cnt, "rows": rows}


# ---------------------------------------------------------------- 手机号 API
def api_phone_lookup(d):
    db = phone_db()
    if not db.path:
        raise ValueError("未找到 phone.dat 号段库")
    out = []
    for it in re.split(r"[\s,，、;；]+", str(d.get("text", "")).strip()):
        if not it:
            continue
        digits = re.sub(r"\D", "", it)
        ok, msg = phonedb.phone_validate(digits)
        if not ok:
            out.append({"input": it, "ok": False, "reason": msg})
            continue
        info = db.lookup(digits)
        if not info:
            out.append({"input": it, "ok": False, "reason": "号段 %s 不在库中" % digits[:7]})
            continue
        region = info["province"] + ("" if info["city"] in ("", info["province"])
                                     else " " + info["city"])
        out.append({"input": it, "ok": True, "region": region, "type": info["type"],
                    "zip": info["zip"], "area": info["area"]})
    return {"rows": out}


def api_phone_brute(d):
    import phone
    seg3 = re.sub(r"\D", "", str(d.get("seg3", "")))
    last2 = re.sub(r"\D", "", str(d.get("last2", "")))
    ok, msg = phone.phone_seg3_validate(seg3)
    if not ok:
        raise ValueError("前三位: " + msg)
    ok, msg = phone.phone_last2_validate(last2)
    if not ok:
        raise ValueError("后两位: " + msg)

    db = phone_db()
    hlr = None
    if d.get("region"):
        if not db.path:
            raise ValueError("未找到号段库，无法按归属地筛选")
        kw = str(d["region"]).strip()
        hits = db.search_region(kw)
        if not hits:
            raise ValueError("没有匹配 '%s' 的号段" % kw)
        hlr = sorted(set(p7[3:7] for p7, _ in hits))
    total = (10000 if hlr is None else len(hlr)) * 100
    if total > 200000:
        raise ValueError("结果过多(%d)，请填写归属地筛选" % total)
    results = []
    for n in phone.phone_brute_iter(seg3, last2, hlr):
        results.append(n)
        if len(results) >= 20000:
            break
    return {"total": total, "results": results, "truncated": total > len(results),
            "hlr_count": 10000 if hlr is None else len(hlr)}


def api_phone_seg(d):
    db = phone_db()
    if not db.path:
        raise ValueError("未找到 phone.dat 号段库")
    kw = str(d.get("keyword", "")).strip()
    if not kw:
        raise ValueError("请输入地区关键字")
    hits = db.search_region(kw)
    groups = {}
    for p7, info in hits:
        key = (info["province"], info["city"], info["type"])
        groups.setdefault(key, []).append(p7)
    out = []
    for k in sorted(groups):
        prov, city, typ = k
        name = prov + ("" if city in ("", prov) else " " + city)
        out.append({"name": name, "type": typ, "count": len(groups[k]),
                    "segments": sorted(groups[k])})
    return {"total": len(hits), "groups": out}


def api_phone_format(d):
    mode = str(d.get("mode", "1"))
    out = []
    for it in re.split(r"[\s,，、;；]+", str(d.get("text", "")).strip()):
        if not it:
            continue
        digits = re.sub(r"\D", "", it)
        v = digits[2:] if (len(digits) == 13 and digits.startswith("86")) else digits
        if len(v) != 11:
            out.append({"input": it, "ok": False, "reason": "需要 11 位数字"})
            continue
        if mode == "1":
            r = "%s %s %s" % (v[:3], v[3:7], v[7:])
        elif mode == "2":
            r = v[:3] + "****" + v[7:]
        elif mode == "3":
            r = v
        else:
            r = "+86 %s %s %s" % (v[:3], v[3:7], v[7:])
        out.append({"input": it, "ok": True, "result": r})
    return {"rows": out}


# ---------------------------------------------------------------- 通用 API
def api_version(d):
    return {"version": updater.local_version()}


def api_check_update(d):
    info = updater.check(force=True)
    cfg = updater.load_config()
    return {"local": info.get("local"), "remote": info.get("remote"),
            "has_update": bool(info.get("has_update")), "newer": bool(info.get("newer")),
            "was_skipped": bool(info.get("was_skipped")),
            "muted": bool(cfg["muted"]), "error": info.get("error")}


def api_do_update(d):
    """执行 git pull 更新"""
    before = updater.local_version()
    ok, msg = updater.do_update()
    after = updater.local_version()
    return {"ok": ok, "message": msg, "before": before, "after": after,
            "changed": before != after, "is_git": updater.project_is_git()}


def api_skip_version(d):
    v = str(d.get("version", "")).strip()
    cfg = updater.load_config()
    if v and v not in cfg["skipped"]:
        cfg["skipped"].append(v)
        updater.save_config(cfg)
    return {"skipped": cfg["skipped"]}


def api_mute(d):
    cfg = updater.load_config()
    cfg["muted"] = bool(d.get("muted", True))
    cfg["last_check"] = 0
    updater.save_config(cfg)
    return {"muted": cfg["muted"]}


def api_config(d):
    cfg = updater.load_config()
    return {"skipped": cfg["skipped"], "muted": cfg["muted"],
            "interval": cfg.get("interval"), "version": updater.local_version()}


ROUTES = {
    "/api/id/brute": api_id_brute,
    "/api/id/check": api_id_check,
    "/api/id/checkdigit": api_id_checkdigit,
    "/api/id/info": api_id_info,
    "/api/id/derive": api_id_derive,
    "/api/id/batch": api_id_batch,
    "/api/phone/lookup": api_phone_lookup,
    "/api/phone/brute": api_phone_brute,
    "/api/phone/seg": api_phone_seg,
    "/api/phone/format": api_phone_format,
    "/api/version": api_version,
    "/api/check_update": api_check_update,
    "/api/update": api_do_update,
    "/api/skip": api_skip_version,
    "/api/mute": api_mute,
    "/api/config": api_config,
}


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "toolbox-web/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[web] %s %s\n" % (self.address_string(), fmt % args))
        sys.stderr.flush()

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            try:
                with open(HTML_FILE, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, "找不到 webui.html", "text/plain; charset=utf-8")
            return
        if path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return
        self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            self._json({"ok": False, "error": "请求体不是合法 JSON"}, 400)
            return
        fn = ROUTES.get(path)
        if not fn:
            self._json({"ok": False, "error": "未知接口: " + path}, 404)
            return
        try:
            self._json({"ok": True, "data": fn(data)})
        except ValueError as e:
            self._json({"ok": False, "error": str(e)}, 200)
        except Exception as e:
            self._json({"ok": False, "error": "%s: %s" % (type(e).__name__, e)}, 200)


def open_url(url):
    """尝试用系统方式打开浏览器(Termux 优先)"""
    if shutil.which("termux-open-url"):
        try:
            subprocess.Popen(["termux-open-url", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
    for c in ("xdg-open", "open"):
        if shutil.which(c):
            try:
                subprocess.Popen([c, url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
    try:
        import webbrowser
        return webbrowser.open(url)
    except Exception:
        return False


def port_free(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def serve(host="127.0.0.1", port=DEFAULT_PORT, open_browser=False, quiet=False):
    if not port_free(host, port):
        if not quiet:
            print("启动失败: 端口 %d 已被占用" % port, file=sys.stderr)
            print("换个端口: python3 web.py --port %d" % (port + 1), file=sys.stderr)
        return 1
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    url = "http://%s:%d/" % (host if host != "0.0.0.0" else "127.0.0.1", port)
    if not quiet:
        print("=" * 52)
        print("  常用工具集 - Web 界面")
        print("=" * 52)
        print("  版本    : v%s" % updater.local_version())
        print("  访问地址: %s" % url)
        if host == "0.0.0.0":
            print("  [注意]  已监听所有网卡，局域网内其他设备可访问")
        print("  停止    : Ctrl+C")
        print("=" * 52)
        sys.stdout.flush()
    if open_browser:
        threading.Thread(target=lambda: open_url(url), daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        if not quiet:
            print("\n已停止")
    finally:
        srv.server_close()
    return 0


def web_url(port=DEFAULT_PORT):
    return "http://127.0.0.1:%d/" % port


def main():
    ap = argparse.ArgumentParser(description="常用工具集 Web 界面")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--open", action="store_true", help="启动后尝试打开浏览器")
    args = ap.parse_args()
    sys.exit(serve(args.host, args.port, args.open))


if __name__ == "__main__":
    main()
