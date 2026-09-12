# -*- coding: utf-8 -*-
"""探测三个 PDF 的结构：页数、文本层、书签目录、题目格式样本"""
import pdfplumber, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FILES = {
    "习题册": r"D:\Users\王奕博\Desktop\relax1000题\relax1000题习题册.pdf",
    "解析册": r"D:\Users\王奕博\Desktop\relax1000题\relax1000题解析册.pdf",
    "勘误":   r"D:\Users\王奕博\Desktop\relax1000题\1000题纸质版勘误.pdf",
}

def outline_recursive(node, depth, out):
    if isinstance(node, list):
        for sub in node:
            outline_recursive(sub, depth, out)
        return
    if hasattr(node, 'get'):
        pass
    # pdfplumber doesn't expose outlines; use pypdf if available
    return

for name, path in FILES.items():
    print("=" * 70)
    print(f"【{name}】 {path}")
    with pdfplumber.open(path) as pdf:
        print(f"页数: {len(pdf.pages)}")
        # 前2页文本
        for i in [0, 1]:
            if i < len(pdf.pages):
                t = pdf.pages[i].extract_text() or ""
                print(f"--- 第{i+1}页文本 (前600字) ---")
                print(t[:600])
        # 中间页样本
        mid = len(pdf.pages) // 2
        t = pdf.pages[mid].extract_text() or ""
        print(f"--- 第{mid+1}页文本 (前500字) ---")
        print(t[:500])
        # 图片统计（判断扫描版）
        p = pdf.pages[mid]
        print(f"中间页图片数: {len(p.images)}, 字符数: {len(p.chars)}")

# 书签目录用 pypdf 读
try:
    from pypdf import PdfReader
    for name, path in FILES.items():
        print("=" * 70)
        print(f"【{name}】书签目录:")
        r = PdfReader(path)
        def walk(items, depth=0):
            for it in items:
                if isinstance(it, list):
                    walk(it, depth + 1)
                else:
                    try:
                        pg = r.get_destination_page_number(it) + 1
                    except Exception:
                        pg = "?"
                    print("  " * depth + f"- {it.title}  (p{pg})")
        try:
            walk(r.outline)
        except Exception as e:
            print(f"  无书签或读取失败: {e}")
except ImportError:
    print("pypdf 未安装，跳过书签读取")
