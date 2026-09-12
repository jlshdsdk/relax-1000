# RELAX 1000题 · 408 自学题册（静态网站）

计算机考研 408 刷题自学网站：**1511 道题**、4 部分 24 章，题干/选项/答案/解析完整，
已应用纸质版勘误，可勾选「已掌握」记录进度（localStorage 本地保存）。

**在线阅读**：https://jlshdsdk.github.io/relax-1000/

## 站点结构（纯 MPA，无框架/无构建依赖）

- `index.html` 总目录 + 总进度
- `p{部分}c{章}.html`（如 `p1c5.html`）：每章一个页面，超过 30 题自动分页（`p1c5-2.html`）
- `style.css` 唯一样式表；每页一个内联小脚本（答案折叠 + 进度记录）
- `assets/` 插图（按题目编号命名）+ `assets/errata/` 勘误替换图
- 左侧目录与书目录逐字一致；窄屏收起为抽屉

## 目录结构

```
sources/   原始 PDF（习题册 / 解析册 / 勘误，未做任何修改）
tools/     解析与构建脚本（Python + PyMuPDF）
data/      解析产物：site.json（站点数据）、各阶段报告
*.html     站点页面（构建产物，部署到 GitHub Pages 的就是仓库根目录）
```

## 重新构建

```bash
pip install pymupdf
python tools/extract.py    # 解析三本 PDF -> data/*_raw.json
python tools/figures.py    # 提取插图 -> assets/
python tools/merge.py      # 合并题解 + 应用勘误 -> data/site.json
python tools/build_site.py # 生成站点 -> site/（发布时复制到仓库根目录）
python tools/check_site.py # 全站自检：死链/题量/体积
```

## 数据口径

- 题目总数 1511，与习题册逐章一致；题解按（部分, 章, 题号）配对，24 章全部对齐
- 勘误 33 条全部落地：文本替换、答案修正、勘误配图、核对备注（详见 `data/merge_report.txt`）
- 数学上下标按 PDF 基线信息还原为 `<sup>/<sub>`；复杂公式以文本近似呈现
- 插图为原图矢量/位图区域裁剪（170 DPI），`loading="lazy"`

## 禁区说明

- `sources/` 内三个 PDF 为原始素材，未做任何修改
- 本仓库为全新仓库，未触碰任何已有仓库/分支
