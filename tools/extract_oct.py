# -*- coding: utf-8 -*-
"""解析 2026-10 勘误版（27版）两本 PDF -> data/oct_qbook_raw.json / oct_abook_raw.json
与 extract.py 同源，适配新版结构：
- 前置页 4 页（序3+目录1），正文从 PDF p5 起；印刷页 = PDF页 - 4；目录在 PDF p4
- 解析册每章开头有【答案速对】表：捕获为章 anskey（不落入题目正文），并逐题校验答案
- 过滤部分封面行 / 章标题碎片行，防止污染上一题
"""
import pymupdf, json, re, os, sys, io
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

DESK = r"C:/Users/王奕博/Desktop"
BOOK_Q = os.path.join(DESK, "27relax1000题题目册_10月勘误版.pdf")
BOOK_A = os.path.join(DESK, "27relax1000题解析册_10月勘误版.pdf")
PAGE_OFFSET = 4
TOC_PAGE = 4
FIRST_CONTENT_PAGE = 5

report = []
def log(s):
    report.append(str(s))
    print(s)

# ---------- 行提取（同 extract.py） ----------
def page_lines(page):
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
        if all(s["gray"] for s in spans_all):
            headers.append((y, "".join(s["t"] for s in spans_all)))
            continue
        oys = sorted(s["oy"] for s in spans_all)
        oy_med = round(oys[len(oys) // 2], 1)   # 基线中位数：行框 y0 有 ±2pt 抖动，基线稳定
        lines.append({"y": y, "oy_med": oy_med, "x0": round(x0, 1), "x1": round(x1, 1), "spans": spans_all})
    # 10月版行框 y 抖动会打乱相邻行 -> 按基线中位数重排
    lines.sort(key=lambda ln: (ln["oy_med"], ln["x0"]))
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

# ---------- 目录 ----------
def parse_toc(path):
    doc = pymupdf.open(path)
    out, hdrs = page_lines(doc[TOC_PAGE - 1])
    toc = []
    for ln in out:
        t = line_text(ln)
        t = re.sub(r"\.{3,}", "...", t)
        if re.match(r"^第[一二三四]部分", t):
            toc.append({"kind": "part", "title": t.split()[0], "full": t, "page": None})
            continue
        m = re.match(r"^(第\s*[\d、]+\s*章)\s*(.+?)\.{0,3}\s*(\d{1,3})\s*$", t)
        if m:
            toc.append({"kind": "chap", "no": re.sub(r"\s", "", m.group(1)),
                        "title": m.group(2).strip().rstrip("."),
                        "page": int(m.group(3))})
    doc.close()
    for i, t in enumerate(toc):
        if t["kind"] == "part" and t["page"] is None:
            for t2 in toc[i + 1:]:
                if t2["kind"] == "chap":
                    t["page"] = t2["page"] - 1
                    break
    return toc

# ---------- 全书游走 ----------
TITLE_JUNK = re.compile(
    r"^(?:第[一二三四]部分.*|408\s*1000\s*题.{0,4}(?:题目册|解析册)|第\s*\d+(?:[、,]\s*\d+)?\s*章|目\s*录|序)$")
KEYWORD_HEADS = ("【答案速对】", "【速对答案】")   # 两种表头写法都存在（P3 起为倒装版）
KEYROW = re.compile(r"^(?:[A-DＡ-Ｄ]|[（(]\s*[A-DＡ-Ｄ]{1,4}\s*[）)])+$")
KEYTOK = re.compile(r"[A-DＡ-Ｄ]|[（(][A-DＡ-Ｄ]{1,4}[）)]")
KEYNORM = {ord(f): ord(t) for f, t in zip("ＡＢＣＤ", "ABCD")}
# 强特征解起点：N．+ (字母[、,]{0,3}。 | （CD）。 | 答案：X | 【解析】)——行内切分与章边界防误触
STRONG_START = re.compile(
    r"(\d{1,3})\s*．\s*(?=(?:答案[:：]\s*)?(?:[A-DＡ-Ｄ]\s*[、,]?\s*){1,4}[。．]"
    r"|[（(]\s*[A-DＡ-Ｄ]{1,4}\s*[）)]\s*[。．]"
    r"|答案[:：]\s*[A-DＡ-Ｄ]|【解析】|【答案】)")

def collect_lines(doc, first_page):
    lines = []
    for pg in range(first_page, doc.page_count + 1):
        lns, _ = page_lines(doc[pg - 1])
        for ln in lns:
            ln["page"] = pg
            lines.append(ln)
    return lines

def expand_row(ln, t):
    """10月版解析册存在相邻两行合并为一个 PDF line 对象的情况：
    在行内按强特征解起点二次切分，返回 [(text, sub_ln), ...]"""
    cuts = [m.start() for m in STRONG_START.finditer(t) if m.start() > 0]
    bounds = [(0, len(t))] if not cuts else (list(zip([0] + cuts, cuts + [len(t)])))
    out = []
    for a, b in bounds:
        seg = t[a:b]
        if seg.strip():
            out.append((seg, slice_ln(ln, a, b)))
    return out

def walk_book(path, toc, start_re, mode):
    doc = pymupdf.open(path)
    chaps = [t for t in toc if t["kind"] == "chap"]
    parts = [t for t in toc if t["kind"] == "part"]
    lines = collect_lines(doc, FIRST_CONTENT_PAGE)
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
    pending_key = []      # 答案速对字母缓冲（属于下一个章）
    key_open = False

    def flush_key():
        nonlocal pending_key, key_open
        if cur_ch is not None and pending_key:
            cur_ch["anskey"] = list(pending_key)   # 令牌数组：多选 (CD) 占一位
        pending_key = []
        key_open = False

    def handle_seg(seg_ln, t):
        nonlocal cur, cur_ch, expected, key_open
        t = t.strip()
        if not t:
            return
        for head in KEYWORD_HEADS:
            if head in t:
                key_open = True
                t = t.split(head, 1)[1].strip()
                break
        if not t:
            return
        if key_open:
            letters = "".join(t.split())
            if letters and KEYROW.match(letters):
                pending_key.extend(tok.translate(KEYNORM)
                                   for tok in KEYTOK.findall(letters))
                return
            key_open = False
        if TITLE_JUNK.match(t):
            return
        m = start_re.match(t)
        if m and mode == "a" and int(m.group(1)) == 1 and not STRONG_START.match(t):
            m = None   # 解析册行首"1．"缺强特征，视作正文防误触章边界（题目册不适用）
        if not m:
            m2 = DETACHED_ANS.match(t)
            if m2 and mode == "a" and cur is not None:
                log(f"[补号] p{seg_ln['page']} 答案行缺题号，按第{expected}解补齐: {t[:36]}")
                cur_ch["items"].append(cur)
                ln_rest = slice_ln(seg_ln, m2.end(), len(t))
                cur = {"num": expected, "ans": m2.group(1).translate(KEYNORM),
                       "body": [(ln_rest, t[m2.end():].strip())], "pages": [seg_ln["page"]]}
                expected += 1
                return
            if cur is not None:
                _attach(cur, mode, seg_ln, t)
            elif re.match(r"^\d{1,3}\s*．", t):
                log(f"[警告] 丢弃编号行(无当前章): p{seg_ln['page']} {t[:50]}")
            return
        num = int(m.group(1))
        if num == 1:
            if cur is not None:
                cur_ch["items"].append(cur)
            if len(chapters) >= len(chaps):
                log(f"[警告] 章边界超过目录章数({len(chaps)})，page={seg_ln['page']} 行={t[:40]}")
                cur = None
                return
            info = chaps[len(chapters)]
            part_idx = part_of_print(info["page"])
            cur_ch = {"part": part_idx + 1,
                      "part_title": parts[part_idx]["title"] if parts else "",
                      "no": info["no"], "title": info["title"], "print_page": info["page"],
                      "items": [], "pages": [seg_ln["page"]]}
            chapters.append(cur_ch)
            flush_key()          # 速对表落在刚创建的新章
            cur = _new_item(mode, 1, seg_ln, t, m)
            expected = 2
            return
        if cur is not None and num == expected:
            cur_ch["items"].append(cur)
            cur = _new_item(mode, num, seg_ln, t, m)
            expected += 1
            return
        if cur is not None:
            _attach(cur, mode, seg_ln, t)
        elif num <= len(chaps) + 5:
            log(f"[警告] 丢弃编号行(无当前章): p{seg_ln['page']} {t[:50]}")

    for ln in lines:
        t = line_text(ln)
        if mode == "a":
            for seg, seg_ln in expand_row(ln, t):
                handle_seg(seg_ln, seg)
        else:
            handle_seg(ln, t)
    flush_key()
    if cur is not None:
        cur_ch["items"].append(cur)
    if len(chapters) != len(chaps):
        log(f"[警告] 章数不符: 解析出{len(chapters)} 目录{len(chaps)}")
    for c, info in zip(chapters, chaps):
        if c["no"] != info["no"] or c["title"] != info["title"]:
            log(f"[警告] 章标题不匹配: {c['no']} {c['title']} vs 目录 {info['no']} {info['title']}")
        nums = [it["num"] for it in c["items"]]
        if nums != list(range(1, len(nums) + 1)):
            log(f"[警告] {c['no']} {c['title']} 题号不连续: {nums[:10]}...")
        if mode == "q":
            bad = [it["num"] for it in c["items"]
                   if len([k for k in "ABCD" if it["opts"].get(k)]) not in (4, 0)]
            if bad:
                log(f"[提示] {c['no']} {c['title']} 选项数异常的题: {bad}")
    return chapters

def _new_item(mode, num, ln, t, m):
    ln0 = slice_ln(ln, m.end(), len(t))
    if mode == "q":
        rest = t[m.end():].strip()
        return {"num": num, "stem": [(ln0, rest)] if rest else [], "opts": {},
                "pages": [ln["page"]]}
    rest = t[m.end():]
    ans = re.sub(r"[、,,，（）()\s]", "", (m.group("ans") or "").upper())
    return {"num": num, "ans": ans, "body": [(ln0, rest.strip())], "pages": [ln["page"]]}

OPT = re.compile(r"([A-D])\s*[．.]")
_HOMO = {}
for _i, _ch in enumerate("ABCD"):
    _HOMO[chr(0x1D434 + _i)] = _ch
    _HOMO[chr(0x1D400 + _i)] = _ch
    _HOMO[chr(0x1D5A0 + _i)] = _ch
    _HOMO[chr(0x1D670 + _i)] = _ch
    _HOMO[chr(0xFF21 + _i)] = _ch
_HOMO["\u0410"] = "A"
_HOMO["\u0412"] = "B"
_HOMO["\u0421"] = "C"

def _opt_split(t, item):
    norm = "".join(_HOMO.get(ch, ch) for ch in t)
    marks = []
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

ANS = re.compile(r"^(\d{1,3})\s*．\s*(?:答案[:：]\s*)?"
                 r"(?P<ans>[A-DＡ-Ｄ](?:\s*[、,,，]\s*[A-DＡ-Ｄ]){0,3}"
                 r"|[（(]\s*[A-DＡ-Ｄ]{1,4}\s*[）)])?"
                 r"\s*[。．]?\s*(【解析】|【答案】|解析[:：])?")
# 版式缺陷兜底：题号前缀与答案行被拆散（行首直接是 字母。【解析】）
DETACHED_ANS = re.compile(r"^([A-DＡ-Ｄ])\s*[。．]\s*(【解析】|【答案】|解析[:：])")

# ---------- 主流程 ----------
def main():
    log("== 目录（题目册） ==")
    toc_q = parse_toc(BOOK_Q)
    for t in toc_q:
        log(f"  {t}")
    log("== 目录（解析册） ==")
    toc_a = parse_toc(BOOK_A)
    for t in toc_a:
        log(f"  {t}")

    log("== 习题册解析 ==")
    QNUM_START = re.compile(r"^(\d{1,3})\s*．")
    qbook = walk_book(BOOK_Q, toc_q, QNUM_START, "q")
    total_q = 0
    part_tot = defaultdict(int)
    for ch in qbook:
        n = len(ch["items"])
        total_q += n
        part_tot[ch["part"]] += n
        log(f"  P{ch['part']} {ch['no']} {ch['title']}: {n}题 起PDFp{ch['pages'][0]}(印{ch['print_page']})")
    log(f"  分部合计: {dict(part_tot)} 总计 {total_q}")

    log("== 解析册解析 ==")
    abook = walk_book(BOOK_A, toc_a, ANS, "a")
    total_a = 0
    for ch in abook:
        n = len(ch["items"])
        total_a += n
        key = ch.get("anskey", "")
        def kv(it):
            tok = key[it["num"] - 1] if len(key) >= it["num"] else "?"
            return tok.strip("（）()")
        ok = sum(1 for it in ch["items"] if it["ans"] and kv(it) == it["ans"])
        miss_ans = [it["num"] for it in ch["items"] if not it["ans"]]
        mism = [(it["num"], it["ans"], kv(it)) for it in ch["items"] if it["ans"] and kv(it) != it["ans"]]
        log(f"  P{ch['part']} {ch['no']} {ch['title']}: {n}解 key={len(key)}字母 答案吻合{ok}"
            + (f" 无字母{miss_ans}" if miss_ans else "")
            + (f" 不吻合{mism}" if mism else "")
            + ("" if len(key) == n else f" [key长度≠题数]"))

    log(f"== 合计: 题目册 {total_q} 题 / 解析册 {total_a} 解 ==")
    log("== 序言口径: ds411 co373 os417 cn375 总1576 ==")

    with open(os.path.join(DATA, "oct_qbook_raw.json"), "w", encoding="utf-8") as f:
        json.dump(qbook, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "oct_abook_raw.json"), "w", encoding="utf-8") as f:
        json.dump(abook, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "oct_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    print("\nDONE -> oct_qbook_raw.json / oct_abook_raw.json")

if __name__ == "__main__":
    main()
