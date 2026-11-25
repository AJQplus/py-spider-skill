# HLS 与 localProxy 播放代理模块 v9.5

处理 HLS AES-128、m3u8 子清单、ts/key 代理、签名时效、data-preview/data-play-src 直链站和播放链路逐级排查。

## 适用特征

- m3u8 含 `#EXT-X-KEY:METHOD=AES-128`、KEY URI、IV。
- 主 m3u8 能访问但播放失败。
- ts/key 在另一个 CDN 域名，或客户端无法直连分片/key。
- 列表卡片含 `data-preview`、`data-play-src`、`video.url` 等直链。
- 播放链接签名 60-100 秒过期。

## 核心规则

- 播放链路必须测到底：主清单 → 子流清单 → key → ts 分片；主 m3u8 200 不等于能播。
- m3u8 明确给出 IV 时，所有分片按该固定 IV 解密；不要自己推导序号 IV。
- `localProxy type=hls` 可重写 m3u8：`#EXT` 行不动，KEY 的 `URI="..."` 包 key 代理，ts 行补全绝对 URL 后包 ts 代理。
- data-preview/data-play-src 若列表里已是 m3u8 直链，应把直链编码进 `vod_id` 或 play id，详情页不要再抓第一个 `data-preview`；详情页首个属性常是推荐位/错片。
- 有时效签名链接不能在详情页预解析后缓存；详情页放 pid，`playerContent` 点击时实时解析。
- iframe 或接口双模板时，正则不能只匹配数字 id；播放 id 可能是 16 位 hex 或字母数字。

## 门禁

- 抽测主 m3u8、子 m3u8、key、首个 ts 状态码和字节头。
- 对签名链接记录是否有时效；若有时效，必须实时解析。
- 对 data-preview 站，验证列表链接与 playerContent 输出完全一致，不被详情推荐位覆盖。

案例参考：`archive/cases/zip_refs/51hub-合集.md`、`archive/cases/zip_refs/拼多多-合集.md`、`archive/cases/zip_refs/91情报局播放双模板.md`。
<!-- 演进: 2026-09-03 | 来源: 雪落影视 py源开发 | 类型: pattern -->

## 多候选直链：先取全集再逐个探活，别信单接口返回

站点常有两类播放接口，行为差异很大：

| 接口 | 返回 | 可靠性 |
|---|---|---|
| 单地址接口（如 `/god/{pid}`） | 1 个实时签发 url，CDN 域名每次随机 | 低，实测 5 个资源里 4 个首次 403 |
| 线路全集接口（如 `/lines?pid=`） | 多字段（`url3` 逗号分隔直链、`m3u8`、`m3u8_2`、`ptoken`） | 高，逐个探活后 5/5 通过 |

对策：优先请求线路全集接口取候选池，逗号切分逐个探活，第一个通过即返回；失败才回退单地址接口并做 CDN 域名重写后再探活。

探活标准（轻量，只取前 1KB）：

    h = dict(self.headers); h["Range"] = "bytes=0-1023"
    r = self.session.get(u, headers=h, timeout=10, stream=True, verify=False)
    if r.status_code not in (200, 206): return False
    d = next(r.iter_content(1024), b"")
    return b"ftyp" in d[:16] or b"#EXTM3U" in d or "video/" in r.headers.get("Content-Type", "")

注意 mp4 直链的 Content-Type 常是 `application/octet-stream`，不能只靠 MIME 判定，必须看 magic bytes（`ftyp` 在偏移 4~8）。

## CDN 域名重写表必须配探活，不能盲信

前端 JS 里的域名重写规则（按 tos 标签 + 黑名单二选一）只是站方经验值，实测同一张表：`tos-alisg-i-0000` 有 6~8 个 host 可用，`tos-alisg-v-0000` / `tos-maliva-o-0000-us` 全部 403/404。重写后仍需探活，探活不过就换候选。

## m3u8 伪装成 PNG（pako 压缩）

若 m3u8 URL 返回体的 magic 是 `\x89PNG`，说明是伪装 + 压缩：前端做法是 `Uint8Array.slice(offset)` 去掉伪装头后 `pako.inflate`，再把 `.ts` 路径批量替换为绝对 CDN 地址。Python 侧等价 `zlib.decompress(data[offset:])`（zlib 头）或 `zlib.decompress(data[offset:], -15)`（raw deflate）。offset 与 chunk 大小常被 XOR 混淆（如 `264939^264177` = 3354，`466042^482426` = 16384），先算出常量再动手。若已有可用直链候选，可跳过这条链路。
