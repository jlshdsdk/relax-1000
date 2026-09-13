# -*- coding: utf-8 -*-
"""生成 MPA 静态站点：
- index.html：总目录 + 总进度
- 每章按 ≤30 题分页：p{part}c{tag}.html / p{part}c{tag}-2.html ...
- 左侧边栏 = 书目录逐字（4部分24章），进度徽标
- 单内联脚本：localStorage 已掌握状态 + 进度
- 底部上一页/下一页
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
pages = []  # {file, cid, chunk_idx, chunk_total, qslice, chapter}
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
    o.append(f'<span class="src" title="来源页">教材第 {q["pages"][0]-2} 页</span>')
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
body = [head("RELAX 1000题 · 408 自学题册")]
body.append('<body>')
body.append('<button class="menu-btn" id="navtoggle-btn" type="button" aria-label="显示/隐藏目录" aria-expanded="true">☰ 目录</button>')
body.append('<div class="backdrop" aria-hidden="true"></div>')
body.append(sidebar("index.html"))
body.append('<main class="content"><header class="ch-head">'
            '<h1>RELAX 1000题 <span class="h-sub">计算机考研 408 · 自学题册</span></h1>'
            f'<p class="ch-meta">共 <span data-all-total="{site["total_q"]}">{site["total_q"]}</span>'
            f' 题 · 4 部分 24 章 · 已完成 <span data-all-prog>0/{site["total_q"]}</span></p>'
            '<div class="bar big"><span class="bar-fill" data-all-bar></span></div>'
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
body.append('<footer class="foot">内容来自《RELAX 1000题》习题册/解析册并应用纸质版勘误 · '
            '<a href="https://github.com/jlshdsdk/relax-1000" rel="noopener">原始素材与脚本（GitHub）</a> · '
            '<button id="reset-progress" class="reset" type="button">清空进度</button></footer>')
body.append('</main>')
body.append(f'<script>{INLINE_JS}</script>')
body.append('</body></html>')
with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
    f.write("".join(body))

# ---------- CSS ----------
CSS = """:root{--ac:#2563eb;--ink:#1f2937;--dim:#6b7280;--line:#e5e7eb;--bg:#fff}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;overflow-wrap:break-word}
.sidebar{position:fixed;top:0;left:0;bottom:0;width:270px;overflow-y:auto;border-right:1px solid var(--line);padding:64px 14px 30px;transition:transform .25s ease}
.brand{display:block;margin:2px 6px 16px}
.brand-t{font-size:19px;font-weight:700;color:var(--ink)}
.brand-s{display:block;font-size:12px;color:var(--dim)}
.toc-part{font-size:12.5px;color:var(--dim);margin:18px 6px 6px;font-weight:600}
.toc-ch,.toc-row{display:block;position:relative;padding:7px 10px;border-radius:8px;color:var(--ink);text-decoration:none;font-size:14.5px}
.toc-ch:hover,.toc-row:hover{background:#f3f4f6}
.toc-ch.current{background:#eff6ff;color:var(--ac)}
.toc-ch.current .toc-title{font-weight:600}
.toc-title{display:inline-block;max-width:170px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom}
.toc-meta{float:right;font-size:12px;color:var(--dim)}
.ch-done .toc-meta{color:#16a34a}
.bar{display:block;height:3px;background:var(--line);border-radius:2px;margin-top:5px;overflow:hidden}
.bar-fill{display:block;height:100%;width:0;background:var(--ac);transition:width .3s}
.content{max-width:840px;margin:0 auto;padding:34px 26px 60px;transition:margin .25s ease}
.crumb{color:var(--dim);font-size:13px;margin:0}
h1{font-size:26px;margin:6px 0 4px;font-weight:700}
.h-sub{font-size:15px;color:var(--dim);font-weight:400;margin-left:8px}
.ch-meta{color:var(--dim);font-size:13.5px;margin:2px 0 10px}
.dim{color:var(--dim)}
h2{font-size:19px;margin:34px 0 8px}
.bar.big{height:6px;margin:6px 0 10px}
.chunks{font-size:13px;color:var(--dim);margin-bottom:6px}
.chunks a,.chunks span{display:inline-block;min-width:26px;text-align:center;padding:1px 6px;margin-right:4px;border-radius:6px;border:1px solid var(--line);text-decoration:none;color:var(--ink)}
.chunks span{background:#eff6ff;border-color:#bfdbfe;color:var(--ac);font-weight:600}
.chapter-note{background:#fffbeb;border:1px solid #fde68a;color:#92400e;font-size:13.5px;padding:8px 12px;border-radius:8px}
.q{border-top:1px solid var(--line);padding:26px 2px 18px;margin-top:6px}
.q.mastered{background:#f0fdf4;border-radius:10px;padding-left:12px;padding-right:12px}
.q-head{display:flex;align-items:center;gap:14px;margin-bottom:10px}
.q-num{font-weight:700;color:var(--ac);font-size:15.5px}
.master{margin-left:auto;font-size:13px;color:var(--dim);cursor:pointer;user-select:none}
.master input{vertical-align:-2px;margin-right:4px;accent-color:#16a34a}
.modified-tag{display:inline-block;font-size:12px;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:1px 8px;margin-bottom:8px}
.stem{font-size:16px}
.opts{list-style:none;margin:12px 0 0;padding:0}
.opts li{display:flex;gap:8px;padding:5px 0}
.opt-letter{color:var(--dim);flex:none}
.fig{display:block;max-width:min(100%,520px);height:auto;margin:12px auto;border:1px solid var(--line);border-radius:8px}
.ans{margin-top:14px;border:1px solid var(--line);border-radius:10px;background:#fafafa}
.ans summary{cursor:pointer;padding:9px 14px;font-size:14px;color:var(--ac);user-select:none}
.ans[open] summary{border-bottom:1px dashed var(--line)}
.ans-line{margin:10px 14px 4px;font-size:15px}
.expl{padding:2px 16px 10px;font-size:15px;color:#374151}
.errata-fix,.errata-note{font-size:13px;color:#92400e;background:#fffbeb;border-radius:8px;padding:6px 10px;margin:8px 14px}
.errata-note{margin:6px 14px 12px}
.src{display:block;text-align:right;font-size:11.5px;color:#c0c6cf;margin-top:6px}
.pager{display:flex;justify-content:space-between;gap:14px;margin:34px 0 10px}
.pager a,.pager span{flex:1;display:block;padding:12px 14px;border:1px solid var(--line);border-radius:10px;text-decoration:none;color:var(--ink);font-size:14px}
.pager a:hover{border-color:var(--ac);color:var(--ac)}
.pager-next{text-align:right}
.foot{display:flex;justify-content:space-between;align-items:center;margin-top:20px;font-size:13px;color:var(--dim)}
.foot a{color:var(--dim)}
.reset{border:1px solid var(--line);background:#fff;color:var(--dim);border-radius:8px;padding:4px 10px;font-size:12.5px;cursor:pointer}
.reset:hover{color:#dc2626;border-color:#fca5a5}
.part{margin-bottom:10px}
.toc-row{display:flex;align-items:center;gap:12px;border:1px solid var(--line);border-radius:10px;padding:10px 16px;margin:8px 0;text-decoration:none;color:var(--ink)}
.toc-row:hover{border-color:var(--ac)}
.toc-row .toc-title{max-width:none;font-size:15px}
.toc-row .toc-meta{float:none;flex:none}
.toc-row .bar{flex:1;margin:0}
.menu-btn{position:fixed;top:10px;left:10px;z-index:40;background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 12px;font-size:14px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.menu-btn:hover{border-color:var(--ac);color:var(--ac)}
.backdrop{display:none}
@media (min-width:921px){
  .content{margin:0 30px 0 300px}
  html.nav-hidden .sidebar{transform:translateX(-105%)}
  html.nav-hidden .content{margin:0 auto}
}
@media (max-width:920px){
  .sidebar{transform:translateX(-105%);z-index:30;background:#fff}
  body.nav-open .sidebar{transform:none;box-shadow:0 0 40px rgba(0,0,0,.18)}
  body.nav-open .backdrop{display:block;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(15,23,42,.35);z-index:25}
  .content{padding:56px 16px 50px}
  .toc-title{max-width:150px}
}
"""
with open(os.path.join(SITE, "style.css"), "w", encoding="utf-8") as f:
    f.write(CSS)

# 复制 assets
import shutil
if os.path.exists(os.path.join(SITE, "assets")):
    shutil.rmtree(os.path.join(SITE, "assets"))
shutil.copytree(os.path.join(BASE, "assets"), os.path.join(SITE, "assets"))

total_pages = len(pages) + 1
total_size = sum(os.path.getsize(os.path.join(SITE, f)) for f in os.listdir(SITE) if f.endswith(".html"))
print(f"生成 {total_pages} 个HTML, 总HTML体积 {total_size//1024}KB, 最大单页 {max(os.path.getsize(os.path.join(SITE,f)) for f in os.listdir(SITE) if f.endswith('.html'))//1024}KB")
