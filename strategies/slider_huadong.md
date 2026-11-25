# 滑动验证 huadong_*.js 纯计算破解模块 v9.5
## 适用特征
```html
<title>滑动验证</title>
<div class="slideBox"><div class="slider"></div></div>
<script src="/huadong_296d626f_<32位hex>.js?id=<时间戳>"></script>
set-cookie: server_name_session=xxx; Max-Age=86400; httponly
```
同一模板多站共用，看到 `huadong_` 就是这套。
## 破解原理（纯计算，无图片无轨迹）
JS 逻辑：`key` 是 32 位 hex（也在 js 文件名里），`value` 是硬编码 32 位 hex；
签名 = `md5(每字符 charCode + 1 直接拼接)`；验证接口 `/<prefix>_yanzheng_huadong.php?type=<32位hex>&key=<key>&value=<签名>`。
滑块只需拖到最右端（`deltaX >= sliderWidth - handlerWidth`）即 complete，无缺口比对、无轨迹检测。
## 标准实现
```python
import re, hashlib
SLIDER_RE = re.compile(r'src="(/huadong_[^"]+\.js)\?id=(\d+)"')
def solve_slider(session, host, html=None, target_url=None, timeout=15):
    """target_url = 触发验证的那个页面，★ 全程 Referer 都用它"""
    try:
        target_url = target_url or (host + '/')
        if html is None:
            r = session.get(target_url, timeout=timeout)
            html = r.text
            if r.status_code != 403 and '滑动验证' not in html:
                return True
        m = SLIDER_RE.search(html)
        if not m:
            return False
        js_path, ts = m.group(1), m.group(2)
        # 拉 JS：必须带触发页 Referer
        js = session.get(host + js_path + '?id=' + ts,
                         headers={'Referer': target_url}, timeout=timeout).text
        # key 优先从文件名取（比 JS 内容里找更稳）
        key = js_path.rsplit('_', 1)[-1].replace('.js', '')
        if not key:
            km = re.search(r'key\s*=\s*"([^"]+)"', js)
            key = km.group(1) if km else ''
        vm = re.search(r'value\s*=\s*"([^"]+)"', js)
        if not (key and vm):
            return False
        # 签名 = md5(每字符 charCode+1 直接拼接)
        sign_src = ''.join(str(ord(c) + 1) for c in vm.group(1))
        sign = hashlib.md5(sign_src.encode('utf-8')).hexdigest()
        # 验证接口路径 + type 也从 JS 提，提不到用默认
        pm = re.search(r'c\.get\("(/[a-z0-9_]+_yanzheng_huadong\.php)\?type=([a-f0-9]+)&key="', js)
        vpath, vtype = (pm.group(1), pm.group(2)) if pm else (
            '/a20be899_96a6_40b2_88ba_32f1f75f1552_yanzheng_huadong.php',
            'ad82060c2e67cc7e2cc47552a4fc1242')
        # 打验证接口（★ 也带 Referer）→ 服务端种 cookie
        session.get('%s%s?type=%s&key=%s&value=%s' % (host, vpath, vtype, key, sign),
                    headers={'Referer': target_url}, timeout=timeout)
        return True
    except Exception:
        return False
```
## 带验证的请求包装
```python
def _fetch_json(self, url, need_verify=True):
    try:
        if need_verify and not self._verified:
            self._verified = solve_slider(self.session, self.host, target_url=url)
        resp = self.session.get(url, timeout=15)
        if resp.status_code == 403 or '滑动验证' in resp.text:
            self._verified = False
            if solve_slider(self.session, self.host, target_url=url):
                resp = self.session.get(url, timeout=15)
        if resp.status_code == 200 and resp.text.lstrip().startswith(('{', '[')):
            return resp.json()
        return {}
    except Exception:
        return {}
```
## 踩坑清单（每条实测踩出）
| # | 坑 | 正确做法 |
|---|---|---|
| 1 | Referer 用首页 | 用触发验证的那个页面 URL |
| 2 | 拉 JS 不带 Referer | 拉 JS 也要带 |
| 3 | key 从 JS 内容里找 | 更稳的是从文件名 `rsplit('_',1)` |
| 4 | 验证请求不带 Referer | 也要带 |
| 5 | 高频请求 | 连续 2 次即 `Connection aborted`，必须 sleep ≥1.5s |
| 6 | 跨环境搬 cookie | 部分站还有 `__mx*__` 设备指纹，浏览器导出的 cookie 无效，必须同进程连续完成 |
## 门禁
- 破解成功判据 = 再次请求目标页 `has_expected_content` 通过，不是仅看验证接口返回。
- 必须记录盾类型为 slider，并注明「纯计算破解」或「叠加设备指纹」。
