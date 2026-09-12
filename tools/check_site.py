# -*- coding: utf-8 -*-
"""全站自检：死链、题量、唯一性、体积、图片存在性"""
import os, re, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")

fails = []
files = [f for f in os.listdir(SITE) if f.endswith(".html")]
href_re = re.compile(r'(?:href|src)="([^"#]+)"')

link_count = 0
for f in files:
    t = open(os.path.join(SITE, f), encoding="utf-8").read()
    for m in href_re.finditer(t):
        u = m.group(1)
        link_count += 1
        if u.startswith(("http:", "https:", "mailto:", "data:")):
            continue
        path = u.split("?")[0]
        target = os.path.normpath(os.path.join(SITE, path))
        if not os.path.exists(target):
            fails.append(f"{f} -> 死链 {u}")
    if os.path.getsize(os.path.join(SITE, f)) > 200 * 1024:
        fails.append(f"{f} 超过200KB")

# 题目完整性
q_ids = Counter()
n_articles = n_details = n_cb = 0
for f in files:
    t = open(os.path.join(SITE, f), encoding="utf-8").read()
    n_articles += t.count('<article class="q"')
    n_details += t.count('<details class="ans">')
    n_cb += t.count('class="master-cb"')
    for m in re.finditer(r'data-qid="(p\d+c\d+q\d+)"', t):
        q_ids[m.group(1)] += 1
dup = [k for k, v in q_ids.items() if v > 1]

# 图片引用存在性
img_refs = Counter()
missing_img = []
for f in files:
    t = open(os.path.join(SITE, f), encoding="utf-8").read()
    for m in re.finditer(r'src="(assets/[^"]+)"', t):
        img_refs[m.group(1)] += 1
        if not os.path.exists(os.path.join(SITE, m.group(1))):
            missing_img.append(f"{f}: {m.group(1)}")

# 未引用的图（清洗候选）
all_imgs = set()
for root, _, fs in os.walk(os.path.join(SITE, "assets")):
    for fn in fs:
        rel = os.path.relpath(os.path.join(root, fn), SITE).replace("\\", "/")
        all_imgs.add(rel)
unref = sorted(all_imgs - set(img_refs))

print(f"HTML文件: {len(files)}, 总链接: {link_count}")
print(f"article: {n_articles}, details: {n_details}, checkbox: {n_cb}, 唯一qid: {len(q_ids)}")
print(f"图片引用: {sum(img_refs.values())} 次 / {len(img_refs)} 张唯一")
if fails:
    print("!! 问题:"); [print("  " + x) for x in fails[:30]]
else:
    print("死链: 0, 超体积: 0")
if dup: print(f"!! 重复qid: {dup[:10]}")
if n_articles != len(q_ids): print(f"!! article数({n_articles}) != 唯一qid数({len(q_ids)})")
if n_articles != 1511: print(f"!! article数 != 1511")
if n_details != 1511: print(f"!! details数 != 1511")
if n_cb != 1511: print(f"!! checkbox数 != 1511")
if missing_img:
    print("!! 缺失图片:"); [print("  " + x) for x in missing_img[:20]]
print(f"未被引用的图片: {len(unref)}")
for u in unref[:10]: print("  " + u)
print("PASS" if not (fails or dup or missing_img or n_articles != 1511 or n_details != 1511 or n_cb != 1511) else "FAIL")
