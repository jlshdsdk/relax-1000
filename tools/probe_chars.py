# -*- coding: utf-8 -*-
"""分析字符属性以区分水印与正文；提取第1页完整目录"""
import pdfplumber, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BOOK = r"D:\Users\王奕博\Desktop\relax1000题\relax1000题习题册.pdf"

with pdfplumber.open(BOOK) as pdf:
    p = pdf.pages[118]  # 第119页，之前看到水印混入
    chars = p.chars
    print(f"页面尺寸: {p.width} x {p.height}, 字符总数: {len(chars)}")
    # 按颜色/大小/方向分组统计
    groups = Counter()
    for c in chars:
        col = c.get('non_stroking_color')
        groups[(str(col), round(c['size'],1), c['upright'])] += 1
    print("\n字符组 (颜色, 字号, upright) -> 数量:")
    for k, v in groups.most_common(20):
        print(f"  {k}: {v}")
    # 每组抽样字符
    print("\n各组样本:")
    seen = {}
    for c in chars:
        key = (str(c.get('non_stroking_color')), round(c['size'],1), c['upright'])
        if key not in seen:
            seen[key] = []
        if len(seen[key]) < 30:
            seen[key].append(c['text'])
    for k, txts in seen.items():
        print(f"  {k}: {''.join(txts)}")

    # 旋转字符的 matrix 特征
    print("\nupright=False 的字符样本(前40):")
    rot = [c for c in chars if not c['upright']][:40]
    for c in rot:
        print(f"  '{c['text']}' matrix={c.get('matrix')} x0={c['x0']:.0f} top={c['top']:.0f} size={c['size']:.1f}")

    # 提取第1页目录全文
    print("=" * 70)
    print("【习题册 第1页完整目录】")
    print(pdf.pages[0].extract_text())
    print("=" * 70)
    print("【解析册 第1页完整目录】")
    with pdfplumber.open(r"D:\Users\王奕博\Desktop\relax1000题\relax1000题解析册.pdf") as pdf2:
        print(pdf2.pages[0].extract_text())
