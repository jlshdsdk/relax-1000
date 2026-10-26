# -*- coding: utf-8 -*-
"""生成 MPA 静态站点（10月勘误版 1576 题）：与 build_site.py 同构
- 来源页 = q.src_print（印刷页 = PDF页-4，已在 merge 计算）
- 首页显示版本更新说明
"""
import json, os, sys, io, html as htmlmod

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(BASE, "site")
os.makedirs(SITE, exist_ok=True)
DATA = os.path.join(BASE, "data")
CHUNK = 30

with open(os.path.join(DATA, "site.json"), encoding="utf-8") as f:
    site = json.load(f)
chapters = site["chapters"]
parts = site["parts"]

# ---------- 分页计划 ----------
pages = []
for ch in chapters:
    qs = ch["questions"]
    n_chunks = max(1, (len(qs) + CHUNK - 1) // CHUNK)
    ch["_files"] = []
    for i in range(n_chunks):
        fname = f"{ch['id']}.html" if i == 0 else f"{ch['id']}-{i+1}.html"
        ch["_files"].append(fname)
        pages.append({"file": fname, "cid": ch["id"], "chunk_idx": i, "chunk_total": n_chunks,
                      "questions": qs[i*CHUNK:(i+1)*CHUNK], "chapter": ch})
page_by_cid = {}
for p in pages:
    page_by_cid.setdefault(p["cid"], []).append(p)

# ---------- 组件 ----------
INLINE_JS = """
(function(){
  var KEY='relax1000.mastered';
  var store={};
  try{store=JSON.parse(localStorage.getItem(KEY)||'{}');}catch(e){store={};}
  function save(){try{localStorage.setItem(KEY,JSON.stringify(store));}catch(e){}}
  // ---- 目录显示/隐藏 ----
  var NAVKEY='relax1000.navHidden';
  var mqMobile=window.matchMedia('(max-width:920px)');
  var navBtn=document.getElementById('navtoggle-btn');
  function syncAria(){
    if(!navBtn)return;
    var open=mqMobile.matches?document.body.classList.contains('nav-open')
             :!document.documentElement.classList.contains('nav-hidden');
    navBtn.setAttribute('aria-expanded',open?'true':'false');
  }
  if(navBtn){
    navBtn.addEventListener('click',function(){
      if(mqMobile.matches){
        document.body.classList.toggle('nav-open');
      }else{
        var h=document.documentElement.classList.toggle('nav-hidden');
        try{localStorage.setItem(NAVKEY,h?'1':'0');}catch(e){}
      }
      syncAria();
    });
  }
  var backdrop=document.querySelector('.backdrop');
  if(backdrop){backdrop.addEventListener('click',function(){
    document.body.classList.remove('nav-open');syncAria();
  });}
  document.querySelectorAll('.sidebar a').forEach(function(a){
    a.addEventListener('click',function(){document.body.classList.remove('nav-open');});
  });
  window.addEventListener('resize',syncAria);
  syncAria();
  // ---- 已掌握进度 ----
  function chapterDone(ch){
    var pre=ch+':',n=0;
    for(var k in store){if(k.indexOf(pre)===0&&store[k])n++;}
    return n;
  }
  function refresh(){
    document.querySelectorAll('[data-ch]').forEach(function(el){
      var ch=el.getAttribute('data-ch'),total=parseInt(el.getAttribute('data-total'),10)||0;
      var done=chapterDone(ch);
      var prog=el.querySelector('[data-prog]');
      if(prog)prog.textContent=done+'/'+total;
      var bar=el.querySelector('[data-bar]');
      if(bar)bar.style.width=(total?Math.round(done*100/total):0)+'%';
      el.classList.toggle('ch-done',total>0&&done>=total);
    });
    var all=document.querySelector('[data-all-total]');
    if(all){
      var total=parseInt(all.getAttribute('data-all-total'),10)||0,done=0;
      for(var k in store){if(store[k])done++;}
      var prog=document.querySelector('[data-all-prog]');
      if(prog)prog.textContent=done+'/'+total;
      var bar=document.querySelector('[data-all-bar]');
      if(bar)bar.style.width=(total?Math.round(done*100/total):0)+'%';
    }
  }
  document.querySelectorAll('input.master-cb[data-qid]').forEach(function(b){
    b.checked=!!store[b.getAttribute('data-qid')];
    b.addEventListener('change',function(){
      var id=b.getAttribute('data-qid');
      if(b.checked)store[id]=1;else delete store[id];
      save();refresh();
      var art=b.closest('article');
      if(art)art.classList.toggle('mastered',b.checked);
    });
  });
  var reset=document.getElementById('reset-progress');
  if(reset)reset.addEventListener('click',function(){
    if(confirm('确定清空全部“已掌握”记录？')){store={};save();
      document.querySelectorAll('input.master-cb').forEach(function(b){b.checked=false;});
      document.querySelectorAll('article.mastered').forEach(function(a){a.classList.remove('mastered');});
      refresh();}
  });
  refresh();
})();
"""

def sidebar(current_file=None):
    out = ['<aside class="sidebar"><div class="brand"><span class="brand-t">RELAX 1000题</span>'
           '<span class="brand-s">408 自学题册</span></div><nav class="toc">']
    cur_cid = None
    for p in pages:
        if p["file"] == current_file:
            cur_cid = p["cid"]
    for pi in (1, 2, 3, 4):
        meta = parts[str(pi)]
        out.append(f'<div class="toc-part">{htmlmod.escape(meta["book"])}</div>')
        for ch in chapters:
            if ch["part"] != pi:
                continue
            total = len(ch["questions"])
            cls = "toc-ch"
            if ch["id"] == cur_cid:
                cls += " current"
            multi = len(page_by_cid[ch["id"]]) > 1
            href = ch["_files"][0]
            tip = f'{ch["no"]}{ch["title"]}（教材第{ch["print_page"]}页起，共{total}题）'
            out.append(
                f'<a class="{cls}" href="{href}" data-ch="{ch["id"]}" data-total="{total}" title="{htmlmod.escape(tip, quote=True)}">'
                f'<span class="toc-title">{htmlmod.escape(ch["no"]+ " " + ch["title"])}</span>'
                f'<span class="toc-meta">{"分页" if multi else ""}<span data-prog></span></span>'
                f'<span class="bar"><span class="bar-fill" data-bar></span></span></a>')
    out.append('</nav><div class="side-foot">进度保存在本设备浏览器</div></aside>')
    return "".join(out)

def head(title):
    return (f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{htmlmod.escape(title)}</title>'
            f'<script>try{{if(localStorage.getItem("relax1000.navHidden")==="1")document.documentElement.classList.add("nav-hidden")}}catch(e){{}}</script>'
            f'<link rel="stylesheet" href="style.css"></head>')

def fig_src(f):
    return f if f.startswith("assets/") else "assets/" + f

def q_html(q):
    o = [f'<article class="q" id="q{q["num"]}">']
    o.append('<div class="q-head"><span class="q-num">'
             f'第 {q["num"]} 题</span>')
    o.append(f'<label class="master"><input type="checkbox" class="master-cb" data-qid="{q["id"]}">已掌握</label></div>')
    if q.get("errata_tag"):
        o.append('<div class="modified-tag">已按勘误修正</div>')
    o.append(f'<div class="stem">{q["stem_html"]}</div>')
    for f in q["stem_figs"]:
        o.append(f'<img class="fig" src="{fig_src(f)}" alt="题目配图" loading="lazy">')
    if q["opts"]:
        o.append('<ol class="opts">')
        for L in "ABCD":
            if L in q["opts"]:
                figs = "".join(f'<img class="fig" src="{fig_src(f)}" alt="选项{L}配图" loading="lazy">'
                               for f in q["opt_figs"].get(L, []))
                o.append(f'<li value="{L}"><span class="opt-letter">{L}．</span>'
                         f'<span class="opt-body">{q["opts"][L]["html"]}{figs}</span></li>')
        o.append('</ol>')
    ans_line = f'答案：<b>{q["ans"]}</b>' if q["ans"] else '答案：见解析'
    o.append('<details class="ans"><summary>答案与解析</summary>'
             f'<p class="ans-line">{ans_line}</p>')
    if q["expl_html"]:
        o.append(f'<div class="expl">{q["expl_html"]}</div>')
    for f in q["sol_figs"]:
        o.append(f'<img class="fig" src="{fig_src(f)}" alt="解析配图" loading="lazy">')
    for n in q.get("errata_notes", []):
        o.append(f'<p class="errata-note">勘误：{htmlmod.escape(n)}</p>')
    o.append('</details>')
    o.append(f'<span class="src" title="来源页">教材第 {q["src_print"]} 页</span>')
    o.append('</article>')
    return "".join(o)

def nav_html(idx):
    prev_p = pages[idx - 1] if idx > 0 else None
    next_p = pages[idx + 1] if idx + 1 < len(pages) else None
    out = ['<nav class="pager">']
    if prev_p:
        ch = prev_p["chapter"]
        label = f'{ch["no"]} {ch["title"]}' + (f'（{prev_p["chunk_idx"]+1}/{prev_p["chunk_total"]}）' if prev_p["chunk_total"] > 1 else '')
        out.append(f'<a class="pager-prev" href="{prev_p["file"]}">← {htmlmod.escape(label)}</a>')
    else:
        out.append('<span class="pager-prev"></span>')
    if next_p:
        ch = next_p["chapter"]
        label = f'{ch["no"]} {ch["title"]}' + (f'（{next_p["chunk_idx"]+1}/{next_p["chunk_total"]}）' if next_p["chunk_total"] > 1 else '')
        out.append(f'<a class="pager-next" href="{next_p["file"]}">{htmlmod.escape(label)} →</a>')
    else:
        out.append('<span class="pager-next"></span>')
    out.append('</nav>')
    return "".join(out)

def chunk_tabs(p):
    if p["chunk_total"] <= 1:
        return ""
    ch = p["chapter"]
    out = ['<nav class="chunks">本章分页：']
    for i in range(p["chunk_total"]):
        f = ch["_files"][i]
        if i == p["chunk_idx"]:
            out.append(f'<span>{i+1}</span>')
        else:
            out.append(f'<a href="{f}">{i+1}</a>')
    out.append('</nav>')
    return "".join(out)

# ---------- 章节页 ----------
for idx, p in enumerate(pages):
    ch = p["chapter"]
    q_lo = p["questions"][0]["num"] if p["questions"] else 0
    q_hi = p["questions"][-1]["num"] if p["questions"] else 0
    title = f'{ch["no"]} {ch["title"]}' + (f'（{p["chunk_idx"]+1}/{p["chunk_total"]}）' if p["chunk_total"] > 1 else '')
    body = [head(title + " - RELAX 1000题")]
    body.append('<body>')
    body.append('<button class="menu-btn" id="navtoggle-btn" type="button" aria-label="显示/隐藏目录" aria-expanded="true">☰ 目录</button>')
    body.append('<div class="backdrop" aria-hidden="true"></div>')
    body.append(sidebar(p["file"]))
    body.append('<main class="content">')
    part_meta = parts[str(ch["part"])]
    body.append(f'<header class="ch-head"><p class="crumb">{htmlmod.escape(part_meta["book"])}</p>'
                f'<h1>{htmlmod.escape(ch["no"])}　{htmlmod.escape(ch["title"])}</h1>'
                f'<p class="ch-meta">共 {len(ch["questions"])} 题 · 教材第 {ch["print_page"]} 页起'
                + (f' · 本页第 {q_lo}–{q_hi} 题' if p["chunk_total"] > 1 else '') + '</p>')
    body.append(chunk_tabs(p))
    for note in ch.get("chapter_notes", []):
        body.append(f'<p class="chapter-note">ℹ {htmlmod.escape(note)}</p>')
    body.append('</header>')
    for q in p["questions"]:
        body.append(q_html(q))
    body.append(nav_html(idx))
    body.append('<footer class="foot"><a href="index.html">返回总目录</a>'
                '<button id="reset-progress" class="reset" type="button">清空进度</button></footer>')
    body.append('</main>')
    body.append(f'<script>{INLINE_JS}</script>')
    body.append('</body></html>')
    with open(os.path.join(SITE, p["file"]), "w", encoding="utf-8") as f:
        f.write("".join(body))

# ---------- 首页 ----------
n_parts = len({c["part"] for c in chapters})
n_chs = len(chapters)
body = [head("RELAX 1000题 · 408 自学题册")]
body.append('<body>')
body.append('<button class="menu-btn" id="navtoggle-btn" type="button" aria-label="显示/隐藏目录" aria-expanded="true">☰ 目录</button>')
body.append('<div class="backdrop" aria-hidden="true"></div>')
body.append(sidebar("index.html"))
body.append('<main class="content"><header class="ch-head">'
            '<h1>RELAX 1000题 <span class="h-sub">计算机考研 408 · 自学题册</span></h1>'
            f'<p class="ch-meta">共 <span data-all-total="{site["total_q"]}">{site["total_q"]}</span>'
            f' 题 · {n_parts} 部分 {n_chs} 章 · 已完成 <span data-all-prog>0/{site["total_q"]}</span></p>'
            '<div class="bar big"><span class="bar-fill" data-all-bar></span></div>'
            f'<p class="ch-meta dim">{htmlmod.escape(site.get("edition", ""))} · 较上一版（1511 题）增补 65 题并重排部分章节，题目内容与答案以本版为准。</p>'
            '<p class="ch-meta dim">点开每题的「答案与解析」自测；做完一题勾选「已掌握」，各章进度会保存在本设备浏览器。</p>'
            '</header>')
for pi in (1, 2, 3, 4):
    meta = parts[str(pi)]
    body.append(f'<section class="part"><h2>{htmlmod.escape(meta["book"])}</h2>')
    for ch in chapters:
        if ch["part"] != pi:
            continue
        total = len(ch["questions"])
        href = ch["_files"][0]
        body.append(f'<a class="toc-row" href="{href}" data-ch="{ch["id"]}" data-total="{total}">'
                    f'<span class="toc-title">{htmlmod.escape(ch["no"])}　{htmlmod.escape(ch["title"])}</span>'
                    f'<span class="toc-meta"><span data-prog></span></span>'
                    f'<span class="bar"><span class="bar-fill" data-bar></span></span></a>')
    body.append('</section>')
body.append('<footer class="foot">内容来自《RELAX 1000题》' + htmlmod.escape(site.get("edition", ""))
            + '习题册/解析册 · '
            '<a href="https://github.com/jlshdsdk/relax-1000" rel="noopener">原始素材与脚本（GitHub）</a> · '
            '<button id="reset-progress" class="reset" type="button">清空进度</button></footer>')
body.append('</main>')
body.append(f'<script>{INLINE_JS}</script>')
body.append('</body></html>')
with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
    f.write("".join(body))

# ---------- CSS（与上一版一致） ----------
CSS = open(os.path.join(BASE, "style.css"), encoding="utf-8").read() if os.path.exists(os.path.join(BASE, "style.css")) else ""
if not CSS:
    raise SystemExit("缺少根目录 style.css 作为样式基线")
with open(os.path.join(SITE, "style.css"), "w", encoding="utf-8") as f:
    f.write(CSS)

# 复制 assets
import shutil
if os.path.exists(os.path.join(SITE, "assets")):
    shutil.rmtree(os.path.join(SITE, "assets"))
shutil.copytree(os.path.join(BASE, "assets"), os.path.join(SITE, "assets"))

total_pages = len(pages) + 1
sizes = [os.path.getsize(os.path.join(SITE, f)) for f in os.listdir(SITE) if f.endswith(".html")]
print(f"生成 {total_pages} 个HTML, 总HTML体积 {sum(sizes)//1024}KB, 最大单页 {max(sizes)//1024}KB")
