# CF Turnstile TLS 指纹过盾策略模块 v9.5

本模块优先级高于普通 UA、请求头补全和通用代理尝试；仅在确认存在 TLS 指纹型挑战时启用，避免影响普通站点。

## 适用特征

- 浏览器可开但纯 `requests` 返回 **403**，正文是 Cloudflare 挑战页（`Just a moment...`、`challenge-platform`、`turnstile`）。
- `curl_cffi`、`extended_http_tools`、改 UA/补全请求头、第三方抓取代理**全部无效**——盾在校验 TLS 指纹而非请求头。
- 客户端（羊壳/海阔等）**没有 cloudscraper/curl_cffi**，源必须零第三方依赖过盾。
- 典型站点：spankbang.com 全站 Turnstile 交互式挑战。

## 核心方案：CipherSuiteAdapter（纯 requests + ssl 标准库）

原理：cloudscraper 过 CF 盾靠的不是 JS 求解，而是 **TLS ClientHello 指纹**（密码套件列表 + ECDH 曲线）。把这个指纹复制到 `requests` 自定义 HTTPAdapter 的 `ssl_context` 里即可零依赖过盾。

```python
import ssl, requests
from requests.adapters import HTTPAdapter

_CIPHERS = 'TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_256_GCM_SHA384:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:AES128-SHA:AES256-SHA'

class _CFAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        # 兼容坑：客户端强制 verify=False 时 check_hostname 必须提前关闭，
        # 否则 CERT_NONE + check_hostname=True 抛 ValueError 导致整个 session 挂掉
        try:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        except Exception:
            pass
        try:
            self.ssl_context.set_ciphers(_CIPHERS)
        except Exception:
            pass
        try:
            self.ssl_context.set_ecdh_curve('prime256v1')
        except Exception:
            pass
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

s = requests.Session()
s.headers.update({...})
s.mount('https://', _CFAdapter())
```

## 关键约束

1. **18 项密码套件列表 + `prime256v1` 曲线是实测指纹**，不要自行增删；低端 OpenSSL 不支持个别套件时 `set_ciphers` 会整体失败，必须 try/except 降级（降级后只是不过盾，不能崩）。
2. **每处 ssl 设置独立 try/except**：`TLSVersion.TLSv1_3` 在老 OpenSSL 上不存在，属性赋值失败不能影响其余设置。
3. **所有请求走 `session.get(url, verify=False)`**，session 已 mount adapter；请求失败重试 3 次 + 退避（`time.sleep(0.8*(attempt+1))`）。
4. **过盾判据**：`status_code == 200 and "Just a moment" not in r.text[:600]`，两者同时满足才算成功。
5. 域名池防失效：主域失败换 www 子域/备用域探活（探活 URL 用真实列表页特征如 `video-item` 计数，不能只看 200）。
6. UA 用完整 Chrome 桌面 UA，headers 带 Accept/Accept-Language/Referer。
7. 站点偶发限流（单次请求返回空）属正常，重试即可，不要误判为盾升级。

## 验证门禁

- `session.get(主页)` 返回 200 且非挑战页；列表页 HTML 含真实视频节点特征。
- 播放直链门禁：m3u8 链接 Range 请求前 4KB 必含 `#EXTM3U`。
- 模拟低版本环境编译通过（`ast.parse`），无 TLSv1_3 硬依赖。

## 案例参考

- SpankBang（spankbang.com，v9.4）：全站 CF Turnstile，curl_cffi/抓取代理/改头全无效 → 内嵌 CipherSuiteAdapter 纯 requests 过盾成功；`verify=False` 与 `check_hostname` 冲突坑实测修复；签名播放链接数小时失效，进详情页实时刷新。
