
# ============ 原文件: missav-folder写法.md ============

# missav.py 女优/标签 folder 写法（用户验证的标准模式）

> 来源: 用户发的 missav.py（doc_cfcd5e9956e0_missav.py），已存档 `/opt/data/archive/xbpq资料/missav参考.py`
> 用途: py 源里"女优/标签/演员"等二级目录的**标准 folder 写法**，用户多次纠正后确认

## 核心机制（三层结构）

```
一级分类（如"女优一览"）→ categoryContent 返回女优列表（folder 标记）
  ↓ 点击女优（vod_id = href 路径）
categoryContent 判断路径 → 返回该女优的作品列表
  ↓ 点击作品（vod_id = v:xxx 或详情 URL）
detailContent → 播放
```

## 关键写法（对照 missav.py）

### 1. folder 列表项（`_parse_actress_list` 第 434-440 行）

```python
item = {
    'vod_id': href,                  # ★ href 直接作 vod_id（如 /actresses/xxx/）
    'vod_name': name or '女优',
    'vod_pic': cover or '',
    'vod_remarks': ' | '.join(remarks) if remarks else '女优',
    'vod_tag': 'folder'              # ★★ 必须有 vod_tag: 'folder' 标记！
}
```

**关键点**：
- `vod_id` 用 **href 路径**（不是 dir_ 前缀、不是自定义编码）——壳识别路径后点击调 **categoryContent**
- **必须带 `vod_tag: 'folder'`**——羊壳靠这个识别文件夹，没有它点击会被当视频直接播放！

### 2. categoryContent 路径判断（第 369-370 行）

```python
if tid.startswith('http') or '/actresses/' in tid:
    return self._get_actress_videos(tid, pg, ext)   # 女优详情 → 作品列表
```

通用写法：`if tid.startswith('/actor/detail/') or tid.startswith('/s/tag/'):` 判断路径 → 请求该页 → 解析列表返回。

### 3. 双保险：detailContent 也兼容

```python
if vid.startswith('/actor/detail/') or vid.startswith('/s/tag/'):
    try:
        return self.categoryContent(vid, 1, '', {})   # 防壳调 detailContent
    except Exception:
        return {'list': []}
```

## 18J 站应用实例（已验证）

```python
# 女优列表项
{'vod_id': '/actor/detail/zhuimingkong/', 'vod_name': '椎名空',
 'vod_pic': '...', 'vod_remarks': '女优', 'vod_tag': 'folder'}

# 标签列表项
{'vod_id': '/s/tag/%E7%B4%A0%E4%BA%BA/', 'vod_name': '素人',
 'vod_pic': '', 'vod_remarks': '标签', 'vod_tag': 'folder'}

# categoryContent 处理
if tid.startswith('/actor/detail/') or tid.startswith('/s/tag/'):
    html = self._req(self.host + tid)
    if '/s/tag/' in tid:
        return {'list': self._parse_videos(html), ...}   # 标签视频列表
    # 女优：先取名字 → 搜索该演员所有作品 → 过滤含名字 → 返回列表
```

## 常见坑（用户纠正过的）

1. ❌ 把 folder 处理放 detailContent 返回多 vod → 壳只取第一个/直接播放
2. ❌ 用 dir_ 前缀但没加 vod_tag: 'folder' → 壳不识别文件夹
3. ✅ 正确：href 作 id + vod_tag folder + categoryContent 判断路径（missav/404xav 都是这个模式）
4. 女优详情用"搜索"方式（先取 h1 名字 → `/cn/s/page/1/wd/{名字}/`）能拿到全部作品，且要**过滤标题含名字**的结果（防无结果时返回热门填充）
5. **⚠️ href 若已含 `.html` 后缀（如 `/type/actor/5849.html`），categoryContent 里直接 `self.host + tid`，不要再拼 `.html`**（91情报局 2026-08-23 实证：拼了变 `5849.html.html` → 404 → 点开空白）。分页才去后缀：`base = tid[:-5] if tid.endswith('.html') else tid.rstrip('/')`，第 2 页起 `{base}/{pg}.html`。对照 missav：`vod_id = href`，`_get_actress_videos` 里 `url = actress_url` 直接请求，不二次拼接
6. **folder 作品分页 URL 与第 1 页不同**（91情报局 实证）：第 1 页 `/type/actor/5849.html`（无页码段），第 2 页 `/type/actor/5849/2.html`——`pg==1` 用原路径，`pg>1` 去 `.html` 加 `/{pg}.html`

# ============ 原文件: missav-写法参考.md ============

# MissAV py 源写作步骤（未完结）

> **状态：播放加密未解完**——ts/key CDN (`tsnew.cpckgr.cn`) 直连 403，需走 `localProxy` 代理。已识别方案，未交付。
> 参考：`cache/documents/91hub2.py`(m3u8+ts+key 代理) + `51吃瓜.py`(AES 图片解密) + `51短剧用久发布站源码.json`(永久/实时发布站解析)

---

## 域名解析（3 个发布站）

- `https://missavt01.netlify.app/`
- `https://missavt01.github.io`
- `https://missavt01.pages.dev/`

HTML 都只有 683 字节，跳转到 `publish.js`，里面随机组合：
- **前缀**：`abcdefg` 之类 5 字符
- **主域名**：3 个随机取一个 → 拼成 `前缀.主域名`

**问题**：主域名本机连不上（阿里云上海 DNS 解析失败），需 shell 端代理能解析的域名直接传入，或在 ext 里硬编码。

---

## 图片解密（瓜系，来自 51吃瓜.py）

- AES-128-CBC，key=`f5d965df75336270`，iv=`97b60394abc2fbe1`
- 走 `localProxy(type=pic)` 或 51吃瓜的 `type=img`，`_aes_decrypt` 解密后返回 `[200, mime, data]`
- **注意**：源码里 `.jpeg` 结尾的图片需要特殊处理（详见 `cache/documents/51短剧图片映射.json`）

---

## 播放解密（91hub 同款，来自 91hub2.py）

**91hub2 已验证可工作的方案**：
- m3u8 里 `#EXT-X-KEY:METHOD=AES-128,URI="key_url"`
- ts 段也 AES-128-CBC 加密，用 key_url 解出 key 后逐段解密
- 全部走 `localProxy`：
  - `type=m3u8` → 解析 m3u8，把 ts 地址改写为代理 URL
  - `type=ts` → 解密 ts 段
  - `type=mkey` → 返回 AES key

**MissAV 待办**：
- m3u8 来源在 `data-url`（详情页 `#app` 里 `__NEXT_DATA__` JSON 中）
- ts/key CDN 是 `tsnew.cpckgr.cn`，直连 403，必须走代理

---

## 分类体系

按 51短剧 思路：
- 首页 `sort/renew`（最近更新）、`sort/hot`（最热）
- 分类：`jp/censored`、`jp/chinese-subtitle`、`cn/madou`、`cn/91-studio`、`uncen/fc2`、`uncen/1pondo`、`amateur/siro` 等
- 女优：`actresses/new`、`actresses/hot`
- 标签：`tags/hot`、`tags/letter/a` 等

---

## 筛选参数

TVBox 壳端筛选走 **`ext` 字符串**（json），不是 `filter` 字典。已确认：
- 壳端调用 `categoryContent(cid, pg, {}, '{"cateId":"xxx"}')`
- 代码里解析 `ext`：先 `json.loads(ext)`，再兜底 `filter`

---

## 待办（未解完）

- [ ] ts/key CDN 403 → 走 `localProxy(type=m3u8)` 代理，参考 `cache/documents/91hub2.py` 实现
- [ ] 域名自动解析 → ext 传真实域名兜底
- [ ] m3u8 直链是否被 CDN 校验 Referer → 加 `Origin/Referer` header
# ============ 原文件: missav-开发记录.md ============

# MissAV py 源开发记录

> 完整交付：`/opt/data/out/missav.py`（484 行）
> 参考源码：`cache/documents/51短剧图片映射(1).json` + `doc_19e068300732_源码.txt` + `doc_db36f36ef9d3_missavt所需源码与要求.json`

---

## 发布站结构

3 个发布站 HTML 完全一样（683 字节），跳转逻辑在 `publish.js`：
- `https://missavt01.netlify.app/`
- `https://missavt01.github.io`
- `https://missavt01.pages.dev/`

**子域名**：5 字符随机前缀（`abcdefghjkmnpqrstuvwxy0123456789`）+ 3 个主域名随机组合：
- `kibsbvpft.cc`
- `fvtweuyk.cc`
- `gcqsnwaam.com`

永久站：`missavt28.com` / `missavt.com`（代理 DNS 常解析不出来）

---

## 域名解析（最关键）

**代理 DNS 常解析不出 MissAV 域名**——飞牛NAS 代理（192.168.31.66:7890）对 `*.cc` / `*.com` 域名 DNS 返回空。本机测试同样失败。

**`_get_domain()` 并发策略**（484 行版本）：
- 每个后缀 8 个前缀，共 24 个候选域名
- 代理探测：本机 7890/1080/1087 + 飞牛NAS 7890/7891/1080 + 10.0.0.1 + 环境变量 HTTPS_PROXY
- 并发 15 worker，超时 25 秒

**如果解析仍失败**：壳端导入时 ext 传真实域名（如 `https://scu.fvtweuyk.cc`），跳过解析。

---

## 图片解密（瓜系）

AES-128-CBC，固定密钥：
- key: `f5d965df75336270`
- iv: `97b60394abc2fbe1`

图片直链从 `<img data-src="...">` 提取，走 `localProxy(type=pic)` → `proxyPic()` → `aesimg()` 解密。

---

## 播放链路（关键坑）

**M3U8 直链**，无 eval 加密。详情页 data-url 格式：
- 推荐/sort：`https://jw-hls.wgmyvq.cn/m3m/{hash}`（无 `.m3u8` 后缀）
- 其他分类：`https://jw-hls.wgmyvq.cn/cloud_01/upload/video/.../{name}.m3u8?auth_key=***

**`data-url` 正则**必须匹配到 `>`，不能只匹配 `[^"\x27]+`——URL 里含 `&` 会被截断：
```python
# 正确：支持 & 在 URL 里，匹配到 > 或 <
um = re.search(r'data-url=["\x27]([^"\x27]*\.[mM]3[uU]8[^"\x27<>]*)["\x27]', html)
```

---

## **致命坑：ts 段 CDN 反爬导致 m3u8 代理方案完全不可行**

MissAV m3u8 里 ts 段走 `tsnew.cpckgr.cn`，**走代理/直连/各种 Referer 全部 403**。

我试了 50+ 种方式：
- m3u8 代理 → 改写 ts 走 `localProxy(type=ts)` → 代理拉 ts → **403**
- 各种 Referer 组合 → **403**
- 各种 Cookie / X-Forwarded-For / Host 头 → **403**

**结论**：ts 段反爬是 CDN 层面，py 端无法绕过。壳端播放器访问 ts 段时自带的环境头可能不同——推荐视频能放是因为 CDN 缓存命中。

**不要尝试加 m3u8 代理**，直接返回直链。

---

## localProxy 只保留图片代理

```python
def localProxy(self, params):
    t = params.get('type')
    if t == 'pic':
        return self.proxyPic(params)
    return [200, 'text/plain', '']
```

**不能调用已删除的方法**——之前我删了 `proxyM3u8`/`proxyTs` 但 `localProxy` 还引用它们，导致 shell 崩溃→空数据。

---

## 分类/筛选

7 个 class：sort/jp/cn/uncen/amateur/actresses/tags
筛选参数 TVBox 主流走 `ext`（json 字符串），兼容 `filter`（字典）兜底：
```python
f = {}
if isinstance(ext, dict): f = ext
elif isinstance(ext, str): f = json.loads(ext)
if not f:
    if isinstance(filter, dict): f = filter
```

---

## vod_play_url 格式

```
{vod_name}${m3u8_url}
```

不带任何自定义 scheme（`m3u8://` 等 shell 不认识），保持纯 URL。
# ============ 原文件: missavt-写作参考.md ============

# MissAVt Spider 写作参考

> MissAV 是 MissAVt（missavt28.com / missavt.com）的壳源，动态域名，Nuxt SSR，图片走"瓜系解密"。
> 完整 py 文件：`/opt/data/out/missav.py`（499 行）。
> 同源：51短剧 v4、91hub2——三站图片 AES 解密 key/iv 相同（`f5d965df75336270` / `97b60394abc2fbe1`）。

---

## 1. 域名获取（动态域名体系）

### 域名结构
```
{5字符前缀}.{3个主域名之一}/{路径}
```

- **前缀**：从 `abcdefghijklmnopqrstuvwxyz0123456789` 随机取 5 字符（不含 `i/l/o/0/1`）
- **3 个主域名**：`kibsbvpft.cc` / `fvtweuyk.cc` / `gcqsnwaam.com`
- **3 个发布站**（3 个 HTML 完全一样，跳转在 `publish.js` 里）：
  - `https://missavt01.github.io`
  - `https://missavt01.netlify.app`
  - `https://missavt01.pages.dev`
- **2 个永久站**：`missavt28.com` / `missavt.com`

### 发布站源码
`<head>` 内 `<script src="/publish.js"></script>`，publish.js 内包含：
- 19 个大学代号前缀（thu/pku/fdu/sjtu/zju/xmu/hitsz/hust/sdu/nju/ustc/xmu/tju/zju/scu/sdu/nju/xmu/hitsz 等）
- 随机选 1 个前缀 + 1 个主域名 → 跳转

### 后端域名解析逻辑（_get_domain）

**并发 10 worker**，从 3 个发布站取后缀 → 随机前缀组合 → 并发探测 → 哪个先通用哪个。

代理探测顺序（`_get_domain` 内）：
1. `127.0.0.1:7890` / `127.0.0.1:1080` / `127.0.0.1:1087`（壳端常见代理端口）
2. `192.168.31.66:7890`（飞牛NAS mihomo，本机/壳端都有时备用）
3. 如果都没代理，**直连兜底**（部分壳端环境直连可用）

并发 10 worker + 12 秒超时，实测 5~9 秒出域名。

**关键优化**：壳端等待时间通常不够，**推荐导入时通过 `ext` 传真实域名**跳过解析：
```
ext: https://scu.fvtweuyk.cc
```
这样 1 秒开。

---

## 2. NUXT_DATA 解析（devalue 编码）

MissAV 用 Nuxt SSR，页面里 `__NUXT_DATA__` 是 devalue 编码格式，不是标准 JSON。

### 结构
```
__NUXT_DATA__ = ["ShallowReactive", 1]
```
- 第一个元素 `"ShallowReactive"` 是**字符串标记**（不是索引！）
- 第二个元素 `1` 是索引，指向 NUXT_DATA 数组里的位置

### 解引用递归
```python
def get(obj, idx, memo):
    if isinstance(obj, list) and obj and isinstance(obj[0], str) and obj[0] == "ShallowReactive":
        idx = obj[1]
        return get(data, idx, memo)
    if isinstance(obj, list) and len(obj) == 2 and isinstance(obj[1], int):
        return memo[obj[1]] if obj[1] in memo else None
    return obj

# 调用时必须加 memo 防循环引用
memo = {}
memo[idx] = get(data, idx, memo)
```

**陷阱**：
- `["ShallowReactive", idx]` 第一个是**字符串不是索引**（我之前写反过）
- NUXT_DATA 数组约 830~900 个元素，索引可达 800+
- **不加 memo 会死循环**（页面里常有循环引用）
- 用户发的源码文件里 `\n` `\r` 是**字面转义字符**，测试时需 `html.replace('\\n','\n')`；`fetch()` 拿真页面不需要

---

## 3. 分类体系（7 大类 + 子分类）

**URL 结构**：
- `/{分类}/{排序或子分类}/` 首页
- `/{分类}/{排序或子分类}/{页码}/` 分页

| 分类 ID | URL 路径 | 筛选字段 |
|---|---|---|
| `sort` | `/sort/{by}/` | `by`: renew/hot/month_hot/ten_minutes/month_comment |
| `jp` | `/category/{cateId}/` | `cateId`: censored/chinese-subtitle/renqishunv/zhifuyouhuo/tiaojiaoSM/jiatingluanlun |
| `cn` | `/category/{cateId}/` | `cateId`: madou/swag/sweet-heart-vlog/ed-mosaic/douyin/91-studio/mr-rabbit/domestic-media/xingbatanhua |
| `uncen` | `/category/{cateId}/` | `cateId`: uncensored-leak/fc2/tokyohot/marriedslash/heyzo/reducing-mosaic/10musume/pacopacomama/xxx-av/caribbeancompr/caribbeancom/1pondo |
| `amateur` | `/category/{cateId}/` | `cateId`: siro/luxu/gana/prestige-premium/s-cute/ara |
| `actresses` | `/actresses/{by}/` | `by`: new/num/hot/name |
| `tags` | `/tags/{cateId}/` | `cateId`: hot/letter/a~z/# |

**actor 二级**（点进女优）：`vod_id = "actress/{中文名}"`，`tag = "folder"`
**tag 二级**（点进标签）：`vod_id = "tag/{英文名}"`，`tag = "folder"`

---

## 4. 图片解密（"瓜系解密"，与 51hub v4 同款）

### AES-128-CBC 固定密钥
```python
IMG_KEY = b'f5d965df75336270'
IMG_IV  = b'97b60394abc2fbe1'
```

### 流程
1. NUXT_DATA 里视频对象的 `cover` 字段是 base64 编码的加密数据
2. base64 解码 → AES-128-CBC 解密 → 得到 PNG/JPG 二进制
3. 通过 `localProxy` 的 `pic` 类型返回：`[200, mime, data]`

### 视频卡片结构（首页/分类页）
```html
<div class="video-item" ...>
  <a href="/watch/mdog-005/" data-url="https://jw-hls.wgmyvq.cn/m3u8/xxx" ...>
    <img class="video-preview-img" data-src="BASE64加密数据" />
    <div class="video-title">男性高潮 双重卡司 ...</div>
  </a>
</div>
```

关键字段：`href`（相对路径）/ `data-src`（加密图片 base64）/ `data-url`（**播放 m3u8 直链**）

**陷阱**：部分视频 `data-src` 为空，需要**跳过或 fallback 到默认图**。

---

## 5. 播放解密（**核心，最容易搞错**）

### 5.1 关键发现

**MissAV 播放不是 eval 加密，不是 91hub 同款**！用户给的"eval packer 解码"要求**是误贴了 91hub 的说明**。

MissAV 首页/分类页 `data-url` 字段里**直接是 m3u8 CDN 直链**：
```
data-url="https://jw-hls.wgmyvq.cn/m3u8/a374bf06ddb200947f3e27a3ea7525cc9ef5a4f39f2?auth_key=..."
```

### 5.2 data-url 正则陷阱

**旧写法**（错）：
```python
re.search(r'data-url=["\x27]([^"\x27]+)["\x27]', html)
```
在 `&` 处截断，丢掉 `.m3u8` 后缀和 `auth_key` 参数。

**正确写法**：
```python
re.search(r'data-url=["\x27]([^"\x27<>]*\.[mM]3[uU]8[^"\x27<>]*)["\x27]', html)
# 或 fallback
re.search(r'data-url=["\x27]([^"\x27<>]+)["\x27]', html)
```

### 5.3 m3u8 里的 ts 段

m3u8 直链可达（200），但里面有：
```
#EXT-X-KEY:METHOD=AES-128,URI="https://tsnew.cpckgr.cn/hc104/m3u8/enc.key?auth_key=xxx",IV=0x64cf692cebc516e4a86ac6081aae50ce
#EXT-X-MEDIA-SEQUENCE:1
tsnew.cpckgr.cn/hc104/m3u8/seg_0.ts?auth_key=xxx
```

**shell 直接放 m3u8 可以**（壳端播放器大多能自动解析 ts AES 段）。

### 5.4 **陷阱：不要用自定义 URI scheme**

我试过加 `m3u8://` 前缀做标记，**壳端不识别，直接超时**。

正确做法：**直接返回完整 URL**，不要加任何 scheme 前缀：
```python
"vod_play_url": vod_name + "$" + play_url   # 正确
# 不要
"vod_play_url": vod_name + "$m3u8://" + play_url   # 错，超时
```

如果必须走代理（比如 shell 不支持 m3u8 里的 ts），可以**通过 m3u8 URL 特征判断**而不是自定义 scheme。

---

## 6. TVBox categoryContent 参数传递（**最容易踩坑**）

**两种壳传参方式**，必须都兼容：

| 壳类型 | `ext` 参数 | `filter` 参数 |
|---|---|---|
| TVBox 主流 | `ext = {"cateId":"censored"}` (dict 或 json 字符串) | `filter = {}` (空) |
| 部分壳 | `ext = ""` (空串) | `filter = {"cateId":"censored"}` (dict) |

**正确写法**（优先 ext，filter 兜底）：
```python
def categoryContent(self, cid, pg, filter, ext):
    f = {}
    if isinstance(ext, dict):
        f = ext
    elif isinstance(ext, str) and ext and ext not in ('{}','null','undefined'):
        try: f = json.loads(ext)
        except: pass
    if not f:
        if isinstance(filter, dict):
            f = filter
        elif isinstance(filter, str) and filter and filter not in ('{}','null','undefined'):
            try: f = json.loads(filter)
            except: pass
    # 用 f.get() 取筛选值
```

**我犯了两次错**：
1. 第一版用 `ext.get('by')` —— shell 传 filter 字典，ext 是空串，`.get()` 永远返回默认值 → **筛选点不动**
2. 第二版改成只用 `filter` —— 有些壳传 ext 字符串，filter 是空 dict → **也没数据**
3. 第三版双兼容 ✅

---

## 7. 完整 py 结构（499 行）

```python
class Spider(Spider):
    IMG_KEY = b'f5d965df75336270'
    IMG_IV  = b'97b60394abc2fbe1'
    PREFIX_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789'

    init(extend)              # 域名解析或直接用 ext 传入域名
    _get_domain()             # 并发域名解析（10 worker + 代理探测）
    _fetch_suffixes()         # 抓 3 个发布站的 publish.js
    fetch(url)                # 带 proxy fallback 的 GET
    _fetch_with_proxy(url)    # 代理重试

    homeContent(filter)       # 返回 7 class + 全部 filter
    homeVideoContent()        # 首页推荐

    categoryContent(...)      # 分 7 大类，双兼容 ext/filter
    detailContent(ids)        # 抓 data-url 直链，data-src 抓图
    playerContent(flag, id)   # 直接返回 m3u8 直链

    parse_videos(html)        # 视频卡片解析（video-item / video-preview-img / data-src / data-url / href）
    parse_actors(html)        # 女优列表解析
    parse_tags(html)          # 标签列表解析

    localProxy(params)        # type=pic 走 AES 解密，其他返回空
    proxyPic(params)          # base64 解码 → AES-128-CBC 解密
    _aes_decrypt(encrypted)   # 固定 key/iv
    _detect_ext(data)         # 自动识别 png/jpg/gif/webp

    isVideoFormat(url)        # .m3u8/.mp4/.ts/.flv 判定
    manualVideoCheck()        # 返回 True（不走二次检测）
```

---

## 8. 关键坑位汇总

| 坑 | 现象 | 修复 |
|---|---|---|
| 自定义 scheme | 播放超时 | 直接返回完整 URL，不加 `m3u8://` 之类前缀 |
| data-url 正则 | 只取到一半 URL | 用 `[^"\x27<>]*` 替代 `[^"\x27]+`，允许到 `>` 为止 |
| NUXT_DATA devalue | 解析失败/死循环 | `["ShallowReactive", idx]` 第一个是字符串标记；必须加 memo 防循环 |
| 筛选参数 | 点筛选没变化 | 双兼容 `ext` (dict/json str) + `filter` (dict) |
| 域名解析 | shell 超时 | 并发 10 worker；壳端导入时 ext 传真实域名跳过解析 |
| 测试文件 `\n` 字面 | 正则匹配失败 | `html.replace('\\n','\n')` 还原；真页面 fetch 不需要 |
| `data-src` 为空 | 部分视频没图 | 解析函数内跳过空 `data-src`，或 fallback 默认图 |
| m3u8 里 ts AES 段 | shell 直接放可玩 | 不需要额外代理解密 ts 段（除非壳端不支持） |
# ============ 原文件: missavt-写作步骤.md ============

# MissAV(missavt) py 源完整写作步骤

> 参考：`cache/documents/51短剧用久发布站源码(1).json`（3个发布站同源 publish.js）+ `51短剧图片映射(1).json`（列表页源码）+ `missavt所需源码与要求.json`（详细分类结构）+ `91hub2.py` / `51吃瓜.py` / `91hub.py`（解密参考）
> 交付：`/opt/data/out/missav.py`（535 行）

---

## 第 1 步：域名自动解析（从 3 个发布站动态取后缀）

### 1.1 发布站同源
`missavt01.netlify.app` / `missavt01.github.io` / `missavt01.pages.dev` 三个发布站**代码完全一致**，`publish.js` 结构：

```js
var urls = ['kibsbvpft.cc', 'fvtweuyk.cc', 'gcqsnwaam.com'];
var JumpPage = "https://missavt28.com";
var foreverUrls = ["https://missavt.com", JumpPage];
```

### 1.2 后缀动态提取
访问任一发布站的 `publish.js`，正则抓取 `['\"]([^'\"]*?\.(?:cc|com))['\"]`。

### 1.3 前缀随机生成
从 `abcdefghijklmnopqrstuvwxyz0123456789` 随机取 5 个字符。

### 1.4 域名结构
```python
domain = "https://" + prefix + "." + suffix + "/"
# 例：https://x7k9j.kibsbvpft.cc/
```

### 1.5 域名轮询策略（⚠️ 必用并发，避免 58s 超时）

**串行逐个测 58 秒（羊壳会超时）**——必须用 `ThreadPoolExecutor` 并发，压到 5~9 秒：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# 构造候选域名池
candidates = []
for suffix in suffixes:
    for _ in range(2):
        prefix = ''.join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5))
        candidates.append("https://" + prefix + "." + suffix + "/")

# 代理端口探测（本机 + 飞牛NAS）
proxies = []
for port in ['7890', '1080', '1087']:
    try:
        self.session.get("http://127.0.0.1:" + port, timeout=1)
        proxies.append({"http": "http://127.0.0.1:" + port, "https": "http://127.0.0.1:" + port})
    except Exception: pass
try:
    self.session.get("http://192.168.31.66:7890", timeout=1)
    proxies.append({"http": "http://192.168.31.66:7890", "https": "http://192.168.31.66:7890"})
except Exception: pass
if not proxies:
    proxies.append({})  # 直连兜底

def try_one(item):
    domain, p = item
    try:
        r = self.session.get(domain, headers={"User-Agent": "Mozilla/5.0"}, timeout=3, verify=False, proxies=p)
        if r.status_code == 200 and ('MissAVt' in r.text or 'video-item' in r.text):
            return (domain, p)
    except Exception: pass
    return None

with ThreadPoolExecutor(max_workers=10) as ex:
    futures = [ex.submit(try_one, (d, p)) for d in candidates for p in proxies]
    for f in as_completed(futures, timeout=12):
        result = f.result()
        if result:
            self.session.proxies = result[1]
            return result[0]
return ""
```

- **fallback**：`init(extend)` 支持用户传真实域名，跳过域名解析

---

## 第 2 步：图片解密（瓜系 AES，与 91hub/51吃瓜 同款）

**密钥**：key = `b'f5d965df75336270'`，iv = `b'97b60394abc2fbe1'`，AES-128-CBC + PKCS7 unpad

**图片位置**：`img data-src="https://image.cpckgr.cn/upload_01/..."`

**实现**：`data-src` 提取 → `_img()` base64 编码拼 `localProxy(type=pic)` URL → 壳端 `localProxy` 收到 → base64 解码 → GET 图片 → AES 解密 → 返回

```python
def proxyPic(self, params):
    url = base64.b64decode(params['url']).decode('utf-8')
    r = requests.get(url, headers=self.header, timeout=15, verify=False)
    data = AES.new(IMG_KEY, AES.MODE_CBC, IMG_IV).decrypt(r.content)
    return [200, 'image/jpeg', unpad(data, AES.block_size)]
```

---

## 第 3 步：视频列表解析

**页面结构**（`<div class="video-item">` 到 `<div class="video-preview w-full h-full left-0 top-0">`）：

```html
<div class="video-item">
  <a href="/watch/1pondo_071217_551/">
    <div class="poster" data-url="https://jw-hls.wgmyvq.cn/.../xxx.m3u8?auth_key=...">
      <img data-src="https://image.cpckgr.cn/upload_01/...jpeg"
           alt="标题">
    </div>
  </a>
</div>
```

**字段提取**：
- `vod_id` = href 里 `/watch/xxx/` 中的 xxx（正则：`/watch/[^"\x27]*/`）
- `vod_name` = `img alt` 属性
- `vod_pic` = `img data-src` → 走 `_img()` 加密代理
- **`data-url`** = m3u8 直链，**详情页直接取**（无需 eval 解密）

---

## 第 4 步：分类体系

### 4.1 近期更新
`{host}sort/{by}/{page}/`，筛选 `renew`（最近更新，默认）/`hot`/`month_hot`/`ten_minutes`/`month_comment`

### 4.2 日本AV / 国产AV / 无码AV / 素人AV
`{host}category/{cateId}/{page}/`

| 分类 | cateId |
|---|---|
| 日本AV | censored / chinese-subtitle / renqishunv / zhifuyouhuo / tiaojiaoSM / jiatingluanlun |
| 国产AV | madou / swag / sweet-heart-vlog / ed-mosaic / douyin / 91-studio / mr-rabbit / domestic-media / xingbatanhua |
| 无码AV | uncensored-leak / fc2 / tokyohot / marriedslash / heyzo / reducing-mosaic / 10musume / pacopacomama / xxx-av / caribbeancompr / caribbeancom / 1pondo |
| 素人AV | siro / luxu / gains / prestige-premium / s-cute / ara |

### 4.3 女优（二级文件夹）
一级：`{host}actresses/{by}/{page}/`，筛选 `num/new/hot/name`
二级：`{host}actress/{urlencode(女优名)}/{page}/`

**关键**：`vod_id="actress/" + name`，`vod_tag="folder"`；二级页 href 里的中文名要 `urllib.parse.quote` 编码。

### 4.4 标签（二级文件夹）
一级：`{host}tags/{cateId}/{page}/`，筛选 `hot`/`letter/a`~`letter/z`/`letter/%23`
二级：`{host}tag/{urlencode(标签名)}/{page}/`

### 4.5 搜索
`{host}search/{urlencode(key)}/{page}/`

### 4.6 筛选参数路由（⚠️ 必测！壳端 ext vs filter 传参不一致）

壳端 `categoryContent(cid, pg, filter, ext)` 的 4 个参数，**不同壳实现传参规则完全不同**：

| 壳实现 | 筛选值放哪 | filter 类型 | ext 类型 |
|--------|----------|------------|---------|
| TVBox 主流 | `ext` | `{}` 空 dict | `"{}"` 空字符串 或 `{"cateId":"xxx"}` JSON 字符串 |
| 部分影视壳 | `filter` | `{"cateId":"xxx"}` dict | `""` 空字符串 |
| 少量壳 | 都在 `ext` | 任意 | dict |

**结论：筛选值必须先从 `ext` 取，再从 `filter` 兜底，两个参数都要处理**：

```python
def categoryContent(self, cid, pg, filter, ext):
    page = int(pg) if pg else 1
    f = {}
    if isinstance(ext, dict): f = ext
    elif isinstance(ext, str) and ext and ext not in ('{}', 'null', 'undefined'):
        try: f = json.loads(ext)
        except Exception: pass
    if not f:
        if isinstance(filter, dict): f = filter
        elif isinstance(filter, str) and filter and filter not in ('{}', 'null', 'undefined'):
            try: f = json.loads(filter)
            except Exception: pass
    by = f.get('by', 'renew')
    c  = f.get('cateId', 'default')
```

**⚠️ 常见翻车（2026-08-26 MissAV 排障实证）**：
- 只写 `ext.get('by')` → 壳把筛选走 filter，ext 空 → 所有分类返回默认内容（"内容都一样"）
- 只写 `filter.get('by')` → 壳把筛选走 ext → 整个源没数据（"现在没数据了"）
- **两种都写就 100% 兼容**

**⚠️ 交付前必测 3 种调用方式**：
```python
s.categoryContent("jp", "1", {}, '{"cateId":"censored"}')   # TVBox 主流
s.categoryContent("jp", "1", {"cateId":"censored"}, "")     # 部分壳
s.categoryContent("jp", "1", {}, "")                        # 空筛选
```
三种都要返回正确分类内容才算通过。

---

## 第 5 步：详情与播放

### 5.1 详情页
`{host}watch/{vod_id}/`

### 5.2 播放直链（**优先**）
详情页 HTML 里 `<div class="poster" data-url="https://jw-hls.wgmyvq.cn/...m3u8?auth_key=...">` 直接就是 m3u8 直链，**无需解密**。

**⚠️ 正则必用 `.m3u8` 锚点兜底，不能只用 `[^"\x27]+`**（2026-08-26 MissAV 播放超时根因实证）：

```python
# ❌ 错误：在 URL 的 & 处截断，丢了 m3u8 后缀和 auth_key 参数
um = re.search(r'data-url=["\x27]([^"\x27]+)["\x27]', html)
# 匹配结果: .../853c9c26bc9a8d4c744e48b3738c37a0  ← 截断

# ✅ 正确：.m3u8 作为锚点，到 .m3u8 后允许任意字符（除 > 和引号）
um = re.search(r'data-url=["\x27]([^"\x27]*\.[mM]3[uU]8[^"\x27<>]*)["\x27]', html) \
   or re.search(r'data-url=["\x27]([^"\x27<>]+)["\x27]', html)
```

原因：`data-url="...m3u8?auth_key=xxx&v=3"` 里的 `&` 是合法 URL 字符，`[^"\x27]+` 只到首个 `&` 就停。**解法 = 正则里让 `.m3u8` 作为锚点，从 `.m3u8` 之后允许任意字符**。

### 5.3 播放解密 fallback（91hub 同款 eval）
如果 `data-url` 为空，fallback 到详情页里的 `eval(function(p,a,c,k,e,d))` 混淆脚本：提取 api/key/iv → GET api → b64 解码 → AES-CBC 解密 → m3u8 直链。

### 5.4 HLS 128 解密播放链路（⚠️ 必测！m3u8 时效签名 + ts 段加密）

MissAV CDN 的 m3u8 结构：
```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-KEY:METHOD=AES-128,URI="https://tsnew.xxx.cn/.../enc.key?auth_key=...",IV=0x...
#EXT-X-TARGETDURATION:3
#EXTINF:3.0,
https://tsnew.xxx.cn/.../seg-001.ts?auth_key=...
```

**壳无法直接播放的 3 个根因（逐一修复）**：

**根因 1：`data-url` 正则截断**（上节 5.2 已覆盖）

**根因 2：m3u8 链接无 `.m3u8` 后缀**（CDN 用 hash 路径如 `/m3m/a374bf06ddb200947...`）
`playerContent` 里 `.lower().find(".m3u8")` 匹配失败 → 直接返回 CDN 直链 → 壳无法识别 m3u8。
- **修复**：detailContent 给 m3u8 打 `m3u8://` 前缀标记，`playerContent` 先剥标记再走代理

**根因 3：ts 段时效签名 + AES-128 加密**
CDN 缓存过期后 401/410，且 ts 段加密。
- **修复**：`localProxy` 加 `m3u8`/`ts`/`mkey` 三分支，m3u8 里把所有 ts/key URL 改写为代理地址

```python
# detailContent：给 m3u8 打标记
vod["vod_play_url"] = vod_name + "$m3u8://" + play_url

# playerContent
def playerContent(self, flag, id, vipFlags):
    url = id if str(id).startswith("http") else self._href(id)
    if str(url).startswith("m3u8://"):
        url = url[7:]  # 剥标记
    if ".m3u8" in str(url).lower():
        return {"parse": 0, "url": self.getProxyUrl() + "&type=m3u8&url=" + self._b64(str(url)), "header": self.header}
    return {"parse": 0, "url": url, "header": self.header}

# proxyM3u8：把 m3u8 里的 ts 和 key 改成代理地址
def proxyM3u8(self, url):
    url = self._d64_safe(url)
    h = {"User-Agent": self.header["User-Agent"], "Referer": self.xurl + "/"}
    r = self.session.get(url, headers=h, timeout=15, verify=False)
    if r.status_code != 200:
        return [404, "text/plain", ""]
    text = r.text
    domain = url[:url.rfind('/')]
    b64 = self._b64
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        mm = re.search(r'URI=["\x27]([^"\x27]+)["\x27]', line)
        if mm:
            key_url = mm.group(1)
            if not key_url.startswith("http"):
                key_url = domain + "/" + key_url.lstrip("/")
            line = line.replace(mm.group(1), self.getProxyUrl() + "&type=mkey&url=" + b64(key_url))
        elif not line.startswith("#") and line.strip() != "":
            ts = line.strip()
            if not ts.startswith("http"):
                ts = domain + "/" + ts.lstrip("/")
            line = self.getProxyUrl() + "&type=ts&url=" + b64(ts)
        new_lines.append(line)
    return [200, "application/vnd.apple.mpegurl", "\n".join(new_lines)]

# proxyTs：流回 ts 密文字节（不 AES 解密）
def proxyTs(self, url):
    url = self._d64_safe(url)
    r = self.session.get(url, headers={"User-Agent": self.header["User-Agent"], "Referer": self.xurl + "/"},
                         stream=True, timeout=15, verify=False)
    return [200, "video/MP2T", r.content]

# proxyKey：返回 AES key 原始 16 字节
def proxyKey(self, url):
    url = self._d64_safe(url)
    r = self.session.get(url, headers={"User-Agent": self.header["User-Agent"]}, timeout=10, verify=False)
    return [200, "application/octet-stream", r.content]

def _d64_safe(self, t):
    try: return base64.b64decode(t.encode()).decode()
    except Exception: return t

def _b64(self, t):
    try: return base64.b64encode(t.encode()).decode()
    except Exception: return t

# localProxy 分发（必带 4 分支）
def localProxy(self, params):
    t = params.get('type')
    if t == 'pic': return self.proxyPic(params)
    if t == 'm3u8': return self.proxyM3u8(params.get('url', ''))
    if t == 'ts': return self.proxyTs(params.get('url', ''))
    if t == 'mkey': return self.proxyKey(params.get('url', ''))
    return [200, 'text/plain', '']
```

**⚠️ ts 段是否要 AES 解密取决于壳的播放实现**：
- 多数壳（OK 影视/海阔视界）拿到 m3u8 后**会自行用 IV+key 解密 ts** → `proxyTs` 直接流回密文就行
- 少数壳不调用 mkey → 需要在 `proxyTs` 里自行 `AES.new(key, AES.MODE_CBC, iv)` 解密后返回
- **优先方案：不解密流回密文**；用户反馈花屏再上 AES 解密

---

## 常见坑

1. **域名解析**：本机连不上 3 个主域名（DNS 超时），必须走代理（飞牛NAS 192.168.31.66:7890 或壳环境代理）；`init(extend)` 传真实域名兜底
2. **`data-url` vs `data-src`**：`data-src` 是图片（AES 解密），`data-url` 是视频直链（不加密，直接返回）
3. **`href="/watch/xxx/"` 正则要用 `*` 不是 `+`**，`/watch/` 前可能没有别的字符
4. **女优/标签二级 URL 里的中文名必须 URL 编码**：`urllib.parse.quote(name)`
5. **页面源码里 `\r` 换行符**：`fetch()` 里 `.replace('\r', '')` 去掉
6. **`&amp;` 转义**：`data-url` 里的 `&` 被源码写成 `&amp;`，解码用 `.replace('&amp;', '&')`
7. **女优 data-src 可能为空字符串**：空 data-src 直接跳过不出图
8. **`data-url` 正则截断**：`[^"\x27]+` 在 `&` 处停，丢了 m3u8 后缀 → 用 `.m3u8` 锚点正则
9. **筛选参数路由**：壳端 ext vs filter 传参不一致，必须两种都处理
10. **域名解析并发**：串行 58 秒 → 并发 5~9 秒（ThreadPoolExecutor + as_completed timeout=12）

---

## 完整 py 文件（535 行，已交付 /opt/data/out/missav.py）
# ============ 原文件: missavt-最终交付版.md ============

# MissAVt 最终交付版（v3 修复 535 行）

> 参考：`references/missavt-写作步骤.md`（主流程）
> 交付：`/opt/data/out/missav.py`（535 行，已修复筛选+播放超时）

## 交付流程（从 0 到 1）

1. 读 `51短剧用久发布站源码(1).json`（3 发布站 publish.js 同源）→ 提取后缀池 `['kibsbvpft.cc','fvtweuyk.cc','gcqsnwaam.com']`，前缀 5 字符随机
2. 图片：AES-128-CBC（key `f5d965df75336270` / iv `97b60394abc2fbe1`）→ localProxy(type=pic)
3. 播放：**列表页 `data-url` 直接就是 m3u8 直链**（无需解密）；详情页 fallback 到 91hub 同款 eval 混淆解密
4. 分类：sort / category / actresses / tags / actress(二级) / tag(二级) / search 七大入口
5. 详情：`data-src` 取封面 → `data-url` 取播放 → 必填 `vod_play_from` + `vod_play_url=名$url`

## v2 关键修正

### 1. 域名并发解析（58s → 5~9s）

原来 `_get_domain` 串行试后缀×前缀×代理端口，58 秒+，壳端会超时。

**改成**：`concurrent.futures.ThreadPoolExecutor(max_workers=10)` 并发构造 `候选域名列表`（3 后缀 × 2 前缀 × 3 代理端口），12 秒 timeout 内谁先通用谁。

```python
def try_one(item):
    domain, p = item
    try:
        r = self.session.get(domain, headers={"User-Agent": "Mozilla/5.0"}, timeout=3, verify=False, proxies=p)
        if r.status_code == 200 and ('MissAVt' in r.text or 'video-item' in r.text):
            return (domain, p)
    except Exception:
        pass
    return None

with ThreadPoolExecutor(max_workers=10) as ex:
    for domain in candidates:
        for p in proxies:
            futures.append(ex.submit(try_one, (domain, p)))
    for f in as_completed(futures, timeout=12):
        result = f.result()
        if result:
            domain, p = result
            self.session.proxies = p
            return domain
```

代理探测顺序：`127.0.0.1:7890` → `127.0.0.1:1080` → `127.0.0.1:1087` → `192.168.31.66:7890`（飞牛NAS）→ 直连

### 2. 筛选参数走 filter 不走 ext（**核心 bug**）

原来 `categoryContent(cid, pg, filter, ext)` 里用 `ext.get('by')`，TVBox 壳端把筛选参数走 **filter**（dict 形式），ext 是空字符串 → `.get()` 永远返回默认值 → 点哪个筛选都没变化。

**修复**：
```python
f = {}
if isinstance(filter, dict):
    f = filter
if not f and isinstance(ext, str) and ext not in ('', '{}', 'null', 'undefined'):
    try: f = json.loads(ext)
    except: pass
# 后续全部用 f.get('by') / f.get('cateId')
```

**教训**：TVBox 壳端 `categoryContent` 参数顺序为 `(cid, pg, filter, ext)`，**筛选值走 filter 字典，不走 ext**。写 py 源必须确认 shell 传入哪个参数。

### 3. 代理自动回退

`fetch()` 主 session 没代理时自动 `_fetch_with_proxy()` 扫 7890/1080/1087：
```python
def _fetch_with_proxy(self, url):
    for port in ['7890', '1080', '1087']:
        try:
            p = {"http": f"http://127.0.0.1:{port}", "https": f"http://127.0.0.1:{port}"}
            r = self.session.get(url, headers=h, timeout=12, verify=False, proxies=p)
            if r.status_code == 200:
                self.session.proxies = p
                return r.text.replace('\r', '')
        except: pass
    return ""
```

### 4. `sys.path.append('..')` 移除

壳端标准写法不需要，直接 `from base.spider import Spider`。

## 最终交付验证

- `init(extend="")` 自动解析 → `https://7auok.kibsbvpft.cc`（8.9s），24 部有图
- `init(extend="https://scu.fvtweuyk.cc")` 传真实域名 → 跳过解析（1s）
- 7 个 class 全部返回（sort / jp / cn / uncen / amateur / actresses / tags）
- 筛选 `filter={"by":"renew"}` / `filter={"cateId":"madou"}` 全部走正确 URL
- 女优二级 `actress/{name}/{page}/` + URL 编码
- 标签二级 `tag/{name}/{page}/`
- 详情 → `vod_play_from="MissAVt"` + m3u8 直链