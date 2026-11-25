---
name: py写源技能
description: 多模块 v9.5。跨 Agent 全类型 Spider 自动开发技能；强化真直链响应门禁、递归静态验收、正式 JSON Schema 和苹果CMS API契约。新增盾类型分诊与过盾决策（CF/滑动验证/JS挑战/WAF/设备指纹/解析站）、huadong 滑动验证纯计算破解、TVBox 运行时状态持久化（类属性缓存坑/保序探活/Android UA）、搜索设置伪分类与多站聚合搜索、XBPQ↔Python 映射与同key双层筛选、全站整页base64/XOR图片/POST播放解密。
---

# py写源技能 v9.5 多模块版

## 1. 目标

输入站点 URL 和可选需求，自动完成需求归一化、站点分析、站点画像、策略选择、代码生成、静态检查、六接口测试（含 homeVideoContent）、播放/阅读/图片/队列端到端验证、自动修复和最终交付。

禁止未分析直接套模板。禁止把未测试源称为完成。

## 2. Operit 工具调用协议

本模块版面向 Operit。优先使用当前会话中实际可用的工具和已激活的包，不假设每个任务都存在或需要全部 py_mcp 工具。工具调用以解决当前阶段问题为准，避免无收益的重复抓取、重复调试和重复测试。

工具优先级：

1. 站点首次分析或结构不明确：优先 `py_mcp:analyze_website`；若当前未提供该工具，使用 `visit_web`、浏览器或 `extended_http_tools` 获取页面/API，再分析。
2. 选择器有实际匹配问题：调用 `py_mcp:debug_selector`；如果选择器已有真实证据且数据正常，不重复调用。
3. 代码生成后需要接口回归：调用 `py_mcp:test_interface`；若无法调用，使用目标框架本地测试或 `super_admin` 终端（Ubuntu heredoc）。
4. 代码规范和字段检查：调用 `py_mcp:evaluate_source`；小改动可先用静态检查，存在跨接口风险时再评估。
5. 播放链接为空、仍是播放页、iframe/API/token 未解析：调用 `py_mcp:debug_play_link`；直链已确认可用时不调用。
6. 文件操作：使用 Operit 文件工具；代码执行优先用 `super_admin` 终端（Python heredoc，可装依赖、可访问被改文件）；网页读取使用 `visit_web`/浏览器/HTTP 工具。工具名以当前会话实际暴露的名称为准。

禁止行为：

- 不把逻辑别名当成真实工具名调用。
- 不因 Skill 写了某工具就盲目调用不存在的工具。
- 不在页面/API已确认正常时重复 analyze、debug 或 fetch。
- 不因某个专用工具不可用而跳过分析；必须按上述降级路径继续。
- **非必要不使用 `code_runner`**。该工具参数必须是严格 JSON 对象（`{script:...}` 多行长代码一碰就坏），且跑在无 `base.spider`/无 pycryptodome 的隔离 Python 环境，测源十测九败。它不参与：源文件增删改、编译校验、运行环境依赖、真实弹幕/接口联调。执行任意脚本一律改用 `super_admin` 终端（`python3 - <<'PY'`）或 `py_mcp` 文件工具；仅用户点名要求时才可考虑 code_runner。

## 3. 唯一执行流程

```text
需求归一化
→ 判断并加载匹配模块
→ 选择合适的分析工具（专用分析优先，普通工具可替代）
→ 建立站点画像
→ 仅在选择器/播放策略有疑点时调试
→ 生成 Spider
→ 静态检查
→ 按风险选择接口回归工具
→ 端到端播放/阅读/图片/队列验证
→ 失败时针对性 debug_selector/debug_play_link
→ 按需 evaluate_source
→ 交付
```

模块加载是强制的，工具调用不是机械强制的。首次写源必须完成有效站点分析；可以使用 `py_mcp:analyze_website`，也可以使用 Operit 的网页/HTTP/代码工具完成等价分析。选择器、路由和播放策略必须以后者的真实结果为准。

站点分析必须先按 `schemas/site_profile.json` 组织站点画像，再按 `schemas/spider_ir.json` 形成实现中间表示（Spider IR）。简单任务可只在当前上下文中维护，不强制落盘；跨轮次、跨 Agent、复杂加密/多模块任务必须保存或在交接报告中完整列出。两个文件保存 Draft 2020-12 Schema 定义，实际画像与 IR 必须另存为实例文件并校验，不得用默认占位值冒充实测结果。

## 4. 决策优先级

用户明确指定 > 当前站点实测 > API/HTML字段 > URL特征 > 模板默认值。未指定模式默认 T4（T4 模式保留，后续再优化）；未指定内容类型按真实行为判断；MacCMS 路由优先归 video；“动漫”按播放列表或章节图片判断。

### 4.1 核心裁决规则

**能用 > 稳定 > 齐全 > 精简**。模板中的播放链接和 filters 仅作格式参考，必须依据目标站实测结果实现。交付版代码保持零注释、零 docstring、零空壳方法、零 `__main__` 测试块、零未使用 import。

## 5. 统一契约

T4 必须继承 `from base.spider import Spider`，有 `init` 和 `getName`；客户端使用独立 `class Spider`。所有 T4/羊壳源必须实现 `homeContent`、`homeVideoContent`、`categoryContent`、`detailContent`、`searchContent`、`playerContent` 六个接口；非羊壳客户端若框架不调用 `homeVideoContent`，也应提供兼容返回。

分类至少返回 `page`、`pagecount`、`limit`、`total`、`list`；详情返回 `{"list":[vod]}`。核心字段为 `vod_id`、`vod_name`、`vod_pic`、`vod_play_from`、`vod_play_url`。线路用 `$$$`，线路内剧集用 `#`，剧集格式为 `名称$播放ID`。统一使用 `self.headers`。

## 6. 冲突修正规则

模块中的历史示例保留知识价值，但最终代码禁止：精确 class XPath、99/999 伪分页、示例域名、`__main__` 测试块、空壳接口、重复请求、未经解析的播放页冒充直链。历史选择器、token、密钥和播放地址必须重新验证。

## 7. 需求识别与模块加载矩阵

先根据用户话术和站点特征确定需求，再加载模块。用户明确需求优先；站点分析发现的特征可追加模块。

**装载规则**：所有任务必载 `validators/gates.md`；按下表取模块集合，多条件命中取并集，模块读取可并行，不命中的模块不加载。模块名缩写：`maccms`/`api_spa`/`nonvideo` 指 `templates/` 下同名模板，其余均指 `strategies/` 下同名模块。读取后先执行模块内“适用条件/关键约束”再套模板；模板只是实现素材，不能覆盖统一契约。模块冲突优先级：当前站点实测 > 主 `SKILL.md` > 专项策略模块 > 类型模板 > 历史归档。模块缺失或读取失败必须报告，并用 `archive/legacy-v5.md` 降级，不得假装模块已激活。分析阶段读 `schemas/site_profile.json`，编码前读 `schemas/spider_ir.json`；画像与 IR 实例必须另存，禁止覆盖 Schema 文件。

### v8.1 追加经验：Nuxt/SSR 短剧站与 folder 分页

- 页面含 `__NUXT_DATA__`、`window.__NUXT__`、`_payload.js`、Nuxt 路由 chunk，且普通 HTML 选择器为空时，不按 XPath 模板硬写；必须还原 Nuxt 索引数组或读取 payload JSON，再递归扫描真实字段。
- 动态域名可能是“入口发布页 → 中转页 → `Base64.decode/atob` 解出 `words.random()+后缀` → 随机前缀域名”的组合链路；必须把发布页跳转、中转页解码、随机子域生成和 Nuxt/API 数据解析分开验证。
- Nuxt 影视/短剧站的列表项如果含 `episode_id`，必须把它保留进 `vod_id` 或播放 ID，例如 `drama-play?id={video_id}&episode_id={episode_id}`；丢失 `episode_id` 可能导致播放页没有 `video_url`。
- 原站裸 ID 播放入口坏不代表资源不可播；必须对比裸入口 `drama-play?id=xxx` 与列表入口 `drama-play?id=xxx&episode_id=yyy`。若后者能返回 `video_url`，源应以列表 episode 入口为准。
- 返回 `vod_tag:"folder"` 的项目不是详情页，而是可分页目录；必须在 `categoryContent(folder_id, pg, ...)` 里实现二级目录和翻页，`detailContent()` 只能做兼容兜底。
- folder 二级分页 URL 必须实测，可能是 `/page/2/`、`?page=2`、`/p/2` 或接口参数；不能固定 `pagecount=1`。
- 图片字段非空不代表可显示；要验证魔数、0 字节、`binary/octet-stream`、加密二进制。若需要本地代理解密，图片代理只处理图片，不能误用于 m3u8/mp4 播放 URL。
- 列表页禁止默认逐条请求详情页补封面/备注。除非用户明确要求“完整优先”，否则列表只用当前页数据；二级/详情请求只在用户点击后发生。
- `vod_remarks` 只能提供角标文本；角标左上/左下由客户端 UI 决定，Spider 不保证位置。

### 统一矩阵

| 站点特征 / 需求 | 加载模块 | 验证重点 |
|---|---|---|
| MacCMS v8：`/frim/index`、`/search.php?searchtype=5` | maccms | v8 分类、POST 搜索、`var now` 播放 |
| MacCMS v10：`/index.php/vod/show`、`/index.php/vod/detail` | maccms | v10 分类、GET 搜索、`player_data` |
| 通用影视（电影/电视剧/综艺/动漫播放） | maccms | 分类、详情线路、playerContent 最终 m3u8/mp4 |
| 合集帖/热榜帖/聚合帖，详情正文含多个按钮指向视频帖 | maccms + album_sub_list | `_subs` 分集提取、真实视频 `_eps` 优先、播放页实时解析 |
| `/index.php/vod/...` 与 `/index.php/art/...` 共存，图集/小说混排 | maccms + nonvideo + mixed_cms_art | vod/art 分流、pics/novel 播放、真实大图 |
| `player_aaaa`、`player/api.php`、`playerconfig.js`、线路名错位、`parse:0` 仍返回播放页、XOR 后伪协议 | maccms + encrypted_iframe | sid/from/show/media 四层映射、解密样本、iframe/API 递归、最终真 m3u8 |
| AES、CryptoJS、XOR、RSA、atob、Base64、Hex、iframe、`customStrDecode/deString` | maccms + encrypted_iframe | 同上四层验证 |
| 苹果CMS采集 API：`/api.php/provide/vod`、ac=list/detail、主分类 t=0 条、suggest 搜索 | api_spa + applecms_api | JSON 字段、子分类合并、批量补图、播放字段直出 |
| SPA/API：首页只有 app 容器、token、enc:true、VITE_BASE_URL、parameterKey/parameterIv | api_spa + nuxt_devalue_api + encrypted_api + encrypted_iframe | API base、鉴权、参数加密、响应解密 |
| Nuxt/SSR：`__NUXT_DATA__`、payload、动态 chunk、短剧 API、`episode_id`、cursor/offset 翻页 | api_spa + nuxt_devalue_api + rsc_flight + encrypted_iframe + resilience | devalue 还原、API base 挖掘、episode_id 保留、参数有效性对比 |
| RSC：首页含 `self.__next_f.push` 或 `__next_f` | rsc_flight（配合 api_spa + nuxt_devalue_api） | Flight payload 还原、追踪 apiBaseUrl/baseURL/apiKey；不得以详情链接数冒充视频数 |
| Vite/SPA 加密 API：AES 参数、响应密文、guest/anonymous token、成人确认、locked 付费集、X-Zone | api_spa + encrypted_api | API 域名探活、URL 编码、请求头大小写、guest-confirm-playback、locked 跳过 |
| `play_data`、pako、`inflateRaw`、raw deflate、Base64 压缩 JSON | compressed_payload | Base64 + raw deflate/zlib 解码 |
| Dean Edwards Packer、`eval(function(p,a,c,k,e,d)`、`split('&#124;')` 字典 | js_unpack | 字符串解包、播放地址二次扫描 |
| 404XAV：`web_api_types`、`web_grid_box`、`cell_box`、`/detail/{cid}/{hash}.html` | 404xav | 动态域名、folder 路由、play_data 播放链路 |
| 发布页 key+data、appConfig、`words.random`、“加载中”href、raw deflate、解出域名不是目标站 | domain_release + resilience | 解密方案 A/B、href 直提、目标站结构验证、候选域名探活 |
| 动态域名：永久/最新地址、zz_line/zz_backup_line、随机子域、频繁更换、限流、图片扩展名异常、JS 时长 | resilience | 发布页解析、域名池、探活切换、图片魔数、时长转换 |
| shell 端没数据、被墙域名、系统 VPN 不生效、`Network is unreachable`、代理端口、`extend.proxy` | proxy_network | session 代理探测、所有请求显式 proxies、禁止写死私人代理 |
| `localProxy`/`proxyPic`、图片 CDN 超时、图片有 URL 但壳端不显示、`binary/octet-stream` | proxy_network + encrypted_iframe | AES key/iv 长度、JPEG EOI 截断、magic bytes、真实 MIME |
| MissAV/MissAVt/91hub 图片加密 | proxy_network + encrypted_iframe（必要时 + resilience） | 图片代理走代理、CDN 替换 |
| JAV CDN：非图片魔数、AES 图片、发布页多类型域名、角标误渲染 | jav_cdn_aes + proxy_network | 图片魔数、AES-CBC、getProxyUrl、localProxy、角标职责分离 |
| m3u8 主清单能开但不能播、HLS AES-128、`#EXT-X-KEY`、ts/key CDN、签名过期、data-preview/data-play-src 直链 | hls_localproxy + proxy_network | 主/子清单/ts/key 逐级验证、固定 IV、m3u8 重写、实时解析、防推荐位错链 |
| Cloudflare/WAF、Next.js、`/_next/`、`__NEXT_DATA__`、HTML 403 但 `/api/` 返回 JSON | proxy_network + api_spa | 移动 UA、Referer/cookie 实测、API 字段优先、HTML fallback |
| 403/503、返回验证页或空页、`Just a moment`、`滑动验证`、`/_waf/`、HTTP 418、cookie 含 `__mx*__` | shield_routing | 先分诊盾类型；真内容校验（盾页词+站点词双判）；请求间隔 ≥1.5s；Referer 用触发页 |
| `huadong_*.js`、`slideBox`、滑块拖到最右即过、无缺口比对 | slider_huadong | md5(每字符charCode+1)；三处必带触发页 Referer；key 从文件名取 |
| 每次翻页/搜索都重探域名、设置「设了不生效」、并发探活域名漂移、桌面 UA 拿跳转壳页 | tvbox_runtime | 类属性/模块级缓存、`ex.map()` 保序、Android UA、localProxy 返回格式 |
| 需要用户切换搜索站点/并发页码/排序、多站聚合搜索、副标题标来源页码 | search_agg_menu | 伪分类+folder卡+编码vod_id+确认卡；`==` 先于 `startswith`；勾选即生效 |
| 手头有 XBPQ JSON 要转 Python、女优/主题一级二级值域不同 | xbpq_mapping | 播放数组vs播放列表；同 tid 多组同 key 双层筛选；`ext['sort']` 统一消费 |
| 页面 HTML = 单引号包裹超长串、图片 XOR、POST 取密文播放、多个/单个/零个 dplayer | nonvideo_playext | 双重 b64 解码、XOR 后查魔数、POST 后实测 `#EXTM3U`、专辑三形态各测 |
| `Just a moment`、`challenge-platform`、Turnstile，浏览器可开但 requests 403，改 UA 仍无效 | cf_tls_fingerprint + proxy_network | CipherSuiteAdapter、18 项套件、prime256v1、verify=False、域名池重试、媒体真链门禁 |
| 标签制 `/s/{tag}/`、Top Tags、主次分类或组合筛选 | tag_two_level_filter | 官方标签提取、排除演员名、推荐区分离、组合标签真实分页 |
| WordPress：`/wp-json/wp/v2`、`featured_media`、`content.rendered` 图集正文 | nonvideo + wordpress_image_api | 批量补封面、双缓存、图片白名单、`pics://` 顺序 |
| 图片站一级/二级分类、客户端不支持图片 folder 路由 | nonvideo + image_category_filter | class 与 filters 分离、默认首个子分类、实测分页 |
| 图片缓存旧域名、CDN 部分失效、需要全量图片可用性检查 | image_cdn_audit | 全量唯一 URL、origin 替换、MIME/长度审计 |
| 二级/三级页面、演员/标签/专题 folder、`vod_tag`、虚拟分类、folder + filters | folder_routing | categoryContent 分发、folder 翻页实测、filters 注册、id 前缀不冲突 |
| 羊壳没数据、只有推荐页、分类空白、XBPQ/JSON 转 py、filters 类型异常、homeVideoContent 缺失 | yk_runtime | 继承基类、class 字段、filters dict、标准签名、翻页字段 |
| 小说/漫画/图片/音乐/直播（novel/manga/image/music/live） | nonvideo（music 加 queues） | `vod_player=novel`/`pics`、`novel://`、`pics://` 顺序、真实 stream、图片魔数 |
| 短剧、微短剧、竖屏、滑动流 | nonvideo + maccms + queues | 分集、竖屏播放、点击项首位 |
| 抖音式随机上下滑、点击哪条第一条就是哪条 | queues + api_spa | 第一项固定、后续随机、避免续播缓存 |
| 改源/优化成品源 | target_source_first | 先记录行为基线，最小改动并回归对比 |
| 不确定类型、混合站、多模块站 | 先 gates，按画像追加 | 每个模块至少一条完整链路 |
| 原文细节缺失、历史案例对照 | archive/legacy-v5.md | 只参考，必须重新实测 |

### 通用 API 参数校验

分类、搜索、分页、标签、排序、年份和语言参数必须通过返回 ID、total、页码或字段值对比确认是否生效；HTTP 200 不代表参数已被服务端采用。整体请求信封加密时，分别验证成功密文响应和明文错误响应。

## 8. 代码模板装载与验证

按站点画像和实现中间表示选择代码模板，模板只提供实现骨架，选择器、字段、路由和播放策略必须以目标站实测为准：

- `templates/code/nonvideo.py`：小说/图片/漫画/音乐/直播/短剧等非影视类型的基础 Spider 模板，含 localProxy/proxyPic 与媒体门禁，具体类型按 `templates/nonvideo.md` 示例扩展。
- `templates/lib/`：HLS 重写/解密、图片解密/魔数、folder 路由、队列、episode 保留通用库（hls.py、image.py、folder.py、queues.py、episode.py、shield.py 盾检测/slider 破解/保序探活）。
- `templates/code/api.py`：API/SPA 类型 Spider 代码模板。
- `templates/code/maccms_v8.py`、`templates/code/maccms_v10.py`：MacCMS Spider 代码模板。

生成代码后必须执行 `validators/static_check.py`；模板中的占位域名只能用于开发示例，交付前必须替换。之后还必须执行 `validators/schema_check.py` 校验画像/IR 实例、`validators/interface_check.py` 做独立六接口导入回归、`validators/behavior_check.py` 做行为契约回归，并对真实接口 JSON 执行 `validators/runtime_check.py`；导入失败、Schema 缺失、接口缺失、行为契约失败、分页字段缺失或线路数量不一致均不得交付。四层线路（sid/from/show/media）、HLS 分片、图片代理与解密、folder 路由和队列行为必须按目标站实测结果逐项记录，缺少实测一律标记未验证。

## 9. 动态内容站通用经验

- 页面只有 Vue/React 模板时，必须提取业务 JS，追踪 axios/fetch/$Http 请求，实测 JSON 接口、字段和分页；不能把模板占位文本当数据。
- 自定义图片属性以 `z-image-loader-url`、`x-image-loader-url` 为优先线索；URL 非空仍需验证响应长度、Content-Type 和图片魔数，binary/octet-stream 需要读取前端解密器并由 localProxy 返回真实图片。
- HTML 属性中的播放器配置必须先解码 HTML 实体，再还原 `\/`，最后解析 JSON；多个播放器节点必须全部转换为剧集列表。
- `parse:0` 只能用于实测确认的 HTTP/HTTPS 媒体地址；M3U8 需验证 `#EXTM3U`，HTML 播放页不得冒充直链。
- 博主、UP 主、专题和榜单使用 `vod_tag: "folder"`，由 `categoryContent` 分发二级作品列表；榜单筛选必须映射真实路径或接口参数。
- 同时存在相对时间和绝对日期时，优先将相对时间写入 `vod_remarks`，绝对日期仅作回退。

## 10. 完成标准

只有静态检查、统一契约检查、六接口测试（含 homeVideoContent）和对应类型端到端链路全部通过，才可写完成。模板只能标记为模板通过，不能标记为站点完成。没有目标 URL、真实站点响应或媒体样本时，分类、详情、线路、筛选、分页、图片、HLS、解密和播放均必须标记为未验证，不得用模板默认值代替。缺少网络或执行工具时必须写未验证。遇到登录、验证码、WAF、签名不明、解密参数缺失或站点持续不稳定时输出阻塞报告。

## 11. 输出格式

工作中只用 1～2 句汇报当前进展和必要问题，不展开过程，不粘贴代码、代码引用、日志或工具输出。

完成后只简要说明：完成内容、测试结论、遗留问题。测试仅汇报通过、失败及必要原因，不罗列测试过程、接口明细或修复轮数。普通任务控制在 1～3 句话；只有用户明确要求时才展示代码、日志、验证细节或完整报告。

## 12. 案例索引

- `archive/cases/getav-me.md`：Cloudflare/Next.js API 优先、Android UA、年龄验证 cookie。
- `archive/cases/missav-image-debug.md`：MissAV 系 localProxy、AES-CBC 图片解密、JPEG EOI 截断和 CDN 替换。
- `archive/cases/nkdvd-line-sign-debug.md`：MacCMS sid/from/show 线路错位、playerconfig 映射、XOR+双字母表 sign 解密和真直链门禁。
- `archive/cases/xlys-lines-cdn-debug.md`：Spring 自研站筛选区定分类、CryptoJS WordArray key vs passphrase、/lines 多线路探活、字节系 CDN 重写、jsessionid 分页、搜索验证码墙与 UA 白名单。
- `archive/cases/acfan-xor-image.md`：Nuxt SSR 封面/漫画图片前端 XOR 加密（前100字节异或、密钥 `2020-zq3-888`）、封面域与播放域分离、m3u8 经 authPath 签名接口解码。
- `archive/cases/zip_refs/`：references.zip 原始实战案例库（51hub、missav、拼多多、短剧站等 50+ 站），只作溯源，不直接执行；第 7 节矩阵中的 strategies/ 模块均由其抽象而来。

## 13. 归档与隔离

- `archive/`、`archive/cases/` 仅作只读溯源，不参与模块通配加载，不作为当前规则直接执行。
- 正式模块只读取主 `SKILL.md` 明确引用的 `strategies/`、`templates/` 模块、`validators/gates.md` 与 `schemas/` 中明确点名的 Schema。
- 禁止在案例目录执行 `.py`；测试产生的 `__pycache__`/`.pyc` 必须清理。验证路径使用 `SPIDER_ROOT` 环境变量，未设置时才回退到 `/sdcard/Download`。