
# ============ 原文件: apple-cms-suggest-limit-翻页真相.md ============

# 苹果CMS suggest 搜索：limit 与翻页真相（2026-08-24 补遗）

> 补充 `references/apple-cms-suggest-search.md` 的最终实测结论（无水印资源网 + 闪电源双站验证）。
> 背景：用户在搜索验证码被锁后追问"还有别的办法能处理翻页问题吗"，全部实测后定稿。

## limit=50 有效

`/index.php/ajax/suggest?mid=1&wd={关键词}&limit=50` 返回 **50 条**（默认 20）。py 源 `searchContent` 用 limit=50 取满。

## 翻页参数全部无效（重要！别浪费时间）

`page` / `pg` / `p` / `offset` / `start` / `pageNum` 全部实测无效：
- page=1/2/3 返回完全相同（id 列表逐位一致）
- pagecount/total 字段是假象：`pagecount=13, total=613` 显示有 13 页，但 page=2 仍返回第 1 页数据
- 原因：suggest 是"搜索框输入提示"接口（home.js 里 `$().autocomplete(...)` 调用），设计上只返回固定前 N 条建议，**服务端不支持翻页**

**结论**：苹果 CMS suggest 搜索最多 50 条，是接口硬限制。用户要求翻页时：①说明是接口限制 ②不要写复杂翻页逻辑 ③分类浏览本身翻页正常（见 `苹果CMS-API源-翻页与补图.md`）。

## 相关站验证

- api.wsyzy.net（无水印资源网）：page 参数无效 ✅
- shandianzy.com（闪电资源网）：page 参数无效 ✅（两站同是苹果 CMS，行为一致）

## 羊壳 require login 坑（再提醒）

搜索返回 vod_id='' 的提示 vod → 羊壳报 "require login [guest]"。suggest 方案返回真实 id，无此问题。搜索别返回空 id 占位项。

# ============ 原文件: apple-cms-suggest-search.md ============

# 苹果CMS 验证码搜索绕过方案（suggest 接口）

> 来源: 无水印资源网（api.wsyzy.net）实战，用户提示 shandianzy.com 的接口后验证成功
> 适用: 苹果 CMS 站点搜索被验证码锁死时

## 问题

苹果 CMS 站点的搜索页（`/index.php/vod/search/wd/xxx.html`）常被**强制验证码**保护：
- py 源请求 → 返回"系统安全验证"页（需人工输验证码）
- 搜索 API（`api.php/provide/vod/?ac=detail&wd=`）→ 返回"暂不支持搜索"
- 验证码服务端校验（`ajax/verify_check`），无法绕过

## 方案：ajax suggest 接口（无验证码！）

苹果 CMS 的**搜索建议接口通常不设验证码**：

```
GET /index.php/ajax/suggest?mid=1&wd={关键词}
```

### 关键参数（血泪教训）
- **必须带 `mid=1`**（mid=模块 id，1=视频）——之前失败就是因为少了它！
- `wd` = 关键词（URL 编码）

### 返回格式（JSON，无验证码）
```json
{
  "code": 1,
  "msg": "数据列表",
  "page": 1,
  "pagecount": 31,
  "limit": 20,
  "total": 613,
  "list": [
    {
      "id": 146895,
      "name": "爱情盲选英国篇第三季",
      "en": "aiqingmangxuanyingguopiandisanji",
      "pic": "https://img1.wsyzy.org/upload/vod/20260819-1/xxx.jpg"
    }
  ]
}
```

## py 源实现

```python
def searchContent(self, key, quick, pg='1'):
    try:
        key = str(key or '').strip()
        if not key:
            return {'list': []}
        # suggest 接口（mid=1&wd=，无验证码）
        r = self.sess.get(
            f"{self.host}/index.php/ajax/suggest?mid=1&wd={quote(key)}",
            timeout=10, verify=False)
        d = json.loads(r.text)
        vods = []
        for it in d.get('list', [])[:30]:
            vods.append({
                'vod_id': str(it.get('id', '')),
                'vod_name': it.get('name', ''),
                'vod_pic': (it.get('pic') or '').replace('\\/', '/'),  # JSON 转义
                'vod_remarks': '',
            })
        return {'list': vods}
    except Exception:
        return {'list': []}
```

### 播放链路
suggest 返回的 `id` 直接用于详情接口：
```python
self._get({'ac': 'detail', 'ids': vid})  # → vod_play_url m3u8 直链
```

## 验证要点

- ✅ 搜索"爱情" → 20 条全部带图
- ✅ 点结果 → 详情（ac=detail&ids=id）→ m3u8 播放
- ⚠️ 番号搜索（如 SSNI）可能 0 条（取决于站点是否有番号资源）

## 常见坑

1. **参数名**：`mid=1&wd=`（不是只有 wd）——不同站 mid 值可能不同（视频模块一般是 1）
2. **JSON 转义**：`pic` 字段的 `\/` 要 replace 成 `/`
3. **无验证码**：suggest 接口本身不触发验证码，直接 JSON
4. 同站验证：shandianzy.com 和无水印资源（api.wsyzy.net）都是苹果 CMS，接口一致

# ============ 原文件: 苹果CMS-API源-翻页与补图.md ============

# 苹果CMS API 源：主分类翻页 + 批量补图（2026-08-23 无水印资源实战定稿）

> 无水印资源网（api.wsyzy.net，苹果 CMS）py 源排障实录。
> 站点结构：主页含 `<script>var maccms={...}</script>`；API `/api.php/provide/vod/`。

## 一、主分类翻页策略（用户"分类页翻几个就看不到了"实证）

**背景**：API `t=主分类id` 返回 0 条（主分类只是容器，视频全挂子分类）→ 主分类必须轮询 CAT_SUBS 子分类合并。

**初版 bug**（每页 24 条 + 翻几页就没）：
```python
per = 30 // len(subs)          # 12 个子分类 → 每类只取 2 条
for sid in subs:
    d = self._get({'ac':'list', 't':sid, 'pg':str(page)})
    for v in d.get('list', [])[:per]: ...   # 固定 2 条/类
```
问题：①每页只 24 条不满 30；②**子分类页数差异巨大**（电影组实测：动作片 287 页 vs Netflix电影仅 7 页）→ 翻到第 7 页后短子分类耗尽，每页只剩 22 条且内容稀疏错乱 = "翻几个就看不到了"。

**正确策略 = 每页取"各子分类第 page 页数据合并，跳过空页，凑满 30 条"**：
```python
if cid in CAT_SUBS:
    vods = []
    for sid in CAT_SUBS[cid]:
        if len(vods) >= 30:
            break
        try:
            d = self._get({'ac': 'list', 't': sid, 'pg': str(page)})
            for v in d.get('list', []):
                vods.append(self._fmt_vod(v))
                if len(vods) >= 30:
                    break
        except Exception:
            pass
    if not vods and page > 1:
        return {'list': [], 'page': page, 'pagecount': page, 'limit': 30, 'total': 99999}
    return {'list': self._fill_pics(vods[:30]), 'page': page, 'pagecount': 9999,
            'limit': 30, 'total': 99999}
```
- 第 N 页 = 所有子分类第 N 页的内容，短子分类空页自然跳过，页数由最长子分类决定（剧情片 1308 页）
- **实测**：电影 1-15 页每页 30 条、页内 0 重复、跨页 0 重复（240 条全部唯一）；6 主分类跨页重复全 0
- **翻过头**（所有子分类该页都空）→ 返回空 list，壳显示"没有了"
- **⚠️ 判定"翻页坏了"的标准**：连续翻 N 页对比每页首页 vod_id 是否变化 + 跨页 id 交集（`len(set(ids1) & set(ids3))`），重复/变少 = 翻页策略问题，不是站点问题

## 二、列表无图 → ac=detail&ids= 批量补图（用户"没图片"/"前几个没有图"实证）

**背景**：`ac=list` 返回字段**没有 vod_pic**（只有 vod_id/vod_name/type_id/vod_remarks/vod_play_from），但 `ac=detail&ids={逗号分隔id}` 带 vod_pic。

**⚠️ 接口限制：ac=detail&ids= 每次最多返回 20 条**——30 个 id 一次请求只回 20 个 → 列表**最前面的** 10 个没补上图（用户"伦理和短剧的前几个没有图"根因）。返回顺序与请求顺序不一致，不能靠截断推断。

**修复 = 按 20 个一批循环请求**：
```python
def _fill_pics(self, vods):
    if not vods:
        return vods
    try:
        pic_map = {}
        ids = [v['vod_id'] for v in vods if v.get('vod_id')]
        for i in range(0, len(ids), 20):          # 每 20 个一批（接口上限）
            batch = ids[i:i + 20]
            try:
                d = self._get({'ac': 'detail', 'ids': ','.join(batch)})
                for v in d.get('list', []):
                    pic_map[str(v.get('vod_id'))] = v.get('vod_pic', '')
            except Exception:
                pass
        for v in vods:
            v['vod_pic'] = pic_map.get(str(v.get('vod_id')), v.get('vod_pic', ''))
    except Exception:
        pass
    return vods
```
实测 6 主分类全 30/30 有图（修复前伦理/短剧只有 20/30）。

**⚠️ 三个都要接 _fill_pics**：homeContent（首页）、homeVideoContent（壳的"推荐"页——调用的是它不是 homeContent，漏接则推荐页 0 图）、categoryContent（主分类合并 + 子分类直查）。

## 三、其他关键点

- **分类树补全法**：主页 HTML `re.findall(r'vod/type/id/(\d+)\.html[^>]*>\s*([^<]{1,15})\s*<', html)` 抓全量（主分类+子分类平铺）；无水印资源实测 6 主类 50 子项（含短剧 9 子、伦理 7 子，初版只写 4 类 33 项被用户打回"分类筛选能否再详细点"）
- **MAIN_CATS 元组顺序 (name, id)**：homeContent/init 必须 `for name, cid in MAIN_CATS` 解包，写反则分类显示 1/2/3/4 点击全 0 条（不报错！）
- **子分类 id 直接 t= 查有效**（54 爽文 9 条、56 港台三级 20 条实证）；主分类 id 是容器 t= 返回 0
- **播放**：线路已是 m3u8 直链 → playerContent 一律 `{'parse':0, 'playUrl':'', 'url':id}`
- **搜索**：见 `references/apple-cms-suggest-search.md`（suggest 接口绕过验证码 + 翻页真相 + 羊壳 require login 坑）

# ============ 原文件: 苹果CMS-API源.md ============

# 苹果 CMS 标准 API 源（无水印资源.py 实战，2026-08-23）

> 站点：`https://api.wsyzy.net`（无水印资源网，苹果 CMS 系统）。成品 `templates/无水印资源.py`。
> 触发：站点主页含 `<script>var maccms={...}</script>` = 苹果 CMS → 有标准采集 API，py 源走 API 比解析 HTML 简单得多。

## 标准 API 端点

```
{host}/api.php/provide/vod/?ac=list&t={type_id}&pg={page}   # 分类列表
{host}/api.php/provide/vod/?ac=detail&ids={id}              # 详情（含线路）
{host}/api.php/provide/vod/?ac=list                          # 首页最新（不带 t）
```

- 列表返回：`{code:1, page, pagecount, total, list:[{vod_id, vod_name, type_id, type_name, vod_pic, vod_remarks}]}`
- 详情返回：`list[0]` 含 `vod_play_from`（线路名如 wsym3u8）+ `vod_play_url`（`HD$https://...m3u8#第01集$https://...` 集数格式，m3u8/mp4 直链）
- 播放：playerContent 直接 `parse=0 + url`（采集线路已是直链）
- 搜索：`ac=detail&wd={词}` → 响应 `"暂不支持搜索"`（该站禁了）；HTML 搜索页 `/index.php/vod/search/wd/{词}.html` → 返回"系统安全验证"验证码页。**搜索默认做不了是站点限制**，但用户会要求"加个弹窗手动输入验证码"→ 见下方"验证码手动输入方案"（2026-08-23 用户明确要求，无水印资源.py 已实现）

## ⚠️ 坑 4：搜索验证码手动输入方案（2026-08-23 用户要求"搜索时加个弹窗，可以手动输入验证码"实现）

**验证码机制**（苹果 CMS 标准，不是该站独有）：
- 触发：搜索页 `/index.php/vod/search/wd/{词}.html` 返回"安全验证"页（`'安全验证' in html` 或 `'mac_verify' in html` 检测）
- 验证码图片接口：**`/index.php/verify/index.html`**（JS 里 `MAC.Verify.Show()` → `maccms.path +'/index.php/verify/index.html?'`；搜索页 HTML 里没有 img，是 JS 动态加载，要自己请求这个接口拿 PNG）
- 校验接口：**`/index.php/ajax/verify_check?type=search&verify={code}`** POST（返回 `{code:1}` 成功 / `{code:1002}` 验证码错误 / PHPSESSID cookie 绑定 session）
- **校验成功后同 session（PHPSESSID）搜索放行** → 用 `requests.Session()` 跨调用保持 cookie 是关键

**py 源实现（用户认可的交互方式：用搜索框当输入框，不弹窗）**：
```
用户第一次搜"爱情" → 检测到验证码 → 下载验证码图存本地（file:// 路径给 vod_pic）
  → 返回单条 vod：vod_name="⚠️ 搜索需验证码：看图后重新输入'关键词 验证码'"
                    vod_pic=验证码图片本地路径  vod_remarks="例: 爱情 1723"
用户看图 → 重新搜索输入 "爱情 1723"（关键词 空格 验证码）
  → searchContent 里 key.rsplit(' ', 1) 拆出 search_key + code
  → POST verify_check?verify={code}（同 session）→ 再搜 → 返回结果
```
- **验证码图片必须存壳能访问的路径**（如 `/data/data/com.9xiu.box/files/cache/verify.png`），vod_pic 用 `file://` 前缀；写失败则 pic 空串不崩
- 校验+搜索**必须同一 session**（`self.sess`），否则 cookie 不共享、校验无效
- 验证码图片随 session 绑定，每次刷新随机（`MAC.Verify.Refresh` 加 `?r=` 随机数）；提交错误后图片作废需重新下载
- **注意**：`rsplit(' ', 1)` 只认"末尾空格+纯数字"为验证码（`parts[1].isdigit()`），普通关键词搜索不受影响

## ⚠️ 坑 5（最终裁决 2026-08-23）：验证码提示 vod 方案在羊壳里触发 "require login [guest]" → 搜索只能返回空

用户实测反馈：**①"require login [guest]"**（羊壳对 `vod_id: ''` 的空提示卡片报错——壳拿空 id 当需登录处理）；**②"手机搜索就触发验证码了，cookie应该不通用？"**（羊壳每次搜索可能重建 Spider 实例，`requests.Session` 的 PHPSESSID 跨调用不共享；文件持久化 cookie 只在壳可写路径存在时有效，不可靠）。

**结论：苹果 CMS 站搜索被验证码锁死时，py 源层面没有可靠方案——不要返回提示 vod（触发 require login），直接 `return {'list': []}`（壳显示"未找到"，不报错），靠分类浏览代替搜索。** 这符合 SKILL.md 陷阱节"搜索验证要试全...测不通就搜索留空——很多源搜索被限流/需登录，分类浏览才是主体"。

**流程修正**：坑 4 的手动输入方案先实现 → 用户实测打回 → 回退 `return {'list': []}`。写同类站直接跳到最终版，不要先做提示 vod。

## ⚠️ 坑 1：主分类 id 在 API t= 参数下返回 0 条

站点导航分类（`/index.php/vod/type/id/1.html`）：1=电影 / 2=电视剧 / 3=综艺 / 4=动漫，子分类 6=动作片 13=国产剧 15=韩剧...

但 **API `t=1`/`t=2` 返回 0 条**——因为视频都挂**子分类** type_id，主分类 id 不是有效过滤值（`t=6`/`t=13`/`t=15` 正常）。

**解法：主分类 = 轮询其子分类合并**
```python
MAIN_CATS = [('电影', '1'), ('电视剧', '2'), ('综艺', '3'), ('动漫', '4')]  # name在前 id在后！
CAT_SUBS = {'1': ['6','7','8',...], '2': ['13','14',...], ...}
# categoryContent 里 cid in CAT_SUBS → for sid in CAT_SUBS[cid]: 每个子分类取前几条合并到 30 条
# 子分类筛选值（ext.get('sub')）→ 直接 t={sub} 单查
```

## ⚠️ 坑 2：MAIN_CATS 元组顺序（分类全空的隐蔽 bug）

`MAIN_CATS = [('电影', '1'), ...]` 是 **(name, id)** 顺序，homeContent/init 里必须 `for name, cid in MAIN_CATS` 解包：
```python
classes = [{'type_id': 'c:' + cid, 'type_name': name} for name, cid in MAIN_CATS]
```
写反成 `for cid, name` 不会报错，但 type_id 拿到的是"电影"字符串、type_name 拿到的是"1"——**分类列表显示 1/2/3/4，点击全 0 条**。症状：子分类筛选正常但主分类全空。排查先打印 homeContent 的 class 看 type_id 是否数字。

## ⚠️ 坑 3：详情页 vod_pic 可能为空

API 列表返回 `vod_pic` 有时是空串（该站实测）——`_fmt_vod` 里 `vod_pic: v.get('vod_pic','')` 兜底即可，不影响播放。

## 数据量验证（判断分类是否废弃）

GET 分类页 HTML 后 `re.search(r'共(\d+)条', html)` 看总数——`共0条` = 站点该分类废弃（91情报局 914/959 同类教训，见 SKILL.md ⑯）。主页导航抓权威分类映射：`<a href="/vod/type/id/{id}.html">名</a>` 全量收集。

## 通用要点

- filters：`filters['c:'+cid] = [{'key':'sub','name':'分类','value':[{'v':'','n':'全部'}+子项]}]`，categoryContent `for d in [filter, extend]` 合并取 sub
- vod_id 用 API 的数字 id（字符串），detailContent 里 `re.search(r'(\d+)', vid)` 兜底提取
- 请求头带移动 UA；苹果 CMS API 一般无防盗链（Referer 可带主页）

# ============ 原文件: 苹果CMS-py源-补图分批与翻页.md ============

# 苹果CMS py源：补图分批 / 主分类翻页 / 灌水去重 / 动态分类（2026-08-24 无水印资源+闪电+18j合并 三站实战）

## 1. ac=detail&ids= 单次最多返回 20 条 → 补图必须分批

**症状**：列表图片缺失呈"前几个/后几个没有"规律（不是全部没图）。
**根因**：`ac=detail&ids={逗号拼接}` 一次最多返回 20 条——请求 30 个 id 只回 20 个，
其余 10 个 id 的 vod_pic 补不上。主分类轮询合并（30 条）时表现最明显。

**正确写法**：
```python
def _fill_pics(self, vods):
    if not vods:
        return vods
    try:
        ids = [v["vod_id"] for v in vods if v.get("vod_id")]
        pic_map = {}
        for i in range(0, len(ids), 20):          # ★ 每 20 个一批
            d = self._get({"ac": "detail", "ids": ",".join(ids[i:i+20])})
            for v in d.get("list", []):
                pic_map[str(v.get("vod_id"))] = v.get("vod_pic", "")
        for v in vods:
            v["vod_pic"] = pic_map.get(str(v.get("vod_id")), v.get("vod_pic", ""))
    except Exception:
        pass
    return vods
```
- 首页 homeContent、**推荐页 homeVideoContent**（壳的推荐页走它！漏接则推荐页 0 图）、
  主分类合并、子分类直查——**所有出列表的地方都要接 `_fill_pics`**
- 检查他人代码（朋友版/大佬版 py）时先看 `_fill_pics` 有没有分批——无水印资源、闪电资源
  （shandianzy）两个站踩了同一个坑

## 2. 主分类翻页策略（每页=各子分类第 N 页合并，凑满 30，跳过空页）

苹果 CMS 主分类 id 在 `t=` 参数下返回 0 条（视频全挂子分类），主分类必须轮询 CAT_SUBS。
**翻页正确姿势**：
```python
if cid in CAT_SUBS:
    vods, seen = [], set()
    for sid in CAT_SUBS[cid]:
        if len(vods) >= 30:
            break
        d = self._get({"ac": "list", "t": sid, "pg": str(page)})  # ★ 每子分类取第 page 页
        for v in d.get("list", []):
            key = (v.get("vod_name") or "").strip()
            if key in seen:      # ★ 站点灌水数据按名称去重
                continue
            seen.add(key)
            vods.append(self._fmt_vod(v))
            if len(vods) >= 30:
                break
    if not vods and page > 1:
        return {"list": [], "page": page, "pagecount": page, "limit": 30, "total": 99999}
    return {"list": self._fill_pics(vods[:30]), "page": page, "pagecount": 9999, ...}
```
- **pagecount 给 9999**（壳显示可继续翻）；不要写 `pagecount: 1`（翻几页就停）
- 错误姿势：每页固定 `per = 30//len(subs)` 各取 2 条 → 短子分类（如 Netflix电影仅 7 页）
  翻几页耗尽 → "翻几个就看不到了"

## 3. 站点灌水数据按名称去重（喜爱夜蒲案例）

**症状**：某分类下全是同一部片子的重复条目（"喜爱夜蒲"×20，id 连续 146104→146085）。
**根因**：站点批量采集失误把同一片源重复入库（纯站点数据问题，不是解析 bug）。
**解法**：主分类合并时 `seen = set()` 按 `vod_name` 去重（见上）。子分类直查（t=56）也重复，
但直查数据量小可接受；主分类合并必须去重否则一页全是同一部片。

## 4. 动态分类写法（18j 大佬版 18J.TV.py，站改版不用改代码）

写死 MAIN_CATS 的 py 源在站点改版后会整体失效。**大佬版（714 行）的做法**：
- init 时从 `/label/sort/`（分类页）动态抓主分类 + 子分类（按位置区间切分，主分类名之间的
  链接即其子分类）
- 从 `/show/1/` 抓排序筛选、`/modol/by/hits_day/` 抓演员地区+排行、`/tags/` 抓标签排序、
  `/t/1/` 抓导航（图文/演员/标签 → nav_entries）
- homeContent 里 `filters` 按 cid 动态挂（sub 分类 + by 排序两组）
- **合并建议**：动态分类（大佬版）+ t26/t30→t33 替换（我的版）双优点合一
  → `templates/18j_合并版.py`（30KB，测试全绿）

## 5. 翻页真相总结（suggest 接口）

苹果 CMS `ajax/suggest?mid=1&wd=` 是**搜索框自动补全**（home.js autocomplete minChars:1），
**天生不支持翻页**（page=1/2/3 返回完全相同，任何参数名 pg/p/offset 都无效）；
`limit=50` 生效（能取 50 条）。搜索页（vod/search/wd/）验证码 + API "暂不支持搜索" 时，
suggest 是唯一无验证码通道 → 搜索返回固定 50 条建议，翻页做不到（接口硬限制，所有苹果 CMS 站一样）。
