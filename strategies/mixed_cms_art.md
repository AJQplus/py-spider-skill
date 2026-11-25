# MacCMS vod+art 混合站（视频+美图+小说）策略模块 v9.5

## 适用条件

站点 URL 同时出现 `/index.php/vod/...` 与 `/index.php/art/...`，即 MacCMS v10 影视模块 + 资讯(article)模块共存；资讯模块下既有图片图集（美图）又有纯文本正文（小说）。典型导航：视频一区/二区/三区/四区 + 美图专区 + 小说专区。

## 站点画像要点

- 导航菜单（`myui-header__menu` 或频道下拉）里的顶层栏目才是 `classes`；每个栏目页筛选区第一组（slideDown-box 里的类型组）才是该栏目的二级分类 → 进 `filters` 挂 `tid`。
- 四个视频大区是并列独立分类（`vod/type/id/1.html` ~ `4.html`），各有自己的子分类（`vod/show/id/{sid}.html`）；美图/小说是 art 模块（`art/type/id/5.html`、`art/type/id/20.html`），也各有子分类（`art/type/id/{cid}.html`）。
- art 详情页（`art/detail/id/{id}.html`）正文 `div.myui-article__content` 内：含 `<img>` 即为美图图集；纯 `<p>` 文本即为小说全文。同一详情模板，靠 `has_img` 分流。

## URL 路由（实测 wztv8 验证）

```
视频主区列表:      /index.php/vod/type/id/{tid}/page/{pg}.html
视频子分类列表:    /index.php/vod/show/id/{sid}/page/{pg}.html
视频子分类+排序:   /index.php/vod/show/by/{by}/id/{sid}/page/{pg}.html   # by=time|hits|score
美图/小说列表:     /index.php/art/type/id/{cid}/page/{pg}.html
视频详情:          /index.php/vod/detail/id/{id}.html
播放页:            /index.php/vod/play/id/{id}/sid/{sid}/nid/{nid}.html
art详情:           /index.php/art/detail/id/{id}.html
视频搜索:          /index.php/vod/search/wd/{quote(key)}.html
art搜索:           /index.php/art/search/wd/{quote(key)}.html
```

## 核心实现骨架

### 1. id 前缀分发（必须）

列表 `vod_id` 统一加前缀区分模块，`detailContent` 按前缀分流，避免数字 id 冲突：

```python
vod_id = "vod" + vid   # 视频
vod_id = "art" + aid   # 美图/小说
```

### 2. 分类 filters（R星精选写法）

`homeContent` 的 `filters[tid]` 挂该栏目真实二级分类；视频区可追加排序筛选：

```python
filters[tid] = [
    {"key": "tid", "name": "分类", "value": [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for v, n in subs]},
    {"key": "by", "name": "排序", "value": [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]},
]
```

`categoryContent` 从 extend/filter 读 `tid`（子分类 id）与 `by`（排序），无子分类时走主区 type 页。

### 3. art 详情分流（美图 pics / 小说 novel）

```python
content_nodes = tree.xpath('//div[contains(@class,"myui-article__content")]')
has_img = bool(content_nodes[0].xpath(".//img")) if content_nodes else False
if has_img:   # 美图
    vod = {"vod_play_from": "美图浏览", "vod_play_url": f"查看图片$aimgplay${aid}", "vod_player": "pics"}
else:         # 小说全文（单页无章节）
    vod = {"vod_play_from": "小说阅读", "vod_play_url": f"阅读全文$abookplay${aid}", "vod_player": "novel"}
```

**美图图片提取——必须用 onclick 大图，不能用 img/@src**（wztv8 实测教训）：

myui 模板 art 详情页正文图片结构是 `<img src="小图/缩略图域名" onclick="window.open('大图域名/大图路径')">`。`src` 通常是已死的旧图床（如 `mtu.sltusl.com/分类/文件名.jpg`），而 `onclick` 里的 `window.open` 才是当前可用图床的**大图链接**。直接取 `img/@src` 会导致全部图片打不开或显示占位图。

```python
# ❌ 错误：src 是死图床域名（或对替换后域名只回占位图）
imgs = tree.xpath('//div[contains(@class,"myui-article__content")]//img/@src')

# ✅ 正确：提取 onclick="window.open('...')" 里的大图 URL（/i/日期/路径格式）
raw = re.findall(r'src="(https?://[^"]+)"[^>]*onclick="[^"]*window\.open\(([^)]+)\)', seg)
for src_u, alt_u in raw:
    if not re.search(r'\.(jpg|jpeg|png|webp|gif)([?#]|$)', src_u, re.I): continue
    m = re.search(r'(https?://[^\']+)', alt_u)
    u = (m.group(1) if m else src_u).replace('p22.k00ppc.com', 'p23.picd232.cc')
    imgs.append(u)
# playerContent 返回 pics://  +  "&&".join(imgs)
```

注意 play id 必须带 `$aid`，不能只存前缀。`playerContent` 对 `aimgplay$` 二次抓详情提取大图；对 `abookplay$` 二次抓详情取正文文本拼 `novel://{"title":...,"content":...}`。

### 4. 视频播放解析（player_aaaa 大括号计数）

myui 模板播放页 `var player_aaaa={...}` 内含 m3u8 直链，但页面还有 `var maccms={...}` 等其他 JS 对象。**禁止**用 `var\s+player_aaaa\s*=\s*(\{.*?\});` 非贪婪正则（会提前命中 maccms 的 url 字段），必须定位 `player_aaaa` 后用大括号深度计数截取完整 JSON：

```python
idx = html.find("player_aaaa")
start = html.find("{", idx); depth = 0
for i in range(start, len(html)):
    if html[i] == "{": depth += 1
    elif html[i] == "}":
        depth -= 1
        if depth == 0:
            data = json.loads(html[start:i + 1]); pu = data.get("url", ""); break
```

取出的 url 需 `replace("\\/", "/")` 还原，并过 `_validate_media` 门禁（HTTP 200 + `#EXTM3U` / `video/` content-type）后才允许 `parse:0`。

### 5. 列表选择器（myui 模板通用）

```python
nodes = tree.xpath('//a[contains(@class,"myui-vodlist__thumb")]') or tree.xpath('//div[contains(@class,"myui-vodlist__box")]//a')
# 封面取 data-original（懒加载），href 正则 /(vod|art)/detail/id/(\d+)\.html 同时兼容两类
```

### 6. 搜索两套解析

- vod 搜索：`ul.myui-vodlist__media` 内图片卡片，取 `a/@title` + `data-original`。
- art 搜索：纯文字列表（`div.detail` 内 `h4.title a`），无图，取文本；两套结果合并去重返回。

## 关键陷阱

- `_text(node)` 工具函数必须兼容 xpath 返回 list（`if isinstance(node, list): node = node[0] if node else None`），否则 `_text(tree.xpath('//h1'))` 直接抛 `AttributeError: 'list' object has no attribute 'xpath'`，被 except 吞掉后表现为详情空列表。
- **图床失效三连排查（wztv8 实测）**：
  1. **先验证再写死**：替换/新增图床域名前，必须对多个不同路径 + 不存在路径做请求，比较状态码/大小/魔数/md5。若任意路径（含不存在路径）都返回同一张图（同 size 同 md5），那是**占位图**，不是真实图——写死它=所有美图显示同一张图。
  2. **同图双域名双路径**：`img src` 与 `onclick window.open` 可能是两个域名+两种路径格式（如死域 `mtu.sltusl.com/分类/x.jpg` vs 活域 `p23.picd232.cc/i/日期/x.jpg`）。**只替换域名不换路径格式同样拿占位图**；必须整体用 onclick 大图的域名+路径。
  3. **列表封面可作保底**：站内 `/upload/art/` 封面通常 100% 可用且每篇唯一（md5 互不相同）。正文图床全死时可回退列表页封面单图，至少不白屏、不重复。列表页 `href=".../art/detail/id/{aid}.html"` 与 `data-original` 在同一 `<a>` 上，可正则配对。
- **参考源复用优先**：同目录/同站已有可用源（尤其美图能正常显示的历史源），必须优先读取对比其图片提取逻辑——`onclick` 大图提取、域名替换目标、路径格式都是血泪经验，直接复用比从零分析快且准。示例：`夏日.py` 的 `_art_content()` 即正确范式。
- show 分页页与 type 分页页都含"猜你喜欢/推荐"区域，`myui-vodlist__thumb` 选择器会多抓到推荐卡片；用 `seen` 按 vid 去重即可，或限定主列表 `ul.myui-vodlist.clearfix` 范围。
- art 列表小说卡片 `data-original` 为空（无封面），属正常；vod 卡片有封面。详情页小说 `vod_pic` 留空即可。
- MacCMS v10 详情页播放源 tab：`ul.nav-tabs li a[href="#playlist{n}"]` 与 `div#playlist{n}` 一一对应；线路名取 tab 文本，剧集取 tab-pane 内 `a[contains(@href,"/index.php/vod/play/")]`，线路顺序按 tab 首次出现顺序（不能按 sid 数值排）。
- 视频详情若无任何线路（页面异常），兜底给"默认线路 + 播放页 URL"由 playerContent 二次解析；但 playerContent 解析失败时不得 `parse:0` 返回播放页冒充直链。
- 静态检查会拦截固定 `pagecount=1` 与 `parse:0` 无真直链门禁；空结果/异常分支的 pagecount 用当前 pg 兜底，搜索 pagecount 按结果数估算。
- 参考源常见规范欠账：接口签名（`homeContent(self, filter)`、`playerContent(self, flag, id, vipFlags)`）、固定 pagecount=1、parse:0 无门禁——复用参考源时一并修掉，静态检查才能 PASS。

## 完成验证矩阵

- 每个顶层栏目至少测第 1 页；至少一个栏目测子分类筛选（`extend={"tid":...}`）；至少一个视频栏目测排序（`extend={"by":...}`）。
- 视频：抽测详情线路数、剧集数、playerContent 最终 URL 过门禁。
- 美图：详情 `vod_player=pics`，playerContent 返回 `pics://` 且图片数 > 1；**抽样请求首图验证非占位**（HTTP 200 + 不同路径 md5 互不相同 + 大小 > 8KB），不能只看 URL 非空。
- 小说：详情 `vod_player=novel`，playerContent 返回 `novel://` 且 content 非空。
- 搜索：视频与 art 结果合并、去重、id 前缀正确。
- 复用参考源时：签名规范、pagecount、parse:0 门禁全部回归，静态检查 `--final` PASS。
