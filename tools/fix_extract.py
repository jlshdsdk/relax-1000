# -*- coding: utf-8 -*-
"""一次性清理 extract.py：删除旧 parse_solutions，补回 OPT 定义"""
import io, re, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

P = "tools/extract.py"
src = open(P, encoding="utf-8").read()

# 1) 删除旧 parse_solutions 函数（从 "def parse_solutions" 到 "return result" 后的空行）
m = re.search(r"\ndef parse_solutions\(path, toc\):.*?\n        return result\n", src, re.S)
if m:
    src = src[:m.start()] + "\n" + src[m.end():]
    print("removed parse_solutions")
else:
    print("parse_solutions not found (already removed?)")

# 2) 在 _attach 前补回 OPT 定义（若缺失）
if "OPT = re.compile" not in src:
    anchor = "def _attach(item, mode, ln, t):"
    src = src.replace(anchor, 'OPT = re.compile(r"(?:^|(?<![A-Za-z]))([A-D])\\s*．")\n\n\n' + anchor)
    print("OPT restored")

open(P, "w", encoding="utf-8").write(src)
print("saved, length:", len(src))
