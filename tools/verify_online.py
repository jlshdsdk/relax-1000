# -*- coding: utf-8 -*-
"""线上验收：等待 Pages 构建，检查首页/章节页/图片/样式 可访问"""
import urllib.request, time, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE_URL = "https://jlshdsdk.github.io/relax-1000/"

def get(path):
    req = urllib.request.Request(BASE_URL + path, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=30)
    return r.status, r.read()

# 等待首次构建
for i in range(20):
    try:
        st, body = get("")
        print(f"attempt {i}: {st}, {len(body)} bytes")
        if st == 200 and len(body) > 1000:
            break
    except Exception as e:
        print(f"attempt {i}: {e}")
        time.sleep(20)
    time.sleep(10)

checks = ["", "style.css", "p1c1.html", "p4c4-4.html", "assets/p1c5q34_f1.png",
          "assets/errata/errata_p1_0.png", "p1c7-3.html"]
ok = True
for path in checks:
    try:
        st, body = get(path)
        print(f"{path or '/'} -> {st}, {len(body)} bytes")
        if st != 200:
            ok = False
    except Exception as e:
        print(f"{path} -> ERR {e}")
        ok = False

st, body = get("")
txt = body.decode("utf-8", "replace")
print("首页含总题数:", "1511" in txt, "| 含四部分目录:", "第四部分 408 1000题cn题目册" in txt)
st, q = get("p1c1.html")
qt = q.decode("utf-8", "replace")
print("章节页含题:", qt.count('class="q"'), "| 含答案折叠:", "答案与解析" in qt)
print("ALL OK" if ok else "SOME FAILED")
