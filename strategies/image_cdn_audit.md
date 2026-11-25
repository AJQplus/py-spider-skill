# 图片 CDN 全量审计策略 v9.5

## 适用条件
图片 URL 来自缓存、接口或历史数据；部分分类缺图；修改 CDN 后仍有旧绝对地址；或需要确认多个 CDN 域名是否可用。

## 处理规则
1. 先区分实时相对路径和缓存绝对 URL。相对路径由统一 URL 函数补全，绝对 URL 不再重复拼接。
2. 替换旧 CDN 时只替换 URL origin，保留 path、query 和 fragment。
3. 递归遍历列表、字典和嵌套结构，提取全部唯一图片 URL，不以单个样本代表全量。
4. 每个 URL 至少检查最终状态码、Content-Type、响应长度；扩展名不是图片有效性的充分条件。
5. `binary/octet-stream` 或加密响应必须先查明前端解密流程，不能直接当图片返回。图片代理只处理图片，不处理 m3u8/mp4。

## Python 审计骨架
```python
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse

def _replace_origin(url, old, new):
    p = urlparse(url)
    if p.scheme and p.netloc == urlparse(old).netloc:
        n = urlparse(new)
        return urlunparse((n.scheme or p.scheme, n.netloc, p.path, p.params, p.query, p.fragment))
    return url

def _audit_one(self, url):
    try:
        r = self.session.get(url, headers=self.headers, timeout=12, stream=True)
        data = next(r.iter_content(32), b'')
        ctype = r.headers.get('Content-Type', '').lower()
        ok = r.ok and len(data) > 0 and ctype.startswith('image/')
        return url, ok, r.status_code, ctype
    except Exception as e:
        return url, False, 0, str(e)

def audit_images(self, urls):
    urls = sorted(set(x for x in urls if x))
    with ThreadPoolExecutor(max_workers=10) as pool:
        result = list(pool.map(self._audit_one, urls))
    return {'total': len(result), 'ok': sum(x[1] for x in result), 'fail': sum(not x[1] for x in result), 'items': result}
```

## 完成标准
报告必须给出全量唯一 URL 的 total、ok、fail；只有失败数为 0 才能声明 CDN 审计通过。
