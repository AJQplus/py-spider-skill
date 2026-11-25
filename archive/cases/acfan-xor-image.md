# ACFAN 封面 XOR 加密图片案例

站点：https://acfan.wwvgadm0.work/mobile（Nuxt SSR 自定义站，非 MacCMS）
内容：动漫 / 漫画 / 视频

## 现象
- 封面能访问，但壳（fongmi/海阔）里不显示封面。
- 直接 GET 封面 URL 返回 application/octet-stream，首字节不是图片魔数。
- 列表接口返回的 coverImg 是相对路径，需拼 imgDomain（图片 CDN 域）。

## 关键结论
1. 封面 CDN 返回的是前端 XOR 加密二进制，不是普通图片。
   - 加密特征：imageEncrypt: true 配置 + 下载后魔数非 JPEG/PNG/WebP。
2. 解密规则：只对前 100 字节做 XOR 循环异或，密钥字符串 2020-zq3-888。
   - 解密后魔数恢复：JPEG FF D8 FF / PNG 89 50 4E 47 / WebP RIFF，长度不变。
3. 封面必须走壳的图片代理，不能直接给加密 URL：
   - 包装为 http://127.0.0.1:9978/proxy?do=py&type=img&url=quote(完整图URL)
   - localProxy 里：下载 → XOR 解密前100字节 → 按魔数返回 MIME。
4. localProxy 返回格式：[200, mime, bytes, {}] 四元组（fongmi/海阔系），MIME 按魔数给，不能统一 octet-stream。
5. 封面域与播放域分开：
   - 封面 = imgDomain（/api/sys/public/imageCdnDomain 动态获取；列表接口的 domain 字段也是封面域）。
   - 视频 = playPath 所在 CDN 域（m3u8），混用会 403 / 空图。
6. 漫画章节图与封面同一套 XOR 加密，pics:// 的每张图同样走该 localProxy 解密，一套逻辑全解决。
7. 播放链路同样有坑：m3u8 不能直连，要调 /api/m3u8/public/decode/authPath?path=..&auth_key=.. 生成带签名的 AES-128 清单。

## 通用方法沉淀
遇到「封面能访问但壳不显示」：
1. 下载图片，查魔数（JPEG/PNG/WebP），不是魔数 → 加密。
2. 在前端 JS 找解密逻辑：imageEncrypt / crypto.subtle / AES.decrypt / XOR 密钥字符串 / arrayBuffer()。
3. 封面 URL 走 getProxyUrl + type=img 包装，localProxy 解密后按魔数返回正确 MIME。
4. 封面域与播放域分离，动态获取 imgDomain，不要复用播放 CDN 域。

## 代码参考（localProxy 图片解密）
```python
def localProxy(self, param):
    url = param.get("url", "")
    r = requests.get(url, headers=self.headers, timeout=25)
    data = bytearray(r.content)
    key = b"2020-zq3-888"
    if data and data[:4] not in (b"\xff\xd8\xff", b"RIFF", b"\x89PNG"):
        for i in range(min(100, len(data))):
            data[i] ^= key[i % len(key)]
    mime = "image/webp" if data[:4] == b"RIFF" else ("image/png" if data[:4] == b"\x89PNG" else "image/jpeg")
    return [200, mime, bytes(data), {}] if r.ok else [404, "text/plain", b"", {}]

def img_proxy(self, url):
    return "http://127.0.0.1:9978/proxy?do=py&type=img&url=" + quote(self.fix(url, self.img), safe="")
```
