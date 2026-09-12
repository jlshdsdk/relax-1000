# -*- coding: utf-8 -*-
"""裁剪放大 index_mobile 顶部段落 + 用500宽重拍对照"""
import io, sys, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r"D:\Users\王奕博\Desktop\relax1000题"
import pymupdf
pix = pymupdf.Pixmap(os.path.join(BASE, r"data\shots\index_mobile.png"))
print("400shot size:", pix.width, pix.height)
# 顶部 0-40, 150-230 放大3倍 -> 保存
clip = pymupdf.IRect(0, 160, 400, 230)
pix2 = pymupdf.Pixmap(pix, clip) if False else None
# pymupdf Pixmap(IRect, pix) 不支持直接裁剪，用 PIL 不可用时手动: 用 IRect 构造
try:
    sub = pymupdf.Pixmap(pix, clip)
except Exception as e:
    print("clip fail:", e)
    sub = pix
sub = pymupdf.Pixmap(sub, pymupdf.IRect(0, 0, sub.width, sub.height)) if False else sub
# 简单放大
big = pymupdf.Pixmap(sub, sub.irect) if False else sub
out = os.path.join(BASE, r"data\shots\para_zoom.png")
try:
    sub.save(out)
    print("saved", out, sub.width, sub.height)
except Exception as e:
    print("save fail:", e)

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
url = "file:///" + os.path.join(BASE, "site", "index.html").replace("\\", "/")
for w, name in [(368, "index_368.png"), (430, "index_430.png")]:
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--window-size={w},900",
                    f"--screenshot={os.path.join(BASE, 'data', 'shots', name)}", url],
                   timeout=60, capture_output=True)
    print(name, os.path.exists(os.path.join(BASE, "data", "shots", name)))
