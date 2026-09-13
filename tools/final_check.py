# -*- coding: utf-8 -*-
"""等待 Pages 构建完成并最终复核线上站点"""
import urllib.request, time, sys, io, json, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def api_status():
    out = subprocess.run(["gh", "api", "repos/jlshdsdk/relax-1000/pages"],
                         capture_output=True, timeout=30)
    if out.returncode != 0:
        return "unknown"
    return json.loads(out.stdout).get("status", "unknown")

for i in range(30):
    st = api_status()
    print(f"poll {i}: {st}")
    if st == "built":
        break
    time.sleep(15)

BASE = "https://jlshdsdk.github.io/relax-1000/"
def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=30)
    return r.status, r.read()

fails = []
import random
random.seed(7)
pages = ["", "style.css", "p1c1.html", "p1c3-2.html", "p1c7-3.html", "p2c2-3.html",
         "p2c5-3.html", "p3c2-5.html", "p3c3-3.html", "p4c4-4.html", "p4c6-2.html"]
pages += [f"assets/p1c5q46_f{i}.png" for i in (1, 2, 3)]
pages += ["assets/errata/errata_p6_0.png", "assets/errata/errata_p8_0.png"]
for p in pages:
    try:
        st, body = get(p)
        if st != 200:
            fails.append((p, st))
        print(p or "/", "->", st)
    except Exception as e:
        fails.append((p, str(e)))
        print(p, "ERR", e)
print("FAILS:", fails if fails else "none — 线上全部可访问")
