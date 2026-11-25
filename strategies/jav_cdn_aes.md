# JAV 系 CDN 加密图片 + 动态域名语义策略模块 v9.5

## 适用特征

- JAV 资源站（91JAV 系）图片 CDN（如 `wuabeza.gyqspl.cn`）返回的封面**全部是 AES-CBC 密文**，魔数非图片（头 `3eaa708e...`），仅看字节数/Content-Type 会误判为"活图"。
- GitLab README 发布页含多种链接类型：国内最新网址（发布页）、国内备用地址（重定向入口）、海外永久地址（需 VPN 主站）、APP 站/邮箱/TG。
- 图片 URL 可能被反引号包裹（`` `https://...` ``）或含 `\/`。
- 列表卡片角标区含多个 `<span>`：`chinese`（字幕/分类）、`label`（时长或广告）。

## 核心规则

### 1. 图片必须验魔数，不能只看字节数和 Content-Type（铁律）

CDN 返回 `binary/octet-stream` 且几百 KB 不代表图片可用——可能是 AES 密文。判活标准：**请求后检查前 4 字节魔数**（`ffd8ff`=JPEG、`89504e47`=PNG、`474946`=GIF、`RIFF....WEBP`=WebP），不是图片格式即视为密文/坏图。

### 2. AES-CBC 解密（91JAV 系固定密钥）

```python
aes_key = b"f5d965df75336270"   # 16 字节 ASCII
aes_iv  = b"97b60394abc2fbe1"
# pycryptodome 优先，缺失时降级返回空（localProxy 透传原字节兜底）
unpad(AES.new(aes_key, AES.MODE_CBC, aes_iv).decrypt(data), AES.block_size)
```

- 实测所有路径（`/upload_01/upload/`、`/upload/upload/`、`/upload/cloud/`）的 `.jpeg`/`.jpg` 全部同密钥加密。
- 解密后验魔数：`dec[:3]==b"\xff\xd8\xff"` 或 PNG/GIF → 返回 `image/jpeg`；解密失败返回原字节（防崩）。
- **不要因扩展名 `.jpg` 就直出**——`/upload/cloud/xxx.jpg` 同样是密文！所有 CDN 图必须走 localProxy 解密。

### 3. localProxy 用 getProxyUrl 原生入口（关键）

- 封面 URL 用 `self.getProxyUrl() + "&url=" + b64(url) + "&type=img"`，**壳端原生图片代理入口**，不要自拼 `localProxy?type=img&url=` 字符串（多数壳端不认）。
- `localProxy` 返回 **4 元组** `[200, content_type, data, ""]`（部分壳端要求 4 元素）。
- 图片代理复用 session + `proxies=self.session.proxies or None`，不裸用 `requests.get`。
- 同一源内可加 `_img_cache` 字典缓存解密结果，避免重复拉 CDN。

### 4. README 发布页域名语义（禁止把发布页当主站）

GitLab README 的链接**不是都是主站域名**，必须按标注分类处理：

| README 标注 | 类型 | 处理 |
|---|---|---|
| `91JAV国内最新网址` | 发布页 | 抓发布页，**提取页内线路域名**（cloudfront/zbywlcc 等）加入备用池，不要把发布页本身当主站 |
| `91JAV国内备用地址` | 重定向入口 | 跟随 `allow_redirects=True`，取 final 域名做主站验证 |
| `91JAV海外永久地址（需要VPN）` | 海外主站 | 直接探测主站路径 |
| `官方APP` / `备用` / `pm.me` / `t.me` / gitlab | 非站点 | 跳过 |

- 发布页的价值在**页面内的线路**（如 `d1nqsse6ono4lc.cloudfront.net`），不在发布页 URL 本身。
- 探测主站路径用真实特征（如 `/theme/detail/3/update/` 含 `bind_video_img`），不能只看 200。

### 5. 动态域名（可选增强）

发布页源码含 `words.random() + ".xxx"` 后缀 → 用 `PREFIX_CHARS` 随机 4 位前缀组装候选域名并发探测（2 秒超时），成功即锁定。可配 30 分钟域名缓存 + 30 秒 line_url 缓存。

## vod_remarks 角标规则（客户端误渲染铁律）

- **时长角标唯一归属 = 视频卡片 `vod_remarks`**（渲染在预览图上）。列表能拿到时长就必须格式化后放入卡片角标，禁止只放详情页。
- **视频卡片** `vod_remarks` 只放**时长文本**（如 `02:30:41`），不要拼接中文分类名（如 `中文字幕 02:30:41`）——客户端会把中文当分类名、把开头数字（`02`→`0`）当影片数量，渲染成"中文字幕 0 部"。
- **详情页** `vod_remarks` 放**纯标签/副标题**（逗号拼接，如 `Sex,japanese girl,Amateur`），不放时长（时长已在卡片，避免详情重复）；`vod_content` 放简介（og:description 等，去除推广前后缀）。
- **folder 目录卡片**（专题/女优）`vod_remarks` 放**影片数量**（`16030 部影片` / `533 部影片`），从 `<span class="label">16030 部影片</span>` 或 `<span>533 部影片</span>` 提取。
- 时长格式化：`8m`→`08:00`、`26m`→`26:00`、`1h 44m`→`01:44:00`、秒数→`mm:ss`/`hh:mm:ss`；**站点原始格式（如 `1h 44m`）直接透传时不保证客户端渲染**，必须转标准 `mm:ss`/`hh:mm:ss`。
- 视频卡片角标 = 时长；folder 目录卡片 = 数量；详情页 = 标签副标题。三者职责分离，绝不混用。
- 广告卡片角标 `广告` 必须过滤（`if "广告" in remarks: remarks = ""`）。

### 正则分块提取陷阱（video-item 子串误截断）

用 `data-testid` 前瞻分块时，**testid 存在前缀包含关系**（`video-item-length` 含 `video-item`），前瞻 `data-testid="video-item` 不带收尾引号会把时长 div 当成下一个视频块，导致每个视频在时长处截断、时长永远提取不到（卡片角标全空）。分界必须带收尾引号：

```python
# ❌ 错：video-item-length 也命中 video-item 前缀，块在时长处截断
r'(?=<div[^>]*data-testid="video-item|...)'
# ✅ 对：收尾引号精确匹配 video-item"，不误伤 video-item-length
r'(?=<div[^>]*data-testid="video-item"|...)'
```

## 验证门禁

- 图片：抽测多个路径 URL，解密后魔数必须为真实图片；`_img_cache` 命中后不重复请求。
- 域名：README 解析后确认加入池的是**真实主站/线路**，不是发布页/APP 站；发布页仅贡献线路。
- 角标：视频列表 `vod_remarks` 为纯时长；folder 列表为影片数量；客户端不出现"0 部"误渲染。

## 案例参考

- 91JAV（cabin.zbywlcc.com）实战：AES 图片解密 + getProxyUrl 原生代理 + README 三类型域名语义 + 角标职责分离。
