# Next.js RSC Flight 数据解析策略 v9.5
适用于 Next.js App Router、RSC Flight、页面主体为空壳但 SSR 数据或业务 API 可用的站点。
## 适用特征
- HTML 或脚本中出现 `self.__next_f.push`、`__next_f`。
- 存在 `/_next/static/chunks/`，普通 HTML 选择器为空或数量明显异常。
- 页面源码中有 `clientConfig`、`apiBaseUrl`、`apiKey`、`canonical_path` 等业务字段。
## 解析流程
1. 请求首页并记录状态码、正文长度、script src。
2. 检查 `self.__next_f.push`，按出现顺序提取其中的 JavaScript 字符串参数。
3. 优先使用 JSON 字符串解码处理转义；只有解码失败时才使用受限的 `unicode_escape` 兼容方案，不要把整个 Flight 文本直接当普通 JSON。
4. 拼接还原后的 Flight 片段，扫描真实字段组合：视频对象至少结合 `id/name/canonical_path`，播放对象结合 `play_links/m3u8_url/episode` 等字段。
5. 同时扫描 RSC payload 和业务 chunk 中的 `apiBaseUrl`、`baseURL`、`apiKey`、接口路径；发现 API 后优先走接口，HTML 仅作回退。
6. 如果出现 `$Lxx`、索引引用或延迟对象，建立索引解析或递归扫描，不能只取表面字符串。
7. 对分类、搜索、分页、排序参数做返回 ID、total 和页码对比，确认参数真实生效。
## 约束
- RSC Flight 是数据传输格式，不等于完整 JSON，也不保证所有 Next.js 站点都含业务数据。
- 页面中 `/movie/` 链接总数不得直接作为视频条数。
- 不得把 `id/name` 两个通用字段单独当成视频对象；需要结合路由、类型、封面、分类或播放字段判断。
- RSC 解码不完整、API base 不明或字段未确认时，记录阻塞原因，不硬套 MacCMS XPath 模板。
## 验证门禁
- 至少确认一个真实列表对象、一个详情对象和一个播放或 episode 对象。
- 至少对比两个分类或分页结果的 ID；搜索至少验证关键词结果与空关键词不同。
- API 成功响应、明文错误响应和加密响应分别记录处理结果。
案例参考：`archive/cases/fktv-rsc-aes-api.md`。
