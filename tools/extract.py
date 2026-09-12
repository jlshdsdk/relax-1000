# -*- coding: utf-8 -*-
"""
RELAX 1000题 主解析脚本
习题册 -> questions.json；解析册 -> solutions.json；勘误 -> errata.json
输出 data/ 目录与 report.txt（供人工/子代理审查）
"""
import pymupdf, json, re, os, sys, io
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

BOOK_Q = os.path.join(BASE, "relax1000题习题册.pdf")
BOOK_A = os.path.join(BASE, "relax1000题解析册.pdf")
BOOK_E = os.path.join(BASE, "1000题纸质版勘误.pdf")
PAGE_OFFSET = 2  # 印刷页 = PDF页 - 2

report = []
def log(s):
    report.append(str(s))
    print(s)

# ---------- 文本行提取（过滤水印/页眉/页码） ----------
def page_lines(page):
    """返回 [(y0, x0, text, is_gray_header)] 按 (y,x) 排序的行列表；
    span 级信息保留用于 <sup>/<sub>"""
    d = page.get_text("dict")
    rows = defaultdict(list)
    headers = []
    for blk in d.get("blocks", []):
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []):
            spans = []
            for sp in line.get("spans", []):
                size = sp.get("size", 0)
                if size > 20:      # 水印
                    continue
                color = sp.get("color", 0)
                # pymupdf color 是 sRGB int；0.647 灰 ≈ 0xA5A5A5
                gray = abs(((color >> 16) & 255) - 165) < 30 and abs(((color >> 8) & 255) - 165) < 30
                text = sp.get("text", "")
                if not text.strip():
                    continue
                text = "".join("•" if ch == "\uf09f" else ("" if "\uf000" <= ch <= "\uf0ff" else ch)
                               for ch in text)
                if not text.strip():
                    continue
                spans.append({"t": text, "size": round(size, 1), "sup": bool(sp.get("flags", 0) & 1),
                              "oy": round(sp.get("origin", (0, 0))[1], 1),
                              "gray": gray})
            if not spans:
                continue
            y = round(line["bbox"][1], 1)
            x = line["bbox"][0]
            rows[(y)].append((x, spans, line["bbox"]))
    lines = []
    for y in sorted(rows):
        spans_all = []
        x0, x1 = 1e9, 0
        for x, spans, bbox in sorted(rows[y]):
            spans_all.extend(spans)
            x0, x1 = min(x0, bbox[0]), max(x1, bbox[2])
        # 页眉：整行灰色
        if all(s["gray"] for s in spans_all):
            headers.append((y, "".join(s["t"] for s in spans_all)))
            continue
        lines.append({"y": y, "x0": round(x0, 1), "x1": round(x1, 1), "spans": spans_all})
    # 页码过滤：单独一行纯数字 且位于页面下部
    h = page.rect.height
    out = []
    for ln in lines:
        txt = "".join(s["t"] for s in ln["spans"]).strip()
        if re.fullmatch(r"\d{1,3}", txt) and ln["y"] > h - 60:
            continue
        out.append(ln)
    return out, headers

def line_text(ln):
    return "".join(s["t"] for s in ln["spans"]).strip()

def slice_ln(ln, start, end):
    """按字符偏移 [start,end) 切分行对象，返回轻量 ln（spans 同步裁剪）"""
    sub = []
    pos = 0
    for sp in ln["spans"]:
        t = sp["t"]
        s0, s1 = pos, pos + len(t)
        pos = s1
        a, b = max(s0, start), min(s1, end)
        if a < b:
            d = dict(sp)
            d["t"] = t[a - s0:b - s0]
            sub.append(d)
    return {"y": ln["y"], "page": ln["page"], "x0": ln.get("x0", 0), "x1": ln.get("x1", 9999),
            "spans": sub}

# ---------- 目录解析 ----------
PART_NAMES = ["第一部分", "第二部分", "第三部分", "第四部分"]
SUB = {"ds": "数据结构", "co": "计算机组成原理", "os": "操作系统", "cn": "计算机网络"}

def parse_toc(path):
    doc = pymupdf.open(path)
    out, hdrs = page_lines(doc[0])
    toc = []  # {kind: part/chap, title, page(印刷)}
    for ln in out:
        t = line_text(ln)
        if re.match(r"^第[一二三四]部分", t):
            m = re.search(r"(\d{1,3})\s*$", t)
            pt = re.match(r"^(第[一二三四]部分)", t)
            toc.append({"kind": "part", "title": pt.group(1),
                        "full": t, "page": int(m.group(1)) if m else None})
            continue
        m = re.match(r"^(第\s*[\d、]+\s*章)\s*(.+?)[\s.]*?(\d{1,3})\s*$", t)
        if m:
            toc.append({"kind": "chap", "no": re.sub(r"\s", "", m.group(1)),
                        "title": m.group(2).strip().rstrip("."),
                        "page": int(m.group(3))})
    doc.close()
    # part 页码兜底：= 该部分第一章印刷页 - 1
    if any(t["kind"] == "part" and t["page"] is None for t in toc):
        for i, t in enumerate(toc):
            if t["kind"] == "part" and t["page"] is None:
                for t2 in toc[i + 1:]:
                    if t2["kind"] == "chap":
                        t["page"] = t2["page"] - 1
                        break
    return toc

# ---------- 全书顺序游走解析 ----------
def collect_lines(doc, first_page):
    """按顺序收集全书内容行（跳过 first_page 之前的页）"""
    lines = []
    page_headers = {}
    for pg in range(first_page, doc.page_count + 1):
        lns, hdrs = page_lines(doc[pg - 1])
        for ln in lns:
            ln["page"] = pg
            lines.append(ln)
        page_headers[pg] = [h for _, h in hdrs]
    return lines, page_headers

def walk_book(path, toc, first_pdf_page, start_re, mode):
    """mode: 'q' 习题册 / 'a' 解析册。章边界=^1．行；顺序号校验"""
    doc = pymupdf.open(path)
    chaps = [t for t in toc if t["kind"] == "chap"]
    parts = [t for t in toc if t["kind"] == "part"]
    lines, page_headers = collect_lines(doc, first_pdf_page)
    doc.close()

    def part_of_print(pp):
        cur = 0
        for i, p in enumerate(parts):
            if p["page"] and pp >= p["page"]:
                cur = i
        return cur

    chapters = []
    cur_ch = None
    cur = None
    expected = 1
    boundaries = 0
    for ln in lines:
        t = line_text(ln)
        m = start_re.match(t)
        if not m:
            if cur is not None:
                _attach(cur, mode, ln, t)
            continue
        num = int(m.group(1))
        if num == 1:
            # 新章开始
            boundaries += 1
            if cur is not None:
                cur_ch["items"].append(cur)
            if len(chapters) >= len(chaps):
                log(f"[警告] 章边界超过目录章数({len(chaps)})，page={ln['page']} 行={t[:40]}")
                cur_ch["items"].append(cur) if cur is not None else None
                cur = None
                continue
            info = chaps[len(chapters)]
            part_idx = part_of_print(info["page"])
            cur_ch = {"part": part_idx + 1,
                      "part_title": parts[part_idx]["title"] if parts else "",
                      "sub": list(SUB.values())[part_idx] if parts else "",
                      "no": info["no"], "title": info["title"], "print_page": info["page"],
                      "items": [], "pages": [ln["page"]]}
            chapters.append(cur_ch)
            cur = _new_item(mode, 1, ln, t, m)
            expected = 2
            continue
        if cur is not None and num == expected:
            cur_ch["items"].append(cur)
            cur = _new_item(mode, num, ln, t, m)
            expected += 1
            continue
        # 非预期编号行 -> 当作正文
        if cur is not None:
            _attach(cur, mode, ln, t)
        elif num <= len(chaps) + 5:
            log(f"[警告] 丢弃编号行(无当前章): p{ln['page']} {t[:50]}")
    if cur is not None:
        cur_ch["items"].append(cur)
    # 校验
    if len(chapters) != len(chaps):
        log(f"[警告] 章数不符: 解析出{len(chapters)} 目录{len(chaps)}")
    for c, info in zip(chapters, chaps):
        if c["no"] != info["no"] or c["title"] != info["title"]:
            log(f"[警告] 章标题不匹配: {c['no']} {c['title']} vs 目录 {info['no']} {info['title']}")
        nums = [it["num"] for it in c["items"]]
        if nums != list(range(1, len(nums) + 1)):
            log(f"[警告] {c['no']} {c['title']} 题号不连续: {nums[:8]}...")
        if mode == "q":
            bad = [it["num"] for it in c["items"]
                   if len([k for k in "ABCD" if it["opts"].get(k)]) not in (4, 0)]
            if bad:
                log(f"[提示] {c['no']} {c['title']} 选项数异常的题: {bad}")
    return chapters, page_headers

def _new_item(mode, num, ln, t, m):
    ln0 = slice_ln(ln, m.end(), len(t))
    if mode == "q":
        rest = t[m.end():].strip()
        return {"num": num, "stem": [(ln0, rest)] if rest else [], "opts": {},
                "pages": [ln["page"]]}
    else:
        rest = t[m.end():]
        ans = (m.group("ans") or "").upper()
        return {"num": num, "ans": ans, "body": [(ln0, rest.strip())], "pages": [ln["page"]]}

OPT = re.compile(r"([A-D])\s*[．.]")
# 同形异码字符归一（仅用于选项标记匹配；1:1 映射，索引不变）
_HOMO = {}
for _i, _ch in enumerate("ABCD"):
    _HOMO[chr(0x1D434 + _i)] = _ch   # 数学斜体
    _HOMO[chr(0x1D400 + _i)] = _ch   # 数学粗体
    _HOMO[chr(0x1D5A0 + _i)] = _ch   # 无衬线
    _HOMO[chr(0x1D670 + _i)] = _ch   # 等宽
    _HOMO[chr(0xFF21 + _i)] = _ch    # 全角
_HOMO["\u0410"] = "A"  # 西里尔 А
_HOMO["\u0412"] = "B"  # 西里尔 В
_HOMO["\u0421"] = "C"  # 西里尔 С

def _opt_split(t, item):
    """选项切分：待收字母即可接受（兼容一行两选项的网格排布 A|D / B|C）。
    匹配时做同形字归一化；内容按原串切片（1:1 映射索引一致）。
    返回 (首选项前字符终点, [(letter, piece_start, piece_end)]) 或 None"""
    norm = "".join(_HOMO.get(ch, ch) for ch in t)
    marks = []  # (letter, m.start, m.end)
    for m in OPT.finditer(norm):
        letter = m.group(1)
        if letter not in item["opts"] and all(letter != mk[0] for mk in marks):
            marks.append((letter, m.start(), m.end()))
    if not marks:
        return None
    out = []
    for i, (letter, ms, me) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(t)
        out.append((letter, me, end))
    return marks[0][1], out


def _attach(item, mode, ln, t):
    """把续行挂到当前题/解：识别选项行（习题册），span 级切分"""
    if mode == "a":
        item["body"].append((ln, t))
        if ln["page"] not in item["pages"]:
            item["pages"].append(ln["page"])
        return
    res = _opt_split(t, item)
    if res:
        before_end, pieces = res
        if before_end > 0 and t[:before_end].strip():
            ln_before = slice_ln(ln, 0, before_end)
            if item.get("_last_opt"):
                item["opts"][item["_last_opt"]].append((ln_before, t[:before_end].strip()))
            else:
                item["stem"].append((ln_before, t[:before_end].strip()))
        for letter, ps, pe in pieces:
            ln_p = slice_ln(ln, ps, pe)
            item["opts"].setdefault(letter, []).append((ln_p, t[ps:pe].strip()))
            item["_last_opt"] = letter
        return
    if item.get("_last_opt"):
        item["opts"][item["_last_opt"]].append((ln, t))
    else:
        item["stem"].append((ln, t))
    if ln["page"] not in item["pages"]:
        item["pages"].append(ln["page"])

# ---------- 解析册 ----------
ANS = re.compile(r"^(\d{1,3})\s*．\s*(?:答案[:：]\s*)?(?P<ans>[A-DＡ-Ｄ])?\s*[。．]?\s*(【解析】|【答案】|解析[:：])?")

def parse_solutions(path, toc):
    doc = pymupdf.open(path)
    chaps = [t for t in toc if t["kind"] == "chap"]
    parts = [t for t in toc if t["kind"] == "part"]
    result = []
    for i, ch in enumerate(chaps):
        start_p = ch["page"] + PAGE_OFFSET
        end_p = chaps[i + 1]["page"] + PAGE_OFFSET - 1 if i + 1 < len(chaps) else doc.page_count
        lines = []
        for pg in range(start_p, min(end_p, doc.page_count) + 1):
            lns, _ = page_lines(doc[pg - 1])
            for ln in lns:
                ln["page"] = pg
                lines.append(ln)
        # 从 ^1． 开始
        qi = None
        for idx, ln in enumerate(lines):
            m = ANS.match(line_text(ln))
            if m and m.group(1) == "1":
                qi = idx
                break
        if qi is None:
            log(f"[警告-解析] 第{ch['no']} {ch['title']} 未找到第1题")
            continue
        lines = lines[qi:]
        sols = []
        cur = None
        for ln in lines:
            t = line_text(ln)
            m = ANS.match(t)
            expect = len(sols) + 1
            if m and int(m.group(1)) == expect:
                if cur:
                    sols.append(cur)
                ans = m.group(2).upper() if m.group(2) else ""
                # 去掉行首已消费部分，保留正文
                rest = t[m.end():]
                if not ans and rest.strip().startswith(("A", "B", "C", "D")):
                    pass
                cur = {"num": expect, "ans": ans, "body": [(ln, rest.strip())], "pages": [ln["page"]]}
                continue
            if cur is not None:
                cur["body"].append((ln, t))
                if ln["page"] not in cur["pages"]:
                    cur["pages"].append(ln["page"])
        if cur:
            sols.append(cur)
        # 解析册答案字母兜底：正文以 "A" 或 "A．xxx" 开头（"26．A 选项..."）不处理，报告为无字母
        part_idx = 0
        for j, p in enumerate(parts):
            if p["page"] and ch["page"] >= p["page"]:
                part_idx = j
        result.append({"part": part_idx + 1, "no": ch["no"], "title": ch["title"],
                       "print_page": ch["page"], "solutions": sols})
    doc.close()
    return result

# ---------- 勘误 ----------
def parse_errata():
    doc = pymupdf.open(BOOK_E)
    full = []
    img_files = []
    os.makedirs(os.path.join(DATA, "errata_imgs"), exist_ok=True)
    for i, page in enumerate(doc):
        pgno = i + 1
        t = page.get_text("text")
        full.append((pgno, t))
        for k, info in enumerate(page.get_images(full=True)):
            xref = info[0]
            pix = pymupdf.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            f = os.path.join(DATA, "errata_imgs", f"errata_p{pgno}_{k}.png")
            pix.save(f)
            img_files.append({"page": pgno, "file": f})
    doc.close()
    return full, img_files

# ---------- 主流程 ----------
log("== 目录解析（习题册） ==")
toc_q = parse_toc(BOOK_Q)
for t in toc_q:
    log(f"  {t}")
log("== 目录解析（解析册） ==")
toc_a = parse_toc(BOOK_A)
for t in toc_a:
    log(f"  {t}")

log("== 习题册解析 ==")
QNUM_START = re.compile(r"^(\d{1,3})\s*．")
qbook, q_headers = walk_book(BOOK_Q, toc_q, 3, QNUM_START, "q")
total_q = 0
for ch in qbook:
    n = len(ch["items"])
    total_q += n
    hdr_ch = [h for h in q_headers.get(ch["pages"][0], []) if "章" in h]
    log(f"  P{ch['part']} {ch['no']} {ch['title']}: {n}题 起始页p{ch['pages'][0]}(印{ch['print_page']}) 页眉:{hdr_ch[:1]}")

log("== 解析册解析 ==")
abook, a_headers = walk_book(BOOK_A, toc_a, 3, ANS, "a")
total_a = 0
for ch in abook:
    n = len(ch["items"])
    total_a += n
    log(f"  P{ch['part']} {ch['no']} {ch['title']}: {n}解")

log(f"== 合计: 习题册 {total_q} 题 / 解析册 {total_a} 解 ==")

log("== 匹配检查（题数 vs 解数） ==")
qmap = {(c["part"], c["no"]): c for c in qbook}
amap = {(c["part"], c["no"]): c for c in abook}
for key in sorted(qmap):
    qc = qmap[key]
    ac = amap.get(key)
    qn = len(qc["items"]) if qc else 0
    an = len(ac["items"]) if ac else 0
    noans = sum(1 for it in (ac["items"] if ac else []) if not it["ans"])
    flag = "" if qn == an else "  <-- 不一致"
    flag += f" （{noans}解无字母答案）" if noans else ""
    log(f"  P{key[0]} {key[1]} {qc['title'] if qc else '?'}: 题{qn} 解{an}{flag}")

log("== 勘误 ==")
efull, eimgs = parse_errata()
for pg, t in efull:
    log(f"--- 勘误第{pg}页 ---")
    log(t)
log(f"勘误图片: {[(e['page'], os.path.basename(e['file'])) for e in eimgs]}")

with open(os.path.join(DATA, "qbook_raw.json"), "w", encoding="utf-8") as f:
    json.dump(qbook, f, ensure_ascii=False, indent=1)
with open(os.path.join(DATA, "abook_raw.json"), "w", encoding="utf-8") as f:
    json.dump(abook, f, ensure_ascii=False, indent=1)
with open(os.path.join(DATA, "errata_raw.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(f"[p{pg}]\n{t}" for pg, t in efull))
with open(os.path.join(DATA, "report.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print("\nDONE")
