# -*- coding: utf-8 -*-
"""组装发布仓库：sources/ + 根目录站点 + 文档，然后 git init/commit"""
import os, shutil, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)

# 1) sources/
os.makedirs("sources", exist_ok=True)
for f in ("relax1000题习题册.pdf", "relax1000题解析册.pdf", "1000题纸质版勘误.pdf"):
    dst = os.path.join("sources", f)
    if not os.path.exists(dst):
        shutil.copy2(f, dst)
        print("copied", f)

# 2) 站点到根目录
for f in os.listdir("site"):
    src = os.path.join("site", f)
    if os.path.isdir(src):
        dst = f
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, f)
print("site -> root done, files:", len(os.listdir(".")))
