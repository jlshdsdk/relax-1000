# -*- coding: utf-8 -*-
"""插图提取 v2：
- 矢量/栅格簇合并；同行竖条(括号碎片)先合并再丢弃
- 输出 bbox(manifest.rect) 供 HTML 生成时对图内文字去重
- 大图自动降 DPI 重渲染，目标单图 <=130KB
题目id: p{part}c{tag}q{num}；解析id: ...s{num}
"""
import pymupdf, json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
ASSETS = os.path.join(BASE, "assets")
os.makedirs(ASSETS, exist_ok=True)
# 清空旧图（跳过子目录）
for f in os.listdir(ASSETS):
    p = os.path.join(ASSETS, f)
    if os.path.isfile(p):
        os.remove(p)

BOOK_Q = os.path.join(BASE, "relax1000题习题册.pdf")
BOOK_A = os.path.join(BASE, "relax1000题解析册.pdf")
MIN_W, MIN_H = 28, 18
HDR_BAND = 55
SIZE_TARGET = 130 * 1024

def graphic_boxes(page):
    boxes = []
    try:
        boxes.extend(page.cluster_drawings())
    except Exception as e:
        print(f"cluster_drawings fail p{page.number+1}: {e}")
    for info in page.get_images(full=True):
        try:
            for r in page.get_image_rects(info[0]):
                boxes.append((r.x0, r.y0, r.x1, r.y1))
        except Exception:
            pass
    cand = []
    for b in boxes:
        x0, y0, x1, y1 = b
        w, h = x1 - x0, y1 - y0
        if w < MIN_W and h < MIN_W:
            continue
        if h < 4 and w < page.rect.width * 0.5:
            continue
        if y1 < HDR_BAND or y0 > page.rect.height - 45:
            continue
        cand.append([x0, y0, x1, y1])
    # 迭代合并（gap=6）
    changed = True
    while changed:
        changed = False
        out = []
        while cand:
            b = cand.pop()
            hit = None
            for o in out:
                if not (b[2] + 6 < o[0] or b[0] - 6 > o[2] or b[3] + 6 < o[1] or b[1] - 6 > o[3]):
                    hit = o
                    break
            if hit:
                hit[0] = min(hit[0], b[0]); hit[1] = min(hit[1], b[1])
                hit[2] = max(hit[2], b[2]); hit[3] = max(hit[3], b[3])
                changed = True
            else:
                out.append(b)
        cand = out
    # 同行竖条合并：w<40 且 h>2.2w 的框，若与另一竖条 y 中心相近(|dy|<12) 且横向距离<95，合并
    slivers = [b for b in cand if (b[2] - b[0]) < 40 and (b[3] - b[1]) > 2.2 * (b[2] - b[0])]
    others = [b for b in cand if b not in slivers]
    used = [False] * len(slivers)
    for i, s in enumerate(slivers):
        if used[i]:
            continue
        for j in range(i + 1, len(slivers)):
            if used[j]:
                continue
            t = slivers[j]
            dy = abs((s[1] + s[3]) / 2 - (t[1] + t[3]) / 2)
            dx = min(abs(s[2] - t[0]), abs(t[2] - s[0]))
            if dy < 12 and dx < 95:
                s[0] = min(s[0], t[0]); s[1] = min(s[1], t[1])
                s[2] = max(s[2], t[2]); s[3] = max(s[3], t[3])
                used[j] = True
    merged = [b for i, b in enumerate(slivers) if not used[i]] + others
    # 剩余孤立竖条丢弃（括号碎片）
    final = []
    for b in merged:
        w, h = b[2] - b[0], b[3] - b[1]
        if w < 40 and h > 2.2 * w and w < 60:
            continue
        final.append(b)
    return final

def text_lines(page):
    """页面内容文本行的 bbox 列表（用于避免裁剪框切字）"""
    d = page.get_text("dict")
    out = []
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            spans = [s for s in line.get("spans", []) if s.get("size", 0) <= 20 and s.get("text", "").strip()]
            if not spans:
                continue
            out.append(line["bbox"])
    return out

def adjust_clip(r, cluster, lines):
    """裁剪框边缘若切过文本行（且该行不是图内文字），收缩到行间隙。
    r: [x0,y0,x1,y1]；cluster: 原始图形bbox；lines: 文本行bbox"""
    for b in lines:
        lx0, ly0, lx1, ly1 = b
        if lx1 < r[0] + 2 or lx0 > r[2] - 2:
            continue
        # 完全在框内 -> 图内文字，保留
        if ly0 >= r[1] - 1 and ly1 <= r[3] + 1:
            continue
        # 顶边切过该行
        if ly0 < r[1] < ly1 - 1:
            new_y0 = ly1 + 2
            if new_y0 <= cluster[1] + 2:
                r[1] = new_y0
        # 底边切过该行
        elif ly0 + 1 < r[3] < ly1:
            new_y1 = ly0 - 2
            if new_y1 >= cluster[3] - 2:
                r[3] = new_y1
    return r

def render(page, clip, name):
    for dpi in (170, 135, 110, 90):
        pix = page.get_pixmap(clip=clip, dpi=dpi)
        path = os.path.join(ASSETS, name)
        pix.save(path)
        if os.path.getsize(path) <= SIZE_TARGET:
            return dpi
    return 90

def span_of_item(item, page):
    ys = []
    for k in ("stem", "body"):
        for ln, _ in item.get(k, []):
            if ln["page"] == page:
                ys.append(ln["y"])
    for _, entries in item.get("opts", {}).items():
        for ln, _ in entries:
            if ln["page"] == page:
                ys.append(ln["y"])
    if not ys:
        return None
    return min(ys), max(ys)

def extract(doc, chapters, kind):
    manifest = []
    for ch in chapters:
        # 预计算每题在各页的行范围，用于相邻题目的硬边界
        item_spans = []
        for item in ch["items"]:
            d = {}
            for pg in set(item["pages"]):
                sp = span_of_item(item, pg)
                if sp:
                    d[pg] = sp
            item_spans.append(d)
        for idx, item in enumerate(ch["items"]):
            qid = f"p{ch['part']}c{ch['_tag']}{kind}{item['num']}"
            prev_sp = item_spans[idx - 1] if idx > 0 else {}
            next_sp = item_spans[idx + 1] if idx + 1 < len(item_spans) else {}
            found = 0
            for pg in item["pages"]:
                page = doc[pg - 1]
                sp = span_of_item(item, pg)
                if sp is None:
                    continue
                y0, y1 = sp
                top_bound = HDR_BAND
                bot_bound = page.rect.height - 40
                if prev_sp.get(pg):
                    top_bound = max(top_bound, prev_sp[pg][1] + 4)
                if next_sp.get(pg):
                    bot_bound = min(bot_bound, next_sp[pg][0] - 4)
                for b in graphic_boxes(page):
                    bx0, by0, bx1, by1 = b
                    cy = (by0 + by1) / 2
                    if not (y0 - 8 <= cy <= y1 + 8):
                        continue
                    clip = [max(0, bx0 - 4), max(HDR_BAND, by0 - 4, min(top_bound, by1 - 6)),
                            min(page.rect.width, bx1 + 4),
                            min(page.rect.height - 40, by1 + 4, max(bot_bound, by0 + 6))]
                    clip = adjust_clip(clip, b, text_lines(page))
                    clip = pymupdf.Rect(*clip)
                    if clip.width < 8 or clip.height < 8:
                        continue
                    found += 1
                    name = f"{qid}_f{found}.png"
                    dpi = render(page, clip, name)
                    manifest.append({"id": qid, "file": name, "page": pg, "dpi": dpi,
                                     "w": round(clip.width, 1), "h": round(clip.height, 1),
                                     "rect": [round(v, 1) for v in clip]})
            if found:
                print(f"  {qid}: {found}图")
    return manifest

def main():
    with open(os.path.join(DATA, "qbook_raw.json"), encoding="utf-8") as f:
        qbook = json.load(f)
    with open(os.path.join(DATA, "abook_raw.json"), encoding="utf-8") as f:
        abook = json.load(f)
    for book in (qbook, abook):
        counters = {}
        for ch in book:
            k = ch["part"]
            counters[k] = counters.get(k, 0) + 1
            ch["_tag"] = counters[k]
    print("== 习题册 ==")
    doc = pymupdf.open(BOOK_Q)
    m1 = extract(doc, qbook, "q")
    doc.close()
    print("== 解析册 ==")
    doc = pymupdf.open(BOOK_A)
    m2 = extract(doc, abook, "s")
    doc.close()
    with open(os.path.join(DATA, "figures_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"q": m1, "a": m2}, f, ensure_ascii=False, indent=1)
    total = sum(os.path.getsize(os.path.join(ASSETS, f)) for f in os.listdir(ASSETS))
    print(f"合计: 习题册图 {len(m1)}, 解析册图 {len(m2)}, 总计 {total//1024}KB")

if __name__ == "__main__":
    main()
