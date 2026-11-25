# XBPQ ↔ Python 映射与双层筛选模块 v9.5
把 XBPQ JSON 配置转换为 Python Spider 时，字段级对照与页面层级路由规律。
## 适用特征
- 手头有 XBPQ JSON 配置，要求转 Python。
- 同一分类（女优/主题/tag 大类）分一级列表页和二级内页，筛选值域不同。
- 需要区分「播放数组」和「播放列表」。
## 1. 核心接口对照
| Python 方法 | XBPQ 字段 | 返回值 |
|---|---|---|
| `init(extend)` | 发布页/实时发布页/域名-c | 无 |
| `homeContent` | 分类 + filters 体系 | `{"class":[...],"filters":{...}}` |
| `categoryContent` | 分类url + 数组/标题/图片/链接 | list/page/pagecount |
| `detailContent` | 详情页解析 | `{"list":[vod]}` |
| `playerContent` | 播放链接/跳转播放链接 + 嗅探 | `{parse,url,header}` |
| `searchContent` | 搜索url + 搜索数组 | 同 categoryContent |
| `localProxy` | 图片代理/代理方式 | `[200,类型,bytes,{}]` |
## 2. 语法层映射
| XBPQ | Python 等价 |
|---|---|
| `&&` 正则分割 | `re.split(r'&&', text)` |
| `j:` JSON 提取 | `json.loads(text)` |
| `p:` jsoup 选择器 | `BeautifulSoup.select()` |
| `a&&b` 分割 | `text.split('&&')` |
| `+` 拼接 | `''.join(parts)` |
| `--` 绑定（筛选→URL） | `ext['key']` 覆盖 `tid` |
| `\|\|` 轮询 | `try/except` fallback |
| `@@` 并发 | `ThreadPoolExecutor` |
| `{&&}` 数组不定项 | `finditer` 逐对象 |
| `∬` 多值分隔 | `.split('∬')` / 取第一个 |
| `*` / `**` 通配符 | 单标签内 / 全文档匹配 |
## 3. 播放数组 vs 播放列表（核心概念）
| 概念 | 作用 |
|---|---|
| 播放数组 | 定义**包含所有播放项的容器范围** |
| 播放列表 | 定义**单个播放项的边界** |
引擎行为：先匹配播放数组拿到整个播放区 HTML，再在该片段内反复匹配播放列表；单集匹配 1 次、多集匹配 N 次。
映射到 Python：
```python
pattern = r'"mutex"\s*:\s*true[\s\S]*?"video"\s*:\s*\{\s*"url"\s*:\s*"([^"]+)"'
for m in re.finditer(pattern, html, re.I):
    play_urls.append(m.group(1))
```
## 4. 同 tid 多组同 key 双层筛选
### 问题
同一分类两层页面：一级女优列表页需「女优排序」（名称/热度/更新/影片数），二级某女优影片列表页需「视频排序」（近期最佳/最多观看/最高收藏）。
### 错误做法
只定义一组 `key="sort"`，试图用同一套值域覆盖两级。一级值（如 `avg_videos_popularity`）传给二级页时站点不认识，回落默认排序，筛选失效。
### 正确做法
同一 `tid` 可定义多组同 `key` 的筛选，TVBox 按页面上下文决定命中哪一组：
```python
filters["models"] = [
    {"key": "sort", "name": "排序", "value": [
        {"n": "名称顺序", "v": "title"},
        {"n": "热度优先", "v": "avg_videos_popularity"}]},   # 一级页用
    {"key": "sort", "name": "视频排序", "value": [
        {"n": "近期最佳", "v": "post_date_and_popularity"},
        {"n": "最多观看", "v": "video_viewed"}]},           # 二级页用
]
```
### 后端路由（统一消费 ext['sort']，不区分 key 名）
```python
def _cat_url(self, path, pg, ext):
    base = path.rstrip('/')
    url = base + '/' if str(pg) == '1' else base + '/' + str(pg) + '/'
    if ext and isinstance(ext, dict) and ext.get('sort'):
        url += '?sort_by=' + ext['sort']
    return url
```
### 与 tag 子分类组合
`tag` 大类 filters 可含两组：`type`（子分类切换，`v='tags/'+slug`）+ `sort`（视频排序）。
## 5. 页面类型分支
XBPQ 用 `||` 分支：`"数组": "<article>规则||往期内容--<brick>规则||标签云--<itags>规则"`。
Python 用 `if/elif` 链：
```python
if tid == "archives":   vods = self._parse_archives(html)
elif tid == "tags":     vods = self._parse_tags(html)
else:                   vods = self._parse_article_list(html)
```
## 6. vod_id 打包策略
详情页封面可能缺失时，分类页将封面拼入 `vod_id`（四段）：
```python
vod_id = f"{path}||||{title}||||{sub}||||{pic}"
parts = ids[0].split('||||', 3)
path = parts[0]; cached_pic = parts[3]
```
jable 等详情页 `og:image` 可靠的站点无需打包。
## 7. 门禁
- 同 key 双层筛选必须实测一二级值域各自生效，不得只测一级。
- 参数生效必须通过返回 ID/total/分页差异确认，HTTP 200 不代表参数被采用。
- 转源后分类名单必须能与原站筛选栏第一组逐项对上。