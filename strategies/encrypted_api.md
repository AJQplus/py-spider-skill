# 加密 API 与游客身份模块 v9.5

处理 Vite/SPA 加密 API、AES 参数加密、响应解密、API 域名候选、guest token、成人确认和登录/付费墙边界。

## 适用特征

- JS 中出现 `VITE_BASE_URL`、`VITE_APP_API_BASE_URL`、`parameterKey`、`parameterIv`、`hash:true`、`data=<密文>`。
- GET/POST 参数被整体 AES 加密，响应 data 也可能是密文。
- API 返回 401、需要 guest/anonymous token、成人确认后免费内容才给播放链接。
- `episode.locked=True` 或明确付费集无 playback_url。

## 核心规则

- API 域名候选要从 JS 数组中提取并逐个探活，第一个可用即用。
- GET 参数若加密成 base64，必须 URL 编码；base64 中 `+/=` 不编码会导致参数错误。
- key/iv 必须按 JS 实测；有的站 key 与 iv 相同且固定 16 字节。
- 请求头字段大小写按实测，例如 `X-Zone` 不能随意改成 `Zone`。
- Go/后端校验错误可反推字段名和嵌套结构，但未解字段不能硬猜完成。
- 遇到成人确认/敏感内容，优先寻找 guest/anonymous 注册和 confirmAge/adult-confirmation 流程；拿到 token 后再请求免费集。
- 明确 locked/付费集没有 playback_url 时跳过，不用污染全局逻辑或伪造播放地址。

## 门禁

- 分别测试加密 GET、加密 POST、响应解密。
- token 流程测试：guest → confirm → playback。
- locked 集必须识别并跳过；免费集必须可播。
- 未破解字段或签名时写阻塞报告，不宣称完成。

案例参考：`archive/cases/zip_refs/91红果-API加密破解.md`、`archive/cases/zip_refs/游客身份解锁登录墙-付费墙API站.md`。
<!-- 演进: 2026-09-03 | 来源: 雪落影视 py源开发 | 类型: troubleshoot -->

## CryptoJS 第二参数：WordArray 还是 passphrase（必判）

复刻 `CryptoJS.AES.encrypt(data, keyArg, opts)` 前，先判定 `keyArg` 类型，两条路完全不兼容：

| keyArg | CryptoJS 行为 | 密文结构 | Python 复刻 |
|---|---|---|---|
| WordArray（被 `enc.Utf8.parse` / `enc.Hex.parse` 包裹） | 直接当原始 key，无 KDF | 纯 ciphertext | `AES.new(key_bytes, MODE_ECB/CBC)` |
| 纯字符串 | EVP_BytesToKey(MD5) 派生 key+iv | `Salted__` + 8 字节 salt + ciphertext | 自行实现 EVP KDF 再拼前缀 |

判据：源码里 key 变量有没有 `enc.*.parse(...)` 包裹。被包裹 = WordArray，不要加 salt/KDF。

实战代价：把 WordArray 当 passphrase 处理（多加了 EVP KDF + `Salted__` 前缀），签名接口返回 `{"code":403,"msg":"非法请求！"}`，排查耗时最长。

常见签名组合（雪落影视实例）：

    key = CryptoJS.enc.Utf8.parse(md5(id + "-" + ts).substring(0, 16))
    sg  = base64ToHex(CryptoJS.AES.encrypt(id + "-" + ts, key, {mode: ECB, padding: Pkcs7}).toString())

Python 等价（`base64ToHex` = atob 后逐字节 hex 大写；WordArray 无前缀，等于直接 hex）：

    def sign(i, ts):
        k = hashlib.md5((i + "-" + ts).encode()).hexdigest()[:16].encode()
        return aes_ecb_pkcs7((i + "-" + ts).encode(), k).hex().upper()

## 壳端无 pycryptodome：内置纯 Python AES 兜底

`from Crypto.Cipher import AES` 在部分壳端运行时不存在。写源时把 AES-ECB 实现为 try/except 双通道：优先 pycryptodome，失败回退纯 Python（S-box 运行时生成 + 标准 key expansion + 10 轮），实测输出与 pycryptodome 逐字节一致。这样单文件源不依赖任何加密库。

同理，能不用 lxml 就不用（纯 `re` 切块解析），顶层 import 一旦缺库整个源加载失败，客户端表现为“什么都不显示”，且没有任何报错线索。

## 整体请求信封加密
部分 Next.js/Vite 影视站会把完整请求信封加密后作为 body 发送。常见字段包括 `deviceId`、`token`、`domain`、`referer`、`user_agent`、`shareCode`、`channel`、`ip`、`data`。

实测为 AES-ECB + PKCS7 时，整个 JSON 先加密，再 Base64 编码，并以 `application/octet-stream` 发送。响应可能是 Base64 密文，也可能是明文 JSON 错误，处理顺序应为：空响应判断 → 首字符为 `{`/`[` 时直接 JSON 解析 → 否则 Base64 解码 → AES 解密 → 去 padding → JSON 解析。

请求头按站点实测保留 `version`、`deviceType`、`time`、`Content-Type`、`User-Agent`、`Origin`、`Referer`。`deviceId` 应动态生成或按站点规则持久化，禁止写入用户账号、私人 token、私人代理或 Cookie。

错误码可以辅助区分“接口不存在”和“参数错误”，但只能作为探测线索，不能替代字段、请求体嵌套结构和成功响应的实测。
## API 参数有效性
不能仅凭 HTTP 200 或返回 total 判断参数生效。必须比较不同 `cat_id`、`page`、`year`、`language`、`tag_id`、`order`、`keywords` 的首批 ID、total、页码和字段值；若结果 ID 完全相同，优先检查参数名、嵌套层级、必需的 position 或服务端静默忽略。
