# 盾类型识别与过盾决策模块 v9.5
站点 403/503、返回验证页或空页时，先分诊盾类型，再选通道。拿 200 不等于过盾。
## 适用特征
| 页面特征 | 盾类型 | 方案 |
|---|---|---|
| `Just a moment`、`cf-chl-widget`、`__cf_chl_opt`、`challenge-form` | Cloudflare | 多通道降级 → cf_tls_fingerprint → WebView |
| `滑动验证`、`slideBox`、`huadong_*.js` | 滑动验证 | slider_huadong.md 纯计算破解 |
| `/_waf/*.sjs`、`GoCaptcha`、HTTP 418 | WAF+验证码 | 纯 HTTP 无解，`parse=1` 交壳 WebView |
| HTTP 200 但内容空白、只有一句验证中/一堆混淆 JS | JS 挑战 | session 取页 + 找 JS 跳转/cookie 逻辑 |
| 滑块过但后续仍 403，cookie 含 `__mxau__/__mxaf__/__mxas__/__mxav__` | 设备指纹风控 | 同进程连续完成，禁止跨环境搬 cookie |
| 播放地址是 iqiyi/youku 等别的站网页地址 | 解析站 | 站点自带 parseApis 拼线路 → 壳 WebView |
## 核心原则
- 拿 200 不等于过盾：必须做真内容校验（盾页特征词 + 站点特征词双判）。
- 壳端取页通道（基类若提供 `self.fetch`）走手机网络，优先级高于服务器 requests；手机 IP 常不触发风控。本项目 T4 模板未内置 `self.fetch`，用 `self.session` 即可；仅在壳端确认存在该基类方法时才用它。未确认前一律走 `self.session`。
- 绝不能高频请求：连续 2 次即可 `Connection aborted` 封 IP 数小时，请求间隔 ≥1.5s。
- `timeout=(连接超时, 读取超时)` 用元组，单值会被慢连接拖死。
- 存活判据 = 状态码 + 特征字符串；只判 200 会把验证页当正常页。
- Referer 用「触发验证的那个页面」，不要用首页。
## 真内容校验（关键）
```python
SHIELD_MARKS = ('Just a moment', 'Attention Required', 'security verification',
                'cf-chl-widget', 'cf-turnstile', 'challenge-form',
                'window._cf_chl_opt', '滑动验证', 'slideBox', '人机身份验证',
                '安全验证', '正在验证', '请稍候')
def has_expected_content(html, keywords=None, min_len=1500):
    if not html or len(html) < min_len:
        return False
    head = html[:3000]
    if any(m in head for m in SHIELD_MARKS):
        return False
    return any(k in html for k in keywords) if keywords else True
```
## 多通道降级取页
```python
def _get_with_fallback(self, url, keywords=None, referer=None):
    # ① 壳端 fetch（仅当基类确认提供时；T4 模板无此方法，直接跳过）
    if hasattr(self, 'fetch'):
        try:
            hd = dict(getattr(self, 'headers', {}) or {})
            if referer or getattr(self, 'host', ''):
                hd['Referer'] = referer or self.host
            r = self.fetch(url, headers=hd)
            if has_expected_content(r.text, keywords):
                return r.text
        except Exception:
            pass
    # ② requests.Session（服务器网络，默认通道）
    try:
        r = self.session.get(url, timeout=(5, 12), headers=self.headers)
        if has_expected_content(r.text, keywords):
            return r.text
    except Exception:
        pass
    # ③ 通用阅读代理 r.jina.ai（外部服务兜底）
    try:
        r = requests.get('https://r.jina.ai/' + url, timeout=20)
        if has_expected_content(r.text, keywords):
            return r.text
    except Exception:
        pass
    # ④ 语言镜像（部分站风控更松）
    for mirror in ('/zh-hant', '/zh-tw'):
        try:
            mp = urlparse(url).path or '/'
            r = self.session.get(self.host.rstrip('/') + mirror + mp, timeout=(5, 12))
            if has_expected_content(r.text, keywords):
                return r.text
        except Exception:
            continue
    return ''
```
## 设备指纹风控
特征：滑块能过（拿到 cookie）但后续请求仍 403；cookie 含同前缀 `__mx*__` 组变量。
原理：三方风控 SDK 校验设备指纹（UA/屏幕/Canvas/WebGL/字体）、cookie 与指纹绑定、行为数据、时间窗口。
结论：纯 Python + 浏览器导出的 cookie 无效；正解是在产生指纹的同一进程里连续完成全流程（访问页 → 拿 key → 算签名 → 打验证接口），不要跨环境搬 cookie。
## WAF + 验证码
HTTP 418 或 `/_waf/*.sjs`、GoCaptcha：纯 HTTP 无解，只能 `parse=1` 交壳 WebView，或放弃该站。
## 解析站（播放地址是别的站网页）
优先读站点自带解析接口：`/api/config` 的 `parseApis`，在 `detailContent` 里逐集展开额外拼线路：
```python
PARSE_APIS = [('解析A', 'https://jx.xmflv.com/?url='), ('解析B', 'https://jx.m3u8.tv/jiexi/?url=')]
for pname, pfx in PARSE_APIS:
    eps = ['%s$%s%s' % (ep_name, pfx, urllib.parse.quote(ep_url, safe=''))
           for ep_name, ep_url in pairs]
    tabs.append('%s·解析' % pname); urls.append('#'.join(eps))
```
`playerContent` 遇到非直链的网页地址返回 `parse=1` 交壳 WebView 嗅探。
现实：主流解析站已全转浏览器端 JS 解析且大多有 WAF，纯 HTTP 取不到 m3u8；能播的前提是壳 WebView 能打开并嗅探到流。
## 门禁
- 站点评测报告必须写清：盾类型、命中通道、是否真内容校验通过。
- 盾页冒充成功不算通过；必须给出站点特征词命中证据。
- 请求间隔 <1.5s 的高频重试视为不合格实现。