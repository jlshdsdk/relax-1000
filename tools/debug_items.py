# -*- coding: utf-8 -*-
"""调试：题目/解析解析异常的原始数据"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
DATA = r"D:\Users\王奕博\Desktop\relax1000题\data"

with open(DATA + r"\qbook_raw.json", encoding="utf-8") as f:
    qbook = json.load(f)
with open(DATA + r"\abook_raw.json", encoding="utf-8") as f:
    abook = json.load(f)

def find(book, part, tag, num):
    counters = {}
    for ch in book:
        k = ch["part"]
        counters[k] = counters.get(k, 0) + 1
        if counters[k] == tag:
            for it in ch["items"]:
                if it["num"] == num:
                    return ch, it
    return None, None

def dump_item(book, part, tag, num, kind, fields):
    ch, it = find(book, part, tag, num)
    if it is None:
        print(f"!!! p{part}c{tag}{kind}{num} 未找到")
        return
    print(f"===== p{part}c{tag}{kind}{num} ({ch['no']}{ch['title']}) =====")
    for fld in fields:
        entries = it.get(fld, [])
        if fld == "opts":
            for letter, ents in sorted(entries.items()):
                print(f"-- opt {letter} --")
                for ln, t in ents:
                    print(f"  p{ln['page']} y{ln['y']}: {t!r}")
            continue
        print(f"-- {fld} --")
        for ln, t in entries:
            spans_desc = "|".join(f"{s['t']!r}@{s['size']}" for s in ln["spans"][:6])
            print(f"  p{ln['page']} y{ln['y']}: {t!r}   [{spans_desc[:120]}]")

# 选项只剩A的
dump_item(qbook, 2, 2, 84, "q", ["stem", "opts"])
dump_item(qbook, 2, 5, 19, "q", ["stem", "opts"])
dump_item(qbook, 4, 5, 16, "q", ["stem", "opts"])
# 题干模式未命中的
dump_item(qbook, 2, 2, 44, "q", ["stem"])
dump_item(qbook, 2, 2, 85, "q", ["stem"])
dump_item(qbook, 3, 4, 61, "q", ["stem"])
# DS 第6章图 q3 / q18（勘误目标）
dump_item(qbook, 1, 5, 3, "q", ["stem"])
dump_item(qbook, 1, 5, 18, "q", ["opts"])
# 解析 p2c3s56（轮次）
dump_item(abook, 2, 3, 56, "s", ["body"])
