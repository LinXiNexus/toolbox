#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手机号交互功能"""

import sys
import os
import re
import csv

from common import (line, ask, ask_input, show_list, BackToPrev, HOME,
                    C_TITLE, C_KEY, C_OK, C_ERR, C_WARN, C_DIM, C_RST)
from phonedb import PHONE_TYPES, PhoneDB, phone_validate

def run_phone_lookup():
    line()
    print(C_TITLE + "[手机号] 归属地 / 运营商查询" + C_RST)
    line()
    db = PhoneDB()
    if not db.path:
        print(C_ERR + " [错误] 未找到 phone.dat 号段库。" + C_RST)
        print(C_DIM + " 请执行以下命令下载后重试：" + C_RST)
        print(C_DIM + '   curl -sSL -o ~/phone.dat "https://raw.githubusercontent.com/ls0f/phone/master/phone/phone.dat"' + C_RST)
        return
    print(" 号段库: %s" % db.path)
    print(" 记录数: %d 条    数据版本: %s" % (db.count, db.version_str))
    print(C_DIM + " 前 7 位即可确定归属地；支持 7-11 位，可一次查多个(空格/逗号分隔)。" + C_RST)
    print(C_DIM + " 输入 空行 或 q 返回主菜单。" + C_RST)
    print()

    while True:
        try:
            raw = ask_input(C_KEY + " 请输入手机号 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        if not raw or raw.lower() in ("q", "quit", "0"):
            return
        items = [x for x in re.split(r"[\s,，、;；]+", raw) if x]
        print()
        for it in items:
            if not it.isdigit():
                print(C_ERR + " %-13s [错误] 只能包含数字" % it + C_RST)
                continue
            digits = it
            ok, msg = phone_validate(digits)
            if not ok:
                print(C_ERR + " %-13s [错误] %s" % (it, msg) + C_RST)
                continue
            info = db.lookup(digits)
            if not info:
                print(C_WARN + " %-13s [未找到] 号段 %s 不在库中" % (it, digits[:7]) + C_RST)
                continue
            region = info["province"] + ("" if info["city"] in ("", info["province"]) else " " + info["city"])
            print(C_OK + " %s" % digits + C_RST)
            print("   - 归属地: " + C_KEY + region + C_RST)
            print("   - 运营商: " + C_KEY + info["type"] + C_RST)
            print("   - 邮编  : " + info["zip"] + "    长途区号: " + (info["area"] or "-"))
        print()


# ================================================================ 模块2b: 手机号穷举

def phone_seg3_validate(x):
    if not x.isdigit():
        return False, "只能包含数字"
    if len(x) != 3:
        return False, "应为 3 位，当前 %d 位" % len(x)
    if x[0] != "1":
        return False, "手机号必须以 1 开头"
    if x[1] not in "3456789":
        return False, "第 2 位应为 3-9（当前 %s）" % x[1]
    return True, ""

def phone_last2_validate(x):
    if not x.isdigit():
        return False, "只能包含数字"
    if len(x) != 2:
        return False, "应为 2 位，当前 %d 位" % len(x)
    return True, ""

def ask_seg3():
    line()
    print(C_TITLE + "[穷举] 第 1 次输入 / 共 2 次: 手机号前三位" + C_RST)
    line()
    print(" 前三位就是运营商号段，如 138 / 159 / 199。")
    print(" 加上下一步的后两位，合计 5 位。")
    print(C_DIM + "   1-3     4-7       8-9     10-11" + C_RST)
    print(C_DIM + "   号段    HLR地区码  未知    后两位" + C_RST)
    print(C_DIM + "   ^^^本次输入          (待穷举) ^^^下次输入" + C_RST)
    print()
    while True:
        x = ask_input(C_KEY + " 请输入前三位 (exit 返回) > " + C_RST)
        ok, msg = phone_seg3_validate(x)
        if not ok:
            print(C_ERR + " [错误] %s。" % msg + C_RST); continue
        print(C_OK + " [OK] 已记录: %s" % x + C_RST)
        return x

def ask_last2(seg3=None):
    line()
    print(C_TITLE + "[穷举] 第 2 次输入 / 共 2 次: 手机号后两位" + C_RST)
    line()
    print(" 即第 10-11 位，如 88。")
    if seg3:
        print(" 已记录前三位: " + C_KEY + seg3 + C_RST + "  还差后两位，合计 5 位。")
    print()
    while True:
        x = ask_input(C_KEY + " 请输入后两位 (exit 返回) > " + C_RST)
        ok, msg = phone_last2_validate(x)
        if not ok:
            print(C_ERR + " [错误] %s。" % msg + C_RST); continue
        print(C_OK + " [OK] 已记录: %s" % x + C_RST)
        return x

def ask_region_filter(db, seg3):
    """返回 (hlr_list 或 None, 描述文本)"""
    line()
    print(C_TITLE + "[穷举] 第 3 步: 是否按归属地筛选(可选)" + C_RST)
    line()
    if not db or not db.path:
        print(C_DIM + " 未找到号段库，跳过筛选。" + C_RST)
        return None, "不筛选"
    prefixes = db.prefixes_for(seg3)
    if not prefixes:
        print(C_WARN + " [警告] 号段 %s 不在库中，无法筛选。" % seg3 + C_RST)
        return None, "不筛选"

    groups = {}
    for p7, info in prefixes.items():
        key = (info["province"], info["city"], info["type"])
        groups.setdefault(key, []).append(p7[3:7])
    keys = sorted(groups)

    def name_of(k):
        prov, city, typ = k
        return (prov + ("" if city in ("", prov) else " " + city), typ)

    def print_range(a, b):
        for i in range(a, min(b, len(keys))):
            nm, typ = name_of(keys[i])
            print("   [%3d] %-14s %-10s (%d 个号段)" % (i + 1, nm, typ, len(groups[keys[i]])))

    shown = 30
    print(" 号段 %s 在库中覆盖 %d 个归属地：" % (seg3, len(keys)))
    print_range(0, shown)
    if len(keys) > shown:
        print(C_DIM + " ... 共 %d 个，仅显示前 %d 个。输入 all 查看全部。" % (len(keys), shown) + C_RST)
    print()
    print(C_DIM + " 不筛选 -> 第 4-9 位全排列，共 1,000,000 个号码。" + C_RST)
    print(C_DIM + " 筛选后 -> 仅枚举该地区的 HLR 码，数量大幅减少。" + C_RST)
    print()

    while True:
        ans = ask_input(C_KEY + " 序号 / 关键字 / all 全部 / 回车不筛选 (exit 返回) > " + C_RST)
        if not ans:
            print(C_OK + " [OK] 不筛选。" + C_RST)
            return None, "不筛选"
        if ans.lower() in ("all", "全部", "list"):
            i = shown
            while i < len(keys):
                print_range(i, i + 40)
                i += 40
                if i < len(keys):
                    if ask(C_DIM + " 回车继续 / 其他结束列表 > " + C_RST).strip():
                        break
            print()
            continue
        if ans.isdigit():
            idx = int(ans)
            if 1 <= idx <= len(keys):
                k = keys[idx - 1]
                nm, typ = name_of(k)
                hlrs = sorted(set(groups[k]))
                print(C_OK + " [OK] 已筛选: %s %s (%d 个号段)" % (nm, typ, len(hlrs)) + C_RST)
                return hlrs, "%s %s" % (nm, typ)
            print(C_ERR + " [错误] 序号超出范围。" + C_RST); continue
        hit = [k for k in keys if ans in k[0] or ans in k[1]]
        if len(hit) == 1:
            nm, typ = name_of(hit[0])
            hlrs = sorted(set(groups[hit[0]]))
            print(C_OK + " [OK] 已筛选: %s %s (%d 个号段)" % (nm, typ, len(hlrs)) + C_RST)
            return hlrs, "%s %s" % (nm, typ)
        if len(hit) > 1:
            print(C_WARN + " [警告] 匹配到 %d 个地区，请输入序号（如 1-%d）。" % (len(hit), len(keys)) + C_RST)
            continue
        print(C_ERR + " [错误] 未匹配到地区。" + C_RST)

def phone_brute_iter(seg3, last2, hlr_list):
    """惰性生成候选号码"""
    if hlr_list is None:
        for h in range(10000):
            h4 = "%04d" % h
            for d8 in "0123456789":
                for d9 in "0123456789":
                    yield seg3 + h4 + d8 + d9 + last2
    else:
        for h4 in hlr_list:
            for d8 in "0123456789":
                for d9 in "0123456789":
                    yield seg3 + h4 + d8 + d9 + last2

def run_phone_brute():
    db = PhoneDB()
    seg3 = last2 = None
    hlr_list = None
    desc = ""
    step = 0
    while step < 3:
        try:
            if step == 0:
                seg3 = ask_seg3(); step = 1
            elif step == 1:
                last2 = ask_last2(seg3); step = 2
            else:
                hlr_list, desc = ask_region_filter(db, seg3); step = 3
        except BackToPrev:
            step -= 1
            if step < 0:
                return
            print(C_WARN + " [返回] 已回到上一步。" + C_RST)

    total = (10000 if hlr_list is None else len(hlr_list)) * 100
    line()
    print(C_TITLE + "生成方案" + C_RST)
    line()
    print(" 前三位: " + C_KEY + seg3 + C_RST + "    后两位: " + C_KEY + last2 + C_RST)
    print(" 筛选  : " + desc)
    print(" 总数  : " + C_KEY + ("%d" % total) + C_RST)
    print()

    if total > 20000:
        print(C_WARN + " [提示] 数量较大，将直接写入文件（逐条生成，不占内存）。" + C_RST)
        default = os.path.join(HOME, "phone_result.txt")
        path = ask_input(C_KEY + " 保存路径 [回车默认 %s, exit 返回] > " % default + C_RST)
        path = os.path.expanduser(path) if path else default
        n = 0
        with open(path, "w", encoding="utf-8") as f:
            for num in phone_brute_iter(seg3, last2, hlr_list):
                f.write(num + "\n")
                n += 1
        print(C_OK + " [OK] 已写入 %d 条到 %s" % (n, path) + C_RST)
        return

    save_path = None
    ans = ask_input(C_KEY + " 保存到文件吗? (y/n, exit 返回) > " + C_RST).lower()
    if ans in ("y", "yes", "是", ""):
        default = os.path.join(HOME, "phone_result.txt")
        pp = ask_input(C_KEY + " 路径 [回车默认 %s, exit 返回] > " % default + C_RST)
        save_path = os.path.expanduser(pp) if pp else default
    results = list(phone_brute_iter(seg3, last2, hlr_list))
    show_list(results, save_path, "生成完成")

def run_phone_batch():
    """从文件批量查询手机号归属地"""
    db = PhoneDB()
    line()
    print(C_TITLE + "[手机号] 批量归属地查询(从文件)" + C_RST)
    line()
    if not db.path:
        print(C_ERR + " [错误] 未找到 phone.dat 号段库。" + C_RST)
        return
    print(" 从文本文件读取号码，每行一个，逐行查询归属地。")
    print(C_DIM + " 空行、以 # 开头的行会被跳过。" + C_RST)
    print()
    default = os.path.join(HOME, "phones.txt")
    print(C_DIM + " 文件不存在时，可先执行:" + C_RST)
    print(C_DIM + "   printf '13800138000\\n19912345678\\n' > ~/phones.txt" + C_RST)
    print()
    while True:
        try:
            path = ask_input(C_KEY + " 文件路径 [回车默认 %s, exit 返回] > " % default + C_RST)
        except BackToPrev:
            return
        path = os.path.expanduser(path) if path else default
        if not os.path.isfile(path):
            print(C_ERR + " [错误] 文件不存在: %s" % path + C_RST); continue
        break

    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError as e:
        print(C_ERR + " [错误] 读取失败: %s" % e + C_RST); return

    items = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    if not items:
        print(C_WARN + " [警告] 文件中没有有效号码。" + C_RST); return

    print()
    print(C_DIM + " 共读取 %d 条，开始查询..." % len(items) + C_RST)
    print()

    results = []
    ok_cnt = 0
    for raw in items:
        digits = re.sub(r"\D", "", raw)
        ok, msg = phone_validate(digits)
        if not ok:
            results.append({"raw": raw, "ok": False, "region": "格式错误: " + msg,
                            "type": "", "zip": "", "area": ""})
            continue
        info = db.lookup(digits)
        if not info:
            results.append({"raw": raw, "ok": False, "region": "号段 %s 不在库中" % digits[:7],
                            "type": "", "zip": "", "area": ""})
            continue
        ok_cnt += 1
        region = info["province"] + ("" if info["city"] in ("", info["province"]) else " " + info["city"])
        results.append({"raw": raw, "ok": True, "region": region, "type": info["type"],
                        "zip": info["zip"], "area": info["area"]})

    show_all = len(results) <= 200
    if not show_all:
        print(C_WARN + " [提示] 共 %d 条，屏幕仅显示失败项，完整结果请保存报告。" % len(results) + C_RST)
        print()
    for r in results:
        if r["ok"] and not show_all:
            continue
        if r["ok"]:
            print(" " + C_OK + "%-13s %s | %s | 邮编%s 区号%s" % (
                r["raw"], r["region"], r["type"], r["zip"], r["area"] or "-") + C_RST)
        else:
            print(" " + C_ERR + "%-13s %s" % (r["raw"], r["region"]) + C_RST)

    print()
    line()
    print(" 合计: %d 条    查到: %s%d%s    失败: %s%d%s" % (
        len(results), C_OK, ok_cnt, C_RST, C_ERR, len(results) - ok_cnt, C_RST))
    line()
    print()

    try:
        ans = ask_input(C_KEY + " 保存报告到文件吗? (y/n) > " + C_RST).lower()
    except BackToPrev:
        return
    if ans in ("y", "yes", "是"):
        default_out = os.path.join(HOME, "phone_report.csv")
        try:
            outp = ask_input(C_KEY + " 报告路径 [回车默认 %s] > " % default_out + C_RST)
        except BackToPrev:
            return
        outp = os.path.expanduser(outp) if outp else default_out
        with open(outp, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["号码", "状态", "归属地", "运营商", "邮编", "区号"])
            for r in results:
                w.writerow([r["raw"], "查到" if r["ok"] else "失败",
                            r["region"], r["type"], r["zip"], r["area"]])
        print(C_OK + " [OK] 已写入报告到 %s" % outp + C_RST)

def run_phone_seg_lookup():
    """按地区反查号段"""
    db = PhoneDB()
    line()
    print(C_TITLE + "[手机号] 号段反查(按地区)" + C_RST)
    line()
    if not db.path:
        print(C_ERR + " [错误] 未找到 phone.dat 号段库。" + C_RST)
        return
    print(" 输入地区关键字(省/市)，列出该地区所有号段。")
    print(C_DIM + " 例: 北京 / 唐山 / 深圳" + C_RST)
    print(C_DIM + " 输入空行 或 q 返回上一级。" + C_RST)
    print()
    while True:
        try:
            kw = ask_input(C_KEY + " 请输入地区关键字 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        if not kw or kw.lower() in ("q", "quit"):
            return
        print()
        print(C_DIM + " 正在检索全库(%d 条)，请稍候..." % db.count + C_RST)
        hits = db.search_region(kw)
        if not hits:
            print(C_WARN + " [警告] 没有匹配 '%s' 的号段。" % kw + C_RST)
            print()
            continue

        groups = {}
        for p7, info in hits:
            key = (info["province"], info["city"], info["type"])
            groups.setdefault(key, []).append(p7)

        print()
        print(" 匹配到 %d 个号段，%d 个归属地：" % (len(hits), len(groups)))
        print()
        for k in sorted(groups):
            prov, city, typ = k
            name = prov + ("" if city in ("", prov) else " " + city)
            segs = sorted(groups[k])
            print(" " + C_KEY + "%s %s" % (name, typ) + C_RST + "  (%d 个号段)" % len(segs))
            for i in range(0, len(segs), 10):
                print("   " + " ".join(segs[i:i + 10]))
            print()

        try:
            ans = ask_input(C_KEY + " 保存结果到文件吗? (y/n) > " + C_RST).lower()
        except BackToPrev:
            return
        if ans in ("y", "yes", "是"):
            default_out = os.path.join(HOME, "segments.txt")
            try:
                outp = ask_input(C_KEY + " 路径 [回车默认 %s] > " % default_out + C_RST)
            except BackToPrev:
                return
            outp = os.path.expanduser(outp) if outp else default_out
            with open(outp, "w", encoding="utf-8") as f:
                for k in sorted(groups):
                    prov, city, typ = k
                    name = prov + ("" if city in ("", prov) else " " + city)
                    for s7 in sorted(groups[k]):
                        f.write("%s %s %s\n" % (s7, name, typ))
            print(C_OK + " [OK] 已写入 %d 条到 %s" % (len(hits), outp) + C_RST)
        print()

def run_phone_format():
    """手机号格式化 / 脱敏 / 清洗"""
    line()
    print(C_TITLE + "[手机号] 格式化 / 脱敏" + C_RST)
    line()
    print(" 选择处理方式：")
    print("   " + C_KEY + "[1]" + C_RST + " 格式化    138 0013 8000")
    print("   " + C_KEY + "[2]" + C_RST + " 脱敏      138****8000")
    print("   " + C_KEY + "[3]" + C_RST + " 清洗      13800138000")
    print("   " + C_KEY + "[4]" + C_RST + " 加国际码  +86 138 0013 8000")
    print()
    while True:
        try:
            mode = ask_input(C_KEY + " 请输入序号 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        if mode in ("1", "2", "3", "4"):
            break
        if mode.lower() in ("q", "quit", "0"):
            return
        print(C_ERR + " [错误] 请输入 1 / 2 / 3 / 4。" + C_RST)

    line()
    print(" 输入一个或多个号码(空格/逗号分隔)，空行 或 q 结束。")
    print()
    while True:
        try:
            raw = ask_input(C_KEY + " 号码 > " + C_RST)
        except BackToPrev:
            return
        if not raw or raw.lower() in ("q", "quit"):
            return
        items = [x for x in re.split(r"[\s,，、;；]+", raw) if x]
        print()
        for it in items:
            digits = re.sub(r"\D", "", it)
            d = digits[2:] if (len(digits) == 13 and digits.startswith("86")) else digits
            if len(d) != 11:
                print(" " + C_ERR + "%-16s [错误] 需要 11 位数字" % it + C_RST)
                continue
            if mode == "1":
                out = "%s %s %s" % (d[:3], d[3:7], d[7:])
            elif mode == "2":
                out = d[:3] + "****" + d[7:]
            elif mode == "3":
                out = d
            else:
                out = "+86 %s %s %s" % (d[:3], d[3:7], d[7:])
            print(" %-16s -> %s" % (it, C_KEY + out + C_RST))
        print()

def run_phone_menu():
    while True:
        line()
        print(C_TITLE + "[手机号] 请选择功能" + C_RST)
        line()
        print("   " + C_KEY + "[1]" + C_RST + " 查询归属地")
        print("   " + C_KEY + "[2]" + C_RST + " 前三后二穷举手机号")
        print("   " + C_KEY + "[3]" + C_RST + " 批量归属地查询(从文件)")
        print("   " + C_KEY + "[4]" + C_RST + " 号段反查(按地区)")
        print("   " + C_KEY + "[5]" + C_RST + " 格式化 / 脱敏")
        print("   " + C_KEY + "[0]" + C_RST + " 返回主菜单")
        print()
        try:
            ans = ask_input(C_KEY + " 请输入序号 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        if ans == "1":
            run_phone_lookup()
        elif ans == "2":
            run_phone_brute()
        elif ans == "3":
            run_phone_batch()
        elif ans == "4":
            run_phone_seg_lookup()
        elif ans == "5":
            run_phone_format()
        elif ans in ("0", "q", "quit"):
            return
        else:
            print(C_ERR + " [错误] 请输入 1 / 2 / 3 / 4 / 5 / 0。" + C_RST)


# ================================================================ 主菜单
