#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""农历年表与生肖 / 星座 / 年龄计算 (数据源自 lunardate, GPLv2)"""

import datetime
import bisect

LUNAR_YEAR_INFOS = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0,
    0x09ad0, 0x055d2, 0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540,
    0x0d6a0, 0x0ada2, 0x095b0, 0x14977, 0x04970, 0x0a4b0, 0x0b4b5, 0x06a50,
    0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970, 0x06566, 0x0d4a0,
    0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2,
    0x0a950, 0x0b557, 0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573,
    0x052b0, 0x0a9a8, 0x0e950, 0x06aa0, 0x0aea6, 0x0ab50, 0x04b60, 0x0aae4,
    0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0, 0x096d0, 0x04dd5,
    0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b5a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46,
    0x0ab60, 0x09570, 0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58,
    0x05ac0, 0x0ab60, 0x096d5, 0x092e0, 0x0c960, 0x0d954, 0x0d4a0, 0x0da50,
    0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5, 0x0a950, 0x0b4a0,
    0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260,
    0x0ea65, 0x0d530, 0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0,
    0x1d0b6, 0x0d250, 0x0d520, 0x0dd45, 0x0b5a0, 0x056d0, 0x055b2, 0x049b0,
    0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0, 0x14b63, 0x09370,
    0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0,
    0x0a6d0, 0x055d4, 0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50,
    0x055a0, 0x0aba4, 0x0a5b0, 0x052b0, 0x0b273, 0x06930, 0x07337, 0x06aa0,
    0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160, 0x0e968, 0x0d520,
    0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
]

LUNAR_YEAR_DAYS = [
    384, 354, 355, 383, 354, 355, 384, 354, 355, 384, 354, 384, 354, 354, 384,
    354, 355, 384, 355, 384, 354, 354, 384, 354, 354, 385, 354, 355, 384, 354,
    383, 354, 355, 384, 355, 354, 384, 354, 384, 354, 354, 384, 355, 354, 385,
    354, 354, 384, 354, 384, 354, 355, 384, 354, 355, 384, 354, 383, 355, 354,
    384, 355, 354, 384, 355, 353, 384, 355, 384, 354, 355, 384, 354, 354, 384,
    354, 384, 354, 355, 384, 355, 354, 384, 354, 384, 354, 354, 384, 355, 355,
    384, 354, 354, 383, 355, 384, 354, 355, 384, 354, 354, 384, 354, 355, 384,
    354, 385, 354, 354, 384, 354, 354, 384, 355, 384, 354, 355, 384, 354, 354,
    384, 354, 355, 384, 354, 384, 354, 354, 384, 355, 354, 384, 355, 384, 354,
    354, 384, 354, 354, 384, 355, 355, 384, 354, 384, 354, 354, 384, 354, 355,
    384, 355, 384, 354, 354, 383, 355, 354, 384, 355, 354, 384, 354, 384, 354,
    355, 384, 354, 355, 384, 354, 384, 354, 354, 384, 355, 354, 384, 355, 354,
    384, 354, 384, 354, 355, 384, 354, 355, 383, 354, 384, 354, 355, 384, 355,
    354, 384, 354, 354, 384,
]

SHENGXIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
XINGZUO = [(1, 20, "水瓶"), (2, 19, "双鱼"), (3, 21, "白羊"), (4, 20, "金牛"),
           (5, 21, "双子"), (6, 22, "巨蟹"), (7, 23, "狮子"), (8, 23, "处女"),
           (9, 23, "天秤"), (10, 24, "天蝎"), (11, 23, "射手"), (12, 22, "摩羯")]


_LUNAR_CUM = []
_acc = 0
for _d in LUNAR_YEAR_DAYS:
    _LUNAR_CUM.append(_acc)
    _acc += _d


def lunar_year_of(y, m, d):
    """公历日期 -> 农历年份(以春节为界), 二分查找"""
    try:
        offset = (datetime.date(y, m, d) - datetime.date(1900, 1, 31)).days
    except ValueError:
        return None
    if offset < 0:
        return None
    idx = bisect.bisect_right(_LUNAR_CUM, offset) - 1
    if idx < 0 or idx >= len(LUNAR_YEAR_DAYS):
        return None
    return 1900 + idx

def shengxiao_of(y, m, d):
    ly = lunar_year_of(y, m, d)
    return None if ly is None else SHENGXIAO[(ly - 1900) % 12]

def xingzuo_of(m, d):
    if (m, d) < XINGZUO[0][:2]:
        return "摩羯"
    name = XINGZUO[0][2]
    for mm, dd, nm in XINGZUO:
        if (m, d) >= (mm, dd):
            name = nm
    return name

def age_of(y, m, d):
    """周岁"""
    today = datetime.date.today()
    try:
        b = datetime.date(y, m, d)
    except ValueError:
        return None
    if b > today:
        return None
    age = today.year - b.year
    if (today.month, today.day) < (b.month, b.day):
        age -= 1
    return age
