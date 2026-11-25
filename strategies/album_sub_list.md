# 合集帖分集播放策略模块 v9.5

## 适用特征

- 站点分类里的条目是"合集帖/聚合帖/热榜帖"：详情页正文含多个 `class="btn btn-primary">[点击查看-]标题` 按钮，每个按钮 href 指向一个真实视频详情页。
- 用户需求："点分类列表项 → 进详情 → 详情里有多个视频（分集）→ 点每集播放对应视频，不同条目内容不同"。
- 典型站点：黑料不打烊（每日热瓜 mrrg / 网黄专辑 whzj），Typecho + Mirages 模板。

## 站点结构识别

合集帖详情页正文（itemprop="articleBody"）：
```html
<h2>🔥🔥🔥热榜TOP1：某话题</h2>
<p>文字描述...</p>
<p><img z-image-loader-url="https://pic.xxx/...jpeg"></p>
<p><a href="/archives/220320.html" target="_blank" class="btn btn-primary">点击查看-一颗卵子竟价值五千万美金</a></p>
<hr><span id="menu_index_2" name="menu_index_2"></span>
<h2>热榜TOP2：...</h2>
<p><a href="/archives/220002.html" target="_blank" class="btn btn-primary">被大鸡巴操到胯下求饶</a></p>
```

两种按钮格式（必须都兼容）：
1. 有前缀：`点击查看-标题`（每日热瓜）
2. 无前缀：`标题`（网黄专辑）

## 核心实现

### 1. _subs 提取分集（按钮 → 视频帖URL + 标题）

```python
def _subs(self, html):
    out = []
    seen = set()
    for m in re.finditer(r'<a href="(/archives/\d+\.html)"[^>]*class="btn[^"]*"[^>]*>\s*(?:点击查看-?)?([^<]*)</a>', html):
        u = self._fix(m.group(1))
        t = (m.group(2) or "").strip()
        if not t or len(t) < 2:
            continue
        if len(t) > 20:
            t = t[:20]
        t = t.replace("#", " ").replace("$", " ")
        if u not in seen:
            seen.add(u)
            out.append(f"{t}${u}")
    return out
```

关键点：
- `class="btn[^"]*"` 兼容 `btn` / `btn btn-primary` 等多种值
- `(?:点击查看-?)?` 可选前缀，兼容有/无"点击查看"两种
- 标题去重（seen）、截断（20字）、清理 `#`/`$`（防破坏 vod_play_url 分隔）
- 空标题/过短标题跳过（避免广告按钮 `rel="nofollow"` 误入）

### 2. detailContent 三级分流（优先级严格！）

```python
eps = self._eps(html)    # dplayer 播放器（真实视频帖的多集）
subs = self._subs(html)  # btn 按钮（合集帖分集）
if eps:
    play_url = "#".join(f"第{i+1}集${u}" for i, u in enumerate(eps))
    pf = "默认线路"
elif subs:
    play_url = "#".join(subs)
    pf = "今日合集"
else:
    play_url = ""
    pf = "图文内容"
```

**dplayer(_eps) 必须优先于 btn(_subs)**！
- 原因：真实视频帖详情页也有 btn 链接（推荐/相关），若 _subs 优先会把视频帖误判成分集列表
- 实测：220746（2集 dplayer 视频帖）若 _subs 优先 → 错误显示"今日合集 1 集"；_eps 优先 → 正确"默认线路 2 集"

### 3. 播放时实时解析视频帖

分集 URL 存**视频帖详情页 URL**（`self._fix(/archives/N.html)`），playerContent 收到后实时解析：

```python
def playerContent(self, flag, id, vipFlags):
    url = str(id)
    m = re.search(r"/archives/(\d+)", url)
    if m:
        html = self._get(f"{self.host}/archives/{m.group(1)}.html")
        eps = self._eps(html)
        if eps:
            url = eps[0]
        elif re.search(r"/archives/", str(id)):
            return {"parse": 1, "playUrl": "", "url": "", "header": self._hd()}
    ...
```

- 视频帖详情页有 dplayer → 解析 m3u8 → parse:0 播放
- 无视频（图文帖）→ parse:1 空 url（壳端可跳过/提示）

## 门禁

- 至少测 2 个合集帖：分集数不同（如 16 集 vs 48 集）、标题各异、每集播放 URL 不同
- 至少测 1 个 dplayer 视频帖：确认走"默认线路"多集，不被 btn 误判
- 播放分集第1集、中间集：确认解析到 m3u8（op.udhhzr.cn 等）
- 无视频图文帖：确认 parse:1 空 url 或"图文内容"

## 与队列模式的区别（重要教训）

- ❌ 错误方案：把整个分类列表当"上下文队列"（每集=分类里一个条目，详情重建分类列表）
  - 问题：所有条目的"集数列表"相同（同一分类30集），且播放时递归找子内容会错位到同一视频 → "集数和内容都一样"
- ✅ 正确方案：**合集帖自带分集**（正文 btn 按钮=分集），列表项点进详情直接显示该帖的分集
  - 不同条目分集不同（各自正文按钮不同），天然满足"每天/每个内容不一样"

## 案例参考

- 黑料不打烊 cbdy6.py（400行完整源）：每日热瓜 mrrg + 网黄专辑 whzj 均用此法，实测完美
