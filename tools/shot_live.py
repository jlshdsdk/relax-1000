# -*- coding: utf-8 -*-
"""线上页面截图确认"""
import os, sys, io, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = r"D:\Users\王奕博\Desktop\relax1000题"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
shots = [(r"https://jlshdsdk.github.io/relax-1000/", "live_index.png", "1280,2400"),
         (r"https://jlshdsdk.github.io/relax-1000/p1c5-2.html", "live_p1c5.png", "1280,3000")]
for url, name, size in shots:
    out = os.path.join(BASE, "data", "shots", name)
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", f"--window-size={size}",
                    f"--screenshot={out}", url], timeout=90, capture_output=True)
    print(name, os.path.exists(out), os.path.getsize(out) // 1024, "KB")
