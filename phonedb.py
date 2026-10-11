#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手机号号段库: phone.dat 解析与查询"""

import os
import re
import struct

import paths

_HERE = os.path.dirname(os.path.abspath(__file__))

PHONE_TYPES = {1: "移动", 2: "联通", 3: "电信", 4: "电信虚拟运营商",
               5: "联通虚拟运营商", 6: "移动虚拟运营商", 7: "广电", 8: "广电虚拟运营商"}


class PhoneDB:
    """解析 phone.dat (ls0f/phone 格式)"""

    def __init__(self, path=None):
        self.path = path or self._find()
        self.buf = None
        self.version = None
        self.first = None
        self.count = None
        if self.path:
            self._load()

    @staticmethod
    def _find():
        """定位号段库(支持源码运行与 zipapp 单文件运行)"""
        return paths.find_data("phone.dat")

    def _load(self):
        with open(self.path, "rb") as f:
            self.buf = f.read()
        self.version, self.first = struct.unpack("<4si", self.buf[:8])
        rec = struct.calcsize("<iiB")
        self.count = (len(self.buf) - self.first) // rec

    @property
    def version_str(self):
        try:
            v = self.version.decode("ascii", "ignore")
            if len(v) == 4 and v.isdigit():
                return "%s (%s年%s月)" % (v, "20" + v[:2], v[2:])
            return v
        except Exception:
            return "?"

    def lookup(self, number):
        """number: 7-11 位数字, 返回 dict 或 None"""
        digits = re.sub(r"\D", "", str(number))
        if len(digits) < 7:
            return None
        target = int(digits[:7])
        rec = struct.calcsize("<iiB")
        left, right = 0, self.count
        while left <= right:
            mid = (left + right) // 2
            off = self.first + mid * rec
            if off + rec > len(self.buf):
                return None
            cur, roff, ptype = struct.unpack("<iiB", self.buf[off:off + rec])
            if cur > target:
                right = mid - 1
            elif cur < target:
                left = mid + 1
            else:
                end = self.buf.find(b"\x00", roff)
                content = self.buf[roff:end].decode("utf-8", "ignore")
                parts = content.split("|")
                while len(parts) < 4:
                    parts.append("")
                return {
                    "prefix": digits[:7],
                    "province": parts[0],
                    "city": parts[1],
                    "zip": parts[2],
                    "area": parts[3].strip(),
                    "type": PHONE_TYPES.get(ptype, str(ptype)),
                }
        return None


    def prefixes_for(self, seg3):
        """返回所有以 seg3 开头的 7 位号段 -> info (二分定位 + 顺序扫描)"""
        rec = struct.calcsize("<iiB")
        target = int(seg3 + "0000")
        left, right = 0, self.count
        while left < right:
            mid = (left + right) // 2
            off = self.first + mid * rec
            cur, _, _ = struct.unpack("<iiB", self.buf[off:off + rec])
            if cur < target:
                left = mid + 1
            else:
                right = mid
        res = {}
        i = left
        while i < self.count:
            off = self.first + i * rec
            if off + rec > len(self.buf):
                break
            cur, roff, ptype = struct.unpack("<iiB", self.buf[off:off + rec])
            sfx = str(cur)
            if not sfx.startswith(seg3):
                break
            end = self.buf.find(b"\x00", roff)
            content = self.buf[roff:end].decode("utf-8", "ignore")
            parts = content.split("|")
            while len(parts) < 4:
                parts.append("")
            res[sfx] = {"province": parts[0], "city": parts[1], "zip": parts[2],
                        "area": parts[3].strip(), "type": PHONE_TYPES.get(ptype, str(ptype))}
            i += 1
        return res


    def search_region(self, keyword):
        """按关键字(省/市)检索号段, 返回 [(prefix7, info), ...]"""
        res = []
        rec = struct.calcsize("<iiB")
        for i in range(self.count):
            off = self.first + i * rec
            if off + rec > len(self.buf):
                break
            cur, roff, ptype = struct.unpack("<iiB", self.buf[off:off + rec])
            end = self.buf.find(b"\x00", roff)
            parts = self.buf[roff:end].decode("utf-8", "ignore").split("|")
            while len(parts) < 4:
                parts.append("")
            if keyword in parts[0] or keyword in parts[1]:
                res.append((str(cur), {"province": parts[0], "city": parts[1],
                                       "zip": parts[2], "area": parts[3].strip(),
                                       "type": PHONE_TYPES.get(ptype, str(ptype))}))
        return res

def phone_validate(digits):
    """返回 (ok, 错误信息)"""
    if not digits.isdigit():
        return False, "只能包含数字"
    if len(digits) not in (7, 8, 9, 10, 11):
        return False, "位数应为 7-11 位（前7位即可定归属地），当前 %d 位" % len(digits)
    if digits[0] != "1":
        return False, "手机号必须以 1 开头"
    if len(digits) >= 2 and digits[1] not in "3456789":
        return False, "第 2 位应为 3-9（当前 %s）" % digits[1]
    return True, ""
