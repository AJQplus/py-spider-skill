# 非标准播放/加密补充模块 v9.5
全站整页解码、图片 XOR、POST 播放解密、专辑三形态。
## 适用特征
- 页面 HTML = 单个被单引号包裹的超长串（快男系）。
- 图片返回非图片魔数、需 XOR 解密。
- 播放需要 POST 接口取密文再 base64 解码（hsck 系）。
- 详情页有多个 dplayer / 单个 dplayer / 无 dplayer（专辑）。
## 1. 全站整页双重 base64
站点所有数据页（列表/搜索/详情/播放）返回：`HTML = '<double-base64>'`，即单个单引号包裹的超长字符串。
```python
def decode_page(self, text):
    m = re.search(r"'([A-Za-z0-9+/=\s]{200,})'", text)
    if not m:
        return text
    try:
        raw = base64.b64decode(m.group(1))
        raw = base64.b64decode(raw)
        return raw.decode('utf-8', 'ignore')
    except Exception:
        return text
```
注意：首页/分类（双重）与搜索/详情/播放（双重）均适用；域名文件（如 `1.json`）是明文，不需解密。
## 2. 图片 XOR 加密
特征：图片域名为特定 CDN；响应为 base64 文本，逐字节 XOR 后得图片。
```python
from base64 import b64decode
XOR_KEY = b'OzoTeoS7D>6Y^@z39JmD'
def xor_decrypt(data):
    enc = b64decode(data.decode('utf-8', 'ignore').strip())
    kl = len(XOR_KEY)
    out = bytearray(len(enc))
    for i in range(len(enc)):
        out[i] = enc[i] ^ XOR_KEY[i % kl]
    return bytes(out)
def magic_type(b):
    if b[:2] == b'\xff\xd8':              return 'image/jpeg'
    if b[:8] == b'\x89PNG\r\n\x1a\n':    return 'image/png'
    if b[:3] == b'GIF':                    return 'image/gif'
    if b[:4] == b'RIFF':                   return 'image/webp'
    return ''
```
代理构造与 localProxy 返回格式严格对齐 `tvbox_runtime.md` 第 5 节。
注意：站点图片是否加密要用域名白名单判定；明文图直接透传，不要一律 XOR。
## 3. POST 播放解密（hsck 系）
链路：详情页提 AID/ASID/ANID/AK → POST `/static/count.php` → 返回 JSON `{"ok":true,"u":"Base64"}` → base64 解码 → m3u8 直链。
```python
post_url = f"{self.host}/static/count.php"
data = {'id': aid, 'sid': asid, 'nid': anid, 'tk': ak,
        'g': 1, 'x': 100, 'y': 200, 'dt': 1200, 'sw': 390, 'sh': 844, 'tz': -480, 't': int(time.time())}
r = self.session.post(post_url, data=data, headers=self.headers, timeout=15)
j = r.json()
if j.get('ok') and j.get('u'):
    url = base64.b64decode(j['u']).decode('utf-8')
```
对应 XBPQ：`播放链接: {{域名-c}}/static/count.php;post;id={{VPID}}&sid={{VPSID}}...`，`播放链接加工: [工具:源码#json截取:u#解b64]`。
解析后的 URL 仍需验证 HTTP 状态与 `#EXTM3U`。
## 4. 专辑三形态判定
详情页播放容器先数 `.dplayer` 数量：
| 数量 | 形态 | 处理 |
|---|---|---|
| >= 2 | 多集 | 逐个 `data-config`（可能是单引号包裹 JSON）→ `video.url` |
| == 1 | 单集 | 同上单条；集标题 `data-video_title` → headline → 正片 |
| 0 | 专辑 | `post-content` 内 `a[href*="/archives/"]` 去重、排除自身 → 并发抓子页 → 子页 `data-config.video.url` 直取 |
- 专辑关键：**不要嗅探**，必须抓子页源码直取；子页多 dplayer 时取第一个有 `video.url` 的。
- 子页并发结果必须按原索引 sort 保序，否则集序乱。
- 判据：先数 `dplayer-loading` 块，为 0 才走子链并发，不要无脑抓。
## 5. 封面传导
详情页 `vod_pic` 优先用列表封面（列表 `getimg` 输出的代理包装 URL），避免详情页现抓 `og:image` 落入广告图或缺失；裸路径 id 无封面段时回退详情页抓取。
## 6. 门禁
- 全站解码站必须先验证解码后含站点特征结构，再解析。
- 图片解密后必须检查魔数；只验证文件头只能说「疑似解密成功」。
- POST 解密后必须实测 `#EXTM3U`，不得把 JSON 的 `u` 字段直接当直链。
- 专辑形态必须三种各自有实测样本，不得只测一种。
