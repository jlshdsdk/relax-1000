# -*- coding: utf-8 -*-
"""合并 v2：习题册 + 解析册 + 勘误 -> data/site.json
part1 章tag: c1=第1章 c2=第2章 c3=第3、4章 c4=第5章树 c5=第6章图 c6=第7章查找 c7=第8章排序
勘误策略：先核对电子版是否已是修正后内容；否则替换/正则修正；始终附勘误注。
"""
import json, os, re, sys, io, shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")

def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)

qbook = load("qbook_raw.json")
abook = load("abook_raw.json")
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

# ---------- HTML 渲染 ----------
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
    """行是否落在图框内（x、y 同时判定）：图右侧/左侧的并列文字不受影响"""
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
        assert cq["part"] == ca["part"] and cq["no"] == ca["no"]
        cid = f"p{cq['part']}c{cq['_tag']}"
        sols = {s["num"]: s for s in ca["items"]}
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
                    # 仅当该选项无文字内容（纯图示选项）且纵向匹配时才归属
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

log("== 勘误应用 ==")
# ---- 工具 ----
def add_note(q, text, to_solution=False, tag="已按勘误修正"):
    q.setdefault("errata_notes", []).append(text)
    q["errata_tag"] = True
    if to_solution:
        piece = f'<p class="errata-fix"><strong>勘误修正：</strong>{_esc(text)}</p>'
        q["expl_html"] = (q["expl_html"] + piece) if q["expl_html"] else piece
        q["sol_touched"] = True

def stem_check_or_repl(cid, n, already_sub, pat, repl, desc, note_text=None):
    q = qget(cid, n)
    if q is None:
        return f"[缺失] {cid}q{n}"
    if already_sub and already_sub in q["stem_text"]:
        add_note(q, note_text or f"电子版题干已为勘误后内容（{desc}），已核对。")
        return f"[已核对] {cid}q{n}: {desc}"
    new, cnt = re.subn(pat, repl, q["stem_text"])
    if cnt:
        q["stem_text"] = new
        q["stem_html"] = _esc(new).replace("\n", "<br>")
        add_note(q, note_text or desc)
        return f"[OK] {cid}q{n} 题干替换x{cnt}: {desc}"
    add_note(q, note_text or f"勘误：{desc}")
    return f"[未命中->注] {cid}q{n}: {desc}"

def opt_check_or_repl(cid, n, letter, already_sub, old, new, note_text=None):
    q = qget(cid, n)
    if q is None:
        return f"[缺失] {cid}q{n}"
    cur = q["opts"].get(letter, {}).get("text", "")
    if already_sub and already_sub in cur:
        add_note(q, note_text or f"选项{letter}已为勘误后内容，已核对。")
        return f"[已核对] {cid}q{n} 选项{letter}"
    if old and old in cur:
        q["opts"][letter]["text"] = cur.replace(old, new)
        q["opts"][letter]["html"] = _esc(q["opts"][letter]["text"])
        add_note(q, note_text or f"选项{letter}已按勘误修正。")
        return f"[OK] {cid}q{n} 选项{letter}: {old} -> {new}"
    if new and not cur:
        q["opts"][letter] = {"text": new, "html": _esc(new)}
        add_note(q, note_text or f"选项{letter}已按勘误设置。")
        return f"[OK] {cid}q{n} 选项{letter} 设为: {new[:30]}"
    add_note(q, note_text or f"选项{letter}应为：{new}")
    return f"[未命中->注] {cid}q{n} 选项{letter} 原文:{cur[:40]}"

def opt_set(cid, n, letter, new, note_text):
    q = qget(cid, n)
    if q is None:
        return f"[缺失] {cid}q{n}"
    if letter in q["opts"]:
        q["opts"][letter] = {"text": new, "html": _esc(new)}
    else:
        q["opts"][letter] = {"text": new, "html": _esc(new)}
    add_note(q, note_text)
    return f"[OK] {cid}q{n} 选项{letter} -> {new[:40]}"

def sol_check_or_repl(cid, n, already_sub, pat, repl, desc, note_text=None):
    q = qget(cid, n)
    if q is None:
        return f"[缺失] {cid}q{n}"
    if already_sub and already_sub in q["expl_text"]:
        add_note(q, note_text or f"解析已为勘误后内容（{desc}），已核对。", to_solution=True)
        return f"[已核对] {cid}q{n}: {desc}"
    new, cnt = re.subn(pat, repl, q["expl_text"])
    if cnt:
        q["expl_text"] = new
        q["expl_html"] = re.sub(pat, repl, q["expl_html"])
        add_note(q, note_text or desc, to_solution=True)
        return f"[OK] {cid}q{n} 解析替换x{cnt}: {desc}"
    add_note(q, note_text or f"勘误：{desc}", to_solution=True)
    return f"[未命中->注] {cid}q{n}: {desc}"

def sol_replace(cid, n, text, ans=None, note_text="解析已按勘误替换"):
    q = qget(cid, n)
    if q is None:
        return f"[缺失] {cid}q{n}"
    q["expl_text"] = text
    q["expl_html"] = _esc(text).replace("\n", "<br>")
    if ans:
        q["ans"] = ans
    q["sol_replaced"] = True
    add_note(q, note_text)
    return f"[OK替换解析] {cid}q{n} ans={q['ans']}"

# ---- 题目册 DS（part1: c4=第5章树 c5=第6章图 c6=第7章查找 c7=第8章排序）----
def t1():
    by_id["p1c3"]["chapter_notes"].append(
        "纸质版第3、4章第19题原缺序号，其后题目序号顺延+1；本电子版题号连续，题解一一对应（已核对）。")
    return "[章注] p1c3 编号说明"
A_T1 = ("T1 P13 DS3、4章19题 编号说明", t1)

A = []
A.append(A_T1)
A.append(("T2 P29 DS6章3题 强连通分量",
          lambda: stem_check_or_repl("p1c5", 3, "强连通分量", r"(?<!强)连通分量", "强连通分量",
                                     "连通分量→强连通分量", "题目中“连通分量”已按勘误为“强连通分量”，已核对。")))
A.append(("T3 P31 DS6章18题 B无向图",
          lambda: opt_check_or_repl("p1c5", 18, "B", "无向图", "有向图", "无向图",
                                    "勘误：B 选项中“有向图”应为“无向图”（电子版已修正，已核对）。")))
A.append(("T4 P38 DS6章59题 图替换", lambda: (qget("p1c5", 59) or {}) and _fig_replace("p1c5", 59)))
def _fig_replace(cid, n):
    q = qget(cid, n)
    q["stem_figs"] = ["assets/errata/errata_p1_0.png"]
    q["opt_figs"] = {}
    q["fig_replaced"] = True
    add_note(q, "题目配图已按勘误替换为下图。")
    return f"[OK替换题图] {cid}q{n}"
# 注意 _fig_replace 定义在 lambda 之后也会被调用时解析 ✓
A.append(("T5 P68 CO2章44题 选项III",
          lambda: stem_check_or_repl("p2c2", 44, "结果的符号位和最高数位进位情况相反",
                                     r"(?m)^III[．.、].*$", "III.运算时采用单符号位，结果的符号位和最高数位进位情况相反",
                                     "选项III按勘误替换", "题目中选项III已按勘误修正，已核对。")))
A.append(("T6 P72 CO2章84题 C选项", lambda: opt_set("p2c2", 84, "C", "30005829H", "C 选项已按勘误改为 30005829H。")))
A.append(("T7 P72 CO2章85题 C0001000H",
          lambda: stem_check_or_repl("p2c2", 85, "C0001000H", r"C\s*0*1\s*0\s*0\s*0\s*0\s*(?:H)?",
                                     "C0001000H", "C0010000→C0001000H",
                                     "题干地址已按勘误为 C0001000H，已核对。")))
A.append(("T8 P82 CO3章71题 序号4",
          lambda: stem_check_or_repl("p2c3", 71, "④TLB 命中，Cache未命中",
                                     r"④\s*TLB\s*命中[，,]\s*页表命中[，,]\s*Cache\s*未命中",
                                     "④TLB 命中，Cache未命中", "④内容按勘误修正",
                                     "序号④内容应为“④TLB 命中，Cache未命中”。")))
A.append(("T9 P92 CO5章19题 D选项", lambda: opt_set("p2c5", 19, "D", "Ⅰ.Ⅲ.Ⅵ", "D 选项已按勘误改为 Ⅰ.Ⅲ.Ⅵ。")))
A.append(("T10 P106 CO6章17题 D选项",
          lambda: opt_set("p2c6", 17, "D", "CPU 需要一直查询外设的状态，直到设备准备就绪时才可以进行数据传输",
                          "D 选项已按勘误替换。")))
A.append(("T11 P135 CO6章25题 解析修正",
          lambda: (add_note(qget("p2c6", 25),
                            "勘误修正：中断响应过程由硬件完成，其间完成断点和PSW的保存；中断处理过程由中断服务程序完成，期间恢复断点和中断屏蔽字；保存和恢复中断屏蔽字由中断服务程序完成。故 B 错误。",
                            to_solution=True), "[注] p2c6q25")[1]))
A.append(("T12 P128 OS2章51题 不严谨",
          lambda: (add_note(qget("p3c2", 51),
                            "原书注明：本题题目不严谨，A、C、D 均可成立，此题可以不做。"), "[注] p3c2q51")[1]))
A.append(("T13 P149 OS3章30题 括号",
          lambda: (add_note(qget("p3c3", 30),
                            "勘误说明：题目中的左右括号应为“^”（纸质版印刷有误，电子文本保留原括号显示）。"), "[注] p3c3q30")[1]))
A.append(("T14 P151 OS3章42题 A选项",
          lambda: opt_set("p3c3", 42, "A", "保存当前程序的现场。", "A 选项已按勘误改为“保存当前程序的现场。”")))
A.append(("T14b", lambda: (add_note(qget("p3c3", 42), "勘误确认：修改后答案仍选 C。"), "[注] p3c3q42")[1]))
A.append(("T15 P155 OS3章64题 C选项", lambda: opt_set("p3c3", 64, "C", "I、II、III", "C 选项已按勘误改为 I、II、III。")))
A.append(("T15b", lambda: (add_note(qget("p3c3", 64), "勘误确认：答案选 C。"), "[注] p3c3q64")[1]))
A.append(("T16 P163 OS4章38题 题干",
          lambda: (add_note(qget("p3c4", 38), "题干应为：设块长为512B，每个块号占2B。"), "[注] p3c4q38")[1]))
A.append(("T17 P167 OS4章61题 4567号块",
          lambda: stem_check_or_repl("p3c4", 61, "4567号块", r"第\s*4567\s*块", "4567号块",
                                     "第4567块→4567号块", "题干已按勘误为“4567号块”，已核对。")))
A.append(("T18 P210 CN4章26题 B选项", lambda: opt_set("p4c4", 26, "B", "0.0.0.1",
                                                     "B 选项已按勘误改为 0.0.0.1（网络号全0、主机号非全0，仅能用作源地址），仅保留 C 正确。")))
A.append(("T19 P219 CN4章98题 A选项", lambda: opt_set("p4c4", 98, "A", "10.0.0.1 的MAC地址",
                                                     "A 选项已按勘误改为“10.0.0.1 的MAC地址”；目的IP地址不变。")))
A.append(("T20 P222 CN5章16题 D选项", lambda: opt_set("p4c5", 16, "D", "0401", "D 选项已按勘误改为 0401。")))
# ---- 解析册 ----
A.append(("S1 P27 DS5章14题 公式图",
          lambda: (qget("p1c4", 14)["sol_figs"].append("assets/errata/errata_p6_0.png"),
                   add_note(qget("p1c4", 14), "解析配图（公式）已按勘误补入。", to_solution=True), "[OK图] p1c4s14")[2]))
A.append(("S2 P40 DS6章18题 dfs",
          lambda: (add_note(qget("p1c5", 18),
                            "解析勘误：B 选项解析中“对有向图做 DFS”应为“对无向图做 DFS”。", to_solution=True),
                   "[注] p1c5q18")[1]))
A.append(("S3 P67 DS8章46题 例子",
          lambda: sol_check_or_repl("p1c7", 46, "12，21", r"21、22", "12，21",
                                    "第一个例子21、22→12，21", "勘误：第一个例子应为 12，21。")))
A.append(("S4 P104 CO3章58题 解析替换",
          lambda: sol_replace("p2c3", 58,
                              "内存地址空间为64M=2^26，物理地址为26位。按字节编址，主存块长64B，块内地址为6bit。Cache数据容量8×64B=512B，标记阵列容量为532-512=20B，一共8行，每行的标记信息一共20bit，回写方式需要1bit脏位，另外1bit有效位，因此tag位为20-1-1=18bit。因此可以知道组号位数为26-18-6=2bit，可知该Cache采用8/2^2=2路组相联。比较器数量为2。答案选C。",
                              "C")))
A.append(("S5 P104 CO3章56题 轮次",
          lambda: sol_check_or_repl("p2c3", 56, "第3轮~第10轮", r"第\s*3\s*轮\s*~\s*第\s*9\s*轮",
                                    "第3轮~第10轮", "第3轮~第9轮→第3轮~第10轮",
                                    "勘误：“后续第3轮~第9轮”应为“后续第3轮~第10轮”。")))
A.append(("S6 P106 CO3章77题 解析补充",
          lambda: (add_note(qget("p2c3", 77),
                            "解析勘误补充：082H 转成十进制是130，此时查段表，存在位是1，段长是304。",
                            to_solution=True), "[注] p2c3q77")[1]))
A.append(("S7 P113 CO5章 第8题编号",
          lambda: (by_id["p2c5"]["chapter_notes"].append(
              "纸质版解析册第8题为多余序号（其内容属于第7题解析），其后解析编号应-1；本电子版已核对题解一一对应。"),
              "[章注] p2c5")[1]))
A.append(("S8 P116 CO5章15题 解析替换",
          lambda: sol_replace("p2c5", 15,
                              "通常将指令执行过程中数据所经过的路径，包括路径上的部件称为数据通路。ALU、通用寄存器、状态寄存器、Cache、MMU、浮点运算逻辑、异常和中断处理逻辑等都是指令执行过程中数据流经的部件，MDR 和 MAR 是CPU和主存进行数据交互的寄存器，也属于数据通路的一部分。\n数据通路由控制部件进行控制。控制部件根据每条指令功能的不同生成对数据通路的控制信号，并正确控制指令的执行流程。控制部件包括PC、IR、ID、控制单元CU、时序信号产生部件等。\n所以10个选项中只有PC、IR、ID不属于数据通路，其他属于，一共有7个，答案选C。",
                              "C")))
A.append(("S9 P167 OS2章42题 缺图",
          lambda: (qget("p3c2", 42)["sol_figs"].append("assets/errata/errata_p8_0.png"),
                   add_note(qget("p3c2", 42), "解析配图已按勘误补入。", to_solution=True), "[OK图] p3c2s42")[2]))
A.append(("S10 P198 OS3章30题 括号",
          lambda: (add_note(qget("p3c3", 30),
                            "解析勘误：解析中的左右括号应为“^”（电子文本保留原括号显示）。", to_solution=True),
                   "[注] p3c3q30")[1]))
A.append(("S11 P204 OS3章64题 解析替换",
          lambda: sol_replace("p3c3", 64,
                              "会发生Belady现象的算法：FIFO、CLOCK以及改进的CLOCK；不会发生Belady现象的算法：LRU、OPT，故Ⅰ、Ⅱ正确。如果进程的工作集都被调入了虚拟内存中，还是会发生缺页中断，且不会保持在较低水平；而如果进程的工作集都被调入物理内存中，进程的缺页率可以保持一个较低水平，故Ⅲ对、Ⅳ错。答案是C，I、II、III正确。",
                              "C")))
A.append(("S12 P264 CN4章26题 解析替换",
          lambda: sol_replace("p4c4", 26,
                              "IP 组播地址代表的是一组主机，而不是某一台特定的主机。因此，D 类组播地址（224.0.0.5）只能出现在IP数据报的目的地址字段中。一个IP数据报的源地址必须是发送该报文的单个主机的单播地址。B 选项：网络号全0，主机号非全0，表示本网络上一个主机，仅能用于源地址，无法作为目的地址。",
                              "C")))
A.append(("S13 P274 CN4章98题 解析替换",
          lambda: sol_replace("p4c4", 98,
                              "当主机H要向IP地址为8.8.8.8的节点发送分组时，会首先对比自己的IP地址和目的IP地址是否位于同一局域网。主机所在网络的网络号为10.0.0.0，而8.8.8.8的前24位与之不匹配，因此主机H会将IP分组发送给默认网关，MAC地址为默认网关的地址，即10.0.0.1的MAC地址。默认网关收到来自主机H的IP分组后，会TTL减1、修改源MAC地址为自己的MAC地址，重新计算IP首部校验和，但是不会修改目的IP地址。注意：源IP地址为私有地址，所以发往公网时，需要修改源地址为公网地址。",
                              "A")))

for desc, fn in A:
    try:
        log(fn())
    except Exception as e:
        log(f"[异常] {desc}: {type(e).__name__} {e}")

# ---------- 答案字母兜底（乱序/跨行答案） ----------
log("== 答案兜底 ==")
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
log(f"  仍无字母答案（多空/解答题）: {noans}")

# ---------- 输出 ----------
part_meta = {
    1: {"title": "第一部分", "book": "第一部分 408 1000题ds题目册"},
    2: {"title": "第二部分", "book": "第二部分 408 1000题co题目册"},
    3: {"title": "第三部分", "book": "第三部分 408 1000题os题目册"},
    4: {"title": "第四部分", "book": "第四部分 408 1000题cn题目册"},
}
err_dir = os.path.join(BASE, "assets", "errata")
os.makedirs(err_dir, exist_ok=True)
for f in os.listdir(os.path.join(DATA, "errata_imgs")):
    shutil.copy(os.path.join(DATA, "errata_imgs", f), os.path.join(err_dir, f))

site = {"parts": part_meta, "chapters": chapters,
        "total_q": sum(len(c["questions"]) for c in chapters)}
with open(os.path.join(DATA, "site.json"), "w", encoding="utf-8") as f:
    json.dump(site, f, ensure_ascii=False, indent=1)
with open(os.path.join(DATA, "merge_report.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(report))
print("\n".join(report))
print("site.json written")
