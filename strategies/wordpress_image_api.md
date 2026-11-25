# WordPress 图片 API 策略 v9.5

## 适用条件
WordPress 图片、写真、壁纸或图集站；接口通常位于 `/wp-json/wp/v2`；列表项带 `featured_media`，图集正文位于 `content.rendered`。

## 实现规则
- 列表请求优先使用 `_fields=id,title,featured_media`，不要逐条请求详情补封面。
- 收集当前页的媒体 ID 后，用 `media?include=id1,id2&_fields=id,source_url` 批量补封面。
- 用 `_media_cache` 按媒体 ID 缓存封面，跨页复用；用 `_pic_cache` 按文章 ID 缓存正文图片，`playerContent` 命中缓存时不重复请求。
- 正文图片按 HTML 出现顺序提取，过滤 `data:`、logo、图标、广告和非图片 URL。
- 图片扩展名只检查 URL path，允许 `jpg/jpeg/png/webp/gif`，不要用整 URL 子串判断。无扩展名图片必须通过响应 MIME 和魔数验证后才保留。
- 缺图或单条解析失败时跳过该项，不影响整页结果。封面可用 `vod_remarks` 标注图片数量。

## 参考实现
```python
from urllib.parse import urljoin, urlparse

def _fix(self, url):
    return urljoin(self.host.rstrip('/') + '/', (url or '').replace('\/', '/'))

def _is_img(self, url):
    if not url or url.startswith('data:'):
        return False
    path = urlparse(url).path.lower()
    return path.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))

def _batch_pics(self, media_ids):
    ids = list(dict.fromkeys(x for x in media_ids if x))
    missing = [x for x in ids if x not in self._media_cache]
    if missing:
        data = self._get_json(self.api + '/media', {'include': ','.join(map(str, missing)), '_fields': 'id,source_url'})
        for item in data if isinstance(data, list) else []:
            mid, url = item.get('id'), self._fix(item.get('source_url'))
            if mid and url:
                self._media_cache[mid] = url
    return {mid: self._media_cache[mid] for mid in ids if mid in self._media_cache}
```

## 验证
验证封面 HTTP 状态、响应长度、Content-Type 和图片魔数；验证 `pics://` 顺序与正文顺序一致，并确认缓存命中后不再请求详情。
