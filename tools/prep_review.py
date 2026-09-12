# -*- coding: utf-8 -*-
"""渲染站点页面 PNG（供视觉审查）+ 抽查包生成（供内容比对）"""
import os, re, sys, io, json, random, subprocess
import html as htmlmod
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")
SHOTS = os.path.join(BASE, "data", "shots")
os.makedirs(SHOTS, exist_ok=True)

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
EDGE = next((p for p in EDGE_CANDIDATES if os.path.exists(p)), None)
print("Edge:", EDGE)

def shot(html_name, out_name, w=1280, h=2400, mobile=False):
    if not EDGE:
        return False
    url = "file:///" + os.path.join(SITE, html_name).replace("\\", "/")
    args = [EDGE, "--headless=new", "--disable-gpu", f"--window-size={w},{h}",
            f"--screenshot={os.path.join(SHOTS, out_name)}", url]
    if mobile:
        args.insert(1, "--force-device-scale-factor=1")
    subprocess.run(args, timeout=60, capture_output=True)
    ok = os.path.exists(os.path.join(SHOTS, out_name))
    print(("OK  " if ok else "FAIL ") + out_name)
    return ok

# 1) 首页（桌面）
shot("index.html", "index.png", h=3000)
# 2) DS 第1章（代码块题图多）
shot("p1c1.html", "p1c1.png", h=4000)
# 3) DS 第6章 图（插图多、含勘误59题在第2页尾/第3页？59题在 chunk3? 60题分2页 31-60 -> p1c5-2 含 31-60 → 59,60）
shot("p1c5-2.html", "p1c5-2.png", h=4000)
# 4) CN 网络层 chunk1（勘误q26）
shot("p4c4.html", "p4c4.png", h=4000)
# 5) OS 内存 chunk2（勘误q64: q31-70? 70题 chunk1=1-30 chunk2=31-60 chunk3=61-70 → q64 在 p3c3-2）
shot("p3c3-2.html", "p3c3-2.png", h=4000)
# 6) 移动端宽度
shot("index.html", "index_mobile.png", w=400, h=1600, mobile=True)
shot("p1c1.html", "p1c1_mobile.png", w=400, h=2600, mobile=True)

# ---------- 抽查包 ----------
import pymupdf
DATA = os.path.join(BASE, "data")
with open(os.path.join(BASE, "data", "site.json"), encoding="utf-8") as f:
    site = json.load(f)
qbook = json.load(open(os.path.join(BASE, "data", "qbook_raw.json"), encoding="utf-8"))
abook = json.load(open(os.path.join(BASE, "data", "abook_raw.json"), encoding="utf-8"))

def strip_html(h):
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    return htmlmod.unescape(h)

random.seed(20260913)
samples = []
for ch in site["chapters"]:
    for q in ch["questions"]:
        samples.append((ch, q))
picks = random.sample(samples, 10)
picks.sort(key=lambda x: (x[0]["part"], x[0]["tag"], x[0]["questions"].index(x[1])))

def raw_book_text(book, part, tag, num, kind):
    counters = {}
    for c in book:
        counters.setdefault(c["part"], 0)
        counters[c["part"]] += 1
        if c["part"] == part and counters[c["part"]] == tag:
            for it in c["items"]:
                if it["num"] == num:
                    if kind == "q":
                        txt = "\n".join(t for _, t in it["stem"])
                        for L in sorted(it["opts"]):
                            txt += f"\n{L}．" + "\n".join(t for _, t in it["opts"][L])
                    else:
                        txt = "".join(t for _, t in it["body"])
                    return txt
    return "(未找到)"

out = []
for ch, q in picks:
    cid = ch["id"]
    n = q["num"]
    out.append(f"{'='*80}")
    out.append(f"[抽查] {cid} 第{n}题 (PDF源页 {q['pages']})")
    out.append("--- 源·习题册原文 ---")
    out.append(raw_book_text(qbook, ch["part"], ch["tag"], n, "q"))
    out.append("--- 站点·题面(含选项) ---")
    opts = "\n".join(f"{L}．{q['opts'][L]['text']}" for L in "ABCD" if L in q["opts"])
    out.append(strip_html(q["stem_html"]) + "\n" + opts)
    out.append("--- 源·解析册原文(前400字) ---")
    out.append(raw_book_text(abook, ch["part"], ch["tag"], n, "s")[:400])
    out.append("--- 站点·答案与解析(前400字) ---")
    out.append((f"答案：{q['ans'] or '(无字母)'}\n" + strip_html(q["expl_html"]))[:500])
with open(os.path.join(DATA, "spotcheck.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("抽查包: data/spotcheck.txt,", len(picks), "题")
