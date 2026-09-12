# -*- coding: utf-8 -*-
"""诊断网格选项 bug：p1c1q1 在 raw json 和 site.json 中的形态"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
DATA = r"D:\Users\王奕博\Desktop\relax1000题\data"

qbook = json.load(open(DATA + r"\qbook_raw.json", encoding="utf-8"))
site = json.load(open(DATA + r"\site.json", encoding="utf-8"))

# raw
ch = qbook[0]
q1 = ch["items"][0]
print("== RAW qbook p1c1 q1 ==")
print("stem:")
for ln, t in q1["stem"]:
    print(f"  {t!r}")
for L in sorted(q1["opts"]):
    print(f"opt {L}:")
    for ln, t in q1["opts"][L]:
        print(f"  {t!r}")

# site
sch = site["chapters"][0]
sq1 = sch["questions"][0]
print("== SITE json p1c1 q1 ==")
for L in "ABCD":
    if L in sq1["opts"]:
        print(f"opt {L}: {sq1['opts'][L]['text']!r}")
