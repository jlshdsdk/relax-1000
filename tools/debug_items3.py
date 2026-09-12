# -*- coding: utf-8 -*-
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
DATA = r"D:\Users\王奕博\Desktop\relax1000题\data"
with open(DATA + r"\qbook_raw.json", encoding="utf-8") as f:
    qbook = json.load(f)

def find(part, tag, num):
    counters = {}
    for ch in qbook:
        counters.setdefault(ch["part"], 0)
        counters[ch["part"]] += 1
        if ch["part"] == part and counters[ch["part"]] == tag:
            for it in ch["items"]:
                if it["num"] == num:
                    return it
    return None

for part, tag, num in [(1, 6, 42), (2, 5, 14), (3, 2, 51), (4, 4, 62)]:
    it = find(part, tag, num)
    print(f"===== p{part}c{tag}q{num} =====")
    for ln, t in it["stem"][-6:]:
        print(f"  stem: {t!r}")
    for k in sorted(it["opts"]):
        for ln, t in it["opts"][k]:
            print(f"  opt {k}: {t!r}")
