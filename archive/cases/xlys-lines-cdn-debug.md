# 雪落影视（v.xl01.eu.cc）实战案例

<!-- 演进: 2026-09-03 | 来源: 雪落影视 py源开发 | 类型: troubleshoot -->

站点画像：Java Spring Boot 自研站（非 MacCMS），HTML 渲染 + AES 签名播放接口 + 字节系 CDN 直链。

## 1. 分类体系：导航菜单 != 资源分类

首页“更多”菜单展开 43 个标签（动作/爱情/动画/综艺/美剧/短剧…），看着像顶级分类，实际是筛选项。
真实分类只有 2 个，藏在分类页筛选栏第一个 dl：

    <dl><dt>资源分类：</dt><dd>
      <a href="/s/all">不限</a>
      <a href="/s/all?type=0">电影</a>
      <a href="/s/all?type=1">电视剧</a>
    </dd></dl>
    <dl><dt>影视类型：</dt><dd> 43 个标签 -> /s/{slug}?type={0|1} </dd></dl>

错误后果：把 43 个标签当 classes，filters 的 key 与 type_id 不匹配导致筛选栏不联动；用户看到的分类与原站完全不符。

规则：定分类体系必须读筛选区 dt 分组，第一组通常才是真实资源分类，其余组是 filters。导航菜单只能当线索。

## 2. type_id 内不能含 ?

把 all?type=0 当 type_id，翻页拼出 /s/all?type=0/2 -> HTTP 400。
正确：type_id 存纯 slug（all / 0 / 1），query 在 categoryContent 单独组装：

    qs = []
    if str(tid) in ("0", "1"): qs.append("type=" + str(tid))
    for k in ("area", "year", "order"):
        if ex.get(k): qs.append(k + "=" + quote(str(ex[k])))
    q = ("?" + "&".join(qs)) if qs else ""
    url = "%s/s/%s/%d%s" % (host, slug, pg, q) if pg > 1 else "%s/s/%s%s" % (host, slug, q)

注意 qs 一律用 ? 开头，写成 "&" + ... 会产出 /s/all&type=0。

## 3. 详情页规范路径 vs 剧集链接可变前缀

- 列表 href：/{cat}/{id}.htm（cat 是分类 slug）
- 详情页规范路径：/v/{id}.htm（cat 换成任意值都能开，说明 cat 不参与路由，只是 SEO 装饰）
- 剧集 href：有的是 /play/{id}-{n}.htm，有的是 /{cat}/play/{id}-{n}.htm

错误做法：正则抽 ID 再重拼 /play/xxx.htm，带 cat 前缀的剧集必 404。
规则：play id 存完整相对路径（href.lstrip("/")），playerContent 直接还原：

    url = p if p.startswith("http") else "%s/%s" % (host, p) if p.endswith(".htm") else "%s/play/%s.htm" % (host, p)

## 4. CryptoJS WordArray key != passphrase（最耗时的坑）

混淆后的签名逻辑：

    const key = CryptoJS.enc.Utf8.parse(md5(pid + "-" + t).substring(0, 16));
    const ct  = CryptoJS.AES.encrypt(pid + "-" + t, key, {mode: ECB, padding: Pkcs7});
    $.post(`/god/${pid}?type=1`, {t: t, sg: base64ToHex(ct.toString()), verifyCode: code});

关键区分：

| 第二参数类型 | CryptoJS 行为 | Python 等价 |
|---|---|---|
| WordArray（enc.Utf8.parse(...)） | 直接当原始 key，无 KDF、无 salt | AES.new(key_bytes, MODE_ECB) |
| str（"mypass"） | EVP_BytesToKey 派生 key+iv，输出前缀 Salted__ + 8 字节 salt | 需自行实现 EVP KDF |

本站是 WordArray。第一版按 passphrase 实现 EVP KDF + Salted__ 前缀 -> /lines 返回 {"code":403,"msg":"非法请求！"}。
base64ToHex(ct.toString()) = atob(b64) 后逐字节转 hex 大写；WordArray 无 salt 前缀，等价于直接 ciphertext.hex().upper()：

    def _sg(pid, t):
        k = hashlib.md5((pid + "-" + t).encode()).hexdigest()[:16].encode()
        return _aes_ecb((pid + "-" + t).encode(), k).hex().upper()

排查捷径：签名接口返回 403/非法请求时，先看 CryptoJS 第二参数是 WordArray 还是字符串，判据是有没有 enc.Utf8.parse / enc.Hex.parse 包裹，再决定要不要 EVP KDF。

## 5. 播放直链：/god 只是候选之一，/lines 才是全集

/lines?t=&sg=&pid=（GET，同一套签名）返回全部线路：

    {"code":0,"data":{
      "url3":"https://a.com/obj/xxx,https://b.com/obj/yyy",
      "m3u8":"https://www.bde4.cc/HEX.m3u8",
      "m3u8_2":"https://www.bde4.cc/HEX.m3u8#iplay,...",
      "tos":1, "ptoken":"..."}}

/god/{pid}?type=1 返回的单个 url 是从 tos 线路实时签发，每次调用 CDN 域名随机，实测 5 个 pid 里 4 个首次返回 403。

最终策略（成功率 5/5）：
1. 先 /lines 取 url3，逗号切分逐个探活（Range: bytes=0-1023 + 校验 ftyp / #EXTM3U），第一个通过即返回
2. 失败才回退 /god，对返回 url 做 CDN 域名重写后再探活

m3u8/m3u8_2 走 www.bde4.cc，替换域名后返回的是 PNG 魔数（\x89PNG），需 slice(3354) + pako.inflate 解密才是真 m3u8（本次未采用，url3 已够用）。

## 6. 字节系 CDN 域名重写表

    BADCDN = ["f19-", "f77-", "lf16-capcut.faceueditorv.com", "lf16-secsdk.bitssec.com",
              "lf16-data.bytepluscdn.com", "lf16-fdm.fdmimgs.com", "lf16-cc-everphoto.faceulv.com",
              "lf16-capcut.faceulv.com", "lf16-geckocdn-offline.g-p-static.com"]
    RULES = [("tos-alisg-v-0000",     "http://lf77-geckocdn.bytegecko-i18n.com/obj/", "https://p16-hera-sign-va.ibyteimg.com/obj/"),
             ("tos-maliva-o-0000-us", "http://lf16-cdn-solve.gauthmath.com/obj/",     "https://p16-hera-sign-va.ibyteimg.com/obj/"),
             ("tos-alisg-i-0000",     "https://lf16-anyweb.anyweb.space/obj/",        "https://p16-hera-sign-va.ibyteimg.com/obj/")]
    # 另有固定替换 v16m-default.tiktokcdn.com -> v16m-default.akamaized.net

命中 BADCDN 走 A 域名，否则走 B。实测 tos-alisg-i-0000 一个资源有 6~8 个可用 host，但 tos-alisg-v-0000 / tos-maliva-o-0000-us 全部 403/404 —— 重写表不是万能的，必须探活兜底。

## 7. Spring 分页链接会插 jsessionid

第 1 页分页 href 正常，从第 2 页起变成：

    <a href="/s/all/1084;jsessionid=40282AF2FD6701EE6FA55610F9DE1CB2">尾页</a>

正则 /(\d+)(?:\?|$) 匹配不到 -> pagecount 从 1084 退化成 5（只剩数字文本 1~5）。
修正：/(\d+)(?:[;?]|$)。Java 站解析分页务必把 ;jsessionid= 纳入分隔符。

## 8. 搜索被验证码墙 + UA 白名单

- /search/{urlencoded_kw} 首次返回 xl-code-wrap「30分钟内首次搜索需要输入验证码」
- 验证码是算术题图片（如 41+57=），130x28 JPEG；tesseract 基本报废，ddddocr 约 50% 正确率（乘号/等号常错）
- ?code=<任意值> 全部无效；穷举 0~199 时命中的“非验证码响应”其实是 nginx 403 限流，不是搜索结果
- 同 session 通过一次后，后续关键词免验证码（30 分钟窗口）
- UA 白名单：okhttp/* curl/* python-requests/* 直接 nginx 403（153 字节）；Dalvik/* 浏览器 UA Baiduspider 可通

结论：Spider 内不做 OCR，检测到 xl-code-wrap 直接返回空列表并打日志。

## 验收记录

| 项 | 结果 |
|---|---|
| homeContent / homeVideoContent | 126 条 |
| categoryContent all/0/1 第1、2页 | 各 24 条，pagecount 1084/821/263 |
| 筛选组合（类型+地区+年份+排序） | 24 条，URL 实测生效 |
| detailContent | 16 集剧集，年份/地区/语言/演员/导演/简介齐全 |
| playerContent | parse=0，HTTP 206 + magic ftypisom 真 mp4 |
| searchContent | 被站点验证码拦截（已知限制） |
