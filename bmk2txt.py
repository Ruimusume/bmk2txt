#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BMK -> TXT 指针解析（最终适配版）
规律：
  [3字节前缀][级数 uint64][N×偏移 uint64][main uint64][0x00 填充...]
  填充后第一个非0字节 = 下一条的级数起点。
"""

import os
import struct
import sys
import glob

MAGIC = b'\x45\x44\x5A\x4E'   # EDZN
MAX_DEPTH = 20
MIN_MAIN = 0x400000
MAX_MAIN = 0x7FFFFFFFFFFF


def u64(buf, off):
    if off < 0 or off + 8 > len(buf):
        return None
    return struct.unpack_from('<Q', buf, off)[0]


def find_first_entry(data):
    """滑动找第一个级数字段位置。"""
    L = len(data)
    pos = 4
    while pos + 8 <= L:
        n = u64(data, pos)
        if n is not None and 1 <= n <= MAX_DEPTH:
            offs = []
            ok = True
            for i in range(n):
                v = u64(data, pos + 8 + 8 * i)
                if v is None:
                    ok = False
                    break
                offs.append(v)
            if ok:
                main = u64(data, pos + 8 + 8 * n)
                if main is not None and MIN_MAIN <= main <= MAX_MAIN:
                    return pos
        pos += 1
    return None


def parse_entries(data):
    entries = []
    L = len(data)
    pos = find_first_entry(data)
    if pos is None:
        return entries

    while pos + 8 <= L:
        n = u64(data, pos)
        if n is None or not (1 <= n <= MAX_DEPTH):
            break

        offs = []
        ok = True
        for i in range(n):
            v = u64(data, pos + 8 + 8 * i)
            if v is None:
                ok = False
                break
            offs.append(v)
        if not ok:
            break

        main_off = pos + 8 + 8 * n
        main = u64(data, main_off)
        if main is None or not (MIN_MAIN <= main <= MAX_MAIN):
            break

        entries.append((n, offs, main))
        pos = main_off + 8

        while pos < L and data[pos] == 0:
            pos += 1

    return entries


def fmt(n, offs, main):
    s = "main+%X" % main
    for ofs in reversed(offs):
        s = "[%s]+%X" % (s, ofs)
    return s


def convert(bmk_path):
    with open(bmk_path, 'rb') as f:
        data = f.read()
    if len(data) < 8 or data[:4] != MAGIC:
        raise ValueError("非 BMK 文件（magic 不匹配）")

    entries = parse_entries(data)
    if not entries:
        print("[!] %s 未解析到指针" % bmk_path)
        return None

    lines = [fmt(n, offs, main) for n, offs, main in entries]

    out = os.path.splitext(bmk_path)[0] + ".txt"
    with open(out, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    print("[OK] %s -> %s  (%d 条)" % (bmk_path, out, len(entries)))
    return out


def main():
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(base)
    files = sorted(glob.glob("*.bmk")) + sorted(glob.glob("*.BMK"))
    seen = set()
    files = [p for p in files if not (p in seen or seen.add(p))]
    if not files:
        print("当前目录无 .bmk 文件")
        input("回车退出...")
        return
    ok = 0
    for p in files:
        try:
            if convert(p):
                ok += 1
        except Exception as e:
            print("[X] %s: %s" % (p, e))
    print("完成 %d/%d" % (ok, len(files)))
    input("回车退出...")


if __name__ == "__main__":
    main()