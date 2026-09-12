# -*- coding: utf-8 -*-
"""全局扫描：栅格图/矢量图分布、渲染依赖、格式变体样本"""
import pdfplumber, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = r"D:\Users\王奕博\Desktop\relax1000题"
BOOKS = {"习题册": BASE + r"\relax1000题习题册.pdf", "解析册": BASE + r"\relax1000题解析册.pdf"}

for name, path in BOOKS.items():
    n_img_pages, n_vec_pages, total_imgs = 0, 0, 0
    vec_page_list = []
    with pdfplumber.open(path) as pdf:
        for i, p in enumerate(pdf.pages):
            ni = len(p.images)
            nv = len(p.lines) + len(p.rects) + len(p.curves)
            total_imgs += ni
            if ni: n_img_pages += 1
            if nv >= 5:  # 少量线可能是表格线/下划线，>=5 才算可能有图
                n_vec_pages += 1
                vec_page_list.append((i+1, nv))
    print(f"【{name}】含栅格图页数: {n_img_pages}, 栅格图总数: {total_imgs}, 矢量对象>=5的页数: {n_vec_pages}")
    if vec_page_list:
        print(f"  矢量页样本(前30): {vec_page_list[:30]}")

# 渲染依赖检查
try:
    import pypdfium2
    print("pypdfium2 OK", pypdfium2.V_PYPDFIUM2 if hasattr(pypdfium2,'V_PYPDFIUM2') else '')
except ImportError:
    print("pypdfium2 未安装")
try:
    import fitz
    print("PyMuPDF OK", fitz.__doc__)
except ImportError:
    print("PyMuPDF 未安装")

# 格式变体探测：解析册抽不同部分各2页
print("=" * 70)
with pdfplumber.open(BOOKS["解析册"]) as pdf:
    def clean(t):
        # 按字号过滤水印的简易版：只保留行
        return t
    for pg in [14, 40, 80, 150, 220, 260, 285]:
        t = pdf.pages[pg].extract_text() or ""
        print(f"--- 解析册 第{pg+1}页 前400字 ---")
        print(t[:400])

# 习题册综合题探测（DS部分可能有解答题）
print("=" * 70)
with pdfplumber.open(BOOKS["习题册"]) as pdf:
    for pg in [3, 20, 60, 130, 190, 230]:
        t = pdf.pages[pg].extract_text() or ""
        print(f"--- 习题册 第{pg+1}页 前350字 ---")
        print(t[:350])
