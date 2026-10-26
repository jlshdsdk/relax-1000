# -*- coding: utf-8 -*-
"""合并（10月勘误版）：oct_qbook_raw + oct_abook_raw + figures_manifest -> data/site.json
- 旧版33条勘误不回灌：10月版已内置（除3条随题目改写退役）
- 速对表答案钥回填与校验；4处速对表/解答行分歧按人工裁决定点覆盖并附注
- 输出 site.json 带 edition 元数据
"""
import json, os, re, sys, io, shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
PAGE_OFFSET = 4

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)

qbook = load("oct_qbook_raw.json")
abook = load("oct_abook_raw.json")
figs = load("figures_manifest.json")

for book in (qbook, abook):
    counters = {}
    for ch in book:
        k = ch["part"]
        counters[k] = counters.get(k, 0) + 1
        ch["_tag"] = counters[k]

qfigs, sfigs = {}, {}
for m in figs["q"]:
    qfigs.setdefault(m["id"], []).append(m)
for m in figs["a"]:
    sfigs.setdefault(m["id"], []).append(m)

report = []
def log(s):
    report.append(str(s))
    print(s)

# ---------- HTML 渲染（同 merge.py） ----------
CJK_END = re.compile(r"[\u4e00-\u9fff。，、；：）】》”？！]，?$")
NEWLINE_START = re.compile(r"^(?:[ⅠⅡⅢⅣⅤⅥ][．.、]|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]|[（(]\d+[）)]\s|[\d]+[）)]\s|[IVX]+\.\s)")

def spans_html(spans, ref_size):
    out = []
    base_oy = sorted((s["oy"] for s in spans), key=lambda v: 0)[len(spans) // 2] if spans else 0
    for s in spans:
        t = s["t"]
        if not t:
            continue
        esc = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        small = s["size"] < ref_size * 0.75
        if s.get("sup") or (small and s["oy"] < base_oy - 1.5):
            esc = f"<sup>{esc}</sup>"
        elif small and s["oy"] > base_oy + 1.5:
            esc = f"<sub>{esc}</sub>"
        out.append(esc)
    return "".join(out)

def covered(ln, fig_rects):
    if not fig_rects:
        return False
    rects = fig_rects.get(ln["page"], [])
    y_mid = ln["y"] + 5
    x0 = ln.get("x0", 0)
    x1 = ln.get("x1", 9999)
    for r in rects:
        if r[1] - 2 <= y_mid <= r[3] + 2 and not (x0 > r[2] + 2 or x1 < r[0] - 2):
            return True
    return False

def render_lines(entries, fig_rects=None):
    pieces = []
    for ln, text in entries:
        if not text or covered(ln, fig_rects):
            continue
        ref = max((s["size"] for s in ln["spans"]), default=10.5)
        html = spans_html(ln["spans"], ref)
        if html.strip():
            pieces.append((ln, html))
    out = []
    for i, (ln, html) in enumerate(pieces):
        raw = "".join(s["t"] for s in ln["spans"])
        if i > 0 and NEWLINE_START.match(raw):
            out.append("<br>" + html)
        elif i > 0:
            prev_raw = "".join(s["t"] for s in pieces[i - 1][0]["spans"])
            if prev_raw and CJK_END.search(prev_raw[-2:]) and raw and '\u4e00' <= raw[0] <= '\u9fff':
                out.append(html)
            elif prev_raw and prev_raw[-1].isalnum() and raw and raw[0].isalnum():
                out.append(html)
            else:
                out.append(" " + html)
        else:
            out.append(html)
    return "".join(out)

def field_text(entries, fig_rects=None):
    return "\n".join(t for ln, t in entries if t and not covered(ln, fig_rects))

# ---------- 收集 ----------
def build_chapters():
    chapters = []
    for cq, ca in zip(qbook, abook):
        assert cq["part"] == ca["part"] and cq["no"] == ca["no"], (cq["no"], ca["no"])
        cid = f"p{cq['part']}c{cq['_tag']}"
        sols = {s["num"]: s for s in ca["items"]}
        anskey = ca.get("anskey", [])
        questions = []
        for q in cq["items"]:
            qid = f"{cid}q{q['num']}"
            sid = f"{cid}s{q['num']}"
            qrects, srects = {}, {}
            for m in qfigs.get(qid, []):
                qrects.setdefault(m["page"], []).append(m["rect"])
            for m in sfigs.get(sid, []):
                srects.setdefault(m["page"], []).append(m["rect"])
            stem_text = field_text(q["stem"], qrects)
            stem_html = render_lines(q["stem"], qrects)
            opts = {}
            for letter in "ABCD":
                entries = q["opts"].get(letter, [])
                if entries:
                    opts[letter] = {"text": field_text(entries, qrects),
                                    "html": render_lines(entries, qrects)}
            stem_figs, opt_fig_map = [], {}
            for m in qfigs.get(qid, []):
                r = m["rect"]
                cy = (r[1] + r[3]) / 2
                placed = False
                for letter, entries in q["opts"].items():
                    ys = [ln["y"] for ln, _ in entries if ln["page"] == m["page"]]
                    otext = opts.get(letter, {}).get("text", "")
                    if ys and not otext and min(ys) - 10 <= cy <= max(ys) + 30:
                        opt_fig_map.setdefault(letter, []).append(m["file"])
                        placed = True
                        break
                if not placed:
                    stem_figs.append(m["file"])
            ans, expl_html, expl_text, sol_figs = "", "", "", []
            if q["num"] in sols:
                s = sols[q["num"]]
                ans = s["ans"]
                expl_text = field_text(s["body"], srects)
                expl_html = render_lines(s["body"], srects)
                sol_figs = [m["file"] for m in sfigs.get(sid, [])]
            questions.append({
                "id": qid, "num": q["num"],
                "stem_text": stem_text, "stem_html": stem_html,
                "opts": opts, "stem_figs": stem_figs, "opt_figs": opt_fig_map,
                "ans": ans, "expl_text": expl_text, "expl_html": expl_html,
                "sol_figs": sol_figs, "pages": q["pages"],
                "src_print": q["pages"][0] - PAGE_OFFSET,
            })
        chapters.append({"id": cid, "part": cq["part"], "tag": cq["_tag"],
                         "no": cq["no"], "title": cq["title"], "print_page": cq["print_page"],
                         "questions": questions, "chapter_notes": []})
    return chapters

chapters = build_chapters()
by_id = {c["id"]: c for c in chapters}
def qget(cid, n):
    for q in by_id[cid]["questions"]:
        if q["num"] == n:
            return q
    return None

def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def add_note(q, text):
    q.setdefault("errata_notes", []).append(text)
    q["errata_tag"] = True

# ---------- 速对表回填（无字母答案的题） ----------
log("== 答案钥回填 ==")
for cq, ca in zip(qbook, abook):
    cid = f"p{cq['part']}c{cq['_tag']}"
    key = ca.get("anskey", [])
    for q in by_id[cid]["questions"]:
        if not q["ans"] and len(key) >= q["num"] and key[q["num"] - 1].strip("（）()"):
            q["ans"] = key[q["num"] - 1].strip("（）()")
            log(f"  [回填] {q['id']}: 答案={q['ans']}（来自速对表）")

# ---------- 4 处人工裁决（速对表 vs 解答行分歧） ----------
log("== 分歧裁决 ==")
VERDICTS = [
    ("p3c4", 7, "C",
     "勘误说明：本章【答案速对】表中本题误印为 B；按题意与解析，磁盘索引节点包含链接计数、物理位置与访问权限，"
     "不包含读写指针，答案应为 C。"),
    ("p4c3", 68, "C",
     "勘误说明：本章【答案速对】表中本题误印为 B；以太网 V2 帧结束由物理层编码违例（信道信号消失）判定，答案应为 C。"),
    ("p4c5", 44, "C",
     "勘误说明：本题解答行首字母误印为 A；按解析内容（ack=3000 累积确认 + SACK 已收 5000–6999），"
     "未确认字节为 3000–4999 与 7000–8999，答案应为 C（与本章速对表一致）。"),
]
for cid, n, ans, note in VERDICTS:
    q = qget(cid, n)
    q["ans"] = ans
    add_note(q, note)
    log(f"  [裁决] {cid}q{n} -> {ans}")

# ---------- 正文杂项清理 ----------
for c in chapters:
    for q in c["questions"]:
        if q["expl_html"].startswith("【解析】"):
            q["expl_html"] = q["expl_html"][4:]

# ---------- 答案字母兜底（答X案 / ①C ②D ③A 变体已在回填覆盖） ----------
log("== 兜底 ==")
for c in chapters:
    for q in c["questions"]:
        if not q["ans"]:
            m = re.search(r"答\s*([A-D])\s*案", q["expl_text"][:80])
            if m:
                q["ans"] = m.group(1)
                q["expl_html"] = re.sub(r"答\s*[A-D]\s*案\s*[:：]?\s*。?\s*【?解析】?", "", q["expl_html"], count=1)
                q["expl_text"] = re.sub(r"答\s*[A-D]\s*案\s*[:：]?\s*。?\s*【?解析】?", "", q["expl_text"], count=1)
                log(f"  [兜底] {q['id']}: 答案={q['ans']}")
noans = [q["id"] for c in chapters for q in c["questions"] if not q["ans"]]
log(f"  仍无答案: {noans}")

# ---------- 输出 ----------
shutil.copy(os.path.join(DATA, "site.json"), os.path.join(DATA, "site_prev_1511.json")) if os.path.exists(os.path.join(DATA, "site.json")) else None
part_meta = {
    1: {"title": "第一部分", "book": "第一部分 408 1000题ds题目册"},
    2: {"title": "第二部分", "book": "第二部分 408 1000题co题目册"},
    3: {"title": "第三部分", "book": "第三部分 408 1000题os题目册"},
    4: {"title": "第四部分", "book": "第四部分 408 1000题cn题目册"},
}
site = {"parts": part_meta, "chapters": chapters,
        "total_q": sum(len(c["questions"]) for c in chapters),
        "edition": "2026年10月勘误版（27版）", "prev_total_q": 1511, "updated": "2026-10-26"}
with open(os.path.join(DATA, "site.json"), "w", encoding="utf-8") as f:
    json.dump(site, f, ensure_ascii=False, indent=1)
with open(os.path.join(DATA, "oct_merge_report.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print("site.json written:", site["total_q"], "题")
