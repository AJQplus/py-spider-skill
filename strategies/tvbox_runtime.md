# TVBox 运行时与状态持久化模块 v9.5
TVBox 每次请求都可能新建 Spider 实例，实例属性会丢；域名缓存、搜索设置状态必须跨实例存活。
## 适用特征
- 源体感很慢：每次翻页/搜索都重新走一遍域名探测链路（如重探 ~14s）。
- 搜索设置/页码档位/勾选站点「设了不生效」或每次回到默认。
- 并发探活返回的域名不是候选列表里排最前那个（域名漂移）。
- 桌面 UA 能跑，但真机/壳端拿到的是跳转壳页或数据结构变了。
## 1. 类属性缓存（最关键的坑）
`self._HOST_CACHE = {...}` 这种赋值会**创建实例属性**。新实例读 `self._HOST_CACHE` 时落到初始类属性 `{'host':'','ts':0}` → 缓存完全失效，每次请求都全链路探测。
```python
class Spider(_B):
    _HOST_CACHE   = {'host': '', 'ts': 0.0}        # 类属性
    _SUFFIX_CACHE = {'suffixes': [], 'ts': 0.0}    # 类属性
    def get_working_host(self):
        now = time.time()
        # ★ 读写一律用 type(self)._HOST_CACHE，不用 self._HOST_CACHE
        if type(self)._HOST_CACHE['host'] and now - type(self)._HOST_CACHE['ts'] < 1800:
            return type(self)._HOST_CACHE['host']
        ...
        type(self)._HOST_CACHE = {'host': alive[0], 'ts': now}
        return alive[0]
```
判据：修复后二次实例应 0.00s 命中，而不是再跑一遍探测。
## 2. 状态变量放模块级
搜索设置、页码档位等会话内状态，放模块级变量而非实例属性（实例重建会丢）：
```python
_SEARCH_PAGES = 10   # 模块级，会话内共享；重启回默认
```
（`PAGE_MARKS` 常量定义见 search_agg_menu.md，本模块不重复定义。）
在 `categoryContent` 里改值需 `global _SEARCH_PAGES`。
## 3. 保序探活（ex.map）
域名探测必须保序。`as_completed()` 会按完成顺序返回，导致命中不是候选列表里最优的那个（域名漂移）。
```python
from concurrent.futures import ThreadPoolExecutor

def probe(candidates, test):
    with ThreadPoolExecutor(max_workers=min(len(candidates), 10)) as ex:
        results = list(ex.map(test, candidates))   # ★ map 保序
    for host, alive in zip(candidates, results):
        if alive:
            return host
    return ''
```
`as_completed` 仅适用于「数量不重要、只要结果集合」的场景（如搜索多页聚合）。
## 4. Android UA 强制
站点 JS 检测 `isPC()`：桌面 UA 会被 `window.location.href = "http://xxx/pc.html"` 跳走，拿到跳转壳页。
必须使用配置内/实测的 Android UA：
```python
UA = ('Mozilla/5.0 (Linux; Android 16; 2510DRK44C Build/BP2A.250605.031.A3) '
      'AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 '
      'Mobile Safari/537.36')
```
Python/curl 复用同样要强制该 UA。
## 5. localProxy 返回格式严格对齐
`localProxy` 返回格式偏差会导致条目被静默丢弃或图片不显示：
- 成功：`[200, 'image/jpeg', bytes_content, {}]`
- 失败：`[404, 'text/plain', '', '']`（★ 空字符串，不是空字节 `b''`）
- 显式定义 `e64/d64/getProxyUrl`，不依赖基类 fallback；代理 URL 严格按 `getProxyUrl() + '&url=' + e64(img) + '&type=img'` 构造。
坏例：为避免条目丢弃直接返回固定占位图（掩盖问题）；`vod_pic` 塞代理 URL 但 e64 未定义（整行丢弃）。
## 6. 会话并发安全
女优/演员无头像兜底等并发补全，用**独立 requests**，不要共用 `self.session`，避免并发竞态。
## 门禁
- 交付前确认域名缓存/搜索状态为类属性或模块级；实例重建后仍命中。
- 域名探测必须保序（除非业务明确不需要顺序）。
- 壳端必须用 Android UA 实测，不以桌面 UA 结果为准。
- localProxy 成功/失败返回格式必须与既有已跑通实现逐字对齐。