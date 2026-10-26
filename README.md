# RELAX 1000题 · 408 自学题册（静态网站）

计算机考研 408 刷题自学网站：**1576 道题**（2026年10月勘误版/27版）、4 部分 24 章，
题干/选项/答案/解析完整，可勾选「已掌握」记录进度（localStorage 本地保存）。

**在线阅读**：https://jlshdsdk.github.io/relax-1000/

## 站点结构（纯 MPA，无框架/无构建依赖）

- `index.html` 总目录 + 总进度
- `p{部分}c{章}.html`（如 `p1c5.html`）：每章一个页面，超过 30 题自动分页（`p1c5-2.html`）
- `style.css` 唯一样式表；每页一个内联小脚本（答案折叠 + 进度记录）
- `assets/` 插图（按题目编号命名）
- 左侧目录与书目录逐字一致；**可一键隐藏/展开**（桌面端记忆偏好，收起后正文占满全宽；窄屏为抽屉 + 遮罩点关）

## 目录结构

```
sources/   原始 PDF（旧版3本 + 2026-10勘误版2本，未做任何修改）
tools/     解析与构建脚本（Python + PyMuPDF；*_oct.py 为 2026-10 版管线）
data/      解析产物：site.json（站点数据）、各阶段报告、旧版 site_prev_1511.json
*.html     站点页面（构建产物，部署到 GitHub Pages 的就是仓库根目录）
```

## 重新构建（2026-10 勘误版）

```bash
pip install pymupdf
python tools/extract_oct.py   # 解析两本10月版PDF -> data/oct_*_raw.json（含速对表答案钥校验）
python tools/figures_oct.py   # 提取插图 -> assets/
python tools/merge_oct.py     # 合并题解 + 答案钥回填 + 分歧裁决 -> data/site.json
python tools/build_oct.py     # 生成站点 -> site/
python tools/check_oct.py     # 全站自检：死链/题量/体积
python tools/stage_repo.py    # 发布：site/ 复制到仓库根目录
```

（旧版 2026-09 管线 extract/figures/merge/build_site 保留在 tools/ 供溯源）

## 数据口径（2026-10 勘误版）

- 题目总数 1576（ds 411 / co 373 / os 417 / cn 375），与习题册序言及逐章计数一致；
  较上一版（1511 题）增补 65 题并重排部分章节
- 解析册每章【答案速对】表已解析为答案钥，逐题校验：1572/1576 直接吻合；
  4 处速对表与解答行分歧经人工裁决并在题目下附「勘误说明」注
  （p3c4q7、p4c3q68 速对表误印；p4c5q44 解答行字母误印；p4c1q37 为①②③配对题由答案钥回填 CDA）
- 旧版 33 条勘误已由 10 月版内置（抽查 19 项 15 项命中，其余 4 项随题目改写/删除退役，不再回灌）
- 跨版同题对比：真实答案变化仅 3 处（p1c6q42 C→B、p1c7q46 C→CB、p1c8q55 D→DA，后两处为新版改判多选）
- 10 月版 PDF 存在行框 y 坐标抖动与个别题号断行（P3概述52解、查找48解），解析器已按基线排序与顺序号补齐处理，
  并经 PaddleOCR 对 p31/p156/p169/p302 四页抽验（文本层与印刷一致，置信度 98%~99%）
- 数学上下标按 PDF 基线信息还原为 `<sup>/<sub>`；复杂公式以文本近似呈现
- 插图为原图矢量/位图区域裁剪，`loading="lazy"`

## 禁区说明

- `sources/` 内 PDF 为原始素材，未做任何修改

