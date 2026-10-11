#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""身份证底层: 常量、校验算法、地区码表"""

import os
import re
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))

WEIGHTS = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
CHECK_CODES = "10X98765432"

PROVINCES = {
    "11": "北京", "12": "天津", "13": "河北", "14": "山西", "15": "内蒙古",
    "21": "辽宁", "22": "吉林", "23": "黑龙江",
    "31": "上海", "32": "江苏", "33": "浙江", "34": "安徽", "35": "福建",
    "36": "江西", "37": "山东",
    "41": "河南", "42": "湖北", "43": "湖南", "44": "广东", "45": "广西",
    "46": "海南",
    "50": "重庆", "51": "四川", "52": "贵州", "53": "云南", "54": "西藏",
    "61": "陕西", "62": "甘肃", "63": "青海", "64": "宁夏", "65": "新疆",
    "71": "台湾", "81": "香港", "82": "澳门", "91": "国外",
}


def check_digit(first17):
    s = sum(int(c) * w for c, w in zip(first17, WEIGHTS))
    return CHECK_CODES[s % 11]

def load_region_table():
    for p in [os.path.join(_HERE, "data", "regions.txt"),
              os.path.join(_HERE, "regions.txt"),
              os.path.expanduser("~/regions.txt")]:
        if os.path.isfile(p):
            codes = {}
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    for ln in f:
                        m = re.search(r"\d{6}", ln)
                        if m:
                            codes[m.group()] = ln[m.end():].strip() or ln.strip()
            except OSError:
                continue
            if codes:
                return codes, p
    return None, None

def validate_date(s):
    y, mo, d = int(s[:4]), int(s[4:6]), int(s[6:8])
    today = datetime.date.today()
    if not (1900 <= y <= today.year):
        return False, "出生年份 %d 超出合理范围 (1900-%d)" % (y, today.year)
    if not (1 <= mo <= 12):
        return False, "出生月份 %02d 非法 (应为 01-12)" % mo
    if not (1 <= d <= 31):
        return False, "出生日期 %02d 非法 (应为 01-31)" % d
    try:
        datetime.date(y, mo, d)
    except ValueError:
        return False, "出生日期 %04d-%02d-%02d 不存在(该月无此日)" % (y, mo, d)
    if datetime.date(y, mo, d) > today:
        return False, "出生日期 %04d-%02d-%02d 晚于今天" % (y, mo, d)
    return True, ""

def validate_prefix(p, region_codes):
    errs, infos = [], []
    if "?" not in p[:2]:
        if p[:2] not in PROVINCES:
            errs.append("省级码 %s 不存在" % p[:2])
        else:
            infos.append("省级: %s" % PROVINCES[p[:2]])
    if region_codes is not None and "?" not in p[:6]:
        if p[:6] not in region_codes:
            errs.append("地区码 %s 不在行政区划表中" % p[:6])
        else:
            infos.append("地区: %s" % region_codes[p[:6]])
    if "?" not in p[6:14]:
        ok, msg = validate_date(p[6:14])
        if not ok:
            errs.append(msg)
        else:
            infos.append("出生: %s-%s-%s" % (p[6:10], p[10:12], p[12:14]))
    return (len(errs) == 0), errs, infos

def brute_force(prefix14, gender):
    parity = (1, 3, 5, 7, 9) if gender == "男" else (0, 2, 4, 6, 8)
    out = []
    for d15 in "0123456789":
        for d16 in "0123456789":
            for d17 in parity:
                f17 = prefix14 + d15 + d16 + str(d17)
                out.append(f17 + check_digit(f17))
    return out

def expand(prefix):
    prefixes = [""]
    for ch in prefix:
        if ch == "?":
            prefixes = [p + d for p in prefixes for d in "0123456789"]
        else:
            prefixes = [p + ch for p in prefixes]
    return prefixes

def normalize_id(raw):
    """归一化并做格式检查, 返回 (norm, err)"""
    norm = re.sub(r"[\s\-]", "", raw).upper()
    if len(norm) != 18:
        return norm, "需要 18 位，实际 %d 位" % len(norm)
    if not re.fullmatch(r"\d{17}[\dX]", norm):
        return norm, "前 17 位必须是数字，第 18 位为数字或 X"
    return norm, ""

def id_check_all(raw, region_codes):
    """校验归一化后的 18 位号码, 返回 (all_ok, checks, gender)"""
    first17, last = raw[:17], raw[17]
    checks = []

    prov = raw[:2]
    if prov in PROVINCES:
        checks.append(("省级码", True, "%s %s" % (prov, PROVINCES[prov])))
    else:
        checks.append(("省级码", False, "%s 不存在" % prov))

    if region_codes:
        if raw[:6] in region_codes:
            checks.append(("地区码", True, "%s %s" % (raw[:6], region_codes[raw[:6]])))
        else:
            checks.append(("地区码", False, "%s 不在行政区划表中" % raw[:6]))
    else:
        checks.append(("地区码", None, "未加载 regions.txt，跳过"))

    ok, msg = validate_date(raw[6:14])
    if ok:
        checks.append(("出生日期", True, "%s-%s-%s" % (raw[6:10], raw[10:12], raw[12:14])))
    else:
        checks.append(("出生日期", False, msg))

    cd = check_digit(first17)
    if cd == last:
        checks.append(("校验位", True, "%s 正确" % last))
    else:
        checks.append(("校验位", False, "应为 %s，实际为 %s" % (cd, last)))

    gender = "男" if int(raw[16]) % 2 else "女"
    all_ok = all(c[1] is not False for c in checks)
    return all_ok, checks, gender
