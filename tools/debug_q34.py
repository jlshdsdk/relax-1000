# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
DATA = r"D:\Users\王奕博\Desktop\relax1000题\data"
qbook = json.load(open(DATA + r"\qbook_raw.json", encoding="utf-8"))
site = json.load(open(DATA + r"\site.json", encoding="utf-8"))
figs = json.load(open(DATA + r"\figures_manifest.json", encoding="utf-8"))

# raw q34（part1 的第5个tag章 = 第6章图）
counters = {}
ch = None
for c in qbook:
    counters.setdefault(c["part"], 0)
    counters[c["part"]] += 1
    if c["part"] == 1 and counters[c["part"]] == 5:
        ch = c
        break
q34 = [it for it in ch["items"] if it["num"] == 34][0]
print("== RAW p1c5q34 ==")
for ln, t in q34["stem"]:
    print(f"  stem: {t!r}")
for L in sorted(q34["opts"]):
    for ln, t in q34["opts"][L]:
        print(f"  opt {L}: {t!r}")

# site q34
sch = [c for c in site["chapters"] if c["id"] == "p1c5"][0]
sq34 = [q for q in sch["questions"] if q["num"] == 34][0]
print("== SITE q34 ==")
print("stem_figs:", sq34["stem_figs"])
print("opt_figs:", sq34["opt_figs"])
for L in "ABCD":
    if L in sq34["opts"]:
        print(f"opt {L} text: {sq34['opts'][L]['text']!r}")

# manifest rect
for m in figs["q"]:
    if m["id"] == "p1c5q34":
        print("fig rect:", m["rect"], "page", m["page"])
