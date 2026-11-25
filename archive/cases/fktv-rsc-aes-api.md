# Fanke 类 Next.js RSC + AES API 站案例
## 站点特征
- Next.js App Router，页面含 `self.__next_f.push`。
- RSC payload 和 chunk 可发现 `/ysapi`、`apiBaseUrl`、`apiKey`。
- 自研影视 API，不是 MacCMS。
## API 行为
- 列表、详情、筛选、标签、推荐使用 POST。
- 请求信封包含 `deviceId/token/domain/referer/user_agent/shareCode/channel/ip/data`。
- 整体 JSON 使用 AES-128-ECB + PKCS7，再 Base64 作为 `application/octet-stream` body。
- 成功响应通常为密文，错误响应可能直接返回 JSON；先按首字符判断，再决定是否解密。
- 端点错误与参数错误的错误码可辅助判断接口存在性，但只能作为辅助证据，不能替代字段实测。
## 播放行为
- 详情返回线路和集数，`playerContent` 点击时重新请求详情获取 m3u8。
- m3u8、key、ts 地址有时效或状态依赖，不能在详情阶段长期缓存最终播放地址。
- m3u8 要求检查 `#EXTM3U`，并抽测 key 与首个 ts。
## 图片行为
- 明文 `img_*_source` 可作为封面来源。
- `.bnc` 返回 `application/octet-stream`，候选 key 解密后样本头部可符合 PNG；只有完成长度、IEND、图片解析和多样本验证后，才能认定完整解密规则。
## 可迁移经验
- 全局 tag 不等于分类筛选项，应通过不同 tag 返回的 `cat_id` 反推归属。
- API 参数必须通过返回 ID、total 和分页差异确认是否生效。
- 普通网页分析器可能把全页详情链接总数误当视频数量，RSC 站必须先还原 payload 或追踪业务 API。
