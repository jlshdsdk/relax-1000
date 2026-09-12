# -*- coding: utf-8 -*-
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
DATA = r"D:\Users\王奕博\Desktop\relax1000题\data"
with open(DATA + r"\qbook_raw.json", encoding="utf-8") as f:
    qbook = json.load(f)

def find(book, part, tag, num):
    counters = {}
    for ch in book:
        if ch["part"] != part:
            continue
        counters[ch["part"]] = counters.get(ch["part"], 0) + 1
        if counters[ch["part"]] == tag:
            for it in ch["items"]:
                if it["num"] == num:
                    return it
    return None

def dump(part, tag, num):
    it = find(qbook, part, tag, num)
    if it is None:
        print(f"p{part}c{tag}q{num} NOT FOUND")
        return
    print(f"===== p{part}c{tag}q{num} =====")
    print("-- stem --")
    for ln, t in it["stem"]:
        print(f"  p{ln['page']}: {t!r}")
    for k in sorted(it["opts"]):
        print(f"-- opt {k} --")
        for ln, t in it["opts"][k]:
            print(f"  p{ln['page']}: {t!r}")

dump(1, 1, 9)
dump(1, 1, 13)
dump(1, 2, 12)
dump(1, 4, 60)
dump(2, 1, 35)
dump(2, 2, 45)
dump(2, 3, 20)
