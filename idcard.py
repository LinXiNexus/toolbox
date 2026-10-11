#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""身份证交互功能"""

import sys
import os
import re
import datetime
import csv

from common import (line, ask, ask_input, show_list, BackToPrev, HOME,
                    C_TITLE, C_KEY, C_OK, C_ERR, C_WARN, C_DIM, C_RST)
from lunar import SHENGXIAO, XINGZUO, shengxiao_of, xingzuo_of, age_of
from idbase import (PROVINCES, check_digit, load_region_table, validate_date,
                    validate_prefix, brute_force, expand, normalize_id, id_check_all)

def id_ask_prefix(region_codes):
    line()
    print(C_TITLE + "[身份证] 输入可见的前 14 位数字" + C_RST)
    line()
    print(" 身份证共 18 位：")
    print(C_DIM + "   1-6   7-14      15-17     18" + C_RST)
    print(C_DIM + "   地址码 出生日期   顺序码   校验码" + C_RST)
    print("   +--- 这 14 位请照着证件输入 ---+" + C_DIM + "  ^这4位是本工具要算的" + C_RST)
    print()
    print(C_KEY + " 例: 11010119900307" + C_RST + "   (北京/1990年3月7日生)")
    print(C_DIM + " 若有认不清的位，用 ? 代替，例: 1101011990?307" + C_RST)
    if region_codes:
        print(C_OK + " 已加载完整地区码表 (%d 条)，将做 6 位精确校验。" % len(region_codes) + C_RST)
    else:
        print(C_DIM + " 未找到 regions.txt，地区码仅做省级(前2位)校验。" + C_RST)
    print()
    while True:
        raw = ask_input(C_KEY + " 请输入前14位 (exit 返回) > " + C_RST).replace(" ", "").replace("-", "")
        if not raw:
            print(C_ERR + " [错误] 不能为空。" + C_RST); continue
        if set(raw) - set("0123456789?"):
            print(C_ERR + " [错误] 只能包含数字和 ?。" + C_RST); continue
        if len(raw) != 14:
            print(C_ERR + " [错误] 需要 14 位，你输入了 %d 位。" % len(raw) + C_RST); continue
        ok, errs, infos = validate_prefix(raw, region_codes)
        if "?" in raw:
            print(C_OK + " [OK] 已记录，含 %d 个模糊位。" % raw.count("?") + C_RST)
        if errs:
            print(C_WARN + " [警告] 校验发现 %d 处问题：" % len(errs) + C_RST)
            for e in errs:
                print(C_WARN + "   - " + e + C_RST)
            if ask_input(C_KEY + " 仍要继续吗? (y=继续 / 其他=重输 / exit 返回) > " + C_RST).lower() not in ("y", "yes", "是"):
                continue
        else:
            for i in infos:
                print(C_OK + "   - " + i + C_RST)
            print(C_OK + " [OK] 校验通过。" + C_RST)
        return raw

def id_ask_gender():
    line()
    print(C_TITLE + "[身份证] 选择性别" + C_RST)
    line()
    print(" 性别由第 17 位决定：奇数 -> 男    偶数 -> 女")
    print()
    while True:
        ans = ask_input(C_KEY + " 请输入 男/女 (也可 m/f, exit 返回) > " + C_RST).lower()
        if ans in ("男", "m", "male", "1"):
            print(C_OK + " [OK] 已记录: 男" + C_RST); return "男"
        if ans in ("女", "f", "female", "0"):
            print(C_OK + " [OK] 已记录: 女" + C_RST); return "女"
        print(C_ERR + " [错误] 请输入 男 或 女。" + C_RST)

def id_ask_output():
    line()
    print(C_TITLE + "[身份证] 是否保存结果到文件" + C_RST)
    line()
    while True:
        ans = ask_input(C_KEY + " 保存到文件吗? (y/n, exit 返回) > " + C_RST).lower()
        if ans in ("y", "yes", "是", ""):
            default = os.path.join(HOME, "id_result.txt")
            path = ask_input(C_KEY + " 路径 [回车默认 %s, exit 返回] > " % default + C_RST)
            path = os.path.expanduser(path) if path else default
            print(C_OK + " [OK] 将保存到: %s" % path + C_RST)
            return path
        if ans in ("n", "no", "否"):
            print(C_OK + " [OK] 仅屏幕显示。" + C_RST); return None
        print(C_ERR + " [错误] 请输入 y 或 n。" + C_RST)

def id_show_results(results, save_path):
    show_list(results, save_path, "穷举完成")

def run_id_tool():
    region_codes, _ = load_region_table()
    prefix = gender = save_path = None
    step = 0
    while step < 3:
        try:
            if step == 0:
                prefix = id_ask_prefix(region_codes); step = 1
            elif step == 1:
                gender = id_ask_gender(); step = 2
            else:
                save_path = id_ask_output(); step = 3
        except BackToPrev:
            step -= 1
            if step < 0:
                return
            print(C_WARN + " [返回] 已回到上一步。" + C_RST)

    prefixes = expand(prefix)
    if len(prefixes) > 1:
        line()
        print(C_DIM + " ? 占位展开为 %d 种组合，正在过滤非法日期/地区..." % len(prefixes) + C_RST)
        kept = [p for p in prefixes if validate_prefix(p, region_codes)[0]]
        if len(prefixes) - len(kept):
            print(C_WARN + " [警告] 已过滤掉 %d 种非法组合。" % (len(prefixes) - len(kept)) + C_RST)
        if not kept:
            print(C_ERR + " [错误] 所有组合均不合法，无候选。" + C_RST); return
        prefixes = kept

    results = []
    for p in prefixes:
        results.extend(brute_force(p, gender))
    id_show_results(results, save_path)
    line()
    print(C_DIM + " 提示: 结果仅保证格式与校验位合法，不代表号码真实存在。" + C_RST)
    print(C_DIM + " 请仅用于本人证件或已获授权的合法用途。" + C_RST)


# ================================================================ 模块2: 手机号

PHONE_TYPES = {1: "移动", 2: "联通", 3: "电信", 4: "电信虚拟运营商",
               5: "联通虚拟运营商", 6: "移动虚拟运营商", 7: "广电", 8: "广电虚拟运营商"}

def run_id_check():
    """输入前 17 位, 算出第 18 位校验码"""
    region_codes, _ = load_region_table()
    line()
    print(C_TITLE + "[身份证] 17 位补校验位" + C_RST)
    line()
    print(" 输入前 17 位，自动算出第 18 位校验码。")
    print(C_DIM + "   1-6   7-14      15-17   18" + C_RST)
    print(C_DIM + "   地址码 出生日期   顺序码  校验码(自动)" + C_RST)
    print()
    print(C_KEY + " 例: 11010119900307001" + C_RST)
    print(C_DIM + " 输入空行 或 q 返回上一级。" + C_RST)
    print()
    while True:
        try:
            raw = ask_input(C_KEY + " 请输入前17位 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        raw = re.sub(r"[\s\-]", "", raw)
        if not raw or raw.lower() in ("q", "quit"):
            return
        if not raw.isdigit():
            print(C_ERR + " [错误] 只能包含数字。" + C_RST); continue
        if len(raw) != 17:
            print(C_ERR + " [错误] 需要 17 位，你输入了 %d 位。" % len(raw) + C_RST); continue

        ok, errs, infos = validate_prefix(raw[:14], region_codes)
        print()
        for i in infos:
            print(C_OK + "   - " + i + C_RST)
        for e in errs:
            print(C_WARN + " [警告] " + e + C_RST)

        cd = check_digit(raw)
        gender = "男" if int(raw[16]) % 2 else "女"
        print(" 前17位: " + raw)
        print(" 校验位: " + C_KEY + cd + C_RST)
        print(" 完整号: " + C_OK + raw + cd + C_RST)
        print(" 性别  : " + C_KEY + gender + C_RST)
        print()

def run_id_verify():
    """校验一个完整 18 位身份证号"""
    region_codes, _ = load_region_table()
    line()
    print(C_TITLE + "[身份证] 校验 18 位号码" + C_RST)
    line()
    print(" 输入完整 18 位，逐项校验：省级码 / 地区码 / 出生日期 / 校验位。")
    print(C_DIM + "   1-6   7-14      15-17   18" + C_RST)
    print(C_DIM + "   地址码 出生日期   顺序码  校验码" + C_RST)
    print()
    print(C_KEY + " 例: 11010519491231002X" + C_RST)
    print(C_DIM + " 输入空行 或 q 返回上一级。" + C_RST)
    print()
    while True:
        try:
            raw = ask_input(C_KEY + " 请输入18位号码 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        raw = re.sub(r"[\s\-]", "", raw).upper()
        if not raw or raw.lower() in ("q", "quit"):
            return
        if len(raw) != 18:
            print(C_ERR + " [错误] 需要 18 位，你输入了 %d 位。" % len(raw) + C_RST); continue
        if not re.fullmatch(r"\d{17}[\dX]", raw):
            print(C_ERR + " [错误] 前 17 位必须是数字，第 18 位为数字或 X。" + C_RST); continue

        all_ok, checks, gender = id_check_all(raw, region_codes)
        print()
        for name, st, detail in checks:
            if st is True:
                mark, color = "[通过]", C_OK
            elif st is False:
                mark, color = "[不通过]", C_ERR
                all_ok = False
            else:
                mark, color = "[跳过]", C_DIM
            print(" " + color + mark + " " + name + ": " + detail + C_RST)
        print()
        print(" 性别(参考): " + C_KEY + gender + C_RST)
        print()
        if all_ok:
            print(C_OK + " 结论: 通过全部校验，格式合法。" + C_RST)
        else:
            print(C_ERR + " 结论: 未通过校验，不是合法的身份证号。" + C_RST)
        print()
        print(C_DIM + " 注: 仅校验格式合法性，不代表该号码真实存在。" + C_RST)
        print()

def run_id_batch():
    """从文本文件批量校验身份证号"""
    region_codes, _ = load_region_table()
    line()
    print(C_TITLE + "[身份证] 批量校验(从文件)" + C_RST)
    line()
    print(" 从文本文件读取号码，每行一个，逐行校验。")
    print(C_DIM + " 空行、以 # 开头的行会被跳过。" + C_RST)
    print()
    default = os.path.join(HOME, "ids.txt")
    print(C_DIM + " 文件不存在时，可先执行:" + C_RST)
    print(C_DIM + "   printf '11010519491231002X\\n110105194912310021\\n' > ~/ids.txt" + C_RST)
    print()
    while True:
        try:
            path = ask_input(C_KEY + " 文件路径 [回车默认 %s, exit 返回] > " % default + C_RST)
        except BackToPrev:
            return
        path = os.path.expanduser(path) if path else default
        if not os.path.isfile(path):
            print(C_ERR + " [错误] 文件不存在: %s" % path + C_RST)
            continue
        break

    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError as e:
        print(C_ERR + " [错误] 读取失败: %s" % e + C_RST)
        return

    items = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    if not items:
        print(C_WARN + " [警告] 文件中没有有效号码。" + C_RST)
        return

    print()
    print(C_DIM + " 共读取 %d 条，开始校验..." % len(items) + C_RST)
    print()

    results = []
    ok_cnt = 0
    for raw in items:
        norm, err = normalize_id(raw)
        if err:
            results.append((raw, False, "格式错误: " + err))
            continue
        all_ok, checks, gender = id_check_all(norm, region_codes)
        if all_ok:
            ok_cnt += 1
            results.append((raw, True, "合法 (%s)" % gender))
        else:
            reason = "；".join("%s %s" % (n, d) for n, st, d in checks if st is False)
            results.append((raw, False, reason))

    show_all = len(results) <= 200
    if not show_all:
        print(C_WARN + " [提示] 共 %d 条，屏幕仅显示不合法项，完整结果请保存报告。" % len(results) + C_RST)
        print()
    for raw, ok, msg in results:
        if ok and not show_all:
            continue
        if ok:
            print(" " + C_OK + "[合法] " + raw + C_RST)
        else:
            print(" " + C_ERR + "[不合法] " + raw + C_RST)
            print("        " + C_DIM + msg + C_RST)

    print()
    line()
    print(" 合计: %d 条    合法: %s%d%s    不合法: %s%d%s" % (
        len(results), C_OK, ok_cnt, C_RST, C_ERR, len(results) - ok_cnt, C_RST))
    line()
    print()

    try:
        ans = ask_input(C_KEY + " 保存报告到文件吗? (y/n) > " + C_RST).lower()
    except BackToPrev:
        return
    if ans in ("y", "yes", "是"):
        default_out = os.path.join(HOME, "id_report.csv")
        try:
            outp = ask_input(C_KEY + " 报告路径 [回车默认 %s] > " % default_out + C_RST)
        except BackToPrev:
            return
        outp = os.path.expanduser(outp) if outp else default_out
        with open(outp, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["号码", "结果", "说明"])
            for raw, ok, msg in results:
                w.writerow([raw, "合法" if ok else "不合法", msg])
        print(C_OK + " [OK] 已写入报告到 %s" % outp + C_RST)

def run_id_info():
    """从 18 位号码提取信息: 地区 / 生日 / 年龄 / 生肖 / 星座 / 性别"""
    region_codes, _ = load_region_table()
    line()
    print(C_TITLE + "[身份证] 信息提取" + C_RST)
    line()
    print(" 输入 18 位号码，输出地区 / 生日 / 年龄 / 生肖 / 星座 / 性别。")
    print(C_DIM + " 输入空行 或 q 返回上一级。" + C_RST)
    print()
    while True:
        try:
            raw = ask_input(C_KEY + " 请输入18位号码 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        if not raw or raw.lower() in ("q", "quit"):
            return
        norm, err = normalize_id(raw)
        if err:
            print(C_ERR + " [错误] " + err + "。" + C_RST); continue

        y, mo, d = int(norm[6:10]), int(norm[10:12]), int(norm[12:14])
        ok, msg = validate_date(norm[6:14])
        prov = norm[:2]
        region = region_codes.get(norm[:6], "") if region_codes else ""
        gender = "男" if int(norm[16]) % 2 else "女"

        print()
        print(" 号码  : " + C_KEY + norm + C_RST)
        print(" 省级  : " + PROVINCES.get(prov, "未知") + " (" + prov + ")")
        if region:
            print(" 地区  : " + region + " (" + norm[:6] + ")")
        elif region_codes:
            print(" 地区  : " + C_WARN + "不在行政区划表中" + C_RST)
        print(" 出生  : %04d-%02d-%02d" % (y, mo, d))
        if ok:
            age = age_of(y, mo, d)
            print(" 年龄  : " + (("%d 周岁" % age) if age is not None else "-"))
            print(" 生肖  : " + (shengxiao_of(y, mo, d) or "-"))
            print(" 星座  : " + xingzuo_of(mo, d))
        else:
            print(C_WARN + " [警告] " + msg + "，年龄/生肖/星座无法计算。" + C_RST)
        print(" 性别  : " + gender)
        print()

def derive_birthdays(sx=None, xz=None, age_lo=None, age_hi=None):
    """按生肖/星座/年龄反推所有可能的出生日期, 返回 [(y,m,d), ...]"""
    today = datetime.date.today()
    if age_lo is None and age_hi is None:
        y_lo, y_hi = 1900, today.year
    else:
        a_lo = age_lo if age_lo is not None else 0
        a_hi = age_hi if age_hi is not None else 150
        y_lo = today.year - a_hi - 1
        y_hi = today.year - a_lo
    y_lo = max(y_lo, 1900)
    y_hi = min(y_hi, today.year)
    out = []
    for y in range(y_lo, y_hi + 1):
        for m in range(1, 13):
            for d in range(1, 32):
                try:
                    dt = datetime.date(y, m, d)
                except ValueError:
                    continue
                if dt > today:
                    continue
                if sx and shengxiao_of(y, m, d) != sx:
                    continue
                if xz and xingzuo_of(m, d) != xz:
                    continue
                if age_lo is not None or age_hi is not None:
                    a = age_of(y, m, d)
                    if a is None:
                        continue
                    if age_lo is not None and a < age_lo:
                        continue
                    if age_hi is not None and a > age_hi:
                        continue
                out.append((y, m, d))
    return out

def ask_shengxiao():
    line()
    print(C_TITLE + "[反推] 第 1 步: 生肖 (可留空跳过)" + C_RST)
    line()
    print(" 可选: " + " ".join(SHENGXIAO))
    print()
    while True:
        x = ask_input(C_KEY + " 生肖 (回车跳过, exit 返回) > " + C_RST).replace("年", "").strip()
        if not x:
            print(C_OK + " [OK] 不限生肖。" + C_RST)
            return None
        if x in SHENGXIAO:
            print(C_OK + " [OK] 生肖: %s" % x + C_RST)
            return x
        print(C_ERR + " [错误] 可选: " + " ".join(SHENGXIAO) + C_RST)

def ask_xingzuo():
    names = [nm for _, _, nm in XINGZUO]
    line()
    print(C_TITLE + "[反推] 第 2 步: 星座 (可留空跳过)" + C_RST)
    line()
    print(" 可选: " + " ".join(names))
    print()
    while True:
        x = ask_input(C_KEY + " 星座 (回车跳过, exit 返回) > " + C_RST).replace("座", "").strip()
        if not x:
            print(C_OK + " [OK] 不限星座。" + C_RST)
            return None
        if x in names:
            print(C_OK + " [OK] 星座: %s" % x + C_RST)
            return x
        print(C_ERR + " [错误] 可选: " + " ".join(names) + C_RST)

def ask_age_range():
    line()
    print(C_TITLE + "[反推] 第 3 步: 年龄范围 (可留空跳过)" + C_RST)
    line()
    print(" 例: 30-40 (30到40岁) / 35 (正好35岁) / 30- (30岁以上)")
    print()
    while True:
        x = ask_input(C_KEY + " 年龄范围 (回车跳过, exit 返回) > " + C_RST).replace("岁", "").strip()
        if not x:
            print(C_OK + " [OK] 不限年龄。" + C_RST)
            return None, None
        m = re.fullmatch(r"(\d{1,3})\s*[-~至到]\s*(\d{1,3})?", x)
        if m:
            lo = int(m.group(1))
            hi = int(m.group(2)) if m.group(2) else None
            if hi is not None and hi < lo:
                lo, hi = hi, lo
            print(C_OK + " [OK] 年龄: %s" % ("%d-%s" % (lo, hi if hi is not None else "以上")) + C_RST)
            return lo, hi
        if re.fullmatch(r"\d{1,3}", x):
            a = int(x)
            print(C_OK + " [OK] 年龄: %d" % a + C_RST)
            return a, a
        print(C_ERR + " [错误] 格式如 30-40 / 35 / 30-" + C_RST)

def ask_region6_optional():
    line()
    print(C_TITLE + "[反推] 第 4 步: 地区码前 6 位 (可留空)" + C_RST)
    line()
    print(" 填了就继续生成完整号码；留空则只列出候选生日。")
    print(C_DIM + " 认不清的位可用 ? 占位, 例: 4403?5" + C_RST)
    print()
    while True:
        x = re.sub(r"[\s\-]", "", ask_input(C_KEY + " 地区码 (回车跳过, exit 返回) > " + C_RST))
        if not x:
            print(C_OK + " [OK] 只列生日，不生成号码。" + C_RST)
            return None
        if len(x) != 6:
            print(C_ERR + " [错误] 需要 6 位，当前 %d 位。" % len(x) + C_RST); continue
        if set(x) - set("0123456789?"):
            print(C_ERR + " [错误] 只能包含数字和 ?。" + C_RST); continue
        print(C_OK + " [OK] 地区码: %s" % x + C_RST)
        return x

def run_id_derive():
    """按生肖/星座/年龄反推生日, 并可生成候选身份证号"""
    line()
    print(C_TITLE + "[身份证] 按生肖/星座反推号码" + C_RST)
    line()
    print(" 用生肖(农历) / 星座 / 年龄 反推出生日期，再生成候选号码。")
    print(C_DIM + " 至少填一项筛选，否则候选日期会覆盖 1900 年至今。" + C_RST)
    print()

    sx = xz = None
    age_lo = age_hi = None
    region = None
    gender = None
    state = 0
    while state < 5:
        try:
            if state == 0:
                sx = ask_shengxiao(); state = 1
            elif state == 1:
                xz = ask_xingzuo(); state = 2
            elif state == 2:
                age_lo, age_hi = ask_age_range(); state = 3
            elif state == 3:
                region = ask_region6_optional()
                state = 5 if region is None else 4
            else:
                gender = id_ask_gender(); state = 5
        except BackToPrev:
            if state == 0:
                return
            state -= 1
            print(C_WARN + " [返回] 已回到上一步。" + C_RST)

    if sx is None and xz is None and age_lo is None:
        print(C_WARN + " [警告] 未设置任何筛选条件，候选生日将覆盖 1900 年至今。" + C_RST)

    print()
    print(C_DIM + " 正在反推..." + C_RST)
    birthdays = derive_birthdays(sx, xz, age_lo, age_hi)

    line()
    print(C_TITLE + "反推结果" + C_RST)
    line()
    print(" 生肖  : " + (sx or "不限"))
    print(" 星座  : " + (xz or "不限"))
    print(" 年龄  : " + (("%d-%s" % (age_lo, age_hi if age_hi is not None else "以上"))
                      if age_lo is not None else "不限"))
    print(" 候选生日: " + C_KEY + ("%d" % len(birthdays)) + C_RST)
    print()
    if not birthdays:
        print(C_ERR + " [错误] 没有符合条件的生日。" + C_RST)
        return

    if region is None:
        show_list(["%04d%02d%02d" % b for b in birthdays], None, "候选生日")
        return

    total = len(birthdays) * 500 * (10 ** region.count("?"))
    print(" 地区码: " + region + "    性别: " + gender)
    print(" 号码总数: " + C_KEY + ("%d" % total) + C_RST)
    print()
    if total > 5000000:
        print(C_ERR + " [错误] 号码总数过大，请增加筛选条件(生肖/星座/年龄)或减少 ? 占位。" + C_RST)
        return

    if total > 20000:
        print(C_WARN + " [提示] 数量较大，将直接写入文件（逐条生成，不占内存）。" + C_RST)
        default = os.path.join(HOME, "id_derive.txt")
        path = ask_input(C_KEY + " 保存路径 [回车默认 %s, exit 返回] > " % default + C_RST)
        path = os.path.expanduser(path) if path else default
        n = 0
        with open(path, "w", encoding="utf-8") as f:
            for (y, m, d) in birthdays:
                for p14 in expand(region + "%04d%02d%02d" % (y, m, d)):
                    for num in brute_force(p14, gender):
                        f.write(num + "\n")
                        n += 1
        print(C_OK + " [OK] 已写入 %d 条到 %s" % (n, path) + C_RST)
        return

    save_path = None
    ans = ask_input(C_KEY + " 保存到文件吗? (y/n, exit 返回) > " + C_RST).lower()
    if ans in ("y", "yes", "是", ""):
        default = os.path.join(HOME, "id_derive.txt")
        pp = ask_input(C_KEY + " 路径 [回车默认 %s, exit 返回] > " % default + C_RST)
        save_path = os.path.expanduser(pp) if pp else default
    results = []
    for (y, m, d) in birthdays:
        for p14 in expand(region + "%04d%02d%02d" % (y, m, d)):
            results.extend(brute_force(p14, gender))
    show_list(results, save_path, "生成完成")

def run_id_menu():
    while True:
        line()
        print(C_TITLE + "[身份证] 请选择功能" + C_RST)
        line()
        print("   " + C_KEY + "[1]" + C_RST + " 后四位穷举")
        print("   " + C_KEY + "[2]" + C_RST + " 17位补校验位")
        print("   " + C_KEY + "[3]" + C_RST + " 校验18位号码")
        print("   " + C_KEY + "[4]" + C_RST + " 批量校验(从文件)")
        print("   " + C_KEY + "[5]" + C_RST + " 信息提取(年龄/生肖/星座)")
        print("   " + C_KEY + "[6]" + C_RST + " 按生肖/星座反推号码")
        print("   " + C_KEY + "[0]" + C_RST + " 返回主菜单")
        print()
        try:
            ans = ask_input(C_KEY + " 请输入序号 (exit 返回) > " + C_RST)
        except BackToPrev:
            return
        if ans == "1":
            run_id_tool()
        elif ans == "2":
            run_id_check()
        elif ans == "3":
            run_id_verify()
        elif ans == "4":
            run_id_batch()
        elif ans == "5":
            run_id_info()
        elif ans == "6":
            run_id_derive()
        elif ans in ("0", "q", "quit"):
            return
        else:
            print(C_ERR + " [错误] 请输入 1 / 2 / 3 / 4 / 5 / 6 / 0。" + C_RST)
