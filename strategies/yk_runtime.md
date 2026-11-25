# 羊壳/海阔 py 运行时兼容模块 v9.5

处理本机测试通过但羊壳/海阔里“没数据、只有推荐页、分类空白、翻页按钮缺失”的运行时差异。

## 适用特征

- 用户反馈“壳里没数据”“只有推荐页”“分类不显示”“推荐页空”。
- XBPQ/JSON 转 py，或从普通 Python 脚本改成 `base.spider.Spider` T4 源。
- 本机直接调用六接口正常，但客户端加载异常。

## 强制规则

- T4 必须 `from base.spider import Spider` 且 `class Spider(Spider)`。
- 必须实现 `homeVideoContent(self)`，返回 `{"list": [...]}`；推荐页常调用它，不存在会显示空。
- `homeContent(self, filter)` 必须返回 `class`；分类必须是 `{"type_id":..., "type_name":...}` 字典列表，不是字符串列表。
- `filters` 必须是 dict；没有筛选就 `{}`，不要返回 list。
- `categoryContent` 返回必须含 `page/pagecount/limit/total/list`；`pg` 入参先转 int。
- `detailContent` 返回 vod 必须含 `vod_play_from` 和 `vod_play_url`，否则壳端无法播放。
- 方法签名用标准参数：`homeContent(self, filter)`、`homeVideoContent(self)`、`categoryContent(self, tid, pg, filter, extend)`、`detailContent(self, ids)`、`searchContent(self, key, quick, pg="1")`、`playerContent(self, flag, id, vipFlags)`。

## 标准片段

```python
def homeVideoContent(self):
    return {"list": self._list(self._get(self.host))}

def categoryContent(self, tid, pg, filter, extend):
    pg = int(pg) if str(pg).isdigit() else 1
    return {"page": pg, "pagecount": pagecount, "limit": limit, "total": total, "list": items}
```

## 排障顺序

1. 先查是否继承基类、类名是否为 `Spider`。
2. 查 `homeVideoContent` 是否存在。
3. 查 `homeContent.class` 和分类字段格式。
4. 查 `filters` 是否 dict。
5. 查分类/搜索是否有 `page/pagecount/limit/total`。
6. 查详情是否输出线路字段。

案例参考：`archive/cases/zip_refs/羊壳py没数据排障清单.md`、`archive/cases/zip_refs/py源转换方法论.md`。
<!-- 演进: 2026-09-03 | 来源: 雪落影视 py源开发 | 类型: troubleshoot -->

## 「什么都不显示」的四层排查顺序

客户端完全空白（连报错都没有）时，按代价从低到高排查，不要一上来改选择器：

1. **顶层 import 缺库** —— `lxml` / `Crypto` / `bs4` 在壳端运行时可能不存在，任一顶层 import 失败会导致整个模块加载失败，客户端表现为静默空白。对策：解析只用 `re`，加密走 try/except 双通道（pycryptodome 优先 + 纯 Python 兜底），其余库全部按需 import 到函数内。
2. **type_id 与 URL 构造不匹配** —— type_id 里含 `?`、`&` 等 query 字符时，翻页拼接会产出非法 URL（如 `/s/all?type=0/2` → HTTP 400）。type_id 必须是纯 slug，query 在 `categoryContent` 内单独组装，且以 `?` 开头。
3. **filters 的 key 与 type_id 不一致** —— `self.filters` 的键必须逐个等于某个 `type_id`，否则筛选栏不联动（部分壳端还会连列表一起不渲染）。
4. **选择器/正则真的不匹配** —— 到这一步才去查 HTML 结构。

验证捷径：本机若无 `base.spider`，最小桩即可跑通六接口回归：

    mkdir -p /tmp/base && printf 'class Spider:\n    def getProxyUrl(self): return "http://127.0.0.1:9978/proxy?do=py"\n' > /tmp/base/spider.py
    cd <源目录> && PYTHONPATH=/tmp python3 <回归脚本>.py

## 入参鲁棒性（壳端实际传值与文档不一致）

不同壳端对同一接口传值差异很大，必须全部容忍：

- `pg`：可能是 `int` 也可能是 `str`
- `filter`：可能是 `True` / `False` / `None`
- `extend`：可能是 `dict`、JSON 字符串、空字符串 `""`、`None`
- `tid`：可能是 `str` 也可能是 `int`
- `ids`：可能是 list 也可能是裸字符串

统一处理：

    pg = int(pg) if str(pg).isdigit() else 1
    slug = self.tids.get(str(tid), str(tid))
    for vid in (ids if isinstance(ids, list) else [ids]):

    def _ext(self, extend):
        if isinstance(extend, dict): return extend
        if isinstance(extend, str) and extend.strip().startswith("{"):
            try: return json.loads(extend)
            except Exception: return {}
        return {}

交付前用参数矩阵跑一遍（tid 三种 × pg int/str × extend 四种形态），全部返回非空才算过。
