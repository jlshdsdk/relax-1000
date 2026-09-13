# -*- coding: utf-8 -*-
"""导航隐藏功能验证：生成预置 class 的测试副本并截图四种形态"""
import os, sys, io, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r"D:\Users\王奕博\Desktop\relax1000题"
SITE = os.path.join(BASE, "site")
SHOTS = os.path.join(BASE, "data", "shots")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 测试副本（截图后删除）
def make_copy(src, dst, html_cls="", body_cls=""):
    t = open(os.path.join(SITE, src), encoding="utf-8").read()
    t = t.replace('<html lang="zh-CN">', f'<html lang="zh-CN"{html_cls}>', 1)
    t = t.replace("<body>", f'<body{body_cls}>', 1)
    open(os.path.join(SITE, dst), "w", encoding="utf-8").write(t)

make_copy("index.html", "_test_hidden.html", html_cls=' class="nav-hidden"')
make_copy("p1c1.html", "_test_drawer.html", body_cls=' class="nav-open"')

def shot(name, out, size):
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--window-size={size}",
                    f"--screenshot={os.path.join(SHOTS, out)}",
                    "file:///" + os.path.join(SITE, name).replace("\\", "/")],
                   timeout=90, capture_output=True)
    ok = os.path.exists(os.path.join(SHOTS, out))
    print(out, "OK" if ok else "FAIL")
    return ok

shot("index.html", "nav_desktop_open.png", "1280,1400")
shot("_test_hidden.html", "nav_desktop_hidden.png", "1280,1400")
shot("_test_drawer.html", "nav_mobile_drawer.png", "400,1400")
shot("p1c1.html", "nav_mobile_closed.png", "400,1400")

for f in ("_test_hidden.html", "_test_drawer.html"):
    os.remove(os.path.join(SITE, f))
print("temp copies removed")
