# -*- coding: utf-8 -*-
"""快速扫描（PyMuPDF）：栅格图/矢量图分布 + 格式变体样本"""
import sys, io
import pymupdf
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r"D:\Users\王奕博\Desktop\relax1000题"
BOOKS = {"习题册": BASE + r"\relax1000题习题册.pdf", "解析册": BASE + r"\relax1000题解析册.pdf",
         "勘误": BASE + r"\1000题纸质版勘误.pdf"}

for name, path in BOOKS.items():
    doc = pymupdf.open(path)
    img_pages, vec_pages, total_imgs = [], [], 0
    for i, page in enumerate(doc):
        ni = len(page.get_images(full=True))
        nd = page.get_drawings()
        nvec = sum(len(d["items"]) for d in nd)
        if ni:
            img_pages.append((i + 1, ni)); total_imgs += ni
        if nvec >= 5:
            vec_pages.append((i + 1, nvec))
    print(f"【{name}】{doc.page_count}页 | 栅格图页: {img_pages} 总数{total_imgs} | 矢量>=5的页({len(vec_pages)}): {vec_pages[:40]}")
    doc.close()

# 解析册/习题册格式变体样本
def dump(path, pages, tag, n=380):
    doc = pymupdf.open(path)
    print("=" * 70)
    for pg in pages:
        t = doc[pg].get_text("text")
        print(f"--- {tag} 第{pg+1}页 前{n}字 ---")
        print(t[:n])
    doc.close()

dump(BOOKS["解析册"], [14, 40, 80, 150, 220, 260, 285], "解析册")
dump(BOOKS["习题册"], [3, 20, 60, 130, 190, 230], "习题册", 300)
